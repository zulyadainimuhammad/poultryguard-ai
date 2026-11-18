# PoultryGuard AI — Measurement Provenance and Data Semantics

**Document status:** Architecture design specification — not yet implemented runtime behaviour
**Stage:** 3.2.2
**Branch:** `docs/measurement-provenance-contract`
**Last reviewed:** 18 November 2026

---

## 1. Purpose and scope

This document defines how PoultryGuard AI identifies, describes, timestamps, validates, tracks and preserves farm and environmental measurements.

It establishes the conceptual and data-contract foundation for:

- Environmental sensor integration and IoT data ingestion.
- Farm monitoring and operational data quality.
- Measurement correction and audit history.
- AI-powered farm intelligence based on trustworthy, traceable observations.

This is a documentation and architecture-design milestone. It does not implement database migrations, change application behaviour or introduce new runtime services. All proposed fields, payloads and schemas are design artefacts, not descriptions of the current database or API.

### Scope boundaries

**In scope:**

- Assessment of the current daily-record data model and its provenance limitations.
- A measurement dictionary for all current daily-record fields.
- A provenance model defining source categories and required metadata.
- Observation-time and recording-time semantics.
- Missing-value and data-quality status definitions.
- A correction and audit model.
- A proposed future measurement data contract with illustrative JSON examples.
- Recommended future architecture evolution.
- Migration and backward-compatibility considerations.
- Security, privacy and access-control considerations.
- Open design decisions.

**Out of scope:**

- Python application code changes.
- SQLite schema modifications or migrations.
- Sensor hardware selection or IoT protocol choice.
- Authentication or authorisation implementation.
- Alert threshold definitions or predictive models.
- Cloud provider selection.

---

## 2. Current implementation assessment

### 2.1 Runtime context

The current application is a local Streamlit MVP backed by SQLite. It is a single-user, single-process application running on a developer machine. There is no network API, no authentication and no multi-user access control.

Farm and flock records are entered manually through the Streamlit interface. Environmental measurements (temperature and humidity) are entered as optional fields within a daily production record. There is no automated sensor ingestion.

### 2.2 Current database schema

Three tables are implemented in `app/database/connection.py` and mapped to dataclasses in `app/database/models.py`.

#### `farms`

| Column | Type | Nullable | Notes |
|---|---|---|---|
| id | INTEGER | No | Auto-increment primary key |
| farm_name | TEXT | No | Required |
| farmer_name | TEXT | No | Required |
| location | TEXT | Yes | Optional free text |
| phone | TEXT | Yes | Optional |
| email | TEXT | Yes | Optional; validated by regex in service layer |
| production_type | TEXT | Yes | Optional |
| created_at | TEXT | No | SQLite `CURRENT_TIMESTAMP` at insert |
| updated_at | TEXT | No | SQLite `CURRENT_TIMESTAMP`; updated on edit |

#### `flocks`

| Column | Type | Nullable | Notes |
|---|---|---|---|
| id | INTEGER | No | Auto-increment primary key |
| farm_id | INTEGER | No | Foreign key to `farms.id` with cascade delete |
| flock_name | TEXT | No | Required |
| species | TEXT | No | Validated against allowed set in service layer |
| production_type | TEXT | Yes | Optional |
| breed | TEXT | Yes | Optional |
| initial_count | INTEGER | No | Must be > 0; enforced by CHECK and service layer |
| stocking_date | TEXT | Yes | Stored as ISO 8601 date string |
| status | TEXT | No | Default `active`; validated against allowed set |
| created_at | TEXT | No | SQLite `CURRENT_TIMESTAMP` at insert |
| updated_at | TEXT | No | SQLite `CURRENT_TIMESTAMP`; updated on edit |

#### `daily_records`

| Column | Type | Nullable | Notes |
|---|---|---|---|
| id | INTEGER | No | Auto-increment primary key |
| flock_id | INTEGER | No | Foreign key to `flocks.id` with cascade delete |
| record_date | TEXT | No | ISO 8601 date string (YYYY-MM-DD) |
| feed_kg | REAL | Yes | Optional; negative values rejected by service layer |
| water_litres | REAL | Yes | Optional; negative values rejected by service layer |
| mortality | INTEGER | No | Default 0; must be >= 0; validated against remaining population |
| average_weight_kg | REAL | Yes | Optional; must be > 0 if provided |
| temperature_c | REAL | Yes | Optional; no range constraint in current schema |
| humidity_percent | REAL | Yes | Optional; constrained to 0–100 by CHECK and service layer |
| notes | TEXT | Yes | Optional free text |
| created_at | TEXT | No | SQLite `CURRENT_TIMESTAMP` at insert |

### 2.3 Current data retrieval

Records are retrieved by `DailyRecordRepository.get_by_flock()` ordered `ASC` by `record_date, id`. This ordering is used for chronological analytics and cumulative mortality calculations.

`AnalyticsService` computes flock summaries, daily metrics and environmental summaries from these ordered records. Missing values (`None`) are excluded from averages and statistics. Genuine zero values are included.

### 2.4 Documented limitations of the current model

The following limitations are accurately recorded. They are not defects in the MVP; they are known gaps that must be addressed before production multi-user use, sensor integration or AI-powered insights.

1. **No exact observation timestamp.** `record_date` is a calendar date (YYYY-MM-DD). It does not record the time of day at which a measurement was taken. Multiple measurements taken at different times on the same day cannot be distinguished.

2. **No explicit `observed_at` field.** The schema has no field for the actual moment of observation. `created_at` records when the row was inserted into the database, not when the measurement was made.

