from typing import Dict, Any
from services.page_fetcher import PageSnapshot
from interfaces.interfaces import DimensionCalculator
from urllib.parse import urlparse
import re
from bs4 import BeautifulSoup

class SecurityCalculator(DimensionCalculator):

    @property
    def name(self) -> str:
        return "Security"
    
    def calculate(self, snapshot: PageSnapshot) -> Dict[str, Any]:
        metrics = {}

        headers = snapshot.headers
        html = snapshot.html
        url = snapshot.url

        # HTTPS / TLS Security
        parsed_url = urlparse(url)
        metrics["https_tls"] = parsed_url.scheme == "https"

        # Content Security Policy (CSP)
        metrics["csp"] = "content-security-policy" in (h.lower() for h in headers.keys())


        # Secure Cookies
        total_cookies, secure_cookies = 0, 0
        if "set-cookie" in (h.lower() for h in headers.keys()):
            cookies = headers.get("Set-Cookie") or headers.get("set-cookie")
            if isinstance(cookies, str):
                cookies = [cookies]
            for cookie in cookies:
                total_cookies += 1
                if "Secure" in cookie and "HttpOnly" in cookie:
                    secure_cookies += 1
        metrics["secure_cookies"] = (total_cookies, secure_cookies)


        # Subresource Integrity (SRI)
        soup = BeautifulSoup(html, "html.parser")
        sri_count = 0
        external_count = 0
        # scripts
        for tag in soup.find_all("script", src=True):
            external_count += 1
            if tag.get("integrity"):
                sri_count += 1
        # stylesheets
        for tag in soup.find_all("link", href=True, rel=lambda x: x and "stylesheet" in x):
            external_count += 1
            if tag.get("integrity"):
                sri_count += 1
        metrics["sri_coverage"] = (sri_count, external_count)

        # Outdated JS (not accurate we can not use JS here)
        outdated_patterns = [
            r"jquery-(1|2)\.\d+\.\d+\.js",  # old jQuery
            r"angularjs-1\.\d+\.\d+\.js",
        ]
        metrics["outdated_js"] = any(re.search(p, html, re.IGNORECASE) for p in outdated_patterns)

        # X-Frame-Options
        xfo = headers.get("X-Frame-Options") or headers.get("x-frame-options")
        metrics["x_frame_options"] = xfo in ["DENY", "SAMEORIGIN"]

        # Security headers
        security_headers = {
            "strict_transport_security": "strict-transport-security" in (h.lower() for h in headers.keys()),
            "x_content_type_options": headers.get("X-Content-Type-Options", "").lower() == "nosniff",
            "referrer_policy": "referrer-policy" in (h.lower() for h in headers.keys()),
            "permissions_policy": "permissions-policy" in (h.lower() for h in headers.keys())
        }
        metrics.update(security_headers)

        # 8. CORS Misconfigurations (Access-Control-Allow-Origin)
        acao = headers.get("Access-Control-Allow-Origin")
        metrics["cors_misconfig"] = acao in ["*", None]

        return metrics