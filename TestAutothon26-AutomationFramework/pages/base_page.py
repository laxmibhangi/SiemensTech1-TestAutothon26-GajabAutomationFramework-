"""Base page object - every page inherits these interaction primitives."""
from __future__ import annotations

import re
import time
from datetime import datetime
from pathlib import Path

from selenium.common.exceptions import (
    ElementClickInterceptedException,
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from config.settings import SCREENSHOT_DIR, config
from core.logger import get_logger

log = get_logger(__name__)

Locator = tuple[str, str]


class BasePage:
    def __init__(self, driver: WebDriver):
        self.driver = driver
        # This app re-renders continuously (live feed, carousels, hydration), so
        # stale references are normal rather than exceptional.
        self.wait = WebDriverWait(
            driver,
            config.EXPLICIT_WAIT,
            ignored_exceptions=(
                NoSuchElementException,
                StaleElementReferenceException,
            ),
        )

    # ------------------------------------------------------------------ waits
    def find(self, locator: Locator) -> WebElement:
        return self.wait.until(EC.presence_of_element_located(locator))

    def find_all(self, locator: Locator) -> list[WebElement]:
        self.wait.until(EC.presence_of_all_elements_located(locator))
        return self.driver.find_elements(*locator)

    def find_clickable(self, locator: Locator) -> WebElement:
        return self.wait.until(EC.element_to_be_clickable(locator))

    def find_visible(self, locator: Locator) -> WebElement:
        """Return the first *displayed* match.

        The Gajab header renders desktop and mobile variants simultaneously and
        reuses the same id for both, so a plain By.ID can resolve to the hidden
        one. Always use this for header widgets.
        """
        def _first_displayed(driver):
            for element in driver.find_elements(*locator):
                try:
                    if element.is_displayed():
                        return element
                except StaleElementReferenceException:
                    return False
            return False

        return self.wait.until(_first_displayed)

    def is_in_viewport(self, element: WebElement) -> bool:
        return bool(self.driver.execute_script(
            "const r = arguments[0].getBoundingClientRect();"
            "return r.top >= 0 && r.left >= 0 && r.bottom <= window.innerHeight"
            " && r.right <= window.innerWidth;",
            element,
        ))

    def click_visible(self, locator: Locator) -> None:
        """Click the first displayed match, tolerating this site's quirks.

        - Header elements are sticky, so only scroll when actually off-screen;
          scrolling can slide them under absolutely positioned footer imagery.
        - A click that navigates can hang because the next page never finishes
          loading, even though the click itself succeeded.
        """
        element = self.find_visible(locator)
        if not self.is_in_viewport(element):
            self.scroll_into_view(element)

        try:
            element.click()
            return
        except TimeoutException:
            # The click succeeded and started a navigation that will not finish
            # loading. Do NOT call window.stop() here - that aborts it.
            log.warning("Click started a slow navigation - continuing")
            return
        except (ElementClickInterceptedException, StaleElementReferenceException):
            log.warning("Click intercepted for %s - retrying via JS", locator)

        try:
            self.driver.execute_script(
                "arguments[0].click();", self.find_visible(locator)
            )
        except TimeoutException:
            log.warning("JS click started a slow navigation - continuing")

    def is_visible(self, locator: Locator, timeout: int = 5) -> bool:
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.visibility_of_element_located(locator)
            )
            return True
        except TimeoutException:
            return False

    # ----------------------------------------------------------- interactions
    def click(self, locator: Locator) -> None:
        element = self.find_clickable(locator)
        try:
            element.click()
        except (ElementClickInterceptedException, StaleElementReferenceException):
            # Sticky headers and cookie banners intercept clicks on this site.
            self.scroll_into_view(element)
            self.driver.execute_script("arguments[0].click();", element)

    def type(self, locator: Locator, text: str, clear: bool = True) -> None:
        element = self.find_clickable(locator)
        if clear:
            element.clear()
        element.send_keys(text)

    def set_react_input(self, locator: Locator, value: str) -> None:
        """Type into a React controlled input using real keystrokes.

        Injecting the value with JS is counter-productive here: React re-renders
        the controlled input from its own state and wipes the injected value.
        Real key events are the only reliable route, so the caller must retry
        if the component had not hydrated yet.
        """
        element = self.find_visible(locator)
        try:
            element.click()
        except ElementClickInterceptedException:
            # A full-screen overlay (location blocker / coach-mark) is in front.
            self.dismiss_onboarding_overlay()
            element = self.find_visible(locator)
            element.click()

        if element.get_attribute("value"):
            element.send_keys(Keys.CONTROL, "a")
            element.send_keys(Keys.DELETE)

        element.send_keys(value)

    def react_sync_value(self, locator: Locator, value: str) -> None:
        """Push a value into React's state via its native setter.

        Used as a repair step when real keystrokes reach the DOM but not the
        component state. It can race with a re-render, so callers should verify
        the outcome and retry.
        """
        self.driver.execute_script(
            """
            const el = arguments[0], v = arguments[1];
            const setter = Object.getOwnPropertyDescriptor(
                window.HTMLInputElement.prototype, 'value').set;
            setter.call(el, v);
            el.dispatchEvent(new Event('input', { bubbles: true }));
            el.dispatchEvent(new Event('change', { bubbles: true }));
            """,
            self.find_visible(locator),
            value,
        )

    def text_of(self, locator: Locator) -> str:
        return self.find(locator).text.strip()

    def scroll_into_view(self, element: WebElement) -> None:
        self.driver.execute_script(
            "arguments[0].scrollIntoView({block:'center', behavior:'instant'});", element
        )

    def scroll_to_bottom(self) -> None:
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

    def open(self, path: str = "") -> None:
        url = f"{config.BASE_URL}/{path.lstrip('/')}" if path else config.BASE_URL
        log.info("Navigating to %s", url)

        for attempt in (1, 2):
            try:
                self.driver.get(url)
            except TimeoutException:
                # 'eager' still waits for DOMContentLoaded; staging is slow, but
                # content usually arrives shortly after. Never window.stop()
                # here - that would abort the in-flight render.
                log.warning("Page load timed out (attempt %d) - continuing", attempt)

            try:
                self.wait_for_dom_ready()
                return
            except TimeoutException:
                log.warning("App shell not ready (attempt %d) - retrying", attempt)

        raise AssertionError(f"{url} did not render an app shell in time")

    def stop_load(self) -> None:
        try:
            self.driver.execute_script("window.stop();")
        except Exception:  # noqa: BLE001
            pass

    # First-time users get a 'Bargain Guide' spotlight overlay after login. It
    # has no close button and blocks every click underneath it.
    ONBOARDING_OVERLAY = (By.ID, "home-bargain-guide-portal-overlay")
    POPUP_SELECTORS = (
        "#home-bargain-guide-portal-overlay",
        "#location-fullscreen-click-blocker",
        "[id$='-portal-overlay']",
        "[id$='-click-blocker']",
        "[id$='-backdrop-overlay']",
    )

    def _visible_popup(self):
        """Return the first displayed blocking popup, or None."""
        for selector in self.POPUP_SELECTORS:
            for element in self.driver.find_elements(By.CSS_SELECTOR, selector):
                try:
                    if element.is_displayed():
                        return element
                except StaleElementReferenceException:
                    continue
        return None

    def dismiss_onboarding_overlay(self) -> bool:
        """Close the post-login coach-mark popup if it is showing.

        It appears intermittently and has no close button, so it is dismissed
        by clicking it, then ESC, then removed outright as a last resort.
        """
        popup = self._visible_popup()
        if popup is None:
            return False

        log.info("Post-login popup detected - dismissing")

        for action in ("click-overlay", "click-corner", "escape"):
            try:
                if action == "click-overlay":
                    self.driver.execute_script("arguments[0].click();", popup)
                elif action == "click-corner":
                    # Click a neutral spot away from any interactive element.
                    ActionChains(self.driver).move_by_offset(5, 5).click().perform()
                    ActionChains(self.driver).move_by_offset(-5, -5).perform()
                else:
                    self.driver.switch_to.active_element.send_keys(Keys.ESCAPE)
            except Exception:  # noqa: BLE001
                pass

            time.sleep(1)
            if self._visible_popup() is None:
                log.info("Popup dismissed via %s", action)
                return True

        log.warning("Popup would not close - removing it from the DOM")
        self.driver.execute_script(
            "document.querySelectorAll(\"[id$='-portal-overlay'], "
            "[id$='-click-blocker']\").forEach(e => e.remove());"
        )
        return True

    def wait_for_dom_ready(self, timeout: int | None = None) -> None:
        """Wait until the app shell exists.

        This site never fires a load event, so readiness is asserted against a
        real element rather than document.readyState.
        """
        WebDriverWait(self.driver, timeout or config.EXPLICIT_WAIT).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "main, header, [id^='signin-'], [id^='header-']")
            )
        )

    # --------------------------------------------------------------- evidence
    def screenshot(self, name: str) -> Path:
        safe = re.sub(r"[^A-Za-z0-9_-]+", "_", name)
        path = SCREENSHOT_DIR / f"{safe}_{datetime.now():%H%M%S}.png"
        self.driver.save_screenshot(str(path))
        log.info("Screenshot -> %s", path)
        return path

    def element_screenshot(self, locator: Locator, name: str) -> Path:
        safe = re.sub(r"[^A-Za-z0-9_-]+", "_", name)
        path = SCREENSHOT_DIR / f"{safe}_{datetime.now():%H%M%S}.png"
        element = self.find(locator)
        self.scroll_into_view(element)
        element.screenshot(str(path))
        return path

    # --------------------------------------------------------------- helpers
    @staticmethod
    def parse_price(raw: str) -> float:
        """'Asking Price Rs.1,234' -> 1234.0"""
        match = re.search(r"([\d,]+(?:\.\d+)?)", raw.replace("\u20b9", " "))
        if not match:
            raise ValueError(f"No price found in {raw!r}")
        return float(match.group(1).replace(",", ""))

    @staticmethod
    def parse_count(raw: str) -> int:
        """'506 Times Bargained' -> 506"""
        match = re.search(r"([\d,]+)", raw)
        if not match:
            raise ValueError(f"No count found in {raw!r}")
        return int(match.group(1).replace(",", ""))


__all__ = ["BasePage", "By", "Locator"]
