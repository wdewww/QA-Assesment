from typing import Dict, Any
from bs4 import BeautifulSoup
from services.page_fetcher import PageSnapshot
from interfaces.interfaces import DimensionCalculator
import requests
from urllib.parse import urljoin, urlparse


class TechnicalQualityCalculator(DimensionCalculator):

    @property
    def name(self) -> str:
        return "Technical Quality"
    
    def calculate(self, snapshot: PageSnapshot) -> Dict[str, Any]:
        metrics = {}
        html = snapshot.html
        soup = BeautifulSoup(html, "html.parser")
        
        
        # Redirect chains (simple heuristic)
        # If the response had a "Location" header, there was a redirect
        # For full chain, one would need to follow redirects using requests
        metrics["redirect_chain_length"] = 0
        try:
            response = requests.get(snapshot.url, allow_redirects=True, timeout=5)
            metrics["redirect_chain_length"] = len(response.history)
        except requests.RequestException:
            metrics["redirect_chain_length"] = -1  # error fetching
        
        
        # Broken links
        broken_links = 0
        total_links = 0
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            # Skip empty anchors or javascript links
            if href.startswith("javascript:") or href.startswith("#"):
                continue
            total_links += 1
            full_url = urljoin(snapshot.url, href)
            parsed = urlparse(full_url)
            if parsed.scheme not in ["http", "https"]:
                continue
            try:
                resp = requests.head(full_url, allow_redirects=True, timeout=3)
                if resp.status_code >= 400:
                    broken_links += 1
            except requests.RequestException:
                broken_links += 1
        metrics["broken_links"] = broken_links
        metrics["total_links_checked"] = total_links
        
        # Missing meta tags
        meta_tags = soup.find_all("meta")
        meta_names = {tag.get("name", "").lower() for tag in meta_tags if tag.get("name")}
        required_meta_tags = {"description", "robots", "viewport"}
        missing_meta = required_meta_tags - meta_names
        metrics["missing_meta_tags"] = list(missing_meta)
        return metrics