3. **No measurement provenance.** The schema does not record whether a value was entered manually by a farmer, imported from a file or generated by a sensor device. All values are treated identically regardless of origin.

4. **No device identifier or calibration information.** There is no device registry, no sensor identifier and no calibration record. Future sensor readings cannot be traced to a specific device or its calibration state.

5. **No authenticated user identity per measurement.** The current application has no authentication. No user identity is associated with an individual measurement or record.

6. **No measurement correction history.** The schema does not support corrections. If a value is wrong, the only option is to delete and re-enter the record. There is no audit trail of what changed, when or why.

7. **`None` is not equivalent to zero.** A `NULL` value in the database means the measurement was not recorded. It does not mean the quantity was zero. The analytics layer correctly preserves this distinction; it must not be eroded.

8. **`NULL` does not distinguish missing-data reasons.** A `NULL` temperature could mean the farmer did not measure it, the sensor was unavailable, the value was invalid, or the measurement is not applicable. The current schema cannot distinguish these cases.

9. **Chronological ordering relies on `record_date` and `id`.** There is no finer-grained timestamp for ordering. If two records share the same `record_date`, ordering falls back to insertion order (`id ASC`), which may not reflect the intended sequence.

10. **Single-user local MVP.** The application is not a production multi-user cloud service. It has no API, no authentication, no farm-level access control and no network-accessible endpoint.

---

## 3. Measurement dictionary

This section defines each measurement currently stored in `daily_records`. All definitions describe the current MVP implementation. Future provenance requirements are noted separately for each measurement.

### 3.1 Mortality

| Property | Value |
|---|---|
| Field | `mortality` |
| Unit | birds (count) |
| Type | INTEGER |
| Required | Yes (defaults to 0) |
| Current validation | Must be >= 0; must not exceed remaining flock population |

**Definition.** The number of birds recorded as dead during the daily reporting period. This is a count of deaths attributed to the calendar date of the record, not a cumulative total.

**Temporal interpretation.** The value represents deaths occurring on `record_date`. The exact time of death within the day is not recorded.

**Current validation constraints.** The service layer rejects negative values. It also rejects a mortality count that would exceed the remaining flock population (initial count minus all previously recorded mortality). The database enforces `mortality >= 0` via a CHECK constraint.

**Future provenance requirements.** When multiple observations per day become possible (for example, morning and evening checks), mortality should carry an `observed_at` timestamp and a `source_type`. Corrections should preserve the original count and record the reason for the change.

**Known limitations.** The cause of death is not recorded. The time of death within the day is not recorded. A single daily record cannot represent multiple mortality events on the same day.

### 3.2 Feed consumed

| Property | Value |
|---|---|
| Field | `feed_kg` |
| Unit | kilograms (kg) |
| Type | REAL |
| Required | No (optional) |
| Current validation | Must be >= 0 if provided |

**Definition.** The total quantity of feed consumed by the flock during the recorded daily period, expressed in kilograms.

**Temporal interpretation.** Represents the aggregate feed consumption attributed to `record_date`. It does not distinguish multiple feeding events within the day.

**Current validation constraints.** The service layer rejects negative values. `NULL` is stored when the farmer does not enter a value; this is preserved as `None` throughout the analytics layer and must not be coerced to zero.

**Future provenance requirements.** Source type (manual entry or automated feeder reading), observation timestamp and recording user identity. Automated feeder systems would require device identifier and calibration metadata.

**Known limitations.** Feed type, formulation and nutritional content are not recorded. The measurement is a daily aggregate; intra-day feeding patterns are not captured.

### 3.3 Water consumed

| Property | Value |
|---|---|
| Field | `water_litres` |
| Unit | litres (L) |
| Type | REAL |
| Required | No (optional) |
| Current validation | Must be >= 0 if provided |

**Definition.** The total quantity of water consumed by the flock during the recorded daily period, expressed in litres.

**Temporal interpretation.** Represents aggregate water consumption attributed to `record_date`.

**Current validation constraints.** The service layer rejects negative values. `NULL` is preserved as `None` and must not be coerced to zero.

**Future provenance requirements.** Source type, observation timestamp, recording user identity. Automated water-meter readings would require device identifier and calibration metadata.

**Known limitations.** Water source quality and temperature are not recorded. The measurement is a daily aggregate.

### 3.4 Average bird weight

| Property | Value |
|---|---|
| Field | `average_weight_kg` |
| Unit | kilograms per bird (kg/bird) |
| Type | REAL |
| Required | No (optional) |
| Current validation | Must be > 0 if provided |

**Definition.** The recorded average weight of sampled birds on `record_date`, expressed in kilograms per bird. This is a sample-based estimate, not a whole-flock measurement.

**Temporal interpretation.** Represents a point-in-time weight measurement on `record_date`. The time of weighing within the day is not recorded.

**Current validation constraints.** The service layer rejects values <= 0. The UI flags values below 0.1 kg as potentially suspicious and prompts the user to verify the entry is in kilograms; the original value is preserved.

**Future provenance requirements.** Sample size (number of birds weighed), weighing method, observation timestamp, recording user identity. Automated weighing systems would require device identifier.

**Known limitations.** Sample size is not recorded. Weighing method (manual, automated scale) is not recorded. The value is an average; individual bird weight distribution is not captured. No biological range constraints are applied; the 0.1 kg flag is a data-entry quality check, not a species- or age-specific threshold.

### 3.5 House temperature

| Property | Value |
|---|---|
| Field | `temperature_c` |
| Unit | degrees Celsius (°C) |
| Type | REAL |
| Required | No (optional) |
| Current validation | None beyond type; no range constraint in current schema |

