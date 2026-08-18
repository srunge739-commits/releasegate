# Overnight build checklist

## Must finish

- [x] From-scratch project boundary
- [x] Synthetic closeout data
- [x] Reproducible synthetic PDFs
- [x] Blocked, review-required, and ready scenarios
- [x] Source citations and confidence values
- [x] Human confidence-review gate
- [x] Explicit release approval
- [x] Non-sending signature boundary
- [x] Tamper-evident audit chain
- [x] Nutrient Data Extraction API request boundary
- [x] Document-specific JSON Schemas
- [x] Live-response citation mapper and contract tests
- [x] Masked one-document credential check
- [x] Five-document live extraction-to-policy path
- [x] Fail-closed required-field validation
- [x] Focused tests
- [x] Local web demo
- [x] README, security notes, demo script, and Devpost draft

## Credential-dependent

- [x] Create participant Nutrient account and obtain event API key
- [x] Capture one genuine Nutrient DWS extraction result
- [x] Capture one genuine five-document Nutrient policy proof
- [x] Map the documented live extraction response shape to the packet evidence model
- [ ] Confirm whether sponsor prizes can be awarded to remote participants
- [x] Wire reviewed live proof into the web demonstration without weakening fixture portability

## Optional after the primary path is stable

- [ ] Obtain Foxit eSign developer credentials
- [ ] Implement Foxit reversible PDF preparation
- [ ] Add direct eSign request only after human approval
- [ ] Obtain Doctavian credentials
- [ ] Generate a conditional waiver with branching and calculated totals

## Go/no-go rule

No optional sponsor integration receives more than four hours before returning focus to the complete Nutrient submission.
