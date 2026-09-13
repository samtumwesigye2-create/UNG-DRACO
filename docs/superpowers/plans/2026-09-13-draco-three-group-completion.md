# UNG-DRACO Three-Group Completion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish the remaining UNG-DRACO implementation in three verified groups and only mark the system operational after a complete end-to-end acceptance pass.

**Architecture:** Preserve the existing FastAPI + PostgreSQL foundation and authoritative SQLAlchemy models. Group 1 merges secure ingestion with JANUS identity/RBAC/audit, Group 2 adds deterministic correlation/tracking/fusion/alerts as focused services, and Group 3 exposes operational read APIs, hardens CI/runtime configuration, and runs a full synthetic acceptance chain with evidence persisted to PostgreSQL.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, PostgreSQL 16, Alembic, Pydantic 2, PyJWT, pytest, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-09-13-draco-three-group-completion-design.md`

## Global Constraints

- Keep `/health` public.
- All non-health operational endpoints require JANUS authentication.
- Protected source identity requires `draco_source_admin` or `draco_admin`.
- Analyst read operations require `draco_analyst` or `draco_admin`.
- Collector ingestion requires `draco_collector` or `draco_admin`.
- Every mutating operational action writes an `AuditEvent` in the same transaction.
- CI must run `alembic upgrade head` against PostgreSQL 16 before `pytest`.
- Final operational status requires one passing end-to-end synthetic acceptance test that proves ingestion, correlation, track creation/update, alerting, reporting, API retrieval, and audit traceability.

---

### Task 1: Merge secure ingestion and JANUS/RBAC/audit

**Files:**
- Modify: `app/main.py`
- Create: `app/security/__init__.py`
- Create: `app/security/auth.py`
- Create: `app/security/rbac.py`
- Create: `app/security/audit.py`
- Modify: `requirements.txt`
- Modify: `.github/workflows/ci.yml`
- Test: `tests/integration/test_observation_api.py`
- Test: `tests/integration/test_source_watch_api.py`
- Test: `tests/integration/test_auth.py`
- Test: `tests/unit/test_rbac.py`

**Interfaces:**
- Consumes: `CollectionItem`, `Source`, `Watch`, `AuditEvent`, `get_db()`.
- Produces: `Principal(subject: str, roles: set[str])`, `get_current_principal()`, `require_roles(*allowed_roles)`, `append_audit_event(...)`, authenticated `/api/draco/v1/observations`, `/api/draco/v1/sources`, `/api/draco/v1/watches`.

- [ ] **Step 1: Preserve PR #5 ingestion tests and make them authentication-aware**

```python
app.dependency_overrides[get_current_principal] = lambda: Principal(
    subject="collector-acceptance",
    roles={"draco_collector", "draco_source_admin", "draco_admin"},
)
```

Add the override before POST/GET calls and clear it after each test so existing persistence assertions remain unchanged.

- [ ] **Step 2: Run ingestion tests and verify the unmerged security path fails**

Run: `python -m pytest tests/integration/test_observation_api.py tests/integration/test_source_watch_api.py -v`

Expected: FAIL until security dependencies are integrated with ingestion.

- [ ] **Step 3: Integrate JANUS auth and role gates into `app/main.py`**

Use:

```python
collector = Depends(require_roles("draco_collector", "draco_admin"))
source_admin = Depends(require_roles("draco_source_admin", "draco_admin"))
analyst = Depends(require_roles("draco_analyst", "draco_admin"))
```

Apply collector/admin to observation creation, source-admin/admin to source create/list, analyst/admin to watch list, and analyst/admin to the security probe. Keep `/health` public.

- [ ] **Step 4: Replace local `_audit` helper with `append_audit_event`**

For each mutation call:

```python
append_audit_event(
    db,
    actor_id=principal.subject,
    action="observation.created",
    resource_type="collection_item",
    resource_id=str(observation.id),
    correlation_id=str(uuid4()),
    result="success",
    request_metadata={"event": "draco.observation.created"},
)
```

Commit the business row and audit row in the same transaction.

- [ ] **Step 5: Run Group 1 tests**

Run: `python -m pytest tests/unit/test_rbac.py tests/integration/test_auth.py tests/integration/test_observation_api.py tests/integration/test_source_watch_api.py -v`

Expected: PASS.

- [ ] **Step 6: Run full CI suite**

Run: `alembic upgrade head && python -m pytest tests -v`

Expected: PASS against PostgreSQL 16.

- [ ] **Step 7: Merge Group 1**

Mark PR #5 ready and squash-merge after CI is green. Rebase/refresh PR #4 onto the new `main`, resolve `app/main.py` and CI overlap by preserving both secure ingestion and security modules, run the full suite, then squash-merge PR #4.

---

### Task 2: Correlation, tracking, fusion/reporting, and alerts

**Files:**
- Create: `app/services/correlation.py`
- Create: `app/services/tracking.py`
- Create: `app/services/fusion.py`
- Create: `app/services/alerts.py`
- Create: `app/services/__init__.py`
- Modify: `app/main.py`
- Test: `tests/unit/test_correlation.py`
- Test: `tests/integration/test_processing_pipeline.py`

**Interfaces:**
- Consumes: persisted `CollectionItem`, `Watch`, `FusedTrack`, `Alert`, `IntelligenceProduct`, `AuditEvent` models.
- Produces: `correlate_observations(db, observation_id) -> list[CollectionItem]`, `upsert_track(db, observation, related) -> FusedTrack`, `build_assessment(db, track) -> IntelligenceProduct`, `evaluate_watches(db, track) -> list[Alert]`.

- [ ] **Step 1: Write a failing correlation unit test**

```python
def test_correlates_same_domain_nearby_observations():
    matches = correlate_candidates(
        anchor={"domain": "air", "location": {"lat": 0.3136, "lon": 32.5811}, "confidence": 0.82},
        candidates=[
            {"id": "a", "domain": "air", "location": {"lat": 0.3140, "lon": 32.5815}, "confidence": 0.75},
            {"id": "b", "domain": "ground", "location": {"lat": 0.3140, "lon": 32.5815}, "confidence": 0.91},
        ],
    )
    assert [item["id"] for item in matches] == ["a"]