**Definition.** The manually recorded temperature inside the poultry house on `record_date`, expressed in degrees Celsius.

**Temporal interpretation.** Represents a single point-in-time reading attributed to `record_date`. The time of measurement within the day is not recorded. A single daily value cannot represent temperature variation throughout the day.

**Current validation constraints.** No range constraint is applied in the current schema or service layer. The UI form limits input to -10.0 °C to 60.0 °C through the `min_value` and `max_value` parameters of the Streamlit number input widget; this is a UI-level guard, not a database constraint.

**Future provenance requirements.** Observation timestamp (`observed_at`), measurement location within the house, source type (manual entry or sensor device), device identifier, calibration date and calibration reference. Sensor readings require device registry integration.

**Known limitations.** A single daily value cannot represent temperature variation throughout the day. Measurement location within the house is not recorded. No biological or husbandry thresholds are defined in the current implementation; any future threshold must have documented provenance and qualified domain review.

### 3.6 Relative humidity

| Property | Value |
|---|---|
| Field | `humidity_percent` |
| Unit | percent relative humidity (%) |
| Type | REAL |
| Required | No (optional) |
| Current validation | Must be in range 0–100 if provided; enforced by CHECK constraint and service layer |

**Definition.** The recorded relative humidity in the poultry house environment on `record_date`, expressed as a percentage.

**Temporal interpretation.** Represents a single point-in-time reading attributed to `record_date`. A single daily value cannot represent humidity variation throughout the day.

**Current validation constraints.** The database enforces `humidity_percent IS NULL OR (humidity_percent >= 0 AND humidity_percent <= 100)` via a CHECK constraint. The service layer enforces the same range and raises `ValueError` for out-of-range values.

**Future provenance requirements.** Observation timestamp, measurement location, source type, device identifier and calibration metadata. Sensor readings require device registry integration.

**Known limitations.** A single daily value cannot represent humidity variation throughout the day. Measurement location within the house is not recorded. No biological or husbandry thresholds are defined in the current implementation.

---

## 4. Provenance model

Provenance answers the question: *where did this measurement come from, and who or what produced it?*

The current implementation records no provenance. All values in `daily_records` are treated identically regardless of origin. This section defines a future extensible provenance model.

### 4.1 Source categories

#### `manual_entry`

A measurement entered directly by a farmer or farm operator through the application interface.

Mandatory metadata:
- `source_type`: `"manual_entry"`
- `recorded_at`: timestamp at which the value was entered into the system

Conditional metadata:
- `entered_by_user_id`: identity of the authenticated user who entered the value (required when authentication is implemented)
- `observed_at`: the actual time of measurement, if the farmer provides it (distinct from `recorded_at`)

#### `file_import`

A measurement imported from a spreadsheet, CSV file or other approved external dataset.

Mandatory metadata:
- `source_type`: `"file_import"`
- `import_batch_id`: identifier for the import operation
- `recorded_at`: timestamp of the import

Conditional metadata:
- `entered_by_user_id`: identity of the user who initiated the import
- `source_reference`: filename, URI or checksum of the source file
- `observed_at`: observation time as recorded in the source file, if available

#### `sensor_device`

A measurement generated automatically by an identified environmental or farm-monitoring device.

Mandatory metadata:
- `source_type`: `"sensor_device"`
- `device_id`: unique identifier of the device that produced the reading
- `observed_at`: timestamp generated by the device at the moment of measurement
- `recorded_at`: timestamp assigned by the platform when the reading is received and persisted. Device payloads may not contain `recorded_at` before ingestion; the platform assigns it on receipt.

Conditional metadata:
- `calibration_reference`: identifier of the calibration record applicable at the time of measurement
- `source_reference`: device model, firmware version or communication channel identifier

#### `system_generated`

A value calculated by an application service from identified source observations.

Mandatory metadata:
- `source_type`: `"system_generated"`
- `calculation_method`: name and version of the calculation (for example, `"cumulative_mortality_v1"`)
- `calculation_version`: version string for reproducibility
- `recorded_at`: timestamp at which the calculation was performed

Conditional metadata:
- `source_reference`: external reference string, such as a filename, URI or import source identifier, when the calculation draws on an external artefact
- `source_observation_ids`: array of observation identifiers used as inputs to the calculation. Required for reproducibility when the calculation depends on specific source observations.

### 4.2 Provenance field summary

| Field | Type | Mandatory for | Conditional for |
|---|---|---|---|
| `source_type` | enum | all | — |
| `recorded_at` | ISO 8601 timestamp | all | — |
| `observed_at` | ISO 8601 timestamp | `sensor_device` | `manual_entry`, `file_import` |
| `entered_by_user_id` | string | — | `manual_entry`, `file_import` |
| `device_id` | string | `sensor_device` | — |
| `import_batch_id` | string | `file_import` | — |
| `source_reference` | string | — | `file_import`, `sensor_device`, `system_generated` |
| `calibration_reference` | string | — | `sensor_device` |
| `calculation_method` | string | `system_generated` | — |
| `calculation_version` | string | `system_generated` | — |
| `source_observation_ids` | array of strings | — | `system_generated` |

`recorded_at` is mandatory for every observation stored by PoultryGuard AI, regardless of source type. For sensor readings, `recorded_at` is assigned by the platform when the reading is received and persisted; it is not expected to be present in the device payload before ingestion. `observed_at` is the device-generated measurement timestamp and is distinct from `recorded_at`.

