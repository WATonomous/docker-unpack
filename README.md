# docker-unpack

Unpack a docker image into a directory. This is useful for using Docker images with [Apptainer](https://apptainer.org/) and [CVMFS](https://cvmfs.readthedocs.io/en/stable/).

## Getting started

Install the package with pip:

```sh
pip install git+https://github.com/WATonomous/docker-unpack.git
```

Unpack an image:

```sh
docker pull hello-world
docker save hello-world | APP_LOG_LEVEL=DEBUG docker-unpack unpack - /tmp/hello-world
```

Start a container using the unpacked image:
```sh
apptainer run /tmp/hello-world /hello
```

## Development

```sh
pdm install
pdm run docker-unpack --help
```

## Notes

This tool is similar to [cvmfs-ducc](https://github.com/cvmfs/cvmfs/tree/531e6f6bd4b2fa8847138d7046d9a09070234464/ducc). The main difference is that cvmfs-ducc is designed to be featureful and compatible with various tools (podman, docker thin image, etc.), whereas docker-unpack is designed to be simple and fast, and only supports unpacking Docker images into flat (not layered) directories.
