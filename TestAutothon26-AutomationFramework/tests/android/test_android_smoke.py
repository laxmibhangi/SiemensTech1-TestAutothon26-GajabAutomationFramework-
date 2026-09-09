"""Android coverage executed on a real device over adb.

Prerequisites:
    1. USB debugging enabled, device listed by `adb devices`
    2. `appium` server running on APPIUM_SERVER_URL
    3. ANDROID_UDID set in .env
Run:  pytest tests/android -m android
"""
from __future__ import annotations

import allure
import pytest

from config.settings import config
from core.excel_reader import read_row
from screens.android_screens import AndroidHomeScreen, AndroidLoginScreen

pytestmark = pytest.mark.android


@allure.feature("Android - Gajab app")
def test_app_launches_and_shows_home(android_driver):
    home = AndroidHomeScreen(android_driver)
    assert home.deal_of_the_day_visible(), "Deal Of The Day widget not shown on launch"
    allure.attach.file(home.screenshot("home"), name="android-home",
                       attachment_type=allure.attachment_type.PNG)


@allure.feature("Android - Gajab app")
def test_android_login_with_default_otp(android_driver):
    data = read_row("Journey", "TestCaseId", "TC_E2E_01")
    login = AndroidLoginScreen(android_driver)
    login.login(config.MOBILE_NUMBER, config.OTP)

    home = AndroidHomeScreen(android_driver)
    assert home.deal_of_the_day_visible(), "Home did not load after login"
    allure.attach.file(home.screenshot("post_login"), name="android-post-login",
                       attachment_type=allure.attachment_type.PNG)
    _ = data  # test data hook for parameterised expansion
