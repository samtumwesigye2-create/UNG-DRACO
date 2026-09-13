# UNG-DRACO Design

## Identity

**System name:** UNG-DRACO  
**Expansion:** Detection, Reconnaissance, Analysis, Collection & Observation

UNG-DRACO is the standalone ISR and intelligence-analysis system described in the approved handoff. It collects information from multiple source types, normalizes observations, detects targets and anomalies, correlates and fuses data across domains, manages reconnaissance missions and surveillance watches, generates alerts, maintains fused tracks, and produces intelligence products and a command picture.

## Goals

1. Preserve the existing prototype behavior while replacing prototype-grade infrastructure with production-oriented components.
2. Use PostgreSQL as the authoritative datastore from the first implementation commit.
3. Protect every API with JANUS-backed authentication and role-based authorization.
4. Maintain strict protection of human-source identity data; source identity must never be emitted in normal operational API responses or backbone events.
5. Provide auditable, testable collection, detection, correlation, fusion, watch, alert, mission, intelligence-product, and command-picture workflows.
6. Integrate DRACO with HEPHA, PULSAR, ORION, SENTINEL, APOLLO, NEXUS, VAULT, and NOVA through stable event contracts rather than tight coupling.
7. Support a Raspberry Pi field agent for motion-triggered media capture, optional GPS tagging, offline buffering, retry, and secure upload.

## Non-goals for the first production pass

- Replacing ORION or SENTINEL as a command system.
- Building a new map frontend.
- Implementing autonomous lethal or weapon-control functions.
- Building custom ML models from scratch.
- Storing raw protected source identities outside DRACO.

## Repository structure

```text
app/
  main.py
  config.py
  database.py
  models/
  api/
  services/
    collection.py
    entities.py
    detection.py
    fusion.py
    watches.py
    intelligence.py
    events.py
  security/
    auth.py
    rbac.py
    audit.py
field/
  field_agent.py
  buffer.py
  gps.py
tests/
  unit/
  integration/
  acceptance/
docs/
  contracts/
  superpowers/
Dockerfile
requirements.txt
.env.example
README.md
```

Each module has one primary responsibility and communicates through explicit service interfaces.

## Data model

The first implementation preserves the prototype entities and relationships:

- `sources`: protected human-source identity records.
- `reports`: human intelligence reports linked by `source_id`; no source identity fields are exposed in report responses.
- `collection_items`: normalized records for OSINT, sensor, report, and media inputs.
- `entities`: extracted people, places, organizations, and other tracked entities.
- `missions`: reconnaissance missions with question, target, deadline, status, and answer.
- `watches`: persistent surveillance definitions.
- `alerts`: watch matches and intelligence alerts.
- `tracks`: fused multi-source tracks.
- `track_items`: contributing collection records linked to tracks.
- `intelligence_products`: fused analytic outputs.
- `audit_events`: immutable security and operational audit records.

PostgreSQL is authoritative storage. Database access uses transactions for collection ingestion and downstream derived records so a failed processing stage does not leave half-written state.

## API surface

The production service preserves the prototype concepts while organizing endpoints under versioned routes.

```text
POST /v1/sources
GET  /v1/sources
POST /v1/reports
GET  /v1/reports
POST /v1/collect/osint
POST /v1/collect/sensor
POST /v1/collect/airborne
POST /v1/collect/space
POST /v1/collect/maritime
POST /v1/collect/ground
POST /v1/collect/media
GET  /v1/collect
GET  /v1/entities
GET  /v1/entities/{id}
POST /v1/missions
GET  /v1/missions
GET  /v1/missions/{id}
POST /v1/missions/{id}/close
POST /v1/watches
GET  /v1/watches
GET  /v1/watches/{id}/timeline
POST /v1/watches/{id}/close
GET  /v1/alerts
POST /v1/alerts/{id}/acknowledge
GET  /v1/tracks
GET  /v1/tracks/{id}
POST /v1/tracks/{id}/close
GET  /v1/command/picture
POST /v1/reports/generate
GET  /v1/intelligence-products
GET  /health
GET  /ready
```

## Processing flow

The canonical processing pipeline is:

```text
Capture/Input
  -> Validate
  -> Normalize to collection_item
  -> Extract entities
  -> Compute target/detection score
  -> Correlate against active tracks
  -> Create/update fused track
  -> Evaluate surveillance watches
  -> Generate alert(s) when thresholds are met
  -> Update mission relevance
  -> Generate intelligence product on request or policy trigger
  -> Publish sanitized UNG events
  -> Update command picture
```

The pipeline must be deterministic and observable. Every stage receives a `correlation_id`, and significant state transitions create an audit event.

## Entity extraction

The prototype regex extractor is replaced with a real NER-capable adapter. The service interface is independent of the implementation so a lightweight library can be used initially and replaced later without changing API behavior.

The extractor returns structured entities with:

- `type`
- `value`
- `normalized_value`
- `confidence`
- `source_span` when applicable

Entity extraction failure must not reject collection ingestion; the item remains stored with extraction status recorded.

## Detection and correlation

Detection is scored instead of boolean keyword-only matching. The first scoring model combines:

- source confidence
- keyword/rule evidence
- repeated sightings
- domain diversity
- location consistency
- entity overlap
- watch relevance
- target-type consistency

The score is normalized to `0.0..1.0` and stored with an explanation structure so analysts can see why an item was flagged.

## Multi-domain fusion

Fusion preserves the prototype's location/time correlation idea but uses an explicit score across:

- spatial proximity
- temporal proximity
- entity overlap
- target type
- platform metadata
- source diversity
- confidence

