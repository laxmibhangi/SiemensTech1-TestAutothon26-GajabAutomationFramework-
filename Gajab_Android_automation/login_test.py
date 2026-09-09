import time

from appium import webdriver
from appium.options.android import UiAutomator2Options
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# =========================
# TEST DATA
# =========================

MOBILE_NUMBER = "YOUR_MOBILE_NUMBER"
OTP = "123456"
PINCODE = "560037"


# =========================
# DRIVER SETUP
# =========================

def create_driver():
    options = UiAutomator2Options()

    options.platform_name = "Android"
    options.automation_name = "UiAutomator2"
    options.device_name = "Android"

    options.app_package = "com.gajab.buyerstore"
    options.app_activity = "com.gajab.buyerstore.MainActivity"

    # Reset app state for every execution
    options.no_reset = False
    options.force_app_launch = True

    return webdriver.Remote(
        "http://127.0.0.1:4723",
        options=options
    )


# =========================
# TEST FLOW
# =========================

def test_login_and_delivery_setup(driver):

    wait = WebDriverWait(driver, 10)

    print("\n========== TEST START ==========")

    # ---------------------------------
    # 1. Get Started
    # ---------------------------------

    get_started = wait.until(
        EC.presence_of_element_located(
            (AppiumBy.ACCESSIBILITY_ID, "welcome_get_started_button")
        )
    )

    get_started.click()
    print("✓ Get Started clicked")

    # ---------------------------------
    # 2. Enter Mobile Number
    # ---------------------------------

    # Mobile field is automatically focused
    driver.switch_to.active_element.send_keys(MOBILE_NUMBER)
    print("✓ Mobile number entered")

    # ---------------------------------
    # 3. Accept Terms
    # ---------------------------------

    terms = wait.until(
        EC.presence_of_element_located(
            (AppiumBy.ACCESSIBILITY_ID, "login_terms_checkbox")
        )
    )

    if not terms.is_selected():
        terms.click()

    print("✓ Terms accepted")

    # ---------------------------------
    # 4. Continue
    # ---------------------------------

    next_button = wait.until(
        EC.presence_of_element_located(
            (AppiumBy.ACCESSIBILITY_ID, "login_next_button")
        )
    )

    next_button.click()
    print("✓ Next clicked")

    # ---------------------------------
    # 5. Enter OTP
    # ---------------------------------

    time.sleep(1)

    # OTP field is automatically focused
    driver.switch_to.active_element.send_keys(OTP)
    print("✓ OTP entered")

    # Submit button is not reliably exposed
    # through accessibility lookup, so coordinate tap
    # is used as a fallback.
    driver.tap([(720, 1436)])
    print("✓ OTP submitted")

    # ---------------------------------
    # 6. Select English
    # ---------------------------------

    language_button = wait.until(
        EC.presence_of_element_located(
            (AppiumBy.ACCESSIBILITY_ID, "language_option_eng_button")
        )
    )

    language_button.click()
    print("✓ English selected")

    # ---------------------------------
    # 7. System Permissions
    # ---------------------------------

    print("\n⚠ System notification/location permissions")
    print("  are handled manually for this execution.")

    time.sleep(2)

    # ---------------------------------
    # 8. Enter Pincode
    # ---------------------------------

    # Pincode field is automatically focused
    driver.switch_to.active_element.send_keys(PINCODE)
    print("✓ Pincode entered")

    # ---------------------------------
    # 9. Select Address Suggestion
    # ---------------------------------

    suggestion = wait.until(
        EC.presence_of_element_located(
            (
                AppiumBy.ACCESSIBILITY_ID,
                "delivery_address_suggestion_0_item"
            )
        )
    )

    suggestion.click()
    print("✓ Address suggestion selected")

    print("\n========== FLOW COMPLETED ==========")


# =========================
# MAIN
# =========================

if __name__ == "__main__":

    driver = None

    try:
        driver = create_driver()
        print("✓ Appium connected")

        test_login_and_delivery_setup(driver)

        print("\n✓ All automated steps completed successfully")

        input("\nPress Enter to close...")

    except Exception as error:

        print("\n✗ TEST FAILED")
        print(f"Error: {error}")

        input("\nPress Enter to close...")

    finally:

        if driver:
            driver.quit()

        print("\n========== DRIVER CLOSED ==========")