```

- [ ] **Step 2: Run the unit test**

Run: `python -m pytest tests/unit/test_correlation.py -v`

Expected: FAIL because `correlate_candidates` does not exist.

- [ ] **Step 3: Implement deterministic candidate correlation**

Match same-domain observations with valid location dictionaries and distance <= 1 km. Sort by confidence descending, then ID for stable output. Do not introduce ML dependencies.

- [ ] **Step 4: Write a failing processing-pipeline integration test**

The test must create two synthetic air observations, create an active location watch, call the processing endpoint, and assert one `FusedTrack`, one `IntelligenceProduct`, at least one matching `Alert`, and audit entries linked to the created resources.

- [ ] **Step 5: Implement track lifecycle**

`upsert_track` must create a track on the first observation and update the existing active track when a correlated observation arrives. Persist lifecycle/status values `DETECTED`, `ACTIVE`, `UPDATED`, `CLOSED` using the existing model fields; never silently delete history.

- [ ] **Step 6: Implement fusion/reporting**

`build_assessment` must persist an `IntelligenceProduct` containing the track ID, contributing observation IDs, confidence derived from contributing observations, and a compact evidence summary in JSONB.

- [ ] **Step 7: Implement watch evaluation and alert creation**

`evaluate_watches` must evaluate active watches against track domain/location metadata, create one alert per matching watch/track condition, and avoid duplicate active alerts for the same watch + track.

- [ ] **Step 8: Wire authenticated processing endpoint**

Add `POST /api/draco/v1/observations/{observation_id}/process` requiring `draco_analyst` or `draco_admin`. In one request, load the observation, correlate, upsert track, build assessment, evaluate watches, append audit records, commit, and return IDs.

- [ ] **Step 9: Run Group 2 tests and full suite**

Run: `python -m pytest tests/unit/test_correlation.py tests/integration/test_processing_pipeline.py -v`

Then: `python -m pytest tests -v`

Expected: PASS.

---

### Task 3: Operational APIs, hardening, live-source adapters, and final acceptance

**Files:**
- Create: `app/api/operations.py`
- Create: `app/api/__init__.py`
- Create: `app/sources/base.py`
- Create: `app/sources/json_adapter.py`
- Create: `app/sources/__init__.py`
- Modify: `app/main.py`
- Modify: `.env.example`
- Modify: `.github/workflows/ci.yml`
- Test: `tests/integration/test_operations_api.py`
- Test: `tests/integration/test_e2e_acceptance.py`

**Interfaces:**
- Consumes: Group 1 security and Group 2 processing services.
- Produces: authenticated read APIs for observations/tracks/alerts/products/audit, `JSONSourceAdapter.normalize(payload) -> ObservationCreate`, and one final acceptance path.

- [ ] **Step 1: Write failing operational read API tests**

Assert `401` without identity and `200` for analyst/admin on:

```text
GET /api/draco/v1/observations
GET /api/draco/v1/tracks
GET /api/draco/v1/alerts
GET /api/draco/v1/products
GET /api/draco/v1/audit
```

Protected source identity must remain restricted to source-admin/admin.

- [ ] **Step 2: Implement focused operations router**

Each endpoint returns IDs, status, timestamps, confidence, evidence references, and related resource IDs. Avoid exposing protected source `real_name`, contact, or notes through general analyst endpoints.

- [ ] **Step 3: Add JSON live-source adapter boundary**

```python
class JSONSourceAdapter:
    def normalize(self, payload: dict) -> ObservationCreate:
        return ObservationCreate(
            source_type=str(payload["source_type"]),
            domain=str(payload["domain"]),
            platform=payload.get("platform"),
            location=payload.get("location"),
            raw_content=payload.get("raw_content"),
            confidence=float(payload.get("confidence", 0.5)),
        )
