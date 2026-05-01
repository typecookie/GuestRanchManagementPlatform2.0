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

# Ensure correct permissions for the www-data user
# We'll do this again after migrations to be sure

cd "$APP_DIR"

echo "Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
pip install .

echo "Setting up Django..."
# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Configuring environment variables..."
    RANDOM_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(50))')
    
    # Check if we are in an interactive terminal
    if [ -t 0 ]; then
        read -p "Enable Django DEBUG mode? (y/N) [Default: N]: " DEBUG_PROMPT
        if [[ "$DEBUG_PROMPT" =~ ^[Yy]$ ]]; then
            DEBUG_VAL="True"
        else
            DEBUG_VAL="False"
        fi
    else
        DEBUG_VAL="False"
        echo "Non-interactive terminal detected. Defaulting DEBUG to False."
    fi

    cat > .env <<EOF
# Django Settings
DJANGO_SECRET_KEY=$RANDOM_KEY
DJANGO_DEBUG=$DEBUG_VAL

# Database Settings (Uncomment if moving away from SQLite)
# DATABASE_URL=postgres://user:password@localhost:5432/dbname
EOF
    echo ".env file created with a random secret key."
fi

# Create directories that might not exist yet to ensure correct ownership
mkdir -p "$APP_DIR/media" "$APP_DIR/staticfiles"

python3 manage.py migrate
python3 manage.py collectstatic --noinput
python3 manage.py setup_admin

# Ensure correct permissions for the www-data user AFTER migrations/setup
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

echo "Setting up systemd service..."
cp deploy/guestranch.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable guestranch
systemctl start guestranch

echo "Setting up Nginx..."
rm -f /etc/nginx/sites-enabled/default
cp deploy/nginx.conf /etc/nginx/sites-available/guestranch
ln -sf /etc/nginx/sites-available/guestranch /etc/nginx/sites-enabled
nginx -t
systemctl restart nginx

echo "Installation complete!"
