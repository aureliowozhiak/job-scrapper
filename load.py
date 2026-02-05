"""Load module for inserting scraped job data into SQLite database."""
from datetime import datetime
import sqlite3
import json
import os
import sys
from utils.logger import get_logger

logger = get_logger(__name__)

# Configuração: Habilitar pré-validação de links (recomendado)
# Pode ser desabilitado via variável de ambiente para carregamentos rápidos
ENABLE_PRE_VALIDATION = os.getenv("ENABLE_PRE_VALIDATION", "true").lower() == "true"
PRE_VALIDATION_SAMPLE_SIZE = int(os.getenv("PRE_VALIDATION_SAMPLE_SIZE", "100"))  # Valida primeiros N jobs

# Diretório de saída
output_directory = "output"

# Data atual
current_year = datetime.now().year
current_month = datetime.now().month
current_day = datetime.now().day

# Caminho do diretório com os arquivos JSON
json_directory = f"{output_directory}/{current_year}/{current_month}/{current_day}"

logger.info(f"Starting load process for {json_directory}")

if not os.path.exists(json_directory):
    logger.warning(f"Directory '{json_directory}' not found. No data will be processed.")
    print(f"Diretório '{json_directory}' não encontrado. Nenhum dado será processado.")
else:
    # Conexão com banco de dados local
    connection = sqlite3.connect("jobs.db")
    cursor = connection.cursor()
    
    logger.info("Connected to jobs.db")

    # Criar tabela com deduplicação (UNIQUE constraint no link) e timestamps
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            link TEXT NOT NULL UNIQUE,
            company TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Migração automática: Verificar se colunas novas existem
    cursor.execute("PRAGMA table_info(positions)")
    columns = [info[1] for info in cursor.fetchall()]
    
    
    if "created_at" not in columns:
        logger.info("Migrating database: Adding created_at column")
        # SQLite limita defaults dinâmicos em ALTER TABLE, usamos string vazia ou null
        cursor.execute("ALTER TABLE positions ADD COLUMN created_at TIMESTAMP")
        # Atualizar registros existentes com data atual
        cursor.execute("UPDATE positions SET created_at = datetime('now') WHERE created_at IS NULL")
        
    if "updated_at" not in columns:
        logger.info("Migrating database: Adding updated_at column")
        cursor.execute("ALTER TABLE positions ADD COLUMN updated_at TIMESTAMP")
        cursor.execute("UPDATE positions SET updated_at = datetime('now') WHERE updated_at IS NULL")
    
    connection.commit()
    
    # Criar índice para buscas mais rápidas
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_title ON positions(title)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_company ON positions(company)
    """)
    
    logger.info("Database schema created/verified")

    # Lista de arquivos JSON no diretório
    try:
        json_files = os.listdir(json_directory)
        logger.info(f"Found {len(json_files)} files in {json_directory}")
    except FileNotFoundError:
        logger.error(f"Directory '{json_directory}' not found.")
        json_files = []

    # Lista para armazenar os dados JSON
    json_data_list = []

    # Ler e armazenar os conteúdos dos arquivos JSON
    for json_filename in json_files:
        json_filepath = os.path.join(json_directory, json_filename)

        # Verifica se é um arquivo JSON
        if not json_filename.endswith(".json"):
            logger.debug(f"Skipping '{json_filename}' (not a JSON file).")
            continue

        try:
            with open(json_filepath, "r", encoding="utf-8") as json_file:
                data = json.load(json_file)
                if isinstance(data, list):
                    json_data_list.append(data)
                    logger.debug(f"Loaded {json_filename} successfully")
                else:
                    logger.warning(f"File '{json_filename}' does not contain a valid list.")
        except json.JSONDecodeError as e:
            logger.error(f"Error reading '{json_filename}': Invalid JSON - {e}")
        except Exception as e:
            logger.error(f"Unexpected error reading '{json_filename}': {e}")

    # Contadores para estatísticas
    total_processed = 0
    inserted_count = 0
    duplicate_count = 0
    error_count = 0
    pre_validation_rejected = 0

    # Flatten all jobs into a single list for pre-validation
    all_jobs = []
    for json_data in json_data_list:
        for data_entry in json_data:
            all_jobs.extend(data_entry)
    
    logger.info(f"Total jobs loaded from JSON: {len(all_jobs)}")
    
    # Pré-validação (se habilitada)
    if ENABLE_PRE_VALIDATION and len(all_jobs) > 0:
        logger.info(f"Pre-validation ENABLED (sample size: {PRE_VALIDATION_SAMPLE_SIZE})")
        try:
            from validate import validate_json_jobs
            
            # Valida uma amostra para economizar tempo
            sample_to_validate = all_jobs[:PRE_VALIDATION_SAMPLE_SIZE]
            remaining_jobs = all_jobs[PRE_VALIDATION_SAMPLE_SIZE:]
            
            valid_jobs, pre_val_stats = validate_json_jobs(sample_to_validate)
            
            # Combina jobs validados com os não validados (assume válidos se não validou todos)
            jobs_to_process = valid_jobs + remaining_jobs
            pre_validation_rejected = pre_val_stats['rejected']
            
            logger.info(f"Pre-validation: {pre_val_stats['valid']} valid, {pre_val_stats['rejected']} rejected")
        except Exception as e:
            logger.warning(f"Pre-validation failed, proceeding without it: {e}")
            jobs_to_process = all_jobs
    else:
        logger.info("Pre-validation DISABLED")
        jobs_to_process = all_jobs

    # Inserir dados no banco de dados
    for position in jobs_to_process:
        total_processed += 1
        
        try:
            title = position.get("title", "").strip()
            link = str(position.get("link", "")).strip()
            company = position.get("company", "").strip()

            # Validar dados antes de inserir
            if not title or not link or not company:
                logger.warning(f"Skipping invalid data: {position}")
                error_count += 1
                continue
            
            # Evitar links N/A
            if link == "N/A" or link == "":
                logger.debug(f"Skipping job with N/A link: {title}")
                error_count += 1
                continue

            try:
                # INSERT OR IGNORE para deduplicação
                now = datetime.utcnow()
                cursor.execute(
                    """INSERT INTO positions (title, link, company, created_at, updated_at) 
                       VALUES (?, ?, ?, ?, ?)""",
                    (title, link, company, now, now),
                )
                
                if cursor.rowcount > 0:
                    inserted_count += 1
                    logger.debug(f"Inserted: {title} at {company}")
                else:
                    duplicate_count += 1
                    logger.debug(f"Duplicate found: {link}")
                    
            except sqlite3.IntegrityError:
                # Link já existe (violação do UNIQUE constraint)
                duplicate_count += 1
                logger.debug(f"Duplicate job (UNIQUE constraint): {link}")

        except KeyError as e:
            logger.error(f"Missing key {e} in JSON: {position}")
            error_count += 1
        except Exception as e:
            logger.error(f"Unexpected error processing position: {e}", exc_info=True)
            error_count += 1

    # Salvar e fechar conexão
    connection.commit()
    connection.close()
    
    # Estatísticas finais
    logger.info("=" * 60)
    logger.info("LOAD PROCESS COMPLETE")
    logger.info(f"Total processed: {total_processed}")
    logger.info(f"Pre-validation rejected: {pre_validation_rejected}")
    logger.info(f"Successfully inserted: {inserted_count}")
    logger.info(f"Duplicates skipped: {duplicate_count}")
    logger.info(f"Errors: {error_count}")
    logger.info("=" * 60)
    
    print(f"\n✅ Load process complete!")
    print(f"📊 Total: {total_processed} | Pre-rejected: {pre_validation_rejected} | Inserted: {inserted_count} | Duplicates: {duplicate_count} | Errors: {error_count}")

