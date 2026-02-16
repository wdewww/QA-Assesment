from typing import Dict, Any
from bs4 import BeautifulSoup
from services.page_fetcher import PageSnapshot
from interfaces.interfaces import DimensionCalculator
from urllib.parse import urljoin
import re
from playwright.sync_api import sync_playwright
import time


class PerformanceCalculator(DimensionCalculator):

    @property
    def name(self) -> str:
        return "Performance"

    def measure_performance(self, url: str) -> Dict[str, Any]:
        
        metrics = {}

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            # Navigate
            page.goto(url, wait_until="load")

            # Extract navigation timing from browser
            timing = page.evaluate("""
                () => {
                    const nav = performance.getEntriesByType('navigation')[0];
                    return {
                        ttfb: nav.responseStart - nav.requestStart,
                        domContentLoaded: nav.domContentLoadedEventEnd,
                        loadEventEnd: nav.loadEventEnd
                    };
                }
            """)

            metrics["ttfb_ms"] = timing["ttfb"]

            # Approximate TTI (heuristic)
            page.wait_for_load_state("networkidle")
            interactive_time = page.evaluate("performance.now()")
            metrics["tti_ms"] = interactive_time

            browser.close()

        return metrics

    def calculate(self, snapshot: PageSnapshot) -> Dict[str, Any]:
        metrics: Dict[str, Any] = {}
        html = snapshot.html
        soup = BeautifulSoup(html, "html.parser")

        # 1. Page size (HTML only)
        page_size_bytes = len(html.encode("utf-8"))
        metrics["page_size_bytes"] = page_size_bytes

        # 2. Image weight estimation
        images = soup.find_all("img")
        total_image_weight = 0
        for img in images:
            width = int(img.get("width") or 0)
            height = int(img.get("height") or 0)
            total_image_weight += width * height * 3  # rough bytes estimate
        metrics["estimated_image_weight_bytes"] = total_image_weight

        # 3. Number of JS & CSS files
        js_files = soup.find_all("script", src=True)
        css_files = soup.find_all("link", rel=lambda x: x and "stylesheet" in x)
        metrics["num_js_files"] = len(js_files)
        metrics["num_css_files"] = len(css_files)

        # 4. Playwright-based metrics
        playwright_metrics = self.measure_performance(snapshot.url)
        metrics.update(playwright_metrics)

        return metrics
