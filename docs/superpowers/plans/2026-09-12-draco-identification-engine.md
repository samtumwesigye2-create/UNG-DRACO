# UNG-DRACO Identification Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the approved DRACO Identification Engine for plates, people/authorized face-watchlist matches, animals/species, vehicles/objects, persistent tracking, offline/central reconciliation, auditable watchlists, model management, and sanitized UNG events.

**Architecture:** The engine is an internal DRACO subsystem. Recognition services emit one normalized identification result contract, feed persistent tracks and governed watchlists, preserve uncertainty, and publish sanitized events into the existing DRACO -> HEPHA -> PULSAR chain. Edge execution uses externally supplied signed model packages and encrypted local caches; raw biometric material, real watchlists, credentials, camera endpoints, and operational locations are never stored in source control.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.x, PostgreSQL 16, Alembic, Pydantic, PyJWT/JANUS auth, cryptography AES-GCM, ONNX Runtime, OpenCV, NumPy, pytest.

**Spec:** `docs/superpowers/specs/2026-09-12-draco-identification-engine-design.md`

## Global Constraints

- DRACO remains the owning system; this feature does not create another UNG system.
- Autonomous lethal targeting or weapon control is explicitly excluded.
- Face recognition is limited to authorized enrolled watchlists/databases and is probabilistic, not definitive identity proof.
- Plate reads are observations, not proof of ownership or driver identity.
- Uncertain values remain null/unknown rather than being fabricated.
- Real watchlists, face embeddings, license-plate datasets, credentials, camera endpoints, operational locations, or keys must never be committed.
- Production uses PostgreSQL; SQLite is not an operational backend.
- All sensitive identification/watchlist actions require JANUS/RBAC and append-only audit records.
- VAULT supplies runtime encryption keys; no hardcoded secrets.
- Model artifacts are external runtime assets and must pass integrity verification before activation.
- Current `main` does not yet contain the pending Task-3 security branch; identification implementation must either merge the approved JANUS/RBAC/audit work first or port those exact security primitives into this feature branch before exposing protected endpoints.

---

## File Structure

Create focused modules rather than one large vision file:

- `app/models/identification.py` — persisted identification results, watchlists, watchlist entries, model registry, edge sync state.
- `app/schemas/identification.py` — Pydantic API/data contracts.
- `app/services/identification/contracts.py` — normalized result types and recognition interfaces.
- `app/services/identification/confidence.py` — Possible/Probable/Confirmed-by-policy threshold logic.
- `app/services/identification/plate.py` — plate detection/OCR adapter and normalization.
- `app/services/identification/face.py` — person/face embedding + authorized watchlist matching adapter.
- `app/services/identification/animal.py` — animal category/species classification adapter.
- `app/services/identification/object.py` — vehicle/general object classification adapter.
- `app/services/identification/tracking.py` — frame-to-frame association and DRACO track handoff.
- `app/services/identification/watchlists.py` — governed watchlist access and matching.
- `app/services/identification/models.py` — signed model manifest validation and last-known-good rollback.
- `app/services/identification/sanitization.py` — outbound minimization/classification.
- `app/services/identification/sync.py` — idempotent offline queue reconciliation.
- `app/api/identification.py` — protected `/v1/identification/*` routes.
- `field/identification_queue.py` — encrypted edge queue/cache support.
- `alembic/versions/20260912_0002_identification_engine.py` — schema migration.
- tests split into `tests/unit/identification/`, `tests/integration/identification/`, and `tests/acceptance/identification/`.

---

### Task 1: Security Dependency Gate and Protected Router

**Files:**
- Modify: `app/main.py`
- Create if missing from current branch: `app/security/auth.py`, `app/security/rbac.py`, `app/security/audit.py`
- Create: `app/api/identification.py`
- Test: `tests/integration/identification/test_auth_gate.py`

**Interfaces:**
- Consumes: `get_current_principal() -> Principal`, `require_roles(*roles)` and `append_audit_event(...)` from DRACO security.
- Produces: protected router mounted at `/v1/identification`.

- [ ] **Step 1: Write the failing authentication test**

```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_identification_status_rejects_missing_identity():
    response = client.get('/v1/identification/status')
    assert response.status_code == 401
```

