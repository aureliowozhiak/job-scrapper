# Authentication & Authorization

## Overview

Sherlock Jobs implements role-based access control (RBAC) to protect administrative features. The system uses session-based authentication with bcrypt password hashing.

## Features

### 🔐 Protected Routes
- **Task Manager**: View and manage background job pipelines
- **Health Monitor**: System health and scraper metrics
- **Admin API Endpoints**: All `/api/admin/*` endpoints

### 👤 User Roles
- **Anonymous**: Can view job feed and search jobs
- **Admin**: Full access to all features including task management and health monitoring

## Configuration

### Environment Variables

```bash
# Enable/disable admin authentication
ADMIN_ENABLED=true

# Admin credentials
ADMIN_USERNAME=admin
ADMIN_PASSWORD_HASH=$2b$12$bmV2GuM1uPLENXrQJRRqE.U8pRHDEZkHNOQGVX1t9qUv6pLXiiir6  # admin123

# Session secret (change in production!)
SESSION_SECRET_KEY=change-this-in-production-to-a-secure-random-key
```

### Default Credentials

**Username**: `admin`  
**Password**: `admin123`

⚠️ **Important**: Change these credentials in production!

## How to Use

### Frontend (Web UI)

1. **Login**:
   - Click the "Admin Login" button in the top-right corner
   - Enter your username and password
   - Click "Login"

2. **Access Protected Features**:
   - After login, you'll see your username displayed
   - The "Task Manager" and "Health Monitor" tabs are now enabled
   - Use keyboard shortcuts: `Ctrl+Shift+T` for Tasks, `Ctrl+Shift+H` for Health

3. **Logout**:
   - Click the "Logout" button in the top-right corner
   - You'll be redirected to the home page

### API

#### Login Endpoint

```bash
curl -X POST http://localhost:8000/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123" \
  -c cookies.txt
```

#### Access Protected Endpoints

```bash
# Use the session cookie from login
curl -X POST http://localhost:8000/api/admin/scrape \
  -b cookies.txt
```

#### Logout

```bash
curl -X POST http://localhost:8000/logout \
  -b cookies.txt
```

## Password Management

### Generate New Password Hash

```python
from src.core.auth import hash_password

new_password = "your_secure_password"
hashed = hash_password(new_password)
print(f"Password hash: {hashed}")
```

### Update Password

1. Generate a new password hash using the script above
2. Update the `ADMIN_PASSWORD_HASH` in your `.env` file
3. Restart the application

## Security Features

- ✅ **bcrypt Hashing**: Industry-standard password hashing
- ✅ **Session Management**: Secure cookie-based sessions with 24-hour expiration
- ✅ **CSRF Protection**: SameSite cookie policy
- ✅ **Frontend Protection**: Disabled UI elements for unauthorized users
- ✅ **Backend Protection**: All admin routes require authentication
- ✅ **Keyboard Shortcuts**: Protected tabs require login

## Testing

Run authentication tests:

```bash
# Unit tests
pytest tests/unit/test_auth.py -v

# Integration tests
pytest tests/integration/test_rbac.py -v
pytest tests/integration/test_frontend_auth.py -v
```

## Architecture

### Backend Components

1. **`src/core/auth.py`**: Password hashing and verification utilities
2. **`src/core/permissions.py`**: FastAPI dependencies for route protection
3. **`src/core/config.py`**: Authentication configuration
4. **`src/api/main.py`**: Login/logout endpoints and session middleware

### Frontend Components

1. **Login Modal**: Bootstrap modal with form validation
2. **Session State**: JavaScript checks `is_admin` flag
3. **Tab Protection**: Disabled state for non-authenticated users
4. **Keyboard Shortcuts**: Intercepted for protected routes

### Flow Diagram

```
┌─────────────┐
│   Browser   │
└──────┬──────┘
       │
       ├─── GET / ──────────────────┐
       │                            │
       │                    ┌───────▼────────┐
       │                    │  Main Endpoint │
       │                    │  (No Auth Req) │
       │                    └───────┬────────┘
       │                            │
       │    ◄───────────────────────┘
       │    Template with is_admin=False
       │
       ├─── Click "Admin Login" ───┐
       │                            │
       │    ◄─── Show Modal ────────┘
       │
       ├─── POST /login ────────────┐
       │    (username + password)   │
       │                    ┌───────▼────────┐
       │                    │ Verify Creds   │
       │                    │ Set Session    │
       │                    └───────┬────────┘
       │                            │
       │    ◄───────────────────────┘
       │    Redirect to /?msg=Login+successful
       │
       ├─── GET / ──────────────────┐
       │    (with session cookie)   │
       │                    ┌───────▼────────┐
       │                    │  Main Endpoint │
       │                    │  Read Session  │
       │                    └───────┬────────┘
       │                            │
       │    ◄───────────────────────┘
       │    Template with is_admin=True
       │
       ├─── POST /api/admin/scrape ─┐
       │    (with session cookie)    │
       │                    ┌────────▼───────┐
       │                    │ require_admin  │
       │                    │ Check Session  │
       │                    └────────┬───────┘
       │                             │
       │                    ┌────────▼───────┐
       │                    │ Enqueue Job    │
       │                    └────────┬───────┘
       │                             │
       │    ◄────────────────────────┘
       │    {"job_id": "...", "status": "queued"}
       │
       └─── POST /logout ───────────┐
            (with session cookie)    │
                            ┌────────▼───────┐
                            │ Clear Session  │
                            └────────┬───────┘
                                     │
            ◄───────────────────────┘
            Redirect to /?msg=Logged+out
```

## Troubleshooting

### Issue: "Admin access required. Please login."

**Solution**: Make sure you're logged in and your session hasn't expired (24-hour limit).

### Issue: Can't access admin routes even after login

**Solution**: 
1. Check browser cookies are enabled
2. Verify `SESSION_SECRET_KEY` hasn't changed (would invalidate sessions)
3. Check browser console for errors

### Issue: Password doesn't work

**Solution**:
1. Verify the password hash in config matches the password you're using
2. Default is `admin123` for username `admin`
3. Generate a new hash if needed (see Password Management section)

### Issue: Admin features disabled in UI

**Solution**: The frontend checks the `is_admin` session flag. Ensure:
1. You've successfully logged in
2. Your session cookie is valid
3. The page has been refreshed after login

## Production Deployment

### Security Checklist

- [ ] Change default admin password
- [ ] Generate strong `SESSION_SECRET_KEY`
- [ ] Enable HTTPS
- [ ] Set `HTTPS_ONLY=true` for session cookies
- [ ] Consider adding rate limiting to login endpoint
- [ ] Implement password complexity requirements
- [ ] Add account lockout after failed attempts
- [ ] Enable audit logging for admin actions
- [ ] Use environment variables (never commit secrets)
- [ ] Consider adding 2FA for admin accounts

### Recommended .env Configuration

```bash
ADMIN_ENABLED=true
ADMIN_USERNAME=your_admin_user
ADMIN_PASSWORD_HASH=<generated_hash_here>
SESSION_SECRET_KEY=<random_64_char_string>
```

Generate a secure session key:

```python
import secrets
print(secrets.token_urlsafe(64))
```

## Future Enhancements

- [ ] Multiple user roles (Admin, Viewer, Operator)
- [ ] User management interface
- [ ] JWT token authentication for API
- [ ] OAuth2 integration
- [ ] Two-factor authentication (2FA)
- [ ] Audit logging
- [ ] Password reset functionality
- [ ] Account lockout policies
- [ ] LDAP/Active Directory integration