`source_reference` is a string for external references such as a filename, URI, firmware version or import source identifier. `source_observation_ids` is a separate array field used by `system_generated` observations to list the specific observation identifiers used as calculation inputs; it is required for reproducibility when a calculation depends on source observations.

These fields are not present in the current database schema. They are defined here as a design contract for future implementation.

---

## 5. Observation time and recording time

### 5.1 Definitions

**Observation time (`observed_at`)** is the actual date and time at which a measurement was taken. For a manually entered temperature reading, this is the moment the farmer held the thermometer in the poultry house. For a sensor reading, this is the timestamp generated by the device at the moment of measurement.

**Recording time (`recorded_at`)** is the date and time at which the observation entered PoultryGuard AI — that is, when the row was written to the database. For manual entry, this is close to the time the farmer submitted the form. For sensor readings, this may be later than `observed_at` due to buffering, connectivity delays or batch ingestion.

**Farm reporting date (`record_date`)** is the calendar date to which a daily production record belongs. It is a date only (YYYY-MM-DD), not a timestamp. It represents the operational day being reported, which may differ from both `observed_at` and `recorded_at` when records are entered retrospectively.

### 5.2 Current state

The current schema stores only `record_date` (a date string) and `created_at` (a SQLite `CURRENT_TIMESTAMP` generated at insert time). Neither field is a reliable proxy for `observed_at`.

- `record_date` is the farmer-chosen reporting date. It may be today, yesterday or an earlier date if the farmer is catching up on records.
- `created_at` is the database insertion time. It reflects when the form was submitted, not when the measurement was taken.

**`created_at` must not be used as a substitute for `observed_at`.** They are semantically different fields.

### 5.3 ISO 8601 representation

All timestamps should be represented as ISO 8601 strings.

- Date-only values: `YYYY-MM-DD` (for example, `"2026-11-03"`)
- Timestamps with time: `YYYY-MM-DDTHH:MM:SSZ` for UTC, or `YYYY-MM-DDTHH:MM:SS+HH:MM` with explicit offset

### 5.4 Timezone handling

**UTC storage recommendation.** Machine-generated timestamps (`observed_at` for sensor readings, `recorded_at` for all sources) should be stored in UTC. UTC storage avoids ambiguity during daylight-saving transitions and simplifies chronological ordering across records.

**Farm local timezone context.** The farm's local timezone should be stored as a farm-level attribute (for example, `Africa/Lagos`, which is the IANA timezone identifier used for Nigeria including Kano, observing West Africa Time, UTC+1). This allows the platform to display timestamps in the farmer's local time without losing the UTC reference.

**`record_date` is a local date.** The farm reporting date is always interpreted in the farm's local timezone. A record dated `2026-11-03` means the third of November in the farm's local calendar, regardless of UTC offset.

### 5.5 Retrospective and late entry

When a farmer enters a record for a past date, `record_date` will be earlier than `recorded_at`. This is expected and valid. The platform must not reject or flag records solely because `record_date` is in the past.

When `observed_at` is unknown (for example, a farmer enters a temperature reading without noting the exact time), `observed_at` should be left `NULL` rather than fabricated from `record_date` or `created_at`. A missing `observed_at` is an honest representation of the data's precision.

### 5.6 Sensor readings: delayed delivery and out-of-order readings

Environmental sensors may buffer readings locally and transmit them in batches when connectivity is restored. This means:

- `recorded_at` (platform receipt time) may be hours or days after `observed_at` (device measurement time).
- Readings from the same device may arrive out of chronological order.
- A reading with an earlier `observed_at` may be inserted after a reading with a later `observed_at`.

The platform must:

1. Store `observed_at` as provided by the device, not as the receipt time.
2. Order sensor readings by `observed_at` for time-series analysis, not by `recorded_at` or database insertion order.
3. Accept and correctly place out-of-order readings without corrupting existing time-series calculations.
4. Flag readings whose `observed_at` is significantly earlier than `recorded_at` for data-quality review, without automatically rejecting them.

The threshold for flagging delayed delivery should be configurable and documented. It must not be hardcoded as a biological or operational limit.

---

## 6. Missing-value semantics

### 6.1 Current state

The current schema uses SQL `NULL` for all optional measurements that were not recorded. `NULL` is a single state that cannot distinguish between different reasons for a missing value.

The analytics layer correctly treats `NULL` as "not recorded" and excludes it from averages and statistics. Genuine zero values (for example, zero feed consumed on a fasting day) are stored as `0.0` and are included in calculations. This distinction is enforced throughout the service and analytics layers and must be preserved.

### 6.2 Proposed explicit status model

A future measurement observation model should support an explicit `quality_status` field with the following values:

| Status | `value` field | Meaning |
|---|---|---|
| `observed` | Non-null accepted measurement | A measurement was taken and the value is considered valid |
| `not_recorded` | Null | The measurement was not taken on this occasion; no value is available |
| `not_measured` | Null | The measurement is applicable but was deliberately not taken (for example, no weighing on this day) |
| `not_applicable` | Null | The measurement does not apply to this flock, species or production context |
| `device_unavailable` | Null | A sensor device was expected but was offline, disconnected or not responding |
| `invalid` | Preserve the received raw value | A value was received but failed validation; the raw value is retained for audit but must not be used as an accepted observation |
| `pending_validation` | Preserve the candidate value | A value has been received but has not yet passed automated or manual quality checks; the candidate value is retained pending review |

A genuine numeric zero is a valid measurement and is never treated as missing. A `value` of `0.0` with `quality_status = "observed"` means zero was genuinely measured. Whether `pending_validation` observations should be included in analytics is an open design decision (see Section 13.8).

