#!/bin/sh

set -e

docker build -t distribrewed/workers:x64 -f Dockerfile .
docker login -u="$DOCKER_USER" -p="$DOCKER_PASS"
docker push distribrewed/workers:x64