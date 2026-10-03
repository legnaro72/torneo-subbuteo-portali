"""Rebuild the Superba 2024/25 MongoDB export from its official PDF report.

The PDF is authoritative for match scores and validation. Fixture identity and
the MongoDB document shape come from the JSON export. This script never writes
to MongoDB or overwrites either input file.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from collections import Counter, defaultdict
import json
from pathlib import Path
import re

import pdfplumber


DAY = re.compile(r"^Giornata (\d+) - Girone (\d+)$")
MATCH = re.compile(r"^(.+?) (\d+) - (\d+) (.+?) UFFICIALE$")


def fixture_key(row: dict) -> tuple[str, int, str, str]:
    return (row["Girone"], int(row["Giornata"]), row["Casa"], row["Ospite"])


def load_report(path: Path) -> tuple[dict, dict]:
    matches: dict[tuple[str, int, str, str], tuple[int, int]] = {}
    standings: dict[str, tuple[int, ...]] = {}
    current_day: int | None = None
    current_group: str | None = None
    with pdfplumber.open(path) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            for raw_line in (page.extract_text() or "").splitlines():
                line = raw_line.strip()
                day = DAY.fullmatch(line)
                if day:
                    current_day = int(day.group(1))
                    current_group = f"Girone {day.group(2)}"
                    continue
                match = MATCH.fullmatch(line)
                if match:
                    if current_day is None or current_group is None:
                        raise ValueError(f"Match before day heading on page {page_number}: {line}")
                    home, home_goals, away_goals, away = match.groups()
                    key = (current_group, current_day, home, away)
                    if key in matches:
                        raise ValueError(f"Duplicate PDF match: {key}")
                    matches[key] = (int(home_goals), int(away_goals))
                    continue
                # The first page includes the official table. Its seven numeric
                # columns are points, wins, draws, losses, GF, GA, difference.
                table = re.fullmatch(r"\d+ (.+?) (\d+) (\d+) (\d+) (\d+) (\d+) (\d+) (-?\d+)", line)
                if table and current_day is None:
                    name = table.group(1)
                    if name in standings:
                        raise ValueError(f"Duplicate PDF standings team: {name}")
                    standings[name] = tuple(int(value) for value in table.groups()[1:])
    return matches, standings


def verify_standings(matches: dict, standings: dict) -> None:
    calculated = defaultdict(lambda: [0] * 7)
    for (_, _, home, away), (home_goals, away_goals) in matches.items():
        a, b = calculated[home], calculated[away]
        a[4] += home_goals
        a[5] += away_goals
        b[4] += away_goals
        b[5] += home_goals
        if home_goals > away_goals:
            a[0] += 2
            a[1] += 1
            b[3] += 1
        elif home_goals < away_goals:
            b[0] += 2
            b[1] += 1
            a[3] += 1
        else:
            a[0] += 1
            b[0] += 1
            a[2] += 1
            b[2] += 1
    for row in calculated.values():
        row[6] = row[4] - row[5]
    if set(calculated) != set(standings):
        raise ValueError(f"Standings teams differ: {set(calculated) ^ set(standings)}")
    for team, actual in calculated.items():
        expected = standings[team]
        if tuple(actual) != expected:
            raise ValueError(f"Standings disagree for {team}: PDF {expected}, calculated {actual}")


def rebuild(source: Path, report: Path, output: Path) -> None:
    documents = json.loads(source.read_text(encoding="utf-8-sig"))
    if not isinstance(documents, list) or len(documents) != 1:
        raise ValueError("Expected a one-document MongoDB Compass JSON export")
    document = documents[0]
    if "24_25" not in document.get("nome_torneo", ""):
        raise ValueError("Source JSON does not identify the 2024/25 tournament")
    pdf_matches, standings = load_report(report)
    if len(pdf_matches) != 240 or len(standings) != 16:
        raise ValueError(f"Incomplete PDF extraction: {len(pdf_matches)} matches, {len(standings)} teams")
    verify_standings(pdf_matches, standings)
    rows = document["calendario"]
    prior_partite = document["partite"]
    if len(rows) != 240 or len(prior_partite) != 240:
        raise ValueError("Expected 240 rows in both calendario and partite")
    keys = [fixture_key(row) for row in rows]
    if len(set(keys)) != len(keys) or set(keys) != set(pdf_matches):
        raise ValueError("Fixtures in calendario differ from the PDF")
    # The backup has three corrupt fixture names in its redundant 'partite'
    # array. Check that everything else lines up positionally, then rebuild
    # that array from the verified calendar instead of trusting those names.
    bad_partite = [i for i, (a, b) in enumerate(zip(rows, prior_partite))
                   if fixture_key(a) != fixture_key(b)]
    if bad_partite != [22, 154, 216]:
        raise ValueError(f"Unexpected partite fixture differences: {bad_partite}")
    calendar_changed = 0
    calendar_invalid = 0
    for row in rows:
        goals = pdf_matches[fixture_key(row)]
        if (row["GolCasa"], row["GolOspite"]) != goals or row["Valida"] is not True:
            calendar_changed += 1
        if row["Valida"] is not True:
            calendar_invalid += 1
        row["GolCasa"], row["GolOspite"] = goals
        row["Valida"] = True
    document["partite"] = deepcopy(rows)
    partite_changed = sum(a != b for a, b in zip(prior_partite, document["partite"]))
    if document["calendario"] != document["partite"]:
        raise ValueError("Calendar and matches are not identical after rebuilding")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(documents, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Created: {output}")
    print(f"PDF: {len(pdf_matches)} matches, {len(standings)} teams, official standings verified")
    print(f"calendario: {calendar_changed} rows corrected, including {calendar_invalid} previously unvalidated")
    print(f"partite: {partite_changed} rows corrected, including {len(bad_partite)} fixture names")
    print(f"Tournament: {document['nome_torneo']}; _id preserved: {document['_id']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("report", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    rebuild(args.source, args.report, args.output)
