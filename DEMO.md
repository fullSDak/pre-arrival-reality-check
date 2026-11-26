# Two-minute walkthrough

This is a reproducible text walkthrough, not a recorded video. All listings, reviews, disclosures, and map notes are fictional. `as_of` is fixed at April 10, 2026; the output is not a current travel advisory.

## 0:00–0:35 — Show source-linked disagreement

From the repository directory:

```bash
python3 -m realitycheck examples/family.json
```

Or open the [generated family report](demo/family-report.md). The `Night noise` section shows **CONFLICTING REPORTS**, citing the manually labeled `review-quiet` and `review-noise` records. The tool has not verified either review or concluded what the stay is actually like.

## 0:35–1:05 — Show a disclosure and an unverified map note

The `Step-free entry` section reports a concern from fictional `host-route`, with its quoted two-step description. Old, undated and future-dated entry records remain visible but are not used in the status. The map note is fictional and marked unverified. The questions for the host are suggestions only; the tool sends nothing.

## 1:05–1:30 — Show missing evidence

```bash
python3 -m realitycheck examples/missing.json
```

Or open the [generated missing-evidence report](demo/missing-report.md). Entry and family sleep both show **INSUFFICIENT EVIDENCE**: an old entry record and an unrelated map annotation cannot fill the gaps. Missing information is not treated as a negative finding.

## 1:30–2:00 — Test and state the boundary

```bash
python3 -m unittest discover -s tests -v
```

The recorded run passed 53 tests. This local prototype processes manually annotated synthetic records using deterministic rules; it does not interpret the text, verify annotations, use AI, fetch real listings, evaluate safety/accessibility, make a booking, or contact anyone. A human must inspect the full source and decide what to do. See the [case study](CASE_STUDY.md) and [test record](TEST_RESULTS.md).
