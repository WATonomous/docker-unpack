#!/bin/bash

# Integration test: compression
# This test aims to verify that the unpacker can handle compressed images

set -o errexit -o nounset -o pipefail

trap 'echo "Error on line $LINENO: $BASH_COMMAND"; exit 1' ERR

docker pull alpine

# MARK: Compressing the whole package
for compression in zstd gzip bzip2 xz; do
  echo "Testing package compression with $compression"
  __tmpdir=$(mktemp -d)
  docker save alpine | $compression > "$__tmpdir/image.tar"
  APP_LOG_LEVEL=INFO pdm run docker-unpack unpack "$__tmpdir/image.tar" "$__tmpdir/unpacked"
  test -d "$__tmpdir/unpacked/etc"
  rm -rf "$__tmpdir"
done

# MARK: Compressing the layers
docker buildx create --name compression-test --driver docker-container --use

for compression in zstd gzip estargz; do
  echo "Testing layer compression with $compression"

    __tmpdir=$(mktemp -d)
    docker buildx build --output type=docker,compression=$compression,force-compression=true,dest=- . > "$__tmpdir/image.tar"
    test $(stat -c %s "$__tmpdir/image.tar") -lt $((10 * 1024 * 1024)) # check that the resulting image is sufficiently small

    APP_LOG_LEVEL=INFO pdm run docker-unpack unpack "$__tmpdir/image.tar" "$__tmpdir/unpacked"
    test -f "$__tmpdir/unpacked/largefile"
    test $(stat -c %s "$__tmpdir/unpacked/largefile") -eq $((128 * 1024 * 1024)) # check that the unpacked file is the correct size
    rm -rf "$__tmpdir"
done

docker buildx rm compression-test

echo "PASS"
