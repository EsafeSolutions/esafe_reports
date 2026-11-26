# Mobile app visual verification

Concept: [mobile-app-concept.png](mobile-app-concept.png), generated with the built-in
image generator. Render: [mobile-app-preview.png](mobile-app-preview.png),
[Alerts](mobile-app-alerts.png) and [Settings](mobile-app-settings.png).
The [generation prompt](mobile-app-prompt.txt) records the full design brief.

Browser/IAB was attempted first but could not reach the Windows loopback preview
(`ERR_CONNECTION_TIMED_OUT`). Local Chrome through Playwright provides the fallback.
The built production bundle is served with isolated, explicitly named API fixtures.
No production POS data is used in the screenshots.

## Comparison ledger

| Point | Concept | Implemented and inspected |
| --- | --- | --- |
| Layout | Brand header, overview, period switch, outlet, sales panel, trend, returns, bottom navigation | Same order and component hierarchy; no desktop header on the mobile route |
| Typography | Plus Jakarta Sans, navy headings, clear primary metric | Bundled brand font, distinct heading/value/label sizes, number alignment |
| Palette | White, navy, teal, pale teal and green logo | White surfaces, navy sales panel, teal controls and selected tabs; existing brand mark retained |
| Navigation | Overview, Reports, Alerts, Settings | Four fixed tabs with labels, selected state and 44px or larger principal touch controls |
| Alerts | Enable action, device switches, daily time, honest empty feed | Explicit permission action, working preferences/time/test/revoke controls, real delivery feed and empty state |
| Installation | App install panel and Android/iPhone directions | Install prompt capture, platform instructions and installed state; accurate iOS prerequisite |
| Responsive | Complete phone screens | 390×844 and 320×740 phone checks, plus a 1440×1000 desktop check; no horizontal overflow |

The concept was generated as a 1536×1024 board containing three phone-sized screens;
the rendered comparison uses three 390px phone captures at native browser scale.
Both the concept and latest captures are inspected with `view_image` before handoff.

Intentional copy/data differences: the actual current date replaces the concept's
illustrative date; the existing green B-star logo replaces its approximate B mark;
all figures come from the saved dashboard (fixtures only in QA); return signs are
preserved; native time formatting follows the device; installation guidance includes
real browser fallbacks and the iOS version requirement. A refresh control, device
time zone and test/revoke actions are included to complete the requested workflows.
Settings and alerts can scroll on shorter screens; the navigation remains available.

Above-the-fold copy was checked against the concept's brand, headings, period
labels, outlet selector, metric labels, primary actions and navigation labels.
Differences are limited to the functional/date/platform details above.

Core flow: open overview, change period and outlet, open reports, open alerts,
enable simulated push, save preferences, queue a test, revoke push, open installation
help, switch appearance/language, recover from offline navigation and handle loss
of reporting permission. Permission failure clears previously displayed figures.

Final checks on 26 November 2026: production build passed; 39 Python tests and
10 Node tests passed; the mobile Chrome suite and the existing POS browser suite
passed. The Python transport test encrypts with the real Web Push library and
decrypts the captured payload without sending a network message. The mobile suite
also checks that Overview controls clear the fixed navigation at 390×844. Layout
polish reduced chart/empty-state height to remove the overlap found during review.
Report rendering is loaded on demand so the initial mobile overview avoids the
larger chart-library download.

The concept and final three-screen preview were inspected together with
`view_image`, covering typography, palette, copy, icons, panel anatomy, navigation,
spacing, responsive layout and the platform-specific installation instructions.

The implementation is faithfully verified against the concept's visual system.
No material visual mismatches remain beyond the intentional differences listed above.
Actual Android/iPhone installation, background push arrival and live deployment
remain device/server checks; browser fixtures cannot establish those outcomes.
