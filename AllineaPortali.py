"""Prepara l'allineamento Superba -> PierCrew/Tigullio senza commit o deploy.

Esegui dalla root del repository, sul branch main:
    py AllineaPortali.py

Le modifiche restano intenzionalmente non committate e quindi visibili in
GitHub Desktop. DeployAllineamenti.py userà il file di stato interno creato
qui per pubblicare solo questi file dopo la revisione.
"""
from __future__ import annotations

import json
import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def run(*args: str, capture: bool = True) -> str:
    completed = subprocess.run(args, cwd=ROOT, text=True, check=True, capture_output=capture)
    return completed.stdout.strip()


def git_path(name: str) -> Path:
    value = run("git", "rev-parse", "--git-path", name)
    return (ROOT / value).resolve() if not Path(value).is_absolute() else Path(value)


def status_paths() -> list[str]:
    output = run("git", "status", "--porcelain", "-z")
    if not output:
        return []
    records = output.split("\0")
    paths: list[str] = []
    for record in records:
        if not record:
            continue
        # Rename records have a second path record; the current path is enough
        # for this controlled sync, which only adds or modifies files.
        paths.append(record[3:])
    return paths


def require_main_and_clean() -> None:
    branch = run("git", "branch", "--show-current")
    if branch != "main":
        raise RuntimeError("Apri il branch main in GitHub Desktop prima di eseguire l'allineamento.")
    if status_paths():
        raise RuntimeError("La cartella contiene già modifiche. Verificale o fai un commit prima di allineare.")
    upstream = run("git", "rev-parse", "--abbrev-ref", "@{upstream}")
    if upstream != "origin/main":
        raise RuntimeError("main deve tracciare origin/main.")
    if run("git", "rev-list", "--left-right", "--count", "main...origin/main") != "0\t0":
        raise RuntimeError("main non è allineato a origin/main. Usa Fetch origin e Pull in GitHub Desktop, poi riprova.")


def main() -> None:
    argparse.ArgumentParser(description=__doc__).parse_args()
    try:
        require_main_and_clean()
        print("Allineamento in corso: nessun commit, push o deploy verrà eseguito.")
        subprocess.run([sys.executable, "ClonaMigrazione.py", "sync", "all"], cwd=ROOT, check=True)
        changed = status_paths()
        if not changed:
            print("Nessun aggiornamento comune da preparare. GitHub Desktop resta pulito.")
            return
        state = {"base": run("git", "rev-parse", "HEAD"), "files": changed}
        destination = git_path("allineamenti-state.json")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
        print(f"Preparati {len(changed)} file. Apri GitHub Desktop, rivedili e poi esegui DeployAllineamenti.py.")
    except (subprocess.CalledProcessError, RuntimeError) as error:
        print(f"Allineamento non eseguito: {error}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
