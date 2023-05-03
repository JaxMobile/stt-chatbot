DOCKER_USERNAME ?= narutosimaha
APPLICATION_NAME ?= lec-chatbot
 
build:
	docker build --tag ${DOCKER_USERNAME}/${APPLICATION_NAME} .

run:
	docker compose up -force-recreate -d