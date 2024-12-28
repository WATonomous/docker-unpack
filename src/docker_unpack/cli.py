import json
import os
import tarfile
import tempfile
from pathlib import Path

from watcloud_utils.logging import logger, set_up_logging

set_up_logging()

from watcloud_utils.typer import app, typer

from ._version import __version__
from .utils import generate_env, generate_runscript


@app.command()
def version():
    """
    Print the version of the tool.
    """
    print(__version__)

@app.command()
def unpack(input_file: typer.FileBinaryRead, output_dir: Path):
    if output_dir.exists() and any(output_dir.iterdir()):
        raise Exception(
            f"Output directory {output_dir} already exists and is not empty!"
        )

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
                        if (extracted_root / orig_file_path).is_dir():
                            (extracted_root / orig_file_path).rmdir()
                        else:
                            (extracted_root / orig_file_path).unlink()
                    else:
                        logger.debug(f"Extracting {member.name} to {extracted_root}")
                        tar.extract(member, extracted_root)

        logger.info(f"Done extracting layers to {extracted_root}")

        generate_runscript(extracted_root, config["config"])
        generate_env(extracted_root, config["config"])

        logger.info(f"Succesfully unpacked image to {extracted_root}")
