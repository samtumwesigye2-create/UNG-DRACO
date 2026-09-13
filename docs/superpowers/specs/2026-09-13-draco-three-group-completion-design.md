# UNG-DRACO Three-Group Completion Design

## Goal
Finish the remaining UNG-DRACO implementation in three coherent build groups while preserving the already-merged Task 1 foundation and Task 2 PostgreSQL domain schema.

## Current repository baseline
- `main` contains the FastAPI/PostgreSQL foundation, health/readiness endpoints, domain models, Alembic migrations, and CI.
- PR #5 (`build/group1-core`) contains the observation-ingestion path and is the preferred base for Group 1.
- PR #4 (`feat/task-3-security`) contains JANUS authentication/RBAC/audit work but must be reconciled with the Group 1 branch before merge.

## Group 1 — Secure Collection and Ingestion

### Scope
1. Finish observation ingestion for OSINT, sensor, field-report, and camera-derived observations through a common input contract.
2. Normalize source metadata, timestamps, evidence references, location, and confidence inputs.
3. Enforce JANUS-compatible authentication and role-based access for protected DRACO endpoints.
4. Persist audit events for security-sensitive operations and protected-source access.
5. Merge the usable security work from PR #4 into the Group 1 implementation rather than maintaining parallel conflicting branches.

### Acceptance
- Health/readiness remain available.
- Non-health DRACO endpoints reject unauthenticated requests.
- Protected-source operations enforce roles.
- Valid observations are persisted and returned with stable IDs.
- Ingestion/audit tests pass against PostgreSQL in CI.

## Group 2 — Correlation, Tracking, Fusion, Reporting, and Alerts

### Scope
1. Correlate normalized observations by time, source, location/entity identity, and confidence.
2. Create and update fused tracks with lifecycle states: detected, active, updated, dormant/lost, reacquired, closed.
3. Preserve evidence provenance from track and assessment back to original observations.
4. Produce structured intelligence assessments and reports from fused tracks.
5. Implement configurable watch rules and deduplicated alerts with an auditable lifecycle.

### Acceptance
- Related observations correlate into a common track without destroying provenance.
- Track updates are deterministic and idempotent for duplicate inputs.
- Reports reference supporting tracks/observations.
- Watch rules produce alerts once per logical event and record state transitions.
- Unit/integration tests cover positive, duplicate, conflict, and no-match paths.

## Group 3 — Operational API, Dashboard Surface, Hardening, Live Sources, and Acceptance

### Scope
1. Expose observations, tracks, watches, alerts, reports, source health, and evidence lineage through authenticated APIs.
2. Provide an operator-facing dashboard surface using the same API contracts.
3. Add production hardening: request validation, rate limits where appropriate, structured logs, error handling, health/readiness dependencies, and safe configuration defaults.
4. Add live-source adapter contracts and at least one controlled live/test source path so runtime behavior can be exercised without fabricated evidence.
5. Add a deterministic end-to-end acceptance scenario that drives data through collection → ingestion → normalization → correlation → tracking → assessment → watch/alert → report → API/dashboard → audit.

### Acceptance
- The full chain executes with real runtime/database evidence.
- Each stage emits a stable identifier/timestamp and preserves provenance.
- API/dashboard surfaces show the resulting observation, track, alert, report, and audit chain.
- CI passes migrations, tests, and the end-to-end acceptance scenario.
- DRACO is marked operational only after the acceptance evidence is green.

## Data flow
Source adapter → authenticated ingestion → normalization → observation persistence → correlation → fused track → assessment/report → watch evaluation → alert lifecycle → API/dashboard → audit trail.

## Error handling
- Reject malformed or unauthorized input before persistence.
- Preserve conflicting observations rather than silently overwriting them.
- Treat duplicate idempotency keys as replays and return the existing logical record.
- Fail closed for protected-source authorization.
- Surface correlation/reporting failures as auditable processing errors without deleting source evidence.

## Testing strategy
Use test-driven implementation. Each build group starts with failing acceptance/integration tests, then the smallest production implementation required to pass. PostgreSQL-backed CI remains the integration authority. Final completion requires a passing end-to-end acceptance test and green CI on the merge candidate.

## Merge strategy
- Complete and merge Group 1 first.
- Branch Group 2 from the new `main`, merge only after its CI is green.
- Branch Group 3 from the new `main`, merge only after its CI and end-to-end acceptance evidence are green.
- Do not mark later groups complete based on design documents or unexecuted tests.
