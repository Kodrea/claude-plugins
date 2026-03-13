#!/usr/bin/env python3
"""
Benchmark scorer for research pipeline optimization.

Scores scout JSON output against a rubric of expected findings.
Outputs a single composite score (0.0-1.0) and detailed breakdown.

Usage:
    python score.py <scout_dir> [--rubric rubric.json] [--verbose]
    python score.py research/esp32s3-benchmark/scout/
"""

import json
import sys
import re
from pathlib import Path


def load_scout_jsons(scout_dir: str) -> list[dict]:
    """Load all scout JSON files from a directory."""
    scouts = []
    for path in sorted(Path(scout_dir).glob("*.json")):
        with open(path) as f:
            scouts.append(json.load(f))
    return scouts


def load_rubric(rubric_path: str) -> dict:
    """Load the scoring rubric."""
    with open(rubric_path) as f:
        return json.load(f)


def normalize(text: str) -> str:
    """Normalize text for fuzzy matching."""
    return re.sub(r'\s+', ' ', text.lower().strip())


def score_finding_recall(findings: list[dict], expected: list[dict]) -> tuple[float, list[str]]:
    """
    Score: what fraction of expected findings were found?
    A finding is "found" if any scout finding contains the required_excerpt_fragment.
    Returns (weighted_score, list of missed finding IDs).
    """
    all_text = ""
    for f in findings:
        excerpt = f.get("raw_excerpt", "")
        summary = f.get("summary", "")
        all_text += f" {excerpt} {summary}"
    all_text_lower = all_text.lower()

    total_weight = sum(e["weight"] for e in expected)
    found_weight = 0.0
    missed = []

    for exp in expected:
        fragment = exp["required_excerpt_fragment"].lower()
        if fragment in all_text_lower:
            found_weight += exp["weight"]
        else:
            missed.append(exp["id"])

    return found_weight / total_weight if total_weight > 0 else 0.0, missed


def score_verbatim_quality(findings: list[dict], source_dir: str) -> float:
    """
    Score: are raw_excerpts actually verbatim from sources?
    Checks if each excerpt appears (substring match) in any source file.
    """
    source_texts = {}
    for path in Path(source_dir).glob("*.md"):
        with open(path) as f:
            source_texts[path.name] = f.read()
    all_source_text = "\n".join(source_texts.values())

    if not findings:
        return 0.0

    total = 0
    verbatim_count = 0
    placeholder_count = 0

    for f in findings:
        excerpt = f.get("raw_excerpt", "")
        if not excerpt:
            continue
        total += 1

        # Placeholder detection: regex to avoid false positives on markdown links/arrays
        if re.match(r'\[(?:could not|unable to|no )', excerpt.lower()):
            placeholder_count += 1
            continue

        excerpt_normalized = normalize(excerpt)
        source_normalized = normalize(all_source_text)

        words = excerpt_normalized.split()
        if len(words) < 3:
            if excerpt_normalized in source_normalized:
                verbatim_count += 1
        else:
            # Floor of 5 words to avoid short-excerpt coincidence matches
            window = max(5, int(len(words) * 0.6))
            found = False
            for i in range(len(words) - window + 1):
                chunk = " ".join(words[i:i + window])
                if chunk in source_normalized:
                    found = True
                    break
            if found:
                verbatim_count += 1

    if total == 0:
        return 0.0

    score = (verbatim_count + placeholder_count * 0.25) / total
    return score


def score_category_coverage(findings: list[dict], core_categories: list[str]) -> float:
    """
    Score: what fraction of core categories have at least one finding?
    Uses exact match after normalization (no bidirectional substring).
    """
    found_categories = set()
    for f in findings:
        cat = f.get("category", "").lower().replace(" ", "_")
        found_categories.add(cat)

    core_lower = [c.lower().replace(" ", "_") for c in core_categories]
    covered = sum(1 for core in core_lower if core in found_categories)

    return covered / len(core_lower) if core_lower else 0.0


def score_precision(findings: list[dict]) -> float:
    """
    Score: what fraction of findings have meaningful content?
    Penalizes: empty excerpts, very short summaries, missing source_location.
    """
    if not findings:
        return 0.0

    good = 0
    for f in findings:
        has_excerpt = bool(f.get("raw_excerpt", "").strip())
        has_summary = len(f.get("summary", "")) > 10
        has_source = bool(f.get("source_location", "").strip())
        has_category = bool(f.get("category", "").strip())

        quality = sum([has_excerpt, has_summary, has_source, has_category]) / 4
        good += quality

    return good / len(findings)


def score_structure_quality(scouts: list[dict]) -> float:
    """
    Score: are the scout JSONs well-structured?
    Checks for required top-level fields, valid metadata, etc.
    """
    if not scouts:
        return 0.0

    total = 0.0
    for scout in scouts:
        checks = 0
        max_checks = 6

        if "scout_id" in scout:
            checks += 1
        if "sources_processed" in scout and isinstance(scout["sources_processed"], list):
            checks += 1
        if "findings" in scout and isinstance(scout["findings"], list):
            checks += 1
        if "gaps" in scout and isinstance(scout["gaps"], list):
            checks += 1
        if "metadata" in scout and isinstance(scout["metadata"], dict):
            checks += 1
            meta = scout["metadata"]
            if all(k in meta for k in ["total_sources", "total_findings", "source_success_rate"]):
                checks += 1

        total += checks / max_checks

    return total / len(scouts)


