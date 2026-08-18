# Security and live-mode boundary

ReleaseGate treats document extraction and signature preparation as separate trust zones.

## Current safe defaults

- The local server binds to loopback only.
- Fixture documents contain synthetic data and are labeled as such.
- The fixture signature gateway can only create a `prepared_not_sent` record.
- A low-confidence field can be confirmed only with a named reviewer and reason.
- A hard business conflict cannot be cleared through the confidence-review endpoint.
- API keys are loaded from environment variables and never sent to the browser.
- The audit ledger hashes the complete prior event reference, sequence, actor, action, timestamp, and payload.

## Required before a real eSignature integration

1. Add authentication and role-based authorization for reviewers and approvers.
2. Store audit events in append-only durable storage with external timestamping.
3. Encrypt uploaded documents at rest and define retention/deletion policies.
4. Add malware scanning, file-size limits, MIME validation, and PDF parser isolation.
5. Pin outbound vendor hosts and configure strict timeouts and retry policies.
6. Use secret storage rather than developer environment variables in deployment.
7. Add idempotency keys and provider-state reconciliation before creating an envelope.
8. Require an authenticated second step for final signing release.
9. Confirm signer identity and authorization from a system of record.
10. Run privacy, legal, and construction-payment policy review for the intended jurisdiction.

## Non-claims

The prototype does not claim legal compliance, payment authorization, signer identity verification, or production readiness. Its purpose is to demonstrate a safer control pattern and a reproducible sponsor integration.

