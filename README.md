# Pre-Arrival Vibe & Reality Check

An independent, offline portfolio prototype for organizing **fictional**, manually annotated reviews, host disclosures, and map notes around a traveler's questions. It shows source IDs, dates, excerpts, conflicts and missing information rather than promising a stay will be quiet, accessible, convenient or suitable.

**Synthetic data only.** Do not use real listing details, traveler records, names, reviews, host messages, customer data, or employer information. The prototype cannot detect or redact private information and is not production-ready. It has no Airbnb, Zillow, mapping, review, or other integration and is not affiliated with or endorsed by any company.

## Try it

Requires Python 3.10 or later; no external packages, credentials, or network connection are needed. From the project directory:

```bash
python3 -m realitycheck examples/family.json
python3 -m realitycheck examples/missing.json
python3 -m unittest discover -s tests -v
```

The first command displays mixed fictional accounts of nighttime noise, a host-stated entry concern, and an unverified fictional map note. The second demonstrates why old or missing information is insufficient. See the actual generated [family report](demo/family-report.md) and [missing-evidence report](demo/missing-report.md), the [two-minute walkthrough](DEMO.md), and [recorded test results](TEST_RESULTS.md).

Save a report to a **new** path; existing files, including the input, are never overwritten:

```bash
python3 -m realitycheck examples/family.json --output my-report.md
```

## What the program does—and does not do

A human supplies the question, chosen topics and **manual** `supports`, `concern`, or `unclear` annotations for each source. The program does not read natural-language evidence to determine its meaning; it cannot tell whether an annotation faithfully reflects the text. It also does not automatically map the question to topics. Review the full source and the labels yourself before relying on any output. Reports quote at most the first 500 characters of each source; later context can change the meaning. Raw report text includes zero-width separators to prevent accidental links when rendered.

For each requested topic the program lists source type, source ID, supplied date, excerpt, labels, and a suggested question for the host. The suggestion is not sent. It applies these deterministic rules to dated sources whose text is not blank or control-only:

- `CONFLICTING REPORTS`: at least one manually labeled supporting and one concerning assertion.
- `CONCERN REPORTED`: one or more concerns and no supporting assertion.
- `REPORTED SUPPORT — NOT VERIFIED`: at least one supporting assertion and no concern.
- `INSUFFICIENT EVIDENCE`: no usable supporting or concerning assertion, including unclear-only or absent evidence.

Only source dates from the user-specified `as_of` date back through 365 days are used in those status rules. **The 365-day cutoff is a prototype heuristic, not a validated freshness threshold.** Older, undated and future-dated sources remain visible but do not determine the status; empty-source annotations are also displayed but not counted. `as_of` is supplied in the JSON, not updated from a clock. The bundled examples use **April 10, 2026** for reproducibility and do not represent present-day conditions. A reviewer must check the actual source and current information; a record within the window may still be stale or wrong. The program never treats the absence of evidence as evidence of absence.

The status describes annotations, not a verified fact or a fit score. Source claims may be inaccurate, incomplete, misleading, biased, or contradictory. A map note does not establish a safe, walkable, accessible, or operating route. A review does not establish noise on every night or family suitability. The tool does not scrape pages, verify reviews, look up live maps, resolve contradictions, assess risk or accessibility, predict outcomes, book a stay, or contact anyone. Travelers remain responsible for checking details with appropriate sources and deciding for themselves.

## Input schema

The [family fixture](examples/family.json) is a full example. Every top-level key is required: `listing_id`, `as_of` (`YYYY-MM-DD`), `question`, nonempty `topics`, and `sources` (which may be empty). Supported topics are `night_noise`, `step_free_entry`, `public_transit`, and `family_sleep`. Each source requires `id`, `source_type` (`review`, `host_disclosure`, or `map`), `date` (`YYYY-MM-DD` or `null`), `text`, and an `assertions` array. Each assertion has a topic and a stance (`supports`, `concern`, or `unclear`). IDs are unique after trimming; duplicate keys, duplicate topics and identical assertions are rejected. Unknown fields and invalid types are rejected. Errors produce a nonzero exit.

```json
{
  "listing_id": "synthetic-stay",
  "as_of": "2026-04-10",
  "question": "What is reported about nighttime noise?",
  "topics": ["night_noise"],
  "sources": [
    {
      "id": "fictional-review-1",
      "source_type": "review",
      "date": "2026-03-18",
      "text": "Fictional review: our room seemed quiet one night.",
      "assertions": [{"topic": "night_noise", "stance": "supports"}]
    }
  ]
}
```

Maximums: 2,000,000 input bytes; 200 sources; 12 assertions per source; 200 characters per ID; 2,000 characters per question; 8,000 characters per source text. The report escapes untrusted text to avoid rendering it as active Markdown/HTML or clickable links. The program has no runtime LLM or model, and source instructions cannot change its rules; these tests are not a general security certification.

## Context, attribution, and next steps

Airbnb's [host ground rules](https://www.airbnb.com/help/article/2895) discuss accurate listing descriptions and disclosure of noise; its [location verification explanation](https://www.airbnb.com/help/article/3542) says that process does not verify listing details, amenities, neighborhood highlights, safety, or quality. These sources inform the design, not its accuracy or endorsement. The [case study](CASE_STUDY.md) describes product decisions, test results, limitations, and proposed—not measured—adoption and success measures. The [portfolio backlog](PORTFOLIO_BACKLOG.md) tracks the 52 supplied ideas.

Sarah Dakubu Meyer selected the idea, set portfolio goals and acceptance criteria, and authorized publication. Manus AI assisted with the code, fictional examples, tests and documentation. This is independent work, not an employer or client project.
