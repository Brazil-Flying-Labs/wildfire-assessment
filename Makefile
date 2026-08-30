THIS_FILE := $(lastword $(MAKEFILE_LIST))

# Define standard colors
ifneq (,$(findstring xterm,${TERM}))
	RED := $(shell tput -Txterm setaf 1)
	GREEN := $(shell tput -Txterm setaf 2)
	BLUE := $(shell tput -Txterm setaf 6)
	ORANGE := $(shell tput -Txterm setaf 3)
	RESET := $(shell tput -Txterm sgr0)
else
	RED := ""
	GREEN := ""
	BLUE := ""
	ORANGE := ""
	RESET := ""
endif

COMPOSE_DEV := docker compose
COMPOSE_PROXY := docker compose -f compose.yml -f compose.override.yml -f compose.npm.yml --profile proxy

# Commands
.PHONY: help up up_proxy down restart logs ps build test test_ui shell clean

help: ## Show this help message
	@echo "\n\n${BLUE}############################################### Wildfire Makefile Help ###################################################################${RESET}"
	@grep -E '^[a-zA-Z_]+:.*?## .*$$' $(THIS_FILE) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-45s\033[0m %s\n", $$1, $$2}'
	@echo "${BLUE}########################################################################################################################################${RESET}"

up: ## Start the full stack (dev, direct ports)
	$(COMPOSE_DEV) up -d

up_proxy: ## Start the stack with the local Nginx Proxy Manager
	$(COMPOSE_PROXY) up -d

down: ## Stop all containers of this project
	$(COMPOSE_DEV) down

restart: ## Restart all containers of this project
	$(COMPOSE_DEV) restart

logs: ## Follow the logs of all containers
	$(COMPOSE_DEV) logs -f

ps: ## List the containers of this project
	$(COMPOSE_DEV) ps

build: ## Build the api and ui images
	$(COMPOSE_DEV) build

test: ## Run backend tests inside running containers (SQLite in-memory, no Redis)
	$(COMPOSE_DEV) exec api bash -lc "cd /api && DJANGO_SETTINGS_MODULE=api.test_settings coverage run --source=wildfire_assessment manage.py test && DJANGO_SETTINGS_MODULE=api.test_settings coverage report && DJANGO_SETTINGS_MODULE=api.test_settings coverage html"

test_ui: ## Run frontend tests inside the running ui container
	$(COMPOSE_DEV) exec ui npm test -- --watchAll=false --ci

shell: ## Open a Django shell inside the api container
	$(COMPOSE_DEV) exec api python manage.py shell

clean: ## Stop and remove containers, networks and volumes of this project
	$(COMPOSE_DEV) down -v

.SILENT:
