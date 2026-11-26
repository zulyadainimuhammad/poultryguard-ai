# Measurement Query and Audit History Semantics

This document describes the read-only accepted-measurement and audit query
layer implemented in Stage 3.2.5D. It follows the approved workflow in
[`measurement_correction_and_quality_review_design.md`](measurement_correction_and_quality_review_design.md).

## Accepted measurements

An accepted-measurement query filters by exact flock ID and metric name, then
by either one exact reporting date or an inclusive start/end date range. It
returns every current eligible observation. Independent observations that
share a flock, metric and date remain separate rows.

An observation is eligible when its raw quality status is `observed`, or its
raw status is `pending_validation` with an `accepted` quality-review event.
The query exposes both the stored `quality_status` and a separately named
`effective_quality_status`. Rejected pending candidates derive effective status
`invalid`; unreviewed candidates remain `pending_validation`. Absence statuses
and invalid observations are excluded. An observation with an accepted
successor is excluded from current leaves.

Correction requests do not participate in accepted-measurement results.
Pending, rejected and invalidated requests do not change measurement results.
An approved proposal appears only after its correction observation is inserted
and linked to the target by `supersedes_observation_id`.

`get_single_accepted_measurement` returns `None` when there are no matches and
the observation when there is one. It raises `AmbiguousMeasurementError` with
the matching observation IDs when multiple eligible leaves exist. It never
chooses a row using timestamp or insertion order.

## Correction-request status

Request state is derived from its immutable event: no event means `pending`;
otherwise the status is the terminal outcome (`approved`, `rejected` or
`invalidated`). There is no mutable status column. Proposals are not accepted
measurement values.

## Audit history

An audit query accepts an exact observation ID and walks the supersession graph
in both directions using a recursive SQLite CTE. It returns the full connected
correction chain whether the supplied ID is the original, an intermediate
correction or the latest correction. The structured `MeasurementAuditHistory`
separates:

- observations in original-to-latest supersession order, including stored and
  effective quality statuses, values, units, provenance, timestamps, links and
  correction reasons;
- all requests targeting any observation in the chain, with derived request
  status and requester identity where present;
- all terminal correction events, including reviewer identity and any created
  observation link;
- all quality-review events, including reviewer identity and review reason.

Chain order follows explicit supersession links. Request history is ordered by
`requested_at` then request ID. Correction decisions are ordered by `event_at`
then event ID, and quality-review events by `reviewed_at` then event ID.
Observation recording times remain visible as `recorded_at`; `observed_at` is
measurement time and is never used as a decision timestamp.

All reads for one audit result use the same Unit-of-Work connection. The query
repository exposes no write methods. Audit operations do not update
observations, requests or events.

## Identity limitation

Requester and reviewer fields remain nullable until authentication and
authorisation exist. The local operator-recorded workflow is not secure
independent approval. A populated identity value is displayed as stored; it is
not proof of authentication or authorisation.
