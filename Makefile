ROOT_DIR := $(shell pwd)

DOCKER_BASE_IMAGE_TAG := distribrewed/core:x64
DOCKER_IMAGE_TAG := distribrewed/workers:x64

DOCKER_STACK_RABBITMQ_CONTAINER_NAME ?= distribrewedstack_rabbitmq_1
DOCKER_STACK_RABBITMQ_LINK ?= --link=${DOCKER_STACK_RABBITMQ_CONTAINER_NAME}:rabbitmq

docker-pull-base:
	docker pull ${DOCKER_BASE_IMAGE_TAG}

docker-build: docker-pull-base
	docker build ${BUILD_FLAGS} -t ${DOCKER_IMAGE_TAG} .

docker-run-telegram-worker: docker-build
	docker run -t -e WORKER_PLUGIN_CLASS=TelegramWorker -e WORKER_NAME=telegram ${DOCKER_STACK_RABBITMQ_LINK} ${DOCKER_IMAGE_TAG}