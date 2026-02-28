import os
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest


def _start_static_server(root_dir: Path):
    class QuietHandler(SimpleHTTPRequestHandler):
        def log_message(self, format, *args):
            return

    handler = partial(QuietHandler, directory=str(root_dir))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


@pytest.fixture(scope="module")
def preview_url():
    repo_root = Path(__file__).resolve().parent
    server, thread = _start_static_server(repo_root)
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}/index.html"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def test_rendered_wcag_contrast(preview_url):
    pytest.importorskip("playwright.sync_api")
    from playwright.sync_api import Error, sync_playwright

    normal_text_min = float(os.environ.get("WCAG_AAA_NORMAL_MIN", "7.0"))
    large_text_min = float(os.environ.get("WCAG_AAA_LARGE_MIN", "4.5"))

    audit_script = """
    ({ normalTextMin, largeTextMin }) => {
      function parseColor(raw) {
        if (!raw || raw === 'transparent') return { r: 0, g: 0, b: 0, a: 0 };
        const m = raw.match(/rgba?\\(([^)]+)\\)/i);
        if (!m) return { r: 0, g: 0, b: 0, a: 0 };
        const p = m[1].split(',').map(x => x.trim());
        return {
          r: Number(p[0]),
          g: Number(p[1]),
          b: Number(p[2]),
          a: p[3] === undefined ? 1 : Number(p[3])
        };
      }

      function blend(top, bottom) {
        const a = top.a + bottom.a * (1 - top.a);
        if (a <= 0) return { r: 0, g: 0, b: 0, a: 0 };
        return {
          r: (top.r * top.a + bottom.r * bottom.a * (1 - top.a)) / a,
          g: (top.g * top.a + bottom.g * bottom.a * (1 - top.a)) / a,
          b: (top.b * top.a + bottom.b * bottom.a * (1 - top.a)) / a,
          a
        };
      }

      function srgb(c) {
        const v = c / 255;
        return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
      }

      function luminance(color) {
        return 0.2126 * srgb(color.r) + 0.7152 * srgb(color.g) + 0.0722 * srgb(color.b);
      }

      function contrastRatio(fg, bg) {
        const l1 = luminance(fg);
        const l2 = luminance(bg);
        const light = Math.max(l1, l2);
        const dark = Math.min(l1, l2);
        return (light + 0.05) / (dark + 0.05);
      }

      function isVisible(el) {
        const style = getComputedStyle(el);
        if (style.visibility === 'hidden' || style.display === 'none') return false;
        const rect = el.getBoundingClientRect();
        return rect.width > 0 && rect.height > 0;
      }

      function selector(el) {
        if (el.id) return '#' + el.id;
        const parts = [];
        let node = el;
        while (node && node.nodeType === 1 && parts.length < 5) {
          const cls = (node.className || '').toString().trim().split(/\\s+/).filter(Boolean).slice(0, 2).join('.');
          let part = node.tagName.toLowerCase();
          if (cls) part += '.' + cls;
          const parent = node.parentElement;
          if (parent) {
            const siblings = Array.from(parent.children).filter(c => c.tagName === node.tagName);
            if (siblings.length > 1) part += `:nth-of-type(${siblings.indexOf(node) + 1})`;
          }
          parts.unshift(part);
          node = parent;
        }
        return parts.join(' > ');
      }

      function resolveBackground(el) {
        let result = { r: 255, g: 255, b: 255, a: 1 };
        let node = el;
        const layers = [];
        while (node) {
          const c = parseColor(getComputedStyle(node).backgroundColor);
          if (c.a > 0) layers.push(c);
          node = node.parentElement;
        }
        for (let i = layers.length - 1; i >= 0; i -= 1) {
          result = blend(layers[i], result);
        }
        return result;
      }

      function textNodes() {
        const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
        const nodes = [];
        while (walker.nextNode()) {
          const n = walker.currentNode;
          if (!n.textContent || !n.textContent.trim()) continue;
          if (!n.parentElement) continue;
          nodes.push(n);
        }
        return nodes;
      }

      const failures = [];
      const seen = new Set();

      for (const node of textNodes()) {
        const el = node.parentElement;
        if (!el || !isVisible(el)) continue;
        const key = selector(el);
        if (seen.has(key)) continue;
        seen.add(key);

        const style = getComputedStyle(el);
        const fg = parseColor(style.color);
        const bg = resolveBackground(el);
        const ratio = contrastRatio(fg, bg);
        const fontSize = Number(style.fontSize.replace('px', ''));
        const fontWeight = Number(style.fontWeight) || 400;
        const isLarge = fontSize >= 24 || (fontSize >= 18.66 && fontWeight >= 700);
        const threshold = isLarge ? largeTextMin : normalTextMin;

        if (ratio < threshold) {
          failures.push({
            selector: key,
            text: node.textContent.trim().replace(/\\s+/g, ' ').slice(0, 80),
            ratio: Number(ratio.toFixed(2)),
            required: threshold
          });
        }
      }

      failures.sort((a, b) => a.ratio - b.ratio);
      return failures.slice(0, 20);
    }
    """

    scenarios = []

    def iterate_theme_modes(page):
        themes = page.eval_on_selector_all("#themeSelect option", "opts => opts.map(o => o.value)")
        for theme in themes:
            page.select_option("#themeSelect", theme)
            page.wait_for_function(
                "theme => document.getElementById('themeStylesheet').getAttribute('href').includes(`${theme}-theme.css`)",
                arg=theme,
            )

            for mode in ("light", "dark"):
                page.evaluate(
                    """
                    (mode) => {
                      document.documentElement.setAttribute('data-bs-theme', mode);
                      if (typeof updateTheme === 'function') updateTheme();
                    }
                    """,
                    mode,
                )
                page.wait_for_function(
                    "mode => document.documentElement.getAttribute('data-bs-theme') === mode",
                    arg=mode,
                )
                page.wait_for_timeout(180)
                yield theme, mode

    with sync_playwright() as pw:
        browser = None
        try:
            browser = pw.chromium.launch(channel="chromium", headless=True)
        except Error:
            try:
                browser = pw.chromium.launch(headless=True)
            except Error as exc:
                pytest.skip(f"Chromium is not available for Playwright: {exc}")

        if browser is None:
            pytest.skip("Chromium is not available for Playwright")
        assert browser is not None

        page = browser.new_page(viewport={"width": 1440, "height": 2200})
        page.goto(preview_url, wait_until="networkidle")
        page.evaluate(
            """
            () => {
              const opacityRange = document.getElementById('opacityRange');
              if (opacityRange) {
                opacityRange.value = opacityRange.max || '1';
                opacityRange.dispatchEvent(new Event('input', { bubbles: true }));
              }

              const motion = document.createElement('style');
              motion.id = 'test-disable-motion';
              motion.innerHTML = '* { transition: none !important; animation: none !important; }';
              document.head.appendChild(motion);

              const style = document.createElement('style');
              style.id = 'test-no-bg-image';
              style.innerHTML = 'body::before { background-image: none !important; }';
              document.head.appendChild(style);
              if (typeof updateTheme === 'function') updateTheme();
            }
            """
        )

        for theme, mode in iterate_theme_modes(page):
            failures = page.evaluate(
                audit_script,
                {"normalTextMin": normal_text_min, "largeTextMin": large_text_min},
            )
            if failures:
                sample = "; ".join(
                    f"{item['ratio']}<{item['required']} at {item['selector']} ('{item['text']}')"
                    for item in failures[:5]
                )
                scenarios.append(f"{theme}/{mode}: {sample}")

        browser.close()

    assert not scenarios, "Rendered WCAG contrast failures detected:\n" + "\n".join(scenarios)


