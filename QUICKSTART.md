# Quick Start Guide

## 🚀 Início Rápido com Docker

### 1. Build e Start
```bash
# Build das imagens
docker-compose build

# Iniciar API
docker-compose up -d api

# Verificar logs
docker-compose logs -f api
```

### 2. Executar Scraping
```bash
# Executar scraper (coleta dados)
docker-compose run --rm scraper

# Carregar dados no banco
docker-compose run --rm loader
```

### 3. Acessar
- **Web UI**: http://localhost:5000
- **API**: http://localhost:5000/positions?word=python

## 🖥️ Desenvolvimento Local

### Setup
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows
pip install -r requirements.txt
```

### Executar
```bash
# 1. Scraping
python app.py

# 2. Load no banco
python load.py

# 3. Iniciar API
python api.py
```

### Testes
```bash
# Executar testes
pytest

# Com coverage
pytest --cov --cov-report=html

# Abrir relatório
open htmlcov/index.html  # Mac
start htmlcov/index.html # Windows
```

## 🔧 Comandos Úteis

### Docker
```bash
# Parar serviços
docker-compose down

# Rebuild forçado
docker-compose build --no-cache

# Ver logs
docker-compose logs api

# Executar comando dentro do container
docker-compose exec api python -c "print('Hello')"
```

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

### Scrapy
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
# Estatísticas
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
# 1. Start services
docker-compose up -d api

# 2. Run scraping job
docker-compose run --rm scraper

# 3. Load data into database
docker-compose run --rm loader

# 4. Query via API
curl "http://localhost:5000/positions?word=data+engineer"

# 5. View logs
docker-compose logs api

# 6. Stop
docker-compose down
```

## 🐛 Troubleshooting

### Porta 5000 já em uso
```bash
# Alterar porta no docker-compose.yml
ports:
  - "5001:5000"  # host:container
```

### Permissões no Docker
```bash
# Dar permissões aos diretórios
chmod -R 755 lake output logs
```

### Limpar banco de dados
```bash
rm jobs.db
python load.py  # Recria o schema
```

### Ver coverage detalhado
```bash
pytest --cov --cov-report=term-missing
```