def score_cross_references(scouts: list[dict], expected_xrefs: list[dict]) -> float:
    """
    Score: did the agent identify cross-references between sources?
    Checks if scout cross_references mention expected source pairs.
    """
    if not expected_xrefs:
        return 1.0

    all_xrefs = []
    for scout in scouts:
        all_xrefs.extend(scout.get("cross_references", []))

    if not all_xrefs:
        return 0.0

    xref_text = ""
    for xr in all_xrefs:
        for val in xr.values():
            xref_text += f" {str(val)}"
    xref_text_lower = xref_text.lower()

    found = 0
    for exp in expected_xrefs:
        from_src = exp.get("from_source", "").lower()
        to_src = exp.get("to_source", "").lower()
        relationship = exp.get("relationship", "").lower()

        if from_src in xref_text_lower and to_src in xref_text_lower:
            found += 1
        elif relationship in xref_text_lower and (from_src in xref_text_lower or to_src in xref_text_lower):
            found += 0.5

    return found / len(expected_xrefs)


def score_gap_detection(scouts: list[dict], expected_gaps: list[dict]) -> float:
    """
    Score: did the agent identify gaps in the documentation?
    Checks if scout gaps mention expected missing information.
    """
    if not expected_gaps:
        return 1.0

    all_gaps = []
    for scout in scouts:
        all_gaps.extend(scout.get("gaps", []))

    if not all_gaps:
        return 0.0

    gap_text = ""
    for g in all_gaps:
        desc = g.get("description", "") if isinstance(g, dict) else str(g)
        gap_text += f" {desc}"
    gap_text_lower = gap_text.lower()

    found = 0
    for exp in expected_gaps:
        desc = exp.get("description", "").lower()
        key_terms = [w for w in desc.split() if len(w) > 4]
        matches = sum(1 for term in key_terms if term in gap_text_lower)
        if key_terms and matches / len(key_terms) > 0.4:
            found += 1

    return found / len(expected_gaps)


def compute_composite(scores: dict, weights: dict) -> float:
    """Compute weighted composite score."""
    composite = 0.0
    for key, weight in weights.items():
        composite += scores.get(key, 0.0) * weight
    return composite


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Score research pipeline benchmark output")
    parser.add_argument("scout_dir", help="Path to scout JSON output directory")
    parser.add_argument("--rubric", default=None, help="Path to rubric.json")
    parser.add_argument("--source-dir", default=None, help="Path to benchmark source files")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed breakdown")
    parser.add_argument("--json", action="store_true", help="Output as JSON (for programmatic use)")
    args = parser.parse_args()

    script_dir = Path(__file__).parent
    rubric_path = args.rubric or str(script_dir / "rubric.json")
    source_dir = args.source_dir or str(script_dir / "sources")

    rubric = load_rubric(rubric_path)
    scouts = load_scout_jsons(args.scout_dir)

    if not scouts:
        print("ERROR: No scout JSON files found in", args.scout_dir)
        sys.exit(1)

    all_findings = []
    for scout in scouts:
        all_findings.extend(scout.get("findings", []))

    finding_recall, missed = score_finding_recall(all_findings, rubric["expected_findings"])
    verbatim = score_verbatim_quality(all_findings, source_dir)
    coverage = score_category_coverage(all_findings, rubric["core_categories"])
    precision = score_precision(all_findings)
    structure = score_structure_quality(scouts)
    cross_refs = score_cross_references(scouts, rubric.get("expected_cross_references", []))
    gaps = score_gap_detection(scouts, rubric.get("expected_gaps", []))

    scores = {
        "finding_recall": round(finding_recall, 4),
        "verbatim_quality": round(verbatim, 4),
        "category_coverage": round(coverage, 4),
        "precision": round(precision, 4),
        "structure_quality": round(structure, 4),
        "cross_references": round(cross_refs, 4),
        "gap_detection": round(gaps, 4),
    }

    composite = compute_composite(scores, rubric["scoring_weights"])

    if args.json:
        output = {
            "composite_score": round(composite, 6),
            "dimensions": scores,
            "total_findings": len(all_findings),
            "scouts_evaluated": len(scouts),
            "missed_findings": missed,
        }
        print(json.dumps(output))
    else:
        print(f"composite_score:   {composite:.6f}")
        print(f"finding_recall:    {scores['finding_recall']:.4f}")
        print(f"verbatim_quality:  {scores['verbatim_quality']:.4f}")
        print(f"category_coverage: {scores['category_coverage']:.4f}")
        print(f"precision:         {scores['precision']:.4f}")
        print(f"structure_quality: {scores['structure_quality']:.4f}")
        print(f"cross_references:  {scores['cross_references']:.4f}")
        print(f"gap_detection:     {scores['gap_detection']:.4f}")
        print(f"total_findings:    {len(all_findings)}")
        print(f"scouts_evaluated:  {len(scouts)}")

        if args.verbose and missed:
            print(f"\nmissed_findings: {', '.join(missed)}")
            for m in missed:
                exp = next((e for e in rubric["expected_findings"] if e["id"] == m), None)
                if exp:
                    print(f"  {m}: {exp['description']}")


if __name__ == "__main__":
    main()