### 6.3 Rules for missing-value handling

**Numeric zero is a genuine value.** A feed consumption of 0.0 kg means zero feed was recorded. It is not missing data. It must not be treated as `NULL` or excluded from calculations.

**`NULL` must not silently become zero.** Any code path that converts `NULL` to `0.0` without explicit intent is a defect. The analytics layer enforces this; it must not be weakened.

**Invalid measurements must not be silently corrected.** If a sensor returns a value outside its valid range, the value should be stored with `quality_status = "invalid"` and the original value preserved. It must not be silently replaced with a default or the previous valid reading.

**Suspicious observations should be flagged, not changed.** The current UI flags average bird weights below 0.1 kg as potentially suspicious. This is the correct pattern: flag for review, preserve the original value, do not alter the stored measurement.

**Data completeness is separate from measurement validity.** A flock with 30 out of 30 daily records entered but with temperature missing on 10 of those days has 100% record completeness and 67% temperature coverage. These are different metrics and must not be conflated.

### 6.4 Rules for specific observation scenarios

**Missing observations.** Store `NULL` (current) or `quality_status = "not_recorded"` (future). Do not interpolate or carry forward the previous value.

**Duplicate observations.** Two records for the same flock on the same `record_date` are normally prevented by `DuplicateRecordError` in `FarmService`. The service also exposes an `allow_duplicate=True` parameter that bypasses this check when explicitly required. In a future multi-source model (for example, a sensor and a manual entry for the same period), duplicates must be identified, flagged and resolved explicitly rather than silently merged.

**Delayed observations.** Accept and store with the correct `observed_at`. Flag if the delay exceeds a configurable threshold. Do not reject solely on the basis of late arrival.

**Out-of-order observations.** Accept and insert with the correct `observed_at`. Re-sort time-series queries by `observed_at` rather than insertion order. Recalculate any affected cumulative metrics.

**Invalid values.** Store with `quality_status = "invalid"` and preserve the original value. Do not silently replace with a default. Surface the invalid status to the user for review.

**Suspected sensor faults.** Flag with `quality_status = "pending_validation"` or a dedicated fault status. Preserve the raw reading. Do not use the suspect value in analytics until it has been reviewed and accepted.

**Corrected measurements.** See Section 8. The original value must be preserved; corrections are recorded as new observations linked to the original.

---

## 7. Data-quality lifecycle

A measurement observation passes through the following lifecycle stages. This model is proposed for future implementation; the current MVP does not implement a formal quality lifecycle.

```
Received / Entered
       |
       v
Validation (range, type, completeness, duplicate check)
       |
       +--[invalid]--> quality_status = "invalid" --> Flag for review
       |
       +--[suspicious]--> quality_status = "pending_validation" --> Flag for review
       |
       v
quality_status = "observed"
       |
       v
Used in analytics and summaries
       |
       +--[correction required]--> Correction event (see Section 8)
       |                           New observation inserted with supersedes_observation_id
       |                           Original observation row is never modified
       v
Original observation retained unchanged
Correction observation accepted (quality_status = "observed")
Current-value queries exclude the original via supersession relationship
Audit queries return the full chain
```

### 7.1 Validation checks

The following checks should be applied at ingestion, regardless of source type:

- **Type check:** the value is of the expected numeric type.
- **Range check:** the value is within the physically plausible range for the measurement (for example, humidity 0–100 %).
- **Completeness check:** required fields are present.
- **Duplicate check:** no existing observation for the same flock, measurement and `observed_at` (or `record_date` for daily records).
- **Chronology check:** `observed_at` is not in the future relative to `recorded_at`.
- **Consistency check:** the value is consistent with related measurements (for example, mortality does not exceed remaining population).

Validation failures must produce explicit error states, not silent defaults.

### 7.2 Coverage metrics

The `get_environmental_summary()` method in `AnalyticsService` already computes `recorded_count`, `missing_count` and `coverage_percent` for temperature and humidity. This is the foundation of a data-quality coverage view.

Future coverage metrics should extend this to:

- Coverage per measurement per time window (daily, weekly, monthly).
- Coverage per source type (manual versus sensor).
- Trend in coverage over time (is data completeness improving or declining?).

---

## 8. Correction and audit model

### 8.1 Principles

The current implementation does not support measurement corrections. If a value is incorrect, the only option is to delete the daily record and re-enter it. This destroys the original value and leaves no audit trail.

A future correction model must satisfy the following principles:

1. **Original observations are completely immutable.** The original row is never updated or deleted. Its `quality_status` remains unchanged.
2. **Corrections are new observations.** A correction is a new record with its own `observation_id`, linked to the original by `supersedes_observation_id`.
3. **Superseded state is derived, not stored.** An observation is considered superseded when an accepted correction exists that references it via `supersedes_observation_id`. No update to the original row is required or permitted to establish this relationship.
4. **Corrections carry their own provenance.** The correcting user or process, the correction timestamp and the reason for the correction are all recorded on the correction observation.
5. **The audit history is complete.** It must be possible to reconstruct the full history of a measurement by following the `supersedes_observation_id` chain.
6. **Current-value queries exclude superseded observations.** A query for the current accepted value returns the most recent observation that is not itself referenced by an accepted correction. Audit queries return the full chain.

### 8.2 Correction versus new measurement

A **correction** replaces an earlier observation for the same measurement, flock and reporting period because the earlier value was wrong. The original observation is preserved and linked.

A **new measurement** is an additional observation for a different time period or a different measurement type. It does not supersede an earlier record.

