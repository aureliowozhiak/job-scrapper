# Word Frequency Filter Architecture

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     USER INTERFACE                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ N-gram   │  │  Source  │  │Date From │  │ Date To  │   │
│  │ Dropdown │  │ Dropdown │  │  Input   │  │  Input   │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘   │
│       │             │             │             │           │
│       └─────────────┴─────────────┴─────────────┘           │
│                          │                                   │
│                          ▼                                   │
│              [ Clear Filters Button ]                       │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           │ onChange event triggers
                           ▼
            ┌──────────────────────────────┐
            │  loadWordStatistics()        │
            │  - Build query parameters    │
            │  - Append filters to URL     │
            └──────────────┬───────────────┘
                           │
                           │ HTTP GET Request
                           ▼
┌──────────────────────────────────────────────────────────────┐
│              BACKEND API ENDPOINT                            │
│  GET /api/jobs/analysis/word-frequency                       │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ Query Parameters:                                       │ │
│  │  • ngram_type: 1 | 2 | 3 | all                         │ │
│  │  • source: string (optional)                           │ │
│  │  • date_from: ISO date (optional)                      │ │
│  │  • date_to: ISO date (optional)                        │ │
│  │  • top_n: integer (5-100)                              │ │
│  └────────────────────────────────────────────────────────┘ │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
            ┌──────────────────────────────┐
            │   DATABASE QUERY BUILDER     │
            │                              │
            │  query = db.query(Position)  │
            │                              │
            │  if source:                  │
            │    .filter(source.ilike(...))│
            │                              │
            │  if date_from:               │
            │    .filter(created_at >= ...) │
            │                              │
            │  if date_to:                 │
            │    .filter(created_at <= ...) │
            └──────────────┬───────────────┘
                           │
                           ▼
            ┌──────────────────────────────┐
            │   N-GRAM EXTRACTION          │
            │                              │
            │  for each position:          │
            │    if process_1gram:         │
            │      extract single words    │
            │    if process_2gram:         │
            │      extract 2-word phrases  │
            │    if process_3gram:         │
            │      extract 3-word phrases  │
            └──────────────┬───────────────┘
                           │
                           ▼
            ┌──────────────────────────────┐
            │   COUNT MATCHING JOBS        │
            │                              │
            │  for each n-gram:            │
            │    count = query             │
            │      .filter(title.ilike())  │
            │      .filter(source...)       │
            │      .filter(date...)         │
            │      .count()                │
            └──────────────┬───────────────┘
                           │
                           ▼
            ┌──────────────────────────────┐
            │   SORT & RETURN TOP N        │
            │                              │
            │  single_words: top N         │
            │  two_word_phrases: top N     │
            │  three_word_phrases: top N   │
            └──────────────┬───────────────┘
                           │
                           │ JSON Response
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                   FRONTEND RENDERING                         │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  renderWordStatistics(data)                            │ │
│  │  - Display single words in first column                │ │
│  │  - Display 2-word phrases in second column             │ │
│  │  - Display 3-word phrases in third column              │ │
│  │  - Each word/phrase is clickable to filter jobs        │ │
│  │  - Bar charts show relative frequency                  │ │
│  └────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

## Filter Combination Logic

### Scenario 1: All Filters Applied
```
User Input:
  ngram_type = "2"
  source = "RemoteOK"
  date_from = "2026-02-10"
  date_to = "2026-02-15"

Result:
  → Only 2-word phrases
  → Only from RemoteOK jobs
  → Only jobs created between Feb 10-15, 2026
```

### Scenario 2: Partial Filters
```
User Input:
  ngram_type = "all"
  source = "SkipTheDrive"
  date_from = null
  date_to = null

Result:
  → All n-gram types (1, 2, 3)
  → Only from SkipTheDrive jobs
  → All dates included
```

### Scenario 3: No Filters (Default)
```
User Input:
  ngram_type = "all"
  source = null
  date_from = null
  date_to = null

Result:
  → All n-gram types
  → All sources
  → All dates
  → (Same as previous behavior)
```

## Performance Optimization

### Query Execution Order
```
1. Apply filters to reduce dataset
   ├─ Source filter (indexed column)
   ├─ Date range filter (indexed column)
   └─ Result: Smaller dataset for processing

2. Extract n-grams from filtered dataset
   └─ Only process relevant jobs

3. Count matches with same filters
   └─ Consistent results across extraction and counting

4. Sort and limit to top N
   └─ Return minimal payload
```

### Index Usage
```sql
-- Indexes used by filters
CREATE INDEX idx_positions_source ON positions(source);
CREATE INDEX idx_positions_created_at ON positions(created_at);
CREATE INDEX idx_positions_title ON positions(title);
```

## Filter State Management

### Frontend State
```javascript
// Filter values stored in DOM
const filters = {
  ngram: document.getElementById('wordFilterNgram').value,
  source: document.getElementById('wordFilterSource').value,
  dateFrom: document.getElementById('wordFilterDateFrom').value,
  dateTo: document.getElementById('wordFilterDateTo').value
};

// Query parameters built dynamically
const params = new URLSearchParams({ top_n: 15 });
if (filters.ngram !== 'all') params.append('ngram_type', filters.ngram);
if (filters.source) params.append('source', filters.source);
if (filters.dateFrom) params.append('date_from', filters.dateFrom);
if (filters.dateTo) params.append('date_to', filters.dateTo);
```

### Backend Validation
```python
# Query parameter validation
ngram_type: Optional[str] = Query(None, regex="^(1|2|3|all)$")
source: Optional[str] = Query(None)
date_from: Optional[str] = Query(None)  # ISO format
date_to: Optional[str] = Query(None)    # ISO format

# Invalid dates silently ignored (graceful degradation)
try:
    date_from_obj = dt.fromisoformat(date_from.replace('Z', '+00:00'))
except ValueError:
    pass  # Continue without date filter
```

## Error Handling

### Invalid Filter Values
```
Invalid ngram_type → Returns 422 Unprocessable Entity
Invalid date format → Silently ignored (filter not applied)
Empty source → Treated as "no filter" (all sources)
top_n out of range → Returns 422 Unprocessable Entity
```

### Edge Cases
```
No jobs match filters → Returns empty arrays
All n-grams filtered out → Returns appropriate empty type arrays
Database connection error → Returns 500 Internal Server Error
```
