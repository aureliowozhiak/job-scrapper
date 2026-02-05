import sqlite3
import threading
from datetime import datetime
from flask import Flask, request, jsonify, redirect
from workflow import pulse

app = Flask(__name__)

# --- JOB LOGIC WRAPPERS ---
# Estas funções encapsulam a lógica de execução para o Pulse


def search(word):
    """Busca vagas no banco de dados."""
    try:
        connection = sqlite3.connect("jobs.db")
        connection.row_factory = sqlite3.Row  # Permite acessar colunas por nome
        cursor = connection.cursor()
        query = """
            SELECT id, title, link, company, created_at 
            FROM positions 
            WHERE UPPER(title) LIKE UPPER(?) OR UPPER(company) LIKE UPPER(?)
            ORDER BY created_at DESC
        """
        cursor.execute(query, (f"%{word}%", f"%{word}%"))
        results = [dict(row) for row in cursor.fetchall()]
        connection.close()
        return results
    except Exception:
        return []


def get_stats():
    """Retorna estatísticas do banco de dados."""
    try:
        connection = sqlite3.connect("jobs.db")
        cursor = connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM positions")
        total = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(DISTINCT company) FROM positions")
        companies = cursor.fetchone()[0]
        connection.close()
        return {"total_jobs": total, "total_companies": companies}
    except Exception:
        return {"total_jobs": 0, "total_companies": 0}


def task_scraper():
    """Executa o script de scraping (app.py)."""
    # Importa e executa o app.py
    import sys
    
    # Recarrega o módulo app se já foi importado para garantir frescor
    if 'app_scraper' in sys.modules:
        del sys.modules['app_scraper']
    
    # Executa o script de scraping
    # O script usa logger próprio, que vai para stdout/file
    exec(open("app.py").read())


def task_loader():
    """Executa o script de loading (load.py)."""
    # Executa o script de loading
    exec(open("load.py").read())


def task_validator():
    """Executa a validação de qualidade."""
    from validate import cleanup_invalid_jobs
    stats = cleanup_invalid_jobs(batch_size=50)
    # Podemos retornar stats se quisermos usar no futuro,
    # mas o Pulse captura apenas sucesso/erro por enquanto
    if stats['removed'] > 0:
        print(f"Validator removed {stats['removed']} invalid jobs")


# --- API ENDPOINTS ---
def positions():
    """Endpoint API para buscar vagas."""
    word = request.args.get("word", "")
    if not word:
        return jsonify({"error": "Parâmetro 'word' é obrigatório"}), 400
    search_results = search(word)
    return jsonify({"results": search_results})


@app.route("/api/scrape", methods=["POST"])
def api_scrape():
    """Endpoint para iniciar o scraping."""
    if scraper_status["running"]:
        return jsonify({"error": "Scraping já está em andamento"}), 409
    
    thread = threading.Thread(target=run_scraper)
    thread.start()
    return jsonify({"message": "Scraping iniciado"})


@app.route("/api/load", methods=["POST"])
def api_load():
    """Endpoint para iniciar o loading."""
    if loader_status["running"]:
        return jsonify({"error": "Loading já está em andamento"}), 409
    
    thread = threading.Thread(target=run_loader)
    thread.start()
    return jsonify({"message": "Loading iniciado"})


@app.route("/api/update", methods=["POST"])
def api_update():
    """Endpoint para executar pipeline completo (Scrape -> Load -> Validate)."""
    try:
        pipeline_steps = [
            ('scraper', task_scraper),
            ('loader', task_loader),
            ('validator', task_validator)
        ]
        pulse.run_pipeline(pipeline_steps)
        return jsonify({"message": "Pipeline completo iniciado (Scrape -> Load -> Validate)"})
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 409


@app.route("/api/validate", methods=["POST"])
def api_validate():
    """Endpoint para validar links de vagas."""
    try:
        pulse.run_job("validator", task_validator)
        return jsonify({"message": "Validação de links iniciada"})
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 409


@app.route("/api/status")
def api_status():
    """Retorna o status unificado do Pulse."""
    # Obtém status do Pulse e combina com status do DB
    status = pulse.get_status()
    status["database"] = get_stats()
    return jsonify(status)


