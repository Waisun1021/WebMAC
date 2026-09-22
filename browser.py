from threading import Event
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page
from playwright._impl._errors import TargetClosedError
import sys
import os

# append parent directory to PATH to import own modules
sys.path.append(os.path.dirname(os.path.abspath(os.getcwd())))

from config_for_clarify import DEFAULT_CDP_PORT


def open_browser_session(url: str, e: Event, f: Event) -> None:
    """開啟 Chromium 並進入指定網址。"""

    with sync_playwright() as playwright:
        browser = None

        try:
            browser = playwright.chromium.launch(
                headless=False,
                args=[
                    f"--remote-debugging-port={DEFAULT_CDP_PORT}",
                    "--disable-dev-shm-usage"
                ]
            )

            context: BrowserContext = browser.new_context()
            page: Page = context.new_page()

            page.goto(url)
            page.wait_for_load_state("domcontentloaded")

            e.set()

            # 保持瀏覽器開啟，直到 WebMAC 通知關閉
            f.wait()

        except TargetClosedError as error:
            print(f"瀏覽器被提前關閉：{error}")

        except Exception as error:
            print(f"啟動瀏覽器時發生錯誤：{type(error).__name__}: {error}")
            e.set()

        finally:
            if browser is not None:
                browser.close()
