# job-scrapper

Repo para crawler the vagas de empregos

## ✨ New: Web Application with Role-Based Access Control

This project now includes a modern web application with FastAPI that provides:
- 🔍 **Public job search** - Search and browse job listings
- 🔐 **Admin authentication** - Secure login for administrative functions
- 📊 **Admin dashboard** - Task manager and health monitoring
- 🎨 **Modern UI** - Clean, responsive interface

See [RBAC_DOCUMENTATION.md](./RBAC_DOCUMENTATION.md) for complete documentation.

### Quick Start - Web Application

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment:
```bash
cp .env.example .env
# Edit .env with your credentials (see RBAC_DOCUMENTATION.md)
```

3. Run the application:
```bash
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

4. Access at: `http://localhost:8000`

---

## Como utilizar?
1. Clone o repositório
2. Prepare o ambiente virtual
```bash
python -m venv .venv

# Linux/MacOS
source .venv/bin/activate

# Windows
.venv/Scripts/activate

pip install -r requirements.txt
```

### Como utilizar o crawler?
Para utilizar apenas o crawler você precisa ter ativado o ambiente virtual e instalado as dependências e estar no mesmo nível que a pasta `jobfinder_bot/`. Neste exemplo o crawler está procurando pela vaga de data engineer.
```bash
cd jobfinder_bot

scrapy crawl skipthedrive_jobs -a query="data+engineer" -o spider_output/skipthedrive.json
```

### Como utilizar a aplicação Flask original?
```bash
python api.py
```

## 📚 Documentation

- [RBAC Documentation](./RBAC_DOCUMENTATION.md) - Complete guide for the new web application
- [.env.example](./.env.example) - Environment configuration template