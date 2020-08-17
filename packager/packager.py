import yaml
import os
import requests
import docker
import json
import sys
import glob
import sys
from jinja2 import Environment, Template

def __read_config(configOpt):
    with open(configOpt) as file:
        config = yaml.load(file, yaml.SafeLoader)
        return config

def buildDockerContainer(configOpt, profiles, overrideVersion, osType):
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

    os_folder="centos"
    if osType == "debian":
        os_folder="debian"
        imageParts=builderDockerImageName.rsplit(':', 1)
        builderDockerImageName=("%s:%s" % (imageParts[0] + "-debian", imageParts[1]))

    dockerfile=os.path.join(os.path.dirname((os.path.dirname(os.path.abspath(__file__)))), "docker", "os", os_folder, "Dockerfile")
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
    client = docker.DockerClient(base_url='unix://var/run/docker.sock')
    volumes={os.path.join(pathdir, "build"): {'bind': '/build', 'mode': 'rw'}}
    container=client.containers.run(builderDockerImageName, "-r /%s.tar.gz /build" % packageName, 
        volumes=volumes,
        detach=False,
        remove=True,
        entrypoint="cp"
    )

def packageDocker(configOpt, overrideVersion, osType):
    config=__read_config(configOpt)
    outputFolder=config["outputFolder"]
    packageFolder=os.path.join(outputFolder, "package")
    packageName=config["package"]["PACKAGE_NAME"]
    packageVersion=overrideVersion if overrideVersion else config["package"]["PACKAGE_VERSION"]
    fpmDockerImageName=config["fpmDockerImageName"]
    # first, build docker image for fpm
    dockerfile=os.path.join(os.path.dirname((os.path.dirname(os.path.abspath(__file__)))), "docker", "fpm", "Dockerfile")
    pathdir=os.path.dirname((os.path.dirname(os.path.abspath(__file__))))
    print("Build fpm docker image: %s" % fpmDockerImageName)
    docker_client = docker.APIClient(base_url='unix://var/run/docker.sock')
    streamer = docker_client.build(path=pathdir, dockerfile=dockerfile, tag=fpmDockerImageName, rm=True, decode=True)
    for chunk in streamer:
        if 'stream' in chunk:
            for line in chunk['stream'].splitlines():
                print(line)
    print("Build package into %s by %s docker container..." % (outputFolder, fpmDockerImageName))
    package_type="rpm" # only supported at the moment
    print("Delete pre-existing rpms from the build folder...")
    for f in glob.glob(os.path.join(outputFolder, "*.rpm")):
        os.remove(f)
    
    logdir=os.path.join(packageFolder, "var", "log", packageName)
    if not os.path.exists(logdir):
        os.makedirs(logdir)

    fpm_build_folder=os.path.join("/src", outputFolder)
    fpm_params=[]
    fpm_params.append(("-s", "dir"))
    fpm_params.append(("--vendor", '"' + config["package"]["COMPANY"] + '"'))
    fpm_params.append(("--license", '"' + config["package"]["LICENSE"] + '"'))
    fpm_params.append(("-n", packageName))
    fpm_params.append(("-v", packageVersion))
    fpm_params.append(("--iteration", "1"))
    fpm_params.append(("--url", config["package"]["WEBPAGE"]))
    fpm_params.append(("-C", os.path.join(fpm_build_folder, "package")))
    fpm_params.append(("--description", '"' + config["package"]["PACKAGE_DESCRIPTION"] + '"'))
    if package_type == "rpm":
        rpm_name="%s-%s.x86_64.rpm" % (packageName.replace("-", "_"), packageVersion)
        package_scripts_folder=os.path.join(fpm_build_folder, "package-scripts", "rpm")
        fpm_params.append(("-t", "rpm"))
        fpm_params.append(("-p", os.path.join(fpm_build_folder, rpm_name)))
        fpm_params.append(("--after-install", os.path.join(package_scripts_folder, "after-install.sh")))
        fpm_params.append(("--before-install", os.path.join(package_scripts_folder, "before-install.sh")))
        fpm_params.append(("--before-remove", os.path.join(package_scripts_folder, "before-remove.sh")))
        fpm_params.append(("--rpm-summary", '"' + config["package"]["PACKAGE_DESCRIPTION"] + '"'))
        fpm_params.append(("--rpm-user", config["package"]["USER"]))
        fpm_params.append(("--rpm-group", config["package"]["GROUP"]))
        fpm_params.append(("--rpm-defattrfile", "0750"))
        fpm_params.append(("--rpm-defattrdir", "0750"))
        fpm_params.append(("--rpm-tag", "'Requires(pre): /usr/bin/getent, /usr/sbin/adduser'"))
        fpm_params.append(("--rpm-tag", "'Requires: libyaml'"))
    print("fpm params:")
    fpm_params_str=''
    for t in fpm_params:
        fpm_params_str="%s %s %s" % (fpm_params_str, t[0], t[1])
    fpm_params_str=fpm_params_str + " ."
    print(fpm_params_str)
    volumes={pathdir: {'bind': '/src', 'mode': 'rw'}}
    client = docker.DockerClient(base_url='unix://var/run/docker.sock')
    container=client.containers.run(fpmDockerImageName, fpm_params_str, 
        volumes=volumes, 
        user="%s:%s" % (os.getuid(), os.getgid()), 
        detach=True,
    )
    result = container.wait()
    exit_code=result["StatusCode"]
    print("Container logs:")
    print(container.logs())
    container.remove()
    if exit_code != 0:
        print("Exit code of the container: %s" % exit_code)
        sys.exit(1)


def generateTemplates(configOpt, overrideVersion, osType):
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

    if osType == "centos":
        rpm_package_template_folder=os.path.join(template_dir, "package-scripts", "fluentd-agent", "rpm")
        rpm_package_output_folder=os.path.join(packageScriptsFolder, "rpm")

        rpm_before_install_template=os.path.join(rpm_package_template_folder, "before-install.sh.j2")
        render_template(rpm_before_install_template, rpm_package_output_folder, "before-install.sh", templateVars)
        
        rpm_before_remove_template=os.path.join(rpm_package_template_folder, "before-remove.sh.j2")
        render_template(rpm_before_remove_template, rpm_package_output_folder, "before-remove.sh", templateVars)
        
        rpm_after_install_template=os.path.join(rpm_package_template_folder, "after-install.sh.j2")
        render_template(rpm_after_install_template, rpm_package_output_folder, "after-install.sh", templateVars)
    elif osType == "debian":
        deb_package_template_folder=os.path.join(template_dir, "package-scripts", "fluentd-agent", "deb")
        deb_package_output_folder=os.path.join(packageScriptsFolder, "deb")

        deb_before_remove_template=os.path.join(deb_package_template_folder, "postinst")
        render_template(deb_before_remove_template, deb_package_output_folder, "postinst", templateVars)
        
        deb_after_install_template=os.path.join(deb_package_template_folder, "postrm")
        render_template(deb_after_install_template, deb_package_output_folder, "postrm", templateVars)

def render_template(source_template, target_dir, filename, templateVars):
    template_str=open(source_template, 'r').read()
    rendered_str=Environment().from_string(template_str).render(templateVars=templateVars, os=os)
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
    rendered_filename=os.path.join(target_dir, filename)
    with open(rendered_filename, "w") as rendered_file:
        rendered_file.write(rendered_str)