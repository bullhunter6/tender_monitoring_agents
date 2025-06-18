"""
Crawl Log Database Model
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base

class CrawlLog(Base):
    """Log of crawling activities"""
    __tablename__ = "crawl_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    page_id = Column(Integer, ForeignKey("monitored_pages.id"), nullable=False)
    
    # Crawl details
    status = Column(String(50), nullable=False, index=True)  # success, failed, partial
    tenders_found = Column(Integer, default=0)
    tenders_new = Column(Integer, default=0)
    
    # Timing
    started_at = Column(DateTime, default=datetime.utcnow, index=True)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    
    # Error details
    error_message = Column(Text, nullable=True)
    error_type = Column(String(100), nullable=True)
    
    # Relationships
    page = relationship("MonitoredPage", back_populates="crawl_logs")
    
    def __repr__(self):
        return f"<CrawlLog(id={self.id}, page_id={self.page_id}, status='{self.status}', tenders_found={self.tenders_found})>"
    
    @property
    def duration(self) -> int:
        """Calculate duration in seconds"""
        if self.completed_at and self.started_at:
            return int((self.completed_at - self.started_at).total_seconds())
        return 0
