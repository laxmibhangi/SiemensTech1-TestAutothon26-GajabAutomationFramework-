r"""Logged-in walkthrough that captures element ids for journey steps 11-16.

Stops BEFORE any payment. Writes one JSON dump per stage to reports/flow/.

Run:  .\.venv\Scripts\python.exe scripts\capture_journey_flow.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import REPORTS_DIR, config  # noqa: E402
from core.driver_factory import create_web_driver  # noqa: E402
from core.excel_reader import read_row  # noqa: E402
from pages.home_page import HomePage  # noqa: E402
from pages.login_page import LoginPage  # noqa: E402

FLOW_DIR = REPORTS_DIR / "flow"
FLOW_DIR.mkdir(parents=True, exist_ok=True)

DUMP_JS = """
return {
  url: location.pathname + location.search,
  ids: [...new Set(Array.from(document.querySelectorAll('[id]')).map(e => e.id))],
  buttons: Array.from(document.querySelectorAll('button'))
      .map(b => ({ id: b.id, text: b.innerText.trim().slice(0, 40), disabled: b.disabled }))
      .filter(b => b.text || b.id),
  inputs: Array.from(document.querySelectorAll('input'))
      .map(i => ({ id: i.id, type: i.type, placeholder: i.placeholder })),
  headings: Array.from(document.querySelectorAll('h1,h2,h3'))
      .map(h => h.innerText.trim()).filter(Boolean).slice(0, 15)
};
"""


def dump(driver, stage: str) -> dict:
    data = driver.execute_script(DUMP_JS)
    target = FLOW_DIR / f"{stage}.json"
    target.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"  [{stage}] url={data['url']} ids={len(data['ids'])} -> {target.name}")
    return data


def main() -> int:
    data = read_row("Journey", "TestCaseId", "TC_E2E_01")
    driver = create_web_driver()
    try:
        home = HomePage(driver)
        login = LoginPage(driver)

        print("Steps 1-4: login")
        home.open()
        login.login(config.MOBILE_NUMBER, config.OTP)
        time.sleep(4)
        if not login.is_logged_in():
            print("ERROR: login failed - aborting")
            return 1
        print("  logged in")
        home.dismiss_onboarding_overlay()
        dump(driver, "01_home_logged_in")

        print("Step 5: pincode")
        try:
            print("  header now reads:", home.set_pincode(str(data["Pincode"])))
        except Exception as exc:  # noqa: BLE001
            print(f"  WARN pincode step failed: {type(exc).__name__}")

        print("Step 11: Toys & Games category")
        home.open_category("toys-games")
        time.sleep(6)
        dump(driver, "02_category_toys_games")

        print("Steps 12-13: filter panel")
        filters = driver.execute_script(
            """
            const ids = Array.from(document.querySelectorAll('[id]')).map(e => e.id);
            return {
              filterIds: ids.filter(id => /filter|brand|price|facet|sort/i.test(id)).slice(0, 60),
              labels: Array.from(document.querySelectorAll('label'))
                  .map(l => ({ id: l.id, text: l.innerText.trim().slice(0, 40) }))
                  .filter(l => l.text).slice(0, 40)
            };
            """
        )
        (FLOW_DIR / "03_filters.json").write_text(json.dumps(filters, indent=2),
                                                  encoding="utf-8")
        print(f"  filter ids: {len(filters['filterIds'])}, labels: {len(filters['labels'])}")

        print("Step 14-15: open the first product and inspect the detail page")
        first = driver.execute_script(
            "const a = document.querySelector('a[href*=\"/product-detail/\"]');"
            "return a ? a.href : null;"
        )
        if first:
            driver.get(first)
            time.sleep(7)
            dump(driver, "04_product_detail")

            print("Step 15: Start Bargaining")
            from pages.bargain_page import BargainPage

            bargain = BargainPage(driver)
            print("  product:", bargain.product_name())
            try:
                print("  asking price:", bargain.asking_price())
            except Exception as exc:  # noqa: BLE001
                print(f"  WARN could not read asking price: {type(exc).__name__}")

            bargain.start_bargaining()
            time.sleep(5)
            dump(driver, "05_bargain_modal")

            print("Step 16: three bargain rounds, then accept")
            try:
                asking = bargain.bargain(attempts=3)
                print(f"  bargained and accepted (asking was {asking})")
            except Exception as exc:  # noqa: BLE001
                print(f"  WARN bargain flow failed: {type(exc).__name__}: {exc}")
            time.sleep(6)
            dump(driver, "06_after_accept")

            print("Step 17: post-accept controls")
            outcome = driver.execute_script(
                """
                return {
                  buttons: Array.from(document.querySelectorAll('button'))
                    .map(b => ({ id: b.id, text: b.innerText.trim().slice(0, 40),
                                 disabled: b.disabled }))
                    .filter(b => b.text),
                  links: Array.from(document.querySelectorAll('a'))
                    .map(a => ({ id: a.id, text: a.innerText.trim().slice(0, 30) }))
                    .filter(a => /buy|checkout|cart|order/i.test(a.text || a.id)),
                  modalOpen: !!document.querySelector('#bargain-seller-modal'),
                  url: location.pathname
                };
                """
            )
            (FLOW_DIR / "07_bargain_outcome.json").write_text(
                json.dumps(outcome, indent=2), encoding="utf-8"
            )
            print("  modal open:", outcome["modalOpen"], "url:", outcome["url"])
            for b in outcome["buttons"]:
                if b["id"] or "Start Bargaining" not in b["text"]:
                    print(f"    btn {b['id']} => '{b['text']}'")
            for a in outcome["links"]:
                print(f"    link {a['id']} => '{a['text']}'")
            print("Step 17: Buy Now")
            try:
                bargain.buy_now()
                time.sleep(8)
                dump(driver, "08_after_buy_now")
                print("  url after Buy Now:", driver.current_url)
            except Exception as exc:  # noqa: BLE001
                print(f"  WARN Buy Now failed: {type(exc).__name__}")
                return 1

            print("Step 18: delivery address")
            from pages.checkout_page import CheckoutPage

            checkout = CheckoutPage(driver)
            try:
                print("  payable:", checkout.payable_amount())
            except Exception:  # noqa: BLE001
                print("  WARN could not read the payable amount")

            try:
                checkout.fill_address({
                    "name": data.get("AddressName"),
                    "phone": data.get("AddressPhone"),
                    "address": data.get("AddressLine"),
                    "address2": data.get("City"),
                    "pincode": data.get("Pincode"),
                })
                time.sleep(6)
                dump(driver, "09_after_address_saved")
            except Exception as exc:  # noqa: BLE001
                print(f"  WARN address step failed: {type(exc).__name__}: {exc}")
                dump(driver, "09_address_failed")

            print("Steps 19-20: payment")
            try:
                checkout.pay_now()
                time.sleep(12)
                dump(driver, "10_payment_page")
                frames = driver.execute_script(
                    "return Array.from(document.querySelectorAll('iframe'))"
                    ".map(f => ({ id: f.id, name: f.name, src: (f.src||'').slice(0,90) }));"
                )
                (FLOW_DIR / "11_payment_frames.json").write_text(
                    json.dumps(frames, indent=2), encoding="utf-8"
                )
                print("  url:", driver.current_url)
                print("  iframes:", len(frames))
                for f in frames:
                    print(f"    {f['id']} | {f['name']} | {f['src']}")
            except Exception as exc:  # noqa: BLE001
                print(f"  WARN payment step failed: {type(exc).__name__}: {exc}")
        else:
            print("  WARN no product link found on the listing")
    finally:
        driver.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
