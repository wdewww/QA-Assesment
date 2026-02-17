from typing import Dict, Any
from bs4 import BeautifulSoup
from services.page_fetcher import PageSnapshot
from interfaces.interfaces import DimensionCalculator
from .utils import calculate_page_size, calculate_estimated_image_weight, count_assets, calculate_playwright_metrics


class PerformanceCalculator(DimensionCalculator):

    @property
    def name(self) -> str:
        return "Performance"

    def calculate(self, snapshot: PageSnapshot) -> Dict[str, Any]:
        metrics: Dict[str, Any] = {}

        html = snapshot.html
        soup = BeautifulSoup(html, "html.parser")
        metrics["page_size_bytes"] = calculate_page_size(html)
        metrics["estimated_image_weight_bytes"] = calculate_estimated_image_weight(soup)
        js_count, css_count = count_assets(soup)
        metrics["num_js_files"] = js_count
        metrics["num_css_files"] = css_count
        playwright_metrics = calculate_playwright_metrics(snapshot.url)
        metrics.update(playwright_metrics)

        return metrics
