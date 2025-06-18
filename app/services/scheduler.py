"""
Updated Background Scheduler Service with Agent 3 Integration
Extended pipeline: Main Page → Agent1 → DB1 → Agent2 → DB2 → Agent3 → Enhanced Email
"""
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import logging
from sqlalchemy.orm import Session

from app.core.database import get_db, SessionLocal
from app.core.config import settings
from app.models import MonitoredPage, DetailedTender, Keyword, CrawlLog
from app.models.tender import Tender
from app.agents import TenderAgent
from app.services.email_service import EnhancedEmailService
from app.repositories.tender_repository import TenderRepository
from app.repositories.page_repository import PageRepository
from app.repositories.keyword_repository import KeywordRepository

logger = logging.getLogger(__name__)

class TenderScheduler:
    """Background scheduler with Agent 3 integration for intelligent email notifications"""
    
    def __init__(self):
        self.tender_agent = TenderAgent()
        self.email_service = EnhancedEmailService()  # Updated to enhanced service
        self.tender_repo = TenderRepository()
        self.page_repo = PageRepository()
        self.keyword_repo = KeywordRepository()
        self.running = False
        self.task = None
    
    async def start(self):
        """Start the periodic crawling scheduler"""
        if self.running:
            return
        
        self.running = True
        logger.info("Starting extended tender monitoring pipeline with Agent 3...")
        logger.info(f"Scheduler will run every {settings.CRAWL_INTERVAL_HOURS} hours")
        logger.info("Extended Pipeline: Main Page -> Agent1 -> DB1 -> Agent2 -> DB2 -> Agent3 -> Enhanced Email")
        
        # Start periodic task
        self.task = asyncio.create_task(self._periodic_task())
    
    async def stop(self):
        """Stop the periodic crawling"""
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info("Scheduler stopped")
    
    async def _periodic_task(self):
        """Internal periodic task runner"""
        interval_seconds = settings.CRAWL_INTERVAL_HOURS * 3600
        
        while self.running:
            try:
                await asyncio.sleep(interval_seconds)
                if self.running:
                    await self.run_extraction_once()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic task: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying
    
    async def run_extraction_once(self):
        """Run the extended extraction pipeline once"""
        logger.info("Starting extended tender extraction cycle with Agent 3...")
        
        db = SessionLocal()
        try:
            # Step 1: Get active monitored pages
            pages = self.page_repo.get_active_pages(db)
            
            if not pages:
                logger.warning("No active monitored pages found")
                return
            
            # Step 2: Get keywords for categorization
            esg_keywords = self.keyword_repo.get_keywords_by_category(db, "esg")
            credit_keywords = self.keyword_repo.get_keywords_by_category(db, "credit_rating")
            
            logger.info(f"Processing {len(pages)} pages")
            logger.info(f"Keywords: {len(esg_keywords)} ESG, {len(credit_keywords)} Credit Rating")
            
            # Step 3: Process each monitored page through extended pipeline
            total_new_tenders = 0
            all_email_compositions = []
            
            for page in pages:
                page_result = await self._process_page_extended_pipeline(db, page, esg_keywords, credit_keywords)
                total_new_tenders += page_result['new_tenders_count']
                all_email_compositions.extend(page_result['email_compositions'])
            
            # Step 4: Send intelligent notifications using Agent 3 compositions
            await self._send_intelligent_notifications(all_email_compositions)
            
            # Step 5: Fallback notifications for any unnotified tenders (if Agent 3 failed)
            await self._send_fallback_notifications(db)
            
            logger.info(f"Extended extraction cycle completed - {total_new_tenders} new tenders processed with {len(all_email_compositions)} intelligent emails")
            
        except Exception as e:
            logger.error(f"Error in extended extraction cycle: {e}")
        finally:
            db.close()
    
    async def _process_page_extended_pipeline(self, db: Session, page: MonitoredPage, 
                                            esg_keywords: List, credit_keywords: List) -> Dict[str, Any]:
        """
        Process a single monitored page through the extended pipeline with Agent 3
        
        Extended Pipeline Flow:
        1. Scrape main page content with crawl4ai
        2. Agent 1: Extract & categorize tenders from main page → Save to DB1
        3. Agent 2: Extract details from individual tender pages → Save to DB2
        4. Agent 3: Compose intelligent email content
        5. Return email compositions for sending
        """
        logger.info(f"Processing page through extended pipeline: {page.name} ({page.url})")
        
        # Create crawl log
        crawl_log = CrawlLog(
            page_id=page.id,
            status="started",
            started_at=datetime.utcnow()
        )
        db.add(crawl_log)
        db.commit()
        
        try:
            # Step 1: Scrape main page content using crawl4ai
            from app.services.scraper import TenderScraper
            
            async with TenderScraper() as scraper:
                logger.info(f"Scraping main page: {page.url}")
                scrape_result = await scraper.scrape_page(page.url)
                
                if scrape_result['status'] != 'success':
                    error_msg = scrape_result.get('error', 'Unknown scraping error')
                    logger.error(f"Failed to scrape main page {page.url}: {error_msg}")
                    
                    # Update crawl log with failure
                    crawl_log.status = "failed"
                    crawl_log.error_message = error_msg
                    crawl_log.completed_at = datetime.utcnow()
                    db.commit()
                    
                    # Update page failure count
                    page.consecutive_failures += 1
                    page.last_crawled = datetime.utcnow()
                    db.commit()
                    return {'new_tenders_count': 0, 'email_compositions': []}
                
                logger.info(f"Successfully scraped main page: {len(scrape_result['markdown'])} characters")
                
                # Step 2-4: Run extended agent workflow (including Agent 3)
                try:
                    logger.info("Starting extended agent pipeline with Agent 3...")
                    
                    result = await self.tender_agent.process_page(
                        page_content=scrape_result['markdown'],
                        page_url=page.url,
                        page_id=page.id,
                        esg_keywords=esg_keywords,
                        credit_keywords=credit_keywords,
                        tender_repo=self.tender_repo,
                        db=db
                    )
                    
                    logger.info("Extended agent pipeline completed")
                    
                except Exception as workflow_error:
                    logger.error(f"Extended agent pipeline failed for page {page.url}: {workflow_error}")
                    
                    # Update crawl log with workflow failure
                    crawl_log.status = "failed"
                    crawl_log.error_message = f"Extended agent pipeline error: {str(workflow_error)}"
                    crawl_log.completed_at = datetime.utcnow()
                    db.commit()
                    
                    # Update page failure count
                    page.consecutive_failures += 1
                    page.last_crawled = datetime.utcnow()
                    db.commit()
                    return {'new_tenders_count': 0, 'email_compositions': []}
                
                # Step 5: Process results
                if result.get('workflow_failed'):
                    error_msg = result.get('error', 'Extended workflow failed')
                    logger.error(f"Extended workflow failed for page {page.url}: {error_msg}")
                    
                    # Update crawl log with workflow failure
                    crawl_log.status = "failed"
                    crawl_log.error_message = error_msg
                    crawl_log.completed_at = datetime.utcnow()
                    db.commit()
                    
                    # Update page failure count
                    page.consecutive_failures += 1
                    page.last_crawled = datetime.utcnow()
                    db.commit()
                    return {'new_tenders_count': 0, 'email_compositions': []}
                
                # Step 6: Log success metrics
                basic_count = result.get('total_saved_basic', 0)
                detailed_count = result.get('total_saved_detailed', 0)
                email_count = result.get('total_email_compositions', 0)
                duplicate_count = result.get('duplicate_count', 0)
                
                logger.info(f"Extended Pipeline Results for {page.name}:")
                logger.info(f"   Basic tenders saved to DB1: {basic_count}")
                logger.info(f"   Detailed tenders saved to DB2: {detailed_count}")
                logger.info(f"   Email compositions created: {email_count}")
                logger.info(f"   Duplicates filtered: {duplicate_count}")
                
                # Update crawl log with success
                crawl_log.status = "completed"
                crawl_log.tenders_found = basic_count
                crawl_log.tenders_new = basic_count
                crawl_log.completed_at = datetime.utcnow()
                db.commit()
                
                # Update page success status
                page.consecutive_failures = 0
                page.last_crawled = datetime.utcnow()
                page.last_successful_crawl = datetime.utcnow()
                db.commit()
                
                logger.info(f"Successfully processed page {page.url} through extended pipeline")
                
                return {
                    'new_tenders_count': basic_count,
                    'email_compositions': result.get('email_compositions', [])
                }
                
        except Exception as e:
            logger.error(f"Error processing page {page.url} through extended pipeline: {e}")
            
            # Update crawl log with error
            crawl_log.status = "failed"
            crawl_log.error_message = str(e)
            crawl_log.completed_at = datetime.utcnow()
            db.commit()
            
            # Update page failure count
            page.consecutive_failures += 1
            page.last_crawled = datetime.utcnow()
            db.commit()
            return {'new_tenders_count': 0, 'email_compositions': []}
    
    async def _send_intelligent_notifications(self, email_compositions: List[Dict[str, Any]]):
        """Send intelligent notifications using Agent 3 composed content"""
        try:
            if not email_compositions:
                logger.info("No email compositions to send")
                return
            
            logger.info(f"Sending {len(email_compositions)} intelligent email notifications...")
            
            # Send all intelligent notifications
            results = await self.email_service.send_intelligent_notifications(email_compositions)
            
            # Log results
            logger.info(f"Intelligent email results:")
            logger.info(f"   Total compositions: {results['total_compositions']}")
            logger.info(f"   Sent successfully: {results['sent_successfully']}")
            logger.info(f"   Failed sends: {results['failed_sends']}")
            
            if results['errors']:
                logger.warning(f"Email sending errors:")
                for error in results['errors']:
                    logger.warning(f"   - {error['tender_title']}: {error['error']}")
            
            if results['sent_emails']:
                logger.info("Successfully sent intelligent emails:")
                for email in results['sent_emails']:
                    logger.info(f"   - {email['tender_title']} to {email['team_category']} team (Priority: {email['priority']})")
            
        except Exception as e:
            logger.error(f"Error sending intelligent notifications: {e}")
    
    async def _send_fallback_notifications(self, db: Session):
        """Send fallback notifications for any unnotified tenders (when Agent 3 fails)"""
        try:
            logger.info("Checking for unnotified tenders (fallback notifications)...")
            
            # Get unnotified ESG tenders
            esg_tenders = self.tender_repo.get_unnotified_tenders(db, "esg")
            if esg_tenders:
                logger.info(f"Sending fallback ESG notification for {len(esg_tenders)} tenders")
                success = await self.email_service.send_fallback_notifications(esg_tenders, "esg")
                if success:
                    for tender in esg_tenders:
                        self.tender_repo.mark_tender_notified(db, tender.id)
                    logger.info(f"Fallback ESG notifications sent for {len(esg_tenders)} tenders")
                else:
                    logger.error("Failed to send fallback ESG notifications")
            
            # Get unnotified Credit Rating tenders
            credit_tenders = self.tender_repo.get_unnotified_tenders(db, "credit_rating")
            if credit_tenders:
                logger.info(f"Sending fallback Credit Rating notification for {len(credit_tenders)} tenders")
                success = await self.email_service.send_fallback_notifications(credit_tenders, "credit_rating")
                if success:
                    for tender in credit_tenders:
                        self.tender_repo.mark_tender_notified(db, tender.id)
                    logger.info(f"Fallback Credit Rating notifications sent for {len(credit_tenders)} tenders")
                else:
                    logger.error("Failed to send fallback Credit Rating notifications")
            
            # Get unnotified 'both' category tenders
            both_tenders = self.tender_repo.get_unnotified_tenders(db, "both")
            if both_tenders:
                logger.info(f"Sending fallback notifications to both teams for {len(both_tenders)} tenders")
                # Send to both teams
                esg_success = await self.email_service.send_fallback_notifications(both_tenders, "esg")
                credit_success = await self.email_service.send_fallback_notifications(both_tenders, "credit_rating")
                
                if esg_success and credit_success:
                    for tender in both_tenders:
                        self.tender_repo.mark_tender_notified(db, tender.id)
                    logger.info(f"Fallback notifications sent to both teams for {len(both_tenders)} tenders")
                else:
                    logger.error("Failed to send fallback notifications to both teams")
            
            if not esg_tenders and not credit_tenders and not both_tenders:
                logger.info("No unnotified tenders found for fallback notifications")
                
        except Exception as e:
            logger.error(f"Error sending fallback notifications: {e}")
    
    async def test_extended_pipeline(self):
        """Test the extended pipeline with Agent 3 (for development)"""
        logger.info("Running extended pipeline test with Agent 3...")
        await self.run_extraction_once()
        logger.info("Extended pipeline test completed")
    
    async def test_agent3_email_composition(self, test_email: str = None):
        """Test Agent 3 email composition and sending"""
        try:
            logger.info("Testing Agent 3 email composition...")
            
            if not test_email:
                # Use ESG team email as default
                test_email = settings.ESG_TEAM_EMAIL
                if not test_email:
                    logger.error("No test email provided and no ESG_TEAM_EMAIL configured")
                    return
            
            # Send test intelligent email
            result = await self.email_service.send_test_intelligent_email(test_email)
            
            if result['status'] == 'success':
                logger.info(f"Agent 3 test email sent successfully to {test_email}")
                logger.info(f"Email preview: {result['email_content_preview']}")
            else:
                logger.error(f"Agent 3 test email failed: {result['message']}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error testing Agent 3 email composition: {e}")
            return {'status': 'failed', 'message': str(e)}

