gdanmaku-server
===============
![](https://img.shields.io/badge/license-GPLv3-blue.svg)
![](https://img.shields.io/badge/python-3.7-yellowgreen.svg)

Web-based danmaku server

## Installation

### The easy way

0. Get yourself a VPS

1. Clone this project
    ```bash
    git clone https://github.com/tuna/gdanmaku-server
    cd gdanmaku-server
    ```
    
    Pay attention to where you see this guide and what repository you are cloning from.
    Actual repository address may differ.
    
2. Install `openssl` `curl` `python3` `nano` if there isn't

3. Install docker and docker-compose
    ```bash
    sudo snap install docker
    sudo curl -L --fail https://github.com/docker/compose/releases/download/1.22.0/run.sh -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    ```

4. Edit configs to your preference

    ```bash
    python3 -c "import random,hashlib;print(hashlib.sha1(str(random.random()).encode()).hexdigest())"
    ```
    
    Copy the output, we will call it <SECRET> in the following easy steps.
    
    ```bash
    curl -4 icanhazip.com
    ```
    This should be your public ip, we will use it in the following steps.
    
    If you want to use Wechat, log into your Wechat Subscription Account, get your Token.
    
    If you want to use telegram, get your telegram token.
    Now we can start editing configs
    ```bash
    cd docker_conf
    nano settings_local.py
    ```
    Copy the following contents into it.
    ```python
    DEBUG = False

    SECRET_KEY = "<SECRET>"

    # WECHAT
    WECHAT_TOKEN = "<WECHAT_TOKEN>"

    # TELEGRAM
    TELEGRAM_TOKEN = "<TELEGRAM_TOKEN>"
    ```
    Change \<SECRET\>, \<WECHAT_TOKEN\>, \<TELEGRAM_TOKEN\> according to your situation.
    
    After that you can press <kbd>Ctrl</kbd> + <kbd>O</kbd> to save and <kbd>Ctrl</kbd> + <kbd>X</kbd> to exit.
    
5. Run the script
    ```bash
    chmod +x ./easy_setup.sh
    sudo ./easy_setup.sh
    ```
    Wait until everything finished.
    
    > If you have trouble building docker image in executing the script above,
    you can try uncommenting the lines commented in PROJECT_ROOT_DIR/Dockerfile


6. Edit Wechat Subscription Account if necessary

    Change URL in your account settings to 
    ```
    http://<PUBLIC_IP>/api/wechat
    ```
7. Finished

    Now you are all set, go to https://www.github.com/tuna/danmaQ and get a display client.
    
### The other way

Install dependencies:

- python modules: `flask`, `gevent`, `pyredis`
- service: `redis`

Run `webserver.py` and open http://localhost:5000/ in your browser.



### I love docker

You should have a vps first,then you need to install the docker(More information you can find in official document of Docker)


Clone this project
```
git clone https://github.com/tuna/gdanmaku-server
cd gdanmaku-server
```

Get a redis docker and run

```
docker pull redis:alpine
docker run --name redis -v /var/lib/redis:/data -d redis:alpine
```

Modify `settings.py` or create a `settings_local.py` in the gdanmaku dir(if you want to use it in Wechat, please modify the `WECHAT_TOKEN` in `setting.py`), and remember the `REDIS_HOST`in your settings. Let's say, `myredis`.

Modify `Dockerfile`, you may want to change the `sources.list` part. Next we build the docker image of danmaku:

```
docker build --tag danmaku:dev .
```

We need to mount the code as volume to the docker container, and link redis to it. Try

```
docker run -it --rm --link redis:myredis -v /path/to/gdanmaku-server:/data/gdanmaku -p IP:Port:5000 danmaku:dev python3 gdanmaku/webserver.py
```
If failed please check the path (use pwd under gdanmaku-server to show the path), then change the path of the command.

Open your browser and visit <http://IP:port/>, you should see the danmaku web page.

If you wanna run danmaku service as a daemon, use

```
docker run -d --name danmaku --link redis:myredis -v /path/to/gdanmaku-server:/data/gdanmaku -p IP:Port:5000 danmaku:dev python3 gdanmaku/webserver.py
```
If you want to use it in Wechat, please set the port to 80, and open the firewall.
  
Good luck, and have fun!

## Client
The official desktop client is available at https://github.com/tuna/danmaQ 

