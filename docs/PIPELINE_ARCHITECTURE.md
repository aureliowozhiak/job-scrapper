# Pipeline Architecture

## Overview

The Sherlock Jobs pipeline consists of **2 main stages**:

1. **Scraper** - Scrapes job data from multiple sources and loads directly to database
2. **Validator** - Validates job entries in the database

## Why No Separate Loader?

Previously, the pipeline had 3 stages: Scraper → Loader → Validator.

**The loader stage has been integrated into the scraper** for better efficiency:

- **Before**: Scraper saved JSON files → Loader read JSON files → Database
- **After**: Scraper saves directly to database (faster, more reliable)

### Benefits

1. **Faster execution**: No intermediate JSON file I/O
2. **Better reliability**: Single transaction, no orphaned files
3. **Simpler architecture**: Less moving parts
4. **Atomic operations**: Scrape and load happen together

## Pipeline Flow

```
┌──────────┐         ┌───────────┐
│  Scraper │────────▶│ Validator │
└──────────┘         └───────────┘
     │
     ▼
  Database
```

### Scraper Stage
- Runs 4 spiders in parallel (SkipTheDrive, WeWorkRemotely, RemoteOK, Remotive)
- Each spider processes 20 search queries
- Jobs are normalized and loaded directly to database
- Duplicates are detected and skipped
- Returns stats: `jobs_scraped`, `jobs_loaded`, `duplicates`, `errors`

### Validator Stage
- Validates job URLs are still active
- Removes dead listings
- Returns stats: `total_checked`, `valid`, `removed`

## API Endpoints

### Trigger Full Pipeline
```bash
POST /api/admin/pipeline
{
  "query": "data engineer",
  "region": "remote"
}
```

### Trigger Individual Tasks
```bash
# Scrape only (includes loading)
POST /api/admin/scrape

# Validate only
POST /api/admin/validate
```

## Background Jobs

Tasks are managed by **RQ (Redis Queue)**:
- Jobs run asynchronously in worker processes
- Progress is tracked via WebSocket
- Failed jobs can be retried
- Job timeouts prevent hung processes

## Stats Response

Pipeline returns comprehensive stats:

```json
{
  "queries_processed": 40,
  "jobs_scraped": 1075,
  "jobs_loaded": 8,
  "duplicates": 1067,
  "errors": 0,
  "spiders": {
    "skipthedrive_jobs": {
      "jobs_scraped": 60,
      "jobs_loaded": 0,
      "duplicates": 60,
      "errors": 0,
      "queries": 20
    },
    ...
  }
}
```

## Legacy Loader Task

The `task_loader` still exists for backwards compatibility but is **not used in the pipeline**.

If you need to load jobs from JSON files manually, you can still call:
```bash
POST /api/admin/load
```

This is useful for:
- Importing historical data
- Recovering from backup JSON files
- Testing the load process independently
