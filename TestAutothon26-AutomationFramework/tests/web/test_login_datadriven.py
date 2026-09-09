"""Data-driven login coverage (positive and negative sets from Excel)."""
from __future__ import annotations

import pytest

from core.excel_reader import read_sheet
from pages.home_page import HomePage
from pages.login_page import LoginPage

pytestmark = pytest.mark.web

LOGIN_DATA = read_sheet("Login")


@pytest.mark.parametrize(
    "case",
    LOGIN_DATA,
    ids=[f"{row['TestCaseId']}-{row['Scenario']}" for row in LOGIN_DATA],
)
def test_login_scenarios(driver, case):
    HomePage(driver).open()
    login = LoginPage(driver)

    login.go_to_login().enter_mobile_and_request_otp(str(case["MobileNumber"]))

    if str(case["ExpectedResult"]).lower() == "pass":
        login.enter_otp(str(case["Otp"])).submit()
        assert login.is_logged_in(), f"{case['Scenario']}: expected a successful login"
    else:
        if case.get("Otp"):
            login.enter_otp(str(case["Otp"])).submit()
        assert not login.is_logged_in(), (
            f"{case['Scenario']}: login succeeded but should have been rejected"
        )