Example: a farmer enters a temperature of 38.5 °C on 2026-11-03 (observation `obs_20261103_flock42_temp_001`) but later realises the value was a transcription error and the correct value is 28.5 °C. The correction:

- Original observation `obs_20261103_flock42_temp_001`: value 38.5 °C, `quality_status = "observed"`. **This row is never modified.**
- Correction observation `obs_20261103_flock42_temp_002`: value 28.5 °C, `quality_status = "observed"`, `supersedes_observation_id = "obs_20261103_flock42_temp_001"`, `correction_reason = "Transcription error; correct value verified against written farm log."`

The original observation's superseded state is derived from the existence of `obs_20261103_flock42_temp_002`. No update to `obs_20261103_flock42_temp_001` is needed or permitted.

### 8.3 Proposed correction record fields

| Field | Description |
|---|---|
| `observation_id` | Unique identifier of this observation |
| `supersedes_observation_id` | Identifier of the observation this record replaces (`null` if this is an original observation) |
| `correction_reason` | Free-text explanation of why the correction was made (`null` for original observations) |
| `entered_by_user_id` | Identity of the user or process that submitted the correction, using the same provenance field as all other observations (`null` for original observations entered without authentication) |
| `recorded_at` | Timestamp at which the correction was stored by the platform, using the same provenance field as all other observations |
| `quality_status` | One of the seven defined statuses; `"observed"` for both original and accepted correction observations |

The seven defined `quality_status` values are: `observed`, `not_recorded`, `not_measured`, `not_applicable`, `device_unavailable`, `invalid`, `pending_validation`. `superseded` is not a `quality_status` value; supersession is a relationship derived from the correction chain.

### 8.4 Append-only model

The correction model is strictly append-only:

- No row is ever updated or deleted for correction purposes.
- Each correction inserts a new row with `supersedes_observation_id` referencing the original.
- The current accepted value for a measurement is the most recent observation whose `observation_id` is not referenced by any accepted correction's `supersedes_observation_id`.
- The full audit history is always available by following the `supersedes_observation_id` chain from the most recent correction back to the original.

This model is compatible with future audit requirements, regulatory data-retention obligations and forensic review.

---

## 9. Proposed measurement data contract

The following JSON payloads illustrate a future measurement observation model. They are **proposed design examples only**. They are not current API requests accepted by the application. The current application has no measurement observation API.

### 9.1 Manually entered temperature observation

```json
{
  "observation_id": "obs_20261103_flock42_temp_001",
  "farm_id": 7,
  "flock_id": 42,
  "record_date": "2026-11-03",
  "metric_name": "temperature_c",
  "value": 38.5,
  "unit": "degrees_celsius",
  "observed_at": null,
  "recorded_at": "2026-11-03T08:14:22Z",
  "source_type": "manual_entry",
  "entered_by_user_id": "user_farm7_operator",
  "device_id": null,
  "import_batch_id": null,
  "calibration_reference": null,
  "calculation_method": null,
  "calculation_version": null,
  "source_observation_ids": null,
  "quality_status": "observed",
  "supersedes_observation_id": null,
  "correction_reason": null,
  "notes": "Measured in the morning near the drinker line; exact observation time was not recorded."
}
```

Notes on this example:
- `observed_at` is `null` because the farmer did not record the exact measurement time. The platform does not fabricate a timestamp.
- `recorded_at` is the UTC timestamp at which the form was submitted. It is mandatory for all observations.
- `source_type` is `"manual_entry"`.
- All sensor and import fields are `null`.
- This observation is later corrected in Example 9.3.

### 9.2 Sensor-generated humidity observation

```json
{
  "observation_id": "obs_20261103_flock42_hum_sensor_0847",
  "farm_id": 7,
  "flock_id": 42,
  "record_date": "2026-11-03",
  "metric_name": "humidity_percent",
  "value": 67.4,
  "unit": "percent_relative_humidity",
  "observed_at": "2026-11-03T07:47:00Z",
  "recorded_at": "2026-11-03T07:47:35Z",
  "source_type": "sensor_device",
  "entered_by_user_id": null,
  "device_id": "sensor_rh_house1_unit03",
  "import_batch_id": null,
  "calibration_reference": "cal_rh_unit03_20261001",
  "calculation_method": null,
  "calculation_version": null,
  "source_observation_ids": null,
  "quality_status": "observed",
  "supersedes_observation_id": null,
  "correction_reason": null,
  "notes": null
}
```

Notes on this example:
- `observed_at` is the device-generated timestamp in UTC.
- `recorded_at` is 35 seconds later, reflecting network transmission time. It is assigned by the platform on receipt and is mandatory for all observations.
- `device_id` identifies the specific sensor unit.
- `calibration_reference` links to the calibration record current at the time of measurement.
- `entered_by_user_id` is `null` because no human entered this value.

### 9.3 Corrected manually entered measurement

The correction observation:

```json
{
  "observation_id": "obs_20261103_flock42_temp_002",
  "farm_id": 7,
  "flock_id": 42,
  "record_date": "2026-11-03",
  "metric_name": "temperature_c",
  "value": 28.5,
  "unit": "degrees_celsius",
  "observed_at": null,
  "recorded_at": "2026-11-04T09:03:11Z",
  "source_type": "manual_entry",
  "entered_by_user_id": "user_farm7_operator",
  "device_id": null,
  "import_batch_id": null,
  "calibration_reference": null,
  "calculation_method": null,
  "calculation_version": null,
  "source_observation_ids": null,
  "quality_status": "observed",
  "supersedes_observation_id": "obs_20261103_flock42_temp_001",
  "correction_reason": "Original value of 38.5 was a transcription error. Correct value verified against written farm log.",
  "notes": null
}
```

