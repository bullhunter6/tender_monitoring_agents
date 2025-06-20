"""
Fixed System API Routes
app/api/routes/system.py
"""
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from datetime import datetime
import logging

from app.core.database import get_db
from app.services.email_service import EnhancedEmailService
from app.models import MonitoredPage, Tender, Keyword, CrawlLog
from app.repositories.email_settings_repository import EmailSettingsRepository

from pydantic import BaseModel, HttpUrl
from app.services.scraper import TenderScraper

router = APIRouter()

# Add these new models for email settings
class EmailSettings(BaseModel):
    esg_emails: List[EmailStr]
    credit_rating_emails: List[EmailStr]
    notification_preferences: Dict[str, bool] = {
        "send_for_new_tenders": True,
        "send_daily_summary": True,
        "send_urgent_notifications": True
    }

class EmailSettingsResponse(BaseModel):
    success: bool
    message: str
    settings: EmailSettings

class TestEmailRequest(BaseModel):
    email: EmailStr
    category: str  # 'esg' or 'credit_rating'

class AddEmailRequest(BaseModel):
    email: EmailStr

class TestCrawlerRequest(BaseModel):
    url: HttpUrl

logger = logging.getLogger(__name__)

@router.get("/status")
async def get_system_status(db: Session = Depends(get_db)):
    """Get overall system status"""
    # Count various entities
    total_pages = db.query(MonitoredPage).count()
    active_pages = db.query(MonitoredPage).filter(MonitoredPage.is_active == True).count()
    total_tenders = db.query(Tender).count()
    total_keywords = db.query(Keyword).filter(Keyword.is_active == True).count()
    
    # Recent activity
    recent_crawls = db.query(CrawlLog).order_by(CrawlLog.started_at.desc()).limit(5).all()
    
    return {
        "system": {
            "status": "running",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0"
        },
        "database": {
            "total_pages": total_pages,
            "active_pages": active_pages,
            "total_tenders": total_tenders,
            "active_keywords": total_keywords
        },
        "recent_activity": [
            {
                "page_id": log.page_id,
                "status": log.status,
                "tenders_found": log.tenders_found,
                "started_at": log.started_at.isoformat(),
                "duration": log.duration
            }
            for log in recent_crawls
        ]
    }

@router.get("/email-settings", response_model=EmailSettingsResponse)
async def get_email_settings(db: Session = Depends(get_db)):
    """Get current email notification settings from database"""
    try:
        email_repo = EmailSettingsRepository()
        settings_dict = email_repo.get_email_settings(db)
        
        logger.info(f"Retrieved email settings: {settings_dict}")
        
        settings = EmailSettings(
            esg_emails=settings_dict.get('esg_emails', []),
            credit_rating_emails=settings_dict.get('credit_rating_emails', []),
            notification_preferences=settings_dict.get('notification_preferences', {
                "send_for_new_tenders": True,
                "send_daily_summary": True,
                "send_urgent_notifications": True
            })
        )
        
        return EmailSettingsResponse(
            success=True,
            message="Email settings retrieved successfully",
            settings=settings
        )
    except Exception as e:
        logger.error(f"Error retrieving email settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve email settings")

@router.post("/email-settings", response_model=EmailSettingsResponse)
async def save_email_settings(settings: EmailSettings, db: Session = Depends(get_db)):
    """Save email notification settings to database - FIXED VERSION"""
    try:
        logger.info(f"Saving email settings: {settings}")
        
        # Validate email addresses
        if not settings.esg_emails and not settings.credit_rating_emails:
            raise HTTPException(
                status_code=400, 
                detail="At least one email address must be configured"
            )
        
        email_repo = EmailSettingsRepository()
        settings_dict = {
            'esg_emails': settings.esg_emails,
            'credit_rating_emails': settings.credit_rating_emails,
            'notification_preferences': settings.notification_preferences
        }
        
        logger.info(f"Converting settings to dict: {settings_dict}")
        
        success = email_repo.save_email_settings(db, settings_dict)
        
        if success:
            logger.info("Email settings saved successfully")
            return EmailSettingsResponse(
                success=True,
                message="Email settings saved successfully",
                settings=settings
            )
        else:
            logger.error("Failed to save email settings to database")
            raise HTTPException(status_code=500, detail="Failed to save email settings to database")
            
    except Exception as e:
        logger.error(f"Error saving email settings: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save email settings: {str(e)}")

@router.post("/test-email")
async def send_test_email(request: TestEmailRequest, db: Session = Depends(get_db)):
    """Send a test email to verify email configuration"""
    try:
        email_service = EnhancedEmailService()
        email_repo = EmailSettingsRepository()
        
        # Create test tender data based on category
        test_tender_data = {
            'title': f'Test {request.category.upper()} Tender - Email Configuration Test',
            'url': 'https://example.com/test-tender',
            'category': request.category,
            'description': f'This is a test tender for {request.category} team email configuration',
            'matched_keywords': ['test', 'configuration']
        }
        
        # Send test email
        result = await email_service.send_test_intelligent_email(
            recipient=request.email,
            test_tender_data=test_tender_data
        )
        
        # Log the test email attempt
        email_repo.log_email_notification(
            db=db,
            recipient_email=request.email,
            email_type='test',
            team_category=request.category,
            subject=f'Test {request.category.upper()} Email',
            status='sent' if result['status'] == 'success' else 'failed',
            error_message=result.get('message') if result['status'] != 'success' else None
        )
        
        if result['status'] == 'success':
            return {
                "success": True,
                "message": f"Test email sent successfully to {request.email}",
                "details": result.get('message', '')
            }
        else:
            return {
                "success": False,
                "message": f"Failed to send test email: {result.get('message', 'Unknown error')}",
                "details": result.get('message', '')
            }
            
    except Exception as e:
        logger.error(f"Error sending test email: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send test email: {str(e)}")

