"""Login / OTP flow - journey steps 2-4."""
from __future__ import annotations

import time

from selenium.common.exceptions import (
    ElementClickInterceptedException,
    ElementNotInteractableException,
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from config.settings import config
from core.logger import get_logger
from pages.base_page import BasePage, By

log = get_logger(__name__)


class LoginPage(BasePage):
    """Locators verified against https://stg.gajab.com/auth/signin on 2026-09-09.

    The sign-in form requires the Terms checkbox to be ticked before
    'Request OTP' can be submitted.
    """

    LOGIN_ENTRY = (By.ID, "header-login-btn")
    MOBILE_INPUT = (By.ID, "signin-mobile-input")        # type=tel, maxlength=10
    TERMS_CHECKBOX = (By.ID, "signin-terms-checkbox")    # visually hidden input
    TERMS_WRAPPER = (By.ID, "signin-terms-checkbox-wrapper")
    TERMS_LABEL_WRAPPER = (By.ID, "signin-terms-label-wrapper")
    TERMS_UNCHECKED_ICON = (By.ID, "signin-terms-unchecked-icon")
    REQUEST_OTP_BTN = (By.ID, "signin-submit-btn")       # label: 'Request OTP'
    # --- OTP screen (verified 2026-09-09) ---
    OTP_CONTAINER = (By.ID, "otp-verification-container")
    OTP_INPUTS = (By.CSS_SELECTOR, "[id^='otp-input-']")   # otp-input-0 .. otp-input-5
    OTP_TIMER = (By.ID, "otp-timer-label")
    SUBMIT_BTN = (By.ID, "otp-submit-btn")
    TOAST = (By.XPATH, "//*[contains(@class,'Toastify') or @role='alert']")
    ACCOUNT_MENU = (By.ID, "header-mobile-profile-btn")

    def go_to_login(self) -> "LoginPage":
        self.click_visible(self.LOGIN_ENTRY)
        try:
            self.wait.until(lambda d: "/auth/signin" in d.current_url)
        except TimeoutException:
            log.warning("Login click did not navigate - retrying once")
            self.click_visible(self.LOGIN_ENTRY)
            self.wait.until(lambda d: "/auth/signin" in d.current_url)

        self.wait_for_dom_ready()
        self.find_visible(self.MOBILE_INPUT)
        return self

    def is_terms_accepted(self) -> bool:
        return bool(self.driver.execute_script(
            "return !!document.querySelector('#signin-terms-checkbox')?.checked;"
        ))

    def accept_terms(self) -> "LoginPage":
        """Tick the Terms checkbox.

        The real <input> is transparent (opacity-0) and sits above the icon,
        which has pointer-events: none. A manual click works, so click the
        input directly first. Synthetic clicks occasionally land before React
        has attached its handler, so fall back to React's native setter.
        """
        if self.is_terms_accepted():
            return self

        for locator in (self.TERMS_CHECKBOX, self.TERMS_WRAPPER):
            try:
                self.driver.find_element(*locator).click()
            except (StaleElementReferenceException,
                    ElementClickInterceptedException,
                    NoSuchElementException):
                continue
            if self.is_terms_accepted():
                log.info("Terms accepted by clicking %s", locator[1])
                return self

        log.warning("Terms checkbox did not respond to clicks - syncing React state")
        self.driver.execute_script(
            """
            const cb = document.querySelector('#signin-terms-checkbox');
            const setter = Object.getOwnPropertyDescriptor(
                window.HTMLInputElement.prototype, 'checked').set;
            setter.call(cb, true);
            cb.dispatchEvent(new Event('click', { bubbles: true }));
            cb.dispatchEvent(new Event('change', { bubbles: true }));
            """
        )
        WebDriverWait(self.driver, 5).until(lambda d: self.is_terms_accepted())
        log.info("Terms accepted via React state sync")
        return self

    def _request_otp_enabled(self, timeout: int) -> bool:
        try:
            WebDriverWait(self.driver, timeout).until(
                lambda d: self.find_visible(self.REQUEST_OTP_BTN).is_enabled()
            )
            return True
        except TimeoutException:
            return False

    def enter_mobile_and_request_otp(self, mobile: str) -> "LoginPage":
        log.info("Requesting OTP for %s", config.masked_mobile())

        # Real keystrokes are preferred, but React sometimes ignores them here
        # and leaves the button disabled. Fall back to a state sync, and retry
        # because the sync can race with a re-render.
        for attempt in range(1, 5):
            self.set_react_input(self.MOBILE_INPUT, mobile)
            if self._request_otp_enabled(3):
                break

            log.warning("Typed value did not reach React state - syncing (attempt %d)",
                        attempt)
            self.react_sync_value(self.MOBILE_INPUT, mobile)
            if self._request_otp_enabled(4):
                break

            time.sleep(1.5)
        else:
            state = self.driver.execute_script(
                """
                const btn = document.querySelector('#signin-submit-btn');
                const inp = document.querySelector('#signin-mobile-input');
                const cb  = document.querySelector('#signin-terms-checkbox');
                return {
                  url: location.pathname,
                  mobileLength: inp ? inp.value.length : null,
                  termsChecked: cb ? cb.checked : null,
                  btnDisabled: btn ? btn.disabled : null,
                  btnText: btn ? btn.innerText.trim() : null,
                  visibleInputs: document.querySelectorAll('#signin-mobile-input').length
                };
                """
            )
            raise AssertionError(
                "'Request OTP' never became enabled after entering the mobile "
                f"number. Page state: {state}"
            )

        # Consent is ticked after the number, matching the manual flow.
        # NOTE: if terms are not ticked, 'Request OTP' fails silently - no
        # toast, no inline error (see bug report).
        self.accept_terms()

        for attempt in range(1, 3):
            self.click_visible(self.REQUEST_OTP_BTN)
            try:
                WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located(self.OTP_CONTAINER)
                )
                log.info("OTP screen displayed")
                return self
            except TimeoutException:
                log.warning("OTP screen did not appear (attempt %d/2)", attempt)
                self.accept_terms()

        raise AssertionError(
            "OTP screen never appeared after requesting the OTP. "
            f"Current URL: {self.driver.current_url}"
        )

    def _submit_enabled(self, timeout: int) -> bool:
        try:
            WebDriverWait(self.driver, timeout).until(
                lambda d: self.find_visible(self.SUBMIT_BTN).is_enabled()
            )
            return True
        except TimeoutException:
            return False

    def _otp_screen_gone(self) -> bool:
        """The form auto-submits once six digits register, removing the boxes."""
        return not self.driver.find_elements(*self.OTP_CONTAINER)

    def enter_otp(self, otp: str) -> "LoginPage":
        """Fill the six single-digit OTP boxes (otp-input-0 .. otp-input-5).

        The boxes auto-advance focus, so the natural interaction is to type the
        whole code into the first box. Later boxes are not interactable until
        the previous one is filled, hence no clearing.
        """
        self.find_visible(self.OTP_CONTAINER)
        boxes = [(By.ID, f"otp-input-{i}") for i in range(len(otp))]

        for attempt in range(1, 4):
            # Type digit by digit into whatever box currently has focus - the
            # component moves focus itself after each keystroke.
            self.find_visible(boxes[0]).click()
            for digit in otp:
                self.driver.switch_to.active_element.send_keys(digit)
                time.sleep(0.15)
            if self._otp_screen_gone():
                log.info("OTP auto-submitted after the sixth digit")
                return self
            if self._submit_enabled(3):
                break

            log.warning("OTP auto-advance did not register (attempt %d)", attempt)
            for locator, digit in zip(boxes, otp):
                try:
                    self.driver.find_element(*locator).send_keys(digit)
                except (ElementNotInteractableException,
                        StaleElementReferenceException,
                        NoSuchElementException):
                    continue
            if self._otp_screen_gone():
                log.info("OTP auto-submitted after the sixth digit")
                return self
            if self._submit_enabled(3):
                break

            for locator, digit in zip(boxes, otp):
                if self._otp_screen_gone():
                    log.info("OTP auto-submitted after the sixth digit")
                    return self
                self.react_sync_value(locator, digit)
            if self._submit_enabled(4):
                break

            time.sleep(1.5)
        else:
            state = self.driver.execute_script(
                """
                const btn = document.querySelector('#otp-submit-btn');
                return {
                  boxes: Array.from(document.querySelectorAll("[id^='otp-input-']"))
                           .map(i => i.value).join(''),
                  btnCount: document.querySelectorAll('#otp-submit-btn').length,
                  btnDisabled: btn ? btn.disabled : null,
                  btnClass: btn ? btn.className.slice(0, 60) : null,
                  btnText: btn ? btn.innerText.trim() : null,
                  timer: document.querySelector('#otp-timer-label')?.innerText || null,
                  url: location.pathname
                };
                """
            )
            raise AssertionError(f"Submit never enabled after the OTP. State: {state}")

        log.info("OTP entered, Submit is enabled")
        return self

    def submit(self) -> "LoginPage":
        if self._otp_screen_gone():
            log.info("OTP screen already submitted - nothing to click")
            return self
        self.click_visible(self.SUBMIT_BTN)
        return self

    def login(self, mobile: str | None = None, otp: str | None = None) -> "LoginPage":
        """Full happy-path login used by the E2E journey.

        A coach-mark popup sometimes appears straight after login and blocks
        every later click, so it is dismissed here.
        """
        (
            self.go_to_login()
            .enter_mobile_and_request_otp(mobile or config.MOBILE_NUMBER)
            .enter_otp(otp or config.OTP)
            .submit()
        )
        time.sleep(3)
        self.dismiss_onboarding_overlay()
        return self

    def success_message(self) -> str:
        return self.text_of(self.TOAST)

    def is_logged_in(self) -> bool:
        return not self.is_visible(self.LOGIN_ENTRY, timeout=8)
