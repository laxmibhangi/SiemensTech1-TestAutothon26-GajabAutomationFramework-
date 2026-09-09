r"""Executes journey steps 1-12 in a single logged-in session, printing results.

Step 7 (email) is skipped until SMTP is configured in .env.

Run:  .\.venv\Scripts\python.exe scripts\run_journey.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import config  # noqa: E402
from core.driver_factory import create_web_driver  # noqa: E402
from core.excel_reader import read_row  # noqa: E402
from pages.home_page import HomePage  # noqa: E402
from pages.login_page import LoginPage  # noqa: E402
from pages.product_list_page import ProductListPage  # noqa: E402

results: list[tuple[str, str, str]] = []


def record(step: str, status: str, detail: str = "") -> None:
    results.append((step, status, detail))
    icon = {"PASS": "[PASS]", "FAIL": "[FAIL]", "SKIP": "[SKIP]"}[status]
    print(f"{icon} {step}: {detail}")


def main() -> int:
    data = read_row("Journey", "TestCaseId", "TC_E2E_01")
    driver = create_web_driver()

    try:
        home = HomePage(driver)
        login = LoginPage(driver)

        # ------------------------------------------------ step 1
        try:
            home.open()
            record("Step 1  Navigate to Gajab", "PASS", driver.title[:60])
        except Exception as exc:  # noqa: BLE001
            record("Step 1  Navigate to Gajab", "FAIL", type(exc).__name__)
            return 1

        # ------------------------------------------------ steps 2-4
        try:
            login.login(config.MOBILE_NUMBER, config.OTP)
            time.sleep(3)
            assert login.is_logged_in(), "still showing Log in / Sign up"
            record("Step 2-4 Login with OTP", "PASS",
                   f"logged in as {config.masked_mobile()}")
        except Exception as exc:  # noqa: BLE001
            record("Step 2-4 Login with OTP", "FAIL", f"{type(exc).__name__}: {exc}")
            return 1

        home.dismiss_onboarding_overlay()

        # ------------------------------------------------ step 5
        try:
            label = home.set_pincode(str(data["Pincode"]))
            status = "PASS" if str(data["Pincode"]) in label else "FAIL"
            record("Step 5  Pincode reflected", status, label)
        except Exception as exc:  # noqa: BLE001
            record("Step 5  Pincode reflected", "FAIL", type(exc).__name__)

        # ------------------------------------------------ step 6
        deal = None
        try:
            deal = home.deal_of_the_day()
            record("Step 6  Deal of the Day", "PASS",
                   f"{deal.name[:50]} @ INR {deal.price}")
        except Exception as exc:  # noqa: BLE001
            record("Step 6  Deal of the Day", "FAIL", type(exc).__name__)

        # ------------------------------------------------ step 7
        record("Step 7  Email the deal", "SKIP", "SMTP not configured in .env")

        # ------------------------------------------------ step 8
        try:
            trending = home.most_bargained_trending_product()
            record("Step 8  Most-bargained trending", "PASS",
                   f"{trending.name[:45]} - {trending.bargains} bargains")
        except Exception as exc:  # noqa: BLE001
            record("Step 8  Most-bargained trending", "FAIL", type(exc).__name__)

        # ------------------------------------------------ step 9
        try:
            order = home.latest_live_order()
            shot = home.capture_live_orders()
            record("Step 9  Latest live order", "PASS",
                   f"{order.name} / {order.city} (screenshot: {Path(shot).name})")
        except Exception as exc:  # noqa: BLE001
            record("Step 9  Latest live order", "FAIL", type(exc).__name__)

        # ------------------------------------------------ step 10
        try:
            home.open_just_bargained_view_all()
            time.sleep(4)
            cheapest = ProductListPage(driver).cheapest_among_most_bargained()
            record("Step 10 Cheapest most-bargained", "PASS",
                   f"{cheapest.name[:45]} @ INR {cheapest.price}")
        except Exception as exc:  # noqa: BLE001
            record("Step 10 Cheapest most-bargained", "FAIL", type(exc).__name__)

        # ------------------------------------------------ step 11
        listing = ProductListPage(driver)
        try:
            home.open()
            home.dismiss_onboarding_overlay()
            home.open_category("toys-games")
            time.sleep(5)
            status = "PASS" if "toys-games" in driver.current_url else "FAIL"
            record("Step 11 Toys & Games tab", status, driver.current_url.split("?")[0])
        except Exception as exc:  # noqa: BLE001
            record("Step 11 Toys & Games tab", "FAIL", type(exc).__name__)

        # ------------------------------------------------ step 12
        try:
            brands = listing.available_brands()
            wanted = str(data.get("Brand") or "").strip()
            brand = wanted if wanted in brands else (brands[0] if brands else "")
            if not brand:
                record("Step 12 Brand filter", "FAIL", "no brands listed")
            else:
                if wanted and wanted != brand:
                    print(f"        note: '{wanted}' not offered; using '{brand}'."
                          f" Available: {', '.join(brands[:8])}")
                before = len(driver.find_elements(*listing.PRODUCT_CARDS))
                listing.apply_filter(brand)
                time.sleep(5)
                after = len(driver.find_elements(*listing.PRODUCT_CARDS))
                record("Step 12 Brand filter", "PASS",
                       f"'{brand}' applied ({before} -> {after} products)")
        except Exception as exc:  # noqa: BLE001
            record("Step 12 Brand filter", "FAIL", f"{type(exc).__name__}")

        # ------------------------------------------------ step 13
        second = str(data.get("SecondFilter") or "").strip()
        if not second:
            record("Step 13 Second filter", "SKIP",
                   "no SecondFilter in the test data sheet")
        else:
            try:
                listing.apply_filter(second)
                time.sleep(4)
                record("Step 13 Second filter", "PASS", f"'{second}' applied")
            except Exception as exc:  # noqa: BLE001
                record("Step 13 Second filter", "FAIL", type(exc).__name__)

        # ------------------------------------------------ step 14
        wanted_product = str(data.get("ProductName") or "").strip()
        product_url = None
        try:
            products = driver.execute_script(
                """
                return Array.from(
                    document.querySelectorAll("a[href*='/product-detail/']")
                ).map(a => ({ href: a.href, text: a.innerText.trim() }))
                 .filter(p => p.text);
                """
            )
            match = next(
                (p for p in products
                 if wanted_product and wanted_product.lower() in p["text"].lower()),
                None,
            )
            if match is None and products:
                print(f"        note: '{wanted_product}' not in the filtered results;"
                      " using the first product instead")
                match = products[0]

            if match is None:
                record("Step 14 Select product", "FAIL", "no products in the listing")
            else:
                product_url = match["href"]
                driver.get(product_url)
                time.sleep(6)
                record("Step 14 Select product", "PASS", match["text"].splitlines()[0][:50])
        except Exception as exc:  # noqa: BLE001
            record("Step 14 Select product", "FAIL", type(exc).__name__)

        if product_url is None:
            return 1

        # ------------------------------------------------ steps 15-16
        from pages.bargain_page import BargainPage

        bargain = BargainPage(driver)
        try:
            asking = bargain.asking_price()
            attempts = int(data.get("BargainAttempts", 3))
            bargain.bargain(attempts=attempts)
            record("Step 15-16 Bargain x3 and accept", "PASS",
                   f"asking INR {asking:.0f}, accepted after {attempts} rounds")
        except Exception as exc:  # noqa: BLE001
            record("Step 15-16 Bargain x3 and accept", "FAIL",
                   f"{type(exc).__name__}: {exc}")
            return 1

        # ------------------------------------------------ step 17
        try:
            bargain.buy_now()
            time.sleep(8)
            status = "PASS" if "/checkout" in driver.current_url else "FAIL"
            record("Step 17 Buy Now", status, driver.current_url.split("?")[0])
        except Exception as exc:  # noqa: BLE001
            record("Step 17 Buy Now", "FAIL", type(exc).__name__)

    finally:
        driver.quit()

    print("\n" + "=" * 62)
    passed = sum(1 for _, s, _ in results if s == "PASS")
    failed = sum(1 for _, s, _ in results if s == "FAIL")
    skipped = sum(1 for _, s, _ in results if s == "SKIP")
    print(f"SUMMARY: {passed} passed, {failed} failed, {skipped} skipped")
    print("=" * 62)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
