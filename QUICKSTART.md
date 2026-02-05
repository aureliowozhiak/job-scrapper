# Quick Start Guide

## 🚀 Setup Inicial

### 1. Instalar Dependências
```bash
# Criar ambiente virtual
python -m venv .venv

# Ativar ambiente virtual
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# Instalar pacotes
pip install -r requirements.txt
```

### 2. Iniciar Aplicação
```bash
# Rodar API (contém Web UI + Scraper + Loader)
python api.py
```

### 3. Acessar Interface
- **Web UI**: http://localhost:5000
- **API REST**: http://localhost:5000/positions?word=python

## 🎨 Usando a Interface Web

1. Abra http://localhost:5000
2. Você verá:
   - 📊 Dashboard com estatísticas
   - 🔄 Botão "Atualizar Vagas" (executa scrape + load)
   - 📥 Botão "Apenas Scrape" (só busca dados)
   - 💾 Botão "Apenas Load" (só carrega no banco)
   - 🔍 Campo de busca de vagas

3. Clique em **"Atualizar Vagas"** para começar
4. A página recarrega automaticamente mostrando o progresso
5. Quando terminar, busque vagas no campo de pesquisa

## 🧪 Testes

```bash
# Executar todos os testes
pytest

# Com cobertura
pytest --cov --cov-report=html

# Abrir relatório
open htmlcov/index.html  # Mac
start htmlcov/index.html # Windows

# Ver cobertura no terminal
pytest --cov --cov-report=term-missing
```

## 🔧 Comandos Úteis

### Database
```bash
# Conectar ao SQLite
sqlite3 jobs.db

# Ver todas as vagas
SELECT * FROM positions LIMIT 10;

# Contar vagas por empresa
SELECT company, COUNT(*) as total 
FROM positions 
GROUP BY company 
ORDER BY total DESC;

# Buscar vagas
SELECT title, company, link 
FROM positions 
WHERE UPPER(title) LIKE '%PYTHON%';
```

### Scrapy (Opcional)
```bash
cd jobfinder_bot

# List spiders
scrapy list

# Run spider
scrapy crawl skipthedrive_jobs -a query="machine+learning" -o output.json

# Com logging
scrapy crawl skipthedrive_jobs -a query="data+engineer" -L INFO
```

## 📊 Verificar Status

### Logs
```bash
# Ver logs recentes
tail -f logs/job-scrapper-$(date +%Y-%m-%d).log

# Ver apenas erros
tail -f logs/errors-$(date +%Y-%m-%d).log

# Buscar no log
grep "ERROR" logs/job-scrapper-*.log
```

### Banco de Dados
```bash
# Estatísticas via Python
python -c "
import sqlite3
conn = sqlite3.connect('jobs.db')
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM positions')
print(f'Total de vagas: {cursor.fetchone()[0]}')
conn.close()
"
```

## 🔄 Workflow Completo

```bash
# 1. Ativar ambiente
source .venv/bin/activate  # ou .venv\Scripts\activate no Windows

# 2. Iniciar aplicação
python api.py

# 3. Acessar interface
# Abra http://localhost:5000

# 4. Atualizar vagas
# Clique no botão 'Atualizar Vagas' na interface

# 5. Buscar vagas via API
curl "http://localhost:5000/positions?word=data+engineer"

# 6. Ver logs
tail -f logs/*.log
```

## 🐛 Troubleshooting

### Módulo não encontrado (ModuleNotFoundError)
```bash
# Verificar se está no venv
which python  # deve mostrar path do .venv

# Reinstalar dependências
pip install -r requirements.txt

# Verificar instalação
pip list
```

### Porta 5000 já em uso
```bash
# Encontrar processo usando a porta
lsof -i :5000  # Linux/Mac
netstat -ano | findstr :5000  # Windows

# Mudar porta no api.py (última linha)
# app.run(debug=True, port=5001)
```

### Limpar banco de dados
```bash
# Remover banco
rm jobs.db

# Recriar schema (rode python load.py ou inicie a API)
python api.py
```

### Ver coverage detalhado
```bash
pytest --cov --cov-report=term-missing
```

### Logs não aparecem
```bash
# Verificar se diretório existe
ls -la logs/

# Criar diretório se necessário
mkdir -p logs
```

