# Role-Based Access Control (RBAC) Documentation

## Overview

This implementation adds comprehensive role-based access control to the Job Scrapper application using FastAPI, providing secure authentication and authorization for administrative functions.

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Copy the example environment file and configure it:

```bash
cp .env.example .env
```

Generate a password hash:

```bash
python -c "from passlib.hash import bcrypt; print(bcrypt.hash('your_admin_password'))"
```

Generate a session secret key:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Update `.env` with your values:

```env
ADMIN_ENABLED=true
ADMIN_USERNAME=admin
ADMIN_PASSWORD_HASH=<your_generated_hash>
SESSION_SECRET_KEY=<your_generated_key>
DATABASE_URL=sqlite:///./jobs.db
```

### 3. Run the Application

```bash
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

The application will be available at `http://localhost:8000`

## Architecture

### Directory Structure

```
src/
├── core/
│   ├── __init__.py
│   ├── config.py          # Configuration management
│   ├── auth.py            # Authentication utilities
│   └── permissions.py     # Authorization dependencies
└── api/
    ├── __init__.py
    ├── main.py            # FastAPI application & auth routes
    └── routes/
        ├── __init__.py
        ├── jobs.py        # Public job search endpoints
        ├── admin.py       # Protected admin endpoints
        └── health.py      # Health monitoring endpoints

templates/
└── index.html             # Main UI with conditional rendering
```

### Authentication Flow

1. **Login**: User submits credentials via POST `/api/auth/login`
2. **Verification**: Backend verifies username/password against bcrypt hash
3. **Session**: On success, sets `is_admin=True` in session
4. **Authorization**: Protected endpoints check session via `require_admin` dependency
5. **Logout**: POST `/api/auth/logout` clears session

## API Endpoints

### Public Endpoints (No Authentication Required)

#### Job Search
```http
GET /api/jobs/search?word=<keyword>
```
Search for jobs by keyword in the database.

#### Health Checks
```http
GET /api/health/          # Basic health check
GET /api/health/db        # Database health status
GET /api/health/redis     # Redis health status (if configured)
```

#### Authentication Status
```http
GET /api/auth/status      # Check if user is authenticated
```

### Protected Endpoints (Admin Authentication Required)

#### Authentication
```http
POST /api/auth/login      # Login with username/password (form data)
POST /api/auth/logout     # Logout and clear session
```

#### Admin Operations
```http
POST /api/admin/scrape          # Start web scraping job
POST /api/admin/load            # Load data into database
POST /api/admin/validate        # Validate data integrity
POST /api/admin/sync-check      # Check synchronization status
POST /api/admin/pipeline        # Run full ETL pipeline
DELETE /api/admin/job/{job_id}  # Delete specific job by ID
DELETE /api/admin/queue/failed  # Clear failed jobs queue
GET /api/admin/sources          # Get available data sources
```

#### Health Dashboard
```http
GET /api/health/dashboard  # Detailed statistics (admin only)
```

## Security Features

### Password Security
- **Bcrypt hashing** with work factor 12
- **Salt** automatically generated per password
- **Timing attack protection** via constant-time comparison

### Session Security
- **Secret key** for signing session cookies
- **HTTP-only cookies** (browser cannot access via JavaScript)
- **Session-based authentication** (no JWT token exposure)

### Authorization
- **FastAPI dependencies** for endpoint protection
- **403 Forbidden** for unauthorized access attempts
- **Configurable admin toggle** via `ADMIN_ENABLED` setting

### Input Validation
- **Pydantic models** for request validation
- **SQL parameterization** to prevent injection attacks
- **Context managers** for proper resource cleanup

## User Interface

### Public View
- **Job Feed tab only**: Search and view job listings
- **Admin Login button**: Access to login modal

### Admin View
- **Job Feed tab**: Same as public view
- **Task Manager tab**: Administrative controls
  - Start scraping jobs
  - Load data to database
  - Validate data integrity
  - Run full ETL pipeline
