# UNG-DRACO Identification Engine Design

Date: 2026-09-12
Status: Approved design baseline
System: UNG-DRACO — Detection, Reconnaissance, Analysis, Collection & Observation

## 1. Purpose

The DRACO Identification Engine extends UNG-DRACO with computer-vision identification and tracking capabilities for authorized monitoring, reconnaissance, wildlife observation, traffic/asset observation, search-and-rescue, and related intelligence workflows. It is a component inside DRACO, not a separate UNG command system.

The engine must support:

- Ugandan and international number-plate recognition.
- Human/person detection and persistent tracking.
- Authorized face-watchlist matching.
- Animal detection, broad category classification, and species-level identification where model confidence supports it.
- Vehicle and other moving-object classification.
- Cross-frame and cross-sensor tracking.
- Confidence scoring, evidence retention, timestamping, GPS/location tagging, and model/version traceability.
- Offline edge operation plus central verification when connectivity is available.

The design explicitly excludes autonomous lethal targeting or weapon control.

## 2. Architectural Position

The Identification Engine sits inside DRACO’s existing collection, detection, fusion, watch, alert, mission, and intelligence-product pipeline.

Canonical flow:

Camera/Sensor -> Object Detection -> Specialized Identification -> Confidence Assessment -> Local/Central Match -> Persistent Track -> DRACO Correlation -> Watch/Mission Match -> Alert -> Intelligence Product -> Sanitized UNG Event

The Identification Engine must not replace DRACO’s fusion engine, ORION, SENTINEL, APOLLO, or any other UNG command function.

## 3. Recognition Services

The engine is divided into independently replaceable services with a common output contract.

### 3.1 Plate Recognition Service

Capabilities:

- Detect number plates in still images and video frames.
- Read Ugandan number plates.
- Read supported international plate formats.
- Preserve alternate OCR candidates where characters are uncertain.
- Produce normalized plate text, country/format hypothesis when known, confidence, bounding box, evidence reference, sensor metadata, and model/version metadata.
- Support permissioned lookup against an authorized vehicle/plate registry when such a registry is connected.

A plate read by itself is an observation, not proof of ownership, driver identity, or current registered status.

### 3.2 Human Detection and Face Recognition Service

Capabilities:

- Detect people without requiring identity.
- Track people across consecutive frames and, where correlation supports it, across sensors.
- Generate face embeddings only when image quality and policy allow.
- Match against authorized enrolled watchlists/databases.
- Support both local encrypted watchlist matching and central verification.
- Return candidate identity references, confidence, quality indicators, evidence references, and model/version metadata.

Face recognition must be treated as probabilistic. A model match is not automatically treated as established identity.

### 3.3 Animal and Species Recognition Service

Capabilities:

- Detect animals.
- Classify broad categories such as livestock, wildlife, pets, and birds when species confidence is insufficient.
- Identify specific species when supported by the active model and confidence threshold.
- Track repeated sightings through DRACO tracks.
- Preserve an "unknown animal" state instead of forcing a low-confidence species assignment.

### 3.4 Vehicle and Object Recognition Service

Capabilities:

- Detect and classify vehicles and other relevant moving or stationary objects.
- Support configurable classes appropriate to the approved operational mission.
- Associate recognized objects with plate reads where available.
- Maintain track continuity through occlusion when confidence remains sufficient.

### 3.5 Motion and Track Association Service

Capabilities:

- Detect motion and initiate candidate tracks.
- Associate detections across frames.
- Maintain track IDs over time.
- Merge or split tracks only when evidence supports the change.
- Hand off persistent observations into DRACO’s broader multi-domain fusion logic.

## 4. Normalized Identification Result

Every recognition service emits a common normalized structure. The logical record includes, at minimum:

- detection_id
- observation_id or collection_item_id
- object_type
- subtype or species
- plate_text and alternate candidates when applicable
- face_match_reference when applicable
- confidence
- confidence_state
- match_source: local, central, analyst, or none
- timestamp
- location/GPS when available
- sensor_id/device_id
- media_reference/evidence_reference
- model_name
- model_version
- track_id
- watch_match_reference when applicable
- policy/classification metadata

