# Cost and credential plan

## What runs free right now

The entire fixture demonstration, local interface, PDF generator, policy engine, audit chain, and test suite run locally with Python's standard library. They require no paid account, cloud deployment, or credit card.

## Primary sponsor: Nutrient

ReleaseGate's strongest sponsor fit is Nutrient's **Turn Documents Into Something People Actually Trust** challenge. Nutrient's public Data Extraction tier advertises 5,000 credits per month without a credit card. The public pricing page lists parse rates of 1 credit per page for text, 1.5 for structure, 9 for understand, and 18 for agentic mode. Schema extraction also incurs extraction work, so the live demo should process only the five one-page synthetic documents and retain the request IDs and normalized results.

Use `structure` first. Escalate only a document that cannot meet the confidence threshold; do not burn agentic credits by default.

Credential needed:

- `NUTRIENT_EXTRACTION_API_KEY`, obtained from Nutrient's Data Extraction dashboard or the hackathon event access path.
- This key is separate from a Processor API key.
- Enter it only through the masked helper. Never paste it into a command, the web interface, a committed file, a screenshot, a recording, or this chat.

Once a key is available:

```powershell
cd C:\Users\seanr\Desktop\opensearch-fieldops\releasegate
powershell -ExecutionPolicy Bypass -File scripts\run_live_invoice.ps1
```

After that succeeds, run the complete five-document proof:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_live_blocked_packet.ps1
```

The helpers remove the temporary key and save sanitized results containing request IDs, response hashes, fields, confidence, pages, and source coordinates. The packet command builds a new packet from live results and runs the policy; it does not reuse fixture fields.

## Optional sponsors

### Foxit

Only add Foxit after the Nutrient path is proven. The useful extension is an explicit, reversible PDF preparation step followed by a human-approved eSignature API call. Do not add a decorative MCP call merely to claim another sponsor. Cost and event-credit availability must be confirmed at registration.

### Doctavian

Only add Doctavian if event credentials are straightforward. The credible use is generating a conditional lien waiver from approved, source-grounded fields with branching clauses and calculated totals. Keep generated documents unsigned until a named human approves them. Cost and event-credit availability must be confirmed at registration.

## Cash exposure

Planned out-of-pocket spend: **$0**. Stop if a sponsor path requests a paid plan or credit card. The fixture path remains a complete judgeable fallback.
