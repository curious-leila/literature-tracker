"""Build and verify the public recorded-run evidence artifact."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from parser import get_journal_tier, parse_file  # noqa: E402


VALID_RELEVANCE = {"high", "medium", "low"}
CASE_TITLES = [
    "翻译与历史记忆：南京大屠杀记忆翻译活动考察",
    "让“世界记忆”成为维护和平的基石",
    "顺应论视阈下的外宣英译策略研究",
]


def _analysis_fields(value: str) -> dict[str, str]:
    fields = {"reason": "", "cross_point": "", "suggestion": ""}
    prefixes = {
        "判定理由:": "reason",
        "研究交叉点:": "cross_point",
        "阅读建议:": "suggestion",
    }
    for line in value.splitlines():
        stripped = line.strip()
        for prefix, key in prefixes.items():
            if stripped.startswith(prefix):
                fields[key] = stripped[len(prefix) :].strip()
                break
    return fields


def _load_import_records(import_dir: Path) -> tuple[list[dict], list[dict]]:
    records = []
    groups: dict[str, list[dict]] = defaultdict(list)
    files = sorted(
        path for path in import_dir.iterdir() if path.is_file() and not path.name.startswith((".", "~"))
    )

    for path in files:
        for paper in parse_file(path):
            record = {
                "file": path.name,
                "dedup_key": paper.dedup_key,
                "title": paper.title,
                "source": paper.source,
            }
            records.append(record)
            groups[paper.dedup_key].append(record)

    duplicates = [
        {
            "dedup_key": key,
            "title": items[0]["title"],
            "occurrences": len(items),
            "files": sorted({item["file"] for item in items}),
        }
        for key, items in groups.items()
        if len(items) > 1
    ]
    duplicates.sort(key=lambda item: item["dedup_key"])
    return records, duplicates


def build_evidence(db_path: Path, import_dir: Path) -> dict:
    import_records, duplicates = _load_import_records(import_dir)
    import_keys = {record["dedup_key"] for record in import_records}

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT id, dedup_key, title, source, year, journal, relevance,
                   analysis, link, doi, created_at
            FROM papers
            ORDER BY id
            """
        ).fetchall()
    finally:
        conn.close()

    db_keys = {row["dedup_key"] for row in rows}
    if import_keys != db_keys:
        missing_in_db = sorted(import_keys - db_keys)
        missing_in_imports = sorted(db_keys - import_keys)
        raise ValueError(
            "Import/database mismatch: "
            f"missing_in_db={len(missing_in_db)}, "
            f"missing_in_imports={len(missing_in_imports)}"
        )

    invalid = [
        row["id"]
        for row in rows
        if row["relevance"] not in VALID_RELEVANCE or not (row["analysis"] or "").strip()
    ]
    if invalid:
        raise ValueError(f"Invalid recorded analysis for paper ids: {invalid}")

    relevance = Counter(row["relevance"] for row in rows)
    sources = Counter(row["source"] for row in rows)
    direct_links = sum(bool(row["link"]) for row in rows)
    doi_fallbacks = sum(not row["link"] and bool(row["doi"]) for row in rows)

    records = []
    case_lookup = {}
    for row in rows:
        analysis = _analysis_fields(row["analysis"])
        item = {
            "id": row["id"],
            "dedup_key": row["dedup_key"],
            "title": row["title"],
            "source": row["source"],
            "year": row["year"] or "",
            "journal": row["journal"] or "",
            "journal_tier": get_journal_tier(row["source"], row["journal"] or ""),
            "relevance": row["relevance"],
            "reason": analysis["reason"],
            "cross_point": analysis["cross_point"],
            "suggestion": analysis["suggestion"],
            "has_direct_link": bool(row["link"]),
            "has_doi_fallback": not row["link"] and bool(row["doi"]),
        }
        records.append(item)
        if row["title"] in CASE_TITLES:
            case_lookup[row["title"]] = item

    if set(case_lookup) != set(CASE_TITLES):
        raise ValueError("One or more fixed evidence cases are missing from the recorded run.")

    return {
        "schema_version": "1.0",
        "run_type": "recorded_local_run",
        "scope": {
            "input_boundary": "Manually exported CNKI RefWorks and WOS RIS files",
            "automated_steps": ["parse", "deduplicate", "classify", "format", "email"],
            "accuracy_evaluated": False,
            "cross_domain_migration_validated": False,
        },
        "model": {
            "provider": "SiliconFlow",
            "name": "Qwen/Qwen2.5-32B-Instruct",
            "prompt_version": "v8",
        },
        "summary": {
            "input_files": len({record["file"] for record in import_records}),
            "raw_records": len(import_records),
            "unique_papers": len(rows),
            "duplicate_records_removed": len(import_records) - len(rows),
            "sources": {"CNKI": sources["CNKI"], "WOS": sources["WOS"]},
            "relevance": {
                "high": relevance["high"],
                "medium": relevance["medium"],
                "low": relevance["low"],
            },
            "links": {
                "direct": direct_links,
                "doi_fallback": doi_fallbacks,
                "reachable_total": direct_links + doi_fallbacks,
                "without_link": len(rows) - direct_links - doi_fallbacks,
            },
            "recorded_at": max(row["created_at"] for row in rows),
        },
        "prompt_milestones": [
            {"version": "v1", "change": "JSON output", "result": "Qwen 7B batches failed to parse"},
            {"version": "v2", "change": "Pipe-delimited lines + examples", "result": "159/159 outputs parsed"},
            {"version": "v3", "change": "Hard constraints + negative rules", "result": "Corrected keyword-driven false positives"},
            {"version": "v8", "change": "32B model + specific-reason constraint", "result": "Current recorded run"},
        ],
        "duplicate_groups": duplicates,
        "cases": [case_lookup[title] for title in CASE_TITLES],
        "records": records,
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Verify the committed artifact is current.")
    parser.add_argument(
        "--db",
        type=Path,
        default=REPO_ROOT / "data" / "literature.db",
    )
    parser.add_argument(
        "--imports",
        type=Path,
        default=REPO_ROOT / "data" / "imports",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "web" / "public" / "run-summary.json",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    evidence = build_evidence(args.db, args.imports)
    rendered = json.dumps(evidence, ensure_ascii=False, indent=2) + "\n"

    if args.check:
        if not args.output.exists():
            print(f"Missing evidence artifact: {args.output}")
            return 1
        if args.output.read_text(encoding="utf-8") != rendered:
            print(f"Evidence artifact is stale: {args.output}")
            return 1
        print("Evidence artifact is current and internally consistent.")
        return 0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
