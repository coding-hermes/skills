#!/usr/bin/env python3
"""Quick HTTP upload server for client catalogs and vendor documents.

Usage: python3 upload-server.py [port] [upload_dir]
Default: port=8095, dir=./data/catalogs/

Features:
- Progress bar (XHR upload progress)
- Multiple file support
- File list shown on page
- Permanent storage (project directory, gitignored)
- Dark-themed UI matching <project> design
"""
import sys
import http.server
import cgi
import html
import json
from pathlib import Path

# Config — override via CLI args
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8095
UPLOAD_DIR = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("data/catalogs")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class Handler(http.server.BaseHTTPRequestHandler):
    """Upload handler with progress bar UI."""

    def do_GET(self):
        if self.path != "/":
            self.send_error(404)
            return
        rows = ""
        files = sorted(UPLOAD_DIR.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True)
        for f in files:
            s = f.stat().st_size
            if s > 1e6:
                size = f"{s / 1e6:.1f}MB"
            elif s > 1e3:
                size = f"{s / 1e3:.0f}KB"
            else:
                size = f"{s}B"
            rows += (
                f'<div style="display:flex;justify-content:space-between;padding:6px 10px;'
                f'border-bottom:1px solid #30363d;font-size:.85rem">'
                f'<span>{html.escape(f.name)}</span>'
                f'<span style="color:#8b949e">{size}</span></div>'
            )
        n = len(files)
        page = (
            '<!doctype html><meta charset=utf-8>'
            '<meta name=viewport content="width=device-width,initial-scale=1">'
            "<title>Upload — <project></title>"
            "<style>"
            "body{font-family:system-ui;max-width:640px;margin:40px auto;padding:16px;"
            "background:#0d1117;color:#e6edf3}"
            "h1{color:#58a6ff;font-size:1.3rem}"
            "h3{font-size:.9rem;margin:20px 0 8px}"
            "form{background:#161b22;padding:20px;border:1px solid #30363d;border-radius:8px}"
            "input[type=file]{width:100%;margin:8px 0;color:#e6edf3;padding:8px}"
            "input[type=submit]{background:#238636;color:#fff;border:none;padding:12px 28px;"
            "border-radius:6px;font-size:.9rem;cursor:pointer}"
            "#status{margin:12px 0;padding:10px;border-radius:6px;display:none;font-size:.85rem}"
            "#status.ok{background:#1b3a2a;color:#3fb950;display:block}"
            "#status.err{background:#3a1b1b;color:#f85149;display:block}"
            "#status.load{background:#1b2e3a;color:#58a6ff;display:block}"
            "progress{width:100%;height:8px;border-radius:4px;margin:8px 0}"
            "progress::-webkit-progress-bar{background:#30363d;border-radius:4px}"
            "progress::-webkit-progress-value{background:#238636;border-radius:4px}"
            "</style>"
            f"<h1>📤 <project> — Catalog Upload</h1>"
            f'<p style="color:#8b949e">Saved to {UPLOAD_DIR} · {n} files</p>'
            '<form id=f enctype=multipart/form-data>'
            '<input type=file name=files multiple id=fi>'
            '<progress id=progress value=0 max=100></progress>'
            '<div id=status></div>'
            '<input type=submit value=Upload id=submitBtn>'
            "</form><h3>Uploaded Catalogs</h3>" + rows
            + "<script>"
            "const f=document.getElementById('f'),s=document.getElementById('status'),"
            "p=document.getElementById('progress'),fi=document.getElementById('fi'),"
            "b=document.getElementById('submitBtn');"
            "f.onsubmit=async e=>{e.preventDefault();"
            "if(!fi.files.length){s.className='err';s.textContent='Select files first';return}"
            "s.className='load';s.textContent='Uploading...';b.disabled=true;p.value=0;"
            "let fd=new FormData();for(let x of fi.files)fd.append('files',x);"
            "try{let x=new XMLHttpRequest();"
            "x.upload.onprogress=ev=>{if(ev.lengthComputable)p.value=100*ev.loaded/ev.total};"
            "await new Promise((r,j)=>{x.open('POST','/upload');"
            "x.onload=()=>x.status===200?r():j(x.status);x.onerror=()=>j('network');x.send(fd)});"
            "let d=JSON.parse(x.responseText);"
            "s.className='ok';s.textContent='✅ '+d.files.length+' file(s) saved: '"
            "+d.files.map(f=>f.name+' ('+(f.size>1e6?(f.size/1e6).toFixed(1)+'MB':"
            "(f.size/1e3).toFixed(0)+'KB')+')').join(', ');"
            "setTimeout(()=>location.reload(),1500)}"
            "catch(e){s.className='err';s.textContent='Failed: '+e;b.disabled=false}};</script>"
        )
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(page.encode())

    def do_POST(self):
        if self.path != "/upload":
            self.send_error(404)
            return
        form = cgi.FieldStorage(
            fp=self.rfile, headers=self.headers, environ={"REQUEST_METHOD": "POST"}
        )
        results = []
        for field in form.list:
            if field.filename:
                data = field.file.read()
                (UPLOAD_DIR / field.filename).write_bytes(data)
                results.append({"name": field.filename, "size": len(data)})
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"ok": True, "files": results}).encode())


if __name__ == "__main__":
    print(f"Upload server on :{PORT} → {UPLOAD_DIR}")
    http.server.HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
