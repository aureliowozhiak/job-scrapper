# job-scrapper

🔍 Sistema automatizado de web scraping para vagas de emprego remotas em tecnologia, com foco em áreas de dados (Data Engineer, Data Scientist, ML Engineer, etc.).

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/flask-3.1.1-green.svg)](https://flask.palletsprojects.com/)
[![Scrapy](https://img.shields.io/badge/scrapy-2.13.3-red.svg)](https://scrapy.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## ✨ Funcionalidades

- 🕷️ **Web Scraping**: Coleta automatizada de vagas de múltiplos sites
- 🗄️ **Banco de Dados**: Armazenamento em SQLite com deduplicação automática
- 🌐 **API REST**: Interface JSON para busca de vagas
- 🎨 **Interface Web**: Busca visual e intuitiva
- 📊 **Logging Estruturado**: Monitoramento completo de operações
- 🔄 **Retry Logic**: Requisições HTTP com tentativas automáticas
- 🐳 **Docker**: Deploy facilitado com containers
- ✅ **Testes**: Cobertura de testes automatizados

## 📂 Estrutura do Projeto

```
job-scrapper/
├── api.py                 # API Flask (REST + Web UI)
├── app.py                 # Script ETL principal
├── load.py                # Carregamento no banco de dados
├── endpoints.py           # Configuração de sites
├── requirements.txt       # Dependências Python
├── Dockerfile            # Container Docker
├── docker-compose.yml    # Orquestração de serviços
├── pytest.ini            # Configuração de testes
│
├── methods/              # Módulos ETL
│   ├── extract.py        # Extração de dados (HTTP)
│   ├── transform.py      # Transformação (parsing HTML)
│   └── utils.py          # Utilitários
│
├── utils/                # Utilitários compartilhados
│   └── logger.py         # Sistema de logging
│
├── jobfinder_bot/        # Projeto Scrapy
│   └── spiders/
│       └── skipthedrive.py
│
├── tests/                # Testes automatizados
│   ├── test_extract.py
│   ├── test_transform.py
│   └── test_api.py
│
├── lake/                 # Data lake (HTML bruto)
├── output/               # JSONs processados
├── logs/                 # Arquivos de log
└── jobs.db               # Banco SQLite
```

## 🚀 Como Usar

### Opção 1: Docker (Recomendado)

```bash
# Iniciar API
docker-compose up api

# Acessar em: http://localhost:5000

# Executar scraping
docker-compose run --rm scraper

# Carregar dados no banco
docker-compose run --rm loader
```

### Opção 2: Instalação Local

#### 1. Preparar ambiente

```bash
# Clone o repositório
git clone <repo-url>
cd job-scrapper

# Criar ambiente virtual
python -m venv .venv

# Ativar ambiente virtual
# Linux/MacOS:
source .venv/bin/activate
# Windows:
.venv\Scripts\activate

# Instalar dependências
pip install -r requirements.txt
```

#### 2. Executar scraping

```bash
# ETL completo (BeautifulSoup)
python app.py

# Carregar dados no banco
python load.py

# Iniciar API
python api.py
```

#### 3. Usar Scrapy (alternativa)

```bash
cd jobfinder_bot
scrapy crawl skipthedrive_jobs -a query="data+engineer" -o spider_output/skipthedrive.json
```

## 🔌 API

### REST Endpoint

```bash
GET /positions?word=<termo>

# Exemplo:
curl "http://localhost:5000/positions?word=python"

# Resposta:
{
  "results": [
    "https://weworkremotely.com/jobs/123",
    "https://skipthedrive.com/job/456"
  ]
}
```

### Interface Web

Acesse `http://localhost:5000` para buscar vagas visualmente.

## 🧪 Testes

```bash
# Executar todos os testes
pytest

# Com cobertura
pytest --cov

# Apenas testes unitários
pytest tests/test_extract.py tests/test_transform.py

# Gerar relatório HTML
pytest --cov --cov-report=html
```

## 📊 Sites Suportados

| Site           | Status  | Método                 |
| -------------- | ------- | ---------------------- |
| WeWorkRemotely | ✅ Ativo | BeautifulSoup          |
| SkipTheDrive   | ✅ Ativo | BeautifulSoup + Scrapy |

## 🔍 Queries Pré-configuradas

O sistema busca automaticamente por 20 termos:
- Data Analytics, Data Engineer, Data Scientist
- Machine Learning Engineer, AI Engineer
- Business Intelligence Analyst, BI Developer
- ETL Developer, Big Data Engineer
- E mais...

(Ver `app.py` para lista completa)

## 📝 Logs

Os logs são salvos em `logs/`:

- `job-scrapper-YYYY-MM-DD.log` - Todos os logs
- `errors-YYYY-MM-DD.log` - Apenas erros

Níveis de log:
- **DEBUG**: Detalhes de operações
- **INFO**: Eventos importantes
- **WARNING**: Avisos
- **ERROR**: Erros com stack trace

## 🗃️ Banco de Dados

### Schema

```sql
CREATE TABLE positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    link TEXT NOT NULL UNIQUE,  -- Deduplicação
    company TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Deduplicação

O sistema evita vagas duplicadas usando:
- UNIQUE constraint no campo `link`
- INSERT com tratamento de IntegrityError
- Logs de duplicatas encontradas

## 📈 Melhorias Implementadas

- ✅ **Logging estruturado** com rotação diária
- ✅ **Tratamento de erros robusto** com retry logic
- ✅ **Testes automatizados** com pytest e coverage
- ✅ **Deduplicação** de vagas no banco
- ✅ **Docker** para deploy facilitado
- ✅ **Type hints** Python 3.12+
- ✅ **Documentação** completa

## 🛠️ Tecnologias

- **Python 3.12+**
- **Flask 3.1.1** - Web framework
- **Scrapy 2.13.3** - Framework de scraping
- **BeautifulSoup4** - Parsing HTML
- **Requests** - Cliente HTTP
- **SQLite** - Banco de dados
- **Pytest** - Framework de testes
- **Docker** - Containerização

## 📄 Licença

MIT License - veja LICENSE para detalhes.

## 🤝 Contribuindo

1. Fork o projeto
2. Crie sua feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## 📞 Suporte

Para bugs ou sugestões, abra uma issue no repositório.

---

Feito com ❤️ para ajudar a encontrar vagas remotas em tech!