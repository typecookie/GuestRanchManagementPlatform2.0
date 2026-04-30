#!/bin/bash

# Guest Ranch Management Platform - Installation Script for Debian-based systems
# Run with sudo: sudo ./install.sh

set -e

APP_DIR="/opt/guestranch"
REPO_URL="YOUR_GIT_REPO_URL" # User should replace this

echo "Updating system packages..."
apt update
apt install -y python3 python3-venv python3-pip nginx git

echo "Setting up application directory..."
if [ ! -d "$APP_DIR" ]; then
    mkdir -p "$APP_DIR"
    git clone "$REPO_URL" "$APP_DIR"
fi

cd "$APP_DIR"

echo "Creating virtual environment..."
python3 -m venv venv
source venv/bin/bin/activate || source venv/bin/activate

echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
pip install .

echo "Setting up Django..."
python3 manage.py migrate
python3 manage.py collectstatic --noinput

echo "Setting up systemd service..."
cp deploy/guestranch.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable guestranch
systemctl start guestranch

echo "Setting up Nginx..."
cp deploy/nginx.conf /etc/nginx/sites-available/guestranch
ln -sf /etc/nginx/sites-available/guestranch /etc/nginx/sites-enabled
nginx -t
systemctl restart nginx

echo "Installation complete!"
