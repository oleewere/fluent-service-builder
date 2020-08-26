# fluent-service-packager

![license](http://img.shields.io/badge/license-Apache%20v2-blue.svg)

Fluent service package builder. Currently support only RPM packages. Built based on [onmibus-td-agent](https://github.com/treasure-data/omnibus-td-agent) and [td-agent-builder](https://github.com/fluent-plugins-nursery/td-agent-builder)

## Description

- configurable package name / version
- configurable fluentd distribution
- configurable ruby/jemalloc distribution
- configurable fluentd plugins (profile based)

## Requirements

- docker
- git
- python3.5+
- pip3

## Usage

Clone the repository:

```bash
git clone git@github.com:oleewere/fluent-service-builder.git
cd fluent-service-builder
```

Build rpm:

```bash
make install-rpm PACKAGE_CONFIG=config/logging-agent.yaml
```

## Release

### Create tag and branch

```bash
make tag-and-branch PACKAGE_CONFIG=config/logging-agent.yaml
```

### Trigger jenkins job:

If tag is pushed with an actual master branch commit, build job will do the release automatically based on the tag.

If you added the tag later you can trigger the release job as well.

- build: https://build.service-delivery.cloudera.com/job/cdp-logging-agent-build
- release: https://build.service-delivery.cloudera.com/job/cdp-logging-agent-release

### Increase the version

After the release has been finished, increase the value in the `VERSION` file.

## Development

```
python3 -m venv env1
python3 setup.py install
python3 packager/cli.py --help
```

## TODOs
- support Windows/MacOS/deb packages
