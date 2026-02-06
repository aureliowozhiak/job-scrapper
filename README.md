# 🚀 Job Scrapper Pro v3.0

Modern job scraping application built with FastAPI, SQLAlchemy, and RQ (Redis Queue) for reliable background job processing.

## ✨ Features

- **🔍 Multi-site Scraping**: Automated scraping from 4 job boards (SkipTheDrive, WeWorkRemotely, RemoteOK, Remotive)
  - **NEW**: WeWorkRemotely using Playwright to bypass Cloudflare ✨
  - **NEW**: RemoteOK and Remotive using JSON APIs for fast data collection 🚀
- **💾 Smart Data Management**: SQLAlchemy ORM with upsert capabilities
- **⚡ Background Jobs**: Redis-backed job queue with RQ
- **🎯 Data Validation**: Automatic link validation and cleanup
- **🔄 Sync Analysis**: Compare local data with database before loading
- **📊 Interactive Dashboard**: Modern web UI with Job Feed, Task Manager, and Health Monitor
- **❤️ Health Monitoring**: Real-time system health dashboard with scraper metrics ✨ **NEW**
- **🔧 REST API**: Full-featured API with auto-generated documentation
- **🐳 Docker Ready**: Complete Docker Compose setup
- **🎭 Browser Automation**: Playwright integration for JavaScript-heavy sites

## 🏗️ Architecture

```
├── src/
│   ├── api/          # FastAPI routes and application
│   ├── core/         # Configuration and settings
│   ├── database/     # SQLAlchemy models and repositories
│   ├── jobs/         # RQ background tasks
│   └── schemas/      # Pydantic validation schemas
├── templates/        # Jinja2 templates
├── data/            # Data directory (created automatically)
│   ├── db/          # SQLite database
│   ├── output/      # Scraped JSON files
│   ├── lake/        # Raw HTML
│   └── logs/        # Application logs
└── worker.py        # RQ worker entry point
```

## 🐳 Quick Start with Docker (Recommended)

```bash
# 1. Copy environment config
cp .env.example .env

# 2. Start all services
docker-compose up -d

# 3. Access the application
# Web UI: http://localhost:8000
# API Docs: http://localhost:8000/api/docs
# RQ Dashboard: http://localhost:9181
```

**That's it!** See [DOCKER_GUIDE.md](DOCKER_GUIDE.md) for detailed Docker usage.

## 💻 Local Development Setup

### Prerequisites
- Python 3.11+
- Redis Server

### Installation

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start Redis
docker run -d -p 6379:6379 redis:7-alpine
# OR if installed locally: redis-server

# 3. Initialize database
python -c "from src.database.connection import init_db; init_db()"

# 4. Start FastAPI (Terminal 1)
python -m uvicorn src.api.main:app --reload

# 5. Start RQ Worker (Terminal 2)
python worker.py
```

Access at http://localhost:8000

## 📖 Documentation

- **[Docker Guide](DOCKER_GUIDE.md)** - Complete Docker setup and usage
- **[Migration Summary](MIGRATION_SUMMARY.md)** - Flask to FastAPI migration details
- **[Roadmap](ROADMAP.md)** - Project roadmap and future plans
- **[Playwright Implementation](PLAYWRIGHT_IMPLEMENTATION.md)** - Browser automation setup
- **[WeWorkRemotely Status](WEWORKREMOTELY_STATUS.md)** - WeWorkRemotely scraper investigation
- **[Test Coverage](TEST_COVERAGE_ACHIEVEMENT.md)** - Comprehensive testing strategy
- **[API Docs](http://localhost:8000/api/docs)** - Interactive API documentation (when running)

## 🎯 Usage

### Web Interface

Visit http://localhost:8000 and use the dashboard to:
- **Job Feed Tab**: View all job listings with search, filter, and sort capabilities
- **Task Manager Tab**: 
  - Trigger pipeline operations (Full Pipeline, Scrape, Load, Validate, Sync Check)
  - Monitor real-time job queue status (queued, running, finished, failed)
  - View and manage active jobs
  - View failed jobs with error details
  - Clear failed jobs from queue
- **Health Monitor Tab** ✨ **NEW**:
  - Real-time system health dashboard
  - Monitor Database, Redis, and Queue status
  - Track individual scraper performance and success rates
  - View 24-hour activity metrics
  - Instant health status indicators (healthy/degraded/unhealthy)

### API Endpoints

#### Health Monitoring ✨ **NEW**
```bash
# Get comprehensive health dashboard
GET /api/health/dashboard

# Check database health
GET /api/health/db

# Check Redis health
GET /api/health/redis

# Basic health check
GET /api/health/
```

#### Job Search & Listing
```bash
# Search jobs
GET /api/jobs/search?q=python&limit=50

# List all jobs with filters
GET /api/jobs/?company=Google&limit=100

# Get statistics
GET /api/jobs/stats
```

#### Admin/Control
```bash
# Trigger scraping
POST /api/admin/scrape

# Trigger full pipeline (scrape -> load -> validate)
POST /api/admin/pipeline

# Check job status
GET /api/admin/job/{job_id}

