from __future__ import annotations

import copy
import html
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from datetime import date, timedelta

from realitycheck import InputError, escape_markdown, load_input, render_report, validate_data
from realitycheck.core import MAX_INPUT_BYTES, MAX_SOURCES

ROOT = Path(__file__).resolve().parents[1]
AS_OF = date(2026, 4, 10)


def record(source_id="r1", *, topic="night_noise", stance="supports", when="2026-03-01", text="A synthetic note.", source_type="review"):
    assertions = [] if topic is None else [{"topic": topic, "stance": stance}]
    return {"id": source_id, "source_type": source_type, "date": when, "text": text, "assertions": assertions}


def data(sources=None, topics=None):
    return {
        "listing_id": "fictional-listing",
        "as_of": AS_OF.isoformat(),
        "question": "What can be said?",
        "topics": ["night_noise"] if topics is None else topics,
        "sources": [] if sources is None else sources,
    }


def section(report, title):
    return report.split(f"## {title}\n", 1)[1].split("\n## ", 1)[0]


def run_cli(*args):
    return subprocess.run([sys.executable, "-m", "realitycheck", *map(str, args)], cwd=ROOT, text=True, capture_output=True, check=False)


class EvidenceTests(unittest.TestCase):
    def test_family_fixture_reports_conflict_and_provenance(self):
        report = render_report(load_input(ROOT / "examples/family.json"))
        noise = section(report, "Night noise")
        self.assertIn("CONFLICTING REPORTS", noise)
        self.assertIn("supports: ID review-quiet", noise)
        self.assertIn("concern: ID review-noise", noise)
        self.assertIn("**Type:** review", noise)
        self.assertIn("2026-03-18", noise)
        self.assertIn("Fictional review", noise)
        self.assertIn("synthetic/manual", report)
        self.assertIn("untrusted-note", report)

    def test_missing_fixture_does_not_turn_absence_into_concern(self):
        report = render_report(load_input(ROOT / "examples/missing.json"))
        self.assertIn("INSUFFICIENT EVIDENCE", section(report, "Step-free entry"))
        self.assertIn("INSUFFICIENT EVIDENCE", section(report, "Family sleep"))
        self.assertIn("unused-map", section(report, "Unrequested and otherwise unmatched sources"))
        self.assertIn("absence is not a negative", report)

    def test_support_only(self):
        body = section(render_report(data([record()])), "Night noise")
        self.assertIn("REPORTED SUPPORT — NOT VERIFIED", body)
        self.assertIn("supports: ID r1", body)

    def test_concern_only(self):
        body = section(render_report(data([record(stance="concern")])), "Night noise")
        self.assertIn("CONCERN REPORTED", body)
        self.assertIn("concern: ID r1", body)

    def test_unclear_only_is_insufficient_with_citation(self):
        body = section(render_report(data([record(stance="unclear")])), "Night noise")
        self.assertIn("INSUFFICIENT EVIDENCE", body)
        self.assertIn("unclear: ID r1", body)

    def test_no_sources_is_insufficient_not_negative(self):
        body = section(render_report(data()), "Night noise")
        self.assertIn("INSUFFICIENT EVIDENCE", body)
        self.assertIn("absence is not a negative", body)
        self.assertIn("**Distinct relevant sources:** 0", body)

    def test_conflicting_claims_cite_both_sources(self):
        report = render_report(data([record("positive"), record("negative", stance="concern")]))
        body = section(report, "Night noise")
        self.assertIn("CONFLICTING REPORTS", body)
        self.assertIn("supports: ID positive", body)
        self.assertIn("concern: ID negative", body)
        self.assertIn("**Distinct relevant sources:** 2", body)

    def test_two_stances_from_one_source_not_counted_twice(self):
        source = record()
        source["assertions"].append({"topic": "night_noise", "stance": "concern"})
        body = section(render_report(data([source])), "Night noise")
        self.assertIn("CONFLICTING REPORTS", body)
        self.assertIn("**Distinct relevant sources:** 1; **current distinct sources:** 1", body)
        self.assertIn("supports: ID r1; concern: ID r1", body)

    def test_365_day_boundary_inclusive(self):
        exactly = (AS_OF - timedelta(days=365)).isoformat()
        older = (AS_OF - timedelta(days=366)).isoformat()
        body = section(render_report(data([record("boundary", when=exactly), record("old", when=older, stance="concern")])), "Night noise")
        self.assertIn("REPORTED SUPPORT — NOT VERIFIED", body)
        self.assertIn("current (365 days", body)
        self.assertIn("stale (366 days", body)
        basis = next(line for line in body.splitlines() if "Status basis" in line)
        self.assertIn("ID boundary", basis)
        self.assertNotIn("ID old", basis)

    def test_stale_unknown_future_excluded_and_all_shown(self):
        records = [
            record("stale", when="2024-01-01"),
            record("undated", when=None, stance="concern"),
            record("future", when="2026-04-11", stance="supports"),
        ]
        body = section(render_report(data(records)), "Night noise")
        self.assertIn("INSUFFICIENT EVIDENCE", body)
        self.assertIn("stale (", body)
        self.assertIn("unknown date", body)
        self.assertIn("future (1 days", body)
        self.assertEqual(body.count("not current evidence"), 3)
        self.assertIn("**current distinct sources:** 0", body)
        for source in records:
            self.assertIn(source["id"], body)

    def test_future_and_stale_support_do_not_conflict_with_current_concern(self):
        records = [record("old", when="2020-01-01"), record("later", when="2030-01-01"), record("today", stance="concern", when=AS_OF.isoformat())]
        body = section(render_report(data(records)), "Night noise")
        self.assertIn("CONCERN REPORTED", body)
        self.assertNotIn("CONFLICTING REPORTS", body)
        self.assertIn("concern: ID today", body)

    def test_input_order_not_date_order(self):
        records = [record("first", when="2026-04-01"), record("second", when="2025-11-01"), record("third", when="2026-03-01")]
        report = render_report(data(records))
        body = section(report, "Night noise")
        self.assertLess(body.index("**Source ID:** first"), body.index("**Source ID:** second"))
        self.assertLess(body.index("**Source ID:** second"), body.index("**Source ID:** third"))
        self.assertIn("not assumed to be chronological", report)

    def test_neutral_review_and_proximity_do_not_infer_topic(self):
        records = [record("neutral", topic=None, text="A very quiet accessible family place"), record("map", topic="public_transit", text="A stop is close; all families will sleep safely", source_type="map")]
        report = render_report(data(records))
        body = section(report, "Night noise")
        self.assertIn("INSUFFICIENT EVIDENCE", body)
        self.assertNotIn("REPORTED SUPPORT", body)
        unused = section(report, "Unrequested and otherwise unmatched sources")
        self.assertIn("neutral", unused)
        self.assertIn("map", unused)

    def test_partially_unrequested_assertions_are_listed_but_not_used(self):
        source = record("multi")
        source["assertions"].append({"topic": "family_sleep", "stance": "concern"})
        report = render_report(data([source]))
        self.assertIn("REPORTED SUPPORT — NOT VERIFIED", section(report, "Night noise"))
        self.assertIn("family_sleep: concern (not used in status)", report)
        self.assertIn("ID multi", report)

    def test_host_questions_for_all_requested_topics(self):
        report = render_report(data(topics=["night_noise", "step_free_entry", "public_transit", "family_sleep"]))
        self.assertEqual(report.count("**Question to ask the host (not sent):**"), 4)
        self.assertIn("thresholds", section(report, "Step-free entry"))
        self.assertIn("routes", section(report, "Public transit"))

    def test_truncation_marked_and_excerpt_preserved(self):
        report = render_report(data([record(text="start " + "x" * 600)]))
        self.assertIn("start ", report)
        self.assertIn("[excerpt truncated]", report)
        self.assertNotIn("x" * 600, report)


