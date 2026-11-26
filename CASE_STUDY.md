# Portfolio case study: Pre-arrival reality check

**Sarah Dakubu Meyer | Independent portfolio prototype | November 2026**

## Problem and intended user

A traveler may need to assess sleeping arrangements, stairs, nighttime noise, and transport before booking, yet relevant details can be scattered across host descriptions, individual reviews, and maps. For a family or a person with a specific mobility requirement, a generic “great stay” review may not answer the decisive question. This is a problem hypothesis from Sarah's supplied idea list. The prototype does not establish customer demand, willingness to pay, business value, or ROI.

The intended user is a traveler collecting context before a consequential booking decision. A reviewer should be able to trace an answer to individual source records, see disagreement, distinguish unknown information from a negative finding, and ask the host a specific follow-up question without being told what to book.

## Product decisions and implementation

The local Python CLI accepts a fictional question, explicitly selected topics, and synthetic review, host-disclosure, and map records. Each record has a source ID, date, text, and **human-supplied** topic/stance annotations. For each selected topic, the tool groups claims and reports `CONFLICTING REPORTS`, `CONCERN REPORTED`, `REPORTED SUPPORT — NOT VERIFIED`, or `INSUFFICIENT EVIDENCE`. It displays its source-ID basis, dates and excerpts; it also generates a topic-specific question for the host but never sends it.

The family example contrasts `review-quiet` with `review-noise` instead of choosing a definitive noise answer. A host's fictional two-step disclosure is shown as a concern; a map note is marked fabricated and unverified. The missing-data example refuses to promote an old entry statement or an unrelated map note into current support. The selected date is fixed in each fixture and the 365-day rule is a prototype heuristic, not an evidence-backed freshness standard. The system shows but excludes future, undated, older and empty-text records from status calculations.

A key limitation is intentional: the software does not interpret text, discover data, verify source accuracy, or check whether a person's labels match the source. Reports truncate excerpts at 500 characters, so the full input must be reviewed for context. A human may enter a misleading annotation. Human review is essential, especially for accessibility and safety. There is no live integration, autonomous tool calling, runtime AI model, account access, messaging, booking, or recommendation engine.

Airbnb's own materials illustrate why the distinction matters: its location-verification process does not verify listing details or safety [1], and its accessibility guidance defines features individually, including the route to the entrance [2]. Those sources are background, not evidence of access, approval, affiliation, or a compliant integration.

## Evaluation actually performed

On November 26, 2026, `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v` ran on Python 3.12.3: **53 tests passed**. Coverage includes source attribution, conflicting claims, missing evidence, stale/undated/future dates, exact 365-day boundary, empty source text, unrelated map data, malformed inputs, output overwrite prevention, and malicious instructions/markup in supplied text. The [test record](TEST_RESULTS.md) contains the actual run; [DEMO.md](DEMO.md) walks through two examples.

These tests check predetermined synthetic behavior; they do not measure real-world accuracy, usability, accessibility, attack resistance against every input, or business outcomes. They cannot detect a label that misrepresents its excerpt or authenticate a source. The prototype uses deterministic rules at runtime; Manus AI assisted development, but no LLM is invoked by the application.

## Deployment and adoption: proposed, not implemented

The deliverable is a local, reproducible command-line prototype—not a live consumer app. Before piloting with real travelers, validate the user problem with guests, hosts and accessibility advocates; establish consent, privacy and source permissions; and design a clear interface for viewing full original material and correcting annotations. Determine a fair process for disputed claims, changing property conditions, and host responses. Live providers would require authorized access, licensing review, accessibility testing, monitoring, privacy and retention controls, and a human-reviewed incident process. No such integration or pilot exists here.

A potential evaluation would compare reviewers using the tool with a manual baseline on a consented, labeled sample. Proposed measures include source-citation accuracy, missing-evidence recall, unsupported-claim rate, disagreement visibility, traveler comprehension, accessibility task completion, review corrections, and time to locate answers. Report sample size and uncertainty; monitor whether any group experiences misleading results. No adoption, improvement, or commercial results are claimed.

## Transferable role relevance

The artifact demonstrates evidence traceability, scoped requirements, product trade-offs, validation, and a proposed human-review/adoption plan. Those skills are relevant to marketplace experience and trust questions at Airbnb and Zillow; evidence handling at Liberty Mutual; grounded knowledge workflows at Glean; AI product and evaluation discussions at OpenAI and Anthropic; and cross-functional technical delivery at Amazon. These are portfolio positioning analogies, not claims of endorsement, partnership, employer-specific requirements, or prior deployment.

## Contribution

Sarah selected the idea, set portfolio goals and acceptance criteria, and authorized publication. Manus AI assisted with implementation, fictional fixtures, tests and documentation. This case study does not claim Sarah wrote the code, reviewed every line, operated a production system, or delivered measured outcomes.

## References

[1]: https://www.airbnb.com/help/article/3542 "Airbnb, How listing locations are verified"
[2]: https://www.airbnb.com/help/article/1961 "Airbnb, Add accessibility features to listings"
