import os
import tarfile
import typing
from pathlib import Path

from watcloud_utils.logging import logger


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


class StreamProxy:
    """
    A stream wrapper to detect compression type.

    Derived from https://github.com/python/cpython/blob/2cf396c368a188e9142843e566ce6d8e6eb08999/Lib/tarfile.py#L574-L598
    """

    def __init__(self, fileobj):
        self.fileobj = fileobj
        self.buf = self.fileobj.read(tarfile.BLOCKSIZE)

    def read(self, size):
        self.read = self.fileobj.read
        return self.buf

    def getcomptype(self):
        if self.buf.startswith(b"\x1f\x8b\x08"):
            return "gz"
        elif self.buf[0:3] == b"BZh" and self.buf[4:10] == b"1AY&SY":
            return "bz2"
        elif self.buf.startswith((b"\x5d\x00\x00\x80", b"\xfd7zXZ")):
            return "xz"
        elif self.buf.startswith(b"\x28\xb5\x2f\xfd"):
            return "zst"
        else:
            return "tar"

    def supports_streaming(self):
        comptype = self.getcomptype()
        return comptype not in ("zst",)

    def close(self):
        self.fileobj.close()


class MyTarFile(tarfile.TarFile):
    """
    A custom TarFile class that supports more compression types.

    Derived from:
    - https://github.com/python/cpython/issues/81276#issuecomment-1966037544
    """

    OPEN_METH = {"zst": "zstopen"} | tarfile.TarFile.OPEN_METH

    @classmethod
    def zstopen(
        cls,
        name: str ,
        mode: typing.Literal["r", "w", "x"] = "r",
        fileobj: typing.Optional[typing.BinaryIO] = None,
    ) -> tarfile.TarFile:
        if mode not in ("r", "w", "x"):
            raise NotImplementedError(f"mode `{mode}' not implemented for zst")
        try:
            import zstandard
        except ImportError:
            raise tarfile.CompressionError("zstandard module not available")
        if mode == "r":
            zfobj = zstandard.open(fileobj or name, "rb")
        else:
            zfobj = zstandard.open(
                fileobj or name,
                mode + "b",
                cctx=zstandard.ZstdCompressor(write_checksum=True, threads=-1),
            )
        try:
            print(f"calling taropen with {name=}, {mode=}, {zfobj=}")
            tarobj = cls.taropen(name, mode, zfobj)
        except (OSError, EOFError, zstandard.ZstdError) as exc:
            zfobj.close()
            if mode == "r":
                raise tarfile.ReadError("not a zst file") from exc
            raise
        except:
            zfobj.close()
            raise
        # Setting the _extfileobj attribute is important to signal a need to
        # close this object and thus flush the compressed stream.
        # Unfortunately, tarfile.pyi doesn't know about it.
        tarobj._extfileobj = False  # type: ignore
        return tarobj