Uncertain fields remain null/unknown rather than being fabricated.

## 5. Confidence and Identity States

DRACO uses graded confidence rather than binary yes/no identity decisions.

Recommended states:

- Possible: candidate evidence exists but is weak or incomplete.
- Probable: multiple indicators or a strong model result support the candidate.
- Confirmed-by-policy: the configured evidentiary threshold has been satisfied or an authorized analyst has confirmed the result under applicable policy.

Thresholds must be configurable by recognition type and operational context. Plate OCR confidence, face-match similarity, image quality, repeated sightings, source diversity, temporal consistency, and analyst review may contribute to the final state.

Low-confidence results must not silently contaminate an established track identity.

## 6. Edge and Central Matching

DRACO must support both offline/local and online/central operation.

### 6.1 Offline Edge Mode

A watchtower node, drone, aircraft payload, vehicle node, or fixed field box may continue to:

- capture sensor input,
- detect objects,
- perform supported local identification,
- compare against a small encrypted authorized local watchlist/cache,
- maintain tracks,
- create local alerts,
- store observations and evidence in an encrypted queue.

No network connection is required for these core local functions once the necessary models and authorized cache are present.

### 6.2 Connected Mode

When connectivity is available, the edge node may send policy-approved observations/results to central DRACO for:

- fresher or larger watchlist checks,
- secondary identity verification,
- cross-camera/cross-sensor correlation,
- broader historical comparison,
- analyst review,
- intelligence-product generation.

### 6.3 Reconnection and Reconciliation

After an outage, the device synchronizes queued observations in order, preserves original timestamps, prevents duplicate ingestion, records which match source produced each decision, and reconciles local provisional matches with newer central data without erasing the original audit trail.

## 7. Watchlists and Authorized Identity Data

DRACO supports separate governed watchlists for:

- people,
- vehicles/plates,
- animals/species,
- other tracked objects.

Each watchlist entry should include:

- internal watchlist ID,
- object/person/plate reference,
- operational reason,
- owning authority or mission,
- creation date,
- expiry date or review date,
- classification,
- match threshold,
- allowed actions,
- edge-sync permission,
- status,
- audit history.

Protected source identity and biometric/watchlist material must not be exposed through ordinary DRACO APIs.

## 8. Privacy, Security, and Audit Controls

Sensitive identification data is compartmentalized.

Requirements:

- JANUS authentication and RBAC protect all identification and watchlist administration endpoints.
- VAULT manages runtime secrets and encryption keys.
- Face templates/embeddings, protected identities, source identities, full-resolution evidence, and sensitive registry records remain inside authorized DRACO storage unless policy explicitly allows release.
- Every sensitive lookup, watchlist read, watchlist modification, biometric comparison, registry query, export, analyst override, and protected-evidence access generates an append-only audit event.
- Local caches are encrypted and scoped to the field device’s approved mission.
- Edge devices support remote/automatic cache expiration and data minimization.
- Real watchlists, face embeddings, license-plate datasets, credentials, camera endpoints, and operational locations must never be committed to source control.

## 9. Data Retention

Retention is tiered by operational value and policy.

Recommended policy model:

- Routine unmatched/low-value detections: short retention, then automatic deletion.
- Mission-relevant detections: retain according to mission policy.
- Watchlist matches: retain according to authorized case/mission policy.
- Intelligence-product evidence: retain with the product’s governing retention rule.
- Legal/operational hold: prevent deletion until an authorized hold is released.
- Edge-device cache: automatically remove expired local records after successful synchronization or policy timeout.

Retention policy must be configurable and auditable.

## 10. Outbound Data Sanitization

Identification data leaving DRACO must pass a policy/sanitization stage.

Default outbound behavior should send the minimum required information. For example, downstream systems may receive:

- a track reference,
- match type,
- confidence state,
- time/location,
- mission/watch relevance,
- sanitized object metadata,
- event classification,

