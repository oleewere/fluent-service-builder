import yaml
import os
import requests
import docker
import json
import sys
from jinja2 import Environment, Template

def __read_config(configOpt):
    with open(configOpt) as file:
        config = yaml.load(file, yaml.SafeLoader)
        return config

def buildDockerContainer(configOpt, profiles, overrideVersion):
    config=__read_config(configOpt)
    outputFolder=config["outputFolder"]
    packageName=config["package"]["PACKAGE_NAME"]
    packageVersion=overrideVersion if overrideVersion else config["package"]["PACKAGE_VERSION"]
    rubyVersion=config["ruby"]["BUNDLED_RUBY_VERSION"]
    builderDockerImageName=config["builderDockerImageName"]
    print("Package name: %s" % packageName)
    print("Package version: %s" % packageVersion)
    if not os.path.exists(outputFolder):
        os.mkdir(outputFolder)
    packageDir="/opt/%s" % packageName
    plugin_gems=config["plugin_gems"]
    plugin_gems_with_repo=[]
    plugin_gems_without_repo=[]
    for plugin_gem in plugin_gems:
        if profiles and "profile" in plugin_gem and plugin_gem["profile"] not in profiles:
            print("Gem '%s' won't be installed as '%s' profile is not provided." % (plugin_gem["name"], plugin_gem["profile"]))
            continue
        if "repo" in plugin_gem:
            plugin_gems_with_repo.append("%s##%s##%s" % (plugin_gem["name"], plugin_gem["version"], plugin_gem["repo"]))
        else:
            plugin_gems_without_repo.append("%s##%s" % (plugin_gem["name"], plugin_gem["version"]))
    plugin_gems_str=";".join(plugin_gems_without_repo)
    plugin_gems_with_repo_str=";".join(plugin_gems_with_repo)

    default_folder="centos"
    dockerfile=os.path.join(os.path.dirname((os.path.dirname(os.path.abspath(__file__)))), "docker", "os", default_folder, "Dockerfile")
    pathdir=os.path.dirname((os.path.dirname(os.path.abspath(__file__))))
    docker_client = docker.APIClient(base_url='unix://var/run/docker.sock')
    # gem install path - tiny version always 0
    gemDirVersion=rubyVersion.rsplit('.',1)[0] + ".0"
    build_args={}
    build_args["PLUGIN_GEMS"]=plugin_gems_str
    build_args["PLUGIN_GEMS_WITH_REPO"]=plugin_gems_with_repo_str
    build_args["GEM_DIR_VERSION"]=gemDirVersion
    build_args["PACKAGE_NAME"]=packageName
    build_args["PACKAGE_VERSION"]=packageVersion
    build_args["FLUENTD_REVISION"]=config["fluentd"]["FLUENTD_REVISION"]
    build_args["BUNDLED_RUBY_VERSION"]=rubyVersion
    build_args["BUNDLED_RUBY_FEATURE_VERSION"]=rubyVersion.rsplit('.',1)[0]
    build_args["JEMALLOC_VERSION"]=config["fluentd"]["JEMALLOC_VERSION"]
    streamer = docker_client.build(path=pathdir, dockerfile=dockerfile, tag=builderDockerImageName, rm=True, decode=True, buildargs=build_args)
    for chunk in streamer:
        if 'stream' in chunk:
            for line in chunk['stream'].splitlines():
                print(line)

