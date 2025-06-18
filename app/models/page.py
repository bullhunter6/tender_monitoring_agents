"""
Monitored Page Database Model
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base

class MonitoredPage(Base):
    """Pages to monitor for tenders"""
    __tablename__ = "monitored_pages"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, index=True)
    url = Column(String(1000), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    
    # Monitoring settings
    is_active = Column(Boolean, default=True, index=True)
    crawl_frequency_hours = Column(Integer, default=3)  # How often to crawl this page
    
    # Status tracking
    last_crawled = Column(DateTime, nullable=True, index=True)
    last_successful_crawl = Column(DateTime, nullable=True)
    consecutive_failures = Column(Integer, default=0)
    
    # Relationships
    tenders = relationship("Tender", back_populates="page", cascade="all, delete-orphan")
    crawl_logs = relationship("CrawlLog", back_populates="page", cascade="all, delete-orphan")
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<MonitoredPage(id={self.id}, name='{self.name}', url='{self.url}')>"
    
    @property
    def is_healthy(self) -> bool:
        """Check if the page is healthy (not too many consecutive failures)"""
        return self.consecutive_failures < 5
    
    @property
    def status(self) -> str:
        """Get the current status of the page"""
        if not self.is_active:
            return "inactive"
        elif not self.is_healthy:
            return "unhealthy"
        elif self.last_successful_crawl is None:
            return "never_crawled"
        else:
            return "healthy"