without receiving raw biometric templates, protected source identities, or unrestricted full-resolution evidence.

Canonical outbound path:

Identification Result -> Policy Check -> Classification/Sanitization -> DRACO Track/Intelligence Record -> HEPHA/PULSAR Event -> Authorized Consumer

Potential future event families, subject to the final event-contract plan, include:

- draco.identification.detected
- draco.plate.read
- draco.face.match_candidate
- draco.animal.identified
- draco.object.tracked

## 11. Edge Hardware Execution Profiles

The software must support multiple deployment profiles.

### 11.1 Fixed/Watchtower Profile

Optimized for continuous operation, larger storage, stronger compute, multiple cameras/sensors, and persistent connectivity where available.

### 11.2 Airborne Profile

Optimized for power, weight, thermal, bandwidth, and intermittent-link constraints on drones or aircraft.

### 11.3 Mobile/Vehicle Profile

Optimized for moving-platform GPS/time tagging, vibration-tolerant storage, changing network conditions, and local buffering.

The active software profile determines which models run locally, frame rates, image resolution, retention, and synchronization behavior.

## 12. Model Management

Recognition models are independently versioned and replaceable.

Requirements:

- Record model name/version with every identification result.
- Verify model package integrity before activation.
- Support staged deployment.
- Keep the last known-good model on each device.
- Roll back automatically when health/acceptance checks fail.
- Support model-specific thresholds and calibration metadata.
- Permit model upgrades without changing the rest of DRACO’s event/data contracts.

## 13. Failure Handling

DRACO must fail safely and preserve uncertainty.

Examples:

- OCR failure -> preserve image/evidence reference and mark plate unreadable/partial.
- Face quality too low -> keep person track without an identity claim.
- Species confidence too low -> keep broad animal class or unknown.
- Central verification unavailable -> preserve local provisional status and queue for later verification.
- Watchlist unavailable -> continue detection/tracking and record that watchlist comparison was not completed.
- Model failure -> fall back to last known-good model when available.
- Storage pressure -> apply retention priority rules before dropping mission-critical evidence.

## 14. Acceptance Tests

The Identification Engine is not accepted as operational until controlled end-to-end tests demonstrate the complete chain.

Minimum acceptance coverage:

1. Readable Ugandan number plate.
2. Partially obscured Ugandan number plate.
3. Supported international number plates.
4. Known authorized test person watchlist match.
5. Unknown person produces no forced identity.
6. Low-quality face produces provisional/no-match rather than false confirmation.
7. Multiple animal species plus unknown-animal fallback.
8. Moving/stationary vehicle and generic-object classification.
9. Object/person continuity across consecutive frames.
10. Repeated sighting association into the same DRACO track when evidence supports it.
11. Offline operation with local encrypted watchlist/cache.
12. Deferred central verification after reconnection.
13. Duplicate-upload prevention during synchronization.
14. False-match rejection at configured thresholds.
15. Audit record generation for every sensitive lookup and watchlist change.
16. Retention and automatic deletion behavior.
17. Outbound sanitization that excludes protected biometric/source data.
18. Model integrity rejection and last-known-good rollback.
19. Model/version metadata retained with every result.
20. End-to-end path from sensor input through identification, track, watch/mission match, alert, intelligence product, and sanitized event.

## 15. Operational Boundary

An identification result is an analytic observation, not an unquestionable fact. Consequential actions must use configured confidence thresholds, applicable authorization, and human/analyst review where policy requires it.

The engine provides detection, identification, correlation, tracking, alerts, and intelligence support. It does not autonomously control weapons or make lethal decisions.

## 16. Definition of Done

The DRACO Identification Engine design is ready for implementation planning when:

- this design is approved,
- implementation tasks are derived with TDD-first sequencing,
- API/data contracts are specified,
- JANUS/RBAC and audit requirements are included,
- sensitive-data handling and retention are testable,
- edge offline/online behavior is testable,
- acceptance criteria above are represented in the implementation plan.

Operational status requires real runtime acceptance evidence; design completion alone is not an operational certification.
