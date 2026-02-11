# Load Statistics Guide

## Understanding Load Task Statistics

When the **Load** task completes, it provides detailed statistics about the job loading process. This document explains what each field means.

### Statistics Fields

#### Overview Fields

- **`total_found`**: Total number of jobs found in all JSON files for this pipeline run
- **`inserted`**: Number of NEW jobs successfully inserted into the database
- **`db_new_jobs`**: Confirmation of how many new records were added (should match `inserted`)

#### Deduplication Fields

- **`unique_in_batch`**: Number of unique jobs after removing duplicates within the same batch
- **`batch_duplicates`**: Jobs that appeared multiple times within the scraped files
- **`db_duplicates`**: Jobs that already existed in the database (not inserted again)
- **`total_skipped`**: Total jobs skipped (batch_duplicates + db_duplicates)

#### Database Counts

- **`db_before`**: Total jobs in database before loading
- **`db_after`**: Total jobs in database after loading
- **`db_new_jobs`**: Net increase in database size (db_after - db_before)

#### Quality Fields

- **`errors`**: Jobs that failed to load due to validation errors (e.g., missing title/company)
- **`pre_rejected`**: Jobs rejected during pre-validation sampling
- **`summary`**: Human-readable summary of the load operation

### Example Interpretation

```json
{
  "total_found": 1583,
  "unique_in_batch": 124,
  "batch_duplicates": 1459,
  "inserted": 4,
  "db_duplicates": 120,
  "total_skipped": 1579,
  "errors": 0,
  "pre_rejected": 0,
  "db_before": 714,
  "db_after": 718,
  "db_new_jobs": 4,
  "summary": "Found 1583 jobs: 4 new, 120 already in DB, 1459 within-batch duplicates"
}
```

**What this means:**
1. Scraper found 1583 total job listings across all files
2. After removing duplicates within the batch: 124 unique jobs remained
3. Of those 124 unique jobs:
   - 4 were NEW and inserted into the database
   - 120 already existed in the database (skipped)
4. The remaining 1459 jobs were duplicates within the scraped files themselves
5. Database grew from 714 → 718 jobs (net +4 new jobs)

### Why So Many Duplicates?

It's normal to see high duplicate counts because:

1. **Scrapers run multiple search queries** - Different queries may return overlapping results
   - Example: "data engineer" and "senior data engineer" may return some of the same jobs
2. **Multiple job boards** - The same company may post the same job on multiple platforms
3. **Previous runs** - If you run the pipeline multiple times, already-scraped jobs will show as db_duplicates
4. **De-duplication strategy** - We use job link (URL) as the unique identifier

### Troubleshooting

#### "All jobs are duplicates"
- **Cause**: You're running the pipeline on the same sources repeatedly
- **Solution**: This is expected behavior! The database preserves existing jobs and only adds new ones

#### "Inserted count doesn't match db_new_jobs"
- **Cause**: Potential database error or race condition
- **Solution**: Check application logs for errors during commit

#### "High error rate"
- **Cause**: Jobs missing required fields (title, company, link)
- **Solution**: Review scraper output quality and transformation logic

### Technical Details

The load process follows this flow:

```
1. Read all JSON files from output directory
2. Flatten nested lists
3. Pre-validation sampling (first N jobs)
4. Deduplicate within batch (by link/URL)
5. Check against existing database records
6. Insert only NEW, unique jobs
7. Report comprehensive statistics
```

Link-based deduplication ensures we never create duplicate database records, even if scrapers return the same job multiple times.

### Related Documentation

- [Pipeline Architecture](./PIPELINE_ARCHITECTURE.md) (if exists)
- [Scraper Configuration](./SCRAPER_CONFIG.md) (if exists)
- [Database Schema](./DATABASE_SCHEMA.md) (if exists)
