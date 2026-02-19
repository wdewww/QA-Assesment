import httpx
import json
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
from playwright.async_api import async_playwright
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

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

    AVAILABLE_TOOLS = [
        {
            "name": "click",
            "description": "Click on an element. Can target by text content, selector, or aria-label.",
            "parameters": {
                "selector": "CSS selector, text content, or aria-label to click on",
                "timeout": "Maximum time to wait in milliseconds (default: 5000)"
            }
        },
        {
            "name": "fill",
            "description": "Fill/type text into an input field or textarea.",
            "parameters": {
                "selector": "CSS selector or placeholder text of the input field",
                "value": "Text to type into the field"
            }
        },
        {
            "name": "select",
            "description": "Select an option from a dropdown/select element.",
            "parameters": {
                "selector": "CSS selector of the select element",
                "value": "Value or label of the option to select"
            }
        },
        {
            "name": "navigate",
            "description": "Navigate to a different URL.",
            "parameters": {
                "url": "Full URL to navigate to"
            }
        },
        {
            "name": "wait",
            "description": "Wait for a specific element to appear or for a duration.",
            "parameters": {
                "selector": "CSS selector to wait for (optional)",
                "duration": "Time to wait in milliseconds (if no selector provided)"
            }
        },
        {
            "name": "scroll",
            "description": "Scroll the page or a specific element.",
            "parameters": {
                "direction": "Direction to scroll: 'down', 'up', 'bottom', 'top'",
                "selector": "CSS selector of element to scroll (optional, scrolls page if not provided)"
            }
        },
        {
            "name": "hover",
            "description": "Hover over an element to trigger hover effects.",
            "parameters": {
                "selector": "CSS selector or text content of element to hover"
            }
        },
        {
            "name": "press",
            "description": "Press a keyboard key or key combination.",
            "parameters": {
                "key": "Key to press (e.g., 'Enter', 'Tab', 'Escape', 'Control+A')"
            }
        }
    ]

    def __init__(
        self,
        headless: bool = True,
        navigation_timeout: int = 15000,
        llm_model: str = "stepfun/step-3.5-flash:free",
    ):
        self.headless = headless
        self.navigation_timeout = navigation_timeout
        self.llm_model = llm_model
        
        # Configure OpenAI client for OpenRouter
        self.llm_client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")
        )

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

                browser = await p.chromium.launch(headless=self.headless)
                context = await browser.new_context()
                page = await context.new_page()
                
                # Navigate to the initial URL
                try:
                    response = await page.goto(url, timeout=self.navigation_timeout)
                except Exception as e:
                    await browser.close()
                    error_msg = str(e)
                    if "ERR_INTERNET_DISCONNECTED" in error_msg or "ERR_NAME_NOT_RESOLVED" in error_msg:
                        raise PageUnreachableException(f"Unable to reach: {url}")
                    elif "Timeout" in error_msg or "timeout" in error_msg:
                        raise PageTimeoutException(f"Timeout while fetching: {url}")
                    else:
                        raise PageUnreachableException(f"Failed to load page: {url}")
                
                if response:
                    status_code = response.status
                    headers = await self._collect_headers(response)

                # If setup instructions provided, use LLM to interpret and execute them
                if setup_instructions:
                    await self._execute_smart_instructions(page, setup_instructions)
                
                # Get final page state
                final_url = page.url
                html = await page.content()

                with open("debug_page.txt", "w", encoding="utf-8") as f:
                    f.write(html)

                await browser.close()

        except (PageUnreachableException, PageTimeoutException, HTTPErrorException, DOMParsingException):
            raise
        except Exception as e:
            raise PageUnreachableException(f"Unexpected error: {str(e)}")

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
    
    async def _collect_headers(self, response) -> dict:

        headers = {}
        
        # Get all headers including duplicates as list of {name, value} objects
        headers_array = await response.headers_array()
        
        # Build headers dict, collecting Set-Cookie headers into a list
        set_cookie_headers = []
        
        for header in headers_array:
            name = header.get('name', '')
            value = header.get('value', '')
            
            if name.lower() == 'set-cookie':
                set_cookie_headers.append(value)
            else:
                headers[name] = value
        
        # Add all Set-Cookie headers as a list (required for security check)
        if set_cookie_headers:
            headers['set-cookie'] = set_cookie_headers
        
        return headers
    
    async def _execute_smart_instructions(self, page, instructions: Union[str, List[str]]):

        if isinstance(instructions, str):
            instructions = [instructions]
        
        for instruction in instructions:
            print(f"\n🤖 Processing instruction: {instruction}")
            
            # Use LLM to interpret the instruction and choose actions
            actions = await self._interpret_instruction(instruction)
            
            # Execute each action
            for action in actions:
                await self._execute_action(page, action)
    
    async def _interpret_instruction(self, instruction: str) -> List[dict]:

        tools_description = json.dumps(self.AVAILABLE_TOOLS, indent=2)
        
        system_prompt = """You are a browser automation expert. You MUST respond ONLY with valid JSON.
Do not include any explanation, markdown formatting, or extra text.
Your response must be a valid JSON array that can be parsed directly."""
        
        user_prompt = f"""Given a user instruction, determine which browser actions to perform.

Available Tools:
{tools_description}

User Instruction: "{instruction}"

Analyze the instruction and output a JSON array of actions to perform. Each action must have:
- "tool": name of the tool to use (from available tools)
- "params": object with the required parameters for that tool

Rules:
1. Choose the most appropriate tool(s) for the instruction
2. Extract specific values (selectors, text, URLs) from the instruction
3. For clicks, prefer text-based selectors when text is mentioned
4. If multiple steps needed, return multiple actions in order
5. CRITICAL: Return ONLY the JSON array, nothing else. No markdown, no code blocks, no explanation.

Example valid response:
[
  {{"tool": "click", "params": {{"selector": "text=Login", "timeout": 5000}}}},
  {{"tool": "fill", "params": {{"selector": "input[name='username']", "value": "user@example.com"}}}}
]

Now output the JSON array for the instruction above:"""

        response = self.llm_client.chat.completions.create(
            model=self.llm_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1
        )
        
        response_text = response.choices[0].message.content.strip()
        
        # Extract JSON from response (handle markdown code blocks if present)
        json_text = response_text
        if "```json" in response_text:
            json_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            json_text = response_text.split("```")[1].split("```")[0].strip()
        
        try:
            # Handle if response is wrapped in object vs direct array
            parsed = json.loads(json_text)
            if isinstance(parsed, dict) and "actions" in parsed:
                actions = parsed["actions"]
            elif isinstance(parsed, list):
                actions = parsed
            else:
                actions = [parsed]
            
            print(f"LLM planned actions: {json.dumps(actions, indent=2)}")
            return actions
        except json.JSONDecodeError as e:
            print(f"⚠ Failed to parse LLM response as JSON: {e}")
            print(f"Raw response: {response_text}")
            print(f"Extracted JSON text: {json_text}")
            return []
    
    async def _execute_action(self, page, action: dict):

        tool = action.get("tool")
        params = action.get("params", {})
        
        try:
            if tool == "click":
                await self._action_click(page, params)
            elif tool == "fill":
                await self._action_fill(page, params)
            elif tool == "select":
                await self._action_select(page, params)
            elif tool == "navigate":
                await self._action_navigate(page, params)
            elif tool == "wait":
                await self._action_wait(page, params)
            elif tool == "scroll":
                await self._action_scroll(page, params)
            elif tool == "hover":
                await self._action_hover(page, params)
            elif tool == "press":
                await self._action_press(page, params)
            else:
                print(f"⚠ Unknown tool: {tool}")
        except Exception as e:
            print(f"Error executing {tool}: {str(e)}")
            raise
    
    async def _action_click(self, page, params: dict):

        selector = params.get("selector", "")
        timeout = params.get("timeout", 5000)
        
        strategies = [
            # Text-based selectors (most natural)
            lambda s: f'text="{s}"' if not s.startswith(('text=', 'css=', '#', '.', '[')) else s,
            # Exact text match case-insensitive
            lambda s: f'text=/{s}/i',
            # Partial text match in links
            lambda s: f'a:has-text("{s}")',
            # Partial text match in buttons
            lambda s: f'button:has-text("{s}")',
            # Aria-label match
            lambda s: f'[aria-label*="{s}" i]',
            # Direct selector if it looks like CSS
            lambda s: s,
        ]
        
        for strategy in strategies:
            try:
                computed_selector = strategy(selector)
                await page.click(computed_selector, timeout=timeout)
                print(f"✓ Clicked: {selector}")
                await page.wait_for_load_state("networkidle", timeout=10000)
                return
            except Exception:
                continue
        
        # If all strategies failed
        raise Exception(f"Could not click on: {selector}")
    
    async def _action_fill(self, page, params: dict):

        selector = params.get("selector", "")
        value = params.get("value", "")
        
        # Try different selector strategies
        strategies = [
            selector,  # Direct selector
            f'input[placeholder*="{selector}" i]',  # Placeholder match
            f'input[name="{selector}"]',  # Name attribute
            f'textarea[placeholder*="{selector}" i]',  # Textarea
        ]
        
        for strategy in strategies:
            try:
                await page.fill(strategy, value, timeout=5000)
                print(f"✓ Filled '{selector}' with: {value}")
                return
            except Exception:
                continue
        
        raise Exception(f"Could not fill field: {selector}")
    
    async def _action_select(self, page, params: dict):
        """Select dropdown option action handler."""
        selector = params.get("selector", "")
        value = params.get("value", "")
        
        await page.select_option(selector, value, timeout=5000)
        print(f"✓ Selected '{value}' in: {selector}")
    
    async def _action_navigate(self, page, params: dict):

        url = params.get("url", "")
        
        await page.goto(url, timeout=self.navigation_timeout)
        await page.wait_for_load_state("networkidle")
        print(f"✓ Navigated to: {url}")
    
    async def _action_wait(self, page, params: dict):

        selector = params.get("selector")
        duration = params.get("duration", 1000)
        
        if selector:
            await page.wait_for_selector(selector, timeout=duration)
            print(f"✓ Waited for element: {selector}")
        else:
            await page.wait_for_timeout(duration)
            print(f"✓ Waited for: {duration}ms")
    
    async def _action_scroll(self, page, params: dict):

        direction = params.get("direction", "down")
        selector = params.get("selector")
        
        if selector:
            element = await page.query_selector(selector)
            if element:
                await element.scroll_into_view_if_needed()
        else:
            scroll_commands = {
                "down": "window.scrollBy(0, 500)",
                "up": "window.scrollBy(0, -500)",
                "bottom": "window.scrollTo(0, document.body.scrollHeight)",
                "top": "window.scrollTo(0, 0)",
            }
            await page.evaluate(scroll_commands.get(direction, scroll_commands["down"]))
        
        print(f"✓ Scrolled: {direction}")
    
    async def _action_hover(self, page, params: dict):

        selector = params.get("selector", "")
        
        await page.hover(selector, timeout=5000)
        print(f"✓ Hovered over: {selector}")
    
    async def _action_press(self, page, params: dict):

        key = params.get("key", "")
        
        await page.keyboard.press(key)
        print(f"✓ Pressed key: {key}")