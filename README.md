# SiemensTech1-TestAutothon26-GajabAutomationFramework-
# Gajab TestAutothon 2026 – Android Automation

Android automation implementation for the STeP-IN TestAutothon 2026 challenge.

## Overview

This project automates the initial user onboarding and delivery-location flow of the Gajab Buyer Android application using:

- Python
- Appium
- UiAutomator2
- Android Debug Bridge (ADB)

## Automated Flow

The current implementation covers:

1. Launch Gajab Buyer application
2. Click Get Started
3. Enter mobile number
4. Accept Terms & Conditions
5. Continue to OTP verification
6. Enter OTP
7. Submit OTP
8. Select English as preferred language
9. Enter delivery pincode
10. Select the first address suggestion from the dropdown

## Project Structure

```text
Gajab Automation/
│
├── login_test.py      # Main Android automation flow
├── inspect_app.py     # Utility for inspecting application UI
└── test_app.py        # Application/test experimentation

