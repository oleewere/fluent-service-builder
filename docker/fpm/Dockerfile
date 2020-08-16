FROM centos:8

RUN set -x \
    && yum --enablerepo=PowerTools install -y libedit-devel libyaml-devel \
    && yum install -y ruby-devel rubygems gcc make rpmdevtools \
    ncurses-devel \
    cyrus-sasl-devel \
    nss-softokn-freebl-devel \
    pkg-config \
    rpm-build \
    rpmdevtools \
    redhat-rpm-config \
    openssl-devel \
    tar \
    zlib-devel \
    rpmlint \
    && gem install fpm \
    && yum clean all \
    && mkdir /src

WORKDIR /src/

ENTRYPOINT ["/usr/local/bin/fpm"]