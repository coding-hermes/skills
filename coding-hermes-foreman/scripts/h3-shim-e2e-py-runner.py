"""H3-shim E2E battery: Python SDK echo harness runner for port :9192.

Known-good content (proven tick #242, 2026-08-04). The sdk-python
src/h3_harness/examples/echo.py builds its app INSIDE __main__ (port 8000
hardcoded) — there is NO module-level `app`, so both
`uvicorn -m h3_harness.examples.echo:app` AND `from h3_harness.examples.echo
import app` fail. The canonical wrapper below constructs the FastAPI app
explicitly with create_router(EchoHarness()) + add_middleware.

Run (from ~/get-h3/sdk-python):
    PYTHONPATH=src .venv/bin/python /tmp/h3shim_tNNN_py_runner.py
"""

import uvicorn
from fastapi import FastAPI

from h3_harness import add_middleware, create_router
from h3_harness.examples.echo import EchoHarness

app = FastAPI()
app.include_router(create_router(EchoHarness()))
add_middleware(app)

if __name__ == '__main__':
    uvicorn.run(app, host='127.0.0.1', port=9192, log_level='warning')
