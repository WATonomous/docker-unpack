# docker-unpack

Unpack a docker image into a directory. This is useful for using Docker images with [Apptainer](https://apptainer.org/) and [CVMFS](https://cvmfs.readthedocs.io/en/stable/).

## Getting started

Install the apckage with pip:

```sh
pip install git+https://github.com/WATonomous/docker-unpack.git
```

Unpack an image:

```sh
docker pull hello-world
docker save hello-world | docker-unpack --output-dir ./hello-world
apptainer run ./hello-world /hello
```

## Development

```sh
pdm run docker-unpack --help
```