def test_can_click_through_theme_and_mode_controls(preview_url):
    pytest.importorskip("playwright.sync_api")
    from playwright.sync_api import Error, sync_playwright

    with sync_playwright() as pw:
        try:
            browser = pw.chromium.launch(channel="chromium", headless=True)
        except Error:
            browser = pw.chromium.launch(headless=True)

        page = browser.new_page(viewport={"width": 1440, "height": 2200})
        page.goto(preview_url, wait_until="networkidle")
        page.evaluate(
            """
            () => {
              const opacityRange = document.getElementById('opacityRange');
              if (opacityRange) {
                opacityRange.value = opacityRange.max || '1';
                opacityRange.dispatchEvent(new Event('input', { bubbles: true }));
              }
            }
            """
        )

        themes = page.eval_on_selector_all("#themeSelect option", "opts => opts.map(o => o.value)")
        assert themes, "No themes found in #themeSelect"

        visited = 0
        for theme in themes:
            page.select_option("#themeSelect", theme)
            page.wait_for_function(
                "theme => document.getElementById('themeStylesheet').getAttribute('href').includes(`${theme}-theme.css`)",
                arg=theme,
            )

            for mode in ("dark", "light"):
                page.click("#themeToggle")
                page.wait_for_function(
                    "mode => document.documentElement.getAttribute('data-bs-theme') === mode",
                    arg=mode,
                )
                visited += 1

        browser.close()

    assert visited == len(themes) * 2


