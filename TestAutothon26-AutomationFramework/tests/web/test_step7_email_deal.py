"""Journey step 7 - email the Deal of the Day details.

Captures the product image, name and asking price, then emails them.
Requires SMTP_HOST / SMTP_USER / SMTP_PASSWORD / EMAIL_TO in .env.

Run:  pytest tests/web/test_step7_email_deal.py --browser chrome
"""
from __future__ import annotations

import allure
import pytest

from config.settings import config
from core.emailer import download_image, send_email
from pages.home_page import HomePage

pytestmark = [pytest.mark.web, pytest.mark.smoke]


@allure.feature("Deal of the Day")
@allure.title("Step 7 - email the Deal of the Day image, name and asking price")
def test_step7_email_deal_of_the_day(driver):
    if not (config.SMTP_HOST and config.SMTP_USER and config.SMTP_PASSWORD
            and config.EMAIL_TO):
        pytest.skip("SMTP not configured in .env - see README")

    home = HomePage(driver)
    home.open()

    with allure.step("Step 6 - capture the Deal of the Day"):
        deal = home.deal_of_the_day()
        assert deal.name, "Deal of the Day product name is empty"
        assert deal.price > 0, "Deal of the Day asking price could not be parsed"
        assert deal.image_url, "Deal of the Day image URL is empty"

    with allure.step("Download the product image"):
        image_path = download_image(deal.image_url)
        assert image_path.stat().st_size > 0, "Downloaded image is empty"
        allure.attach.file(str(image_path), name="deal-of-the-day",
                           attachment_type=allure.attachment_type.PNG)

    with allure.step(f"Email the details to {config.EMAIL_TO}"):
        body = (
            "Gajab - Deal of the Day\n\n"
            f"Product name : {deal.name}\n"
            f"Asking price : INR {deal.price:,.2f}\n"
            f"Product URL  : {deal.url}\n\n"
            "The product image is attached.\n"
        )
        html = (
            "<h2>Gajab - Deal of the Day</h2>"
            f"<p><b>Product name:</b> {deal.name}</p>"
            f"<p><b>Asking price:</b> INR {deal.price:,.2f}</p>"
            f'<p><a href="{deal.url}">View product</a></p>'
            f'<p><img src="{deal.image_url}" alt="{deal.name}" width="320"></p>'
        )
        send_email(
            subject=f"Gajab Deal of the Day - {deal.name[:60]}",
            body=body,
            attachments=[image_path],
            html=html,
        )

    allure.attach(f"{deal.name} @ INR {deal.price}", name="emailed-deal")