class ValidationTests(unittest.TestCase):
    def test_required_field(self):
        sample = data()
        del sample["question"]
        with self.assertRaisesRegex(InputError, "missing required"):
            validate_data(sample)

    def test_unexpected_field(self):
        sample = data()
        sample["surprise"] = True
        with self.assertRaisesRegex(InputError, "unexpected"):
            validate_data(sample)

    def test_nonempty_required_text_and_topics(self):
        for key, value in [("listing_id", "   "), ("question", ""), ("topics", [])]:
            sample = data()
            sample[key] = value
            with self.subTest(key=key), self.assertRaises(InputError):
                validate_data(sample)

    def test_wrong_types_and_disallowed_values(self):
        variants = []
        for key, value in [("listing_id", False), ("as_of", None), ("question", 22), ("topics", "night_noise"), ("sources", {})]:
            sample = data()
            sample[key] = value
            variants.append(sample)
        for key, value in [("id", None), ("source_type", "survey"), ("date", False), ("text", None), ("assertions", {})]:
            sample = data([record()])
            sample["sources"][0][key] = value
            variants.append(sample)
        sample = data([record(topic="safety")])
        variants.append(sample)
        sample = data([record(stance="positive")])
        variants.append(sample)
        for sample in variants:
            with self.subTest(sample=sample), self.assertRaises(InputError):
                validate_data(sample)

    def test_duplicate_source_id_even_with_outer_whitespace(self):
        with self.assertRaisesRegex(InputError, "duplicates"):
            validate_data(data([record("same"), record(" same ")]))

    def test_duplicate_topics(self):
        with self.assertRaisesRegex(InputError, "duplicates"):
            validate_data(data(topics=["night_noise", "night_noise"]))

    def test_duplicate_assertion(self):
        source = record()
        source["assertions"].append(copy.deepcopy(source["assertions"][0]))
        with self.assertRaisesRegex(InputError, "duplicates"):
            validate_data(data([source]))

    def test_date_format_and_calendar(self):
        for invalid in ("20260410", "2026-4-10", "2026-02-30", "2026-04-10T00:00:00", 20260410):
            sample = data()
            sample["as_of"] = invalid
            with self.subTest(invalid=invalid), self.assertRaises(InputError):
                validate_data(sample)
        source = record(when="2025-02-29")
        with self.assertRaises(InputError):
            validate_data(data([source]))
        validate_data(data([record(when="2024-02-29")]))

    def test_bounds(self):
        sample = data([record(str(i)) for i in range(MAX_SOURCES + 1)])
        with self.assertRaisesRegex(InputError, "at most"):
            validate_data(sample)
        sample = data([record(text="x" * 8001)])
        with self.assertRaisesRegex(InputError, "exceeds"):
            validate_data(sample)

    def test_duplicate_json_key_rejected_at_any_depth(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "duplicate.json"
            path.write_text('{"listing_id":"a","listing_id":"b"}', encoding="utf-8")
            with self.assertRaisesRegex(InputError, "duplicate JSON object key"):
                load_input(path)
            path.write_text('{"listing_id":"a","as_of":"2026-04-10","question":"q","topics":["night_noise"],"sources":[{"id":"x","id":"y"}]}', encoding="utf-8")
            with self.assertRaisesRegex(InputError, "duplicate JSON object key"):
                load_input(path)

    def test_reject_bad_json_utf8_numeric_nan_and_oversized_file(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "bad.json"
            for raw in (b"{", b"\xff", b'{"x": NaN}', b'{"x": 2}', b'{"x": 1.5}', b" " * (MAX_INPUT_BYTES + 1)):
                path.write_bytes(raw)
                with self.subTest(prefix=raw[:20]), self.assertRaises(InputError):
                    load_input(path)


class SecurityAndCliTests(unittest.TestCase):
    def test_hostile_text_cannot_form_markdown_html_or_autolinks(self):
        evil = "<script>alert(1)</script> [link](https://evil.invalid/x) www.evil.invalid a@evil.invalid `cmd`\n\x1b[31m \u202e"
        sample = data([record("source-1", text=evil)])
        sample["listing_id"] = "<img src=x onerror=alert(1)>"
        sample["question"] = "[go](javascript:alert(1))"
        report = render_report(sample)
        self.assertNotIn("<script>", report)
        self.assertNotIn("<img", report)
        self.assertNotIn("[link](", report)
        self.assertNotIn("javascript:", report)
        self.assertNotIn("https://evil.invalid", report)
        self.assertNotIn("www.evil.invalid", report)
        self.assertNotIn("a@evil.invalid", report)
        self.assertNotIn("\x1b", report)
        self.assertNotIn("\u202e", report)
        self.assertIn("&#60;script&#62;", report)
        self.assertIn("&#92;u000A", report)
        self.assertIn("&#92;u001B", report)
        self.assertIn("&#92;u202E", report)
        # Even linkifiers that decode entities first encounter an inserted
        # zero-width separator after URL/email punctuation.
        decoded = html.unescape(escape_markdown("https://evil.invalid www.evil.invalid a@evil.invalid"))
        self.assertNotIn("https://evil.invalid", decoded)
        self.assertNotIn("www.evil.invalid", decoded)
        self.assertNotIn("a@evil.invalid", decoded)

    def test_surrogates_and_unicode_controls_are_not_emitted(self):
        encoded = escape_markdown("x\ud800\u0085\u2028\u2066y")
        self.assertIn("&#92;uD800", encoded)
        self.assertIn("&#92;u0085", encoded)
        self.assertIn("&#92;u2028", encoded)
        self.assertIn("&#92;u2066", encoded)

    def test_cli_stdout_example(self):
        result = run_cli("examples/family.json")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.startswith("# Pre-Arrival"))
        self.assertIn("CONFLICTING REPORTS", result.stdout)
        self.assertEqual(result.stderr, "")

    def test_cli_create_new_file_and_refuse_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "new.md"
            first = run_cli("examples/family.json", "--output", output)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(first.stdout, "")
            before = output.read_bytes()
            self.assertTrue(before.startswith(b"# Pre-Arrival"))
            second = run_cli("examples/family.json", "--output", output)
            self.assertNotEqual(second.returncode, 0)
            self.assertIn("refusing to overwrite", second.stderr)
            self.assertEqual(output.read_bytes(), before)

    def test_cli_refuses_overwriting_input(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "input.json"
            original = json.dumps(data()).encode("utf-8")
            path.write_bytes(original)
            result = run_cli(path, "--output", path)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("refusing to overwrite", result.stderr)
            self.assertEqual(path.read_bytes(), original)

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks unavailable")
    def test_cli_refuses_existing_or_dangling_symlink_output(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "missing.md"
            link = Path(temp) / "out.md"
            os.symlink(target, link)
            result = run_cli("examples/missing.json", "--output", link)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("refusing to overwrite", result.stderr)
            self.assertFalse(target.exists())
            self.assertTrue(link.is_symlink())

    def test_cli_invalid_input_is_clean_error_and_does_not_create_output(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "bad.json"
            output = Path(temp) / "out.md"
            source.write_text('{"broken": true}', encoding="utf-8")
            result = run_cli(source, "--output", output)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("error:", result.stderr)
            self.assertNotIn("Traceback", result.stderr)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
