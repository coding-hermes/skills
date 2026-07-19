# Frontend Worker Prompt: Backend API Type Mapping

When spawning a frontend worker (Next.js, React, Vue, etc.) for a page that talks to a backend API, the foreman must **read the backend API code** and **embed exact types and endpoint paths** in the worker prompt. The worker should never have to discover the API contract — the foreman already did the discovery.

## Workflow

### 1. Read the backend API router

```bash
# Python/FastAPI:
read_file path/to/api/<router>.py

# Go/echo:
read_file internal/api/<handler>.go

# TypeScript/Next.js API routes:
read_file src/app/api/<endpoint>/route.ts
```

Extract:
- Every endpoint path (e.g. `GET /v1/connectors/providers`)
- Query parameters, path parameters, request body schemas
- Response model fields

### 2. Read the backend schemas/models

```bash
# Python Pydantic schemas — this is THE authoritative source:
read_file path/to/schemas/<resource>.py

# Go structs:
read_file internal/api/<types>.go
```

Extract exact field names, types, and which fields are nullable.

### 3. Convert to frontend naming conventions

Backend sends **snake_case** by default (FastAPI/Pydantic). Frontend types use **camelCase**. Convert every field:

| Backend (Python) | Frontend (TypeScript) |
|------------------|----------------------|
| `provider_id` | `providerId: string` |
| `display_name` | `displayName: string` |
| `o_auth_support` | `oAuthSupport: boolean` |
| `created_at` | `createdAt: string` |
| `has_next` | `hasNext: boolean` |
| `total_pages` | `totalPages: number` |

**If the backend has a custom JSON encoders that outputs camelCase** (check `app.py` or middleware for `camelize`), the frontend types match the API directly. But the authoritative source is still the Python schemas — read them, convert, verify.

### 4. Build the type map into the worker prompt

The worker prompt should contain:

```typescript
// Exact types matching the API response (camelCase)
interface ConnectorProviderResponse {
  id: string;
  displayName: string;
  categories: string[];
  oauthSupport: boolean;
  webhookSupport: boolean;
  docsUrl: string | null;
  createdAt: string;
}

// Pagination wrapper — match the actual response shape
interface ListResponse<T> {
  data: T[];
  pagination: {
    page: number;
    perPage: number;
    total: number;
    totalPages: number;
    hasNext: boolean;
    hasPrev: boolean;
  };
}
```

Include every endpoint the worker will need, with exact HTTP method and path:

```
GET  /v1/connectors/providers?page=&perPage= → ListResponse<ConnectorProviderResponse>
POST /v1/connectors/accounts { providerId, displayName? } → ConnectorAccountResponse
```

### 5. Include patterns from existing frontend pages

Read one or two existing pages to understand the conventions:

```typescript
// From existing datapoints page — this is the pattern
const res = await api.get<DatapointListResponse>(buildPath());
```

Then tell the worker: "Follow this exact pattern. Use `api.get<T>()`, `api.post<T>()`, etc."

## Why This Matters

Without this type-mapping step, the worker will:
- Guess API field names (wrong if backend uses snake_case)
- Waste iterations reading backend code to discover the contract
- Produce TypeScript interfaces that don't match the actual API response
- Generate broken data flows that fail at runtime

With this step, the worker produces correct code on the first pass because every type and endpoint path is embedded in the prompt before the worker starts coding.

## Proven

DexDat Core FRONTEND-8 (2026-07-15) — foreman read `src/api/connectors.py`, `src/schemas/connector.py`, and `frontend/src/app/datapoints/page.tsx`, then built a worker prompt with exact ConnectorProviderResponse and ConnectorAccountResponse types plus all 5 endpoint paths. Worker (glm-5.2 @ zai-glm) completed 1713 lines across 2 files in one pass with zero type mismatches. Build clean (22 routes), guard PASS.
