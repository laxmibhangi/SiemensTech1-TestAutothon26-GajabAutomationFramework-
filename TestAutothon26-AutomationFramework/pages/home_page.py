"""Home page - journey steps 5, 6, 8, 9, 10, 11 plus language and pincode."""
from __future__ import annotations

from dataclasses import dataclass

from core.logger import get_logger
from pages.base_page import BasePage, By

log = get_logger(__name__)


@dataclass
class Product:
    name: str
    price: float
    bargains: int = 0
    url: str = ""
    image_url: str = ""


@dataclass
class LiveOrder:
    name: str
    city: str
    detail: str


class HomePage(BasePage):
    """Locators verified against https://stg.gajab.com on 2026-09-09.

    The app exposes stable element ids, but renders the desktop AND mobile
    header simultaneously, duplicating every id. Header widgets therefore go
    through ``find_visible`` / ``click_visible``.
    """

    # --- header widgets (verified ids) ---
    PINCODE_TRIGGER = (By.ID, "location-desktop-menu-btn")
    PINCODE_LABEL = (By.ID, "location-desktop-menu-text")
    PINCODE_INPUT = (By.ID, "location-desktop-search-input")
    PINCODE_SUGGESTIONS = (By.ID, "location-desktop-suggestions-list")
    PINCODE_FIRST_SUGGESTION = (By.ID, "location-desktop-suggestion-item-0")
    PINCODE_CLOSE = (By.ID, "location-desktop-dropdown-close-btn")
    LANGUAGE_TRIGGER = (By.ID, "language-switcher-desktop-btn")
    SEARCH_INPUT = (By.ID, "header-search-input")

    # --- Deal of the Day (widget WP3) ---
    DEAL_CARD = (By.ID, "home-wp3-card")
    DEAL_NAME = (By.ID, "home-wp3-title-link")
    DEAL_PRICE = (By.ID, "home-wp3-price-p")
    DEAL_IMAGE = (By.ID, "home-wp3-product-img")
    DEAL_BARGAIN_BTN = (By.ID, "home-wp3-bargain-btn")

    # --- Trending (widget WP2) ---
    TRENDING_CARDS = (By.CSS_SELECTOR, "[id^='home-wp2-item-card-']")
    TRENDING_VIEW_ALL = (By.ID, "home-wp2-view-more")

    # --- Live orders ---
    LIVE_ORDER_CARDS = (By.CSS_SELECTOR, "[id^='home-live-orders-card-']")

    # --- Just Bargained (widget WP1) ---
    JUST_BARGAINED_VIEW_ALL = (By.ID, "home-wp1-view-more")

    # --- Category nav: the href slug is the stable part ---
    @staticmethod
    def category_tab(slug: str):
        return (By.CSS_SELECTOR, f"a[href*='/product-list/{slug}/']")

    # ------------------------------------------------------------ step 5
    def set_pincode(self, pincode: str) -> str:
        """Set the delivery pincode and return the label shown afterwards.

        The trigger first renders as 'Location' and is replaced once the app
        resolves a default city; clicking before that yields a stale element,
        so wait for the resolved label first.
        """
        # A post-login popup can sit over the header and swallow the click.
        self.dismiss_onboarding_overlay()

        self.wait.until(
            lambda d: self.find_visible(self.PINCODE_LABEL).text.strip().lower() != "location"
        )
        self.click_visible(self.PINCODE_TRIGGER)

        field = self.find_visible(self.PINCODE_INPUT)
        field.clear()
        field.send_keys(pincode)

        self.find_visible(self.PINCODE_SUGGESTIONS)
        self.click_visible(self.PINCODE_FIRST_SUGGESTION)

        self.wait.until(lambda d: pincode in self.find_visible(self.PINCODE_LABEL).text)
        label = self.find_visible(self.PINCODE_LABEL).text.strip()
        log.info("Pincode set, header now reads: %s", label)
        return label

    # ------------------------------------------------- language (En/Hinglish)
    def set_language(self, language: str) -> None:
        self.click_visible(self.LANGUAGE_TRIGGER)
        self.click((By.XPATH, f"//*[normalize-space()='{language}']"))
        log.info("Language switched to %s", language)

    # ------------------------------------------------------------ step 6 & 7
    def deal_of_the_day(self) -> Product:
        """Capture the Deal of the Day in a single atomic read.

        The widget is a rotating carousel: reading the name, price and image in
        separate calls can return details from three different products. Pull
        the whole card in one JS call instead.
        """
        card = self.find(self.DEAL_CARD)
        self.scroll_into_view(card)
        snapshot = self.driver.execute_script(
            """
            const link  = document.querySelector('#home-wp3-title-link');
            const price = document.querySelector('#home-wp3-price-p');
            const img   = document.querySelector('#home-wp3-product-img');
            return {
                name: link ? link.innerText.trim() : '',
                price: price ? price.innerText.trim() : '',
                image: img ? img.src : '',
                url: link ? link.href : ''
            };
            """
        )

        product = Product(
            name=snapshot["name"],
            price=self.parse_price(snapshot["price"]),
            image_url=snapshot["image"],
            url=snapshot["url"],
        )
        log.info("Deal of the Day: %s @ %s", product.name, product.price)
        return product

    # ------------------------------------------------------------ step 8
    def most_bargained_trending_product(self) -> Product:
        """Highest 'Times Bargained'. Ties resolve to the first in scroll order.

        Each card exposes per-SKU ids for price and bargain count. The card text
        carries no product name, so it is derived from the product-detail slug.
        Counts update live, so all cards are read in a single snapshot.
        """
        self.find(self.TRENDING_CARDS)
        cards = self.driver.execute_script(
            """
            return Array.from(
                document.querySelectorAll("[id^='home-wp2-item-card-']")
            ).map(card => {
                const sku = card.id.replace('home-wp2-item-card-', '');
                const price = document.getElementById('home-wp2-item-price-' + sku);
                const count = document.getElementById('home-wp2-item-bargain-count-' + sku);
                const link  = document.getElementById('home-wp2-item-link-' + sku);
                const href  = link ? link.getAttribute('href') || '' : '';
                const slug  = href.split('/product-detail/')[1] || '';
                return {
                    sku: sku,
                    price: price ? price.innerText.trim() : '',
                    count: count ? count.innerText.trim() : '',
                    url: link ? link.href : '',
                    name: (slug.split('/')[0] || sku).replace(/-/g, ' ')
                };
            });
            """
        )

        products: list[Product] = []
        for card in cards:
            if "Times Bargained" not in card["count"]:
                continue
            try:
                products.append(
                    Product(
                        name=card["name"],
                        price=self.parse_price(card["price"]),
                        bargains=self.parse_count(card["count"]),
                        url=card["url"],
                    )
                )
            except ValueError:
                continue

        if not products:
            raise AssertionError(
                f"No trending products with bargain counts were found "
                f"({len(cards)} cards scanned)"
            )

        winner = max(products, key=lambda p: p.bargains)  # max() keeps the first on ties
        log.info("Most bargained trending: %s (%d bargains)", winner.name, winner.bargains)
        return winner

    # ------------------------------------------------------------ step 9
    def latest_live_order(self) -> LiveOrder:
        """Read the newest live-order card.

        Structure: <article> ... <p><span>Name</span> City</p><p>message</p>
        The feed prepends new entries continuously, so read it in one JS call.
        """
        card = self.find_all(self.LIVE_ORDER_CARDS)[0]
        self.scroll_into_view(card)
        snapshot = self.driver.execute_script(
            """
            const card = document.querySelector("[id^='home-live-orders-card-']");
            if (!card) { return { name: '', city: '', detail: '' }; }
            const paras = card.querySelectorAll('p');
            const first = paras[0];
            const span = first ? first.querySelector('span') : null;
            const name = span ? span.innerText.trim() : '';
            const city = first ? first.innerText.replace(name, '').trim() : '';
            return { name, city, detail: card.innerText.replace(/\\n/g, ' ').trim() };
            """
        )
        order = LiveOrder(**snapshot)
        log.info("Latest live order: %s from %s", order.name, order.city)
        return order

    def capture_live_orders(self) -> str:
        """Screenshot the live-orders area.

        An element screenshot times the renderer out here because the feed
        scrolls continuously, so scroll it into view and capture the viewport.
        """
        self.scroll_into_view(self.find_all(self.LIVE_ORDER_CARDS)[0])
        return str(self.screenshot("latest_live_order"))

    # ------------------------------------------------------------ step 10
    def open_just_bargained_view_all(self) -> None:
        self.click(self.JUST_BARGAINED_VIEW_ALL)

    # ------------------------------------------------------------ step 11
    def open_category(self, slug: str) -> None:
        """``slug`` is the URL fragment, e.g. 'toys-games'."""
        log.info("Opening category tab: %s", slug)
        self.click_visible(self.category_tab(slug))
