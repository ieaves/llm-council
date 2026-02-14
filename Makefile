SHELL := /bin/bash

REGISTRY ?= ghcr.io
GHCR_OWNER ?= $(shell git remote get-url origin 2>/dev/null | awk -F'[:/]' '{print $$(NF-1)}')
GHCR_REPO ?= $(notdir $(CURDIR))
GHCR_USER ?= $(GHCR_OWNER)
PYPROJECT_PATH ?= pyproject.toml
BACKEND_VERSION ?= $(shell uv version --short)
IMAGE_TAGS ?= latest $(BACKEND_VERSION)
PLATFORMS ?= linux/amd64 linux/arm64
VITE_API_BASE ?= http://localhost:8001
OCI_IMAGE_SOURCE ?= https://github.com/$(GHCR_OWNER)/$(GHCR_REPO)

BACKEND_IMAGE ?= $(REGISTRY)/$(GHCR_OWNER)/$(GHCR_REPO)
FRONTEND_IMAGE ?= $(REGISTRY)/$(GHCR_OWNER)/$(GHCR_REPO)-web

BAKE_PLATFORM_FLAGS := $(foreach platform,$(PLATFORMS),--set backend.platform=$(platform) --set frontend.platform=$(platform))
BAKE_BACKEND_TAG_FLAGS := $(foreach tag,$(IMAGE_TAGS),--set backend.tags=$(BACKEND_IMAGE):$(tag))
BAKE_FRONTEND_TAG_FLAGS := $(foreach tag,$(IMAGE_TAGS),--set frontend.tags=$(FRONTEND_IMAGE):$(tag))
BAKE_SOURCE_LABEL_FLAGS := --set backend.labels.org.opencontainers.image.source=$(OCI_IMAGE_SOURCE) --set frontend.labels.org.opencontainers.image.source=$(OCI_IMAGE_SOURCE)
BAKE_SOURCE_ANNOTATION_FLAGS := --set backend.annotations=org.opencontainers.image.source=$(OCI_IMAGE_SOURCE) --set frontend.annotations=org.opencontainers.image.source=$(OCI_IMAGE_SOURCE)

.PHONY: help check-ghcr-vars check-version check-buildx check-ghcr-login images ghcr-login build push publish

help:
	@echo "Targets:"
	@echo "  make build            Build and push backend + frontend images (buildx, multi-arch)"
	@echo "  make push             Alias for make build"
	@echo "  make publish          Alias for make build"
	@echo "  make ghcr-login       Login to GHCR using GITHUB_TOKEN"
	@echo "  make images           Print resolved image names"
	@echo ""
	@echo "Variables:"
	@echo "  GHCR_OWNER=<owner>    GitHub owner/org (default: inferred from git remote)"
	@echo "  GHCR_REPO=<name>      Image prefix (default: current folder name)"
	@echo "  GHCR_USER=<user>      GitHub username for docker login (default: GHCR_OWNER)"
	@echo "  PLATFORMS=\"...\"      Space-separated platforms (default: linux/amd64 linux/arm64)"
	@echo "  IMAGE_TAGS=\"...\"     Space-separated tags (default: latest + backend version)"
	@echo "  BACKEND_VERSION=<v>   Override backend version tag (default: from pyproject.toml)"
	@echo "  VITE_API_BASE=<url>   Frontend build arg (default: http://localhost:8001)"
	@echo "  OCI_IMAGE_SOURCE=<u>  OCI source label URL (default: https://github.com/<owner>/<repo>)"

check-ghcr-vars:
	@test -n "$(GHCR_OWNER)" || (echo "GHCR_OWNER is empty. Set it explicitly, e.g. GHCR_OWNER=ieaves"; exit 1)
	@test -n "$(GHCR_REPO)" || (echo "GHCR_REPO is empty. Set it explicitly, e.g. GHCR_REPO=llm-council"; exit 1)

check-version:
	@test -n "$(BACKEND_VERSION)" || (echo "Could not detect backend version from $(PYPROJECT_PATH)"; exit 1)

check-buildx:
	@docker buildx version >/dev/null

check-ghcr-login:
	@test -f "$$HOME/.docker/config.json" || (echo "Docker config not found. Run: GITHUB_TOKEN=<token> make ghcr-login GHCR_USER=$(GHCR_USER)"; exit 1)
	@rg -q '"ghcr.io"' "$$HOME/.docker/config.json" || (echo "Not logged in to ghcr.io. Run: GITHUB_TOKEN=<token> make ghcr-login GHCR_USER=$(GHCR_USER)"; exit 1)

images: check-ghcr-vars check-version
	@echo "Backend image:  $(BACKEND_IMAGE)"
	@echo "Frontend image: $(FRONTEND_IMAGE)"
	@echo "Backend version: $(BACKEND_VERSION)"
	@for tag in $(IMAGE_TAGS); do \
		echo "Backend tag:  $(BACKEND_IMAGE):$$tag"; \
		echo "Frontend tag: $(FRONTEND_IMAGE):$$tag"; \
	done

ghcr-login:
	@test -n "$(GITHUB_TOKEN)" || (echo "GITHUB_TOKEN is required (needs write:packages scope)."; exit 1)
	@test -n "$(GHCR_USER)" || (echo "GHCR_USER is required for docker login."; exit 1)
	@echo "$(GITHUB_TOKEN)" | docker login $(REGISTRY) -u "$(GHCR_USER)" --password-stdin

build: check-ghcr-vars check-version check-buildx check-ghcr-login
	docker buildx bake backend frontend \
		$(BAKE_PLATFORM_FLAGS) \
		$(BAKE_BACKEND_TAG_FLAGS) \
		$(BAKE_FRONTEND_TAG_FLAGS) \
		$(BAKE_SOURCE_LABEL_FLAGS) \
		$(BAKE_SOURCE_ANNOTATION_FLAGS) \
		--set frontend.args.VITE_API_BASE=$(VITE_API_BASE) \
		--set backend.args.OCI_IMAGE_SOURCE=$(OCI_IMAGE_SOURCE) \
		--set frontend.args.OCI_IMAGE_SOURCE=$(OCI_IMAGE_SOURCE) \
		--push
