"""Gajab automation test script using Appium for Android UI testing."""
import time
from appium import webdriver
from appium.options.android import UiAutomator2Options

options = UiAutomator2Options()

options.platform_name = "Android"
options.automation_name = "UiAutomator2"
options.device_name = "Android"
options.app_package = "com.gajab.buyerstore"
options.app_activity = "com.gajab.buyerstore.MainActivity"

options.no_reset = False

driver = webdriver.Remote(
    "http://127.0.0.1:4723",
    options=options
)

print("Appium connected successfully!")

# Explicitly bring Gajab to the foreground
driver.activate_app("com.gajab.buyerstore")

time.sleep(5)

print("Current package:", driver.current_package)

input("Press Enter to close the Appium session...")

driver.quit()
print("Test completed!")