# Cross-cutting: i18n & localization

## A spec fails i18n rating (when the product serves >1 locale) if:
- The locale inventory and launch order is unstated.
- Strings: extraction mechanism, plural rules (CLDR), interpolation, and the
  untranslated-string fallback behavior.
- Data model: locale-aware fields (names, addresses, currency, measurement) use the
  right shapes (no single 'name' field; currency as minor units + code; TZ-aware datetimes).
- UI: layout tolerance for 40% text expansion (German), RTL mirroring for Arabic/Hebrew,
  font coverage for CJK.
- Sorting/collation per locale, and search normalization (accent folding rules, stated).

## Rating checks
- FAIL if any datetime is stored without timezone.
- FAIL if currency is a float.
- FAIL if RTL support is claimed without a mirroring statement per screen class.
