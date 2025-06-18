"""
Enhanced Tender Database Models with Keyword Tracking
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, JSON, Table
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base

# Association table for many-to-many relationship between tenders and matched keywords
tender_keywords = Table(
    'tender_keywords',
    Base.metadata,
    Column('tender_id', Integer, ForeignKey('tenders.id'), primary_key=True),
    Column('keyword_id', Integer, ForeignKey('keywords.id'), primary_key=True),
    Column('created_at', DateTime, default=datetime.utcnow)
)

class Tender(Base):
    """Enhanced tender information with keyword tracking"""
    __tablename__ = "tenders"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False, index=True)
    url = Column(String(1000), nullable=False, unique=True, index=True)
    tender_date = Column(DateTime, nullable=True, index=True)
    category = Column(String(50), nullable=False, index=True)  # esg, credit_rating, both
    description = Column(Text, nullable=True)
    
    # NEW: Add matched keywords storage
    matched_keywords_json = Column(JSON, nullable=True)  # Store matched keyword strings
    keyword_count = Column(Integer, default=0)  # Number of keywords matched
    
    # Relationships
    page_id = Column(Integer, ForeignKey("monitored_pages.id"), nullable=False)
    page = relationship("MonitoredPage", back_populates="tenders")
    
    # Detailed tender information
    detailed_tender = relationship("DetailedTender", back_populates="tender", uselist=False)
    
    # NEW: Many-to-many relationship with keywords
    matched_keywords = relationship(
        "Keyword", 
        secondary=tender_keywords, 
        back_populates="tenders_using_keyword"
    )
    
    # Metadata
    is_processed = Column(Boolean, default=False, index=True)
    is_notified = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Tender(id={self.id}, title='{self.title[:50]}...', category='{self.category}', keywords={self.keyword_count})>"

class DetailedTender(Base):
    """Enhanced detailed tender information"""
    __tablename__ = "detailed_tenders"
    
    id = Column(Integer, primary_key=True, index=True)
    tender_id = Column(Integer, ForeignKey("tenders.id"), nullable=False, unique=True)
    
    # Detailed information from Agent 2
    detailed_title = Column(String(1000), nullable=True)
    detailed_description = Column(Text, nullable=True)
    requirements = Column(Text, nullable=True)
    deadline = Column(DateTime, nullable=True)
    contact_info = Column(Text, nullable=True)
    additional_details = Column(Text, nullable=True)
    
    # Full page content
    full_content = Column(Text, nullable=True)
    
    # Processing metadata
    processing_status = Column(String(50), default="pending")  # pending, processed, partial, failed
    ai_response = Column(JSON, nullable=True)  # Store raw AI response
    
    # NEW: Enhanced date validation information
    date_validation = Column(JSON, nullable=True)  # Store date validation results
    
    # Relationships
    tender = relationship("Tender", back_populates="detailed_tender")
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<DetailedTender(id={self.id}, tender_id={self.tender_id}, status='{self.processing_status}')>"