- [ ] **Step 2: Run the test and confirm RED**

Run: `python -m pytest tests/integration/identification/test_auth_gate.py -v`

Expected: FAIL because the route or security dependency is missing.

- [ ] **Step 3: Add the protected router**

```python
# app/api/identification.py
from fastapi import APIRouter, Depends
from app.security.auth import get_current_principal
from app.security.rbac import Principal

router = APIRouter(prefix='/v1/identification', tags=['identification'])

@router.get('/status')
def status(principal: Principal = Depends(get_current_principal)) -> dict[str, str]:
    return {'system': 'UNG-DRACO', 'component': 'identification', 'status': 'ok'}
```

Mount it from `app/main.py` with `app.include_router(identification.router)`.

- [ ] **Step 4: Run the test and existing health/security tests**

Run: `python -m pytest tests/integration/identification/test_auth_gate.py tests/unit/test_health.py tests/integration/test_auth.py -v`

Expected: PASS. If `tests/integration/test_auth.py` does not exist on this branch, first merge/port the previously approved Task-3 JANUS/RBAC/audit implementation, then rerun.

- [ ] **Step 5: Commit**

```bash
git add app/main.py app/api/identification.py app/security tests/integration/identification/test_auth_gate.py
git commit -m "feat: protect DRACO identification API"
```

---

### Task 2: Authoritative Identification Schema

**Files:**
- Create: `app/models/identification.py`
- Modify: `app/models/__init__.py`
- Create: `alembic/versions/20260912_0002_identification_engine.py`
- Test: `tests/integration/identification/test_schema.py`

**Interfaces:**
- Produces SQLAlchemy models: `IdentificationResult`, `Watchlist`, `WatchlistEntry`, `RecognitionModel`, `EdgeSyncItem`.

- [ ] **Step 1: Write failing schema tests**

```python
from sqlalchemy import inspect
from app.database import engine

def test_identification_tables_exist():
    tables = set(inspect(engine).get_table_names())
    assert {'identification_results', 'watchlists', 'watchlist_entries', 'recognition_models', 'edge_sync_items'} <= tables
```

- [ ] **Step 2: Confirm RED**

Run: `alembic upgrade head && python -m pytest tests/integration/identification/test_schema.py -v`

Expected: FAIL because the five tables do not exist.

- [ ] **Step 3: Implement models and migration**

Required `IdentificationResult` columns: UUID `id`, UUID `collection_item_id` nullable FK, `object_type`, `subtype`, `species`, `plate_text`, JSONB `plate_alternates`, UUID `face_match_reference` nullable, float `confidence`, `confidence_state`, `match_source`, timezone-aware `observed_at`, JSONB `location`, `sensor_id`, `device_id`, `media_reference`, `evidence_reference`, `model_name`, `model_version`, UUID `track_id` nullable, UUID `watch_match_reference` nullable, JSONB `policy_metadata`, JSONB `classification_metadata`, timestamps.

Required `Watchlist` columns: UUID `id`, `name`, `watch_type`, `owning_authority`, `classification`, `status`, timestamps.

Required `WatchlistEntry` columns: UUID `id`, FK `watchlist_id`, `subject_reference`, `operational_reason`, `match_threshold`, JSONB `allowed_actions`, bool `edge_sync_allowed`, `expires_at`, `review_at`, JSONB `encrypted_match_material`, timestamps.

Required `RecognitionModel` columns: UUID `id`, `model_name`, `model_version`, `recognition_type`, `sha256`, `manifest_signature`, `artifact_path`, `status`, bool `last_known_good`, JSONB `calibration`, timestamps.

Required `EdgeSyncItem` columns: UUID `id`, unique `idempotency_key`, `device_id`, `payload_type`, JSONB `payload`, `original_timestamp`, `sync_status`, `attempt_count`, `last_error`, timestamps.

- [ ] **Step 4: Run migration and schema tests**

Run: `alembic upgrade head && python -m pytest tests/integration/identification/test_schema.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/models alembic/versions/20260912_0002_identification_engine.py tests/integration/identification/test_schema.py
git commit -m "feat: add identification engine schema"
```

---

### Task 3: Normalized Result Contract and Confidence Engine

