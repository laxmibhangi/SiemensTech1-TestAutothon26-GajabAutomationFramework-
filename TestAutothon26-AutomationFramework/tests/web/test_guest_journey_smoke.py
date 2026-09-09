"""Login-free coverage of the journey steps that work as a guest.

Lets the framework be validated end-to-end before an authorised test mobile
number is available. Covers steps 1, 5, 6, 8, 9, 10 and 11.

Run:  pytest tests/web/test_guest_journey_smoke.py --browser chrome
"""
from __future__ import annotations

import allure
import pytest

from core.excel_reader import read_row
from pages.home_page import HomePage
from pages.product_list_page import ProductListPage

pytestmark = [pytest.mark.web, pytest.mark.smoke]


@pytest.fixture
def journey_data():
    return read_row("Journey", "TestCaseId", "TC_E2E_01")


@allure.feature("Guest browsing")
def test_step1_home_page_loads(driver):
    home = HomePage(driver)
    home.open()
    assert "Gajab" in driver.title


@allure.feature("Guest browsing")
def test_step5_pincode_is_reflected(driver, journey_data):
    home = HomePage(driver)
    home.open()
    pincode = str(journey_data["Pincode"])
    label = home.set_pincode(pincode)
    assert pincode in label, f"Pincode not reflected in header. Header shows: {label}"


@allure.feature("Guest browsing")
def test_step6_capture_deal_of_the_day(driver):
    home = HomePage(driver)
    home.open()
    deal = home.deal_of_the_day()
    assert deal.name, "Deal of the Day product name is empty"
    assert deal.price > 0, "Deal of the Day price could not be parsed"
    allure.attach(f"{deal.name} @ INR {deal.price}", name="deal-of-the-day")


@allure.feature("Guest browsing")
def test_step8_most_bargained_trending_product(driver):
    home = HomePage(driver)
    home.open()
    trending = home.most_bargained_trending_product()
    assert trending.bargains > 0, "No bargain counts found in Trending"
    allure.attach(f"{trending.name} - {trending.bargains} bargains",
                  name="most-bargained-trending")


@allure.feature("Guest browsing")
def test_step9_latest_live_order(driver):
    home = HomePage(driver)
    home.open()
    order = home.latest_live_order()
    assert order.name, "Could not read the live order customer name"
    assert order.city, "Could not read the live order city"
    home.capture_live_orders()
    allure.attach(f"{order.name} / {order.city}", name="latest-live-order")


@allure.feature("Guest browsing")
def test_step10_cheapest_among_most_bargained(driver):
    home = HomePage(driver)
    home.open()
    home.open_just_bargained_view_all()
    cheapest = ProductListPage(driver).cheapest_among_most_bargained()
    assert cheapest.price > 0
    allure.attach(f"{cheapest.name} @ INR {cheapest.price}", name="cheapest-most-bargained")


@allure.feature("Guest browsing")
def test_step11_open_toys_and_games_category(driver):
    home = HomePage(driver)
    home.open()
    home.open_category("toys-games")
    assert "toys-games" in driver.current_url
