#!/usr/bin/env python3

import argparse
import re
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import sync_playwright


def _start_static_server(root_dir: Path):
    class QuietHandler(SimpleHTTPRequestHandler):
        def log_message(self, format, *args):
            return

    handler = partial(QuietHandler, directory=str(root_dir))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def _theme_label(option_label: str) -> str:
    m = re.search(r"\(([^)]+)\)", option_label)
    if m:
        return m.group(1).strip()
    return option_label.strip()


def _mode_label(mode: str) -> str:
    return "Day" if mode == "light" else "Night"


def run(url: str, verbose: bool) -> list[str]:
    audit_script = """
    ({ normalTextMin, largeTextMin, verbose }) => {
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

      function classify(el) {
        const cls = (el.className || '').toString().toLowerCase();
        const tags = [];
        if (cls.includes('btn')) tags.push('Button');
        if (cls.includes('btn-outline-')) tags.push('Outline');
        if (cls.includes('badge')) tags.push('Badge');
        if (cls.includes('alert')) tags.push('Alert');
        if (cls.includes('nav-link')) tags.push('Nav');
        if (cls.includes('page-link')) tags.push('Pagination');
        if (cls.includes('card')) tags.push('Card');
        for (const tone of ['primary', 'secondary', 'success', 'info', 'warning', 'danger', 'light', 'dark']) {
          if (cls.includes(tone)) {
            tags.push(tone.charAt(0).toUpperCase() + tone.slice(1));
            break;
          }
        }
        if (tags.length === 0) tags.push(el.tagName.toLowerCase());
        return [...new Set(tags)];
      }

      const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
      const seen = new Set();
      const checked = [];
      const failures = [];

      while (walker.nextNode()) {
        const node = walker.currentNode;
        if (!node.textContent || !node.textContent.trim()) continue;
        const el = node.parentElement;
        if (!el || !isVisible(el)) continue;

        const key = `${el.tagName}|${el.className}|${node.textContent.trim()}`;
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

        if (verbose) {
          checked.push({
            text: node.textContent.trim().replace(/\\s+/g, ' ').slice(0, 80),
            tags: classify(el),
            ratio: Number(ratio.toFixed(2))
          });
        }

        if (ratio < threshold) {
          failures.push({
            text: node.textContent.trim().replace(/\\s+/g, ' ').slice(0, 80),
            ratio: Number(ratio.toFixed(2)),
            required: threshold,
            tags: classify(el)
          });
        }
      }

      failures.sort((a, b) => a.ratio - b.ratio);
      return { failures, checked };
    }
    """

    scenarios = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="chromium", headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 2200})
        page.goto(url, wait_until="networkidle")
        page.evaluate(
            """
            () => {
              const motion = document.createElement('style');
              motion.innerHTML = '* { transition: none !important; animation: none !important; }';
              document.head.appendChild(motion);
              const bg = document.createElement('style');
              bg.innerHTML = 'body::before { background-image: none !important; }';
              document.head.appendChild(bg);
              if (typeof updateTheme === 'function') updateTheme();
            }
            """
        )

        options = page.eval_on_selector_all(
            "#themeSelect option",
            "opts => opts.map(o => ({ value: o.value, label: o.textContent.trim() }))",
        )

        for option in options:
            page.select_option("#themeSelect", option["value"])
            page.wait_for_function(
                "theme => document.getElementById('themeStylesheet').getAttribute('href').includes(`${theme}-theme.css`)",
                arg=option["value"],
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

                result = page.evaluate(
                    audit_script,
                    {"normalTextMin": 7.0, "largeTextMin": 4.5, "verbose": verbose},
                )

                theme_name = _theme_label(option["label"])
                mode_name = _mode_label(mode)

                if verbose:
                    for checked in result["checked"]:
                        tags = ", ".join(checked["tags"])
                        print(f'{theme_name}, {mode_name}, "{checked["text"]}", {tags}')

                if result["failures"]:
                    sample = "; ".join(
                        f"{f['ratio']}<{f['required']} ('{f['text']}') [{', '.join(f['tags'])}]"
                        for f in result["failures"][:5]
                    )
                    scenarios.append(f"{theme_name}/{mode_name}: {sample}")

        browser.close()

    return scenarios


def main():
    parser = argparse.ArgumentParser(description="Run browser WCAG text-contrast audit")
    parser.add_argument("-v", "--verbose", action="store_true", help="Log every checked text element")
    parser.add_argument("--url", help="Use an existing preview URL instead of local index.html")
    args = parser.parse_args()

    server = None
    thread = None
    url = args.url

    try:
        if not url:
            repo_root = Path(__file__).resolve().parent
            server, thread = _start_static_server(repo_root)
            url = f"http://127.0.0.1:{server.server_address[1]}/index.html"

        failures = run(url, args.verbose)
        if failures:
            print("\nRendered WCAG contrast failures detected:")
            for f in failures:
                print(f"- {f}")
            raise SystemExit(1)

        print("Rendered WCAG contrast audit passed.")
    finally:
        if server is not None:
            server.shutdown()
            server.server_close()
        if thread is not None:
            thread.join(timeout=3)


if __name__ == "__main__":
    main()
