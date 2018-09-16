FROM python:3.7-alpine

RUN adduser -S danmaku
USER danmaku

COPY requirements.txt /data/requirements.txt

USER root

# RUN echo "http://mirrors.tuna.tsinghua.edu.cn/alpine/v3.3/main" > /etc/apk/repositories  && \
# 	echo "[global]" > /etc/pip.conf && \
# 	echo "index-url=https://pypi.tuna.tsinghua.edu.cn/simple" >> /etc/pip.conf

RUN apk add --update --no-cache --virtual .build-deps \
	gcc libc-dev linux-headers

RUN pip3 install --upgrade pip setuptools && \
	pip3 install cython && \
	pip3 install -r /data/requirements.txt

RUN apk del .build-deps

WORKDIR /data
USER danmaku
