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

## Development

```
python3 -m venv env1
python3 setup.py install
python3 packager/cli.py --help
```

## TODOs
- support Windows/MacOS/deb packages
