"""Product listing page - journey steps 10, 12, 13, 14."""
from __future__ import annotations

from core.logger import get_logger
from pages.base_page import BasePage, By
from pages.home_page import Product

log = get_logger(__name__)


class ProductListPage(BasePage):
    """Locators verified against the Toys & Games listing on 2026-09-09."""

    PRODUCT_CARDS = (By.CSS_SELECTOR, "a[href*='/product-detail/']")
    FILTER_PANEL = (By.ID, "filter-section-desktop-panel")
    CLEAR_ALL_FILTERS = (By.ID, "filter-section-desktop-clear-all-btn")
    BRAND_FILTER_TOGGLE = (By.ID, "brand-filter-accordion-toggle-btn")
    BRAND_FILTER_ITEMS = (By.CSS_SELECTOR, "[id^='brand-filter-item-label-']")
    LOAD_MORE = (By.XPATH, "//button[contains(.,'Load More') or contains(.,'Show More')]")

    @staticmethod
    def filter_option(label: str):
        """Brand rows are <label id='brand-filter-item-label-<brandId>'>."""
        return (
            By.XPATH,
            "//label[starts-with(@id,'brand-filter-item-label-')]"
            f"[normalize-space()='{label}']",
        )

    @staticmethod
    def product_link(name: str):
        return (By.XPATH, f"//a[contains(@href,'/product-detail/') and contains(normalize-space(),'{name}')]")

    # ------------------------------------------------------------ steps 12-13
    def available_brands(self) -> list[str]:
        return [e.text.strip() for e in self.find_all(self.BRAND_FILTER_ITEMS)]

    def apply_filter(self, label: str) -> None:
        log.info("Applying filter: %s", label)
        if self.is_visible(self.BRAND_FILTER_TOGGLE, timeout=5):
            # The accordion may be collapsed; opening it is idempotent enough.
            if not self.driver.find_elements(*self.BRAND_FILTER_ITEMS):
                self.click_visible(self.BRAND_FILTER_TOGGLE)
        self.click_visible(self.filter_option(label))

    # ------------------------------------------------------------ step 14
    def open_product(self, name: str) -> None:
        log.info("Opening product: %s", name)
        self.click(self.product_link(name))

    # ------------------------------------------------------------ step 10
    def collect_products(self, scrolls: int = 5) -> list[Product]:
        """Scroll through the lazy-loaded grid and collect every product card."""
        seen: dict[str, Product] = {}
        for _ in range(scrolls):
            for card in self.driver.find_elements(*self.PRODUCT_CARDS):
                href = card.get_attribute("href") or ""
                text = card.text.strip()
                if not href or not text or href in seen:
                    continue
                try:
                    price = self.parse_price(text)
                except ValueError:
                    continue
                bargains = 0
                if "Bargained" in text:
                    bargains = self.parse_count(text.split("Times Bargained")[0].split("\u26a1")[-1])
                seen[href] = Product(
                    name=text.splitlines()[0].strip(), price=price, bargains=bargains, url=href
                )
            self.scroll_to_bottom()
            if self.is_visible(self.LOAD_MORE, timeout=2):
                self.click(self.LOAD_MORE)

        log.info("Collected %d products from the listing", len(seen))
        return list(seen.values())

    def cheapest_among_most_bargained(self) -> Product:
        """Cheapest product in the 'most bargained' listing."""
        products = self.collect_products()
        if not products:
            raise AssertionError("No products found on the listing page")
        cheapest = min(products, key=lambda p: p.price)
        log.info("Cheapest most-bargained product: %s @ %s", cheapest.name, cheapest.price)
        return cheapest
