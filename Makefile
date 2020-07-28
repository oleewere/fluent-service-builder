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
RPM_NAME := $(shell echo ${PACKAGE_NAME} | tr '-' '_')
PACKAGE_DESCRIPTION := $(shell grep 'PACKAGE_DESCRIPTION:' $(PACKAGE_CONFIG) | tr -d '"' | cut -d':' -f2- | sed -e 's/^[[:space:]]*//')
COMPANY := $(shell grep 'COMPANY:' $(PACKAGE_CONFIG) | tr -d '"' | cut -d':' -f2- | sed -e 's/^[[:space:]]*//')
WEBPAGE := $(shell grep 'WEBPAGE:' $(PACKAGE_CONFIG) | tr -d '"' | cut -d':' -f2- | sed -e 's/^[[:space:]]*//')

DOCKER_BUILDER_CONTAINER := $(shell grep 'builderDockerImageName:' $(PACKAGE_CONFIG) | tr -d '"' | cut -d':' -f2- | sed -e 's/^[[:space:]]*//')
DOCKER_FPM_CONTAINER := $(shell grep 'fpmDockerImageName:' $(PACKAGE_CONFIG) | tr -d '"' | cut -d':' -f2- | sed -e 's/^[[:space:]]*//')
ifeq ("$(DOCKER_BUILDER_CONTAINER)","")
DOCKER_BUILDER_CONTAINER:="oleewere/fluent-service-builder:latest"
endif
ifeq ("$(DOCKER_FPM_CONTAINER)","")
DOCKER_FPM_CONTAINER:="oleewere/fpm:centos8"
endif

RELEASE_COMMAND:= $(shell grep 'RELEASE_COMMAND:' $(PACKAGE_CONFIG) | tr -d '"' | cut -d':' -f2- | sed -e 's/^[[:space:]]*//')
RELEASE_COMMAND_PARAMETERS:= $(shell grep 'RELEASE_COMMAND_PARAMETERS:' $(PACKAGE_CONFIG) | tr -d '"' | cut -d':' -f2- | sed -e 's/^[[:space:]]*//' | sed -e 's/$${VERSION}/${VERSION}/')

VENV_NAME?=env1
VENV_ACTIVATE=. $(VENV_NAME)/bin/activate
PYTHON=${VENV_NAME}/bin/python3

install-rpm: print-build-params clean install-deps package copy-package template create-pre-package rpm

clean:
	rm -rf build

print-build-params:
	@echo "--------- INPUT PARAMETERS ---------"
	@echo "PACKAGE_NAME: $(PACKAGE_NAME)"
	@echo "PACKAGE_DESCRIPTION: $(PACKAGE_DESCRIPTION)"
	@echo "VERSION: $(VERSION)"
	@echo "COMPANY: $(COMPANY)"
	@echo "WEBPAGE: $(WEBPAGE)"
	@echo "DOCKER_BUILDER_CONTAINER: $(DOCKER_BUILDER_CONTAINER)"
	@echo "DOCKER_FPM_CONTAINER: $(DOCKER_FPM_CONTAINER)"
	@echo "--------- INPUT PARAMETERS ---------"

package: venv
	${PYTHON} packager/cli.py build -c $(PACKAGE_CONFIG) --override-version $(VERSION) --profile databus --profile aws --profile abfs

template: venv
	${PYTHON} packager/cli.py template -c $(PACKAGE_CONFIG) --override-version $(VERSION)

copy-package:
	docker run --rm -it --entrypoint "cp" -v $$(pwd)/build:/build $(DOCKER_BUILDER_CONTAINER) -r /$(PACKAGE_NAME).tar.gz /build

create-python-env:
	pip3 install virtualenv
	python3 -m venv env1

venv: $(VENV_NAME)/bin/activate

install-deps: venv
	${PYTHON} setup.py install

create-pre-package:
	rm -rf build/package
	mkdir -p build/package
	tar -xf build/$(PACKAGE_NAME).tar.gz -C build/package
	cp -r build/generated/** build/package

build-fpm-container:
	docker build -t $(DOCKER_FPM_CONTAINER) -f Dockerfile.fpm .

rpm: build-fpm-container
	rm -rf ${PWD}/build/*.rpm
	mkdir -p build/package/var/log/$(PACKAGE_NAME)
	docker run --rm -v ${PWD}:/src --user $$(id -u):$$(id -g) $(DOCKER_FPM_CONTAINER) -s dir -t rpm -n $(PACKAGE_NAME) -v $(VERSION) -p /src/build/$(RPM_NAME)-$(VERSION).x86_64.rpm \
	  --rpm-user root --rpm-group root --license "ASL 2.0" --vendor "$(COMPANY)" --iteration 1 --url "$(WEBPAGE)" \
	  --rpm-defattrfile 0750 --rpm-defattrdir 0750 \
	  --rpm-tag 'Requires(pre): /usr/bin/getent, /usr/sbin/adduser' \
	  --rpm-tag 'Requires: libyaml' \
	  --after-install /src/build/package-scripts/rpm/after-install.sh \
	  --before-remove /src/build/package-scripts/rpm/before-remove.sh \
	  --before-install /src/build/package-scripts/rpm/before-install.sh \
	  --description "${PACKAGE_DESCRIPTION}" --rpm-summary "${PACKAGE_DESCRIPTION}" \
	  -C /src/build/package .

test-rpm-container:
	docker build -t oleewere/logging-agent:latest -f Dockerfile.test .
	docker run --rm --entrypoint bash -it oleewere/logging-agent:latest

release: install-rpm
	${RELEASE_COMMAND} ${RELEASE_COMMAND_PARAMETERS}
	
