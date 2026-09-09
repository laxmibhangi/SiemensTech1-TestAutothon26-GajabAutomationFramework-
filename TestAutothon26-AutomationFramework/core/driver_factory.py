"""Creates web (Selenium) and Android (Appium) drivers from configuration.

Selenium 4.6+ ships Selenium Manager, so browser drivers are resolved
automatically - no webdriver-manager needed.
"""
from __future__ import annotations

from appium import webdriver as appium_webdriver
from appium.options.android import UiAutomator2Options
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions

from config.settings import DOWNLOAD_DIR, config
from core.logger import get_logger

log = get_logger(__name__)

SUPPORTED_BROWSERS = ("chrome", "firefox", "edge")


def _chrome(headless: bool):
    opts = ChromeOptions()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-notifications")
    opts.add_argument("--disable-dev-shm-usage")
    # The site never goes idle (live-order polling, lottie animations), so a
    # 'normal' strategy times the renderer out. 'eager' returns at
    # DOMContentLoaded; BasePage adds window.stop() guards on top.
    opts.page_load_strategy = "eager"
    opts.add_experimental_option("prefs", {
        "download.default_directory": str(DOWNLOAD_DIR),
        "profile.default_content_setting_values.notifications": 2,
    })
    # Console logs only. Enabling 'performance' here floods the driver on this
    # site (constant live-order polling) and stalls execute_script calls.
    opts.set_capability("goog:loggingPrefs", {"browser": "ALL"})
    return webdriver.Chrome(options=opts)


def _firefox(headless: bool):
    opts = FirefoxOptions()
    if headless:
        opts.add_argument("-headless")
    opts.add_argument("--width=1920")
    opts.add_argument("--height=1080")
    opts.page_load_strategy = "eager"
    opts.set_preference("dom.webnotifications.enabled", False)
    opts.set_preference("browser.download.dir", str(DOWNLOAD_DIR))
    return webdriver.Firefox(options=opts)


def _edge(headless: bool):
    opts = EdgeOptions()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-notifications")
    opts.page_load_strategy = "eager"
    return webdriver.Edge(options=opts)


def create_web_driver(browser: str | None = None, headless: bool | None = None):
    """Return a ready-to-use Selenium WebDriver."""
    browser = (browser or config.BROWSER).lower()
    headless = config.HEADLESS if headless is None else headless

    if browser not in SUPPORTED_BROWSERS:
        raise ValueError(f"Unsupported browser '{browser}'. Use one of {SUPPORTED_BROWSERS}.")

    log.info("Launching %s (headless=%s)", browser, headless)
    driver = {"chrome": _chrome, "firefox": _firefox, "edge": _edge}[browser](headless)
    driver.maximize_window()
    driver.set_page_load_timeout(25)
    return driver


def create_android_driver():
    """Return an Appium driver bound to a physical Android device over adb.

    Requires: `appium` running, USB debugging enabled, device visible in
    `adb devices`.
    """
    opts = UiAutomator2Options()
    opts.platform_name = "Android"
    opts.automation_name = "UiAutomator2"
    opts.new_command_timeout = 300
    opts.auto_grant_permissions = True
    opts.set_capability("appium:ignoreHiddenApiPolicyError", True)

    if config.ANDROID_UDID:
        opts.udid = config.ANDROID_UDID
    if config.ANDROID_PLATFORM_VERSION:
        opts.platform_version = config.ANDROID_PLATFORM_VERSION

    # Prefer installing the APK; fall back to launching an already-installed build.
    if config.ANDROID_APP_PATH:
        opts.app = config.ANDROID_APP_PATH
    else:
        opts.app_package = config.ANDROID_APP_PACKAGE
        if config.ANDROID_APP_ACTIVITY:
            opts.app_activity = config.ANDROID_APP_ACTIVITY

    log.info("Connecting to Appium at %s (udid=%s)",
             config.APPIUM_SERVER_URL, config.ANDROID_UDID or "<auto>")
    return appium_webdriver.Remote(config.APPIUM_SERVER_URL, options=opts)
