# Project name

ReleaseGate

# Elevator pitch

ReleaseGate stops unsupported subcontractor payments before a lien waiver is signed by turning a messy closeout packet into a source-grounded, human-approved, and replayable release decision.

# Inspiration

Construction payment teams routinely reconcile an invoice, W-9, insurance certificate, approval, and lien waiver under deadline pressure. A packet may look complete while containing an expired certificate, the wrong project, a duplicate invoice, or an amount that exceeds approval. A generic document chatbot can summarize those files without establishing whether the evidence actually supports release.

We built ReleaseGate to put an explicit evidence boundary between document understanding and signature.

# What it does

ReleaseGate extracts field-level evidence from each closeout document, including confidence, page, and source location. It then runs a deterministic policy that checks:

- required-document completeness;
- vendor identity across the W-9, invoice, insurance, approval, and waiver;
- project identifiers;
- invoice, approval, and waiver amounts;
- insurance expiration;
- duplicate invoice history; and
- extraction confidence.

Hard conflicts block release and must be corrected in the source documents. Uncertain values enter a named human review queue. Even after every check passes, a person must explicitly approve before the signature boundary can be invoked.

Every transition is written to a hash-linked audit record.

# How we built it

The core is a dependency-light Python service with a deterministic fixture mode and a server-side Nutrient Data Extraction API adapter. The adapter submits a document-specific JSON Schema with citations enabled, then maps returned fields, confidence values, page references, and source coordinates into the same evidence model used by the policy. A small web interface makes the failure, review, and approval states visible.

The checked-in demonstration uses clearly labeled synthetic documents so any reviewer can run it without credentials. We validated the complete blocked scenario through five genuine Nutrient requests: 18 cited fields were assembled into a new packet and produced the expected approval mismatch and expired-insurance blockers. A manually reviewed, credential-scanned proof is bundled for read-only replay; deterministic fixtures remain separately labeled fallbacks.

The signature provider is isolated behind an interface. The checked-in demonstration intentionally uses a non-sending, idempotent fixture gateway. This lets reviewers exercise the complete control flow without sending documents or emails.

# Where Nutrient does the heavy lifting and why

Nutrient DWS converts heterogeneous business documents into source-grounded structured evidence—values, confidence, page references, and coordinates—so ReleaseGate can validate the packet deterministically and send only uncertain fields to human review.

# What makes it different

ReleaseGate does not treat an AI answer as authorization. It distinguishes model-assisted extraction, deterministic policy, human evidence review, and final release approval. The most important demo is a refusal: an expired certificate and under-approved invoice cannot be explained away or approved through the low-confidence review path.

# Accomplishments

- Three deterministic scenarios: blocked, review-required, and ready-for-approval.
- Evidence citations for every exception.
- Hard-blocker bypass prevention.
- Named human review and explicit release approval.
- Idempotent, non-sending signature preparation.
- Tamper-evident audit verification.
- Synthetic PDF generator and focused automated tests.
- Five document-specific extraction schemas and tested Nutrient citation mapping.
- Genuine five-document Nutrient validation with unique request IDs and source citations.
- No third-party dependency in fixture-mode runtime.

# What we learned

Document automation is safest when uncertainty is a routing signal rather than a prompt-engineering problem. The boundary between reversible document work and irreversible signature dispatch is also a product feature: it makes responsibility visible instead of burying it inside an agent.

# What's next

- Embed reviewed live source highlights beside the human-review queue.
- Add Foxit reversible PDF preparation and direct eSign dispatch after approval.
- Add Doctavian conditional lien-waiver generation.
- Replace the in-memory audit ledger with append-only durable storage and external timestamping.
- Add authenticated roles, document retention controls, and provider reconciliation.

# Built with

Python, Nutrient DWS, HTML, CSS, JavaScript, SHA-256
