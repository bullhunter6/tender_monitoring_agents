"""
Web Scraping Service
Handles crawl4ai integration for web scraping
"""
import asyncio
from typing import Dict, Any, Optional
from crawl4ai import AsyncWebCrawler
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

class TenderScraper:
    """Web scraper for tender pages using crawl4ai"""
    
    def __init__(self):
        self.crawler = None
        self.session_id = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.crawler = AsyncWebCrawler(verbose=False)
        await self.crawler.__aenter__()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.crawler:
            await self.crawler.__aexit__(exc_type, exc_val, exc_tb)
    
    async def scrape_page(self, url: str, **kwargs) -> Dict[str, Any]:
        """
        Scrape a single page and return structured data
        
        Args:
            url: URL to scrape
            **kwargs: Additional crawl4ai parameters
            
        Returns:
            Dict containing status, content, and metadata
        """
        try:
            logger.info(f"Scraping page: {url}")
            
            # Default crawl4ai parameters
            crawl_params = {
                'url': url,
                'word_count_threshold': 10,
                'bypass_cache': True,
                'timeout': settings.REQUEST_TIMEOUT,
                **kwargs
            }
            
            # Perform the crawl
            result = await self.crawler.arun(**crawl_params)
            
            if result.success:
                return {
                    'status': 'success',
                    'url': url,
                    'title': result.metadata.get('title', ''),
                    'markdown': result.markdown,
                    'html': result.html,
                    'links': result.links,
                    'media': result.media,
                    'metadata': result.metadata,
                    'word_count': len(result.markdown.split()) if result.markdown else 0,
                    'char_count': len(result.markdown) if result.markdown else 0
                }
            else:
                logger.error(f"Failed to scrape {url}: {result.error_message}")
                return {
                    'status': 'failed',
                    'url': url,
                    'error': result.error_message,
                    'markdown': '',
                    'html': '',
                    'links': [],
                    'media': [],
                    'metadata': {}
                }
                
        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
            return {
                'status': 'error',
                'url': url,
                'error': str(e),
                'markdown': '',
                'html': '',
                'links': [],
                'media': [],
                'metadata': {}
            }
    
    async def scrape_multiple_pages(self, urls: list, max_concurrent: int = None) -> Dict[str, Dict[str, Any]]:
        """
        Scrape multiple pages concurrently
        
        Args:
            urls: List of URLs to scrape
            max_concurrent: Maximum concurrent requests
            
        Returns:
            Dict mapping URLs to their scrape results
        """
        if max_concurrent is None:
            max_concurrent = settings.MAX_CONCURRENT_CRAWLS
        
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def scrape_with_semaphore(url: str) -> tuple:
            async with semaphore:
                result = await self.scrape_page(url)
                return url, result
        
        # Create tasks for all URLs
        tasks = [scrape_with_semaphore(url) for url in urls]
        
        # Execute all tasks
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        scraped_data = {}
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Error in concurrent scraping: {result}")
                continue
            
            url, data = result
            scraped_data[url] = data
        
        return scraped_data
    
    def extract_links(self, content: str, base_url: str) -> list:
        """
        Extract and normalize links from content
        
        Args:
            content: HTML or markdown content
            base_url: Base URL for relative links
            
        Returns:
            List of normalized URLs
        """
        # This is a simplified implementation
        # In a real scenario, you might want to use BeautifulSoup or similar
        import re
        from urllib.parse import urljoin, urlparse
        
        # Extract URLs from markdown links
        markdown_links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', content)
        
        # Extract URLs from HTML links
        html_links = re.findall(r'href=["\']([^"\']+)["\']', content)
        
        all_links = []
        
        # Process markdown links
        for text, url in markdown_links:
            normalized_url = urljoin(base_url, url)
            if self._is_valid_url(normalized_url):
                all_links.append(normalized_url)
        
        # Process HTML links
        for url in html_links:
            normalized_url = urljoin(base_url, url)
            if self._is_valid_url(normalized_url):
                all_links.append(normalized_url)
        
        return list(set(all_links))  # Remove duplicates
    
    def _is_valid_url(self, url: str) -> bool:
        """Check if URL is valid and not a fragment or mailto link"""
        try:
            parsed = urlparse(url)
            return (
                parsed.scheme in ('http', 'https') and
                parsed.netloc and
                not url.startswith('#') and
                not url.startswith('mailto:')
            )
        except:
            return False
