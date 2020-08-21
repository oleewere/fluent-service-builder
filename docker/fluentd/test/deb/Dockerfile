FROM debian:buster
ADD build /build
ARG PACKAGE_NAME=logging-agent
RUN dpkg -i /build/*.deb
ENTRYPOINT ["${PACKAGE_NAME}"]