def generateTemplates(configOpt, overrideVersion):
    config=__read_config(configOpt)
    outputFolder=config["outputFolder"]
    packageName=config["package"]["PACKAGE_NAME"]
    packageVersion=overrideVersion if overrideVersion else config["package"]["PACKAGE_VERSION"]
    packageRelease=config["package"]["PACKAGE_RELEASE"] if "PACKAGE_RELEASE" in config["package"] else 0
    rubyVersion=config["ruby"]["BUNDLED_RUBY_VERSION"]
    packageDisplayName=config["package"]["PACKAGE_DISPLAY_NAME"]
    if not os.path.exists(outputFolder):
        os.mkdir(outputFolder)
    templateOutputDir=os.path.join(outputFolder, "generated")
    if not os.path.exists(templateOutputDir):
        os.mkdir(templateOutputDir)
    packageDir="/opt/%s" % packageName
    templateVars={}
    print("Generating project files from the following template inputs:")
    templateVars["project_name"]=packageName
    templateVars["project_version"]=packageVersion
    templateVars["project_release"]=packageRelease
    templateVars["project_user"]=config["package"]["USER"] if "USER" in config["package"] else packageName
    templateVars["project_group"]=config["package"]["GROUP"] if "GROUP" in config["package"] else packageName
    templateVars["project_var_prefix"]=str(packageName).upper().replace("-", "_")
    templateVars["company"]=config["package"]["COMPANY"]
    templateVars["copyright"]=config["package"]["COPYRIGHT"]
    templateVars["project_webpage_docs"]=config["package"]["WEBPAGE_DOCS"]
    templateVars["install_path"]=packageDir
    # gem install path - tiny version always 0
    gemDirVersion=rubyVersion.rsplit('.',1)[0] + ".0"
    templateVars["gem_install_path"]=os.path.join(packageDir, "lib", "ruby", "gems", gemDirVersion)

    print(templateVars)
    parent_dir=os.path.dirname((os.path.dirname(os.path.abspath(__file__))))
    template_dir=os.path.join(parent_dir, "templates")
    
    initd_template=os.path.join(template_dir, "etc", "init.d", "fluentd-agent.j2")
    initd_file_parent=os.path.join(templateOutputDir, "etc", "init.d")
    render_template(initd_template, initd_file_parent, "%s" % packageName, templateVars)

    fluentd_conf_template=os.path.join(template_dir, "etc", "fluentd", "fluentd.conf")
    fluentd_conf_file_parent=os.path.join(templateOutputDir, "etc", packageName)
    render_template(fluentd_conf_template, fluentd_conf_file_parent, "%s.conf" % packageName, templateVars)

    logrotate_template=os.path.join(template_dir, "etc", "logrotate.d", "fluentd-agent")
    logrotate_file_parent=os.path.join(templateOutputDir, "etc", "logrotate.d")
    render_template(logrotate_template, logrotate_file_parent, "%s" % packageName, templateVars)

    systemd_template=os.path.join(template_dir, "etc", "systemd", "fluentd-agent.service.j2")
    systemd_file_parent=os.path.join(templateOutputDir, "etc", "systemd")
    render_template(systemd_template, systemd_file_parent, "%s.service" % packageName, templateVars)

    sbin_agent_template=os.path.join(template_dir, "usr", "sbin", "fluentd-agent.j2")
    sbin_agent_file_parent=os.path.join(templateOutputDir, "usr", "sbin")
    render_template(sbin_agent_template, sbin_agent_file_parent, "%s" % packageName, templateVars)

    sbin_gem_template=os.path.join(template_dir, "usr", "sbin", "fluentd-gem.j2")
    sbin_gem_file_parent=os.path.join(templateOutputDir, "usr", "sbin")
    render_template(sbin_gem_template, sbin_gem_file_parent, "%s-gem" % packageName, templateVars)

    tmp_files_template=os.path.join(template_dir, "usr", "lib", "tmpfiles.d", "fluentd-agent.conf.j2")
    tmp_files_file_parent=os.path.join(templateOutputDir, "usr", "lib", "tmpfiles.d")
    render_template(tmp_files_template, tmp_files_file_parent, "%s.conf" % packageName, templateVars)

    ruby_conf_template=os.path.join(template_dir, "opt", "fluentd-agent", "share", "fluentd-agent-ruby.conf.j2")
    ruby_conf_file_parent=os.path.join(templateOutputDir, "opt", packageName, "share")
    render_template(ruby_conf_template, ruby_conf_file_parent, "%s-ruby.conf" % packageName, templateVars)

    tmpl_conf_template=os.path.join(template_dir, "opt", "fluentd-agent", "share", "fluentd-agent.conf.tmpl.j2")
    tmpl_conf_file_parent=os.path.join(templateOutputDir, "opt", packageName, "share")
    render_template(tmpl_conf_template, tmpl_conf_file_parent, "%s.conf.tmpl" % packageName, templateVars)

    packageScriptsFolder=os.path.join(outputFolder, "package-scripts")
    if not os.path.exists(packageScriptsFolder):
        os.mkdir(packageScriptsFolder)
    rpm_package_template_folder=os.path.join(template_dir, "package-scripts", "fluentd-agent", "rpm")
    rpm_package_output_folder=os.path.join(packageScriptsFolder, "rpm")

    rpm_before_install_template=os.path.join(rpm_package_template_folder, "before-install.sh.j2")
    render_template(rpm_before_install_template, rpm_package_output_folder, "before-install.sh", templateVars)

    rpm_before_remove_template=os.path.join(rpm_package_template_folder, "before-remove.sh.j2")
    render_template(rpm_before_remove_template, rpm_package_output_folder, "before-remove.sh", templateVars)
    
    rpm_after_install_template=os.path.join(rpm_package_template_folder, "after-install.sh.j2")
    render_template(rpm_after_install_template, rpm_package_output_folder, "after-install.sh", templateVars)

def render_template(source_template, target_dir, filename, templateVars):
    template_str=open(source_template, 'r').read()
    rendered_str=Environment().from_string(template_str).render(templateVars=templateVars, os=os)
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
    rendered_filename=os.path.join(target_dir, filename)
    with open(rendered_filename, "w") as rendered_file:
        rendered_file.write(rendered_str)