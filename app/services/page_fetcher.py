import httpx
import asyncio
from bs4 import BeautifulSoup
from typing import List, Optional, Union, Callable, Any
from dataclasses import dataclass
from exceptions.exceptions import (
    PageUnreachableException,
    PageTimeoutException,
    HTTPErrorException,
    UnsupportedContentTypeException,
    EmptyResponseException,
    DOMParsingException,
)
# Use create_agent (newer langchain) — you already import it without error
from langchain.agents import create_agent
# Avoid importing langchain.tools.Tool which may not exist in your installed langchain
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.tools.playwright.utils import (
    create_async_playwright_browser,  # A synchronous browser is available, though it isn't compatible with jupyter.\n",   },
)
from langchain_community.agent_toolkits import PlayWrightBrowserToolkit
from langchain_openai import ChatOpenAI
from playwright.async_api import async_playwright

@dataclass
class PageSnapshot:
    url: str
    status_code: int
    headers: dict
    html: str
    dom: str


class PageFetcher:
    async def fetch(self, url: str, setup_scripts=None):
        # assuming url is correct because of pydantic validation
        try:
            async with httpx.AsyncClient(
                follow_redirects=True,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    )
                },
            ) as client:
                response = await client.get(url)
        except httpx.ConnectError:  # Tested http://localhost:4000
            raise PageUnreachableException(f"Unable to reach: {url}")
        except httpx.ReadTimeout:  # https://httpbin.org/delay/10
            raise PageTimeoutException(f"Timeout while fetching: {url}")
        except httpx.RequestError:
            raise PageUnreachableException(f"Request failed for: {url}")

        if response.status_code >= 400:  # https://httpbin.org/status/404
            raise HTTPErrorException(response.status_code)

        content_type = response.headers.get("content-type", "")
        if "text/html" not in content_type:  # https://httpbin.org/json
            raise UnsupportedContentTypeException(
                f"Unsupported content type: {content_type}"
            )
        html = response.text.strip()
        if not html:
            raise EmptyResponseException("Empty response body")  # https://httpbin.org/status/204

        try:
            dom = BeautifulSoup(html, "html.parser")
        except Exception:
            raise DOMParsingException("Failed to parse DOM")

        return PageSnapshot(
            url=str(response.url),
            status_code=response.status_code,
            headers=dict(response.headers),
            html=html,
            dom=dom,
        )

    async def _setup_page(self, url: str, setup_scripts: Union[str, List[str]]):
        # placeholder for any future non-agent setup logic
        raise NotImplementedError


class AgenticPageFetcher:
    def __init__(
        self,
        llm=None,
        headless: bool = True,
        navigation_timeout: int = 15000,
    ):
        self.llm = llm or ChatOpenAI(model="stepfun/step-3.5-flash:free")
        self.headless = headless
        self.navigation_timeout = navigation_timeout

    async def fetch(
        self,
        url: str,
        setup_instructions: Optional[Union[str, List[str]]] = None,
    ) -> PageSnapshot:

        status_code = None
        headers = {}
        html = None
        final_url = url

        try:
            async with async_playwright() as p:

                browser = await p.chromium.launch()
                context = await browser.new_context()
                page = await context.new_page()

                # Create toolkit with existing page
                toolkit = PlayWrightBrowserToolkit.from_browser(
                    async_browser=browser
                )
                tools = toolkit.get_tools()

                agent_chain = create_agent(
                    model=self.llm,
                    tools=tools,
                )

                # Let the agent manipulate the browser
                result = await agent_chain.ainvoke(
                    {
                        "messages": [
                            (
                                "user",
                                f"Navigate to {url}. "
                                f"Then perform: {setup_instructions}"
                            )
                        ]
                    }
                )
                for msg in result["messages"]:
                    print("=" * 50)
                    print(type(msg).__name__)
                    print(msg.content)
                    if hasattr(msg, "tool_calls") and msg.tool_calls:
                        print("Tool calls:", msg.tool_calls)
                final_url = page.url
                html = await page.content()
                response = await page.goto(final_url)
                if response:
                    status_code = response.status
                    headers = response.headers

                await browser.close()

        except Exception as e:
            raise e

        try:
            dom = BeautifulSoup(html, "html.parser")
        except Exception:
            raise DOMParsingException("Failed to parse DOM")

        return PageSnapshot(
            url=final_url,
            status_code=status_code or 0,
            headers=headers,
            html=html,
            dom=dom,
        )