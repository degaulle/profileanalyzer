"""
Website scraping utility for extracting information from personal websites
"""

import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Optional
import re


class WebsiteScraper:
    def __init__(self):
        """Initialize website scraper"""
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

    def scrape_website(self, url: str) -> Dict[str, any]:
        """
        Scrape a personal website and extract relevant information

        Args:
            url: Website URL

        Returns:
            Dictionary with scraped data
        """
        if not url or not url.startswith('http'):
            return {}

        try:
            print(f"Scraping website: {url}")
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Extract data
            data = {
                'url': url,
                'title': self._get_title(soup),
                'description': self._get_description(soup),
                'text_content': self._get_text_content(soup),
                'links': self._get_links(soup, url),
                'emails': self._extract_emails(soup),
                'social_links': self._extract_social_links(soup),
                'keywords': self._extract_keywords(soup),
                'images': self._get_images(soup, url)[:10]  # Limit to 10 images
            }

            print(f"Successfully scraped website: {url}")
            return data

        except Exception as e:
            print(f"Error scraping website {url}: {e}")
            return {'url': url, 'error': str(e)}

    def _get_title(self, soup: BeautifulSoup) -> str:
        """Extract page title"""
        if soup.title:
            return soup.title.string.strip()

        # Try og:title
        og_title = soup.find('meta', property='og:title')
        if og_title and og_title.get('content'):
            return og_title['content'].strip()

        # Try h1
        h1 = soup.find('h1')
        if h1:
            return h1.get_text().strip()

        return ''

    def _get_description(self, soup: BeautifulSoup) -> str:
        """Extract page description"""
        # Try meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            return meta_desc['content'].strip()

        # Try og:description
        og_desc = soup.find('meta', property='og:description')
        if og_desc and og_desc.get('content'):
            return og_desc['content'].strip()

        # Get first paragraph
        p = soup.find('p')
        if p:
            return p.get_text().strip()[:500]

        return ''

    def _get_text_content(self, soup: BeautifulSoup) -> str:
        """Extract main text content"""
        # Remove script and style elements
        for script in soup(['script', 'style', 'nav', 'footer', 'header']):
            script.decompose()

        # Get text
        text = soup.get_text()
        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)

        # Limit text length
        return text[:5000]

    def _get_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extract links from page"""
        links = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            if href.startswith('http'):
                links.append(href)
            elif href.startswith('/'):
                from urllib.parse import urljoin
                links.append(urljoin(base_url, href))

        return list(set(links))[:20]  # Limit to 20 unique links

    def _get_images(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extract image URLs"""
        images = []
        for img in soup.find_all('img', src=True):
            src = img['src']
            if src.startswith('http'):
                images.append(src)
            elif src.startswith('/'):
                from urllib.parse import urljoin
                images.append(urljoin(base_url, src))

        return list(set(images))

    def _extract_emails(self, soup: BeautifulSoup) -> List[str]:
        """Extract email addresses"""
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        text = soup.get_text()
        emails = re.findall(email_pattern, text)
        return list(set(emails))

    def _extract_social_links(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract social media links"""
        social_platforms = {
            'twitter': ['twitter.com', 'x.com'],
            'instagram': ['instagram.com'],
            'linkedin': ['linkedin.com'],
            'github': ['github.com'],
            'facebook': ['facebook.com'],
            'youtube': ['youtube.com'],
            'tiktok': ['tiktok.com']
        }

        social_links = {}
        for a in soup.find_all('a', href=True):
            href = a['href']
            for platform, domains in social_platforms.items():
                if any(domain in href for domain in domains):
                    if platform not in social_links:
                        social_links[platform] = href

        return social_links

    def _extract_keywords(self, soup: BeautifulSoup) -> List[str]:
        """Extract keywords from meta tags"""
        keywords = []

        # Try meta keywords
        meta_keywords = soup.find('meta', attrs={'name': 'keywords'})
        if meta_keywords and meta_keywords.get('content'):
            keywords.extend([k.strip() for k in meta_keywords['content'].split(',')])

        # Try meta tags
        og_tags = soup.find_all('meta', property=lambda x: x and x.startswith('og:'))
        for tag in og_tags:
            content = tag.get('content', '')
            if content:
                keywords.append(content)

        return list(set(keywords))[:10]
