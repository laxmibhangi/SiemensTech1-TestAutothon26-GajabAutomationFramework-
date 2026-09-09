"""Product detail + bargaining flow - journey steps 15, 16, 17."""
from __future__ import annotations

import time

from selenium.webdriver.support.ui import WebDriverWait

from config.settings import config
from core.logger import get_logger
from pages.base_page import BasePage, By

log = get_logger(__name__)


class BargainPage(BasePage):
    """Product detail page + bargain modal. Locators verified 2026-09-09.

    'Start Bargaining' renders several times (desktop, mobile, sticky bar) and
    only some copies carry an id, so it is matched by button text.
    """

    # --- product detail ---
    PRODUCT_TITLE = (By.ID, "pdp-product-title")
    BRAND_NAME = (By.ID, "pdp-brand-name")
    ASKING_PRICE = (By.ID, "varient-price")
    BARGAIN_CARD = (By.ID, "pdp-bargain-card")
    START_BARGAINING = (By.XPATH, "//button[normalize-space()='Start Bargaining']")

    # --- bargain modal ---
    MODAL = (By.ID, "bargain-seller-modal")
    MODAL_TITLE = (By.ID, "bargain-modal-title")
    MODAL_CLOSE = (By.ID, "bargain-modal-close-btn")
    MODAL_MUTE = (By.ID, "bargain-modal-mute-btn")
    MODAL_PRODUCT_TITLE = (By.ID, "bargain-product-title")
    MODAL_ASKING_PRICE = (By.ID, "bargain-asking-price-val")
    OFFER_INPUT = (By.ID, "bargain-offer-price")
    PRICE_SLIDER = (By.ID, "bargain-price-slider")
    SEND_OFFER = (By.ID, "bargain-submit-offer-btn")
    OFFER_TITLE = (By.ID, "bargain-offer-title")
    SLIDER_WARNING = (By.ID, "bargain-slider-warning")

    # --- outcome (shown after the seller counters) ---
    ACCEPT_OFFER = (By.ID, "bargain-accept-offer-btn")     # 'Accept the offer'
    BARGAIN_AGAIN = (By.ID, "bargain-again-btn")           # 'Bargain More'
    BUY_NOW = (By.ID, "bargain-accepted-buy-now-btn")      # shown once accepted

    def product_name(self) -> str:
        return self.text_of(self.PRODUCT_TITLE)

    def asking_price(self) -> float:
        return self.parse_price(self.text_of(self.ASKING_PRICE))

    def start_bargaining(self) -> "BargainPage":
        self.click_visible(self.START_BARGAINING)
        self.find_visible(self.MODAL)
        # The modal plays audio on every offer; mute it for unattended runs.
        if self.is_visible(self.MODAL_MUTE, timeout=3):
            self.click_visible(self.MODAL_MUTE)
        log.info("Bargain modal opened")
        return self

    def suggested_offer(self) -> float:
        """The offer box pre-fills a suggested price as its placeholder."""
        raw = self.find_visible(self.OFFER_INPUT).get_attribute("placeholder") or ""
        return self.parse_price(raw)

    def make_offer(self, amount: float) -> "BargainPage":
        log.info("Offering %.0f", amount)
        self.set_react_input(self.OFFER_INPUT, str(int(amount)))
        if self.find_visible(self.OFFER_INPUT).get_attribute("value") != str(int(amount)):
            self.react_sync_value(self.OFFER_INPUT, str(int(amount)))
        self.click_visible(self.SEND_OFFER)
        return self

    def is_deal_accepted(self) -> bool:
        """'Buy Now' only renders once a price has been agreed."""
        return bool(self.driver.find_elements(*self.BUY_NOW))

    def bargain(self, attempts: int = 3, discount_step: float = 0.10) -> float:
        """Bargain for ``attempts`` rounds, then accept the offer (step 16).

        After each offer the seller counters and the input is replaced by
        'Accept the offer' / 'Bargain More', so another round needs
        'Bargain More' clicking first. The seller can also accept outright,
        which jumps straight to 'Buy Now'.
        """
        asking = self.asking_price()
        self.start_bargaining()

        for round_no in range(1, attempts + 1):
            if round_no > 1:
                if self.is_deal_accepted():
                    log.info("Seller accepted at round %d - no further offers",
                             round_no - 1)
                    break
                if not self.is_visible(self.BARGAIN_AGAIN, timeout=10):
                    log.warning("'Bargain More' not offered - stopping at round %d",
                                round_no - 1)
                    break
                self.click_visible(self.BARGAIN_AGAIN)
                self.find_visible(self.OFFER_INPUT)

            offer = round(asking * (1 - discount_step * (attempts - round_no + 1)))
            log.info("Bargain attempt %d/%d", round_no, attempts)
            self.make_offer(offer)

            # Either a counter-offer or an outright acceptance follows.
            WebDriverWait(self.driver, config.EXPLICIT_WAIT).until(
                lambda d: d.find_elements(*self.ACCEPT_OFFER)
                or d.find_elements(*self.BUY_NOW)
            )

        if self.is_visible(self.ACCEPT_OFFER, timeout=8):
            self.click_visible(self.ACCEPT_OFFER)
            log.info("Offer accepted after %d rounds (asking was %.0f)",
                     attempts, asking)
        elif self.is_deal_accepted():
            log.info("Deal already accepted by the seller (asking was %.0f)", asking)
        else:
            raise AssertionError("Neither 'Accept the offer' nor 'Buy Now' appeared")

        self.find_visible(self.BUY_NOW)
        return asking

    def buy_now(self) -> None:
        self.click_visible(self.BUY_NOW)