The original observation (unchanged — never modified):

```json
{
  "observation_id": "obs_20261103_flock42_temp_001",
  "farm_id": 7,
  "flock_id": 42,
  "record_date": "2026-11-03",
  "metric_name": "temperature_c",
  "value": 38.5,
  "unit": "degrees_celsius",
  "observed_at": null,
  "recorded_at": "2026-11-03T08:14:22Z",
  "source_type": "manual_entry",
  "entered_by_user_id": "user_farm7_operator",
  "device_id": null,
  "import_batch_id": null,
  "calibration_reference": null,
  "calculation_method": null,
  "calculation_version": null,
  "source_observation_ids": null,
  "quality_status": "observed",
  "supersedes_observation_id": null,
  "correction_reason": null,
  "notes": "Measured in the morning near the drinker line; exact observation time was not recorded."
}
```

Notes on this example:
- The original observation `obs_20261103_flock42_temp_001` retains `quality_status = "observed"`. Its row is never modified.
- Its superseded state is derived from the existence of `obs_20261103_flock42_temp_002`, which references it via `supersedes_observation_id`. No update to the original row is required.
- The correction `obs_20261103_flock42_temp_002` also has `quality_status = "observed"` and carries the `correction_reason`.
- The correction was recorded the following day (`recorded_at` is 2026-11-04).
- Current-value queries for temperature on 2026-11-03 return 28.5 °C (the correction, because it supersedes the original). Audit queries return both records.

---

## 10. Recommended future architecture

### 10.1 Evolution from daily records to measurement observations

The current `daily_records` table is a daily operational summary. It aggregates multiple measurements (feed, water, mortality, weight, temperature, humidity) into a single row per flock per day. This is appropriate for the current manual-entry MVP.

As the platform evolves towards sensor integration and higher-frequency data, a more granular model is needed. The recommended evolution has two complementary layers:

**Layer 1 — Daily operational summary (current model, retained)**

The `daily_records` table continues to serve as the farmer-facing daily summary. It captures the farmer's reported values for the day and remains the primary interface for manual entry. This layer is backward-compatible with all existing farm and flock records.

**Layer 2 — Individual measurement observations (future model)**

A new `measurement_observations` table (or equivalent) stores individual timestamped observations from any source. Each row represents a single measurement of a single metric at a specific time, with full provenance metadata.

This layer supports:
- Multiple temperature readings per day from a sensor.
- Sensor readings with device identifiers and calibration references.
- Imported historical data with batch identifiers.
- System-calculated values with method and version references.
- Corrections with full audit chains.

### 10.2 Supporting components

**Device registry.** A table or service that records each sensor device: identifier, type, location, installation date, owner and current status. Required before any sensor reading can be attributed to a specific device.

**Calibration history.** A record of calibration events for each device: calibration date, reference standard, calibration result and the identifier used in `calibration_reference` fields. Required to assess the reliability of historical sensor readings.

**Quality validation service.** A service layer that applies configurable validation rules to incoming observations: range checks, duplicate detection, chronology checks and consistency checks. Produces `quality_status` values and flags for review.

**Correction and audit service.** A service that manages the correction workflow: accepts a correction request, preserves the original observation, creates the correction record and updates the accepted-value view.

**Provenance query interface.** A query interface that can return either the current accepted value for a measurement or the full audit history, depending on the caller's intent.

### 10.3 Backward compatibility

The evolution from daily records to measurement observations must not lose existing farm and flock data.

- The `farms`, `flocks` and `daily_records` tables must be preserved.
- Existing `daily_records` rows can be treated as `manual_entry` observations with `observed_at = null` and `recorded_at` approximated from `created_at`.
- New measurement observations are stored in the new layer without modifying existing rows.
- Analytics queries can be updated to prefer the new observation layer when available, falling back to `daily_records` for historical data.

Any schema migration must be versioned, tested and reversible. Existing records must be verifiable after migration.

### 10.4 Separation of concerns

| Concern | Responsible component |
|---|---|
| Daily operational summary entry | `FarmService`, `DailyRecordRepository`, Streamlit daily-records form |
| Individual observation ingestion | Future ingestion service (manual, import, sensor) |
| Provenance metadata | Provenance model fields on each observation |
| Quality validation | Future quality validation service |
| Correction and audit | Future correction service and audit log |
| Device registry | Future device registry service |
| Calibration history | Future calibration record store |
| Analytics | `AnalyticsService` (extended to use observation layer) |
| Presentation | Streamlit UI (extended to show provenance and quality status) |

---

## 11. Migration and backward-compatibility considerations

### 11.1 Schema migration strategy

Before any schema change is applied to the production database:

1. Write a versioned migration script that applies the change and can be rolled back.
2. Test the migration against a copy of the production database.
3. Verify that all existing records are intact and queryable after migration.
4. Update repository and service code to handle both old and new schema states during the transition.
5. Update tests to cover the migrated schema.

The current SQLite schema has no migration infrastructure. Before production multi-user deployment, a migration tool (for example, Alembic for SQLAlchemy, or a custom versioned script runner) must be introduced.

### 11.2 Adding provenance fields to `daily_records`

Adding `source_type`, `observed_at` and `entered_by_user_id` columns to `daily_records` is a backward-compatible change if the new columns are nullable. Existing rows will have `NULL` in these columns, which correctly represents "provenance not recorded" for historical entries.

The analytics and service layers must handle `NULL` provenance fields gracefully and must not require provenance for existing records.