A configurable threshold determines whether a collection item joins an active track or creates a new one. Every track update retains its contributing `track_items` for traceability.

## Surveillance watches and alerts

Every new collection item and every materially updated track is evaluated against active watches. Match reasons are stored, and duplicate alerts for the same watch/correlation window are suppressed.

Alerts include:

- watch reference
- related collection or track reference
- match reason
- confidence
- severity
- acknowledgement state
- timestamps

## Intelligence products

An intelligence product contains:

- analytic summary
- confidence assessment
- supporting observations
- contradictions or unresolved evidence
- related entities
- related tracks
- watch matches
- mission relevance
- analyst-review flags

Products never include protected human-source identity fields.

## Command picture

`GET /v1/command/picture` returns one operational snapshot containing:

- active watches
- open reconnaissance missions
- unacknowledged alerts
- active fused tracks
- recent activity grouped by domain
- latest intelligence products

This is a DRACO intelligence picture, not a replacement for the wider ORION command environment.

## Security

### JANUS

JANUS is the authentication and authorization authority. DRACO validates JANUS-issued service/user identity and maps claims to DRACO roles.

Initial roles:

- `draco_collector`: submit collection data only.
- `draco_analyst`: read operational intelligence, manage missions/watches, acknowledge alerts, generate products.
- `draco_source_admin`: manage protected source identity records.
- `draco_admin`: administrative configuration and operational oversight.
- `draco_service`: authenticated machine-to-machine integration.

Source identity access requires `draco_source_admin` or an explicitly equivalent privileged claim. Normal analysts see only `source_id` references.

### Audit

Audit records are append-only and capture:

- actor/service identity
- action
- resource type/id
- timestamp
- correlation id
- result
- source IP/request metadata when available

Reading protected source identity creates an audit event.

### Secrets and encryption

Secrets and cryptographic material are supplied through VAULT-backed runtime configuration. PostgreSQL and media-storage encryption at rest are infrastructure requirements. HTTPS/TLS is mandatory for every non-local connection.

## UNG backbone integration

DRACO publishes sanitized events through HEPHA/PULSAR rather than letting downstream systems read DRACO tables directly.

Required event families:

```text
draco.collection.received
draco.entity.detected
draco.target.detected
draco.track.created
draco.track.updated
draco.watch.matched
draco.alert.created
draco.mission.opened
draco.mission.closed
draco.intelligence_product.created
```

Every event envelope contains:

- `event_id`
- `event_type`
- `timestamp`
- `source_system` = `UNG-DRACO`
- `classification`
- `correlation_id`
- `mission_id` when applicable
- `track_id` when applicable
- `confidence` when applicable
- `location` when policy permits
- `payload_version`
- `payload`

Human-source identity, credentials, secrets, and raw protected metadata are forbidden in outbound event payloads.

### Consumers

- HEPHA: event normalization and common envelope handling.
- PULSAR: event transport.
- ORION: operational/intelligence picture consumption.
- SENTINEL: security-relevant DRACO alerts.
- APOLLO: intelligence products for planning and analysis.
- NEXUS: controlled external interoperability.
- NOVA: long-term analytics and metrics.
- VAULT: secrets and cryptographic material.

## Field agent

The field agent supports:

- Raspberry Pi 4/5 first target
- camera capture through OpenCV/picamera2 adapter
- motion-triggered capture
- optional GPS tagging
- local offline queue
- retry with backoff
- authenticated HTTPS upload
- no hard-coded credentials

Loss of connectivity must not discard captures. The queue is flushed in order when connectivity returns.

## Error handling and observability

All API responses use a consistent error envelope with `error_code`, `message`, and `correlation_id`. Internal exceptions are logged without leaking protected data.

Health endpoints:

- `/health`: process alive.
- `/ready`: process can reach required dependencies, especially PostgreSQL and configured auth/event services.

Metrics should cover ingestion count, processing latency, fusion decisions, alert generation, event-publish success/failure, queue depth, and failed authentication/authorization attempts.

## Testing strategy

### Unit

- entity extraction adapter
- detection scoring
- fusion scoring
- watch matching
- event sanitization
- RBAC decisions

### Integration

- PostgreSQL CRUD/transactions
- API authentication
- ingestion pipeline
- mission/watch lifecycle
- alert acknowledgement
- intelligence-product generation

### Acceptance

A controlled observation is injected and must produce verifiable runtime evidence for:

1. authenticated ingestion
2. persisted `collection_item`
3. entity/detection output
4. track creation or update
5. watch match when applicable
6. alert generation
7. intelligence-product generation
8. command-picture visibility
9. sanitized outbound event creation/delivery
10. audit records for the transaction

DRACO is not marked operational until this acceptance path runs against a live deployed service and PostgreSQL instance.

## Deployment

The backend is packaged as a Docker service. Runtime configuration comes from environment variables/secrets. The service must not depend on SQLite in production. Production hosting must support private networking, PostgreSQL, encrypted storage, TLS, backups, and restricted administrative access.

## Definition of done for V1 production baseline

UNG-DRACO V1 is complete when:

- PostgreSQL is authoritative storage.
- JANUS-backed authentication/RBAC protects every non-health endpoint.
- protected source identity is isolated and audited.
- collection, missions, watches, alerts, tracks, intelligence products, and command picture work end-to-end.
- detection/fusion use scored, explainable logic rather than the prototype's simple keyword/location-only behavior.
- sanitized backbone events are emitted through the defined integration adapter.
- field-agent offline buffering is covered by tests.
- unit, integration, and live acceptance tests pass.
- production deployment exposes passing health/readiness checks.
