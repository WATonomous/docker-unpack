#!/bin/bash

# Integration test: whiteout
# This test aims to verify that whiteout files (deletions) are correctly handled by the unpacker

set -o errexit -o nounset -o pipefail

trap 'echo "Error on line $LINENO: $BASH_COMMAND"; exit 1' ERR

docker build --tag whiteout .

__tmpdir=$(mktemp -d)
docker save whiteout | APP_LOG_LEVEL=DEBUG pdm run docker-unpack unpack - "$__tmpdir"

test -f "$__tmpdir/1"
test ! -f "$__tmpdir/2"
test -f "$__tmpdir/3"
test "hello" = "$(cat "$__tmpdir/3")"

test -d "$__tmpdir/dir/4"
test ! -d "$__tmpdir/dir/5"
test -d "$__tmpdir/dir/6"
test -f "$__tmpdir/dir/6/somefile"

rm -rf "$__tmpdir"
docker rmi whiteout

echo "PASS"
