"""
Page Repository
Database operations for monitored page management
"""
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session

from app.models.page import MonitoredPage

class PageRepository:
    """Repository for monitored page database operations"""
    
    def get_active_pages(self, db: Session) -> List[MonitoredPage]:
        """Get all active monitored pages"""
        return db.query(MonitoredPage).filter(MonitoredPage.is_active == True).all()
    
    def get_all_pages(self, db: Session) -> List[MonitoredPage]:
        """Get all monitored pages"""
        return db.query(MonitoredPage).all()
    
    def get_page_by_id(self, db: Session, page_id: int) -> Optional[MonitoredPage]:
        """Get page by ID"""
        return db.query(MonitoredPage).filter(MonitoredPage.id == page_id).first()
    
    def get_page_by_url(self, db: Session, url: str) -> Optional[MonitoredPage]:
        """Get page by URL"""
        return db.query(MonitoredPage).filter(MonitoredPage.url == url).first()
    
    def create_page(self, db: Session, name: str, url: str, description: str = None, 
                   crawl_frequency_hours: int = 3) -> MonitoredPage:
        """Create a new monitored page"""
        page = MonitoredPage(
            name=name,
            url=url,
            description=description,
            crawl_frequency_hours=crawl_frequency_hours
        )
        db.add(page)
        db.commit()
        db.refresh(page)
        return page
    
    def update_page(self, db: Session, page_id: int, **kwargs) -> Optional[MonitoredPage]:
        """Update a monitored page"""
        page = self.get_page_by_id(db, page_id)
        if not page:
            return None
        
        for key, value in kwargs.items():
            if hasattr(page, key):
                setattr(page, key, value)
        
        page.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(page)
        return page
    
    def delete_page(self, db: Session, page_id: int) -> bool:
        """Delete a monitored page"""
        page = self.get_page_by_id(db, page_id)
        if not page:
            return False
        
        db.delete(page)
        db.commit()
        return True
    
    def update_crawl_status(self, db: Session, page_id: int, success: bool):
        """Update page crawl status"""
        page = self.get_page_by_id(db, page_id)
        if not page:
            return
        
        page.last_crawled = datetime.utcnow()
        
        if success:
            page.consecutive_failures = 0
            page.last_successful_crawl = datetime.utcnow()
        else:
            page.consecutive_failures += 1
        
        db.commit()
