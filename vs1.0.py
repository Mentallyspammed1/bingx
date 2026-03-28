```python
import argparse
import asyncio
import json
import logging
import os
import re
import ssl
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import aiohttp
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from tqdm.asyncio import tqdm

CONFIG_FILE = 'config.json'
DEFAULT_CONFIG = {
    "default_engines": ["pexels", "dailymotion", "vimeo"],
    "max_results": 30,
    "output_format": "json",
    "proxy": None,
    "user_agent_rotation": True,
    "thumbnail_download_dir": "thumbnails",
    "search_timeout": 15,
    "log_level": "INFO",
    "download_thumbnails": False,
    "engines": {
        "pexels": {"enabled": True, "base_url": "https://www.pexels.com/search/"},
        "dailymotion": {"enabled": True, "api_url": "https://api.dailymotion.com/videos"},
        "vimeo": {"enabled": True, "api_url": "https://api.vimeo.com/videos"},
        "pornhub": {"enabled": False},
        "xvideos": {"enabled": False}
    }
}

class PyrmethusTool:
    def __init__(self):
        self.config = self._load_config()
        self._setup_logging()
        self.ua = self._init_ua()
        self.session: Optional[aiohttp.ClientSession] = None

    def _load_config(self) -> Dict[str, Any]:
        config = DEFAULT_CONFIG.copy()
        p = Path(CONFIG_FILE)
        if p.exists():
            try:
                with p.open('r', encoding='utf-8') as f:
                    user_config = json.load(f)
                    for k, v in user_config.items():
                        if isinstance(v, dict) and k in config:
                            config[k].update(v)
                        else:
                            config[k] = v
            except (json.JSONDecodeError, Exception) as e:
                print(f"Config Error: {e}. Reverting to defaults.")
        else:
            try:
                with p.open('w', encoding='utf-8') as f:
                    json.dump(DEFAULT_CONFIG, f, indent=4)
            except Exception:
                pass
        return config

    def _setup_logging(self):
        lvl = self.config.get('log_level', 'INFO').upper()
        logging.basicConfig(
            level=getattr(logging, lvl),
            format='[%(asctime)s] %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )

    def _init_ua(self) -> Optional[UserAgent]:
        if self.config.get('user_agent_rotation'):
            try:
                return UserAgent()
            except Exception:
                return None
        return None

    def get_headers(self) -> Dict[str, str]:
        agent = self.ua.random if self.ua else "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/119.0.0.0"
        return {
            "User-Agent": agent,
            "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        }

    async def fetch_raw(self, url: str) -> Optional[Union[str, Dict]]:
        timeout = aiohttp.ClientTimeout(total=self.config.get('search_timeout', 15))
        proxy = self.config.get('proxy')
        try:
            async with self.session.get(url, headers=self.get_headers(), timeout=timeout, proxy=proxy) as resp:
                if resp.status == 200:
                    ctype = resp.headers.get('Content-Type', '')
                    if 'application/json' in ctype:
                        return await resp.json()
                    return await resp.text()
                logging.warning(f"Engine {url} returned status {resp.status}")
        except Exception as e:
            logging.error(f"Fetch failure for {url}: {str(e)}")
        return None

    async def search_pexels(self, query: str, limit: int) -> List[Dict]:
        clean_query = query.replace(' ', '-')
        url = f"{self.config['engines']['pexels']['base_url']}{clean_query}/videos/"
        content = await self.fetch_raw(url)
        results = []
        if isinstance(content, str):
            soup = BeautifulSoup(content, 'lxml' if 'lxml' in sys.modules else 'html.parser')
            for idx, vid in enumerate(soup.select('article')[:limit]):
                link = vid.find('a', href=True)
                img = vid.find('img', src=True)
                if link and img:
                    results.append({
                        "title": img.get('alt', f'Pexels Video {idx}'),
                        "url": f"https://www.pexels.com{link['href']}",
                        "thumbnail_url": img['src'],
                        "source_engine": "pexels"
                    })
        return results

    async def search_dailymotion(self, query: str, limit: int) -> List[Dict]:
        url = f"{self.config['engines']['dailymotion']['api_url']}?search={query}&limit={limit}&fields=title,url,thumbnail_720_url"
        data = await self.fetch_raw(url)
        results = []
        if isinstance(data, dict):
            for item in data.get('list', []):
                results.append({
                    "title": item.get('title'),
                    "url": item.get('url'),
                    "thumbnail_url": item.get('thumbnail_720_url'),
                    "source_engine": "dailymotion"
                })
        return results

    async def search_vimeo(self, query: str, limit: int) -> List[Dict]:
        url = f"{self.config['engines']['vimeo']['api_url']}?query={query}&per_page={limit}"
        data = await self.fetch_raw(url)
        results = []
        if isinstance(data, dict) and 'data' in data:
            for item in data['data']:
                results.append({
                    "title": item.get('name'),
                    "url": item.get('link'),
                    "thumbnail_url": item.get('pictures', {}).get('base_link'),
                    "source_engine": "vimeo"
                })
        return results

    async def perform_search(self, query: str, engines: List[str], limit: int) -> List[Dict]:
        tasks = []
        engine_map = {
            "pexels": self.search_pexels,
            "dailymotion": self.search_dailymotion,
            "vimeo": self.search_vimeo
        }
        
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl.create_default_context())) as session:
            self.session = session
            for engine in engines:
                e_name = engine.lower()
                if e_name in engine_map and self.config['engines'].get(e_name, {}).get('enabled'):
                    tasks.append(engine_map[e_name](query, limit))

            search_results = await tqdm.gather(*tasks, desc="Scrying Digital Realms", leave=True)
            
        unified = []
        for res_list in search_results:
            unified.extend(res_list_dir = Path(self.config.get('thumbnail_download_dir', 'thumbnails'))
        out_dir.mkdir(exist_ok=True)
        
        async with aiohttp.ClientSession() as session:
            tasks = []
            for item in data:
                t_url = item.get('thumbnail_url')
                if t_url:
                    safe_name = re.sub(r'[^\w\-_.]', '_', f"{item['source_engine']}_{item['title'][:30]}") + ".jpg"
                    tasks.append(self._save_img(session, t_url, out_dir / safe_name))
            
            await tqdm.gather(*tasks, desc="Manifesting Imagery", leave=False)

    async def _save_img(self, session: aiohttp.ClientSession, url: str, path: Path):
        try:
            async with session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    path.write_bytes(await resp.read())
        except Exception:
            pass

            filename = f"arcane_results_{timestamp}.html"
        rows = ""
        for item in data:
            rows += f"""
            <div class='card'>
                <img src='{item.get("thumbnail_url", "")}' alt='thumb'>
                <div class='info'>
                    <h3>{item.get("title")}</h3>
                    <p class='engine'>Realm: {item.get("source_engine")}</p>
                    <a href='{item.get("url")}' target='_blank'>Gateway</a>
                </div>
            </div>"""

        html = f"""<!DOCTYPE html><html><head><title>Pyrmethus Search</title>
        <style>
            body {{ background: #121212; color: #e0e0e0; font-family: 'Segoe UI', sans-serif; }}
            .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; padding: 20px; }}
            .card {{ background: #1e1e1e; border-radius: 10px; overflow: hidden; border: 1px solid #333; transition: 0.3s; }}
            .card:hover {{ transform: translateY(-5px); border-color: #bb86fc; }}
            .card img {{ width: 100%; height: 180px; object-fit: cover; }}
            .info {{ padding: 15px; }}
            h3 {{ margin: 0 0 10px; font-size: 16px; height: 40px; overflow: hidden; }}
            .engine {{ color: #03dac6; font-size: 12px; font-weight: bold; text-transform: uppercase; }}
            a {{ display: inline-block; margin-top: 10px; color: #bb86fc; text-decoration: none; border: 1px solid #bb86fc; padding: 5px 15px; border-radius: 5px; }}
            a:hover {{ background: #bb86fc; color: #000; }}
        </style>
        </head><body><div class='grid'>{rows}</div></body></html>"""
        
        Path(filename).write_text(html, encoding='utf-8')
        print(f"\n[!] Arcane Gateway Generated: {filename}")

async def main():
    parser = argparse.ArgumentParser(description="Pyrmethus Advanced Video Search")
    parser.add_argument("query", help="Search query")
    parser.add_argument("-e", "--engines", nargs="+", help="Engines to use")
    parser.add_argument("-n", "--num", type=int, help="Limit results")
    parser.add_argument("-o", "--output", choices=["json", "html", "text"], help="Output format")
    parser.add_argument("-d", "--download", action="store_true", help="Download thumbnails")
    args = parser.parse_args()

    wizard = PyrmethusTool()
    
    target_engines = args.engines if args.engines else wizard.config.get("default_engines")
    res_limit = args.num if args.num else wizard.config.get("max_results")
    out_fmt = args.output if args.output else wizard.config.get("output_format")

    results = await wizard.perform_search(args.query, target_engines, res_limit)

    if not results:
        print("[-] The digital voids returned nothing.")
        return

    if args.download or wizard.config.get("download_thumbnails"):
        await wizard.download_thumbnails(results)

    if out_fmt == "json":
        print(json.dumps(results, indent=2))
    elif out_fmt == "html":
        wizard.export_html(results)
    else:
        for i, r in enumerate(results, 1):
            print(f"{i}. [{r['source_engine']}] {r['title']} -> {r['url']}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        logging.critical(f"A fatal ritual error occurred: {e}")
        sys.exit(1)
```
