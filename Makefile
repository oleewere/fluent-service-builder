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
PYTHON=${VENV_NAME}/bin/python
PIP=pip3

install-rpm: print-build-params clean install-deps build template create-pre-package package-rpm

clean:
	rm -rf build

print-build-params:
	@echo "--------- INPUT PARAMETERS ---------"
	@echo "PACKAGE_NAME: $(PACKAGE_NAME)"
	@echo "VERSION: $(VERSION)"
	@echo "DOCKER_BUILDER_CONTAINER: $(DOCKER_BUILDER_CONTAINER)"
	@echo "COMMIT: $(COMMIT)"
	@echo "TAG: $(TAG)"
	@echo "TAG COMMIT: $(TAG_COMMIT)"
	@echo "--------- INPUT PARAMETERS ---------"

build: venv
	${PYTHON} packager/cli.py fluentd build -c $(PACKAGE_CONFIG) --override-version $(VERSION) --profile databus --profile aws --profile abfs --profile google

build-deb: venv
	${PYTHON} packager/cli.py fluentd build -c $(PACKAGE_CONFIG) --override-version $(VERSION) --profile databus --profile aws --profile abfs --profile google --os-type "debian"

template: venv
	${PYTHON} packager/cli.py fluentd template -c $(PACKAGE_CONFIG) --override-version $(VERSION)

template-deb: venv
	${PYTHON} packager/cli.py fluentd template -c $(PACKAGE_CONFIG) --override-version $(VERSION) --os-type "debian"

package-rpm: venv
	${PYTHON} packager/cli.py fluentd package -c $(PACKAGE_CONFIG) --override-version $(VERSION)

package-deb: venv
	${PYTHON} packager/cli.py fluentd package -c $(PACKAGE_CONFIG) --override-version $(VERSION) --os-type "debian"

package-bit-rpm: venv
	${PYTHON} packager/cli.py fluent-bit package -c $(PACKAGE_CONFIG)

create-python-env:
	${PIP} install virtualenv
	python3 --version
	python3 -m venv env1

docker-in-docker:
	docker build -t cloudera/python3.7 .
	docker run --rm --privileged -e REAL_HOST_VOLUME=${PWD} -v ${PWD}:/app -v /var/run/docker.sock:/var/run/docker.sock cloudera/python3.7 make install-rpm PACKAGE_CONFIG=/app/config/cdp-logging-agent.yaml
	docker rmi cloudera/python3.7

venv: create-python-env $(VENV_NAME)/bin/activate

install-deps: venv
	${PYTHON} setup.py install

create-pre-package:
	rm -rf build/package
	mkdir -p build/package
	tar -xf build/$(PACKAGE_NAME).tar.gz -C build/package
	cp -r build/generated/** build/package

tag-and-branch:
	git checkout -b "release/$$(cat VERSION)" $(RELEASE_COMMIT)
	git tag "v$$(cat VERSION)" $(RELEASE_COMMIT)
	git push origin "v$$(cat VERSION)"
	git push -u origin "release/$$(cat VERSION)"

test-rpm-container:
	docker build -t oleewere/logging-agent:latest -f docker/fluentd/test/rpm/Dockerfile .
	docker run --rm --entrypoint bash -it oleewere/logging-agent:latest

test-rpm-bit-container:
	docker build -t oleewere/logging-agent-bit:latest -f docker/fluent-bit/test/rpm/Dockerfile .
	docker run --rm --entrypoint bash -it oleewere/logging-agent-bit:latest

test-deb-container:
	docker build -t oleewere/logging-agent-deb:latest -f docker/fluentd/test/deb/Dockerfile .
	docker run --rm --entrypoint bash -it oleewere/logging-agent-deb:latest

release: docker-in-docker
	${RELEASE_COMMAND} ${RELEASE_COMMAND_PARAMETERS}