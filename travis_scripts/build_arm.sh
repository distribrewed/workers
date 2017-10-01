#!/bin/bash

set -e

sed 's/\/core:x64/\/core:arm/g' Dockerfile > Dockerfile.arm
docker run --rm --privileged multiarch/qemu-user-static:register --reset
docker build -t distribrewed/workers:arm -f Dockerfile.arm .

if [[ ${TRAVIS} == "true" ]]; then
    docker login -u="$DOCKER_USER" -p="$DOCKER_PASS"
    docker push distribrewed/workers:arm
fi