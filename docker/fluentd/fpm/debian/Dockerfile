ARG FROM=debian:buster
FROM ${FROM}

#COPY qemu-* /usr/bin/

RUN \
  echo "debconf debconf/frontend select Noninteractive" | \
    debconf-set-selections

ARG DEBUG

RUN sed -i'' -e 's/main$/main contrib non-free/g' /etc/apt/sources.list
RUN grep '^deb' /etc/apt/sources.list | sed -e 's/^deb /deb-src /g' >> /etc/apt/sources.list

RUN quiet=$([ "${DEBUG}" = "yes" ] || echo "-qq") && apt update ${quiet} && apt install -y -V ${quiet} \
    build-essential \
    debhelper \
    devscripts \
    ruby-dev \
    ruby-bundler \
    libedit2 \
    libncurses5-dev \
    libyaml-dev \
    git \
    pkg-config \
    libssl-dev \
    libpq-dev \
    tar \
    lsb-release \
    zlib1g-dev && \
    apt build-dep -y ruby && \
    gem install fpm && mkdir /src && apt clean && rm -rf /var/lib/apt/lists/*

WORKDIR /src/

ENTRYPOINT ["/usr/local/bin/fpm"]



