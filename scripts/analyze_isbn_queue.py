#!/usr/bin/env python3
"""Analyse prudemment les photographies ISBN en attente.

Le script lit les codes-barres localement, contrôle les ISBN, interroge la BnF
et Open Library, puis prépare les modifications qui seront proposées dans une
pull request. Une correspondance ambiguë n'est jamais publiée : l'image est
déplacée vers ``a_verifier`` et le rapport conserve les candidats trouvés.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import sys
import unicodedata
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]
WORKBOOK = ROOT / "inventaire_bibliotheque.xlsx"
PIPELINE = ROOT / "data" / "bibliotheque_pipeline.json"
JOURNAL = ROOT / "data" / "bibliotheque" / "imports" / "journal.csv"
REPORTS = ROOT / "data" / "bibliotheque" / "imports" / "analyses"
ISBN_ROOT = ROOT / "photos" / "bibliotheque" / "isbn"
QUEUE = ISBN_ROOT / "a_traiter"
VERIFY = ISBN_ROOT / "a_verifier"
DONE = ISBN_ROOT / "traite"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"}
MARC_NS = {"m": "info:lc/xmlns/marcxchange-v2"}
LANGUAGES = {"fre": "Français", "fra": "Français", "ita": "Italien", "eng": "Anglais"}
ROLE_CODES = {"070": "auteur", "080": "préfacier", "730": "traducteur", "440": "illustrateur"}
JOURNAL_FIELDS = [
    "date_traitement", "image_source", "image_archivee", "isbn_lu", "isbn_valide",
    "bib_id", "statut", "source_principale", "identifiant_notice", "message_controle",
]


def clean(value) -> str:
    return "" if value is None else str(value).strip()


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFD", clean(value).casefold())
    return "".join(ch for ch in value if unicodedata.category(ch) != "Mn")


def digits(value: str) -> str:
    return re.sub(r"[^0-9Xx]", "", clean(value))


def valid_isbn13(value: str) -> bool:
    value = digits(value)
    if len(value) != 13 or not value.startswith(("978", "979")):
        return False
    total = sum(int(char) * (1 if index % 2 == 0 else 3) for index, char in enumerate(value[:12]))
    return (10 - total % 10) % 10 == int(value[-1])


def isbn10_from_13(value: str) -> str:
    value = digits(value)
    if not valid_isbn13(value) or not value.startswith("978"):
        return ""
    stem = value[3:12]
    remainder = sum((10 - index) * int(char) for index, char in enumerate(stem)) % 11
    check = (11 - remainder) % 11
    return stem + ("X" if check == 10 else str(check))


def isbn_from_filename(path: Path) -> str:
    for candidate in re.findall(r"(?:97[89][0-9\s_-]{9,20}[0-9])", path.stem):
        value = digits(candidate)
        if valid_isbn13(value):
            return value
    return ""


def isbn_from_image(path: Path) -> str:
    """Lit un EAN-13 avec zbar après quelques transformations sans perte."""
    try:
        from PIL import Image, ImageOps
        if path.suffix.lower() in {".heic", ".heif"}:
            from pillow_heif import register_heif_opener
            register_heif_opener()
        from pyzbar.pyzbar import decode
    except ImportError as error:
        raise RuntimeError("Dépendances de lecture des codes-barres absentes.") from error

    with Image.open(path) as source:
        source.load()
        variants = [source.copy(), ImageOps.autocontrast(ImageOps.grayscale(source))]
        variants.extend(image.resize((image.width * 2, image.height * 2)) for image in list(variants))
        for image in variants:
            for angle in (0, 90, 180, 270):
                rotated = image if angle == 0 else image.rotate(angle, expand=True)
                for symbol in decode(rotated):
                    value = digits(symbol.data.decode("ascii", errors="ignore"))
                    if valid_isbn13(value):
                        return value
    return isbn_from_filename(path)


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "Trinketa-ISBN/1.0 (bibliographic pipeline)"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def subfields(record: ET.Element, tag: str, code: str) -> list[str]:
    return [clean(node.text) for node in record.findall(f"m:datafield[@tag='{tag}']/m:subfield[@code='{code}']", MARC_NS) if clean(node.text)]


def first_subfield(record: ET.Element, tag: str, code: str) -> str:
    values = subfields(record, tag, code)
    return values[0] if values else ""


def bnf_candidates(isbn: str) -> list[dict]:
    query = urllib.parse.quote(f'bib.isbn all "{isbn}"')
    url = f"https://catalogue.bnf.fr/api/SRU?version=1.2&operation=searchRetrieve&query={query}&recordSchema=unimarcxchange&maximumRecords=10"
    root = ET.fromstring(fetch(url))
    candidates = []
    for record in root.findall(".//m:record", MARC_NS):
        recorded_isbns = {digits(value) for value in subfields(record, "010", "a") + subfields(record, "073", "a")}
        if isbn not in recorded_isbns:
            continue
        title = first_subfield(record, "200", "a")
        if not title:
            continue
        author_parts = []
        for field in record.findall("m:datafield[@tag='700']", MARC_NS):
            surname = next((clean(n.text) for n in field.findall("m:subfield[@code='a']", MARC_NS) if clean(n.text)), "")
            given = next((clean(n.text) for n in field.findall("m:subfield[@code='b']", MARC_NS) if clean(n.text)), "")
            if surname:
                author_parts.append(", ".join(part for part in (surname, given) if part))
        responsibilities = []
        for field in record.findall("m:datafield[@tag='702']", MARC_NS):
            surname = next((clean(n.text) for n in field.findall("m:subfield[@code='a']", MARC_NS) if clean(n.text)), "")
            given = next((clean(n.text) for n in field.findall("m:subfield[@code='b']", MARC_NS) if clean(n.text)), "")
            role_code = next((clean(n.text) for n in field.findall("m:subfield[@code='4']", MARC_NS) if clean(n.text)), "")
            if surname:
                person = ", ".join(part for part in (surname, given) if part)
                responsibilities.append(f"{person} [{ROLE_CODES.get(role_code, role_code or 'autre responsabilité')}]")
        date_raw = first_subfield(record, "210", "d") or first_subfield(record, "214", "d")
        year_match = re.search(r"\b(1[0-9]{3}|20[0-9]{2})\b", date_raw)
        extent = first_subfield(record, "215", "a")
        pages_match = re.search(r"(\d+)\s*p\.", extent)
        subjects = []
        for field in record.findall("m:datafield[@tag='606']", MARC_NS):
            parts = [clean(node.text) for node in field.findall("m:subfield", MARC_NS) if node.get("code") in {"a", "x", "y", "z"} and clean(node.text)]
            if parts:
                subjects.append(" — ".join(parts))
        ark = clean(record.get("id"))
        if ark.startswith("ark:/"):
            ark_url = f"https://catalogue.bnf.fr/{ark}"
        else:
            ark_url = ""
        language_code = first_subfield(record, "101", "a")
        candidates.append({
            "ISBN": isbn,
            "ISBN_13": isbn,
            "ISBN_10": isbn10_from_13(isbn),
            "Auteur_editeur_scientifique": "; ".join(author_parts),
            "Autre_responsabilite": "; ".join(responsibilities),
            "Titre": title,
            "Sous_titre": first_subfield(record, "200", "e"),
            "Type_document": "Ouvrage",
            "Editeur": first_subfield(record, "210", "c") or first_subfield(record, "214", "c"),
            "Lieu_publication": first_subfield(record, "210", "a") or first_subfield(record, "214", "a"),
            "Date_publication": year_match.group(1) if year_match else date_raw,
            "Collection": first_subfield(record, "225", "a"),
            "Nbr_pages": int(pages_match.group(1)) if pages_match else "",
            "Dimensions": first_subfield(record, "215", "d"),
            "Langue": LANGUAGES.get(language_code, language_code),
            "Sujet": "; ".join(subjects),
            "Mots_cles": "; ".join(subjects),
            "Source_notice": "BnF",
            "Identifiant_notice": ark,
            "URL_notice": ark_url,
            "Statut_notice": "Proposition à valider",
            "Confiance_notice": "Élevée",
            "Publie": "Oui",
        })
    unique = {}
    for candidate in candidates:
        signature = (normalize(candidate["Titre"]), normalize(candidate["Auteur_editeur_scientifique"]), clean(candidate["Date_publication"]))
        unique.setdefault(signature, candidate)
    return list(unique.values())


def openlibrary_candidate(isbn: str) -> dict | None:
    key = f"ISBN:{isbn}"
    url = "https://openlibrary.org/api/books?" + urllib.parse.urlencode({"bibkeys": key, "format": "json", "jscmd": "data"})
    data = json.loads(fetch(url))
    item = data.get(key)
    if not item:
        return None
    authors = [clean(author.get("name")) for author in item.get("authors", []) if clean(author.get("name"))]
    publishers = [clean(pub.get("name")) for pub in item.get("publishers", []) if clean(pub.get("name"))]
    places = [clean(place.get("name")) for place in item.get("publish_places", []) if clean(place.get("name"))]
    subjects = [clean(subject.get("name")) for subject in item.get("subjects", []) if clean(subject.get("name"))][:12]
    return {
        "ISBN": isbn, "ISBN_13": isbn, "ISBN_10": isbn10_from_13(isbn),
        "Auteur_editeur_scientifique": "; ".join(authors), "Titre": clean(item.get("title")),
        "Type_document": "Ouvrage", "Editeur": "; ".join(publishers),
        "Lieu_publication": "; ".join(places), "Date_publication": clean(item.get("publish_date")),
        "Nbr_pages": item.get("number_of_pages") or "", "Sujet": "; ".join(subjects),
        "Mots_cles": "; ".join(subjects), "Source_notice": "Open Library",
        "Identifiant_notice": item.get("key", ""), "URL_notice": item.get("url", ""),
        "Statut_notice": "Proposition à valider", "Confiance_notice": "Moyenne", "Publie": "Oui",
    }


def choose_candidate(isbn: str) -> tuple[dict | None, list[dict], str]:
    errors = []
    try:
        bnf = bnf_candidates(isbn)
    except Exception as error:  # une source indisponible ne doit pas inventer une notice
        bnf = []
        errors.append(f"BnF indisponible : {error}")
    try:
        openlibrary = openlibrary_candidate(isbn)
    except Exception as error:
        openlibrary = None
        errors.append(f"Open Library indisponible : {error}")
    if len(bnf) == 1:
        return bnf[0], bnf, "; ".join(errors)
    if len(bnf) > 1 and openlibrary:
        matches = [candidate for candidate in bnf if normalize(candidate["Titre"]) == normalize(openlibrary["Titre"])]
        if len(matches) == 1:
            matches[0]["Confiance_notice"] = "Moyenne"
            return matches[0], bnf, "Plusieurs notices BnF départagées par Open Library."
    if len(bnf) > 1:
        return None, bnf, "Plusieurs notices distinctes portent cet ISBN."
    if openlibrary and openlibrary.get("Titre"):
        return openlibrary, [openlibrary], "; ".join(errors)
    return None, [], "; ".join(errors) or "Aucune notice trouvée dans les sources interrogées."


def existing_state() -> tuple[set[int], set[str]]:
    ids, isbns = set(), set()
    if WORKBOOK.exists():
        wb = load_workbook(WORKBOOK, read_only=True, data_only=True)
        ws = wb["Catalogue"]
        rows = ws.iter_rows(values_only=True)
        headers = [clean(value) for value in next(rows)]
        for values in rows:
            row = dict(zip(headers, values))
            match = re.fullmatch(r"BIB-(\d+)", clean(row.get("ID")).upper())
            if match:
                ids.add(int(match.group(1)))
            for field in ("ISBN", "ISBN_13"):
                value = digits(row.get(field))
                if valid_isbn13(value):
                    isbns.add(value)
    records = json.loads(PIPELINE.read_text(encoding="utf-8")) if PIPELINE.exists() else []
    for row in records:
        match = re.fullmatch(r"BIB-(\d+)", clean(row.get("ID")).upper())
        if match:
            ids.add(int(match.group(1)))
        value = digits(row.get("ISBN_13") or row.get("ISBN"))
        if valid_isbn13(value):
            isbns.add(value)
    return ids, isbns


def unique_target(directory: Path, filename: str) -> Path:
    target = directory / filename
    index = 2
    while target.exists():
        target = directory / f"{Path(filename).stem}_{index}{Path(filename).suffix}"
        index += 1
    return target


def journal_row(**values) -> dict:
    return {field: clean(values.get(field)) for field in JOURNAL_FIELDS}


def write_journal(rows: list[dict]) -> None:
    if not rows:
        return
    JOURNAL.parent.mkdir(parents=True, exist_ok=True)
    exists = JOURNAL.exists() and JOURNAL.stat().st_size > 0
    with JOURNAL.open("a", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=JOURNAL_FIELDS)
        if not exists:
            writer.writeheader()
        writer.writerows(rows)


def render_report(results: list[dict], stamp: str) -> Path:
    REPORTS.mkdir(parents=True, exist_ok=True)
    path = REPORTS / f"analyse-{stamp}.md"
    lines = [f"# Analyse ISBN — {stamp}", "", "| Image | ISBN | Résultat | Notice |", "|---|---|---|---|"]
    for result in results:
        lines.append(f"| `{result['image']}` | {result.get('isbn') or '—'} | {result['status']} | {result.get('notice') or '—'} |")
        if result.get("message"):
            lines.extend(["", f"**{result['image']}** — {result['message']}"])
        for candidate in result.get("candidates", []):
            lines.append(f"- candidat : {candidate.get('Titre', 'Sans titre')} — {candidate.get('Auteur_editeur_scientifique', '')} — {candidate.get('Date_publication', '')} ({candidate.get('URL_notice', '')})")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=25, help="Nombre maximal d’images traitées par exécution")
    args = parser.parse_args()
    QUEUE.mkdir(parents=True, exist_ok=True)
    VERIFY.mkdir(parents=True, exist_ok=True)
    DONE.mkdir(parents=True, exist_ok=True)
    images = sorted(path for path in QUEUE.iterdir() if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS)[: args.limit]
    if not images:
        print("Aucune photographie ISBN à traiter.")
        return 0

    ids, known_isbns = existing_state()
    records = json.loads(PIPELINE.read_text(encoding="utf-8")) if PIPELINE.exists() else []
    next_id = max(ids, default=0) + 1
    now = datetime.now(timezone.utc)
    stamp = now.strftime("%Y%m%d-%H%M%S")
    timestamp = now.isoformat(timespec="seconds")
    results, journal = [], []

    for image in images:
        try:
            isbn = isbn_from_image(image)
        except Exception as error:
            isbn = ""
            decode_message = str(error)
        else:
            decode_message = ""
        if not isbn:
            target = unique_target(VERIFY, image.name)
            shutil.move(image, target)
            message = decode_message or "Aucun ISBN-13 valide n’a pu être lu."
            results.append({"image": image.name, "isbn": "", "status": "À vérifier", "message": message})
            journal.append(journal_row(date_traitement=timestamp, image_source=image.name, image_archivee=str(target.relative_to(ROOT)), isbn_valide="Non", statut="a_verifier", message_controle=message))
            continue
        if isbn in known_isbns:
            target = unique_target(VERIFY, image.name)
            shutil.move(image, target)
            message = "Cet ISBN existe déjà dans le catalogue ou le pipeline."
            results.append({"image": image.name, "isbn": isbn, "status": "Doublon à vérifier", "message": message})
            journal.append(journal_row(date_traitement=timestamp, image_source=image.name, image_archivee=str(target.relative_to(ROOT)), isbn_lu=isbn, isbn_valide="Oui", statut="doublon", message_controle=message))
            continue
        candidate, candidates, message = choose_candidate(isbn)
        if not candidate:
            target = unique_target(VERIFY, image.name)
            shutil.move(image, target)
            results.append({"image": image.name, "isbn": isbn, "status": "À vérifier", "message": message, "candidates": candidates})
            journal.append(journal_row(date_traitement=timestamp, image_source=image.name, image_archivee=str(target.relative_to(ROOT)), isbn_lu=isbn, isbn_valide="Oui", statut="a_verifier", message_controle=message))
            continue

        book_id = f"BIB-{next_id:03d}"
        next_id += 1
        candidate["ID"] = book_id
        candidate["Localisation"] = "Bureau"
        candidate["Notes_controle"] = message or "ISBN contrôlé ; une notice bibliographique concordante a été trouvée."
        records.append(candidate)
        known_isbns.add(isbn)
        archive_name = f"{book_id}_isbn_{isbn}{image.suffix.lower()}"
        target = unique_target(DONE, archive_name)
        shutil.move(image, target)
        notice = f"{candidate['Titre']} — {candidate.get('Auteur_editeur_scientifique', '')}".strip(" —")
        results.append({"image": image.name, "isbn": isbn, "status": f"Notice proposée : {book_id}", "notice": notice, "message": candidate["Notes_controle"]})
        journal.append(journal_row(date_traitement=timestamp, image_source=image.name, image_archivee=str(target.relative_to(ROOT)), isbn_lu=isbn, isbn_valide="Oui", bib_id=book_id, statut="proposition", source_principale=candidate.get("Source_notice"), identifiant_notice=candidate.get("Identifiant_notice"), message_controle=candidate["Notes_controle"]))

    PIPELINE.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_journal(journal)
    report = render_report(results, stamp)
    print(f"{len(results)} image(s) analysée(s). Rapport : {report.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
