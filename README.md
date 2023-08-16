# HNSHosting Wordpress
This is split into two parts.
There is the master server which is the server that will be used to manage the worker servers.
Then there is the worker server which is the server that will be used to host the wordpress site.

This is done to make it easier to manage multiple wordpress sites on multiple servers.

## Overview

The master server will be used to manage the worker servers.
The worker servers will be used to host the wordpress sites.
The bot will be used to provide an easier way to manage the master server.

## Usage

!TODO


## Master server install

Docker is the easiest way to install the master server.

```
docker run -d -p 5000:5000 -e LICENCE-API=your-api-key -e WORKER_KEY=your-api-key --name hnshosting-master git.woodburn.au/nathanwoodburn/hnshosting-master:latest -v ./data:/data
```
You can also mount a docker volume to /data to store the files instead of mounting a host directory.

Alternatively you can install it manually.
Set your .env file.
```
cd master
python3 -m pip install -r requirements.txt
python3 main.py
```


## Worker server install

Install prerequisites:

```
chmod +x install.sh
./install.sh
```

Add worker to master server:

```
curl -X POST http://master-server-ip:5000/add-worker?worker=worker-name&ip=worker-server-ip -H "key: api-key"
```

## Discord bot install

Docker install
```
docker run -d -p 5000:5000 -e MASTER_IP=<MASTER SERVER IP> -e DISCORD_TOKEN=<YOUR-BOT-TOKEN> -e LICENCE-API=your-api-key -e WORKER_KEY=your-api-key --name hnshosting-bot git.woodburn.au/nathanwoodburn/hnshosting-bot:latest
```