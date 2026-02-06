# Dashboard Structure

## New Tab Layout

```
┌─────────────────────────────────────────────────────────────┐
│  🚀 Job Scrapper Pro                    [Status Badges]     │
│  ─────────────────────────────────────────────────────────  │
│  📊 Dashboard  |  ⚙️ Task Manager  |  📋 Browse Jobs       │
└─────────────────────────────────────────────────────────────┘
```

### Tab 1: 📊 Dashboard
**Purpose:** Overview and data pipeline controls

```
┌─────────────────────────────────────────────────────────────┐
│  Statistics                                                  │
│  ┌────────┐  ┌────────┐  ┌────────┐                         │
│  │ Total  │  │ Comp.  │  │ Sites  │                         │
│  │ Jobs   │  │        │  │ Mon.   │                         │
│  └────────┘  └────────┘  └────────┘                         │
│                                                              │
│  ☁️ Data Management Controls                                │
│  [🔄 Update] [📥 Scrape] [💾 Load] [🔍 Validate] [⚡ Sync]  │
│                                                              │
│  Sync Status Panel (when available)                         │
└─────────────────────────────────────────────────────────────┘
```

### Tab 2: ⚙️ Task Manager (NEW!)
**Purpose:** Real-time job monitoring and lifecycle management

```
┌─────────────────────────────────────────────────────────────┐
│  ⚙️ Task Lifecycle Management                               │
│                                                              │
│  Queue Statistics (Auto-updates every 2s via WebSocket)     │
│  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐           │
│  │ ⏳ 0    │  │ ▶️ 1   │  │ ✅ 15  │  │ ❌ 2   │           │
│  │ Queued │  │ Running│  │ Done   │  │ Failed │           │
│  └────────┘  └────────┘  └────────┘  └────────┘           │
│                                                              │
│  [🔄 Refresh] [🗑️ Clear Failed]                             │
│                                                              │
│  ▶️ Active Jobs                                             │
│  ┌──────────────────────────────────────────────┐          │
│  │ scraper-20260205220130             [🛑 Cancel]│          │
│  │ Status: started | Started: 22:01:30           │          │
│  └──────────────────────────────────────────────┘          │
│                                                              │
│  ❌ Failed Jobs                                             │
│  ┌──────────────────────────────────────────────┐          │
│  │ loader-20260205215500                         │          │
│  │ Failed at: 21:56:45                           │          │
│  │ ▸ Error Details (expandable)                 │          │
│  └──────────────────────────────────────────────┘          │
└─────────────────────────────────────────────────────────────┘
```

### Tab 3: 📋 Browse Jobs
**Purpose:** Search and view all jobs (unchanged)

```
┌─────────────────────────────────────────────────────────────┐
│  [Filter input.....................] [Filter] [Clear]       │
│                                                              │
│  Job listings with pagination                               │
│  ┌──────────────────────────────────────────────┐          │
│  │ Senior Python Developer                       │          │
│  │ 🏢 Company X | 📅 2026-02-05 | 🔗 Ver Vaga   │          │
│  └──────────────────────────────────────────────┘          │
│                                                              │
│  [←] [1] [2] [3] [→]                                        │
└─────────────────────────────────────────────────────────────┘
```

## Key Improvements

### Before:
- ❌ Search tab with limited functionality (duplicate of Browse filters)
- ❌ No visibility into job queue status
- ❌ No way to monitor running jobs
- ❌ No way to cancel jobs from UI
- ❌ Failed jobs just accumulated

### After:
- ✅ Streamlined interface (2 tabs instead of 3)
- ✅ Real-time job monitoring with WebSocket
- ✅ Job lifecycle management (view, cancel, cleanup)
- ✅ Error debugging with full stack traces
- ✅ Better separation of concerns

## User Workflows

### Monitoring Pipeline Execution
1. Click "Update" in Dashboard tab
2. Switch to Task Manager tab
3. Watch jobs progress in real-time
4. See when each stage completes

### Debugging Failed Jobs
1. Go to Task Manager tab
2. Check Failed Jobs section
3. Expand "Error Details" for any failed job
4. View full stack trace
5. Fix the issue
6. Click "Clear Failed" to clean up

### Managing Long-Running Jobs
1. Monitor Active Jobs in Task Manager
2. If job is stuck or taking too long
3. Click "Cancel" button
4. Job will be terminated

## Technical Implementation

### WebSocket Connection
```javascript
// Auto-connects when Task Manager tab is active
const wsUrl = `ws://localhost:8000/ws/status`;
taskWebSocket = new WebSocket(wsUrl);

// Receives updates every 2 seconds
taskWebSocket.onmessage = (data) => {
  updateQueueStatus(data.queue_status);
}
```

### API Integration
```javascript
// Fetch job details
GET /api/admin/job/{job_id}

// Cancel job
DELETE /api/admin/job/{job_id}

// Clear failed jobs
DELETE /api/admin/queue/failed

// Get queue status
GET /api/admin/queue/status
```