- **Health Monitor tab**: System status
  - Application health
  - Database statistics
  - Redis status
  - Total jobs count
- **Admin badge**: Indicates admin status
- **Logout button**: End admin session

## Configuration Options

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ADMIN_ENABLED` | No | `true` | Enable/disable admin functionality |
| `ADMIN_USERNAME` | No | `admin` | Admin username for login |
| `ADMIN_PASSWORD_HASH` | Yes* | - | Bcrypt hash of admin password |
| `SESSION_SECRET_KEY` | Yes | - | Secret key for session signing |
| `DATABASE_URL` | No | `sqlite:///./jobs.db` | Database connection URL |

\* Required in production (when `debug=False`)

### Security Best Practices

1. **Never commit `.env` file** to version control
2. **Use strong passwords** (12+ characters, mixed case, numbers, symbols)
3. **Rotate session keys** periodically
4. **Use HTTPS** in production
5. **Set secure cookie flags** for production deployment

## Development

### Running Tests

The implementation has been tested for:
- ✅ Authentication flow (login/logout)
- ✅ Admin endpoint protection
- ✅ Public endpoint access
- ✅ UI conditional rendering
- ✅ Database connection handling
- ✅ Security vulnerabilities (CodeQL)

### Adding New Protected Endpoints

To protect a new endpoint with admin authentication:

```python
from fastapi import APIRouter, Depends
from src.core.permissions import require_admin

router = APIRouter()

@router.post("/my-admin-endpoint", dependencies=[Depends(require_admin)])
async def my_admin_function():
    """Protected admin endpoint."""
    return {"message": "Admin access granted"}
```

### Optional Admin Check (for Templates)

To check admin status without requiring it:

```python
from fastapi import Request, Depends
from src.core.permissions import get_optional_admin

@router.get("/")
async def home(request: Request, is_admin: bool = Depends(get_optional_admin)):
    """Render page with admin status."""
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "is_admin": is_admin}
    )
```

## Troubleshooting

### "SESSION_SECRET_KEY must be set"
Generate a secret key and add it to `.env`:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### "Invalid username or password"
Verify your password hash is correct:
```python
from passlib.hash import bcrypt
from src.core.config import settings
print(bcrypt.verify("your_password", settings.admin_password_hash))
```

### Session not persisting
Check that:
1. Session middleware is configured with a secret key
2. Cookies are enabled in the browser
3. The application is not in incognito/private mode

### Database errors
Ensure the `jobs.db` file exists and has the `positions` table:
```bash
sqlite3 jobs.db "SELECT COUNT(*) FROM positions;"
```

## Screenshots

### Public View
Only the Job Feed tab is visible to non-authenticated users.

![Public View](https://github.com/user-attachments/assets/510e775b-55cf-492d-8ae0-95973060eb68)

### Login Modal
Admin login form for authentication.

![Login Modal](https://github.com/user-attachments/assets/fa959d9e-9c0f-46bf-a1ae-2ceb737bda2d)

### Admin View
All three tabs (Job Feed, Task Manager, Health Monitor) visible to authenticated admins.

![Admin View](https://github.com/user-attachments/assets/0c1eceea-f288-46b8-aec6-81582ec0dc64)

### Task Manager
Administrative controls for managing the job scraping pipeline.

![Task Manager](https://github.com/user-attachments/assets/43fc7653-2130-4663-919a-6f8e0a4da72b)

### Health Monitor
System health statistics and monitoring dashboard.

![Health Monitor](https://github.com/user-attachments/assets/fdd6f2b1-5469-49ce-a180-cf41bea70599)

## Migration from Flask

This implementation adds FastAPI alongside the existing Flask application (`api.py`). Both can coexist:

- **FastAPI app** (new): `uvicorn src.api.main:app`
- **Flask app** (existing): `python api.py`

To fully migrate, you can:
1. Port remaining Flask routes to FastAPI
2. Update all frontend code to use FastAPI endpoints
3. Remove the Flask application

## License

Same license as the parent project.
