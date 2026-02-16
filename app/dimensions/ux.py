from typing import Dict, Any
from bs4 import BeautifulSoup
from services.page_fetcher import PageSnapshot
from interfaces.interfaces import DimensionCalculator
import re


class UxAccessibilityCalculator(DimensionCalculator):

    @property
    def name(self) -> str:
        return "UX & Accessibility"
    
    def calculate(self, snapshot: PageSnapshot) -> Dict[str, Any]:
        metrics: Dict[str, Any] = {}
        html = snapshot.html
        soup = BeautifulSoup(html, "html.parser")
        
        # 1. Title length
        title_tag = soup.find("title")
        title_text = title_tag.get_text(strip=True) if title_tag else ""
        metrics["title_length"] = len(title_text)
        metrics["title_too_long"] = len(title_text) > 60  # typical SEO/UX threshold
        
        # 2. Accessibility issues (creative heuristic)
        accessibility_issues = []
        if not soup.html.get("lang"):
            accessibility_issues.append("Missing <html lang> attribute")
        if not soup.find(["header", "main", "footer", "nav"]):
            accessibility_issues.append("No semantic landmarks detected")
        metrics["accessibility_issues"] = accessibility_issues
        
        # 3. Forms missing labels
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
        metrics["forms_missing_labels"] = forms_missing_labels
        
        # 4. Meta description
        meta_desc_tag = soup.find("meta", attrs={"name": "description"})
        metrics["meta_description"] = meta_desc_tag["content"] if meta_desc_tag and meta_desc_tag.get("content") else ""
        metrics["meta_description_missing"] = meta_desc_tag is None or not meta_desc_tag.get("content")
        
        # 5. Images without alt
        images_without_alt = 0
        for img in soup.find_all("img"):
            if not img.get("alt"):
                images_without_alt += 1
        metrics["images_without_alt"] = images_without_alt
        
        # 6. Contrast warnings on inline styles (basic heuristic)
        low_contrast_elements = 0
        color_regex = re.compile(r"(color\s*:\s*(#[0-9a-fA-F]{3,6}|rgba?\([^)]+\)|[a-zA-Z]+))")
        bg_regex = re.compile(r"(background(-color)?\s*:\s*(#[0-9a-fA-F]{3,6}|rgba?\([^)]+\)|[a-zA-Z]+))")
        for tag in soup.find_all(style=True):
            style = tag["style"]
            color_match = color_regex.search(style)
            bg_match = bg_regex.search(style)
            if color_match and bg_match:
                # simple check: if color and background both exist, flag it
                low_contrast_elements += 1
        metrics["low_contrast_inline_styles"] = low_contrast_elements
        
        # 7. Links without descriptive text
        links_without_text = 0
        for a in soup.find_all("a"):
            if not a.get_text(strip=True):
                links_without_text += 1
        metrics["links_without_text"] = links_without_text
        
        # 8. Heading structure violations (e.g., skipping H1→H3)
        heading_tags = ["h1","h2","h3","h4","h5","h6"]
        last_level = 0
        heading_violations = 0
        for tag in soup.find_all(heading_tags):
            current_level = int(tag.name[1])
            if last_level != 0 and current_level > last_level + 1:
                heading_violations += 1
            last_level = current_level
        metrics["heading_structure_violations"] = heading_violations
        
        return metrics
