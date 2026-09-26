# Verify the report render without eyes

For the HTML report's finish pass. No vision needed; all mechanical.

## 1. Markup

Parse with HTMLParser using a void-element set (meta br link img input
hr source track wbr col base area embed param) — a naive checker
false-flags every `<hr>` as unclosed.

## 2. Layout + fonts + contrast (Playwright, file:// URL)

```python
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch()
    for w in (1280, 390):
        pg = b.new_page(viewport={'width': w, 'height': 900})
        pg.goto('file:///path/report.html')
        pg.wait_for_timeout(500)
        print(w, pg.evaluate("""() => ({
          overflow: document.documentElement.scrollWidth
            - document.documentElement.clientWidth,
          chakra: document.fonts.check('700 40px "Your Face"'),
        })"""))
        pg.close()
    b.close()
```

Contrast math (WCAG AA: body ≥ 4.5:1, large ≥ 3:1) — compute in-page:
relative luminance per channel `v<=.03928 ? v/12.92 : ((v+.055)/1.055)^2.4`,
ratio `(L1+.05)/(L2+.05)`. Check every text/background pair the design
introduces, including captions, table cells, and inverted panels —
secondary text is where designs fail, not body text.

`document.fonts.check()` only proves a face that page content actually
requests — an embedded-but-unused weight reads False. Either use every
embedded weight in the design or drop it.

## 3. Screenshots

Prefer headless chrome directly — it never hangs:

```bash
google-chrome --headless --disable-gpu --no-sandbox --hide-scrollbars \
  --window-size=1280,900 --screenshot=/tmp/desk.png file:///path/report.html
google-chrome --headless --disable-gpu --no-sandbox --hide-scrollbars \
  --window-size=390,844 --screenshot=/tmp/mob.png file:///path/report.html
```

Fall back to these when the harnessed browser's full-page capture times
out (typical cause: infinite CSS animation — the compositor never
settles). Sticky nav with negative margins is the classic mystery
horizontal overflow: the nav is body-level, so keep its margins at zero.
