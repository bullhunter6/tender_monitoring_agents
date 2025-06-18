"""
Enhanced Keyword Database Model with Tender Relationships
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base

class Keyword(Base):
    """Enhanced keywords for tender categorization with usage tracking"""
    __tablename__ = "keywords"
    
    id = Column(Integer, primary_key=True, index=True)
    keyword = Column(String(100), nullable=False, index=True)
    category = Column(String(50), nullable=False, index=True)  # esg, credit_rating
    description = Column(String(500), nullable=True)
    
    # Settings
    is_active = Column(Boolean, default=True, index=True)
    case_sensitive = Column(Boolean, default=False)
    
    # NEW: Usage tracking
    usage_count = Column(Integer, default=0)  # How many tenders matched this keyword
    last_used = Column(DateTime, nullable=True)  # When was this keyword last matched
    
    # NEW: Match statistics
    match_statistics = Column(Text, nullable=True)  # JSON string with match stats
    
    # NEW: Many-to-many relationship with tenders
    tenders_using_keyword = relationship(
        "Tender", 
        secondary="tender_keywords", 
        back_populates="matched_keywords"
    )
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Keyword(id={self.id}, keyword='{self.keyword}', category='{self.category}', usage={self.usage_count})>"
    
    def increment_usage(self):
        """Increment usage count and update last used timestamp"""
        self.usage_count += 1
        self.last_used = datetime.utcnow()
        self.updated_at = datetime.utcnow()