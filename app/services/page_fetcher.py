import httpx
from bs4 import BeautifulSoup
from typing import List
from dataclasses import dataclass
from exceptions.exceptions import (
                                    PageUnreachableException,
                                    PageTimeoutException,
                                    HTTPErrorException,
                                    UnsupportedContentTypeException,
                                    EmptyResponseException,
                                    DOMParsingException,
                                )


@dataclass
class PageSnapshot:
    url: str
    status_code: int
    headers: dict
    html: str
    dom: str


class PageFetcher:

    async def fetch(self, url : str, setup_scripts=None):
        # assuming url is correct because of pydantic validation
        try:
            async with httpx.AsyncClient(follow_redirects=True, headers={
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36" 
            )}
        ) as client:
                response = await client.get(url)
        except httpx.ConnectError: # Tested http://localhost:4000
            raise PageUnreachableException(f"Unable to reach: {url}")
        except httpx.ReadTimeout:  # https://httpbin.org/delay/10
            raise PageTimeoutException(f"Timeout while fetching: {url}")
        except httpx.RequestError:
            raise PageUnreachableException(f"Request failed for: {url}")
        
        if response.status_code >= 400:  # https://httpbin.org/status/404
            print("Here ?")
            raise HTTPErrorException(response.status_code)
        
        content_type = response.headers.get("content-type", "")
        if "text/html" not in content_type:  # https://httpbin.org/json
            raise UnsupportedContentTypeException(
                f"Unsupported content type: {content_type}"
            )
        html = response.text.strip()
        if not html:
            raise EmptyResponseException("Empty response body") # https://httpbin.org/status/204
        
        try:
            dom = BeautifulSoup(html, "html.parser")
        except Exception:
            raise DOMParsingException("Failed to parse DOM")
        

        return PageSnapshot(
            url = str(response.url),
            status_code=response.status_code,
            headers = dict(response.headers),
            html = html,
            dom = dom,
        )

        
    async def _setup_page(self, url : str, setup_scripts : str | List[str]):
        pass