def test_active_pill_is_contrast_compliant(preview_url):
    pytest.importorskip("playwright.sync_api")
    from playwright.sync_api import Error, sync_playwright

    threshold = float(os.environ.get("WCAG_AAA_NORMAL_MIN", "7.0"))
    issues = []

    contrast_for_selector_script = """
    (selector) => {
      function parseColor(raw) {
        if (!raw || raw === 'transparent') return { r: 0, g: 0, b: 0, a: 0 };
        const m = raw.match(/rgba?\\(([^)]+)\\)/i);
        if (!m) return { r: 0, g: 0, b: 0, a: 0 };
        const p = m[1].split(',').map(x => x.trim());
        return {
          r: Number(p[0]),
          g: Number(p[1]),
          b: Number(p[2]),
          a: p[3] === undefined ? 1 : Number(p[3])
        };
      }

      function blend(top, bottom) {
        const a = top.a + bottom.a * (1 - top.a);
        if (a <= 0) return { r: 0, g: 0, b: 0, a: 0 };
        return {
          r: (top.r * top.a + bottom.r * bottom.a * (1 - top.a)) / a,
          g: (top.g * top.a + bottom.g * bottom.a * (1 - top.a)) / a,
          b: (top.b * top.a + bottom.b * bottom.a * (1 - top.a)) / a,
          a
        };
      }

      function srgb(c) {
        const v = c / 255;
        return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
      }

      function luminance(color) {
        return 0.2126 * srgb(color.r) + 0.7152 * srgb(color.g) + 0.0722 * srgb(color.b);
      }

      function contrastRatio(fg, bg) {
        const l1 = luminance(fg);
        const l2 = luminance(bg);
        const light = Math.max(l1, l2);
        const dark = Math.min(l1, l2);
        return (light + 0.05) / (dark + 0.05);
      }

      function resolveBackground(el) {
        let result = { r: 255, g: 255, b: 255, a: 1 };
        let node = el;
        const layers = [];
        while (node) {
          const c = parseColor(getComputedStyle(node).backgroundColor);
          if (c.a > 0) layers.push(c);
          node = node.parentElement;
        }
        for (let i = layers.length - 1; i >= 0; i -= 1) {
          result = blend(layers[i], result);
        }
        return result;
      }

      const el = document.querySelector(selector);
      if (!el) return null;
      const style = getComputedStyle(el);
      const fg = parseColor(style.color);
      const bg = resolveBackground(el);
      return Number(contrastRatio(fg, bg).toFixed(2));
    }
    """

    with sync_playwright() as pw:
        browser = None
        try:
            browser = pw.chromium.launch(channel="chromium", headless=True)
        except Error:
            try:
                browser = pw.chromium.launch(headless=True)
            except Error as exc:
                pytest.skip(f"Chromium is not available for Playwright: {exc}")

        if browser is None:
            pytest.skip("Chromium is not available for Playwright")

        page = browser.new_page(viewport={"width": 1440, "height": 2200})
        page.goto(preview_url, wait_until="networkidle")
        page.evaluate(
            """
            () => {
              const opacityRange = document.getElementById('opacityRange');
              if (opacityRange) {
                opacityRange.value = opacityRange.max || '1';
                opacityRange.dispatchEvent(new Event('input', { bubbles: true }));
              }
            }
            """
        )
        page.evaluate(
            """
            () => {
              const motion = document.createElement('style');
              motion.id = 'test-disable-motion';
              motion.innerHTML = '* { transition: none !important; animation: none !important; }';
              document.head.appendChild(motion);
            }
            """
        )

        themes = page.eval_on_selector_all("#themeSelect option", "opts => opts.map(o => o.value)")
        for theme in themes:
            page.select_option("#themeSelect", theme)
            page.wait_for_function(
                "theme => document.getElementById('themeStylesheet').getAttribute('href').includes(`${theme}-theme.css`)",
                arg=theme,
            )

            for mode in ("light", "dark"):
                page.evaluate(
                    """
                    (mode) => {
                      document.documentElement.setAttribute('data-bs-theme', mode);
                      if (typeof updateTheme === 'function') updateTheme();
                    }
                    """,
                    mode,
                )
                page.wait_for_function(
                    "mode => document.documentElement.getAttribute('data-bs-theme') === mode",
                    arg=mode,
                )
                page.wait_for_timeout(180)
                ratio = page.evaluate(contrast_for_selector_script, "#pills-home-tab")
                if ratio is None:
                    issues.append(f"{theme}/{mode}: #pills-home-tab not found")
                elif ratio < threshold:
                    issues.append(f"{theme}/{mode}: contrast {ratio} < {threshold}")

        browser.close()

    assert not issues, "Active pill contrast failures:\n" + "\n".join(issues)
