from typing import Optional, Tuple, Dict, Any, List
from bs4 import BeautifulSoup
import requests
from playwright.sync_api import sync_playwright
from urllib.parse import urlparse, urljoin
import re



def calculate_page_size(html: str) -> Optional[int]:
    try:
        return len(html.encode("utf-8"))
    except Exception:
        return None
    
def calculate_estimated_image_weight(soup: BeautifulSoup) -> Optional[int]:
    try:
        images = soup.find_all("img")
        total_image_weight = 0

        for img in images:
            width = int(img.get("width") or 0)
            height = int(img.get("height") or 0)
            total_image_weight += width * height * 3

        return total_image_weight
    except Exception:
        return None

def count_assets(soup: BeautifulSoup) -> Tuple[Optional[int], Optional[int]]:
    try:
        js_files = soup.find_all("script", src=True)
        css_files = soup.find_all("link", rel=lambda x: x and "stylesheet" in x)
        return len(js_files), len(css_files)
    except Exception:
        return None, None
    

def calculate_playwright_metrics(url: str) -> Dict[str, Optional[float]]:
    metrics = {
        "ttfb_ms": None,
        "tti_ms": None,
    }

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            page.goto(url, wait_until="load")

            timing = page.evaluate("""
                () => {
                    const nav = performance.getEntriesByType('navigation')[0];
                    return {
                        ttfb: nav.responseStart - nav.requestStart
                    };
                }
            """)

            metrics["ttfb_ms"] = timing.get("ttfb")

            page.wait_for_load_state("networkidle")
            interactive_time = page.evaluate("performance.now()")
            metrics["tti_ms"] = interactive_time

            browser.close()

    except Exception:
        # return partial results or None
        return metrics

    return metrics


def check_https_tls(url: str) -> Optional[bool]:
    try:
        parsed_url = urlparse(url)
        return parsed_url.scheme == "https"
    except Exception:
        return None

def check_csp(headers: Dict[str, str]) -> Optional[bool]:
    try:
        return "content-security-policy" in (h.lower() for h in headers.keys())
    except Exception:
        return None

def check_secure_cookies(headers: Dict[str, str]) -> Optional[Tuple[int, int]]:
    try:
        total_cookies, secure_cookies = 0, 0

        if "set-cookie" in (h.lower() for h in headers.keys()):
            cookies = headers.get("Set-Cookie") or headers.get("set-cookie")

            if isinstance(cookies, str):
                cookies = [cookies]

            for cookie in cookies:
                total_cookies += 1
                if "Secure" in cookie and "HttpOnly" in cookie:
                    secure_cookies += 1

        return total_cookies, secure_cookies

    except Exception:
        return None
def calculate_sri_coverage(html: str) -> Optional[Tuple[int, int]]:
    try:
        soup = BeautifulSoup(html, "html.parser")
        sri_count = 0
        external_count = 0

        for tag in soup.find_all("script", src=True):
            external_count += 1
            if tag.get("integrity"):
                sri_count += 1

        for tag in soup.find_all("link", href=True, rel=lambda x: x and "stylesheet" in x):
            external_count += 1
            if tag.get("integrity"):
                sri_count += 1

        return sri_count, external_count

    except Exception:
        return None

def detect_outdated_js(html: str) -> Optional[bool]:
    try:
        outdated_patterns = [
            r"jquery-(1|2)\.\d+\.\d+\.js",
            r"angularjs-1\.\d+\.\d+\.js",
        ]

        return any(re.search(p, html, re.IGNORECASE) for p in outdated_patterns)

    except Exception:
        return None

def check_x_frame_options(headers: Dict[str, str]) -> Optional[bool]:
    try:
        xfo = headers.get("X-Frame-Options") or headers.get("x-frame-options")
        return xfo in ["DENY", "SAMEORIGIN"]
    except Exception:
        return None

def check_security_headers(headers: Dict[str, str]) -> Dict[str, Any]:
    try:
        return {
            "strict_transport_security": "strict-transport-security" in (h.lower() for h in headers.keys()),
            "x_content_type_options": headers.get("X-Content-Type-Options", "").lower() == "nosniff",
            "referrer_policy": "referrer-policy" in (h.lower() for h in headers.keys()),
            "permissions_policy": "permissions-policy" in (h.lower() for h in headers.keys())
        }
    except Exception:
        return {
            "strict_transport_security": None,
            "x_content_type_options": None,
            "referrer_policy": None,
            "permissions_policy": None
        }

def check_cors_misconfig(headers: Dict[str, str]) -> Optional[bool]:
    try:
        acao = headers.get("Access-Control-Allow-Origin")
        return acao in ["*", None]
    except Exception:
        return None

