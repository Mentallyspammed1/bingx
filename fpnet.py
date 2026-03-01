#!/usr/bin/env python3
import argparse
import json
import logging
import sys
import time
from typing import Dict, List, Optional, Generator, Any, Final, TypedDict
from urllib.parse import quote, urljoin
from pathlib import Path

import requests
from bs4 import BeautifulSoup, SoupStrainer
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class PornHatResult(TypedDict):
    title: str
    url: str
    thumb: str
    duration: str
    views: str

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

class PornHatScraper:
    BASE_URL: Final[str] = "https://www.pornhat.com"
    DEFAULT_HEADERS: Final[Dict[str, str]] = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Referer': f'{BASE_URL}/',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
    }

    __slots__ = ('timeout', 'session', '_strainer')

    def __init__(self, proxy: Optional[str] = None, timeout: int = 15):
        self.timeout = timeout
        self.session = self._init_session(proxy)
        self._strainer = SoupStrainer(['div', 'a', 'img', 'span', 'h3', 'h4'])

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.close()

    def _init_session(self, proxy: Optional[str]) -> requests.Session:
        session = requests.Session()
        retries = Retry(
            total=5,
            backoff_factor=0.3,
            status_forcelist={429, 500, 502, 503, 504},
            raise_on_status=False
        )
        adapter = HTTPAdapter(
            max_retries=retries,
            pool_connections=100,
            pool_maxsize=100,
            pool_block=False
        )
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        session.headers.update(self.DEFAULT_HEADERS)
        if proxy:
            session.proxies = {'http': proxy, 'https': proxy}
        return session

    def search(self, query: str, limit: int = 50, pages: int = 1) -> List[PornHatResult]:
        return list(self.stream_search(query, limit, pages))

    def stream_search(self, query: str, limit: int, pages: int) -> Generator[PornHatResult, None, None]:
        count = 0
        encoded_query = quote(query)

        for page in range(1, pages + 1):
            if count >= limit:
                break

            url = f"{self.BASE_URL}/search/{encoded_query}/"
            if page > 1:
                url = f"{url}?page={page}"

            try:
                logger.info(f"Fetching page {page}: {url}")
                with self.session.get(url, timeout=self.timeout) as response:
                    if response.status_code == 404:
                        logger.warning(f"Page {page} returned 404.")
                        break
                    response.raise_for_status()

                    soup = BeautifulSoup(response.content, 'lxml', parse_only=self._strainer)
                    items = soup.select('div.video-item, div.thumb-video, .item')
                    
                    if not items:
                        logger.info("No more items found.")
                        break

                    for item in items:
                        if count >= limit:
                            return
                        
                        data = self._parse_item(item)
                        if data:
                            yield data
                            count += 1

                if page < pages:
                    time.sleep(0.25)

            except requests.RequestException as e:
                logger.error(f"Network error on page {page}: {e}")
                break
            except Exception as e:
                logger.error(f"Parsing error on page {page}: {e}")
                break

    def _parse_item(self, item: Any) -> Optional[PornHatResult]:
        try:
            link_tag = item.select_one('a[href*="/video/"]')
            if not link_tag:
                return None
            
            href = link_tag.get('href', '')
            url = urljoin(self.BASE_URL, href)
            
            title_tag = item.select_one('.title, h3, h4')
            title = (title_tag.get_text(strip=True) if title_tag else link_tag.get('title', 'Unknown')).strip()

            img = item.find('img')
            thumb = ""
            if img:
                thumb_url = img.get('data-src') or img.get('src') or ""
                thumb = urljoin(self.BASE_URL, thumb_url)

            return {
                'title': title,
                'url': url,
                'thumb': thumb,
                'duration': self._extract_text(item, '.duration, .time'),
                'views': self._extract_text(item, '.views, .metadata')
            }
        except Exception:
            return None

    @staticmethod
    def _extract_text(element: Any, selector: str) -> str:
        target = element.select_one(selector)
        return target.get_text(strip=True) if target else ""

def main():
    parser = argparse.ArgumentParser(description="Optimized PornHat Scraper")
    parser.add_argument("query", help="Search query")
    parser.add_argument("-l", "--limit", type=int, default=50, help="Max results (default: 50)")
    parser.add_argument("-p", "--pages", type=int, default=1, help="Max pages (default: 1)")
    parser.add_argument("-o", "--output", help="Output JSON file path")
    parser.add_argument("--proxy", help="Proxy URL")
    
    args = parser.parse_args()
    
    try:
        with PornHatScraper(proxy=args.proxy) as scraper:
            results = scraper.search(args.query, limit=args.limit, pages=args.pages)
        
        if not results:
            logger.info("No results found.")
            return

        for i, res in enumerate(results, 1):
            print(f"{i:3}. {res['title'][:75]}")
            print(f"     URL: {res['url']}")
            if res['duration'] or res['views']:
                print(f"     [{res['duration']}] | {res['views']}")

        output_path = args.output or f"results_{int(time.time())}.json"
        Path(output_path).write_text(
            json.dumps(results, indent=2, ensure_ascii=False), 
            encoding='utf-8'
        )
        logger.info(f"Exported {len(results)} results to {output_path}")

    except KeyboardInterrupt:
        logger.info("Interrupted by user.")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()