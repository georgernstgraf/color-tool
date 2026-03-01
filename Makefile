PYTHON ?= ./venv/bin/python
PYTEST ?= $(PYTHON) -m pytest

.PHONY: test test-contrast test-browser test-audit generate

## Run all tests (unit + browser)
test: test-contrast test-browser

## Unit/regression contrast checks against generated CSS
test-contrast:
	$(PYTEST) test_contrast.py -q

## Playwright browser-rendered WCAG audit (3 tests)
test-browser:
	$(PYTEST) test_browser_wcag.py -q

## Standalone CLI WCAG audit (not pytest, prints pass/fail)
test-audit:
	$(PYTHON) browser_wcag_tool.py

## Regenerate all theme CSS and overrides
generate:
	./generate_all.sh
