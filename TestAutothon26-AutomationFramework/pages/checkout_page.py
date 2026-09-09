"""Address, payment and order confirmation - journey steps 18-22."""
from __future__ import annotations

import time

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait

from config.settings import config
from core.logger import get_logger
from pages.base_page import BasePage, By

log = get_logger(__name__)


class CheckoutPage(BasePage):
    """Checkout page. Locators verified against /checkout on 2026-09-09."""

    # --- address form (step 18) ---
    ADDRESS_NAME = (By.ID, "add-new-address-name-input")
    ADDRESS_PHONE = (By.ID, "add-new-address-phone-input")
    ADDRESS_LINE1 = (By.ID, "add-new-address-address1-input")
    ADDRESS_LINE2 = (By.ID, "add-new-address-address2-input")
    ADDRESS_PINCODE = (By.ID, "add-new-address-pincode-input")
    ADDRESS_CITYSTATE = (By.ID, "add-new-address-citystate-input")
    ADDRESS_TYPE_HOME = (By.ID, "home-0")
    SET_AS_DEFAULT = (By.ID, "default-new")
    SAVE_ADDRESS_BTN = (By.ID, "save-delivery-address-btn")
    VIEW_SAVED_ADDRESS_BTN = (By.ID, "add-address-view-saved-btn")

    # --- payment (steps 19-20) ---
    PAY_NOW = (By.ID, "checkout-pay-now-desktop-btn")
    PAY_NOW_MOBILE = (By.ID, "checkout-pay-now-mobile-btn")
    OFFERS_BTN = (By.ID, "checkout-offers-btn")

    # Razorpay renders in an iframe; these are matched inside it.
    NET_BANKING = (By.XPATH, "//*[contains(translate(.,'NET BANKING','net banking'),'net banking')]")
    BANK_OPTIONS = (By.XPATH, "//*[contains(@class,'bank')]//input | //label[contains(@class,'bank')]")
    SUCCESS_BTN = (By.XPATH, "//button[contains(.,'Success')]")
    CONFIRM_PAYMENT = (By.XPATH, "//button[contains(.,'Confirm') or contains(.,'Pay')]")

    # --- confirmation (step 21) ---
    ORDER_CONFIRMATION = (By.XPATH, "//*[contains(.,'Order Placed') or contains(.,'order has been placed') or contains(.,'Thank you')]")
    ORDER_ID = (By.XPATH, "//*[contains(.,'Order ID') or contains(.,'Order Id')]")

    def payable_amount(self) -> float:
        """Read the amount from the 'Pay Rs.X' button."""
        return self.parse_price(self.text_of(self.PAY_NOW))

    def _fill_field(self, locator, value: str) -> None:
        """Type a value and make sure React actually received it."""
        self.set_react_input(locator, value)
        if self.find_visible(locator).get_attribute("value") != value:
            self.react_sync_value(locator, value)

    def _select_address_type(self) -> None:
        """Pick the 'Home' address type.

        The radio is styled, so a plain click can miss; fall back to a JS click
        which still drives React through the change event.
        """
        radio = self.driver.find_elements(*self.ADDRESS_TYPE_HOME)
        if not radio:
            return
        try:
            radio[0].click()
        except Exception:  # noqa: BLE001
            pass
        if not radio[0].is_selected():
            self.driver.execute_script(
                "arguments[0].click();"
                "arguments[0].dispatchEvent(new Event('change', {bubbles: true}));",
                radio[0],
            )
        log.info("Address type selected: home=%s", radio[0].is_selected())

    def fill_address(self, address: dict[str, str]) -> "CheckoutPage":
        """Complete the delivery address form and save it (step 18).

        The pincode triggers a city/state lookup that re-renders the form and
        clears anything typed before it, so the pincode goes in first. Fields
        are then re-checked and re-filled if the re-render wiped them.

        The Pay button stays disabled until a valid address is stored, so that
        is used as the success signal rather than trusting the click.
        """
        pincode = address.get("pincode")
        if pincode and self.driver.find_elements(*self.ADDRESS_PINCODE):
            self._fill_field(self.ADDRESS_PINCODE, str(pincode))
            time.sleep(3)  # let the city/state lookup settle

        field_map = (
            (self.ADDRESS_NAME, address.get("name")),
            (self.ADDRESS_PHONE, address.get("phone")),
            (self.ADDRESS_LINE1, address.get("address")),
            (self.ADDRESS_LINE2, address.get("address2")),
            (self.ADDRESS_PINCODE, pincode),
        )

        for attempt in (1, 2):
            for locator, value in field_map:
                if not value or not self.driver.find_elements(*locator):
                    continue
                current = self.driver.find_element(*locator).get_attribute("value")
                if current != str(value):
                    self._fill_field(locator, str(value))

            time.sleep(1)
            empty = [
                locator[1] for locator, value in field_map
                if value and self.driver.find_elements(*locator)
                and not self.driver.find_element(*locator).get_attribute("value")
            ]
            if not empty:
                break
            log.warning("Fields still empty after attempt %d: %s", attempt, empty)

        self._select_address_type()
        self.click_visible(self.SAVE_ADDRESS_BTN)

        try:
            WebDriverWait(self.driver, config.EXPLICIT_WAIT).until(
                lambda d: self.find_visible(self.PAY_NOW).is_enabled()
            )
            log.info("Delivery address saved - payment enabled")
        except TimeoutException:
            state = self.driver.execute_script(
                """
                const val = id => document.getElementById(id)?.value ?? null;
                return {
                  name: val('add-new-address-name-input'),
                  phone: val('add-new-address-phone-input'),
                  address1: val('add-new-address-address1-input'),
                  address2: val('add-new-address-address2-input'),
                  pincode: val('add-new-address-pincode-input'),
                  cityState: val('add-new-address-citystate-input'),
                  typeError: document.getElementById('add-address-type-error')?.innerText || null,
                  payDisabled: document.getElementById('checkout-pay-now-desktop-btn')?.disabled
                };
                """
            )
            raise AssertionError(f"Address was not accepted. Form state: {state}")

        return self

    def pay_now(self) -> "CheckoutPage":
        amount = self.text_of(self.PAY_NOW)
        log.info("Proceeding to payment: %s", amount)
        self.click_visible(self.PAY_NOW)
        return self

    def pay_with_net_banking(self, bank_index: int = 0) -> "CheckoutPage":
        """Steps 19-20 - Razorpay renders inside an iframe."""
        log.info("Selecting Net Banking")
        self.switch_to_payment_frame()
        self.click_visible(self.NET_BANKING)
        banks = self.find_all(self.BANK_OPTIONS)
        self.scroll_into_view(banks[bank_index])
        banks[bank_index].click()
        return self

    def switch_to_payment_frame(self) -> bool:
        """Focus the Razorpay iframe if one is present."""
        self.driver.switch_to.default_content()
        for frame in self.driver.find_elements(By.TAG_NAME, "iframe"):
            src = (frame.get_attribute("src") or "").lower()
            if "razorpay" in src or "checkout" in src:
                self.driver.switch_to.frame(frame)
                log.info("Switched into the payment iframe")
                return True
        return False

    def complete_payment(self) -> "CheckoutPage":
        self.click_visible(self.SUCCESS_BTN)
        if self.is_visible(self.CONFIRM_PAYMENT, timeout=5):
            self.click_visible(self.CONFIRM_PAYMENT)
        self.driver.switch_to.default_content()
        return self

    def is_order_placed(self) -> bool:
        self.driver.switch_to.default_content()
        placed = self.is_visible(self.ORDER_CONFIRMATION, timeout=40)
        log.info("Order placed: %s", placed)
        return placed


class MyBargainsPage(BasePage):
    MY_BARGAINS_LINK = (By.ID, "header-my-bargains-btn")
    SAVINGS = (By.XPATH, "//*[contains(.,'Saved') or contains(.,'Savings')]")
    BARGAIN_ROWS = (By.XPATH, "//*[contains(@class,'bargain') and contains(@class,'card')]")

    def open_my_bargains(self) -> "MyBargainsPage":
        self.click_visible(self.MY_BARGAINS_LINK)
        return self

    def total_savings(self) -> float:
        return self.parse_price(self.text_of(self.SAVINGS))
