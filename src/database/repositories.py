"""Data access layer for job positions."""
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from datetime import datetime, timezone
from src.database.models import Position


class PositionRepository:
    """Repository for position data access."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, title: str, link: str, company: str, source: str = None) -> Position:
        """Create a new position."""
        position = Position(
            title=title,
            link=link,
            company=company,
            source=source
        )
        self.db.add(position)
        self.db.commit()
        self.db.refresh(position)
        return position
    
    def upsert(self, title: str, link: str, company: str, source: str = None) -> Position:
        """Insert or update position if link already exists."""
        position = self.get_by_link(link)
        
        if position:
            # Update existing
            position.title = title
            position.company = company
            if source:
                position.source = source
            position.updated_at = datetime.now(timezone.utc)
            self.db.commit()
            self.db.refresh(position)
        else:
            # Create new
            position = self.create(title, link, company, source)
        
        return position
    
    def get_by_id(self, position_id: int) -> Optional[Position]:
        """Get position by ID."""
        return self.db.query(Position).filter(Position.id == position_id).first()
    
    def get_by_link(self, link: str) -> Optional[Position]:
        """Get position by link."""
        return self.db.query(Position).filter(Position.link == link).first()
    
    def search(self, query: str, limit: int = 100, offset: int = 0) -> List[Position]:
        """Search positions by title or company."""
        return self.db.query(Position).filter(
            or_(
                Position.title.ilike(f"%{query}%"),
                Position.company.ilike(f"%{query}%"),
                Position.source.ilike(f"%{query}%")
            )
        ).order_by(Position.created_at.desc()).limit(limit).offset(offset).all()
    
    def get_all(self, limit: int = 100, offset: int = 0, 
                search: str = None, company: str = None, source: str = None) -> List[Position]:
        """Get all positions with optional filters."""
        query = self.db.query(Position)
        
        if search:
            query = query.filter(
                or_(
                    Position.title.ilike(f"%{search}%"),
                    Position.company.ilike(f"%{search}%"),
                    Position.source.ilike(f"%{search}%")
                )
            )
        
        if company:
            query = query.filter(Position.company.ilike(f"%{company}%"))
        
        if source:
            query = query.filter(Position.source.ilike(f"%{source}%"))
        
        return query.order_by(Position.created_at.desc()).limit(limit).offset(offset).all()
    
    def count(self, search: str = None, company: str = None, source: str = None) -> int:
        """Count positions with optional filters."""
        query = self.db.query(func.count(Position.id))
        
        if search:
            query = query.filter(
                or_(
                    Position.title.ilike(f"%{search}%"),
                    Position.company.ilike(f"%{search}%"),
                    Position.source.ilike(f"%{search}%")
                )
            )
        
        if company:
            query = query.filter(Position.company.ilike(f"%{company}%"))
            
        if source:
            query = query.filter(Position.source.ilike(f"%{source}%"))
        
        return query.scalar()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        total_jobs = self.db.query(func.count(Position.id)).scalar()
        total_companies = self.db.query(func.count(func.distinct(Position.company))).scalar()
        total_sources = self.db.query(func.count(func.distinct(Position.source))).scalar()
        
        return {
            "total_jobs": total_jobs or 0,
            "total_companies": total_companies or 0,
            "total_sources": total_sources or 0
        }
    
    def delete_by_link(self, link: str) -> bool:
        """Delete a position by link."""
        position = self.get_by_link(link)
        if position:
            self.db.delete(position)
            self.db.commit()
            return True
        return False
    
    def bulk_upsert(self, positions: List[Dict[str, str]]) -> Dict[str, int]:
        """Bulk upsert positions. Returns stats."""
        stats = {"inserted": 0, "updated": 0, "errors": 0}
        
        for pos_data in positions:
            try:
                link = pos_data.get("link", "").strip()
                title = pos_data.get("title", "").strip()
                company = pos_data.get("company", "").strip()
                source = pos_data.get("source", "").strip()
                
                if not link or not title or not company:
                    stats["errors"] += 1
                    continue
                
                existing = self.get_by_link(link)
                if existing:
                    existing.title = title
                    existing.company = company
                    if source:
                        existing.source = source
                    existing.updated_at = datetime.now(timezone.utc)
                    stats["updated"] += 1
                else:
                    new_pos = Position(title=title, link=link, company=company, source=source)
                    self.db.add(new_pos)
                    stats["inserted"] += 1
                    
            except Exception as e:
                stats["errors"] += 1
                continue
        
        self.db.commit()
        return stats