@app.route("/api/jobs")
def api_jobs():
    """Retorna todas as vagas para o datatable."""
    try:
        connection = sqlite3.connect("jobs.db")
        connection.row_factory = sqlite3.Row
        cursor = connection.cursor()
        
        # Parâmetros opcionais
        search = request.args.get("search", "")
        company = request.args.get("company", "")
        limit = request.args.get("limit", type=int)
        offset = request.args.get("offset", 0, type=int)
        
        # Query base
        query = """
            SELECT id, title, link, company, created_at 
            FROM positions 
            WHERE 1=1
        """
        params = []
        
        # Filtros
        if search:
            query += " AND (UPPER(title) LIKE UPPER(?) OR UPPER(company) LIKE UPPER(?))"
            params.extend([f"%{search}%", f"%{search}%"])
        
        if company:
            query += " AND UPPER(company) LIKE UPPER(?)"
            params.append(f"%{company}%")
        
        # Ordenação
        query += " ORDER BY created_at DESC"
        
        # Paginação
        if limit:
            query += f" LIMIT {limit} OFFSET {offset}"
        
        cursor.execute(query, params)
        jobs = [dict(row) for row in cursor.fetchall()]
        
        # Total count para paginação
        count_query = "SELECT COUNT(*) as total FROM positions WHERE 1=1"
        count_params = []
        if search:
            count_query += " AND (UPPER(title) LIKE UPPER(?) OR UPPER(company) LIKE UPPER(?))"
            count_params.extend([f"%{search}%", f"%{search}%"])
        if company:
            count_query += " AND UPPER(company) LIKE UPPER(?)"
            count_params.append(f"%{company}%")
        
        cursor.execute(count_query, count_params)
        total = cursor.fetchone()["total"]
        
        connection.close()
        
        return jsonify({
            "jobs": jobs,
            "total": total,
            "count": len(jobs)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/browse")
def browse():
    """Redireciona para a página principal (compatibilidade)."""
    return redirect("/")


@app.route("/", methods=["GET", "POST"])
def web():
    """Interface web unificada (Dashboard + Search + Browse)."""
    results = []
    error = None
    success_msg = None
    word = ""
    
    # Processa ações de formulário (POST)
    if request.method == "POST":
        action = request.form.get("action", "search")
        
        try:
            if action == "update":
                pipeline_steps = [
                    ('scraper', task_scraper),
                    ('loader', task_loader),
                    ('validator', task_validator)
                ]
                pulse.run_pipeline(pipeline_steps)
                success_msg = "Pipeline completo iniciado! Acompanhe no painel."
                    
            elif action == "scrape":
                pulse.run_job("scraper", task_scraper)
                success_msg = "Scraping iniciado!"
                    
            elif action == "load":
                pulse.run_job("loader", task_loader)
                success_msg = "Loader iniciado!"
                    
            elif action == "validate":
                pulse.run_job("validator", task_validator)
                success_msg = "Validação de links iniciada!"
                
            elif action == "search":
                word = request.form.get("word", "")
                if word:
                    results = search(word)
                else:
                    error = "Digite um termo para buscar."
        except RuntimeError as e:
            error = str(e)
    
    # Obtém status atualizado do Pulse
    current_status = pulse.get_status()
    
    # Obtém estatísticas do banco
    stats = get_stats()
    
    # Badges de status (Extraídos do Pulse)
    scraper_badge = "🟢 Pronto" if not current_status["scraper"]["running"] else "🔄 Executando..."
    loader_badge = "🟢 Pronto" if not current_status["loader"]["running"] else "🔄 Executando..."
    validator_badge = "🟢 Pronto" if not current_status["validator"]["running"] else "🔄 Validando..."
    
    # HTML da aplicação
    return f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <title>Job Scrapper Pro</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
        <style>
            :root {{
                --primary: #00d9ff;
                --primary-dark: #00b3d4;
                --bg-dark: #1a1a2e;
                --bg-card: rgba(255, 255, 255, 0.05);
                --text-main: #ffffff;
                --text-muted: #888888;
                --border: rgba(255, 255, 255, 0.1);
            }}
            * {{ box-sizing: border-box; }}
            body {{
                background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
                font-family: 'Inter', sans-serif;
                min-height: 100vh;
                margin: 0;
                color: var(--text-main);
                padding-bottom: 40px;
            }}
            .container {{
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
            }}
            
            /* Header & Tabs */
            .app-header {{
                display: flex;
                flex-direction: column;
                gap: 20px;
                margin-bottom: 30px;
                background: rgba(0,0,0,0.2);
                padding: 20px;
                border-radius: 16px;
                border: 1px solid var(--border);
            }}
            .app-title-row {{
                display: flex;
                justify-content: space-between;
                align-items: center;
            }}
            .app-title h1 {{
                margin: 0;
                color: var(--primary);
                font-size: 24px;
                display: flex;
                align-items: center;
                gap: 10px;
            }}
            .status-badges {{
                display: flex;
                gap: 12px;
                font-size: 13px;
                background: rgba(0,0,0,0.3);
                padding: 8px 16px;
                border-radius: 20px;
            }}
            
            /* Tabs Navigation */
            .tabs {{
                display: flex;
                gap: 5px;
                background: rgba(255,255,255,0.05);
                padding: 5px;
                border-radius: 12px;
                width: fit-content;
            }}
            .tab-btn {{
                padding: 10px 24px;
                border: none;
                background: transparent;
                color: var(--text-muted);
                font-weight: 600;
                cursor: pointer;
                border-radius: 8px;
                transition: all 0.2s;
            }}
            .tab-btn:hover {{
                color: #fff;
                background: rgba(255,255,255,0.05);
            }}
            .tab-btn.active {{
                background: var(--primary);
                color: #1a1a2e;
            }}
            
            /* Tab Content Areas */
            .tab-content {{
                display: none;
                animation: fadeIn 0.3s ease;
            }}
            .tab-content.active {{
                display: block;
            }}
            @keyframes fadeIn {{
                from {{ opacity: 0; transform: translateY(10px); }}
                to {{ opacity: 1; transform: translateY(0); }}
            }}
            
            /* Controls Section */
            .controls-section {{
                display: flex;
                gap: 12px;
                margin-top: 10px;
                flex-wrap: wrap;
            }}
            .btn {{
                padding: 12px 20px;
                border: none;
                border-radius: 10px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.2s;
                font-size: 14px;
                display: inline-flex;
                align-items: center;
                gap: 8px;
            }}
            .btn:disabled {{
                opacity: 0.5;
                cursor: not-allowed;
            }}
            .btn-primary {{
                background: var(--primary);
                color: #1a1a2e;
            }}
            .btn-primary:hover:not(:disabled) {{
                background: var(--primary-dark);
                transform: translateY(-2px);
            }}
            .btn-secondary {{
                background: var(--bg-card);
                color: #fff;
                border: 1px solid var(--border);
            }}
            .btn-secondary:hover:not(:disabled) {{
                background: rgba(255,255,255,0.1);
            }}
            .btn-success {{
                background: #00c853;
                color: #fff;
            }}
            .btn-success:hover:not(:disabled) {{
                background: #00e676;
                transform: translateY(-2px);
            }}
            
            /* Stats Cards */
            .stats-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }}
            .stat-card {{
                background: var(--bg-card);
                padding: 24px;
                border-radius: 16px;
                border: 1px solid var(--border);
                text-align: center;
            }}
            .stat-val {{ font-size: 36px; font-weight: 700; color: var(--primary); }}
            .stat-label {{ color: var(--text-muted); font-size: 14px; margin-top: 5px; }}

            /* Search & List Styles */
            .search-box input {{
                width: 100%;
                padding: 16px;
                background: var(--bg-card);
                border: 1px solid var(--border);
                border-radius: 12px;
                color: #fff;
                font-size: 16px;
                outline: none;
            }}
            .search-box input:focus {{ border-color: var(--primary); }}
            
            .job-card {{
                background: var(--bg-card);
                border: 1px solid var(--border);
                border-radius: 12px;
                padding: 20px;
                margin-bottom: 12px;
                cursor: pointer;
                transition: all 0.2s;
            }}
            .job-card:hover {{
                border-color: var(--primary);
                background: rgba(255,255,255,0.08);
            }}
            .job-card h3 {{ color: var(--primary); margin: 0 0 8px 0; font-size: 18px; }}
            .job-meta {{ display: flex; gap: 15px; font-size: 13px; color: var(--text-muted); }}
            
            /* Datatable Styles */
            .filters-row {{ display: flex; gap: 12px; margin-bottom: 20px; }}
            .filters-row input {{ flex: 1; padding: 12px; background: var(--bg-card); border: 1px solid var(--border); border-radius: 8px; color: #fff; }}
            .pagination {{ display: flex; justify-content: center; gap: 5px; margin-top: 20px; }}
            .page-btn {{ padding: 8px 12px; background: var(--bg-card); border: 1px solid var(--border); color: #fff; cursor: pointer; border-radius: 6px; }}
            .page-btn.active {{ background: var(--primary); color: #1a1a2e; }}

            .alerts {{ margin: 20px 0; }}
            .alert-success {{ background: rgba(0, 200, 83, 0.2); color: #00c853; padding: 15px; border-radius: 8px; }}
            .alert-error {{ background: rgba(255, 82, 82, 0.2); color: #ff5252; padding: 15px; border-radius: 8px; }}

        </style>
    </head>
    <body onload="initApp()">
        <div class="container">
        
            <!-- Header Unificado -->
            <div class="app-header">
                <div class="app-title-row">
                    <div class="app-title">
                        <h1>🚀 Job Scrapper Pro</h1>
                    </div>
                    <div class="status-badges">
                        <span>Scraper: {scraper_badge}</span>
                        <span>Loader: {loader_badge}</span>
                        <span>Validator: {validator_badge}</span>
                    </div>
                </div>
                
                <!-- Navegação Tabs -->
                <div class="tabs">
                    <button class="tab-btn active" onclick="switchTab('dashboard')">📊 Dashboard</button>
                    <button class="tab-btn" onclick="switchTab('search')">🔍 Busca Rápida</button>
                    <button class="tab-btn" onclick="switchTab('browse')">📋 Browse Jobs</button>
                </div>
            </div>
            
            <!-- Mensagens de Feedback -->
            <div class="alerts">
                {"<div class='alert-error'>" + error + "</div>" if error else ""}
                {"<div class='alert-success'>" + success_msg + "</div>" if success_msg else ""}
            </div>

            <!-- TAB 1: DASHBOARD -->
            <div id="tab-dashboard" class="tab-content active">
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-val">{stats['total_jobs']}</div>
                        <div class="stat-label">Vagas Total</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-val">{stats['total_companies']}</div>
                        <div class="stat-label">Empresas</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-val">2</div>
                        <div class="stat-label">Sites Monitorados</div>
                    </div>
                </div>
                
                <h3>☁️ Gerenciamento de Dados</h3>
                <div class="controls-section">
                    <form method="post" style="display:inline;">
                        <input type="hidden" name="action" value="update">
                        <button type="submit" class="btn btn-success" {'disabled' if current_status["scraper"]["running"] or current_status["loader"]["running"] else ''}>
                            🔄 Atualizar Vagas (Completo)
                        </button>
                    </form>
                    <form method="post" style="display:inline;">
                        <input type="hidden" name="action" value="scrape">
                        <button type="submit" class="btn btn-secondary" {'disabled' if current_status["scraper"]["running"] else ''}>
                            📥 Apenas Scrape
                        </button>
                    </form>
                    <form method="post" style="display:inline;">
                        <input type="hidden" name="action" value="load">
                        <button type="submit" class="btn btn-secondary" {'disabled' if current_status["loader"]["running"] else ''}>
                            💾 Apenas Load (DB)
                        </button>
                    </form>
                    <form method="post" style="display:inline;">
                        <input type="hidden" name="action" value="validate">
                        <button type="submit" class="btn btn-secondary" {'disabled' if current_status["validator"]["running"] else ''}>
                            🔍 Validar Links (Quality Gate)
                        </button>
                    </form>
                </div>
            </div>

            <!-- TAB 2: SEARCH (Formulário POST padrão) -->
            <div id="tab-search" class="tab-content">
                <form method="post" class="search-box">
                    <input type="hidden" name="action" value="search">
                    <div style="display:flex; gap:10px;">
                        <input type="text" name="word" placeholder="Digite tecnologias (ex: Python, React)..." value="{word}">
                        <button type="submit" class="btn btn-primary">Buscar</button>
                    </div>
                </form>
                
                <div style="margin-top: 20px;">
                    {f'''
                    <div style="margin-bottom:10px; color:#888;">Encontradas {len(results)} vagas</div>
                    {''.join(f"""
                        <div class="job-card" onclick="window.open('{job['link']}', '_blank')">
                            <h3>{job['title']}</h3>
                            <div class="job-meta">
                                <span>🏢 {job['company']}</span>
                                <span>📅 {job['created_at'][:10] if job.get('created_at') else 'N/A'}</span>
                                <span style="margin-left:auto; color:var(--primary);">🔗 Ver Vaga</span>
                            </div>
                        </div>
                    """ for job in results)}
                    ''' if results else '<div style="text-align:center; padding:40px; color:#666;">Use a busca acima para encontrar vagas específicas.</div>'}
                </div>
            </div>

            <!-- TAB 3: BROWSE (Datatable JS) -->
            <div id="tab-browse" class="tab-content">
                <div class="filters-row">
                    <input type="text" id="browseSearch" placeholder="Filtrar por título ou empresa..." onkeyup="if(event.key==='Enter') applyFilters()">
                    <button onclick="applyFilters()" class="btn btn-primary">Filtrar</button>
                    <button onclick="clearFilters()" class="btn btn-secondary">Limpar</button>
                </div>
                
                <div id="browseList">
                    <div style="text-align:center; padding:40px; color:#888;">Carregando dados...</div>
                </div>
                
                <div id="pagination" class="pagination"></div>
            </div>

        </div>

        <script>
            // --- TAB SYSTEM ---
            function switchTab(tabName) {{
                // Hide all contents
                document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
                document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
                
                // Show selected
                document.getElementById('tab-' + tabName).classList.add('active');
                
                // Active button state - find button with specific onclick text or index
                // Simplified: Just loop buttons and check text context or index
                const buttons = document.querySelectorAll('.tab-btn');
                if(tabName === 'dashboard') buttons[0].classList.add('active');
                if(tabName === 'search') buttons[1].classList.add('active');
                if(tabName === 'browse') {{
                    buttons[2].classList.add('active');
                    if(allJobs.length === 0) loadAllJobs(); // Load data on first view
                }}
                
                // Save state
                localStorage.setItem('activeTab', tabName);
            }}

            function initApp() {{
                // Restore tab state or default to dashboard
                // If search results exist (server side), go to search tab
                const hasResults = { 'true' if results else 'false' };
                const savedTab = localStorage.getItem('activeTab') || 'dashboard';
                
                if (hasResults) {{
                    switchTab('search');
                }} else {{
                    switchTab(savedTab);
                }}
                
                // Auto-refresh if running
                {'setTimeout(() => location.reload(), 5000);' if current_status["scraper"]["running"] or current_status["loader"]["running"] or current_status["validator"]["running"] else ''}
            }}

            // --- BROWSE LOGIC (Datatable) ---
            let allJobs = [];
            let filteredJobs = [];
            let currentPage = 1;
            const pageSize = 15;

            async function loadAllJobs() {{
                try {{
                    const response = await fetch('/api/jobs');
                    const data = await response.json();
                    allJobs = data.jobs;
                    filteredJobs = allJobs;
                    renderBrowse();
                }} catch (e) {{
                    document.getElementById('browseList').innerHTML = '<div class="alert-error">Erro ao carregar dados.</div>';
                }}
            }}

            function applyFilters() {{
                const term = document.getElementById('browseSearch').value.toLowerCase();
                filteredJobs = allJobs.filter(j => 
                    j.title.toLowerCase().includes(term) || j.company.toLowerCase().includes(term)
                );
                currentPage = 1;
                renderBrowse();
            }}
            
            function clearFilters() {{
                document.getElementById('browseSearch').value = '';
                filteredJobs = allJobs;
                currentPage = 1;
                renderBrowse();
            }}

            function renderBrowse() {{
                const start = (currentPage - 1) * pageSize;
                const pageJobs = filteredJobs.slice(start, start + pageSize);
                
                if(pageJobs.length === 0) {{
                    document.getElementById('browseList').innerHTML = '<div style="text-align:center; padding:40px;">Nenhuma vaga encontrada.</div>';
                    document.getElementById('pagination').innerHTML = '';
                    return;
                }}
                
                let html = pageJobs.map(job => `
                    <div class="job-card" onclick="window.open('${{job.link}}', '_blank')">
                        <h3>${{job.title}}</h3>
                        <div class="job-meta">
                            <span>🏢 ${{job.company}}</span>
                            <span>📅 ${{new Date(job.created_at).toLocaleDateString()}}</span>
                            <span style="margin-left:auto; color:var(--primary);">🔗 Abrir</span>
                        </div>
                    </div>
                `).join('');
                
                document.getElementById('browseList').innerHTML = html;
                renderPagination();
            }}

            function renderPagination() {{
                const totalPages = Math.ceil(filteredJobs.length / pageSize);
                if(totalPages <= 1) {{
                    document.getElementById('pagination').innerHTML = '';
                    return;
                }}
                
                let btns = '';
                // Simple pagination logic (prev, current, next)
                if(currentPage > 1) btns += `<button class="page-btn" onclick="goToPage(${{currentPage-1}})">«</button>`;
                
                // Show limited range
                const start = Math.max(1, currentPage - 2);
                const end = Math.min(totalPages, currentPage + 2);
                
                for(let i=start; i<=end; i++) {{
                    btns += `<button class="page-btn ${{i===currentPage?'active':''}}" onclick="goToPage(${{i}})">${{i}}</button>`;
                }}
                
                if(currentPage < totalPages) btns += `<button class="page-btn" onclick="goToPage(${{currentPage+1}})">»</button>`;
                
                document.getElementById('pagination').innerHTML = btns;
            }}
            
            function goToPage(p) {{
                currentPage = p;
                renderBrowse();
                document.getElementById('tab-browse').scrollIntoView({{behavior:'smooth'}});
            }}
        </script>
    </body>
    </html>
    """


if __name__ == "__main__":  # pragma: no cover
    app.run(debug=True)
