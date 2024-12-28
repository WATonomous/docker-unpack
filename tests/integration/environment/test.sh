#!/bin/bash

# Integration test: compression
# This test aims to verify that the unpacker can handle compressed images

set -o errexit -o nounset -o pipefail

trap 'echo "Error on line $LINENO: $BASH_COMMAND"; exit 1' ERR

docker pull alpine:3.19

__tmpdir=$(mktemp -d)
docker save alpine:3.19 | APP_LOG_LEVEL=INFO pdm run docker-unpack unpack - "$__tmpdir"

# Test whether the environment variables are correctly set
apptainer exec --compat --env MYTEST=someteststring "$__tmpdir" env | grep MYTEST

rm -rf "$__tmpdir"
echo "PASS"