**Files:**
- Create: `app/schemas/identification.py`
- Create: `app/services/identification/__init__.py`
- Create: `app/services/identification/contracts.py`
- Create: `app/services/identification/confidence.py`
- Test: `tests/unit/identification/test_contracts.py`
- Test: `tests/unit/identification/test_confidence.py`

**Interfaces:**
- Produces `IdentificationObservation`, `BoundingBox`, `MatchSource`, `ConfidenceState`, `ConfidencePolicy.classify(score, evidence_count, analyst_confirmed=False)`.

- [ ] **Step 1: Write failing confidence tests**

```python
from app.services.identification.confidence import ConfidencePolicy, ConfidenceState

def test_low_score_is_possible():
    policy = ConfidencePolicy(probable_threshold=0.75, confirm_threshold=0.92)
    assert policy.classify(0.55, evidence_count=1) == ConfidenceState.POSSIBLE

def test_high_score_is_not_confirmed_without_policy_evidence():
    policy = ConfidencePolicy(probable_threshold=0.75, confirm_threshold=0.92, minimum_confirming_observations=2)
    assert policy.classify(0.96, evidence_count=1) == ConfidenceState.PROBABLE

def test_authorized_analyst_can_confirm():
    policy = ConfidencePolicy(probable_threshold=0.75, confirm_threshold=0.92)
    assert policy.classify(0.80, evidence_count=1, analyst_confirmed=True) == ConfidenceState.CONFIRMED_BY_POLICY
```

- [ ] **Step 2: Confirm RED**

Run: `python -m pytest tests/unit/identification/test_contracts.py tests/unit/identification/test_confidence.py -v`

- [ ] **Step 3: Implement strict Pydantic/dataclass contracts**

`IdentificationObservation` must require `detection_id`, `object_type`, `confidence`, `confidence_state`, `match_source`, `observed_at`, `sensor_id`, `model_name`, `model_version`; optional fields stay `None` instead of inferred.

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/unit/identification/test_contracts.py tests/unit/identification/test_confidence.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/schemas/identification.py app/services/identification tests/unit/identification
git commit -m "feat: normalize DRACO identification results"
```

---

### Task 4: Model Runtime, Integrity Verification, and Rollback

**Files:**
- Create: `app/services/identification/models.py`
- Modify: `requirements.txt`
- Test: `tests/unit/identification/test_model_registry.py`

**Interfaces:**
- Produces `ModelManifest`, `verify_sha256(path, expected)`, `ModelRegistry.activate(manifest)`, `ModelRegistry.rollback(recognition_type)`.

- [ ] **Step 1: Write RED tests for integrity rejection and rollback**

```python
from pathlib import Path
import pytest
from app.services.identification.models import verify_sha256

def test_model_hash_mismatch_is_rejected(tmp_path: Path):
    artifact = tmp_path / 'model.onnx'
    artifact.write_bytes(b'not-the-approved-model')
    with pytest.raises(ValueError, match='integrity'):
        verify_sha256(artifact, '0' * 64)
```

Add a registry test where model `v2` fails health validation and `v1` remains `last_known_good=True`.

- [ ] **Step 2: Confirm RED**

Run: `python -m pytest tests/unit/identification/test_model_registry.py -v`

- [ ] **Step 3: Implement model manifest and ONNX runtime dependency**

Add `onnxruntime`, `opencv-python-headless`, `numpy`, and `cryptography` using versions compatible with Python 3.12. Model weights remain external runtime files; tests create tiny fake files and fake health probes.

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/unit/identification/test_model_registry.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/services/identification/models.py requirements.txt tests/unit/identification/test_model_registry.py
git commit -m "feat: verify and rollback recognition models"
```

---

### Task 5: Plate, Animal, Vehicle/Object Recognition Adapters

**Files:**
- Create: `app/services/identification/plate.py`
- Create: `app/services/identification/animal.py`
- Create: `app/services/identification/object.py`
- Test: `tests/unit/identification/test_plate.py`
- Test: `tests/unit/identification/test_animal.py`
- Test: `tests/unit/identification/test_object.py`

**Interfaces:**
- Each adapter exposes `recognize(frame: np.ndarray, context: RecognitionContext) -> list[IdentificationObservation]`.
- Plate adapter also exposes `normalize_plate_text(raw: str) -> str` and retains alternate OCR candidates.

