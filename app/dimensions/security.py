from typing import Dict, Any
from services.page_fetcher import PageSnapshot
from interfaces.interfaces import DimensionCalculator
from .utils import (check_https_tls, check_csp, 
                    check_secure_cookies, check_cors_misconfig, 
                    calculate_sri_coverage, detect_outdated_js,
                    check_x_frame_options, check_security_headers)


class SecurityCalculator(DimensionCalculator):

    @property
    def name(self) -> str:
        return "Security"

    def calculate(self, snapshot: PageSnapshot) -> Dict[str, Any]:
        metrics: Dict[str, Any] = {}

        headers = snapshot.headers
        html = snapshot.html
        url = snapshot.url

        metrics["https_tls"] = check_https_tls(url)
        metrics["csp"] = check_csp(headers)
        metrics["secure_cookies"] = check_secure_cookies(headers)
        metrics["sri_coverage"] = calculate_sri_coverage(html)
        metrics["outdated_js"] = detect_outdated_js(html)
        metrics["x_frame_options"] = check_x_frame_options(headers)

        metrics.update(check_security_headers(headers))

        metrics["cors_misconfig"] = check_cors_misconfig(headers)

        return metrics
