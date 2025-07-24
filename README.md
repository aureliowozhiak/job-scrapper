# job-scrapper

Repo para crawler the vagas de empregos

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