### 11.3 Introducing the observation layer

The `measurement_observations` table can be introduced as an additive change without modifying `daily_records`. Analytics queries can be updated to use the observation layer for new data while continuing to read from `daily_records` for historical data.

A migration script can optionally back-fill `measurement_observations` rows from existing `daily_records` rows, treating each non-null measurement field as a `manual_entry` observation with `observed_at = null`.

### 11.4 SQLite to PostgreSQL

The current SQLite schema is a local-development foundation. Before production multi-user deployment, migration to PostgreSQL (or an equivalent managed database) is required. Key considerations:

- SQLite `TEXT` timestamps must be migrated to PostgreSQL `TIMESTAMPTZ` columns.
- SQLite `REAL` columns map to PostgreSQL `DOUBLE PRECISION` or `NUMERIC` depending on precision requirements.
- SQLite `AUTOINCREMENT` maps to PostgreSQL `SERIAL` or `BIGSERIAL`.
- Foreign key enforcement is always on in PostgreSQL; no `PRAGMA` is needed.
- The migration must be tested end-to-end with representative data before production use.

---

## 12. Security, privacy and access-control considerations

### 12.1 Current state

The current application has no authentication, no authorisation and no network-accessible API. All data is stored locally in SQLite on the developer's machine. There are no multi-user access controls.

### 12.2 Farm-level data isolation

Before multi-user deployment, farm records must be isolated so that one farm operator cannot access another farm's data. This requires:

- Authenticated user identity associated with each session.
- Farm ownership or membership records linking users to farms.
- Repository-level filtering that enforces farm ownership on every query.
- Tests that verify cross-farm data isolation.

### 12.3 Measurement provenance and privacy

Provenance fields introduce personal data. `entered_by_user_id` identifies a specific person. This has implications for:

- **Data minimisation:** collect only the user identity fields necessary for the provenance purpose.
- **Retention:** define how long provenance records are retained and when they can be anonymised.
- **Access control:** provenance audit history should be accessible to farm owners and authorised administrators, not to all users.
- **Consent:** users should be informed that their identity is recorded against measurements they enter.

### 12.4 Sensor data security

Sensor devices introduce additional attack surface:

- Device credentials must be managed securely and rotated.
- Sensor communication channels must be authenticated and encrypted.
- Ingested sensor data must be validated before storage to prevent injection of malicious values.
- Device identifiers must not be user-controllable without authorisation.

### 12.5 Audit log integrity

The correction and audit log must be protected against tampering:

- Audit records must be append-only; no update or delete operations should be permitted on audit rows.
- Access to audit records should be restricted to authorised roles.
- In a production deployment, consider write-once storage or cryptographic chaining for high-integrity audit requirements.

---

## 13. Open design decisions and implementation dependencies

The following questions must be resolved before implementing the proposed provenance model. They are recorded here to make the design's open boundaries explicit.

### 13.1 Observation granularity

**Decision:** Should the platform support multiple observations per measurement per day (for example, hourly sensor readings), or should it continue with one daily summary per measurement?

**Dependency:** Sensor integration requirements, storage cost, analytics complexity and UI design for high-frequency data.

### 13.2 Observation identifier scheme

**Decision:** What identifier scheme should be used for `observation_id`? Options include auto-increment integers, UUIDs, or structured identifiers (as shown in the examples above).

**Dependency:** Database choice, distributed ingestion requirements and external system integration needs.

### 13.3 Timezone storage

**Decision:** Should the farm timezone be stored as an IANA timezone name (for example, `Africa/Lagos`, the IANA identifier for Nigeria) or as a UTC offset (for example, `+01:00`)? IANA names handle daylight-saving transitions correctly; UTC offsets are simpler but may be ambiguous.

**Dependency:** Target deployment regions and whether any target region observes daylight-saving time.

### 13.4 Duplicate resolution policy

**Decision:** When two observations exist for the same flock, measurement and time period (for example, a manual entry and a sensor reading for the same day), which takes precedence? Options include: manual entry overrides sensor, sensor overrides manual, both are retained with explicit conflict status, or a human review step is required.

**Dependency:** Operational workflow design and farmer trust in sensor accuracy.

### 13.5 Correction authorisation

**Decision:** Who is authorised to correct a measurement? Options include: only the original entering user, any farm operator, any farm owner, or a designated data-quality role.

**Dependency:** Authentication and authorisation design (Stage 6).

### 13.6 Calibration model depth

**Decision:** How detailed should the calibration record be? A minimal model records calibration date and a reference identifier. A fuller model records the calibration standard, the measured offset, the correction factor applied and the calibration technician.

**Dependency:** Sensor hardware selection, calibration process design and regulatory requirements.

### 13.7 Back-fill of historical records

**Decision:** Should existing `daily_records` rows be back-filled into the `measurement_observations` table as `manual_entry` observations with `observed_at = null`? This would unify the query interface but adds migration complexity.

**Dependency:** Migration strategy, analytics query design and the decision on whether to maintain `daily_records` as the primary manual-entry interface.

### 13.8 Quality status workflow

**Decision:** Should `pending_validation` observations be excluded from analytics by default, or included with a visible quality flag? Excluding them may hide data; including them may mislead users.

**Dependency:** UI design for quality status display and farmer expectations about data completeness.

---

*This document is a design specification for Stage 3.2.2 of the PoultryGuard AI development plan. It does not describe implemented runtime behaviour. All proposed fields, schemas and JSON payloads are design artefacts. See [docs/project_plan.md](../project_plan.md) and [ROADMAP.md](../../ROADMAP.md) for implementation status.*
