gdanmaku-server
===============
![](https://img.shields.io/badge/license-GPLv3-blue.svg)
![](https://img.shields.io/badge/python-2.7-yellowgreen.svg)

Web-based danmaku server

## Installation

Install dependencies:

- python modules: `flask`, `gevent`, `pyredis`
- service: `redis`

Run `webserver.py` and open http://localhost:5000/ in your browser.

### I love docker 

Clone me first
```
git clone https://github.com/tuna/gdanmaku-server
cd gdanmaku-server
```

Get a redis docker and run

```
docker pull redis:alpine
docker run --name redis -v /var/lib/redis:/data -d redis:alpine
```

Modify `settings.py` or create a `settings_local.py` in the gdanmaku dir, and remember the `REDIS_HOST`
in your settings. Let's say, `myredis`.

Modify `Dockerfile`, you may want to change the `sources.list` part. Next we build the docker image of danmaku:

```
docker build --tag danmaku:dev .
```

We need to mount the code as volume to the docker container, and link redis to it. Try

```
docker run -it --rm --link redis:myredis -v /path/to/gdanmaku-server:/data/gdanmaku -p 127.0.0.1:5000:5000 danmaku:dev python2 gdanmaku/webserver.py
```

Open your browser and visit <http://localhost:5000/>, you should see the danmaku web page.

If you wanna run danmaku service as a daemon, use

```
docker run -d --name danmaku --link redis:myredis -v /path/to/gdanmaku-server:/data/gdanmaku -p 127.0.0.1:5000:5000 danmaku:dev python2 gdanmaku/webserver.py
```

Good luck, and have fun!

## Client

The official desktop client is available at https://github.com/bigeagle/danmaQ 

## TODO

- [ ] i18n
