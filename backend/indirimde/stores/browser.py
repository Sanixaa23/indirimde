"""The one place a real browser is launched for every store adapter.

Turkish shops answer a plain HTTP request with 403 or a bot wall, so the live
fetchers render the page in a headless Chromium (Playwright) and read the same
data the browser sees. Centralising the launch here means every store shares
one user agent, locale, and viewport, and one place to switch to the installed
Google Chrome (INDIRIMDE_BROWSER_CHANNEL=chrome) when a site challenges the
bundled Chromium.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)


@contextmanager
def page(
    timeout_ms: int = 25000,
    headless: bool = True,
    channel: "str | None" = None,
) -> Iterator["object"]:
    """Open a page in a fresh Chromium, yield it, always clean up.

    Each call launches and closes its own browser: slower than pooling but
    stateless and safe to call from FastAPI's thread pool, where several polls
    may run at once.

    `channel` (explicit, else INDIRIMDE_BROWSER_CHANNEL) picks the installed
    Google Chrome, and `headless=False` drives a visible window — some shops
    (Hepsiburada) only let a real, headful Chrome through their bot wall. A
    headful run needs a desktop session (or Xvfb on a server).
    """
    from playwright.sync_api import sync_playwright

    channel = channel or os.environ.get("INDIRIMDE_BROWSER_CHANNEL") or None
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=headless, channel=channel)
        try:
            context = browser.new_context(
                user_agent=USER_AGENT,
                locale="tr-TR",
                viewport={"width": 1366, "height": 900},
            )
            pg = context.new_page()
            pg.set_default_timeout(timeout_ms)
            yield pg
        finally:
            browser.close()