- [ ] **Step 1: Write failing plate normalization tests**

```python
from app.services.identification.plate import normalize_plate_text

def test_plate_normalization_keeps_alphanumerics():
    assert normalize_plate_text(' UBA-123 A ') == 'UBA123A'
```

Add tests ensuring a partially unreadable plate preserves alternate candidates and never invents missing characters.

- [ ] **Step 2: Write animal/object fallback tests**

A low-confidence species score must return broad category `animal`/`wildlife` and `species=None`; low-confidence vehicle subclass must preserve `object_type='vehicle'` without forced subtype.

- [ ] **Step 3: Confirm RED**

Run: `python -m pytest tests/unit/identification/test_plate.py tests/unit/identification/test_animal.py tests/unit/identification/test_object.py -v`

- [ ] **Step 4: Implement ONNX adapter boundaries**

Use dependency-injected model runners so tests do not require production model weights. Production adapters consume verified model manifests from Task 4 and emit normalized results with exact model name/version and bounding boxes.

- [ ] **Step 5: Run tests and commit**

Run: `python -m pytest tests/unit/identification/test_plate.py tests/unit/identification/test_animal.py tests/unit/identification/test_object.py -v`

```bash
git add app/services/identification/{plate,animal,object}.py tests/unit/identification
git commit -m "feat: add plate animal and object recognition adapters"
```

---

### Task 6: Person Detection and Authorized Face-Watchlist Matching

**Files:**
- Create: `app/services/identification/face.py`
- Create: `app/services/identification/watchlists.py`
- Test: `tests/unit/identification/test_face.py`
- Test: `tests/integration/identification/test_watchlists.py`

**Interfaces:**
- Produces `FaceEmbeddingProvider.embed(face_crop) -> np.ndarray | None`.
- Produces `WatchlistMatcher.match(embedding, watchlist_id, threshold) -> MatchCandidate | None`.
- Matching is authorized-watchlist-only; no open-world identity lookup.

- [ ] **Step 1: Write failing unknown-person and low-quality tests**

```python
def test_unknown_person_has_no_forced_identity(face_service, unknown_face):
    result = face_service.identify(unknown_face)
    assert result.face_match_reference is None
    assert result.confidence_state != 'confirmed-by-policy'

def test_low_quality_face_skips_embedding(face_service, blurred_face):
    result = face_service.identify(blurred_face)
    assert result.face_match_reference is None
```

- [ ] **Step 2: Write failing authorization/audit tests**

Test that `draco_analyst` cannot administer biometric watchlist material, `draco_source_admin`/`draco_admin` can where policy permits, and each sensitive match lookup creates an `AuditEvent`.

- [ ] **Step 3: Confirm RED**

Run: `python -m pytest tests/unit/identification/test_face.py tests/integration/identification/test_watchlists.py -v`

- [ ] **Step 4: Implement encrypted watchlist matching**

Use AES-GCM for `encrypted_match_material` with key material supplied at runtime by the VAULT integration/environment abstraction. Store only encrypted authorized embeddings; decrypt in memory for comparison, zero references promptly, and never serialize raw embeddings in API responses or logs.

Use cosine similarity:

```python
def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)
```

- [ ] **Step 5: Run tests and commit**

Run: `python -m pytest tests/unit/identification/test_face.py tests/integration/identification/test_watchlists.py -v`

```bash
git add app/services/identification/{face,watchlists}.py tests/unit/identification/test_face.py tests/integration/identification/test_watchlists.py
git commit -m "feat: add governed face watchlist matching"
```

---

### Task 7: Persistent Tracking and Cross-Sensor Handoff

**Files:**
- Create: `app/services/identification/tracking.py`
- Test: `tests/unit/identification/test_tracking.py`
- Test: `tests/integration/identification/test_track_handoff.py`

**Interfaces:**
- Produces `TrackAssociationService.associate(observation) -> TrackAssociation`.
- Hands material sightings into existing DRACO `tracks`/`track_items` rather than creating a competing track system.

- [ ] **Step 1: Write failing continuity tests**

Test same-object consecutive frames preserve a track ID; incompatible class/location/time evidence starts a separate track; low-confidence identity never overwrites an established stronger identity.

