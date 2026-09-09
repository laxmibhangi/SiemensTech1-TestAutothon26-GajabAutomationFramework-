r"""Performs the PDF login flow (steps 2-4) and captures the OTP screen locators.

Reads the mobile number from .env so it never appears in chat, logs or reports.
Writes the discovered element ids to reports/otp_dom.json so the page objects
can be finalised.

Run:  .\.venv\Scripts\python.exe scripts\login_and_capture.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import REPORTS_DIR, config  # noqa: E402
from core.driver_factory import create_web_driver  # noqa: E402
from pages.home_page import HomePage  # noqa: E402
from pages.login_page import LoginPage  # noqa: E402

DOM_DUMP_JS = """
const ids = [...new Set(Array.from(document.querySelectorAll('[id]')).map(e => e.id))]
    .filter(id => /otp|signin|verify|resend|timer|submit/i.test(id));
const inputs = Array.from(document.querySelectorAll('input')).map(i => ({
    id: i.id, type: i.type, placeholder: i.placeholder,
    maxLength: i.maxLength, inputMode: i.inputMode, autocomplete: i.autocomplete
}));
const buttons = Array.from(document.querySelectorAll('button'))
    .map(b => ({ id: b.id, text: b.innerText.trim().slice(0, 40), disabled: b.disabled }))
    .filter(b => b.text);
return { url: location.pathname, ids, inputs, buttons };
"""


def main() -> int:
    if not config.MOBILE_NUMBER:
        print("ERROR: TEST_MOBILE_NUMBER is not set in .env - add the authorised "
              "test number there and re-run.")
        return 1

    driver = create_web_driver()
    try:
        home = HomePage(driver)
        login = LoginPage(driver)

        print("Step 1: navigating to the Gajab website")
        home.open()

        print("Step 2: clicking Log in / Sign up")
        login.go_to_login()

        print(f"Step 3: entering mobile {config.masked_mobile()} and requesting OTP")
        login.enter_mobile_and_request_otp(config.MOBILE_NUMBER)

        import time
        time.sleep(6)

        dump = driver.execute_script(DOM_DUMP_JS)
        target = REPORTS_DIR / "otp_dom.json"
        target.write_text(json.dumps(dump, indent=2), encoding="utf-8")
        print(f"OTP screen structure captured -> {target}")

        print(f"Step 4: entering the default OTP and submitting")
        login.enter_otp(config.OTP).submit()
        time.sleep(6)

        login.screenshot("after_login_submit")
        print(f"Logged in: {login.is_logged_in()}")
        print(f"Landing URL: {driver.current_url}")

        post = driver.execute_script(DOM_DUMP_JS)
        (REPORTS_DIR / "post_login_dom.json").write_text(
            json.dumps(post, indent=2), encoding="utf-8"
        )
    finally:
        driver.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
