FROM centos:7
ADD build /build
RUN yum install -y /build/fluent-bit/*.rpm
CMD ["bash"]
