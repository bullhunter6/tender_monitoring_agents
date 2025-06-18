# app/models/__init__.py - Add email settings models

from .page import MonitoredPage
from .tender import Tender, DetailedTender
from .keyword import Keyword
from .crawl_log import CrawlLog
from .email_settings import EmailNotificationSettings, EmailNotificationLog

__all__ = [
    'MonitoredPage',
    'Tender', 
    'DetailedTender',
    'Keyword',
    'CrawlLog',
    'EmailNotificationSettings',
    'EmailNotificationLog'
]