# Get queue status
GET /api/admin/queue/status
```

#### Health Checks
```bash
# Overall health
GET /api/health

# Database health
GET /api/health/db

# Redis health
GET /api/health/redis
```

## 🔧 Configuration

Edit `.env` file (copy from `.env.example`):

```env
# Application
DEBUG=false

# Server
HOST=0.0.0.0
PORT=8000

# Database
DATABASE_URL=sqlite:///./data/db/jobs.db

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# Validation
ENABLE_PRE_VALIDATION=true
VALIDATION_SAMPLE_SIZE=100
```

## 🕷️ Active Scrapers

The application currently supports 4 job boards:

| Scraper | Domain | Method | Status |
|---------|--------|--------|--------|
| **SkipTheDrive** | skipthedrive.com | HTML Scraping | ✅ Active |
| **WeWorkRemotely** | weworkremotely.com | Playwright (Browser) | ✅ Active |
| **RemoteOK** | remoteok.com | JSON API | ✅ Active |
| **Remotive** | remotive.com | JSON API | ✅ Active |

All scrapers are monitored in real-time via the Health Monitor dashboard.

## 📊 Monitoring

### Health Monitor Dashboard ✨ **NEW**
Access the comprehensive health dashboard at http://localhost:8000 (Health Monitor tab) to view:
- **System Health**: Overall status (healthy/degraded/unhealthy)
- **Component Status**: Database, Redis, and Queue health
- **Scraper Metrics**: Per-scraper performance and success rates
- **24h Activity**: Recent scraping activity and job counts
- **Success Rates**: Visual progress bars showing scraper reliability

### RQ Dashboard
When running with Docker, access the RQ Dashboard at http://localhost:9181 to monitor:
- Queue status
- Running jobs
- Completed jobs
- Failed jobs
- Worker health

### Queue Status API
```bash
curl http://localhost:8000/api/admin/queue/status
```

### Health Check API
```bash
# Comprehensive health dashboard
curl http://localhost:8000/api/health/dashboard

# Individual component checks
curl http://localhost:8000/api/health/db
curl http://localhost:8000/api/health/redis
```

## 🧪 Testing

### Run All Tests
```bash
# Run all tests
pytest

# With coverage report
pytest --cov=src --cov=methods --cov=utils --cov-report=html

# View coverage report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

### Test Categories
```bash
# Unit tests only
pytest tests/unit/

# Integration tests only
pytest tests/integration/

# Specific module
pytest tests/test_load.py -v
pytest tests/test_validate.py -v
```

### In Docker
```bash
docker-compose run --rm api pytest --cov=src --cov=methods --cov=utils
```

### Coverage Goals
- **Target**: 95%+ coverage
- **Critical modules**: 95%+ (load, validate, repositories, API)
- **Utility modules**: 100% (utils, logger)

See [TEST_COVERAGE_PLAN.md](TEST_COVERAGE_PLAN.md) for detailed coverage strategy.

## 📦 Technology Stack

- **FastAPI** - Modern web framework
- **SQLAlchemy 2.0** - SQL toolkit and ORM
- **RQ (Redis Queue)** - Background job processing
- **Pydantic** - Data validation
- **Redis** - Job queue backend
- **Uvicorn** - ASGI server
- **Jinja2** - Template engine
- **BeautifulSoup4** - HTML parsing
- **Scrapy** - Web scraping framework

## 🔄 Background Job Flow

1. **Trigger**: API receives request to start a job
2. **Enqueue**: Job is added to Redis queue with unique ID
3. **Process**: RQ worker picks up the job and executes it
4. **Monitor**: Check status via API or RQ Dashboard
5. **Complete**: Results stored and available via API

Jobs support:
- ✅ Dependencies (pipeline execution)
- ✅ Retries on failure
- ✅ Timeout handling
- ✅ Result persistence

## 🚨 Troubleshooting

### Redis Connection Error
```bash
# Check if Redis is running
redis-cli ping  # Should return PONG

# Start Redis with Docker
docker run -d -p 6379:6379 redis:7-alpine
```

### Worker Not Processing Jobs
```bash
# Check worker logs
python worker.py

# Check queue length
redis-cli LLEN rq:queue:default
```

### Database Errors
```bash
# Reinitialize database
rm data/db/jobs.db
python -c "from src.database.connection import init_db; init_db()"
```

See [DOCKER_GUIDE.md](DOCKER_GUIDE.md) for more troubleshooting tips.

## 📝 Development

### Project Structure
- `src/api/routes/` - Add new API endpoints here
- `src/jobs/` - Add new background tasks here
- `src/database/models.py` - Define database models
- `src/schemas/` - Define Pydantic schemas
- `templates/` - HTML templates

### Adding a New Background Task

1. Create task file in `src/jobs/task_*.py`
2. Add enqueue method in `src/jobs/manager.py`
3. Create API endpoint in `src/api/routes/admin.py`
4. Test with RQ Dashboard

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

MIT License

## 🔗 Links

- **Live Demo**: N/A
- **API Documentation**: http://localhost:8000/api/docs (when running)
- **RQ Dashboard**: http://localhost:9181 (when running with Docker)

---

**Built with ❤️ using FastAPI and modern Python practices**