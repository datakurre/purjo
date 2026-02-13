.DEFAULT_GOAL := help

export UV_NO_SYNC=0

# Configuration
DEPLOY_FILES = hello.bpmn
ROBOT_TEST = test_hello.robot

.PHONY: help dist test deploy serve run

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

dist: test ## Build distribution package
	pur wrap

test: ## Run Robot Framework tests
	uv run --group dev robot $(ROBOT_TEST)

deploy: ## Deploy files (BPMN, DMN, forms) to engine
	pur deploy $(DEPLOY_FILES)

serve: deploy ## Start external task worker
	pur serve .

run: ## Deploy and start worker
	pur run $(DEPLOY_FILES)
	pur serve .