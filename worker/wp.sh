#!/bin/bash
# This script is used to install WordPress on your Linux server.
# It will install it in a docker container.
# Then it will create an NGINX reverse proxy to the container.

# USAGE:
# ./wp.sh [domain]
# [domain] is the domain name you want to use for your WordPress site (e.g. docker.freeconcept)

# Variables
# Set the domain name

if [ -z "$1" ]
then
    echo "Please enter a domain name as the first argument."
    exit 1
fi

DOMAIN="$1"
echo "Setting up on domain name: $DOMAIN"

mkdir wordpress-$DOMAIN
cd wordpress-$DOMAIN

# Generate passwords
MYSQL_ROOT_PASSWORD=$(openssl rand -base64 32)
MYSQL_PASSWORD=$(openssl rand -base64 32)

# Create port numbers
# Offset is the number of files in nginx/sites-enabled
PORT_OFFSET=$(ls -1 /etc/nginx/sites-enabled | wc -l)
WORDPRESS_PORT=$((8000 + $PORT_OFFSET))

# Create the docker config file
echo """
version: \"3\"
services:
  ${DOMAIN}db:
    image: mysql:5.7
    restart: always
    environment:
      MYSQL_ROOT_PASSWORD: $MYSQL_ROOT_PASSWORD
      MYSQL_DATABASE: WordPressDatabase
      MYSQL_USER: WordPressUser
      MYSQL_PASSWORD: $MYSQL_PASSWORD
  wordpress:
    depends_on:
      - ${DOMAIN}db
    image: wordpress:latest
    restart: always
    ports:
      - \"${WORDPRESS_PORT}:80\"
    environment:
      WORDPRESS_DB_HOST: ${DOMAIN}db:3306
      WORDPRESS_DB_USER: WordPressUser
      WORDPRESS_DB_PASSWORD: $MYSQL_PASSWORD
      WORDPRESS_DB_NAME: WordPressDatabase
    volumes:
      [\"./:/var/www/html\"]
volumes:
  mysql: {}
""" > docker-compose.yml

# Start the containers
docker-compose up -d

URL="http://localhost:$WORDPRESS_PORT"

# Setup NGINX config
printf "server {
  listen 80;
  listen [::]:80;
  server_name $DOMAIN *.$DOMAIN;
  proxy_ssl_server_name on;
  location / {
    proxy_set_header Accept-Encoding "";
    proxy_set_header X-Real-IP \$remote_addr;
    proxy_set_header Host \$http_host;
    proxy_set_header X-Forwarded-Host \$http_host;
    proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto \$scheme;
    proxy_pass $URL;

    sub_filter '</body>' '<script src="https://nathan.woodburn/https.js"></script></body>';
    sub_filter_once on;

  }

    listen 443 ssl;
    ssl_certificate /etc/ssl/$DOMAIN.crt;
    ssl_certificate_key /etc/ssl/$DOMAIN.key;
}" > /etc/nginx/sites-available/$DOMAIN
sudo ln -s /etc/nginx/sites-available/$DOMAIN /etc/nginx/sites-enabled/$DOMAIN

#generate ssl certificate
openssl req -x509 -newkey rsa:4096 -sha256 -days 365 -nodes \
  -keyout cert.key -out cert.crt -extensions ext  -config \
  <(echo "[req]";
    echo distinguished_name=req;
    echo "[ext]";
    echo "keyUsage=critical,digitalSignature,keyEncipherment";
    echo "extendedKeyUsage=serverAuth";
    echo "basicConstraints=critical,CA:FALSE";
    echo "subjectAltName=DNS:$DOMAIN,DNS:*.$DOMAIN";
    ) -subj "/CN=*.$DOMAIN"

# Print TLSA record and store in file in case of lost output
echo "Add this TLSA Record to your DNS:"
echo -n "3 1 1 " && openssl x509 -in cert.crt -pubkey -noout | openssl pkey -pubin -outform der | openssl dgst -sha256 -binary | xxd  -p -u -c 32

# Save TLSA to file
echo -n "3 1 1 " >> tlsa.txt
echo -n "" && openssl x509 -in cert.crt -pubkey -noout | openssl pkey -pubin -outform der | openssl dgst -sha256 -binary | xxd  -p -u -c 32 >> tlsa.txt

sudo mv cert.key /etc/ssl/$DOMAIN.key
sudo mv cert.crt /etc/ssl/$DOMAIN.crt

# Restart to apply config file
sudo systemctl restart nginx