def calculate_redirect_chain_length(url: str) -> Optional[int]:
    try:
        response = requests.get(url, allow_redirects=True, timeout=5)
        return len(response.history)
    except requests.RequestException:
        return None
    except Exception:
        return None


def calculate_broken_links(html: str, base_url: str) -> Tuple[Optional[int], Optional[int]]:
    try:
        soup = BeautifulSoup(html, "html.parser")

        broken_links = 0
        total_links = 0

        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]

            if href.startswith("javascript:") or href.startswith("#"):
                continue

            total_links += 1
            full_url = urljoin(base_url, href)
            parsed = urlparse(full_url)

            if parsed.scheme not in ["http", "https"]:
                continue

            try:
                resp = requests.head(full_url, allow_redirects=True, timeout=3)
                if resp.status_code >= 400:
                    broken_links += 1
            except requests.RequestException:
                broken_links += 1

        return broken_links, total_links

    except Exception:
        return None, None


def calculate_missing_meta_tags(html: str) -> Optional[List[str]]:
    try:
        soup = BeautifulSoup(html, "html.parser")

        meta_tags = soup.find_all("meta")
        meta_names = {
            tag.get("name", "").lower()
            for tag in meta_tags
            if tag.get("name")
        }

        required_meta_tags = {"description", "robots", "viewport"}
        missing_meta = required_meta_tags - meta_names

        return list(missing_meta)

    except Exception:
        return None


def analyze_title(html: str) -> Tuple[Optional[int], Optional[bool]]:
    try:
        soup = BeautifulSoup(html, "html.parser")
        title_tag = soup.find("title")
        title_text = title_tag.get_text(strip=True) if title_tag else ""
        length = len(title_text)
        return length, length > 60
    except Exception:
        return None, None

def check_accessibility_landmarks(html: str) -> Optional[List[str]]:
    try:
        soup = BeautifulSoup(html, "html.parser")
        issues = []

        if not soup.html or not soup.html.get("lang"):
            issues.append("Missing <html lang> attribute")

        if not soup.find(["header", "main", "footer", "nav"]):
            issues.append("No semantic landmarks detected")

        return issues

    except Exception:
        return None

def count_forms_missing_labels(html: str) -> Optional[int]:
    try:
        soup = BeautifulSoup(html, "html.parser")
        forms_missing_labels = 0

        for form in soup.find_all("form"):
            inputs = form.find_all("input")
            for input_tag in inputs:
                has_label = False
                input_id = input_tag.get("id")

                if input_id and soup.find("label", attrs={"for": input_id}):
                    has_label = True

                if input_tag.find_parent("label"):
                    has_label = True

                if not has_label:
                    forms_missing_labels += 1

        return forms_missing_labels

    except Exception:
        return None

def analyze_meta_description(html: str) -> Tuple[Optional[str], Optional[bool]]:
    try:
        soup = BeautifulSoup(html, "html.parser")
        meta_desc_tag = soup.find("meta", attrs={"name": "description"})

        if meta_desc_tag and meta_desc_tag.get("content"):
            return meta_desc_tag["content"], False

        return "", True

    except Exception:
        return None, None

def count_images_without_alt(html: str) -> Optional[int]:
    try:
        soup = BeautifulSoup(html, "html.parser")
        count = 0

        for img in soup.find_all("img"):
            if not img.get("alt"):
                count += 1

        return count

    except Exception:
        return None

def detect_low_contrast_inline_styles(html: str) -> Optional[int]:
    try:
        soup = BeautifulSoup(html, "html.parser")
        low_contrast_elements = 0

        color_regex = re.compile(r"(color\s*:\s*(#[0-9a-fA-F]{3,6}|rgba?\([^)]+\)|[a-zA-Z]+))")
        bg_regex = re.compile(r"(background(-color)?\s*:\s*(#[0-9a-fA-F]{3,6}|rgba?\([^)]+\)|[a-zA-Z]+))")

        for tag in soup.find_all(style=True):
            style = tag["style"]
            if color_regex.search(style) and bg_regex.search(style):
                low_contrast_elements += 1

        return low_contrast_elements

    except Exception:
        return None

def count_links_without_text(html: str) -> Optional[int]:
    try:
        soup = BeautifulSoup(html, "html.parser")
        count = 0

        for a in soup.find_all("a"):
            if not a.get_text(strip=True):
                count += 1

        return count

    except Exception:
        return None

def detect_heading_structure_violations(html: str) -> Optional[int]:
    try:
        soup = BeautifulSoup(html, "html.parser")
        heading_tags = ["h1","h2","h3","h4","h5","h6"]

        last_level = 0
        violations = 0

        for tag in soup.find_all(heading_tags):
            current_level = int(tag.name[1])
            if last_level != 0 and current_level > last_level + 1:
                violations += 1
            last_level = current_level

        return violations

    except Exception:
        return None