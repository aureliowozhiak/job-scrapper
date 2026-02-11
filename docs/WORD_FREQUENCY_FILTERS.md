# Word Frequency Analysis - Compound Filters

## Overview
The word frequency analysis endpoint now supports compound filtering, allowing users to analyze job title statistics with multiple criteria applied simultaneously.

## API Endpoint

```
GET /api/jobs/analysis/word-frequency
```

## Query Parameters

| Parameter | Type | Default | Description | Example |
|-----------|------|---------|-------------|---------|
| `top_n` | integer | 20 | Number of top results (5-100) | `15` |
| `min_length` | integer | 3 | Minimum word length (2-10) | `3` |
| `ngram_type` | string | `all` | N-gram filter: `1`, `2`, `3`, or `all` | `2` |
| `source` | string | None | Filter by job source | `RemoteOK` |
| `date_from` | string | None | Start date (ISO format) | `2026-02-10` |
| `date_to` | string | None | End date (ISO format) | `2026-02-15` |

## Response Schema

```json
{
  "single_words": [
    {"text": "engineer", "count": 282},
    {"text": "data", "count": 251}
  ],
  "two_word_phrases": [
    {"text": "software engineer", "count": 45},
    {"text": "data scientist", "count": 32}
  ],
  "three_word_phrases": [
    {"text": "machine learning engineer", "count": 18}
  ]
}
```

## Usage Examples

### 1. Get All N-grams (Default)
```bash
curl "http://localhost:8000/api/jobs/analysis/word-frequency?top_n=15"
```

### 2. Filter by N-gram Type

**Single Words Only:**
```bash
curl "http://localhost:8000/api/jobs/analysis/word-frequency?ngram_type=1&top_n=15"
```

**Two-Word Phrases Only:**
```bash
curl "http://localhost:8000/api/jobs/analysis/word-frequency?ngram_type=2&top_n=15"
```

**Three-Word Phrases Only:**
```bash
curl "http://localhost:8000/api/jobs/analysis/word-frequency?ngram_type=3&top_n=15"
```

### 3. Filter by Source
```bash
curl "http://localhost:8000/api/jobs/analysis/word-frequency?source=RemoteOK&top_n=15"
```

### 4. Filter by Date Range
```bash
# Jobs from Feb 10, 2026 onwards
curl "http://localhost:8000/api/jobs/analysis/word-frequency?date_from=2026-02-10&top_n=15"

# Jobs up to Feb 15, 2026
curl "http://localhost:8000/api/jobs/analysis/word-frequency?date_to=2026-02-15&top_n=15"

# Jobs between dates
curl "http://localhost:8000/api/jobs/analysis/word-frequency?date_from=2026-02-10&date_to=2026-02-15&top_n=15"
```

### 5. Compound Filters
```bash
# 2-word phrases from RemoteOK posted after Feb 10
curl "http://localhost:8000/api/jobs/analysis/word-frequency?source=RemoteOK&date_from=2026-02-10&ngram_type=2&top_n=15"

# Single words from SkipTheDrive in date range
curl "http://localhost:8000/api/jobs/analysis/word-frequency?source=SkipTheDrive&date_from=2026-02-09&date_to=2026-02-11&ngram_type=1&top_n=15"
```

## Frontend UI

### Filter Controls
The word frequency panel includes the following filter controls:

1. **N-gram Type Dropdown**
   - Options: All Types, Single Words Only, 2-Word Phrases Only, 3-Word Phrases Only
   - Default: All Types

2. **Source Dropdown**
   - Auto-populated from available job sources
   - Options: All Sources, SkipTheDrive, RemoteOK, Remotive, etc.
   - Default: All Sources

3. **Date From Input**
   - HTML5 date picker
   - Format: YYYY-MM-DD

4. **Date To Input**
   - HTML5 date picker
   - Format: YYYY-MM-DD

5. **Clear Filters Button**
   - Resets all filters to default values
   - Triggers automatic refresh

### Behavior
- Changing any filter automatically refreshes the statistics
- Source dropdown is populated dynamically from actual job data
- Invalid dates are gracefully ignored
- All filters work together (compound filtering)

## Implementation Details

### Backend Changes
**File:** `src/api/routes/jobs.py`

1. Added filter parameters to endpoint
2. Implemented query filtering for source and date range
3. Added n-gram type filtering logic
4. Ensured filters apply consistently in both extraction and counting phases

### Frontend Changes
**File:** `templates/index.html`

1. Added filter control panel with responsive grid layout
2. Implemented `loadWordStatistics()` with query parameter building
3. Added `clearWordFilters()` function
4. Added `populateSourceFilter()` function for dynamic source options
5. Enhanced `loadAllJobs()` to populate source filter on load

### Testing
**File:** `tests/unit/test_word_frequency.py`

Added tests for:
- N-gram type filtering
- Source filtering
- Date filtering
- Compound filters

## Performance Considerations

1. **Query Optimization**: Filters reduce the dataset size before n-gram extraction
2. **Index Usage**: Source and created_at columns are indexed for faster filtering
3. **Caching**: Consider caching common filter combinations for frequently accessed data
4. **Pagination**: Top N limiting prevents excessive data transfer

## Future Enhancements

1. **Company Filter**: Add filtering by company name
2. **Advanced Date Ranges**: Add preset options (Last 7 days, Last 30 days, etc.)
3. **Export**: Add CSV/JSON export of filtered results
4. **Visualization**: Add charts for visual representation of trends
5. **Saved Filters**: Allow users to save and reuse filter combinations

## Notes

- Empty results (0 jobs matching filters) return empty arrays for all n-gram types
- Invalid date formats are silently ignored (no error thrown)
- Case-insensitive matching for source filter
- Consecutive words only counted within same segment (no cross-punctuation phrases)
