# Integration test: whiteout

```
docker build -t whiteout .
docker save whiteout | APP_LOG_LEVEL=DEBUG pdm run docker-unpack unpack /tmp/whiteout
ls -l /tmp/whiteout # files `/1` and `/3` should be available. File `/2` should not exist.
```