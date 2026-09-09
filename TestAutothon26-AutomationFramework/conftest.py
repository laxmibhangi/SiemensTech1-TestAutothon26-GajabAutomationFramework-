"""Shared pytest fixtures, CLI options and failure-evidence hooks."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.settings import SCREENSHOT_DIR, config  # noqa: E402
from core.driver_factory import create_android_driver, create_web_driver  # noqa: E402
from core.logger import get_logger  # noqa: E402

log = get_logger("conftest")


def pytest_addoption(parser):
    parser.addoption("--browser", action="store", default=None,
                     help="chrome | firefox | edge")
    parser.addoption("--headless", action="store_true", default=None,
                     help="Run the browser headless")
    parser.addoption("--language", action="store", default=None,
                     help="English | Hinglish")


@pytest.fixture(scope="session")
def browser_name(request) -> str:
    return (request.config.getoption("--browser") or config.BROWSER).lower()


@pytest.fixture(scope="session")
def language(request) -> str:
    return request.config.getoption("--language") or config.DEFAULT_LANGUAGE


@pytest.fixture
def driver(request, browser_name):
    """Function-scoped browser so a failed journey cannot poison the next test."""
    headless = request.config.getoption("--headless")
    web_driver = create_web_driver(browser_name, headless)
    request.node._driver = web_driver
    yield web_driver
    web_driver.quit()


@pytest.fixture
def android_driver(request):
    """Requires a real device: USB debugging on and visible in `adb devices`."""
    try:
        mobile_driver = create_android_driver()
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"Android device/Appium unavailable: {exc}")
        return
    request.node._driver = mobile_driver
    yield mobile_driver
    mobile_driver.quit()


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_makereport(item, call):
    """Attach a screenshot and browser console logs to every failure."""
    outcome = yield
    report = outcome.get_result()

    if report.when != "call" or not report.failed:
        return

    active_driver = getattr(item, "_driver", None)
    if active_driver is None:
        return

    shot = SCREENSHOT_DIR / f"FAILURE_{item.name}.png"
    try:
        active_driver.save_screenshot(str(shot))
        log.error("Failure screenshot -> %s", shot)
    except Exception:  # noqa: BLE001
        pass

    try:
        import allure

        allure.attach.file(str(shot), name="failure-screenshot",
                           attachment_type=allure.attachment_type.PNG)
        for entry in active_driver.get_log("browser"):
            if entry.get("level") in ("SEVERE", "ERROR"):
                allure.attach(str(entry), name="console-error",
                              attachment_type=allure.attachment_type.TEXT)
    except Exception:  # noqa: BLE001
        pass
