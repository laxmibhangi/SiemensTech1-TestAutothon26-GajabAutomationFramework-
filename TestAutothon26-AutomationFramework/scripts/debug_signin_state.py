r"""Ad-hoc diagnostic for the sign-in form state. Not part of the test suite.

Run:  .\.venv\Scripts\python.exe scripts\debug_signin_state.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import config  # noqa: E402
from core.driver_factory import create_web_driver  # noqa: E402
from pages.home_page import HomePage  # noqa: E402
from pages.login_page import LoginPage  # noqa: E402

STATE_JS = """
const btn = document.querySelector('#signin-submit-btn');
const cb  = document.querySelector('#signin-terms-checkbox');
const inp = document.querySelector('#signin-mobile-input');
return {
  url: location.pathname,
  mobileLength: inp ? inp.value.length : null,
  termsChecked: cb ? cb.checked : null,
  btnFound: !!btn,
  btnDisabled: btn ? btn.disabled : null,
  btnAriaDisabled: btn ? btn.getAttribute('aria-disabled') : null,
  btnText: btn ? btn.innerText.trim() : null,
  btnCount: document.querySelectorAll('#signin-submit-btn').length,
  mobileCount: document.querySelectorAll('#signin-mobile-input').length
};
"""


def show(driver, label: str) -> None:
    print(f"--- {label} ---")
    print(json.dumps(driver.execute_script(STATE_JS), indent=2))


def main() -> int:
    driver = create_web_driver()
    try:
        HomePage(driver).open()
        login = LoginPage(driver)
        login.go_to_login()
        show(driver, "on signin page")

        login.set_react_input(login.MOBILE_INPUT, config.MOBILE_NUMBER)
        time.sleep(1.5)
        show(driver, "after set_react_input")

        login.accept_terms()
        time.sleep(1.5)
        show(driver, "after accepting terms")

        btn = login.find_visible(login.REQUEST_OTP_BTN)
        print("--- selenium view of the button ---")
        print(json.dumps({
            "is_enabled": btn.is_enabled(),
            "is_displayed": btn.is_displayed(),
            "disabled_attr": btn.get_attribute("disabled"),
            "class": (btn.get_attribute("class") or "")[:80],
            "matches": len(driver.find_elements(*login.REQUEST_OTP_BTN)),
        }, indent=2))
    finally:
        driver.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
