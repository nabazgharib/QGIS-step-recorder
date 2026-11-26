# Changelog

## 1.1.2
- Security scan (Bandit) fixes: every `except` block now logs instead of silently passing
  (new `log.py`; unexpected errors appear in *Log Messages > StepRecorder*).
- Renamed the i18n key `text_secret` to `text_masked` (false-positive "hardcoded password").
- Added `tests/test_security_patterns.py` so these patterns cannot come back.

## 1.1.1
- Fix: menu capture on QGIS 4 (Qt6) - `QAction.associatedWidgets` was removed.

## 1.1.0
- Added Kurdish Sorani (کوردی سۆرانی).
- Menu clicks are also captured through menu signals.
- Opening of menus, submenus and toolbar drop-down lists is recorded with a screenshot.

## 1.0.0
- First release.
