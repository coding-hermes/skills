# Cross-cutting: accessibility

## A spec fails a11y rating (for any UI surface) if:
- The target standard is unstated (WCAG 2.2 AA is the sane default; name it).
- Interactive elements: every control's keyboard path and focus order, visible focus.
- Semantics: roles/labels for every custom component; the screen-reader script for
  the canonical journey.
- Media: captions, transcripts, contrast ratios (4.5:1 text, 3:1 UI) with the
  palette checked, not assumed.
- Error handling announced to AT (aria-live regions), never color-only status.
- The verification method: automated checks (axe) + manual AT pass, and who does it.

## Rating checks
- FAIL if any flow requires a pointer/precision gesture exclusively.
- FAIL if focus management in modals/route-changes is unspecified (the classic trap).
- FAIL if contrast is claimed without the palette check.
