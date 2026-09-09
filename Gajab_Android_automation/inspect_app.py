from appium import webdriver
from appium.options.android import UiAutomator2Options
import time

options = UiAutomator2Options()

options.platform_name = "Android"
options.automation_name = "UiAutomator2"
options.device_name = "Android"

options.app_package = "com.gajab.buyerstore"
options.app_activity = "com.gajab.buyerstore.MainActivity"

options.no_reset = False
options.force_app_launch = True

driver = webdriver.Remote(
    "http://127.0.0.1:4723",
    options=options
)

print("Appium connected!")

time.sleep(3)

print("\n========== CURRENT SCREEN ==========\n")
xml = driver.page_source

print("\n========== USEFUL ELEMENTS ==========\n")

for line in xml.splitlines():
    if any(x in line for x in [
        'EditText',
        'Button',
        'resource-id=',
        'content-desc=',
        'text='
    ]):
        print(line.strip())

input("\nPress Enter to close...")

driver.quit()