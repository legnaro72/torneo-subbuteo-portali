"""Pubblica un allineamento già preparato e controllato in GitHub Desktop.

Prima esegui AllineaPortali.py e verifica i file non committati. Poi:
    py DeployAllineamenti.py

Il comando non esegue ClonaMigrazione.py: legge solo il piano salvato da
AllineaPortali.py, committa quei file su main, fa push e pubblica PierCrew e
Tigullio su Vercel. Richiede Git e l'accesso Vercel già configurato.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path


ROOT = Path(__file__).resolve().parent
ORG_ID = "team_uDqC5LiUP16i7Z0U65R6BLcC"
PROJECTS = {
    "piercrew": "prj_yCDj9jHib3bjC3Gvun1MopLYWcLB",
    "tigullio": "prj_8UhuEC0hyJQ5Tsf7awkR4O9JIFDd",
}


def run(*args: str, capture: bool = True) -> str:
    completed = subprocess.run(args, cwd=ROOT, text=True, check=True, capture_output=capture)
    return completed.stdout.strip()


def git_path(name: str) -> Path:
    value = run("git", "rev-parse", "--git-path", name)
    return (ROOT / value).resolve() if not Path(value).is_absolute() else Path(value)


def status_paths() -> list[str]:
    output = run("git", "status", "--porcelain", "-z")
    return [record[3:] for record in output.split("\0") if record]


def load_plan() -> dict:
    state_file = git_path("allineamenti-state.json")
    if not state_file.is_file():
        raise RuntimeError("Nessun allineamento preparato: esegui prima AllineaPortali.py.")
    plan = json.loads(state_file.read_text(encoding="utf-8"))
    if not isinstance(plan.get("files"), list) or not plan["files"]:
        raise RuntimeError("Il piano di allineamento è vuoto o non valido.")
    return plan


@contextmanager
def vercel_project(project_id: str):
    metadata = ROOT / ".vercel" / "project.json"
    previous = metadata.read_bytes() if metadata.exists() else None
    metadata.parent.mkdir(exist_ok=True)
    metadata.write_text(json.dumps({"orgId": ORG_ID, "projectId": project_id}), encoding="utf-8")
    try:
        yield
    finally:
        if previous is None:
            metadata.unlink(missing_ok=True)
        else:
            metadata.write_bytes(previous)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--yes", action="store_true", help="salta la conferma finale")
    parser.add_argument("--message", default="chore: allinea portali", help="messaggio del commit")
    parser.add_argument("--no-vercel", action="store_true", help="fa commit e push, ma non avvia Vercel")
    options = parser.parse_args()
    try:
        if run("git", "branch", "--show-current") != "main":
            raise RuntimeError("Apri il branch main prima della pubblicazione.")
        plan = load_plan()
        if run("git", "rev-parse", "HEAD") != plan["base"]:
            raise RuntimeError("main è cambiato dopo l'allineamento. Ripeti AllineaPortali.py e verifica di nuovo.")
        actual = status_paths()
        expected = plan["files"]
        if sorted(actual) != sorted(expected):
            raise RuntimeError("I file modificati non coincidono con l'allineamento verificato. Non pubblico modifiche aggiuntive.")
        print("File pronti per la pubblicazione:")
        for path in expected:
            print(f"  - {path}")
        print(run("git", "diff", "--stat", "--", *expected))
        if not options.yes and input("Commit, push su main e deploy PierCrew/Tigullio? [s/N] ").strip().lower() not in {"s", "si", "sì", "y", "yes"}:
            print("Pubblicazione annullata: le modifiche restano non committate.")
            return
        run("git", "add", "--", *expected)
        run("git", "commit", "-m", options.message)
        run("git", "push", "origin", "main", capture=False)
        git_path("allineamenti-state.json").unlink(missing_ok=True)
        if options.no_vercel:
            print("Push completato. Deploy Vercel non richiesto.")
            return
        for club, project_id in PROJECTS.items():
            print(f"Avvio deploy Vercel: {club}…")
            with vercel_project(project_id):
                subprocess.run(["npx", "vercel", "--prod", "--yes"], cwd=ROOT, check=True)
        print("Commit, push e deploy Vercel completati.")
    except (subprocess.CalledProcessError, RuntimeError) as error:
        print(f"Pubblicazione non eseguita: {error}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
