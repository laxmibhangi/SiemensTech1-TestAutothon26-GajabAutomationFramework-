# Test Strategy — Gajab Bargain Bazar (stg.gajab.com)

**Project:** TestAutothon 2026 — Automation Quest
**Application:** Gajab Bargain Bazar (bargaining e-commerce marketplace)
**Environment:** Staging — `https://stg.gajab.com/`
**Author:** QA Automation Team
**Version:** 1.0 · 2026-09-09

---

## 1. Purpose

This document defines the overall test strategy for validating the Gajab
bargaining marketplace: what we test, how we test it, the tools and
environments used, and the criteria for success. It covers the end-to-end
customer journey (browse → bargain → buy → verify) plus functional,
non-functional, and defect-discovery testing.

---

## 2. Scope

### 2.1 In Scope
- **End-to-end customer journey** (22-step challenge flow): landing, login
  (mobile + OTP), pincode/location, product discovery (deal of the day, most
  bargained, live orders, categories), bargaining, purchase, payment
  (Pay Online → Net Banking), and order/savings verification.
- **Functional testing** of core modules: authentication, search & browse,
  category/brand/price filtering, bargaining engine, cart & checkout,
  payment, order confirmation, and "My Bargains".
- **Data-driven login** (positive & negative cases) from Excel.
- **Non-functional checks:** accessibility (WCAG via axe-core), page-load
  performance budgets, and visual regression.
- **Cross-browser** (Chrome, Edge, Firefox) and **localization** (English,
  Hinglish).
- **Defect discovery** via automated site audit (console/JS errors, failed
  network requests, broken images, SEO/meta issues).

### 2.2 Out of Scope
- Backend/API contract testing and database validation (no access on staging).
- Real payment settlement (staging uses test payment paths only).
- Load/stress/performance-at-scale testing.
- Native Android app (placeholders provided for future extension via Appium).
- Security penetration testing (only observational, non-intrusive checks).

---

## 3. Test Objectives

1. Confirm the complete bargaining purchase journey works end-to-end.
2. Validate business rules: price filters, bargain attempts/limits, savings.
3. Ensure login works with valid data and fails gracefully with invalid data.
4. Surface functional, accessibility, performance, and visual defects early.
5. Provide repeatable, cross-browser, data-driven, CI-runnable automation.

---

## 4. Test Approach

### 4.1 Test Levels
| Level | Coverage | Method |
|-------|----------|--------|
| Component / UI | Individual pages & controls (locators, actions) | Page Object Model classes |
| Integration | Module-to-module flow (login → browse → checkout) | Playwright fixtures |
| System / E2E | Full 22-step customer journey | `test_e2e_journey.py` |
| Non-functional | A11y, performance, visual | axe-core, nav-timing, Pillow diff |

### 4.2 Test Types
- **Functional:** happy path + alternate flows for each module.
- **Data-driven:** login and journey data sourced from `data/test_data.xlsx`
  (positive/negative cases parametrized).
- **Cross-browser:** Chrome / Edge / Firefox.
- **Localization:** English & Hinglish string bundles.
- **Accessibility:** axe-core scans against WCAG 2.1 A/AA.
- **Performance:** navigation-timing load budget per key page.
- **Visual regression:** baseline vs. actual full-page screenshot diff.
- **Exploratory / defect audit:** automated crawl capturing JS errors, HTTP
  4xx/5xx, broken images, and metadata issues.

### 4.3 Test Design Techniques
- Equivalence partitioning & boundary values (price range, OTP length,
  mobile-number validation, bargain attempt limits).
- Decision tables for payment method combinations.
- State transition for login/OTP and bargaining states.
- Error guessing for negative login and network-slowness handling.

---

## 5. Test Data Management
- All test data centralized in **`data/test_data.xlsx`**:
  - `LoginData` sheet — positive/negative login cases.
  - `JourneyData` sheet — mobile, OTP, pincode, category, brand, price range,
    product, payment method.
- Secrets (SMTP, authorized numbers) kept in **`.env`**, never committed.
- OTP login uses an authorized staging test number; default OTP is the
  staging-provided value.

---

## 6. Environment & Tooling

| Area | Choice |
|------|--------|
| Language / Runner | Python 3.12 · pytest |
| Browser automation | Playwright (Chrome/Edge/Firefox) |
| Test data | openpyxl (Excel) |
| Config / secrets | PyYAML + python-dotenv |
| Accessibility | axe-playwright-python (axe-core) |
| Visual diff | Pillow |
| Reporting | pytest-html, Playwright video & trace, failure screenshots |
| Parallel / retry | pytest-xdist, pytest-rerunfailures |
| CI | GitHub Actions (browser × language matrix) |
| Mobile (future) | Appium placeholders (`android/`) |

**Environment notes:** Staging is intermittently slow — navigation uses
retries with extended timeouts; geolocation is auto-granted to bypass the
browser location prompt; login requires a single manual checkbox tick.

---

## 7. Roles & Responsibilities
- **Automation Engineer:** build/maintain page objects, tests, CI.
- **QA Analyst:** design cases, triage defects, own the bug report.
- **Reviewer/Lead:** approve strategy, sign off entry/exit criteria.

---

## 8. Entry & Exit Criteria

### 8.1 Entry Criteria
- Staging build deployed and reachable.
- Authorized test mobile number + OTP available.
- Test data workbook populated; framework dependencies installed.

### 8.2 Exit Criteria
- All in-scope E2E and functional tests executed.
- No open **Critical/High** functional defects (or documented with sign-off).
- Accessibility, performance, and visual results captured and reviewed.
- Bug report and test summary delivered.

---

## 9. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Staging slowness / timeouts | Flaky runs | Retry logic, 60s nav timeout, non-blocking NFR checks |
| OTP login requires authorized number | Blocks E2E | Data-driven number from Excel; manual checkbox only |
| Dynamic SPA locators change | Broken tests | Robust, verified locators; ID-based selectors |
| Bot-gated Terms checkbox | Automation stall | Human-in-the-loop pause for checkbox only |
| Third-party (Maps/geolocation) popups | Interruptions | Auto-grant permissions in browser context |

---

## 10. Deliverables
1. Automated test suite (E2E, login, non-functional).
2. Data-driven Excel test data (`test_data.xlsx`).
3. Test execution reports (HTML, video, traces, screenshots).
4. **Bug Report** (Excel defect log) from functional + site-audit findings.
5. This Test Strategy and a test summary.

---

## 11. Suspension & Resumption
- **Suspend** when: staging is down, a blocking defect prevents journey
  progression, or test data/credentials are unavailable.
- **Resume** when: the blocker is resolved and a smoke check of the login and
  home page passes.

---

## 12. Test Schedule (indicative)
1. Framework setup & smoke validation.
2. Functional + data-driven login coverage.
3. Full E2E journey execution (cross-browser).
4. Non-functional scans + site audit.
5. Defect triage, reporting, and sign-off.
