FROM centos:7
ADD build /build
ARG PACKAGE_NAME=logging-agent
RUN yum install -y /build/*.rpm
ENTRYPOINT ["${PACKAGE_NAME}"]