```

This establishes a real adapter contract without coupling DRACO to any single external provider.

- [ ] **Step 4: Harden configuration**

Add `JANUS_ISSUER`, `JANUS_AUDIENCE`, `JANUS_JWKS_URL`, `DATABASE_URL`, and explicit `DRACO_ENV` placeholders to `.env.example`. Readiness must return `503` when PostgreSQL is unavailable; protected endpoints must return `503` when JANUS is not configured rather than silently bypassing auth.

- [ ] **Step 5: Write final end-to-end acceptance test**

The test must:

```text
1. create/register a protected source as source-admin
2. create a watch as analyst/admin
3. ingest observation A as collector
4. ingest correlated observation B as collector
5. process A and B as analyst
6. verify one active/updated fused track
7. verify an intelligence product references both observations
8. verify a watch alert exists
9. verify operational APIs return the track/product/alert
10. verify audit events trace source registration, ingestion, processing, product creation, and alert creation
```

- [ ] **Step 6: Run final acceptance**

Run: `alembic upgrade head && python -m pytest tests/integration/test_e2e_acceptance.py -v`

Expected: PASS.

- [ ] **Step 7: Run complete regression suite**

Run: `python -m pytest tests -v`

Expected: PASS with zero failures.

- [ ] **Step 8: Verify GitHub Actions and merge**

CI must show PostgreSQL migration success and full pytest success on the final completion PR before merge to `main`.

- [ ] **Step 9: Operational certification rule**

Only after Step 8 succeeds, record DRACO as `OPERATIONAL / ACCEPTED`. If any acceptance assertion fails, leave status `NOT YET OPERATIONAL` and fix the specific failing stage rather than restarting completed groups.
