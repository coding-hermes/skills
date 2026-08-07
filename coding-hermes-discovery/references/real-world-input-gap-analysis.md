# Real-World Input Gap Analysis

> Proven: <project> 2026-07-23 — 6 client PDFs tested, 0 products found, 10 gaps discovered.

## When to use this sweep

Run when:
- The project processes external documents (PDFs, spreadsheets, CAD files, images)
- All synthetic tests pass but no one has tested with actual client files
- The board is empty and the discovery sweep found nothing
- Bane or a client provides real-world test data

## The problem

Synthetic tests pass because they test what the parser was BUILT for. But real-world documents don't match the parser's assumptions:

| Assumption | Reality |
|---|---|
| Product catalogs have table rows (name, SKU, price) | Construction spec books have hierarchical item codes (KE101) with free-text descriptions |
| Catalog + prices are in one PDF | Catalog and price list are SEPARATE documents (FIMA 23MB catalog + 89MB price list) |
| Product details are in text | Design catalogs are 99% images — pdftotext gets 14 chars on 2 pages |
| Documents are in English | Croatian spec books, Italian catalogs with Russian translations |
| Area quantities are pre-calculated | Spec says "1,151m² of KE101 tiles" — must compute tiles/m² from product dimensions |

## Method

### Step 1: Gather real files
Get actual client documents. Not synthetic test fixtures. Real PDFs from real projects. The <project> test set:
- Construction spec book (42MB, 28 trade categories)
- 2 vendor product catalogs (23MB FIMA faucets, 11MB Scarabeo ceramics)
- 2 vendor price lists (89MB FIMA, 72MB Scarabeo)
- 1 example output format (66KB BOQ)

### Step 2: Run pdftotext on each file
```bash
pdftotext -l <pages> <file> - | head -100
```
Note: text extraction quality, languages present, whether content is text or images.

### Step 3: Run the project's parser against each file
Write a real test (not a synthetic one):
```go
func TestRealCatalogs(t *testing.T) {
    data, _ := os.ReadFile("/path/to/real-catalog.pdf")
    result, _ := parser.Parse(ctx, data, "catalog.pdf")
    t.Logf("Products found: %d", len(result.Products))
    // Don't assert — just log. The gap is the finding.
}
```

### Step 4: Catalog every gap
For each file, for each pipeline step, record:
- Expected output vs actual output
- Root cause (wrong document model, missing feature, language barrier)
- Severity: Critical (pipeline blocker), Important (quality/accuracy), Minor (performance)

### Step 5: Categorize by severity

| Severity | Definition | Examples |
|---|---|---|
| Critical | Pipeline cannot process real data at all. Returns 0 results. | Spec book parser, catalog-price cross-reference, OCR for image catalogs, missing end-to-end pipeline |
| Important | Processes data but with wrong results. | Multi-language classification fails, area→quantity not calculated, fuzzy matching doesn't find products, wrong output format |
| Minor | Works but untested at scale or with edge cases. | Large PDF timeout, incremental parsing not implemented |

### Step 6: Output the gap matrix
Produce a table: Gap ID, capability, current state, gap description, severity, recommended implementation order. File it as `gap-analysis.html` in the project root. Add all gaps to `.coding-hermes/tasks.md` with Load directives.

## Why this works when other sweeps don't

| Sweep | What it catches | What it misses |
|---|---|---|
| 1.5a Build | Compile errors | Parser compiles but returns 0 products |
| 1.5b Live endpoints | 500s, stubs | Endpoint returns 200 with empty array |
| 1.5c Spec alignment | Missing TODOs | Spec matches code but code doesn't match real documents |
| 1.5h E2E verification | Service health, CLI | Input pipeline producing no output from real data |
| **1.5i Real-world input test** | **Architectural input model mismatch** | (this is the gap this sweep fills) |

## Concrete <project> results

After running this sweep against 6 real client PDFs:
- **0 products found** across all 6 files
- **4 critical gaps**: spec book parser, catalog-price cross-reference, image catalog OCR, end-to-end pipeline
- **5 important gaps**: multi-language taxonomy, area-to-quantity, fuzzy matching, BOQ format, price tiers
- **1 minor gap**: large PDF performance (untested at 42-89MB)

Without this sweep, the foreman would have reported the project complete (15/15 tests pass, 41 routes wired, 0 stubs) while the system was fundamentally incapable of processing actual client documents.
