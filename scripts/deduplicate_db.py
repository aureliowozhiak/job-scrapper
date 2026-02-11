#!/usr/bin/env python3
"""
Database Deduplication Script

Removes duplicate entries from the database based on the 'link' field.
Keeps the oldest entry (first created_at timestamp) for each unique link.
"""
import sqlite3
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.config import settings
from src.core.logging import get_logger

logger = get_logger(__name__)


def get_db_path():
    """Get database path from settings."""
    db_url = settings.database_url
    db_path = db_url.replace("sqlite:///", "").replace("sqlite://", "")
    
    if db_path.startswith("./"):
        db_path = project_root / db_path[2:]
    elif not Path(db_path).is_absolute():
        db_path = project_root / db_path
    
    return str(db_path)


def deduplicate_database():
    """Remove duplicate entries based on link field."""
    db_path = get_db_path()
    
    logger.info(f"Connecting to database: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Count before
        cursor.execute("SELECT COUNT(*) FROM positions")
        count_before = cursor.fetchone()[0]
        logger.info(f"Database has {count_before} entries")
        
        # Find duplicates
        cursor.execute("""
            SELECT link, COUNT(*) as count
            FROM positions
            GROUP BY link
            HAVING count > 1
        """)
        duplicates = cursor.fetchall()
        
        if not duplicates:
            logger.info("✅ No duplicates found!")
            return
        
        logger.info(f"Found {len(duplicates)} duplicate links")
        
        # For each duplicate link, keep oldest and delete others
        deleted_count = 0
        for link, count in duplicates:
            logger.info(f"Deduplicating: {link} ({count} occurrences)")
            
            # Get IDs sorted by created_at (oldest first)
            cursor.execute("""
                SELECT id FROM positions
                WHERE link = ?
                ORDER BY created_at ASC
            """, (link,))
            
            ids = [row[0] for row in cursor.fetchall()]
            
            # Keep first (oldest), delete rest
            if len(ids) > 1:
                ids_to_delete = ids[1:]
                placeholders = ','.join('?' * len(ids_to_delete))
                cursor.execute(f"""
                    DELETE FROM positions
                    WHERE id IN ({placeholders})
                """, ids_to_delete)
                
                deleted_count += len(ids_to_delete)
                logger.debug(f"  Kept ID {ids[0]}, deleted {len(ids_to_delete)} duplicates")
        
        conn.commit()
        
        # Count after
        cursor.execute("SELECT COUNT(*) FROM positions")
        count_after = cursor.fetchone()[0]
        
        logger.info("=" * 60)
        logger.info(f"✅ Deduplication complete!")
        logger.info(f"   Before: {count_before} entries")
        logger.info(f"   After:  {count_after} entries")
        logger.info(f"   Deleted: {deleted_count} duplicates")
        logger.info("=" * 60)
        
        # Verify no duplicates remain
        cursor.execute("""
            SELECT COUNT(DISTINCT link), COUNT(*)
            FROM positions
        """)
        unique_links, total = cursor.fetchone()
        
        if unique_links == total:
            logger.info(f"✅ Verification passed: {total} entries, all unique")
        else:
            logger.error(f"⚠️ Verification failed: {total} entries but only {unique_links} unique links")
        
    except Exception as e:
        logger.error(f"Error during deduplication: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    logger.info("Starting database deduplication...")
    deduplicate_database()
    logger.info("Done!")
