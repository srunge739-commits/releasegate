# ReleaseGate — 2½ minute sponsor demo

## 0:00–0:20 — The problem

“A closeout packet can contain five apparently valid documents and still support the wrong payment. ReleaseGate checks whether the evidence agrees before a lien waiver reaches a signer.”

Point out the safe fixture-mode badge and the three scenarios.

## 0:20–0:55 — Block a dangerous packet

Choose **Northstar Electrical — August Closeout** and click **Run evidence check**.

“The packet is blocked for two independent reasons: its insurance expired before today, and the invoice exceeds its documented approval by one thousand dollars.”

Open both evidence chips.

“These are not model opinions. Each finding names the document, field, page, observed value, and extraction confidence. A reviewer cannot waive either conflict from this screen; the source documents must be corrected.”

## 0:55–1:40 — Route uncertainty to a human

Choose **Atlas Fire Protection — Review Queue** and run the check.

“Here the documents agree, but Nutrient-style evidence marks the invoice total at only 68 percent confidence. ReleaseGate will not silently promote that value into a payment decision.”

Enter a reviewer name and reason, then click **Confirm after source review**.

“The human confirmation is recorded, and the same deterministic policy is replayed. The packet is now ready for approval—but it still has not been signed.”

## 1:40–2:10 — Preserve the signature boundary

Click **Prepare signature**.

“A named person explicitly approves the release. In safe demo mode this creates an idempotent, non-sending envelope record. The Foxit extension will replace only this isolated boundary; it cannot bypass the policy.”

Point out the `prepared_not_sent` notice.

## 2:10–2:30 — Prove auditability

Scroll to the audit trail.

“Evaluation, human review, policy replay, approval, and signature preparation are hash-linked. Any retrospective alteration breaks verification. ReleaseGate turns messy documents into a decision a person can inspect, defend, and safely continue.”

End on: **Evidence before signature.**

