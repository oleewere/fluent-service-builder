TAG_COMMIT := $(shell git rev-list --abbrev-commit --tags --max-count=1)
TAG := $(shell git describe --abbrev=0 --tags ${TAG_COMMIT} 2>/dev/null || true)
COMMIT := $(shell git rev-parse --short HEAD)
SNAPSHOT_VERSION := 0.1.0-SNAPSHOT
VERSION := $(TAG:v%=%)
ifeq ($(TAG),)
	VERSION := $(SNAPSHOT_VERSION)
endif
ifndef PACKAGE_CONFIG
$(error PACKAGE_CONFIG is undefined)
endif
ifeq ("$(wildcard $(PACKAGE_CONFIG))","")
$(error $(PACKAGE_CONFIG) file does not exist)
endif
PACKAGE_NAME := $(shell grep 'PACKAGE_NAME:' $(PACKAGE_CONFIG) | tr -d '"' | cut -d':' -f2- | sed -e 's/^[[:space:]]*//')
DOCKER_BUILDER_CONTAINER := $(shell grep 'builderDockerImageName:' $(PACKAGE_CONFIG) | tr -d '"' | cut -d':' -f2- | sed -e 's/^[[:space:]]*//')
ifeq ("$(DOCKER_BUILDER_CONTAINER)","")
DOCKER_BUILDER_CONTAINER:="oleewere/fluent-service-builder:latest"
endif

RELEASE_COMMAND:= $(shell grep 'RELEASE_COMMAND:' $(PACKAGE_CONFIG) | tr -d '"' | cut -d':' -f2- | sed -e 's/^[[:space:]]*//')
RELEASE_COMMAND_PARAMETERS:= $(shell grep 'RELEASE_COMMAND_PARAMETERS:' $(PACKAGE_CONFIG) | tr -d '"' | cut -d':' -f2- | sed -e 's/^[[:space:]]*//' | sed -e 's/$${VERSION}/${VERSION}/')

VENV_NAME?=env1
VENV_ACTIVATE=. $(VENV_NAME)/bin/activate
PYTHON=${VENV_NAME}/bin/python3

install-rpm: print-build-params clean install-deps build copy-package template create-pre-package package-rpm

clean:
	rm -rf build

print-build-params:
	@echo "--------- INPUT PARAMETERS ---------"
	@echo "PACKAGE_NAME: $(PACKAGE_NAME)"
	@echo "VERSION: $(VERSION)"
	@echo "DOCKER_BUILDER_CONTAINER: $(DOCKER_BUILDER_CONTAINER)"
	@echo "--------- INPUT PARAMETERS ---------"

build: venv
	${PYTHON} packager/cli.py build -c $(PACKAGE_CONFIG) --override-version $(VERSION) --profile databus --profile aws --profile abfs

template: venv
	${PYTHON} packager/cli.py template -c $(PACKAGE_CONFIG) --override-version $(VERSION)

copy-package:
	docker run --rm -it --entrypoint "cp" -v $$(pwd)/build:/build $(DOCKER_BUILDER_CONTAINER) -r /$(PACKAGE_NAME).tar.gz /build

create-python-env:
	pip3 install virtualenv
	python3 -m venv env1

venv: create-python-env $(VENV_NAME)/bin/activate

install-deps: venv
	${PYTHON} setup.py install

create-pre-package:
	rm -rf build/package
	mkdir -p build/package
	tar -xf build/$(PACKAGE_NAME).tar.gz -C build/package
	cp -r build/generated/** build/package

package-rpm: venv
	${PYTHON} packager/cli.py package -c $(PACKAGE_CONFIG) --override-version $(VERSION)

test-rpm-container:
	docker build -t oleewere/logging-agent:latest -f docker/test/rpm/Dockerfile .
	docker run --rm --entrypoint bash -it oleewere/logging-agent:latest

release: install-rpm
	${RELEASE_COMMAND} ${RELEASE_COMMAND_PARAMETERS}
	
