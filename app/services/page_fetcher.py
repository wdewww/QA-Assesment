import httpx
import asyncio
from bs4 import BeautifulSoup
from typing import List, Optional, Union
from dataclasses import dataclass
from exceptions.exceptions import (
                                    PageUnreachableException,
                                    PageTimeoutException,
                                    HTTPErrorException,
                                    UnsupportedContentTypeException,
                                    EmptyResponseException,
                                    DOMParsingException,
                                )
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

from langchain.agents import initialize_agent, AgentType
from langchain.tools import Tool
from langchain.chat_models import ChatOpenAI
from langchain_community.agent_toolkits.playwright.toolkit import PlayWrightBrowserToolkit




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



class AgenticPageFetcher:

    def __init__(
        self,
        llm: Optional[ChatOpenAI] = None,
        headless: bool = True,
        navigation_timeout: int = 15000,
    ):
        self.llm = llm or ChatOpenAI(temperature=0)
        self.headless = headless
        self.navigation_timeout = navigation_timeout

    async def fetch(
        self,
        url: str,
        setup_instructions: Optional[Union[str, List[str]]] = None,
    ) -> PageSnapshot:

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=self.headless)
                page = await browser.new_page()
                try:
                    response = await page.goto(
                        url,
                        timeout=self.navigation_timeout,
                        wait_until="domcontentloaded",
                    )

                    if response is None:
                        raise PageUnreachableException(
                            f"No response received from {url}"
                        )

                    status_code = response.status
                    headers = response.headers

                    if status_code >= 400:
                        raise HTTPErrorException(status_code)

                except PlaywrightTimeoutError:
                    raise PageTimeoutException(
                        f"Timeout while loading {url}"
                    )

                if setup_instructions:

                    if isinstance(setup_instructions, list):
                        setup_instructions = "\n".join(setup_instructions)

                    toolkit = PlayWrightBrowserToolkit.from_browser(page)
                    tools = toolkit.get_tools()

                    snapshot_tool = Tool(
                        name="return_snapshot",
                        description=(
                            "Call this tool when all required actions "
                            "have been completed and the page is ready."
                        ),
                        func=lambda _: "SNAPSHOT_READY",
                    )

                    tools.append(snapshot_tool)

                    agent = initialize_agent(
                        tools=tools,
                        llm=self.llm,
                        agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
                        verbose=False,
                    )

                    prompt = f"""
                    You are controlling a real browser.

                    The page is already loaded at: {url}

                    Execute the following instructions carefully:

                    {setup_instructions}

                    When the page is fully prepared and ready for analysis,
                    call the tool: return_snapshot
                    """

                    await asyncio.to_thread(agent.run, prompt)

                await page.wait_for_load_state("networkidle")

                html = await page.content()

                final_url = page.url

                await browser.close()

        except PageTimeoutException:
            raise

        except HTTPErrorException:
            raise

        except Exception as e:
            raise PageUnreachableException(str(e))

        if not html:
            raise DOMParsingException("Empty HTML content after execution")

        try:
            dom = BeautifulSoup(html, "html.parser")
        except Exception:
            raise DOMParsingException("Failed to parse DOM")

        return PageSnapshot(
            url=final_url,
            status_code=status_code,
            headers=headers,
            html=html,
            dom=dom,
        )