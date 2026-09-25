"""Clone the isolated Superba web portal for another club, without touching MongoDB.

Run from the repository root:
  python ClonaMigrazione.py piercrew|tigullio|all
  python ClonaMigrazione.py sync piercrew|tigullio|all

`sync` updates shared code from Superba without deleting clone files. It preserves
the club logo, theme, database mapping, environment examples and documentation.
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "superba_web"
EXCLUDE = {".venv", ".vercel", "node_modules", "dist", "tmp", "__pycache__", "test-results", ".env", ".env.local", "tsconfig.tsbuildinfo"}
TEXT_SUFFIXES = {".py", ".ts", ".tsx", ".css", ".html", ".json", ".md", ".txt", ".example"}
SYNC_PRESERVE = {
    Path("backend/store.py"), Path("src/theme.css"), Path(".env.example"),
    Path("README.md"), Path("CLONE_INFO.json"), Path("public/logo-superba.jpg"),
    Path("public/manifest.webmanifest"), Path("public/pwa-192.png"),
    Path("public/pwa-512.png"), Path("public/pwa-maskable-192.png"),
    Path("public/pwa-maskable-512.png"),
}

CLUBS = {
    "piercrew": {
        "name": "PierCrew", "label": "PIER CREW", "logo": "logo_piercrew.jpg",
        "colors": {
            "#102b4e": "#164d32", "#173f72": "#187442", "#0b2e59": "#0c5930",
            "#e7d9b4": "#ffda45", "#fffdf6": "#fffdf1", "#f3f5f6": "#f2f8e9",
            "#142b49": "#173c2a", "#62758b": "#577061", "#dbe2e8": "#d6e4d5",
            "#254e7a": "#246a43", "#3d6085": "#478363", "#315883": "#34804f",
            "#0d294a": "#103f2b", "#194d7d": "#288147", "#e1ebf3": "#edf8db",
            "#c7d5e3": "#e6edc9", "#0c2748": "#103d2a", "#285b87": "#2a7c48",
            "#4a82b5": "#e4be28", "#081e36": "#0b2b1b",
        },
    },
    "tigullio": {
        "name": "Tigullio", "label": "TIGULLIO", "logo": "logo_tigullio.jpg",
        "colors": {
            "#102b4e": "#143d70", "#173f72": "#de6626", "#0b2e59": "#bb4f17",
            "#e7d9b4": "#ffa65a", "#fffdf6": "#fffaf4", "#f3f5f6": "#f6f2ef",
            "#142b49": "#18385e", "#62758b": "#68788b", "#dbe2e8": "#e4dcd6",
            "#254e7a": "#24558b", "#3d6085": "#4673a4", "#315883": "#316397",
            "#0d294a": "#103866", "#194d7d": "#e27432", "#e1ebf3": "#fff0e2",
            "#c7d5e3": "#f9d7bb", "#0c2748": "#10325c", "#285b87": "#d8652b",
            "#4a82b5": "#f18a42", "#081e36": "#0a274d",
        },
    },
}

PWA = {
    "superba": {"name": "Superba Subbuteo Club", "short_name": "Superba", "primary": "#173f72", "paper": "#fffdf6"},
    "piercrew": {"name": "PierCrew Subbuteo Club", "short_name": "PierCrew", "primary": "#187442", "paper": "#fffdf1"},
    "tigullio": {"name": "Tigullio Subbuteo Club", "short_name": "Tigullio", "primary": "#de6626", "paper": "#fffaf4"},
}


def _ignored(_directory: str, names: list[str]) -> set[str]:
    return {name for name in names if name in EXCLUDE or name.endswith(".pyc")}


def _club_text(content: str, relative: Path, club: dict) -> str:
    if relative.name == "theme.css":
        for old, new in club["colors"].items():
            content = content.replace(old, new)
    if relative == Path("index.html"):
        content = content.replace('content="#173f72"', f'content="{PWA[club["key"]]["primary"]}"')
    content = content.replace("SUPERBA", club["name"].upper())
    content = content.replace("Superba", club["name"])
    content = content.replace("superba", club["key"])
    content = content.replace("SUBBUTEO CLUB", f"{club['label']} · SUBBUTEO")
    if relative == Path("backend/main.py"):
        start = content.index("DESTINATIONS = {")
        end = content.index("\n}\n", start) + 2
        content = content[:start] + (
            "DESTINATIONS = {\n"
            "    'finali': os.getenv('LEGACY_FINALI_URL', ''),\n"
            "    'svizzero': os.getenv('LEGACY_SVIZZERO_URL', ''),\n"
            "    'club': os.getenv('LEGACY_CLUB_URL', ''),\n"
            "    'italiana-classica': os.getenv('LEGACY_ITALIANA_URL', ''),\n"
            "}"
        ) + content[end:]
    return content


def _write_pwa_assets(target: Path, club_key: str) -> int:
    """Create club-specific PWA metadata and icons without copying Superba branding."""
    spec = PWA[club_key]
    public = target / "public"
    logo_name = f"logo-{club_key}.jpg"
    if not (public / logo_name).is_file():
        raise FileNotFoundError(f"Logo PWA mancante: {public / logo_name}")
    manifest = {
        "id": "/", "name": spec["name"], "short_name": spec["short_name"],
        "description": f"Tornei e club del mondo {spec['short_name']}.", "lang": "it",
        "start_url": "/", "scope": "/", "display": "standalone",
        "background_color": spec["paper"], "theme_color": spec["primary"],
        "icons": [
            {"src": "/pwa-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
            {"src": "/pwa-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"},
            {"src": "/pwa-maskable-192.png", "sizes": "192x192", "type": "image/png", "purpose": "maskable"},
            {"src": "/pwa-maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
        ],
    }
    updated = 0
    manifest_path = public / "manifest.webmanifest"
    manifest_content = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    if not manifest_path.exists() or manifest_path.read_text(encoding="utf-8") != manifest_content:
        manifest_path.write_text(manifest_content, encoding="utf-8")
        updated += 1
    with Image.open(public / logo_name) as source:
        source = ImageOps.exif_transpose(source).convert("RGBA")
        for size, maskable in ((192, False), (512, False), (192, True), (512, True)):
            inset = 0.62 if maskable else 0.82
            image = Image.new("RGBA", (size, size), spec["paper"])
            logo = ImageOps.contain(source, (round(size * inset), round(size * inset)), Image.Resampling.LANCZOS)
            image.alpha_composite(logo, ((size - logo.width) // 2, (size - logo.height) // 2))
            suffix = f"pwa-{'maskable-' if maskable else ''}{size}.png"
            destination = public / suffix
            previous = destination.read_bytes() if destination.exists() else None
            from io import BytesIO
            encoded = BytesIO()
            image.save(encoded, format="PNG", optimize=True)
            if previous != encoded.getvalue():
                destination.write_bytes(encoded.getvalue())
                updated += 1
    return updated


def clone(club_key: str) -> Path:
    if club_key not in CLUBS:
        raise ValueError(f"Club sconosciuto: {club_key}")
    if not SOURCE.is_dir():
        raise FileNotFoundError(f"Cartella sorgente mancante: {SOURCE}")
    club = {**CLUBS[club_key], "key": club_key}
    target = ROOT / f"{club_key}_web"
    if target.exists():
        raise FileExistsError(f"{target} esiste già; nessun file è stato sovrascritto.")
    logo = ROOT / club["logo"]
    if not logo.is_file():
        raise FileNotFoundError(f"Logo mancante: {logo}")

    shutil.copytree(SOURCE, target, ignore=_ignored)
    try:
        for file in target.rglob("*"):
            if not file.is_file() or file.suffix not in TEXT_SUFFIXES:
                continue
            content = file.read_text(encoding="utf-8")
            relative = file.relative_to(target)
            content = _club_text(content, relative, club)
            if file.name == "README.md":
                content = (f"> Clone {club['name']} generato da ClonaMigrazione.py. Configurare un progetto Vercel e i segreti specifici del club prima della pubblicazione.\n\n" + content)
                start = content.find("Il portale è pubblicato su")
                end = content.find("\n\n", start)
                if start >= 0 and end >= 0:
                    content = content[:start] + "Questo clone non è ancora pubblicato; usare variabili d'ambiente e progetto Vercel separati. Nessun dato MongoDB viene copiato dallo script." + content[end:]
            if file.name == ".env.example":
                content += "\n# Optional links to the matching legacy apps; leave empty until verified.\nLEGACY_FINALI_URL=\nLEGACY_SVIZZERO_URL=\nLEGACY_CLUB_URL=\nLEGACY_ITALIANA_URL=\n"
            file.write_text(content, encoding="utf-8")

        # Old Superba image is replaced with the corresponding legacy club logo.
        (target / "public" / "logo-superba.jpg").unlink()
        shutil.copy2(logo, target / "public" / f"logo-{club_key}.jpg")
        _write_pwa_assets(target, club_key)
        (target / "CLONE_INFO.json").write_text(json.dumps({
            "club": club["name"], "source": "superba_web", "deployment": "not-configured",
            "mongo_writes_by_script": False,
        }, indent=2) + "\n", encoding="utf-8")
    except Exception:
        shutil.rmtree(target)
        raise
    return target


def sync(club_key: str) -> int:
    if club_key not in CLUBS:
        raise ValueError(f"Club sconosciuto: {club_key}")
    if not SOURCE.is_dir():
        raise FileNotFoundError(f"Cartella sorgente mancante: {SOURCE}")
    target = ROOT / f"{club_key}_web"
    if not target.is_dir():
        raise FileNotFoundError(f"Clone mancante: {target}. Esegui prima la clonazione iniziale.")
    club = {**CLUBS[club_key], "key": club_key}
    updated = 0
    for source_file in SOURCE.rglob("*"):
        if not source_file.is_file():
            continue
        relative = source_file.relative_to(SOURCE)
        if any(part in EXCLUDE for part in relative.parts) or source_file.name.endswith(".pyc") or relative in SYNC_PRESERVE:
            continue
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source_file.suffix in TEXT_SUFFIXES:
            content = _club_text(source_file.read_text(encoding="utf-8"), relative, club)
            if not destination.exists() or destination.read_text(encoding="utf-8") != content:
                destination.write_text(content, encoding="utf-8")
                updated += 1
        elif not destination.exists() or source_file.read_bytes() != destination.read_bytes():
            shutil.copy2(source_file, destination)
            updated += 1
    updated += _write_pwa_assets(target, club_key)
    return updated


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=[*CLUBS, "all", "sync"])
    parser.add_argument("club", nargs="?", choices=[*CLUBS, "all"])
    args = parser.parse_args()
    if args.command == "sync":
        if not args.club:
            parser.error("specifica il club: sync piercrew, sync tigullio oppure sync all")
        for club_key in (CLUBS if args.club == "all" else [args.club]):
            print(f"{club_key}: aggiornati {sync(club_key)} file condivisi")
        print("Sincronizzazione completata. Nessun file specifico del club è stato eliminato.")
        return
    if args.club:
        parser.error("per la clonazione iniziale usa soltanto piercrew, tigullio oppure all")
    for club_key in (CLUBS if args.command == "all" else [args.command]):
        print(f"Creato {clone(club_key)}")
    print("Clonazione locale completata. Configurare i segreti Vercel per ciascun club.")


if __name__ == "__main__":
    main()
