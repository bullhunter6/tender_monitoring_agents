"""
Keyword Repository
Database operations for keyword management
"""
from typing import List, Optional
from sqlalchemy.orm import Session

from app.models.keyword import Keyword

class KeywordRepository:
    """Repository for keyword database operations"""
    
    def get_keywords_by_category(self, db: Session, category: str) -> List[str]:
        """Get active keywords for a category"""
        keywords = db.query(Keyword).filter(
            Keyword.category == category,
            Keyword.is_active == True
        ).all()
        return [k.keyword for k in keywords]
    
    def get_all_keywords(self, db: Session) -> List[Keyword]:
        """Get all keywords"""
        return db.query(Keyword).all()
    
    def get_keyword_by_id(self, db: Session, keyword_id: int) -> Optional[Keyword]:
        """Get keyword by ID"""
        return db.query(Keyword).filter(Keyword.id == keyword_id).first()
    
    def create_keyword(self, db: Session, keyword: str, category: str, 
                      description: str = None, case_sensitive: bool = False) -> Keyword:
        """Create a new keyword"""
        new_keyword = Keyword(
            keyword=keyword,
            category=category,
            description=description,
            case_sensitive=case_sensitive
        )
        db.add(new_keyword)
        db.commit()
        db.refresh(new_keyword)
        return new_keyword
    
    def update_keyword(self, db: Session, keyword_id: int, **kwargs) -> Optional[Keyword]:
        """Update a keyword"""
        keyword = self.get_keyword_by_id(db, keyword_id)
        if not keyword:
            return None
        
        for key, value in kwargs.items():
            if hasattr(keyword, key):
                setattr(keyword, key, value)
        
        db.commit()
        db.refresh(keyword)
        return keyword
    
    def delete_keyword(self, db: Session, keyword_id: int) -> bool:
        """Delete a keyword"""
        keyword = self.get_keyword_by_id(db, keyword_id)
        if not keyword:
            return False
        
        db.delete(keyword)
        db.commit()
        return True