# Additional utility functions for monitoring the extended pipeline
async def test_extended_pipeline():
    """Test function for the extended pipeline with Agent 3"""
    scheduler = TenderScheduler()
    await scheduler.test_extended_pipeline()

async def test_agent3_emails(test_email: str = None):
    """Test Agent 3 email composition"""
    scheduler = TenderScheduler()
    return await scheduler.test_agent3_email_composition(test_email)

def get_extended_pipeline_status():
    """Get status of the extended pipeline including Agent 3"""
    db = SessionLocal()
    try:
        # Get recent crawl logs
        recent_logs = db.query(CrawlLog).order_by(CrawlLog.started_at.desc()).limit(10).all()
        
        # Get unnotified tenders
        tender_repo = TenderRepository()
        unnotified_esg = len(tender_repo.get_unnotified_tenders(db, "esg"))
        unnotified_credit = len(tender_repo.get_unnotified_tenders(db, "credit_rating"))
        unnotified_both = len(tender_repo.get_unnotified_tenders(db, "both"))
        
        # Get recent detailed tenders (for Agent 3 email composition)
        recent_detailed = db.query(DetailedTender).order_by(DetailedTender.created_at.desc()).limit(5).all()
        
        return {
            "status": "extended_pipeline_with_agent3_active",
            "pipeline_version": "3.0",
            "agents_active": ["Agent1_Extract", "Agent2_Details", "Agent3_EmailComposer"],
            "recent_crawls": len(recent_logs),
            "unnotified_tenders": {
                "esg": unnotified_esg,
                "credit_rating": unnotified_credit,
                "both": unnotified_both,
                "total": unnotified_esg + unnotified_credit + unnotified_both
            },
            "recent_detailed_extractions": len(recent_detailed),
            "last_crawl": recent_logs[0].started_at.isoformat() if recent_logs else None,
            "pipeline_flow": "Main Page -> Agent1 -> DB1 -> Agent2 -> DB2 -> Agent3 -> Enhanced Email"
        }
    finally:
        db.close()

if __name__ == "__main__":
    import asyncio
    
    # Test the extended pipeline
    asyncio.run(test_extended_pipeline())