- [ ] **Step 2: Confirm RED**

Run: `python -m pytest tests/unit/identification/test_tracking.py tests/integration/identification/test_track_handoff.py -v`

- [ ] **Step 3: Implement deterministic association scoring**

Score uses bounding-box overlap when same sensor/frame sequence is available plus temporal proximity, spatial proximity, object class agreement, plate agreement, authorized face candidate agreement, and existing DRACO track evidence. Return score + explanation fields for auditability.

- [ ] **Step 4: Run tests**

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/services/identification/tracking.py tests/unit/identification/test_tracking.py tests/integration/identification/test_track_handoff.py
git commit -m "feat: correlate identification observations into DRACO tracks"
```

---

### Task 8: Offline Edge Queue, Encrypted Cache, and Idempotent Reconciliation

**Files:**
- Create: `field/identification_queue.py`
- Create: `app/services/identification/sync.py`
- Test: `tests/unit/identification/test_edge_queue.py`
- Test: `tests/integration/identification/test_sync.py`

**Interfaces:**
- Produces `EncryptedEdgeQueue.enqueue(idempotency_key, payload, observed_at)`, `.pending()`, `.acknowledge(key)`.
- Produces `SyncService.ingest(device_id, items) -> SyncResult` with duplicate suppression.

- [ ] **Step 1: Write failing offline/reconnect tests**

Test observations remain queued with original timestamps while network is unavailable, sync once after reconnection, and a repeated upload with the same `idempotency_key` does not create a duplicate `IdentificationResult`.

- [ ] **Step 2: Confirm RED**

Run: `python -m pytest tests/unit/identification/test_edge_queue.py tests/integration/identification/test_sync.py -v`

- [ ] **Step 3: Implement encrypted queue and reconciliation**

Encrypt payloads at rest using AES-GCM with a per-device runtime key from VAULT. The server enforces a unique database constraint on `idempotency_key` and returns already-processed status for duplicates.

- [ ] **Step 4: Run tests**

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add field/identification_queue.py app/services/identification/sync.py tests/unit/identification/test_edge_queue.py tests/integration/identification/test_sync.py
git commit -m "feat: sync encrypted offline identification observations"
```

---

### Task 9: Retention, Sanitization, and UNG Event Contracts

**Files:**
- Create: `app/services/identification/retention.py`
- Create: `app/services/identification/sanitization.py`
- Modify: `app/services/events.py` if present, otherwise create `app/services/events.py`
- Test: `tests/unit/identification/test_retention.py`
- Test: `tests/unit/identification/test_sanitization.py`

**Interfaces:**
- Produces `RetentionPolicy.expiry_for(result) -> datetime | None`.
- Produces `sanitize_identification_event(result) -> dict`.

- [ ] **Step 1: Write failing sanitization tests**

```python
def test_outbound_event_excludes_biometric_material(result_with_face_match):
    event = sanitize_identification_event(result_with_face_match)
    serialized = str(event).lower()
    assert 'embedding' not in serialized
    assert 'encrypted_match_material' not in serialized
```

Also test protected source identity and unrestricted full-resolution evidence references are absent unless an explicit outbound policy permits them.

- [ ] **Step 2: Write retention tests**

Routine unmatched observations receive short configurable expiry; mission/watch/intelligence evidence uses governing policy; legal hold returns no deletion deadline.

- [ ] **Step 3: Confirm RED**

Run: `python -m pytest tests/unit/identification/test_retention.py tests/unit/identification/test_sanitization.py -v`

- [ ] **Step 4: Implement event families**

Emit versioned sanitized contracts for `draco.identification.detected`, `draco.plate.read`, `draco.face.match_candidate`, `draco.animal.identified`, and `draco.object.tracked`. Include event ID/type/time/source/classification/correlation/track/confidence/location/payload version, but never raw biometric templates.

- [ ] **Step 5: Run tests and commit**

```bash
git add app/services/identification/{retention,sanitization}.py app/services/events.py tests/unit/identification
git commit -m "feat: sanitize identification events and enforce retention"
```

---

### Task 10: Identification API and Audit-Covered Administration

**Files:**
- Modify: `app/api/identification.py`
- Modify: `app/schemas/identification.py`
- Test: `tests/integration/identification/test_api.py`

