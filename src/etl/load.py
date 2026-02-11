"""Load module for inserting scraped job data into SQLite database."""
from datetime import datetime, timezone
from typing import Optional
import sqlite3
import json
import os
from pathlib import Path
from src.core.config import settings
from src.core.logging import get_logger

logger = get_logger(__name__)

# Configuração
PRE_VALIDATION_SAMPLE_SIZE = settings.pre_validation_sample_size

# Diretórios
output_directory = str(settings.output_path)

def get_current_json_directory():
    """Get current date's JSON directory."""
    now_=datetime.now(timezone.utc)
    current_year = now_.year
    current_month = now_.month
    current_day = now_.day
    return f"{output_directory}/{current_year}/{current_month}/{current_day}"

def get_db_connection():
    """Get connection to SQLite DB."""
    db_url = settings.database_url
    db_path = db_url.replace("sqlite:///", "").replace("sqlite://", "")
    
    # Handle relative paths for SQLite
    if db_path.startswith("./"):
        db_path = os.path.join(os.getcwd(), db_path[2:])
    elif not os.path.isabs(db_path):
        db_path = os.path.join(os.getcwd(), db_path)
        
    # Ensure directory exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    conn = sqlite3.connect(db_path)
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
            source TEXT,
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

    if "source" not in columns:
        logger.info("Migrating database: Adding source column")
        cursor.execute("ALTER TABLE positions ADD COLUMN source TEXT")
    
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

def run_load_process(output_dir: Optional[str] = None):
    """Execute the load process.
    
    CRITICAL: This now expects a CONSOLIDATED validated file from the validation step.
    It will ONLY load from validated_jobs_*.json files to avoid re-processing duplicates.
    
    Args:
        output_dir: Specific directory to load files from (if None, uses today's date directory)
    """
    if output_dir:
        json_directory = output_dir
    else:
        json_directory = get_current_json_directory()
    
    logger.info(f"Starting load process for {json_directory}")
    
    if not os.path.exists(json_directory):
        logger.warning(f"Directory '{json_directory}' not found.")
        return {
            "error": "Directory not found",
            "processed": 0,
            "inserted": 0,
            "duplicates": 0,
            "errors": 0,
            "pre_rejected": 0,
            "db_before": 0,
            "db_after": 0,
            "db_new_jobs": 0
        }
        
    connection = get_db_connection()
    cursor = connection.cursor()
    
    try:
        setup_database(cursor)
        
        # ONLY load from validated_jobs_*.json files (consolidated, deduplicated files from validation step)
        json_files = sorted(Path(json_directory).glob("validated_jobs_*.json"))
        
        if not json_files:
            logger.warning("No validated_jobs_*.json files found. Did you run validation step first?")
            return {
                "error": "No validated files found",
                "processed": 0,
                "inserted": 0,
                "duplicates": 0,
                "errors": 0,
                "pre_rejected": 0,
                "db_before": 0,
                "db_after": 0,
                "db_new_jobs": 0
            }
        
        # Use the most recent validated file
        latest_validated_file = json_files[-1]
        logger.info(f"Loading from validated file: {latest_validated_file.name}")
        
        # Load jobs from consolidated file
        all_jobs = []
        try:
            with open(latest_validated_file, "r", encoding="utf-8") as f:
                all_jobs = json.load(f)
                
            if not isinstance(all_jobs, list):
                logger.error(f"Invalid format in {latest_validated_file.name}: Expected list")
                return {"error": "Invalid file format", "processed": 0, "inserted": 0}
                
            logger.info(f"Loaded {len(all_jobs)} jobs from validated file")
        except Exception as e:
            logger.error(f"Error reading validated file: {e}")
            return {"error": f"File read error: {e}", "processed": 0, "inserted": 0}
                    
        # Get existing links for duplicate checking
        cursor.execute("SELECT link FROM positions")
        result = cursor.fetchall()
        existing_links = {row[0] for row in (result or [])}
        db_count_before = len(existing_links)
        logger.info(f"Found {db_count_before} existing jobs in database")
        
        # Insert (jobs are already deduplicated from validation step)
        stats = {
            "processed": len(all_jobs),  # Total jobs examined from validated file
            "inserted": 0,
            "duplicates": 0,
            "errors": 0,
            "db_before": db_count_before
        }
        
        for position in all_jobs:
            try:
                # Normalize field names
                title = position.get("title") or position.get("job_title", "")
                title = title.strip() if title else ""
                
                company = position.get("company", "").strip()
                source = position.get("source", "unknown").strip()
                
                link = position.get("link") or position.get("url", "")
                link = link.strip() if link else ""
                
                if not title or not company or not link:
                    stats["errors"] += 1
                    continue
                
                # Check if already in database
                if link in existing_links:
                    stats["duplicates"] += 1
                    continue
                    
                now = datetime.now(timezone.utc)
                
                try:
                    cursor.execute(
                        "INSERT INTO positions (title, link, company, source, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                        (title, link, company, source, now, now)
                    )
                    stats["inserted"] += 1
                    existing_links.add(link)  # Track newly inserted
                except sqlite3.IntegrityError:
                    stats["duplicates"] += 1
                    
            except Exception as e:
                logger.error(f"Error processing job: {e}")
                stats["errors"] += 1
                
        connection.commit()
        
        # Add final database count
        cursor.execute("SELECT COUNT(*) FROM positions")
        result = cursor.fetchone()
        stats["db_after"] = result[0] if result else db_count_before
        stats["db_new_jobs"] = stats["db_after"] - db_count_before
        
        logger.info(f"Load complete. Processed: {stats['processed']}, Inserted: {stats['inserted']}, Duplicates: {stats['duplicates']}")
        logger.info(f"Database: {db_count_before} → {stats['db_after']} (+{stats['db_new_jobs']} new)")
        
        return {
            "processed": stats["processed"],
            "inserted": stats["inserted"],
            "duplicates": stats["duplicates"],
            "errors": stats["errors"],
            "pre_rejected": 0,
            "db_before": stats["db_before"],
            "db_after": stats["db_after"],
            "db_new_jobs": stats["db_new_jobs"]
        }
        
    finally:
        connection.close()

if __name__ == "__main__":
    run_load_process()