@router.delete("/email-settings/{category}/{email}")
async def remove_email_from_settings(category: str, email: str, db: Session = Depends(get_db)):
    """Remove an email from notification settings - FIXED VERSION"""
    try:
        if category not in ['esg', 'credit_rating']:
            raise HTTPException(status_code=400, detail="Category must be 'esg' or 'credit_rating'")
        
        logger.info(f"Removing email {email} from {category} category")
        
        email_repo = EmailSettingsRepository()
        success = email_repo.remove_email_from_category(db, category, email)
        
        if success:
            logger.info(f"Successfully removed email {email} from {category}")
            return {
                "success": True,
                "message": f"Email {email} removed from {category} notifications"
            }
        else:
            logger.error(f"Failed to remove email {email} from {category}")
            raise HTTPException(status_code=500, detail="Failed to remove email from database")
            
    except Exception as e:
        logger.error(f"Error removing email: {e}")
        raise HTTPException(status_code=500, detail="Failed to remove email")

@router.post("/email-settings/{category}/add")
async def add_email_to_settings(category: str, request: AddEmailRequest, db: Session = Depends(get_db)):
    """Add an email to notification settings - FIXED VERSION"""
    try:
        if category not in ['esg', 'credit_rating']:
            raise HTTPException(status_code=400, detail="Category must be 'esg' or 'credit_rating'")
        
        logger.info(f"Adding email {request.email} to {category} category")
        
        email_repo = EmailSettingsRepository()
        success = email_repo.add_email_to_category(db, category, request.email)
        
        if success:
            logger.info(f"Successfully added email {request.email} to {category}")
            return {
                "success": True,
                "message": f"Email {request.email} added to {category} notifications"
            }
        else:
            logger.error(f"Failed to add email {request.email} to {category}")
            raise HTTPException(status_code=500, detail="Failed to add email to database")
            
    except Exception as e:
        logger.error(f"Error adding email: {e}")
        raise HTTPException(status_code=500, detail="Failed to add email")

@router.get("/email-logs")
async def get_email_logs(
    limit: int = 50,
    category: str = None,
    status: str = None,
    db: Session = Depends(get_db)
):
    """Get email notification logs"""
    try:
        email_repo = EmailSettingsRepository()
        logs = email_repo.get_email_logs(db, limit, category, status)
        
        return [
            {
                "id": log.id,
                "recipient_email": log.recipient_email,
                "email_type": log.email_type,
                "team_category": log.team_category,
                "subject": log.subject,
                "status": log.status,
                "error_message": log.error_message,
                "tender_id": log.tender_id,
                "sent_at": log.sent_at.isoformat() if log.sent_at else None,
                "created_at": log.created_at.isoformat()
            }
            for log in logs
        ]
        
    except Exception as e:
        logger.error(f"Error retrieving email logs: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve email logs")

@router.get("/logs/crawl")
async def get_crawl_logs(
    limit: int = 50,
    page_id: int = None,
    db: Session = Depends(get_db)
):
    """Get crawl logs"""
    query = db.query(CrawlLog)
    
    if page_id:
        query = query.filter(CrawlLog.page_id == page_id)
    
    logs = query.order_by(CrawlLog.started_at.desc()).limit(limit).all()
    
    return [
        {
            "id": log.id,
            "page_id": log.page_id,
            "page_name": log.page.name if log.page else None,
            "status": log.status,
            "tenders_found": log.tenders_found,
            "tenders_new": log.tenders_new,
            "started_at": log.started_at.isoformat(),
            "completed_at": log.completed_at.isoformat() if log.completed_at else None,
            "duration_seconds": log.duration_seconds,
            "error_message": log.error_message,
            "error_type": log.error_type
        }
        for log in logs
    ]

@router.post("/test-crawler")
async def test_crawler(request: TestCrawlerRequest):
    """Test crawl4ai on a given URL to see if it can extract content"""
    try:
        url = str(request.url)
        logger.info(f"Testing crawler on URL: {url}")
        
        # Use the existing TenderScraper to test the URL
        async with TenderScraper() as scraper:
            result = await scraper.scrape_page(url)
        
        if result['status'] == 'success':
            logger.info(f"Crawler test successful for {url}")
            return {
                'status': 'success',
                'url': url,
                'title': result.get('title', ''),
                'markdown': result.get('markdown', ''),
                'html': result.get('html', ''),
                'links': result.get('links', []),
                'media': result.get('media', []),
                'metadata': result.get('metadata', {}),
                'word_count': result.get('word_count', 0),
                'char_count': result.get('char_count', 0)
            }
        else:
            logger.error(f"Crawler test failed for {url}: {result.get('error', 'Unknown error')}")
            return {
                'status': 'failed',
                'url': url,
                'error': result.get('error', 'Failed to extract content from the page')
            }
            
    except Exception as e:
        logger.error(f"Error testing crawler for {url}: {e}")
        return {
            'status': 'error',
            'url': str(request.url),
            'error': f'Server error while testing crawler: {str(e)}'
        }