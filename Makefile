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

build:  ## Build application
	$(DEVENV) $(DEVENV_OPTIONS) build outputs.python.app

build-docs: ## Build the Sphinx documentation site
	sphinx-build docs docs/_build/html

watch-docs: ## Serve the Sphinx documentation site locally
	sphinx-autobuild docs docs/_build/html

check:  ## Run static analysis checks
	black --check src tests
	isort -c src tests
	flake8 src tests
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

E2E_WAIT_SECONDS ?= 180
# The engine authenticates one way at a time, so each auth scenario is its own
# devenv profile and its own CI job. Override both of these together:
#   oauth2 (default `shell` profile): ports 8080 8200 8081, -m "e2e and auth_oauth2"
#   basic  (`basic` profile):         ports 8080 8200,      -m "e2e and auth_basic"
E2E_PORTS ?= 8080 8200 8081
E2E_MARKERS ?= e2e

test-e2e:  ## Run e2e tests against live devenv services (see E2E_MARKERS)
	pytest -o addopts="" -m "$(E2E_MARKERS)" tests/e2e

test-e2e-ci:  ## Wait for already-started devenv services, then run e2e (used by CI)
# Waits itself rather than relying on `devenv test`, which does not run
# enterTest until every process reports ready -- and mockoon and
# keycloak-realm-export-all ship no readiness probe, so that wait never
# finishes. Fails loudly on a missing service: require_live_services in
# tests/e2e/conftest.py *skips* the suite when a port is closed, so without
# this a dead service would be a green run.
	@for port in $(E2E_PORTS); do \
	  echo "waiting for localhost:$$port"; \
	  timeout $(E2E_WAIT_SECONDS) bash -c \
	    "until (echo > /dev/tcp/localhost/$$port) 2>/dev/null; do sleep 1; done" \
	    || { echo "ERROR: nothing listening on port $$port after $(E2E_WAIT_SECONDS)s"; exit 1; }; \
	done
	@set -a; . "$$DEVENV_STATE/env_file"; set +a; $(MAKE) test-e2e E2E_MARKERS="$(E2E_MARKERS)"

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
