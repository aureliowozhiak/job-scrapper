import sqlite3
import threading
from datetime import datetime
from flask import Flask, request, jsonify

app = Flask(__name__)

# Estado global para rastrear operações em andamento
scraper_status = {"running": False, "last_run": None, "message": "", "success": None}
loader_status = {"running": False, "last_run": None, "message": "", "success": None}


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


def run_scraper():
    """Executa o scraper em background."""
    global scraper_status
    scraper_status["running"] = True
    scraper_status["message"] = "Buscando vagas nos sites..."
    
    try:
        # Importa e executa o app.py
        import importlib
        import sys
        
        # Recarrega o módulo app se já foi importado
        if 'app_scraper' in sys.modules:
            del sys.modules['app_scraper']
        
        # Executa o script de scraping
        exec(open("app.py").read())
        
        scraper_status["success"] = True
        scraper_status["message"] = "Scraping concluído com sucesso!"
    except Exception as e:
        scraper_status["success"] = False
        scraper_status["message"] = f"Erro no scraping: {str(e)}"
    finally:
        scraper_status["running"] = False
        scraper_status["last_run"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def run_loader():
    """Executa o loader em background."""
    global loader_status
    loader_status["running"] = True
    loader_status["message"] = "Carregando vagas no banco de dados..."
    
    try:
        # Executa o script de loading
        exec(open("load.py").read())
        
        loader_status["success"] = True
        loader_status["message"] = "Loading concluído com sucesso!"
    except Exception as e:
        loader_status["success"] = False
        loader_status["message"] = f"Erro no loading: {str(e)}"
    finally:
        loader_status["running"] = False
        loader_status["last_run"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@app.route("/positions")
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
    """Endpoint para executar scraping + loading."""
    if scraper_status["running"] or loader_status["running"]:
        return jsonify({"error": "Uma operação já está em andamento"}), 409
    
    def run_both():
        run_scraper()
        if scraper_status["success"]:
            run_loader()
    
    thread = threading.Thread(target=run_both)
    thread.start()
    return jsonify({"message": "Atualização iniciada (scrape + load)"})


@app.route("/api/status")
def api_status():
    """Retorna o status das operações."""
    stats = get_stats()
    return jsonify({
        "scraper": scraper_status,
        "loader": loader_status,
        "database": stats
    })


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
    """Página de navegação com datatable."""
    with open("templates/browse.html", "r", encoding="utf-8") as f:
        return f.read()


@app.route("/", methods=["GET", "POST"])
def web():
    """Interface web principal."""
    results = []
    error = None
    success_msg = None
    word = ""
    
    # Processa ações de formulário
    if request.method == "POST":
        action = request.form.get("action", "search")
        
        if action == "search":
            word = request.form.get("word", "")
            if not word:
                error = "Parâmetro 'word' é obrigatório"
            else:
                results = search(word)
        
        elif action == "scrape":
            if not scraper_status["running"]:
                thread = threading.Thread(target=run_scraper)
                thread.start()
                success_msg = "🔄 Scraping iniciado em background..."
            else:
                error = "Scraping já está em andamento"
        
        elif action == "load":
            if not loader_status["running"]:
                thread = threading.Thread(target=run_loader)
                thread.start()
                success_msg = "🔄 Loading iniciado em background..."
            else:
                error = "Loading já está em andamento"
        
        elif action == "update":
            if not scraper_status["running"] and not loader_status["running"]:
                def run_both():
                    run_scraper()
                    if scraper_status["success"]:
                        run_loader()
                thread = threading.Thread(target=run_both)
                thread.start()
                success_msg = "🔄 Atualização completa iniciada (scrape + load)..."
            else:
                error = "Uma operação já está em andamento"
    
    # Obtém estatísticas
    stats = get_stats()
    
    # Status das operações
    scraper_badge = "🟢 Pronto" if not scraper_status["running"] else "🔄 Executando..."
    loader_badge = "🟢 Pronto" if not loader_status["running"] else "🔄 Executando..."
    
    if scraper_status["last_run"]:
        scraper_badge += f" (Último: {scraper_status['last_run']})"
    if loader_status["last_run"]:
        loader_badge += f" (Último: {loader_status['last_run']})"
    
    return f"""
    <html>
        <head>
            <title>Job Scrapper - Busca de Vagas</title>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                * {{ box-sizing: border-box; }}
                body {{
                    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
                    font-family: 'Segoe UI', Arial, sans-serif;
                    min-height: 100vh;
                    margin: 0;
                    padding: 20px;
                    color: #fff;
                }}
                .container {{
                    max-width: 800px;
                    margin: 0 auto;
                }}
                .card {{
                    background: rgba(255,255,255,0.1);
                    backdrop-filter: blur(10px);
                    padding: 24px;
                    border-radius: 16px;
                    margin-bottom: 20px;
                    border: 1px solid rgba(255,255,255,0.1);
                }}
                h1 {{
                    color: #00d9ff;
                    margin: 0 0 8px 0;
                    font-size: 28px;
                }}
                .subtitle {{
                    color: #888;
                    margin-bottom: 20px;
                }}
                .stats {{
                    display: flex;
                    gap: 20px;
                    margin-bottom: 20px;
                }}
                .stat {{
                    background: rgba(0,217,255,0.1);
                    padding: 16px;
                    border-radius: 12px;
                    flex: 1;
                    text-align: center;
                }}
                .stat-value {{
                    font-size: 32px;
                    font-weight: bold;
                    color: #00d9ff;
                }}
                .stat-label {{
                    color: #888;
                    font-size: 14px;
                }}
                .actions {{
                    display: flex;
                    gap: 10px;
                    flex-wrap: wrap;
                    margin-bottom: 20px;
                }}
                .search-form {{
                    display: flex;
                    gap: 10px;
                    margin-bottom: 20px;
                }}
                input[type="text"] {{
                    flex: 1;
                    padding: 14px 18px;
                    border: 2px solid rgba(255,255,255,0.2);
                    border-radius: 12px;
                    font-size: 16px;
                    background: rgba(255,255,255,0.1);
                    color: #fff;
                    outline: none;
                    transition: border-color 0.3s;
                }}
                input[type="text"]:focus {{
                    border-color: #00d9ff;
                }}
                input[type="text"]::placeholder {{
                    color: #888;
                }}
                button {{
                    padding: 14px 24px;
                    border: none;
                    border-radius: 12px;
                    font-size: 16px;
                    font-weight: 600;
                    cursor: pointer;
                    transition: all 0.3s;
                }}
                .btn-primary {{
                    background: linear-gradient(135deg, #00d9ff, #0099ff);
                    color: #fff;
                }}
                .btn-primary:hover {{
                    transform: translateY(-2px);
                    box-shadow: 0 8px 20px rgba(0,217,255,0.3);
                }}
                .btn-secondary {{
                    background: rgba(255,255,255,0.1);
                    color: #fff;
                    border: 1px solid rgba(255,255,255,0.2);
                }}
                .btn-secondary:hover {{
                    background: rgba(255,255,255,0.2);
                }}
                .btn-success {{
                    background: linear-gradient(135deg, #00c853, #00e676);
                    color: #fff;
                }}
                .btn-success:hover {{
                    transform: translateY(-2px);
                    box-shadow: 0 8px 20px rgba(0,200,83,0.3);
                }}
                .status {{
                    font-size: 13px;
                    color: #888;
                    margin-top: 10px;
                }}
                .alert {{
                    padding: 14px 18px;
                    border-radius: 12px;
                    margin-bottom: 20px;
                }}
                .alert-error {{
                    background: rgba(255,82,82,0.2);
                    border: 1px solid rgba(255,82,82,0.3);
                    color: #ff5252;
                }}
                .alert-success {{
                    background: rgba(0,200,83,0.2);
                    border: 1px solid rgba(0,200,83,0.3);
                    color: #00c853;
                }}
                .job-list {{
                    display: flex;
                    flex-direction: column;
                    gap: 16px;
                }}
                .job-card {{
                    background: rgba(255,255,255,0.05);
                    border: 1px solid rgba(255,255,255,0.1);
                    border-radius: 12px;
                    padding: 20px;
                    transition: all 0.3s;
                    cursor: pointer;
                }}
                .job-card:hover {{
                    background: rgba(255,255,255,0.1);
                    border-color: #00d9ff;
                    transform: translateX(4px);
                }}
                .job-title {{
                    font-size: 20px;
                    font-weight: 600;
                    color: #00d9ff;
                    margin: 0 0 8px 0;
                    line-height: 1.3;
                }}
                .job-company {{
                    font-size: 16px;
                    color: #aaa;
                    margin: 0 0 12px 0;
                    display: flex;
                    align-items: center;
                    gap: 6px;
                }}
                .job-meta {{
                    display: flex;
                    gap: 16px;
                    align-items: center;
                    flex-wrap: wrap;
                    margin-top: 12px;
                    padding-top: 12px;
                    border-top: 1px solid rgba(255,255,255,0.1);
                }}
                .job-date {{
                    font-size: 13px;
                    color: #888;
                    display: flex;
                    align-items: center;
                    gap: 4px;
                }}
                .job-link {{
                    font-size: 13px;
                    color: #00d9ff;
                    text-decoration: none;
                    display: flex;
                    align-items: center;
                    gap: 4px;
                    margin-left: auto;
                }}
                .job-link:hover {{
                    text-decoration: underline;
                }}
                .results-header {{
                    color: #aaa;
                    font-size: 14px;
                    margin-bottom: 16px;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }}
                .results-count {{
                    font-weight: 600;
                    color: #00d9ff;
                }}
                .empty {{
                    text-align: center;
                    color: #888;
                    padding: 40px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="card">
                    <h1>🔍 Job Scrapper</h1>
                    <p class="subtitle">Busque e atualize vagas de emprego remotas</p>
                    
                    <div class="stats">
                        <div class="stat">
                            <div class="stat-value">{stats['total_jobs']}</div>
                            <div class="stat-label">Vagas no Banco</div>
                        </div>
                        <div class="stat">
                            <div class="stat-value">{stats['total_companies']}</div>
                            <div class="stat-label">Empresas</div>
                        </div>
                    </div>
                    
                    <div class="actions">
                        <form method="post" style="display:inline;">
                            <input type="hidden" name="action" value="update">
                            <button type="submit" class="btn-success" {'disabled' if scraper_status["running"] or loader_status["running"] else ''}>
                                🔄 Atualizar Vagas
                            </button>
                        </form>
                        <form method="post" style="display:inline;">
                            <input type="hidden" name="action" value="scrape">
                            <button type="submit" class="btn-secondary" {'disabled' if scraper_status["running"] else ''}>
                                📥 Apenas Scrape
                            </button>
                        </form>
                        <form method="post" style="display:inline;">
                            <input type="hidden" name="action" value="load">
                            <button type="submit" class="btn-secondary" {'disabled' if loader_status["running"] else ''}>
                                💾 Apenas Load
                            </button>
                        </form>
                        <a href="/browse" style="display:inline-block; text-decoration:none;">
                            <button type="button" class="btn-secondary">
                                📋 Browse All Jobs
                            </button>
                        </a>
                    </div>
                    
                    <div class="status">
                        <div>Scraper: {scraper_badge}</div>
                        <div>Loader: {loader_badge}</div>
                    </div>
                </div>
                
                {"<div class='alert alert-error'>" + error + "</div>" if error else ""}
                {"<div class='alert alert-success'>" + success_msg + "</div>" if success_msg else ""}
                
                <div class="card">
                    <form method="post" class="search-form">
                        <input type="hidden" name="action" value="search">
                        <input type="text" name="word" placeholder="Digite o termo da vaga (ex: Python, React, Data)" value="{word}">
                        <button type="submit" class="btn-primary">Buscar</button>
                    </form>
                    
                    {f'''
                    <div class="results-header">
                        <span>Resultados da busca</span>
                        <span class="results-count">{len(results)} vaga{'s' if len(results) != 1 else ''} encontrada{'s' if len(results) != 1 else ''}</span>
                    </div>
                    <div class="job-list">
                        {''.join(f"""
                        <div class="job-card" onclick="window.open('{job['link']}', '_blank')">
                            <h3 class="job-title">{job['title']}</h3>
                            <div class="job-company">
                                🏢 {job['company']}
                            </div>
                            <div class="job-meta">
                                <span class="job-date">
                                    📅 Adicionado em {job['created_at'][:10] if job.get('created_at') else 'N/A'}
                                </span>
                                <a href="{job['link']}" target="_blank" class="job-link" onclick="event.stopPropagation()">
                                    🔗 Ver vaga
                                </a>
                            </div>
                        </div>
                        """ for job in results)}
                    </div>
                    ''' if results else ('<div class="empty">Busque por vagas usando o campo acima</div>' if not word else '<div class="empty">Nenhuma vaga encontrada para "' + word + '"</div>')}
                </div>
            </div>
            
            <script>
                // Auto-refresh a cada 5 segundos se houver operação em andamento
                {'setTimeout(() => location.reload(), 5000);' if scraper_status["running"] or loader_status["running"] else ''}
            </script>
        </body>
    </html>
    """


if __name__ == "__main__":  # pragma: no cover
    app.run(debug=True)
