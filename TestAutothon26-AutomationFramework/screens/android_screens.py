"""Android screen objects for the Gajab APK (real device over adb).

IMPORTANT - the Gajab app (com.gajab.buyerstore) is a **Flutter release build**:

* Flutter renders to a single canvas, so there is NO native view hierarchy and
  NO resource-id. Locating by resource-id or android.widget.* XPath will fail.
* UiAutomator2 can only see Flutter's *semantics tree*, and only while an
  accessibility service is active. Enable TalkBack (or any a11y service) on the
  device first, otherwise Appium Inspector shows one empty FlutterView.
* Therefore: locate by ACCESSIBILITY_ID (content-desc) or UiSelector textContains.
* appium-flutter-driver is NOT usable here - it requires a debug/profile build
  with the Dart VM service exposed. This is a release build.

Confirm every locator with Appium Inspector before relying on it.
"""
from __future__ import annotations

from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from config.settings import SCREENSHOT_DIR, config
from core.logger import get_logger

log = get_logger(__name__)


class BaseScreen:
    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, config.EXPLICIT_WAIT)

    def find(self, locator):
        return self.wait.until(EC.presence_of_element_located(locator))

    def tap(self, locator):
        self.find(locator).click()

    def type(self, locator, text: str):
        element = self.find(locator)
        element.clear()
        element.send_keys(text)

    def is_visible(self, locator, timeout: int = 5) -> bool:
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.visibility_of_element_located(locator)
            )
            return True
        except Exception:
            return False

    def screenshot(self, name: str) -> str:
        path = SCREENSHOT_DIR / f"android_{name}.png"
        self.driver.get_screenshot_as_file(str(path))
        return str(path)

    def scroll_to_text(self, text: str):
        """UiScrollable-based scroll - much faster than swipe loops."""
        return self.driver.find_element(
            AppiumBy.ANDROID_UIAUTOMATOR,
            'new UiScrollable(new UiSelector().scrollable(true))'
            f'.scrollIntoView(new UiSelector().descriptionContains("{text}"))',
        )


class AndroidLoginScreen(BaseScreen):
    # Flutter exposes widgets through content-desc / semantics labels only.
    LOGIN_ENTRY = (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().descriptionContains("Log in")')
    MOBILE_INPUT = (AppiumBy.CLASS_NAME, "android.widget.EditText")
    REQUEST_OTP = (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().descriptionContains("OTP")')
    SUBMIT = (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().descriptionContains("Submit")')

    def login(self, mobile: str, otp: str):
        log.info("Android login for %s", config.masked_mobile())
        self.tap(self.LOGIN_ENTRY)
        self.type(self.MOBILE_INPUT, mobile)
        self.tap(self.REQUEST_OTP)
        for element, digit in zip(self.driver.find_elements(*self.MOBILE_INPUT), otp):
            element.send_keys(digit)
        self.tap(self.SUBMIT)


class AndroidHomeScreen(BaseScreen):
    DEAL_OF_THE_DAY = (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().descriptionContains("Deal Of The Day")')
    TRENDING = (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().descriptionContains("Trending")')
    START_BARGAINING = (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().descriptionContains("Start Bargaining")')

    def deal_of_the_day_visible(self) -> bool:
        return self.is_visible(self.DEAL_OF_THE_DAY, timeout=30)
