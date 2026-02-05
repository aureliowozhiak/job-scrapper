"""Main ETL script for job scraping."""
from endpoints import urls
from datetime import datetime
from methods.utils import Utils
from methods.extract import Extract
from methods.transform import Transform
from utils.logger import get_logger
import json

logger = get_logger(__name__)

# Configuração do ambiente / Criação de pastas
path = "lake"
output = "output"
year = datetime.now().year
month = datetime.now().month
day = datetime.now().day

logger.info("=" * 60)
logger.info("STARTING JOB SCRAPING ETL PROCESS")
logger.info(f"Date: {year}-{month:02d}-{day:02d}")
logger.info("=" * 60)

utils = Utils()

# Criar estrutura de diretórios
try:
    utils.createDir(f"{path}")
    utils.createDir(f"{path}/{year}")
    utils.createDir(f"{path}/{year}/{month}")
    utils.createDir(f"{path}/{year}/{month}/{day}")
    logger.info("Data lake directory structure created")
except Exception as e:
    logger.error(f"Failed to create directory structure: {e}")
    raise

# Inicializar extrator
extract = Extract(
    urls=urls,
    date={
        "year": year,
        "month": month,
        "day": day
    },
    utils=utils
)

# Queries pré-configuradas
queries = [
    "data analytics",
    "data engineer",
    "data scientist",
    "data analyst",
    "machine learning engineer",
    "business intelligence analyst",
    "ETL developer",
    "big data engineer",
    "database administrator",
    "SQL developer",
    "Python developer data",
    "AI engineer",
    "cloud data engineer",
    "data architect",
    "BI developer",
    "data warehouse specialist",
    "analytics engineer",
    "data governance specialist",
    "quantitative analyst",
    "data product manager"
]

logger.info(f"Processing {len(queries)} search queries")

# Extrair dados para cada query
successful_queries = 0
for idx, query in enumerate(queries, 1):
    logger.info(f"Processing query {idx}/{len(queries)}: '{query}'")
    try:
        if extract.extractData(query=query):
            successful_queries += 1
    except Exception as e:
        logger.error(f"Failed to process query '{query}': {e}", exc_info=True)

logger.info(f"Extraction phase complete: {successful_queries}/{len(queries)} queries successful")

# Transformar dados
logger.info("Starting transformation phase")
transform = Transform()

directories = utils.listDir(f"{path}/{year}/{month}/{day}")
logger.info(f"Found {len(directories)} site directories to process")

processed_sites = 0
total_jobs = 0

for directory in directories:
    try:
        logger.info(f"Processing directory: {directory}")
        files = utils.listDir(f"{path}/{year}/{month}/{day}/{directory}")
        jobs = []
        
        for file_name in files:
            try:
                file_path = f"{path}/{year}/{month}/{day}/{directory}/{file_name}"
                html_text = utils.loadFile(file_path)
                soup = transform.soupHtml(html_text)
                extracted_jobs = transform.getJobs(directory, soup)
                jobs.append(extracted_jobs)
                logger.debug(f"Processed file: {file_name}")
            except Exception as e:
                logger.error(f"Failed to process file {file_name}: {e}")
                continue

        # Criar estrutura de output
        utils.createDir(f"{output}")
        utils.createDir(f"{output}/{year}")
        utils.createDir(f"{output}/{year}/{month}")
        utils.createDir(f"{output}/{year}/{month}/{day}")
        
        # Salvar JSON
        output_file = f"{output}/{year}/{month}/{day}/{directory}.json"
        
        try:
            with open(output_file, 'w', encoding='utf-8') as json_file:
                json.dump(jobs, json_file, ensure_ascii=False, indent=4)
            
            job_count = sum(len(job_list) for job_list in jobs)
            total_jobs += job_count
            processed_sites += 1
            logger.info(f"Saved {job_count} jobs from {directory} to {output_file}")
            
        except IOError as e:
            logger.error(f"Failed to write output file {output_file}: {e}")
            
    except Exception as e:
        logger.error(f"Failed to process directory {directory}: {e}", exc_info=True)

# Sumário final
logger.info("=" * 60)
logger.info("ETL PROCESS COMPLETE")
logger.info(f"Queries processed: {successful_queries}/{len(queries)}")
logger.info(f"Sites processed: {processed_sites}/{len(directories)}")
logger.info(f"Total jobs extracted: {total_jobs}")
logger.info("=" * 60)

print(f"\n✅ ETL process complete!")
print(f"📊 Queries: {successful_queries}/{len(queries)} | Sites: {processed_sites} | Jobs: {total_jobs}")
print(f"📁 Output saved to: {output}/{year}/{month}/{day}/")




