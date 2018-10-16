#!/usr/bin/env bash
cd .. && docker build --tag gdanmaku-server:current . && cd docker_conf &&
# I don't want to know string manipulation in shell
tg_token=$(python3 -c "import re;print(re.findall(r'TELEGRAM_TOKEN = .+',str(open('./settings_local.py').read()))[-1][18:-1])") &&
ipv4_addr=$(curl -4 icanhazip.com) &&
rm -Rf ./cert_key && mkdir ./cert_key &&
openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout ./cert_key/nginx-selfsigned.key -out ./cert_key/nginx-selfsigned.crt -subj "/C=US/ST=NY/L=BYL/O=TEST/CN=$ipv4_addr" &&
curl -F "url=" https://api.telegram.org/bot$tg_token/setWebhook &&
curl -F "url=https://$ipv4_addr/api/telegram/$tg_token" -F "certificate=@./cert_key/nginx-selfsigned.crt" https://api.telegram.org/bot$tg_token/setWebhook &&
docker swarm init --advertise-addr $ipv4_addr &&
docker stack deploy -c docker-compose.yml gdanmaku-server

