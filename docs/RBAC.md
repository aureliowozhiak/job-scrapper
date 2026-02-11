# Role-Based Access Control (RBAC)

## Overview

Sherlock Jobs implements session-based authentication to protect admin endpoints.

## Quick Start

1. **Default credentials**:
   - Username: `admin`
   - Password: `admin123`
   - **⚠️ CHANGE IN PRODUCTION!**

2. **Generate new password**:
   ```bash
   python scripts/generate_password_hash.py YourSecurePassword
   ```

3. **Update .env**:
   ```bash
   ADMIN_USERNAME=admin
   ADMIN_PASSWORD_HASH=<hash-from-step-2>
   SESSION_SECRET_KEY=<random-string>
   ```

## Protected Endpoints

All `/api/admin/*` endpoints require authentication:
- `POST /api/admin/scrape`
- `POST /api/admin/load`
- `POST /api/admin/validate`
- `POST /api/admin/pipeline`
- `POST /api/admin/sync`

## Login/Logout

- **Login**: `POST /login` (form: username, password)
- **Logout**: `POST /logout`
- Sessions expire after 24 hours

## Security

Production checklist:
- [ ] Change default password
- [ ] Use strong session secret (32+ random characters)
- [ ] Enable HTTPS
- [ ] Set strong password policy

