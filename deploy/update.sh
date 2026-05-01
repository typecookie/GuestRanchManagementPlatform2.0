#!/bin/bash

# Guest Ranch Management Platform - Update Script for Debian-based systems
# Run with sudo: sudo ./update.sh

set -e

APP_DIR="/opt/guestranch"

cd "$APP_DIR"

echo "Pulling latest changes from git..."
git pull

# Ensure correct permissions after pull
chown -R www-data:www-data "$APP_DIR"

echo "Activating virtual environment..."
source venv/bin/activate

echo "Updating dependencies..."
pip install -r requirements.txt
pip install .

echo "Running migrations..."
python3 manage.py migrate
python3 manage.py collectstatic --noinput

# Ensure correct permissions for the www-data user AFTER migrations
# SQLite needs the directory to be writable to create journal files
chown -R www-data:www-data "$APP_DIR"
find "$APP_DIR" -type d -exec chmod 775 {} +
find "$APP_DIR" -type f -exec chmod 664 {} +

# Re-enable execution for scripts and binaries
chmod +x "$APP_DIR/manage.py" || true
chmod +x "$APP_DIR/deploy/"*.sh || true
if [ -d "$APP_DIR/venv/bin" ]; then
    chmod -R +x "$APP_DIR/venv/bin/" || true
fi

echo "Restarting services..."
systemctl restart guestranch
systemctl restart nginx

echo "Update complete!"
