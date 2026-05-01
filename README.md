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
   The installer will:
   - Automatically create a `.env` file with a random secret key.
   - Prompt you to enable/disable Debug mode.
   - Prompt you to create a superuser if one doesn't exist.
   This user will have full access to both the platform and the Django Admin.

3. **User Roles**:
   - **Superusers**: Access to everything, including `/admin/`.
   - **Ranch Admins**: Access to all ranch management features and User Management within the app, but *cannot* access `/admin/`. To create a Ranch Admin, create a regular user and add them to the "Ranch Admins" group.

4. **Configure Nginx (Optional customization)**:
   The installer automatically sets up Nginx as the default server. If you want to change the domain name later, edit `/etc/nginx/sites-available/guestranch`:
   ```bash
   sudo nano /etc/nginx/sites-available/guestranch
   sudo systemctl restart nginx
   ```

### Updates

To update the application to the latest version from Git:

```bash
sudo ./deploy/update.sh
```

## Troubleshooting

### "attempt to write a readonly database" (OperationalError)
If you see this error when logging in or saving data, it means the web server doesn't have write permissions to the SQLite database file or the directory it's in.

To fix this, run the following command on your server:
```bash
sudo chown -R www-data:www-data /opt/guestranch
sudo chmod -R 775 /opt/guestranch
```
The installation and update scripts are designed to handle this automatically, but you may need to run it manually if you've made manual changes as root.

## Development

1. Create a virtual environment: `python -m venv venv`
2. Activate it: `source venv/bin/activate` (Linux) or `venv\Scripts\activate` (Windows)
3. Install dependencies: `pip install -r requirements.txt`
4. Run migrations: `python manage.py migrate`
5. Start server: `python manage.py runserver`
