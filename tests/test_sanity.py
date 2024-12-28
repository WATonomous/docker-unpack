import docker_unpack


def test_version():
    assert (
        hasattr(docker_unpack, "__version__") and docker_unpack.__version__ is not None
    )
