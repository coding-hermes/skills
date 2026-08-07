# Client Catalog File Upload

Quick HTTP upload server for receiving vendor catalogs, spec books, and price lists from clients. Single-file Python, tunneled through cloudflared.

## Why not /tmp?

Bane's rule: **"make sure that you dont keep files in /tmp and you find a proper place to store them — maybe in the downloads directory under <project>."**

Files go to the project's permanent directory (e.g. `data/catalogs/`), not `/tmp`. This survives restarts and is gitignored.

## Pattern

```bash
# 1. Create permanent storage (gitignored)
mkdir -p <project>/data/catalogs/
echo "/data/catalogs/" >> <project>/.gitignore

# 2. Start upload server (port 8095, has progress bar, multiple files)
# See scripts/upload-server.py for the full implementation.

# 3. Tunnel
cloudflared tunnel --url http://localhost:8095 &

# 4. Get URL from logs
grep "trycloudflare" /tmp/cf-catalogs.log | tail -1

# 5. After uploads: SHUT DOWN
pkill -f "cloudflared tunnel"
fuser -k 8095/tcp
```

## PDF Text Extraction

**pdftotext is the reliable fallback.** PyPDF2 may not be installed. The ledongthuc/pdf Go library panics on malformed real-world PDFs (offset errors). pdftotext always works:

```bash
pdftotext -l 5 catalog.pdf -  # first 5 pages to stdout
pdftotext -f 20 -l 25 spec.pdf -  # pages 20-25
```

## Real-world catalog challenges

- **Design/photo catalogs** (Scarabeo, FIMA): 99% images, pdftotext gets ~14 chars on cover pages. Product details (dimensions, codes, finishes) are in structured **price lists** — separate PDFs.
- **Construction spec books**: Hierarchical item codes (KE101, KB441), free-text descriptions, area quantities. Not table rows. Needs spec-book-aware parser.
- **Multi-language**: Croatian/Italian/German text in European construction docs. Material classification needs language-specific keyword dictionaries.
- **Large PDFs**: 42-89MB spec books and price lists. Sub-60s parsing target achieved with page-range extraction and streaming.

## Upload server features the client needs

- Progress bar (XHR upload.onprogress)
- Multiple files at once
- Shows uploaded files list
- Confirms with filenames and sizes
- Permanent storage (not /tmp)
