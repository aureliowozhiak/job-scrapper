"""Load module for inserting scraped job data into SQLite database."""
from datetime import datetime
import sqlite3
import json
import os
from utils.logger import get_logger

logger = get_logger(__name__)

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

    # Inserir dados no banco de dados
    for json_data in json_data_list:
        for data_entry in json_data:
            for position in data_entry:
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
                        cursor.execute(
                            """INSERT INTO positions (title, link, company) 
                               VALUES (?, ?, ?)""",
                            (title, link, company),
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
    logger.info(f"Successfully inserted: {inserted_count}")
    logger.info(f"Duplicates skipped: {duplicate_count}")
    logger.info(f"Errors: {error_count}")
    logger.info("=" * 60)
    
    print(f"\n✅ Load process complete!")
    print(f"📊 Total: {total_processed} | Inserted: {inserted_count} | Duplicates: {duplicate_count} | Errors: {error_count}")

