help:
	@grep -Eh '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}' | uniq

INDEX_URL ?= https://pypi.python.org/simple
INDEX_HOSTNAME ?= pypi.python.org

export NETRC ?= $(HOME)/.netrc

export PYTHONPATH=$(PWD)/src

MODULE := purjo
APP := pur

# Check if 'devenv' exists
ifeq (, $(shell command -v devenv))
DEVENV := nix run nixpkgs/nixos-25.05\#devenv --
else
DEVENV := devenv
endif
DEVENV_OPTIONS ?= --nix-option extra-sandbox-paths $(NETRC)

develop: devenv.local.nix ## Launch opinionated IDE
	devenv shell --profile devcontainer -- code .

devenv.local.nix:
	cp devenv.local.nix.example devenv.local.nix

build:  ## Build application
	$(DEVENV) $(DEVENV_OPTIONS) build outputs.python.app

build-docs: ## Build the Sphinx documentation site
	sphinx-build docs docs/_build/html

watch-docs: ## Serve the Sphinx documentation site locally
	sphinx-autobuild docs docs/_build/html

env:  ## Build and link the Python virtual environment
	ln -s $(shell $(DEVENV) $(DEVENV_OPTIONS) build outputs.python.virtualenv) env

check:  ## Run static analysis checks
	black --check src tests
	isort -c src tests
	flake8 src
	MYPYPATH=$(PWD)/stubs mypy --show-error-codes --strict src tests
	python scripts/check-links.py

clean:  ## Remove build artifacts and temporary files
	$(DEVENV) $(DEVENV_OPTIONS) gc
	$(RM) -r env htmlcov .devenv

devenv-up:  ## Start background services
	$(DEVENV) $(DEVENV_OPTIONS) processes up -d

devenv-attach:  ## Attach to background services monitor
	$(DEVENV) $(DEVENV_OPTIONS) shell -- process-compose attach

devenv-down:  ## Stop background services
	$(DEVENV) $(DEVENV_OPTIONS) processes down

devenv-test: ## Run all test and checks with background services
	$(DEVENV) $(DEVENV_OPTIONS) test

format:  ## Format the codebase
	treefmt

shell:  ## Start an interactive development shell
	@$(DEVENV) $(DEVENV_OPTIONS) shell

show:  ## Show build environment information
	@$(DEVENV) $(DEVENV_OPTIONS) info

test: check test-pytest  ## Run all tests and checks

test-coverage: htmlcov  ## Generate HTML coverage reports

test-pytest:  ## Run unit tests with pytest
	pytest --cov=$(MODULE) tests

watch: .env  ## Start the application in watch mode
	$(APP) -- --reload

watch-mypy:  ## Continuously run mypy for type checks
	find src tests -name "*.py"|MYPYPATH=$(PWD)/stubs entr mypy --show-error-codes --strict src tests

watch-pytest:  ## Continuously run pytest
	find src tests -name "*.py"|entr pytest tests

watch-tests:  ## Continuously run all tests
	  $(MAKE) -j watch-mypy watch-pytest

###

.coverage: test

htmlcov: .coverage
	coverage html

define _env_script
cat << EOF > .env
ENGINE_REST_BASE_URL=http://localhost:8080/engine-rest
ENGINE_REST_AUTHORIZATION=Basic ZGVtbzpkZW1v
EOF
endef
export env_script = $(value _env_script)
.env: ; @ eval "$$env_script"

devenv-%:  ## Run command in $(DEVENV) $(DEVENV_OPTIONS) shell
	$(DEVENV) $(DEVENV_OPTIONS) shell -- $(MAKE) $*

nix-%:  ## Run command in $(DEVENV) $(DEVENV_OPTIONS) shell
	$(DEVENV) $(DEVENV_OPTIONS) shell -- $(MAKE) $*

FORCE:

include release-container.mk
