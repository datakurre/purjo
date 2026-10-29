# Required inputs:
CONTAINER_PATH ?= datakurre/purjo/purjo
CONTAINER_DOMAIN ?= ghcr.io
CONTAINER_NAME = $(CONTAINER_DOMAIN)/$(CONTAINER_PATH)

ifdef CI_PIPELINE_ID
CONTAINER_TAG = $(if $(CI_COMMIT_TAG),$(CI_COMMIT_TAG),$(CI_PIPELINE_ID)-$(CI_COMMIT_SHORT_SHA))
else
CONTAINER_TAG = $(shell git describe --dirty --tags)
endif

CONTAINER_RT_BUILD_NAME := $(CI_PROJECT_ID)
CONTAINER_RT_BUILD_NUMBER := $(CI_PIPELINE_ID)
CONTAINER_RT_IMAGE = $(CONTAINER_DOMAIN)/$(CONTAINER_PATH)
CONTAINER_RT_REPO_STAGING ?=
CONTAINER_RT_REPO_PROMOTED ?=

# Optional: fill in some meta for local builds
CI_COMMIT_TAG ?= $(shell git describe --exact-match --tags 2>/dev/null)
CI_COMMIT_SHA ?= $(shell git rev-parse HEAD)

# Bash is needed for pipefail
SHELL := bash
JF_CLI ?= jf
SKOPEO ?= skopeo
CONTAINER_PUBLISHER ?= skopeo

container-show:  ## Show container details
	# CONTAINER_NAME = $(CONTAINER_NAME)
	# CONTAINER_TAG = $(CONTAINER_TAG)
	#
	# CONTAINER_RT_BUILD_NAME = $(CONTAINER_RT_BUILD_NAME)
	# CONTAINER_RT_BUILD_NUMBER = $(CONTAINER_RT_BUILD_NUMBER)
	#
	# CI_COMMIT_REF_NAME = $(CI_COMMIT_REF_NAME)
	# CI_COMMIT_TAG = $(CI_COMMIT_TAG)

container-show-image:
	@echo $(CONTAINER_NAME):$(CONTAINER_TAG)

.PHONY: .FORCE
Labels.json: .FORCE
	@echo '{' > Labels.json
	@echo '  "fi.jyu.vasara.rev": "$(CI_COMMIT_SHA)",' >> Labels.json
	@echo '  "fi.jyu.vasara.ref_name": "$(CI_COMMIT_REF_NAME)",' >> Labels.json
	@echo '  "fi.jyu.vasara.tag": "$(CI_COMMIT_TAG)",' >> Labels.json
	@echo '  "fi.jyu.vasara.url": "$(CI_PROJECT_URL)",' >> Labels.json
	@echo '  "fi.jyu.vasara.ci_job_id": "$(CI_JOB_ID)",' >> Labels.json
	@echo '  "fi.jyu.vasara.ci_pipeline_id": "$(CI_PIPELINE_ID)"' >> Labels.json
	@echo '}' >> Labels.json

container-dist: Labels.json  ## Build container image
	@echo "# Build the image"
	nix --extra-experimental-features 'nix-command flakes' build .#image
	git restore Labels.json

container-clean:
	rm -fr result-image.json result-image.digest result-image-details.txt image-archive.*

ifeq ($(CONTAINER_PUBLISHER),jf)
container-publish: container-required-vars container-jfrog-required-vars container-dist
	# Stage the Nix image stream so an early Skopeo exit does not break the producer pipe.
	@archive=$$(mktemp image-archive.XXXXXX) && trap 'rm -f "$$archive"' EXIT && ./result > "$$archive" && $(SKOPEO) copy --dest-registry-token "$$ARTIFACTORY_ACCESS_TOKEN" --digestfile result-image.digest docker-archive:"$$archive" docker://$(CONTAINER_RT_IMAGE):$(CONTAINER_TAG)
	# Copy the versioned image to the mutable latest tag in Artifactory.
	@$(SKOPEO) copy --src-registry-token "$$ARTIFACTORY_ACCESS_TOKEN" --dest-registry-token "$$ARTIFACTORY_ACCESS_TOKEN" docker://$(CONTAINER_RT_IMAGE):$(CONTAINER_TAG) docker://$(CONTAINER_RT_IMAGE):latest
	# JFrog expects the image tag and registry manifest digest in this file.
	@digest=$$(cat result-image.digest) && test -n "$$digest" && printf '%s@%s\n' "$(CONTAINER_RT_IMAGE):$(CONTAINER_TAG)" "$$digest" > result-image-details.txt
	# Associate the current Git revision and CI build number with build-info.
	$(JF_CLI) rt build-add-git \
		$(CONTAINER_RT_BUILD_NAME) \
		$(CONTAINER_RT_BUILD_NUMBER)
	# Record only the versioned image; latest remains a rolling tag.
	@$(JF_CLI) rt build-docker-create $(CONTAINER_RT_REPO_STAGING) \
	--image-file=result-image-details.txt \
	--build-name="$(CONTAINER_RT_BUILD_NAME)" \
	--build-number="$(CONTAINER_RT_BUILD_NUMBER)" \
	$(JF_AUTH_OPTS)
	# Publish the collected Git and image metadata to Artifactory.
	@$(JF_CLI) rt build-publish \
		$(JF_AUTH_OPTS) \
		$(CONTAINER_RT_BUILD_NAME) \
		$(CONTAINER_RT_BUILD_NUMBER)
else
container-publish: container-dist
	@archive=$$(mktemp image-archive.XXXXXX) && trap 'rm -f "$$archive"' EXIT && ./result > "$$archive" && $(SKOPEO) copy docker-archive:"$$archive" docker://$(CONTAINER_NAME):$(CONTAINER_TAG)
	$(SKOPEO) copy docker://$(CONTAINER_NAME):$(CONTAINER_TAG) docker://$(CONTAINER_NAME):latest
endif

container-promote: container-required-vars
	$(JF_CLI) rt build-promote \
		$(JF_AUTH_OPTS) \
		$(CONTAINER_RT_BUILD_NAME) \
		$(CONTAINER_RT_BUILD_NUMBER) \
		$(CONTAINER_RT_REPO_PROMOTED)

container-required-vars:
	@test -n "$(CONTAINER_RT_BUILD_NAME)" || { echo "Error: CONTAINER_RT_BUILD_NAME is not set"; exit 1; }
	@test -n "$(CONTAINER_RT_BUILD_NUMBER)" || { echo "Error: CONTAINER_RT_BUILD_NUMBER is not set"; exit 1; }

container-jfrog-required-vars:
	@test -n "$$ARTIFACTORY_URL" || { echo "Error: ARTIFACTORY_URL is not set"; exit 1; }
	@test -n "$$ARTIFACTORY_ACCESS_TOKEN" || { echo "Error: ARTIFACTORY_ACCESS_TOKEN is not set"; exit 1; }
	@test -n "$(CONTAINER_RT_REPO_STAGING)" || { echo "Error: CONTAINER_RT_REPO_STAGING is not set"; exit 1; }
