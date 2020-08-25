FROM python:3.7-stretch

#RUN apt update && apt install -y git make
RUN pip install virtualenv
RUN python3 -m venv /root/env1
COPY . /app
WORKDIR /app
RUN . /root/env1/bin/activate && python3 setup.py install