**Interfaces:**
- Protected routes: `POST /v1/identification/observations`, `GET /v1/identification/results`, `POST/GET /v1/identification/watchlists`, `POST /v1/identification/watchlists/{id}/entries`, `POST /v1/identification/sync`, `GET /v1/identification/models`.

- [ ] **Step 1: Write failing RBAC/API tests**

Verify collector/service roles can ingest observations, analysts can read policy-approved results, source_admin/admin can manage protected watchlist material as configured, and unauthorized role/action combinations return 403.

- [ ] **Step 2: Write audit tests**

Every watchlist read/change, biometric lookup, protected evidence access, analyst override, and export path must create an append-only audit event containing actor subject, action, resource type/id, timestamp, and minimal safe details.

- [ ] **Step 3: Confirm RED**

Run: `python -m pytest tests/integration/identification/test_api.py -v`

- [ ] **Step 4: Implement routes with response minimization**

Never return `encrypted_match_material`, raw face embeddings, protected source identity, or secrets from normal response schemas.

- [ ] **Step 5: Run tests and commit**

```bash
git add app/api/identification.py app/schemas/identification.py tests/integration/identification/test_api.py
git commit -m "feat: expose audited identification API"
```

---

### Task 11: Controlled End-to-End Acceptance Harness

**Files:**
- Create: `tests/acceptance/identification/test_end_to_end.py`
- Create: `tests/acceptance/identification/fixtures/README.md`
- Modify: `.github/workflows/ci.yml`
- Modify: `README.md`

**Interfaces:**
- Exercises the full sensor-input-to-sanitized-event chain with synthetic/authorized test fixtures only.

- [ ] **Step 1: Add the acceptance test before implementation is declared complete**

The test suite must cover all 20 cases from the approved spec: Ugandan and international plate cases, authorized test-person match, unknown/low-quality person handling, animal/species fallback, vehicle/object classification, frame continuity, repeated-sighting DRACO track association, offline cache, deferred verification, duplicate suppression, false-match rejection, sensitive-action audit, retention deletion, outbound sanitization, model integrity rejection/rollback, model/version traceability, and full pipeline through track/watch/alert/intelligence product/sanitized event.

- [ ] **Step 2: Run full RED/GREEN acceptance loop**

Run:

```bash
alembic upgrade head
python -m pytest tests/unit tests/integration tests/acceptance/identification -v
```

Expected final result: all tests PASS with zero xfails/skips for the 20 mandatory identification acceptance cases.

- [ ] **Step 3: Add CI job**

CI must start PostgreSQL 16, run `alembic upgrade head`, run unit/integration/identification acceptance suites, and fail on any mandatory skipped test.

- [ ] **Step 4: Document runtime model configuration**

README must document only configuration names and safe example paths/hashes; do not commit model weights, keys, watchlists, embeddings, real camera endpoints, or operational data.

- [ ] **Step 5: Commit**

```bash
git add tests/acceptance/identification .github/workflows/ci.yml README.md
git commit -m "test: complete DRACO identification acceptance harness"
```

---

## Verification Before Completion

Run exactly:

```bash
alembic upgrade head
python -m pytest tests/unit -v
python -m pytest tests/integration -v
python -m pytest tests/acceptance/identification -v
```

Then verify the CI run for the final branch head is green. Do not call the Identification Engine operational until the controlled end-to-end acceptance suite and a live runtime acceptance using approved external model packages both pass.

## Self-Review

- Spec coverage: all approved sections are mapped to Tasks 1-11, including recognition services, normalized result, confidence states, edge/central modes, governed watchlists, security/audit, retention, sanitization, hardware profiles through runtime configuration, model management, failure handling, and all 20 acceptance cases.
- Placeholder scan: no TBD/TODO/fill-later steps remain.
- Type consistency: all recognition adapters emit `IdentificationObservation`; confidence uses `ConfidenceState`; model loading uses verified manifests; watchlist matching returns `MatchCandidate`; tracking consumes normalized observations; sync uses unique `idempotency_key`; outbound events consume persisted normalized results.
- Dependency risk: current `main` lacks the pending Task-3 JANUS/RBAC/audit code visible in earlier work; Task 1 explicitly gates protected identification work on merging/porting those primitives first.
