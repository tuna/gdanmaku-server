FROM python:2.7-slim

RUN useradd danmaku
USER danmaku

COPY requirements.txt /data/requirements.txt

USER root

RUN echo "deb http://mirrors.tuna.tsinghua.edu.cn/debian/ jessie main contrib non-free" > /etc/apt/sources.list && \
	echo "deb http://mirrors.tuna.tsinghua.edu.cn/debian/ jessie-backports main contrib non-free" >> /etc/apt/sources.list && \
	echo "deb http://mirrors.tuna.tsinghua.edu.cn/debian/ jessie-updates main contrib non-free" >> /etc/apt/sources.list && \
	echo "deb http://mirrors.tuna.tsinghua.edu.cn/debian-security/ jessie/updates main contrib non-free" >> /etc/apt/sources.list

RUN echo "[global]" > /etc/pip.conf && \
	echo "index-url=https://pypi.tuna.tsinghua.edu.cn/simple" >> /etc/pip.conf

RUN apt-get update && apt-get install -y gcc

RUN pip2 install --upgrade pip setuptools && \
	pip2 install cython && \
	pip2 install -r /data/requirements.txt

RUN apt-get remove -y gcc && apt-get -y autoremove && apt-get -y clean 

WORKDIR /data
USER danmaku
