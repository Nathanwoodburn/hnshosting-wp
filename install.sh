#!/bin/bash
# Initial install for all prerequisites for the project.

# Update the system
sudo apt update && sudo apt upgrade -y

# Install python prerequisites
python3 -m pip install -r requirements.txt

# Create a service to run the python web server

# Flask app directory and file
APP_DIR=$(pwd)
APP_FILE=main.py

# Name for your systemd service
SERVICE_NAME=HNSHosting-Main

# Create a user and group to run the service

SERVICE_USER=hnshosting
SERVICE_GROUP=hnshosting

sudo groupadd $SERVICE_GROUP
sudo useradd -g $SERVICE_GROUP $SERVICE_USER

# Create a systemd service unit file
echo "[Unit]
Description=HNSHosting Main Service
After=network.target

[Service]
User=$SERVICE_USER
Group=$SERVICE_GROUP
WorkingDirectory=$APP_DIR
ExecStart=/usr/bin/python3 $APP_DIR/$APP_FILE
Restart=always

[Install]
WantedBy=multi-user.target" | sudo tee /etc/systemd/system/$SERVICE_NAME.service

# Reload systemd to pick up the new unit file
sudo systemctl daemon-reload

# Enable and start the service
sudo systemctl enable $SERVICE_NAME
sudo systemctl start $SERVICE_NAME

echo "Service created and started."
