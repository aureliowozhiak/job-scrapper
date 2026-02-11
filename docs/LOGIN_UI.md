# Adding Login UI to Dashboard

## Simple Login Form Integration

Add this to your `templates/index.html` to provide a login interface:

### Option 1: Modal Dialog

```html
<!-- Add this near the top of your template, inside <body> -->
<div id="loginModal" style="display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.5); z-index:9999;">
    <div style="position:absolute; top:50%; left:50%; transform:translate(-50%, -50%); background:white; padding:2rem; border-radius:8px; box-shadow:0 4px 6px rgba(0,0,0,0.1);">
        <h2>Admin Login</h2>
        <form method="POST" action="/login">
            <div style="margin-bottom:1rem;">
                <label>Username:</label>
                <input type="text" name="username" required style="width:100%; padding:0.5rem; border:1px solid #ddd; border-radius:4px;">
            </div>
            <div style="margin-bottom:1rem;">
                <label>Password:</label>
                <input type="password" name="password" required style="width:100%; padding:0.5rem; border:1px solid #ddd; border-radius:4px;">
            </div>
            <button type="submit" style="width:100%; padding:0.5rem; background:#007bff; color:white; border:none; border-radius:4px; cursor:pointer;">
                Login
            </button>
            <button type="button" onclick="document.getElementById('loginModal').style.display='none'" style="width:100%; margin-top:0.5rem; padding:0.5rem; background:#6c757d; color:white; border:none; border-radius:4px; cursor:pointer;">
                Cancel
            </button>
        </form>
    </div>
</div>

<script>
// Show login modal on 403 errors
function showLoginModal() {
    document.getElementById('loginModal').style.display = 'block';
}

// Intercept fetch requests to show login on 403
const originalFetch = window.fetch;
window.fetch = function(...args) {
    return originalFetch.apply(this, args).then(response => {
        if (response.status === 403) {
            showLoginModal();
        }
        return response;
    });
};
</script>
```

### Option 2: Login Button in Header

```html
<!-- Add this to your dashboard header -->
<div style="display:flex; justify-content:space-between; align-items:center; padding:1rem; background:#f8f9fa; border-bottom:1px solid #dee2e6;">
    <h1>Sherlock Jobs</h1>
    
    {% if request.session.get('is_admin') %}
        <!-- Logged in -->
        <div>
            <span>Welcome, {{ request.session.get('username') }}</span>
            <form method="POST" action="/logout" style="display:inline;">
                <button type="submit" style="margin-left:1rem; padding:0.5rem 1rem; background:#dc3545; color:white; border:none; border-radius:4px; cursor:pointer;">
                    Logout
                </button>
            </form>
        </div>
    {% else %}
        <!-- Not logged in -->
        <button onclick="showLoginModal()" style="padding:0.5rem 1rem; background:#007bff; color:white; border:none; border-radius:4px; cursor:pointer;">
            Admin Login
        </button>
    {% endif %}
</div>
```

### Option 3: Inline Login Form (Collapsed)

```html
<!-- Add this to your dashboard -->
<details style="margin:1rem; padding:1rem; background:#f8f9fa; border-radius:8px;">
    <summary style="cursor:pointer; font-weight:bold;">Admin Panel (Login Required)</summary>
    <div style="margin-top:1rem;">
        {% if request.session.get('is_admin') %}
            <p>✅ Logged in as {{ request.session.get('username') }}</p>
            <form method="POST" action="/logout">
                <button type="submit">Logout</button>
            </form>
        {% else %}
            <form method="POST" action="/login" style="max-width:300px;">
                <input type="text" name="username" placeholder="Username" required style="width:100%; margin-bottom:0.5rem; padding:0.5rem;">
                <input type="password" name="password" placeholder="Password" required style="width:100%; margin-bottom:0.5rem; padding:0.5rem;">
                <button type="submit" style="width:100%; padding:0.5rem; background:#007bff; color:white; border:none; border-radius:4px;">
                    Login
                </button>
            </form>
        {% endif %}
    </div>
</details>
```

## Checking Login Status in Templates

Use Jinja2 to conditionally show/hide elements:

```html
{% if request.session.get('is_admin') %}
    <!-- Admin-only content -->
    <button onclick="triggerScrape()">Start Scraping</button>
{% else %}
    <!-- Public content -->
    <button onclick="showLoginModal()">Login to Scrape</button>
{% endif %}
```

## JavaScript Helper

Add this to handle protected actions gracefully:

```javascript
async function protectedAction(action) {
    try {
        const response = await fetch(`/api/admin/${action}`, {
            method: 'POST',
            credentials: 'include'  // Important: send cookies
        });
        
        if (response.status === 403) {
            showLoginModal();
            return null;
        }
        
        return await response.json();
    } catch (error) {
        console.error('Error:', error);
        return null;
    }
}

// Usage
document.getElementById('scrapeBtn').onclick = () => protectedAction('scrape');
```

## Complete Example

See your current `templates/index.html` and add the modal from Option 1 above. The system will automatically:

1. Intercept 403 errors from admin endpoints
2. Show login modal
3. Redirect back after successful login
4. Maintain session with cookies

