#!/bin/bash

# Guest Ranch Management Platform - Update Script for Debian-based systems
# Run with sudo: sudo ./update.sh

set -e

APP_DIR="/opt/guestranch"

cd "$APP_DIR"

echo "Pulling latest changes from git..."
git pull

echo "Activating virtual environment..."
source venv/bin/activate

echo "Updating dependencies..."
pip install -r requirements.txt
pip install .

echo "Running migrations..."
python3 manage.py migrate
python3 manage.py collectstatic --noinput

echo "Restarting services..."
systemctl restart guestranch
systemctl restart nginx

echo "Update complete!"
