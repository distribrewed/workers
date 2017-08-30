ROOT_DIR := $(shell pwd)

DOCKER_IMAGE_TAG := distribrewed/workers

DOCKER_STACK_RABBITMQ_CONTAINER_NAME ?= distribrewedstack_rabbitmq_1
DOCKER_STACK_RABBITMQ_LINK ?= --link=${DOCKER_STACK_RABBITMQ_CONTAINER_NAME}:rabbitmq

docker-build:
	docker build ${BUILD_FLAGS} -t ${DOCKER_IMAGE_TAG} .

docker-run-telegram-worker: docker-build
	docker run -t -e WORKER_PLUGIN_CLASS=TelegramWorker -e WORKER_NAME=telegram ${DOCKER_STACK_RABBITMQ_LINK} ${DOCKER_IMAGE_TAG}