"""Validate job links and remove dead/invalid entries."""
import sqlite3
import requests
import time
import random
from utils.logger import get_logger

logger = get_logger(__name__)

# Headers realistas para evitar bloqueios
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

def validate_link(url: str, timeout: int = 10) -> tuple[bool, int]:
    """
    Valida se um link está acessível.
    
    Returns:
        tuple: (is_valid, status_code)
    """
    try:
        # Pequeno delay para evitar rate limiting
        time.sleep(random.uniform(0.5, 1.5))
        
        response = requests.head(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        status_code = response.status_code
        
        # Considera válido apenas 2xx
        is_valid = 200 <= status_code < 300
        
        logger.debug(f"Validated {url}: {status_code} - {'Valid' if is_valid else 'Invalid'}")
        return is_valid, status_code
        
    except requests.exceptions.Timeout:
        logger.warning(f"Timeout validating {url}")
        return False, 408  # Request Timeout
    except requests.exceptions.ConnectionError:
        logger.warning(f"Connection error for {url}")
        return False, 0  # Connection failed
    except Exception as e:
        logger.error(f"Error validating {url}: {e}")
        return False, 500  # Generic error


def cleanup_invalid_jobs(db_path: str = "jobs.db", batch_size: int = 50) -> dict:
    """
    Valida links no banco de dados e remove vagas inválidas.
    
    Args:
        db_path: Caminho para o banco de dados SQLite
        batch_size: Número de links a validar por execução (para evitar sobrecarga)
    
    Returns:
        dict: Estatísticas da operação
    """
    logger.info("Starting job validation and cleanup process")
    
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()
    
    # Buscar vagas mais antigas primeiro (priorizar validação de links antigos)
    cursor.execute("""
        SELECT id, title, link, company, created_at 
        FROM positions 
        ORDER BY created_at ASC 
        LIMIT ?
    """, (batch_size,))
    
    jobs = cursor.fetchall()
    total_checked = len(jobs)
    
    if total_checked == 0:
        logger.info("No jobs found to validate")
        connection.close()
        return {
            "total_checked": 0,
            "valid": 0,
            "removed": 0,
            "errors": []
        }
    
    logger.info(f"Validating {total_checked} job links...")
    
    valid_count = 0
    removed_count = 0
    errors = []
    
    for job in jobs:
        job_id = job["id"]
        link = job["link"]
        title = job["title"]
        company = job["company"]
        
        is_valid, status_code = validate_link(link)
        
        if is_valid:
            valid_count += 1
        else:
            # Remover vaga inválida
            logger.info(f"Removing invalid job: {title} at {company} (Status: {status_code})")
            cursor.execute("DELETE FROM positions WHERE id = ?", (job_id,))
            removed_count += 1
            errors.append({
                "id": job_id,
                "title": title,
                "company": company,
                "link": link,
                "status_code": status_code
            })
    
    connection.commit()
    connection.close()
    
    stats = {
        "total_checked": total_checked,
        "valid": valid_count,
        "removed": removed_count,
        "errors": errors
    }
    
    logger.info(f"Validation complete: {valid_count} valid, {removed_count} removed")
    
    return stats


def validate_json_jobs(jobs_list: list, max_jobs: int = None) -> tuple[list, dict]:
    """
    Pré-valida uma lista de vagas (normalmente vinda de JSON) antes do load.
    
    Args:
        jobs_list: Lista de dicionários com jobs (deve ter 'title', 'link', 'company')
        max_jobs: Número máximo de jobs a validar (None = todos)
    
    Returns:
        tuple: (valid_jobs, stats_dict)
    """
    logger.info(f"Starting pre-validation of {len(jobs_list)} jobs...")
    
    if max_jobs:
        jobs_list = jobs_list[:max_jobs]
    
    valid_jobs = []
    rejected_jobs = []
    
    for job in jobs_list:
        link = job.get("link", "")
        title = job.get("title", "Unknown")
        company = job.get("company", "Unknown")
        
        # Validações básicas
        if not link or link == "N/A":
            logger.debug(f"Rejected (no link): {title} at {company}")
            rejected_jobs.append({
                "job": job,
                "reason": "missing_link",
                "status_code": None
            })
            continue
        
        # Validação HTTP
        is_valid, status_code = validate_link(link)
        
        if is_valid:
            valid_jobs.append(job)
        else:
            logger.info(f"Rejected (invalid link): {title} at {company} (HTTP {status_code})")
            rejected_jobs.append({
                "job": job,
                "reason": "invalid_link",
                "status_code": status_code
            })
    
    stats = {
        "total": len(jobs_list),
        "valid": len(valid_jobs),
        "rejected": len(rejected_jobs),
        "rejected_details": rejected_jobs
    }
    
    logger.info(f"Pre-validation complete: {stats['valid']} valid, {stats['rejected']} rejected")
    
    return valid_jobs, stats


if __name__ == "__main__":
    # Execução standalone
    print("🔍 Starting job link validation...")
    stats = cleanup_invalid_jobs(batch_size=100)
    
    print("\n" + "="*60)
    print("VALIDATION RESULTS")
    print("="*60)
    print(f"Total checked: {stats['total_checked']}")
    print(f"Valid links: {stats['valid']}")
    print(f"Removed (invalid): {stats['removed']}")
    
    if stats['removed'] > 0:
        print(f"\nRemoved jobs:")
        for error in stats['errors'][:10]:  # Mostrar até 10
            print(f"  - {error['title']} at {error['company']} (HTTP {error['status_code']})")
    
    print("="*60)
