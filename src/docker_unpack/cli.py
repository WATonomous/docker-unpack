import json
import sys
import tarfile
import tempfile
import time
from pathlib import Path
import os

from watcloud_utils.logging import logger, set_up_logging

set_up_logging()

from watcloud_utils.typer import app


def escape(value):
    """Escapes special characters in a string for use in a shell script."""
    return value.replace('"', r"\"").replace("'", r"\'")


def args_quoted(args):
    """Quotes each argument and joins them as a single string."""
    return " ".join(f'"{arg}"' for arg in args)


def generate_runscript(root_path: Path, img_config: dict):
    """
    Generates the runscript (entrypoint) for the Apptainer container.

    References:
    - https://apptainer.org/docs/user/main/cli/apptainer_run.html#examples
    - https://github.com/cvmfs/cvmfs/blob/531e6f6bd4b2fa8847138d7046d9a09070234464/ducc/singularity/startup_files.go#L65-L148
    """
    runscript_path = root_path / ".singularity.d/runscript"
    logger.info(f"Generating Apptainer runscript at {runscript_path}")

    # Create and open the runscript file
    runscript_path.parent.mkdir(parents=True, exist_ok=True)
    with open(runscript_path, "w") as f:
        # Write the shell shebang
        f.write("#!/bin/sh\n")

        # Write OCI_ENTRYPOINT
        if img_config.get("Entrypoint"):
            entrypoint = args_quoted(img_config["Entrypoint"])
            f.write(f"OCI_ENTRYPOINT='{entrypoint}'\n")
        else:
            f.write("OCI_ENTRYPOINT=''\n")

        # Write OCI_CMD
        if img_config.get("Cmd"):
            cmd = args_quoted(img_config["Cmd"])
            f.write(f"OCI_CMD='{cmd}'\n")
        else:
            f.write("OCI_CMD=''\n")

        # Write the rest of the script
        f.write(
            r"""CMDLINE_ARGS=""
# prepare command line arguments for evaluation
for arg in "$@"; do
CMDLINE_ARGS="${CMDLINE_ARGS} \"$arg\""
done
# ENTRYPOINT only - run entrypoint plus args
if [ -z "$OCI_CMD" ] && [ -n "$OCI_ENTRYPOINT" ]; then
if [ $# -gt 0 ]; then
    SINGULARITY_OCI_RUN="${OCI_ENTRYPOINT} ${CMDLINE_ARGS}"
else
    SINGULARITY_OCI_RUN="${OCI_ENTRYPOINT}"
fi
fi
# CMD only - run CMD or override with args
if [ -n "$OCI_CMD" ] && [ -z "$OCI_ENTRYPOINT" ]; then
if [ $# -gt 0 ]; then
    SINGULARITY_OCI_RUN="${CMDLINE_ARGS}"
else
    SINGULARITY_OCI_RUN="${OCI_CMD}"
fi
fi
# ENTRYPOINT and CMD - run ENTRYPOINT with CMD as default args
# override with user provided args
if [ $# -gt 0 ]; then
SINGULARITY_OCI_RUN="${OCI_ENTRYPOINT} ${CMDLINE_ARGS}"
else
SINGULARITY_OCI_RUN="${OCI_ENTRYPOINT} ${OCI_CMD}"
fi
# Evaluate shell expressions first and set arguments accordingly,
# then execute final command as first container process
eval "set ${SINGULARITY_OCI_RUN}"
exec "$@"
"""
        )

    # Change permissions
    os.chmod(runscript_path, 0o755)


def generate_env(root_path: Path, img_config: dict):
    """
    Generates the environment script for the Apptainer container.

    References:
    - https://github.com/cvmfs/cvmfs/blob/531e6f6bd4b2fa8847138d7046d9a09070234464/ducc/singularity/startup_files.go#L150-L190
    """
    env_path = root_path / ".singularity.d/env/10-docker2singularity.sh"
    logger.info(f"Generating Apptainer environment script at {env_path}")

    # Ensure the directory exists
    env_path.parent.mkdir(parents=True, exist_ok=True)

    # Create and open the environment script file
    with open(env_path, "w") as f:
        # Write the shell shebang
        f.write("#!/bin/sh\n")

        # Write environment variables
        for element in img_config.get("Env", []):
            env_parts = element.split("=", 1)
            if len(env_parts) == 1:
                export_line = f'export {env_parts[0]}="${{{env_parts[0]}:-}}"\n'
            else:
                if env_parts[0] == "PATH":
                    export_line = f"export {env_parts[0]}={escape(env_parts[1])!r}\n"
                else:
                    export_line = f'export {env_parts[0]}="${{{env_parts[0]}:-{escape(env_parts[1])!r}}}"\n'

            f.write(export_line)

        # Sync file to disk
        f.flush()
        os.fsync(f.fileno())

    # Set executable permissions
    os.chmod(env_path, 0o755)


@app.command()
def unpack(output_dir: Path):
    output_dir.mkdir(parents=True)

    input_file = sys.stdin.buffer

    with tempfile.TemporaryDirectory() as temp_dir:
        logger.info(f"Extracting tar file to {temp_dir=}")
        with tarfile.open(fileobj=input_file, mode="r|*") as tar:
            tar.extractall(temp_dir)

        manifest_path = Path(temp_dir) / "manifest.json"
        logger.info(f"Reading manifest from {manifest_path=}")

        manifests = json.loads(manifest_path.read_text())
        if len(manifests) != 1:
            raise Exception(f"Expected exactly one manifest, got {len(manifests)}")

        manifest = manifests[0]
        logger.debug(json.dumps(manifest, indent=2))

        config_path = Path(temp_dir) / manifest["Config"]
        logger.info(f"Reading config from {config_path=}")

        config = json.loads(config_path.read_text())
        logger.debug(json.dumps(config, indent=2))

        extracted_root = output_dir

        for layer in manifest["Layers"]:
            layer_path = Path(temp_dir) / layer
            logger.info(f"Extracting {layer_path=}")

            with tarfile.open(layer_path) as tar:
                for member in tar:
                    basename = os.path.basename(member.name)

                    if basename.startswith(".wh."):
                        # This is a whiteout file, used to indicate that a file is removed
                        orig_file_path = Path(member.name).with_name(
                            basename.removeprefix(".wh.")
                        )
                        logger.debug(f"Removing {orig_file_path} from {extracted_root}")
                        (extracted_root / orig_file_path).unlink()
                    else:
                        logger.debug(f"Extracting {member.name} to {extracted_root}")
                        tar.extract(member, extracted_root)

        logger.info(f"Done extracting layers to {extracted_root}")

        generate_runscript(extracted_root, config["config"])
        generate_env(extracted_root, config["config"])

        logger.info(f"Succesfully unpacked image to {extracted_root}")
