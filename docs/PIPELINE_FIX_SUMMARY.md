# Pipeline Fix: Loader Task Returns Zero Stats

## Problem

When running the full pipeline, the **loader task was returning zero processed/inserted jobs** even though the scraper successfully scraped 1075 jobs:

**Scraper output:**
```json
{
  "jobs_scraped": 1075,
  "jobs_loaded": 8,
  "duplicates": 1067
}
```

**Loader output:**
```json
{
  "processed": 0,
  "inserted": 0,
  "duplicates": 0
}
```

## Root Cause

**The loader task was redundant** because the scraper already loads data to the database:

1. **Scraper (`task_scraper`)** calls `run_integrated_scraper()` which:
   - Scrapes jobs to temporary JSON files
   - **Loads jobs directly to database via `load_jobs_to_database()`**
   - Returns scraping + loading stats

2. **Loader (`task_loader`)** calls `run_load_process()` which:
   - Looks for JSON files in `data/output/{year}/{month}/{day}/`
   - Reads and loads those files
   - **But the scraper uses temp files that are deleted immediately!**

**Result:** Loader has no files to process, returns zero stats.

## Solution

**Removed the loader step from the pipeline** since it's redundant:

### Code Changes

1. **`src/jobs/manager.py`** - Updated `enqueue_pipeline()`:
   - **Before:** 3 steps (scraper → loader → validator)
   - **After:** 2 steps (scraper → validator)

2. **`src/api/routes/admin.py`** - Updated pipeline response:
   - Changed `steps=["scraper", "loader", "validator"]`
   - To `steps=["scraper", "validator"]`

3. **`README.md`** - Updated pipeline documentation

### Why This Works

- **Scraper already loads data:** No need for separate loader
- **Faster:** Eliminates redundant I/O operations
- **More reliable:** Single atomic operation (scrape + load)
- **Cleaner architecture:** Less moving parts

### Backward Compatibility

The `task_loader` still exists for:
- Manual loading from backup JSON files
- Historical data imports
- Independent testing

You can still trigger it via: `POST /api/admin/load`

## Verification

Test that pipeline now has 2 steps:
```python
from src.jobs.manager import JobManager
jm = JobManager()
job_ids = jm.enqueue_pipeline()
# Returns: ['pipeline-scraper-XXX', 'pipeline-validator-XXX']
```

## Impact

✅ **Fixed:** Loader no longer returns confusing zero stats  
✅ **Improved:** Pipeline is faster and more reliable  
✅ **Simplified:** 2-step pipeline instead of 3  
✅ **Maintained:** Can still manually trigger loader if needed  

## Files Modified

- `src/jobs/manager.py` - Removed loader from pipeline
- `src/api/routes/admin.py` - Updated pipeline steps
- `README.md` - Updated API documentation
- `docs/PIPELINE_ARCHITECTURE.md` - Added architecture documentation
