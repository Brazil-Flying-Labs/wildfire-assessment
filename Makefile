THIS_FILE := $(lastword $(MAKEFILE_LIST))

MIGRATION_NAME ?= migration name
REVISION_UP ?= head
REVISION_DOWN ?= -1

BRANCH_NAME ?= ''

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

# Commands
.PHONY: help configure_devel up reset test

help: ## Show this help message
	@echo "\n\n${BLUE}############################################### Wildfire Makefile Help ###################################################################${RESET}"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(THIS_FILE) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-45s\033[0m %s\n", $$1, $$2}'
	@echo "${BLUE}########################################################################################################################################${RESET}"


configure_devel:  ## Configure a local development environment
	if [ -d "venv" ]; then \
		rm -rf venv; \
	fi

	docker compose down -v
	docker volume rm courted-core-app_postgres_data 2>/dev/null || true; \
	bash -c "python3 -m venv venv && source venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt && pre-commit install"
	@echo "\n\n📺${ORANGE} Don't forget to activate your virtual environment!${RESET}"
	@echo "⚙️ ${GREEN}Run: source venv/bin/activate${RESET}"
	@echo "⚙️ ${GREEN}Run: ./venv/bin/activate${RESET}\n\n"
	docker compose up -d
	docker compose logs -f

up: ## Start localstack with the services needed for the project
	docker compose up

reset: ## Reconfigure local environment then run the project
	$(MAKE) do_clean_wildfire_docker
	$(MAKE) configure_devel
	$(MAKE) up

test: ## Run backend tests inside running containers (SQLite in-memory, no Redis)
	docker compose exec api bash -lc "cd /api && DJANGO_SETTINGS_MODULE=api.test_settings coverage run --source=wildfire_assessment manage.py test && DJANGO_SETTINGS_MODULE=api.test_settings coverage report && DJANGO_SETTINGS_MODULE=api.test_settings coverage html"

do_clean_wildfire_docker:
	echo "${ORANGE} Forcely stoping all wildfire containers...${RESET}";
	$(MAKE) do_stop;
	echo "${ORANGE} Pruning all wildfire docker system...${RESET}";
	/bin/bash -c 'docker system prune -a -f --filter "label=com.docker.compose.project=wildfire-api" 2>/dev/null || true';
	/bin/bash -c 'docker system prune -a -f --filter "label=com.docker.compose.project=wildfire-db" 2>/dev/null || true';
	echo "${ORANGE} Pruning all wildfire docker images...${RESET}";
	/bin/bash -c 'docker image rm -f $$(docker images -a -q --filter "reference=*wildfire*") 2>/dev/null || true';
	/bin/bash -c 'docker image rm -f $$(docker images -a -q --filter=dangling=true) 2>/dev/null || true';
	/bin/bash -c 'docker rm $$(docker images -a -q --filter "reference=*wildfirewildfire*") 2>/dev/null || true';
	echo "${ORANGE} Pruning all dangling volumes...${RESET}";
	docker volume prune --filter "label!=com.docker.compose.volume";

.SILENT:
do_stop: ## Stop all containers
	docker kill $$(docker ps -q --filter "name=wildfire") 2>/dev/null || true;
