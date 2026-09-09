# TestAutothon 2026 - Gajab Automation Framework

Python + Selenium + Appium + pytest framework covering the Gajab bargain-to-order
journey on **web** (Chrome / Firefox / Edge) and **Android** (real device over adb).

> Rename this repo to `<TeamName>-TestAutothon26-AutomationFramework` before submitting.

## Structure

```
config/     settings.py        environment-driven configuration (no secrets in code)
core/       driver_factory.py  web + Appium driver creation
            excel_reader.py    Excel-backed test data provider
            emailer.py         SMTP send + product image download
            logger.py          run-scoped file and console logging
pages/      page objects for the web application
screens/    screen objects for the Android app
tests/web/  browser tests (E2E journey, data-driven login)
tests/android/ real-device tests
scripts/    generate_testdata.py -> testdata/test_data.xlsx
reports/    HTML + Allure output, screenshots, logs (git-ignored)
```

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env      # then fill in the values
python scripts\generate_testdata.py
```

## Running

```powershell
pytest -m web --browser chrome            # single browser
pytest -m web --browser firefox --headless
pytest -m e2e --language Hinglish         # language coverage
pytest -m web -n 4                        # parallel
pytest -m android                         # real Android device
```

Allure report:

```powershell
allure serve reports\allure-results
```

## Android on a real device

No emulator or virtualization required.

The Gajab app (`com.gajab.buyerstore`, launcher `MainActivity`) is a **Flutter
release build** whose backend points at `stg.gajab.com` - the correct staging
target. Because Flutter draws to a single canvas there is no native view
hierarchy: locate elements by **content-desc / accessibility id**, and enable an
accessibility service (TalkBack) on the device so the semantics tree is exposed.

1. Install [SDK Platform-Tools](https://developer.android.com/tools/releases/platform-tools),
   set `ANDROID_HOME` and add `platform-tools` to `PATH`.
2. Install Temurin **JDK 17** and set `JAVA_HOME`.
3. `npm i -g appium` then `appium driver install uiautomator2`.
4. On the phone: enable Developer Options -> **USB Debugging**, connect by USB,
   accept the RSA prompt. Turn **TalkBack on** for the automation run.
5. `adb devices` -> copy the id into `ANDROID_UDID` in `.env`.
6. `adb install ..\gajab-hackathon-sep4.apk`
7. Start the server with `appium`, then `pytest -m android`.

Use **Appium Inspector** to confirm the locators in `screens/android_screens.py`
against the installed build.

## Security notes

- No credential, OTP or mobile number is stored in the repo; everything comes from
  `.env` (git-ignored) or CI secrets.
- Mobile numbers are masked in logs via `Config.masked_mobile()`.
- Testing is restricted to `https://stg.gajab.com` - production is never touched.

## Known limitations

- Web locators are text-based and need confirmation against the live staging DOM.
- Android screen locators are placeholders pending an Appium Inspector session.
- The Android job is not wired into CI because GitHub-hosted runners have no
  physical device; it runs locally against a connected handset.
