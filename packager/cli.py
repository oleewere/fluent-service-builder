import click
import os
import packager

def version():
    version="0.1.0-SNAPSHOT"
    version_path="VERSION"
    if os.path.isfile(version_path):
        with open(version_path) as f:
            version = f.readline().rstrip()
    return version

__version__=version()

@click.group()
@click.version_option(__version__, message='%(version)s')
def main():
    """Tool for packaging custom fluent service"""

@main.command('build')
@click.option('--config','-c', help='Configuration file for service generatio.', type=click.Path(exists=True), required=True)
@click.option('--profile', '-p', help='Gem profile that are included in the binary', multiple=True, default=[])
@click.option('--override-version', help='Override package version (configuration).')
def build(config, profile, override_version):
    """Generate docker container for fluentd service generation"""
    packager.buildDockerContainer(config, profile, override_version)

@main.command('template')
@click.option('--config','-c', help='Configuration file for service generatio.', type=click.Path(exists=True), required=True)
@click.option('--override-version', help='Override package version (configuration).')
def generate(config, override_version):
    """Generate fluentd files from pre-defined jinja templates"""
    packager.generateTemplates(config, override_version)

@main.command('package')
@click.option('--config','-c', help='Configuration file for service generatio.', type=click.Path(exists=True), required=True)
@click.option('--override-version', help='Override package version (configuration).')
def package(config, override_version):
    """Generate os package based on the 'build' output"""
    packager.packageDocker(config, override_version)

if __name__ == "__main__":
    main()