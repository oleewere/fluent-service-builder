ARG FROM=debian:buster
FROM ${FROM}

#COPY qemu-* /usr/bin/

RUN \
  echo "debconf debconf/frontend select Noninteractive" | \
    debconf-set-selections

ARG DEBUG

RUN sed -i'' -e 's/main$/main contrib non-free/g' /etc/apt/sources.list
RUN grep '^deb' /etc/apt/sources.list | sed -e 's/^deb /deb-src /g' >> /etc/apt/sources.list

RUN \
  quiet=$([ "${DEBUG}" = "yes" ] || echo "-qq") && \
  apt update ${quiet} && \
  apt install -y -V ${quiet} \
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
  apt clean && \
  rm -rf /var/lib/apt/lists/*

ENV LC_ALL=en_US.UTF-8
ENV LANG=en_US.UTF-8

RUN mkdir -p /downloads
WORKDIR /downloads

# download fluentd
ARG FLUENTD_REVISION=6beca80f6467fd2e12ea25b21e0474d978007b08
RUN git clone https://github.com/fluent/fluentd.git && cd fluentd && git checkout ${FLUENTD_REVISION}

# download ruby
ARG BUNDLED_RUBY_FEATURE_VERSION=2.7
ARG BUNDLED_RUBY_VERSION=2.7.1

RUN curl -k -O -J -L -o ruby-${BUNDLED_RUBY_VERSION}.tar.gz https://cache.ruby-lang.org/pub/ruby/${BUNDLED_RUBY_FEATURE_VERSION}/ruby-${BUNDLED_RUBY_VERSION}.tar.gz
RUN tar -xzf ruby-${BUNDLED_RUBY_VERSION}.tar.gz

# apply ruby patches
COPY ruby-${BUNDLED_RUBY_FEATURE_VERSION} /app/ruby-${BUNDLED_RUBY_FEATURE_VERSION}
RUN cd ruby-${BUNDLED_RUBY_VERSION} && find . -name "/app/ruby-*/*.patch" | xargs patch -p1 --input=

# download jemalloc
ARG JEMALLOC_VERSION=5.2.1
RUN curl -k -O -J -L -o jemalloc-${JEMALLOC_VERSION}.tar.bz2 https://github.com/jemalloc/jemalloc/releases/download/${JEMALLOC_VERSION}/jemalloc-${JEMALLOC_VERSION}.tar.bz2
RUN tar -xf jemalloc-${JEMALLOC_VERSION}.tar.bz2

ARG PACKAGE_NAME=logging-agent
ENV PACKAGE_DIR=/opt/${PACKAGE_NAME}
# install jemalloc
RUN cd jemalloc-${JEMALLOC_VERSION} && ./configure --prefix ${PACKAGE_DIR} && make install
# install ruby 
RUN cd ruby-${BUNDLED_RUBY_VERSION} && ./configure --prefix ${PACKAGE_DIR} && make install

# gem dir tiny version is always 0
ARG GEM_DIR_VERSION=2.7.0
RUN mkdir -p /downloads/plugin_gems
ENV GEM_HOME ${PACKAGE_DIR}/lib/ruby/gems/${GEM_DIR_VERSION}
ENV PATH="${PATH}:${PACKAGE_DIR}/bin"

# install fluentd
RUN cd /downloads/fluentd && rake build && gem install pkg/fluentd*.gem --no-document --bindir ${PACKAGE_DIR}/bin

ARG PLUGIN_GEMS
ARG PLUGIN_GEMS_WITH_REPO
# download plugin gems
RUN cd /downloads/plugin_gems && echo "${PLUGIN_GEMS}" | tr ';' '\n' | awk '{split($0,a,"##"); printf "%s --version %s\n",  a[1], a[2]}' | xargs -L1 gem fetch 
RUN cd /downloads/plugin_gems && echo "${PLUGIN_GEMS_WITH_REPO}" | tr ';' '\n' | awk '{split($0,a,"##"); printf "%s --version %s -s %s\n",  a[1], a[2], a[3]}' | xargs -L1 gem fetch
# install plugin gems
RUN cd /downloads/plugin_gems && gem install *.gem --no-document --bindir ${PACKAGE_DIR}/bin

# remove unneded files
RUN rm -rf ${PACKAGE_DIR}/share/doc
# todo: unless windows - endswith ".dll.a"
RUN rm -rf ${PACKAGE_DIR}/lib/lib*.a 
RUN rm -rf ${GEM_HOME}/cache/*.gem
RUN rm -rf ${GEM_HOME}/gems/*/test
RUN rm -rf ${GEM_HOME}/gems/*/spec
RUN rm -rf ${GEM_HOME}/gems/*/**/gem.build_complete
RUN rm -rf ${GEM_HOME}/gems/*/ext/**/a.out
RUN rm -rf ${GEM_HOME}/gems/*/ext/**/*.o
RUN rm -rf ${GEM_HOME}/gems/*/ext/**/*.la
RUN rm -rf ${GEM_HOME}/gems/*/ext/**/*.a
RUN rm -rf ${GEM_HOME}/gems/*/ext/**/.libs
RUN rm -rf ${GEM_HOME}/gems/*/.github
# remove unneeded google-api related files
RUN find ${GEM_HOME}/gems/google-api-client-*/generated/google/apis -mindepth 1 -type d -not -name "storage*_v1" -exec rm -rf {} +; exit 0
RUN find ${GEM_HOME}/gems/google-api-client-*/generated/google/apis -type f -not -name "storage*_v1" -exec rm -rf {} +; exit 0

# licenses
RUN mkdir -p ${PACKAGE_DIR}/LICENSES
COPY LICENSE ${PACKAGE_DIR}/LICENSES/LICENSE-${PACKAGE_NAME}.txt
RUN cp /downloads/ruby-${BUNDLED_RUBY_VERSION}/COPYING ${PACKAGE_DIR}/LICENSES/LICENSE-Ruby.txt
RUN cp /downloads/jemalloc-${JEMALLOC_VERSION}/COPYING ${PACKAGE_DIR}/LICENSES/LICENSE-jemalloc.txt
RUN gem list -d > ${PACKAGE_DIR}/LICENSES/LICENCE-gems.txt

WORKDIR /
RUN tar -czf ${PACKAGE_NAME}.tar.gz ${PACKAGE_DIR}