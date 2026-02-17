from typing import Dict, Any
from services.page_fetcher import PageSnapshot
from interfaces.interfaces import DimensionCalculator
from .utils import calculate_redirect_chain_length, calculate_broken_links, calculate_missing_meta_tags

class TechnicalQualityCalculator(DimensionCalculator):

    @property
    def name(self) -> str:
        return "Technical Quality"

    def calculate(self, snapshot: PageSnapshot) -> Dict[str, Any]:
        metrics: Dict[str, Any] = {}

        metrics["redirect_chain_length"] = calculate_redirect_chain_length(snapshot.url)

        broken_links, total_links = calculate_broken_links(
            snapshot.html,
            snapshot.url
        )

        metrics["broken_links"] = broken_links
        metrics["total_links_checked"] = total_links

        metrics["missing_meta_tags"] = calculate_missing_meta_tags(snapshot.html)

        return metrics
