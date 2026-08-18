# Genuine Nutrient Data Extraction proof

Validation date: 2026-08-18 UTC  
Packet: `PKT-1001-BLOCKED`  
Mode: `structure`  
Result kind: `live_nutrient_packet_evaluation`

## Outcome

ReleaseGate sent five original synthetic one-page PDFs to Nutrient Data Extraction API. Every request returned HTTP 200, produced a unique vendor request ID, and returned the required schema fields with confidence, page, and source coordinates.

The deterministic policy was then run over a new packet assembled from those live extracted fields. It returned `blocked` with exactly two findings:

1. `approval_amount_mismatch` — invoice `$12,850.00`; approval `$11,850.00`.
2. `insurance_expired` — coverage ended `2026-07-31`; evaluation date `2026-08-17`.

No fixture field values were reused in the live packet decision.

## Vendor traceability

| Synthetic document | Nutrient request ID | Fields | Processing time |
|---|---|---:|---:|
| `northstar-invoice-1048.pdf` | `GMz1wp9LNu47ZVUAAQbx` | 5 | 2,700 ms |
| `northstar-w9.pdf` | `GMz1w24r9yTHLOkAAOwi` | 2 | 2,132 ms |
| `northstar-coi-expired.pdf` | `GMz1xCJrpchdAy8AAOgy` | 3 | 2,336 ms |
| `northstar-payment-approval.pdf` | `GMz1xN54lHL2EYEAAOZC` | 4 | 2,329 ms |
| `northstar-conditional-waiver.pdf` | `GMz1xZs02pKvUYEAAOby` | 4 | 3,081 ms |

Total extracted fields: 18. All values matched the intended synthetic source documents. Field confidence ranged from 0.95 to 0.97.

## Local proof controls

The sanitized proof is stored locally at:

`artifacts/live/northstar-packet-20260818-171607Z.json`

A byte-identical, manually reviewed replay copy is bundled for judges at:

`assets/proofs/northstar-packet-20260818-reviewed.json`

File SHA-256:

`07C4DE86F625DEC33E5D223E904BD05D1CD3C01066B83B73F833649612D72A1E`

Credential-pattern scan result: zero matches for authorization headers, environment-variable names, known key prefixes, raw vendor bodies, or API-key fields. New proof runs remain ignored by Git; only the reviewed replay copy is intended for the public repository.

This evidence establishes a genuine sponsor integration. It does not claim production readiness, regulatory compliance, real payment authorization, or live signature delivery.
