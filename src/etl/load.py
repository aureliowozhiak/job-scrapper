"""Load module for inserting scraped job data into SQLite database."""
from datetime import datetime, timezone
import sqlite3
import json
import os
from pathlib import Path
from src.core.logging import get_logger

logger = get_logger(__name__)

# Configuração
ENABLE_PRE_VALIDATION = os.getenv("ENABLE_PRE_VALIDATION", "true").lower() == "true"
PRE_VALIDATION_SAMPLE_SIZE = int(os.getenv("PRE_VALIDATION_SAMPLE_SIZE", "100"))

# Diretórios
output_directory = "output"

def get_current_json_directory():
    """Get current date's JSON directory."""
    current_year = datetime.now().year
    current_month = datetime.now().month
    current_day = datetime.now().day
    return f"{output_directory}/{current_year}/{current_month}/{current_day}"

def get_db_connection():
    """Get connection to SQLite DB."""
    conn = sqlite3.connect("jobs.db")
    conn.row_factory = sqlite3.Row
    return conn

def setup_database(cursor):
    """Setup database schema and migrations."""
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
        cursor.execute("ALTER TABLE positions ADD COLUMN created_at TIMESTAMP")
        cursor.execute("UPDATE positions SET created_at = datetime('now') WHERE created_at IS NULL")
        
    if "updated_at" not in columns:
        logger.info("Migrating database: Adding updated_at column")
        cursor.execute("ALTER TABLE positions ADD COLUMN updated_at TIMESTAMP")
        cursor.execute("UPDATE positions SET updated_at = datetime('now') WHERE updated_at IS NULL")
    
    # Criar índices
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_title ON positions(title)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_company ON positions(company)")
    
    logger.info("Database schema created/verified")

def get_sync_status():
    """Get synchronization status between local JSON files and DB."""
    json_dir = get_current_json_directory()
    
    if not os.path.exists(json_dir):
        return {"status": "no_data", "message": f"Directory {json_dir} not found"}
        
    # Count local jobs
    local_count = 0
    try:
        files = os.listdir(json_dir)
        for f in files:
            if f.endswith(".json"):
                 with open(os.path.join(json_dir, f), 'r', encoding='utf-8') as file:
                    data = json.load(file)
                    if isinstance(data, list):
                        # Flatten if nested
                        for item in data:
                            if isinstance(item, list):
                                local_count += len(item)
                            else:
                                local_count += 1
    except Exception as e:
        logger.error(f"Error counting local jobs: {e}")
        
    # Count db jobs
    db_count = 0
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Count total or just for today? Usually total sync status focuses on 
        # "do we have everything from today?". 
        # But for now, let's just return total db count as a proxy.
        cursor.execute("SELECT COUNT(*) FROM positions")
        db_count = cursor.fetchone()[0]
        conn.close()
    except Exception as e:
        logger.error(f"Error counting db jobs: {e}")

    return {
        "status": "ok",
        "local_jobs_today": local_count,
        "total_db_jobs": db_count,
        "json_directory": json_dir
    }

def run_load_process():
    """Execute the load process."""
    json_directory = get_current_json_directory()
    logger.info(f"Starting load process for {json_directory}")
    
    if not os.path.exists(json_directory):
        logger.warning(f"Directory '{json_directory}' not found.")
        return {"error": "Directory not found", "inserted": 0, "duplicates": 0, "errors": 0}
        
    connection = get_db_connection()
    cursor = connection.cursor()
    
    try:
        setup_database(cursor)
        
        # Load JSON files
        json_data_list = []
        try:
            json_files = os.listdir(json_directory)
            for json_filename in json_files:
                if not json_filename.endswith(".json"):
                    continue
                    
                filepath = os.path.join(json_directory, json_filename)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            json_data_list.append(data)
                except Exception as e:
                    logger.error(f"Error reading {json_filename}: {e}")
        except FileNotFoundError:
            return {"error": "Directory not found during read", "inserted": 0}
            
        # Flatten jobs
        all_jobs = []
        for json_data in json_data_list:
            for data_entry in json_data:
                if isinstance(data_entry, list):
                    all_jobs.extend(data_entry)
                else:
                    all_jobs.append(data_entry) # Start handling direct lists of jobs too
                    
        # Pre-validation
        jobs_to_process = all_jobs
        pre_validation_rejected = 0
        
        if ENABLE_PRE_VALIDATION and len(all_jobs) > 0:
            try:
                from src.etl.validate import validate_json_jobs
                
                sample_size = min(len(all_jobs), PRE_VALIDATION_SAMPLE_SIZE)
                sample = all_jobs[:sample_size]
                remaining = all_jobs[sample_size:]
                
                valid, stats = validate_json_jobs(sample)
                jobs_to_process = valid + remaining
                pre_validation_rejected = stats['rejected']
                logger.info(f"Pre-validation: {stats['valid']} valid, {stats['rejected']} rejected")
            except ImportError:
                 logger.warning("Could not import validation module, skipping pre-validation")
            except Exception as e:
                logger.warning(f"Pre-validation failed: {e}")
        
        # Insert
        stats = {
            "processed": 0,
            "inserted": 0,
            "duplicates": 0,
            "errors": 0,
            "pre_rejected": pre_validation_rejected
        }
        
        for position in jobs_to_process:
            stats["processed"] += 1
            try:
                # Handle nested lists if any remained
                if isinstance(position, list):
                     continue 
                     
                title = position.get("title", "").strip()
                link = str(position.get("link", "")).strip()
                company = position.get("company", "").strip()
                
                if not title or not link or not company or link == "N/A":
                    stats["errors"] += 1
                    continue
                    
                now = datetime.now(timezone.utc)
                
                try:
                    cursor.execute(
                        "INSERT INTO positions (title, link, company, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                        (title, link, company, now, now)
                    )
                    stats["inserted"] += 1
                except sqlite3.IntegrityError:
                    stats["duplicates"] += 1
                    
            except Exception as e:
                logger.error(f"Error processing job: {e}")
                stats["errors"] += 1
                
        connection.commit()
        
        logger.info(f"Load complete. Stats: {stats}")
        return stats
        
    finally:
        connection.close()

if __name__ == "__main__":
    run_load_process()
