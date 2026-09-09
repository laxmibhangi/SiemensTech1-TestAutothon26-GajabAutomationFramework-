"""The mandated 22-step Gajab bargain-to-order journey.

Run:  pytest tests/web/test_e2e_bargain_journey.py --browser chrome
"""
from __future__ import annotations

import allure
import pytest

from config.settings import config
from core.emailer import download_image, send_email
from core.excel_reader import read_row
from pages.bargain_page import BargainPage
from pages.checkout_page import CheckoutPage, MyBargainsPage
from pages.home_page import HomePage
from pages.login_page import LoginPage
from pages.product_list_page import ProductListPage

pytestmark = [pytest.mark.web, pytest.mark.e2e]


@pytest.fixture
def journey_data():
    return read_row("Journey", "TestCaseId", "TC_E2E_01")


@allure.feature("Bargain to Order")
@allure.severity(allure.severity_level.BLOCKER)
def test_end_to_end_bargain_journey(driver, language, journey_data):
    home = HomePage(driver)
    login = LoginPage(driver)

    with allure.step("1. Navigate to the Gajab website"):
        home.open()

    with allure.step("2-4. Log in with mobile number and default OTP"):
        login.login(config.MOBILE_NUMBER, config.OTP)
        assert login.is_logged_in(), "Login did not complete successfully"

    if language.lower() != "english":
        with allure.step(f"Switch language to {language}"):
            home.set_language(language)

    with allure.step("5. Set the pincode and confirm it is reflected"):
        label = home.set_pincode(journey_data.get("Pincode") or config.PINCODE)
        assert str(journey_data.get("Pincode") or config.PINCODE) in label, (
            f"Pincode not reflected in header. Header shows: {label}"
        )

    with allure.step("6-7. Capture the Deal of the Day and email it"):
        deal = home.deal_of_the_day()
        assert deal.name and deal.price > 0
        image_path = download_image(deal.image_url)
        send_email(
            subject=f"Gajab Deal of the Day - {deal.name}",
            body=f"Product: {deal.name}\nAsking Price: INR {deal.price:.2f}\nImage attached.",
            attachments=[image_path],
        )
        allure.attach.file(str(image_path), name="deal-of-the-day",
                           attachment_type=allure.attachment_type.PNG)

    with allure.step("8. Identify the most-bargained trending product"):
        trending = home.most_bargained_trending_product()
        assert trending.bargains > 0
        allure.attach(f"{trending.name} - {trending.bargains} bargains",
                      name="most-bargained-trending")

    with allure.step("9. Verify the latest live order"):
        order = home.latest_live_order()
        assert order.name, "Could not read the live order customer name"
        home.capture_live_orders()
        allure.attach(f"{order.name} / {order.city}", name="latest-live-order")

    with allure.step("10. Cheapest product among the most-bargained list"):
        home.open_just_bargained_view_all()
        listing = ProductListPage(driver)
        cheapest = listing.cheapest_among_most_bargained()
        allure.attach(f"{cheapest.name} @ INR {cheapest.price}", name="cheapest-most-bargained")

    with allure.step("11-13. Toys & Games, then apply the brand and price filters"):
        home.open()
        home.open_category("toys-games")
        listing.apply_filter(journey_data["Brand"])
        if journey_data.get("SecondFilter"):
            listing.apply_filter(journey_data["SecondFilter"])

    with allure.step("14-16. Open the product and bargain three times, then accept"):
        listing.open_product(journey_data["ProductName"])
        bargain = BargainPage(driver)
        final_price = bargain.bargain(attempts=int(journey_data.get("BargainAttempts", 3)))
        assert final_price > 0

    with allure.step("17-20. Buy Now, address, Net Banking, payment success"):
        bargain.buy_now()
        checkout = CheckoutPage(driver)
        checkout.fill_address({
            "name": journey_data.get("AddressName"),
            "phone": journey_data.get("AddressPhone"),
            "pincode": journey_data.get("Pincode"),
            "address": journey_data.get("AddressLine"),
            "city": journey_data.get("City"),
        })
        checkout.pay_with_net_banking().complete_payment()

    with allure.step("21. Verify the order was placed"):
        assert checkout.is_order_placed(), "Order confirmation was not displayed"
        checkout.screenshot("order_confirmation")

    with allure.step("22. Open My Bargains and verify the savings"):
        savings = MyBargainsPage(driver).open_my_bargains().total_savings()
        assert savings >= 0
        allure.attach(f"Total savings: INR {savings}", name="my-bargains-savings")
