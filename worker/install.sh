#!/bin/bash
# Initial install for all prerequisites for the project.
# This makes it quicker to get each site up and running.

# Stop kernel prompts
export DEBIAN_FRONTEND=noninteractive
export NEEDRESTART_MODE=a
echo "Dpkg::Options { \"--force-confdef\"; \"--force-confold\"; };" | sudo tee /etc/apt/apt.conf.d/local

KERNEL_VERSION=$(uname -r)
sudo apt-mark hold linux-image-generic linux-headers-generic linux-generic linux-image-$KERNEL_VERSION linux-headers-$KERNEL_VERSION

# Install Docker
sudo apt update
sudo apt install apt-transport-https ca-certificates curl software-properties-common python3-pip nginx -y
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
apt-cache policy docker-ce
sudo apt install docker-ce docker-compose -y

# Install python prerequisites
python3 -m pip install -r requirements.txt
cp .env.example .env
chmod +x wp.sh tlsa.sh

# Add proxy to docker
mkdir ~/.docker
echo """{
  \"proxies\": {
    \"default\": {
      \"httpProxy\": \"http://proxy.hnsproxy.au:80\",
      \"httpsProxy\": \"https://proxy.hnsproxy.au:443\",
      \"noProxy\": \"localhost\"
    }
  }
}""" > ~/.docker/config.json

# Restart docker
sudo systemctl restart docker

# Pull docker images to save time later
docker pull mysql:5.7 &
docker pull wordpress:latest &
wait