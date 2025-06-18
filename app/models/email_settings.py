"""
Email Settings Database Model
Create this as app/models/email_settings.py
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON, Text
from datetime import datetime

from app.core.database import Base

class EmailNotificationSettings(Base):
    """Email notification settings storage"""
    __tablename__ = "email_notification_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    setting_key = Column(String(100), nullable=False, unique=True, index=True)  # 'esg_emails', 'credit_emails', 'preferences'
    setting_value = Column(JSON, nullable=False)  # JSON array for emails or object for preferences
    description = Column(Text, nullable=True)  # Optional description
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<EmailNotificationSettings(key='{self.setting_key}', value='{self.setting_value}')>"

class EmailNotificationLog(Base):
    """Log of email notifications sent"""
    __tablename__ = "email_notification_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    recipient_email = Column(String(255), nullable=False, index=True)
    email_type = Column(String(50), nullable=False, index=True)  # 'new_tender', 'daily_summary', 'test', etc.
    team_category = Column(String(50), nullable=False, index=True)  # 'esg', 'credit_rating'
    subject = Column(String(500), nullable=True)
    status = Column(String(50), nullable=False, index=True)  # 'sent', 'failed', 'pending'
    error_message = Column(Text, nullable=True)
    
    # Related data
    tender_id = Column(Integer, nullable=True)  # Link to tender if applicable
    
    # Metadata
    sent_at = Column(DateTime, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<EmailNotificationLog(id={self.id}, recipient='{self.recipient_email}', status='{self.status}')>"