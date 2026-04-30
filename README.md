# Guest Ranch Management Platform (Beta v1)

This project is a Django-based management platform for a guest ranch.

## Features
- Horse management
- Client and household tracking
- Reservation management
- Vehicle tracking
- Ranch office reporting

## Git Setup

To set this project up on Git, run the following commands in your terminal:

```bash
git init
git add .
git commit -m "Initial commit: Beta version 1"
# Add your remote repository
git remote add origin YOUR_REMOTE_REPO_URL
git push -u origin main
```

## Debian Installation

This project includes scripts for easy installation and updates on Debian-based Linux systems (Ubuntu, Debian, etc.).

### Prerequisites
- A Debian-based server
- Root or sudo access
- A Git repository hosting this code

### Installation Steps

1. **Upload or Clone the code**:
   On your server, clone the repository or upload the files.

2. **Run the installation script**:
   ```bash
   cd GuestRanchManagementPlatform
   chmod +x deploy/install.sh
   sudo ./deploy/install.sh
   ```

   *Note: Edit `deploy/install.sh` first to set your `REPO_URL`.*

3. **Configure Nginx**:
   Edit `/etc/nginx/sites-available/guestranch` to set your domain name or IP address, then restart Nginx:
   ```bash
   sudo systemctl restart nginx
   ```

### Updates

To update the application to the latest version from Git:

```bash
sudo ./deploy/update.sh
```

## Development

1. Create a virtual environment: `python -m venv venv`
2. Activate it: `source venv/bin/activate` (Linux) or `venv\Scripts\activate` (Windows)
3. Install dependencies: `pip install -r requirements.txt`
4. Run migrations: `python manage.py migrate`
5. Start server: `python manage.py runserver`
