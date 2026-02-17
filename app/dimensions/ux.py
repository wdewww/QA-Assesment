from typing import Dict, Any
from services.page_fetcher import PageSnapshot
from interfaces.interfaces import DimensionCalculator
from .utils import ( analyze_title, check_accessibility_landmarks,
                     count_forms_missing_labels, analyze_meta_description,
                     count_images_without_alt, detect_low_contrast_inline_styles,
                     count_links_without_text, detect_heading_structure_violations )

class UxAccessibilityCalculator(DimensionCalculator):

    @property
    def name(self) -> str:
        return "UX & Accessibility"

    def calculate(self, snapshot: PageSnapshot) -> Dict[str, Any]:
        metrics: Dict[str, Any] = {}

        title_length, title_too_long = analyze_title(snapshot.html)
        metrics["title_length"] = title_length
        metrics["title_too_long"] = title_too_long

        metrics["accessibility_issues"] = check_accessibility_landmarks(snapshot.html)
        metrics["forms_missing_labels"] = count_forms_missing_labels(snapshot.html)

        meta_desc, meta_missing = analyze_meta_description(snapshot.html)
        metrics["meta_description"] = meta_desc
        metrics["meta_description_missing"] = meta_missing

        metrics["images_without_alt"] = count_images_without_alt(snapshot.html)
        metrics["low_contrast_inline_styles"] = detect_low_contrast_inline_styles(snapshot.html)
        metrics["links_without_text"] = count_links_without_text(snapshot.html)
        metrics["heading_structure_violations"] = detect_heading_structure_violations(snapshot.html)

        return metrics
