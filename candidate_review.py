#!/usr/bin/env python3
"""Validate candidate media and create a local gallery without selecting a dataset."""

from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime
import html
import math
from pathlib import Path
import re

import benchmark as b


CC0_STATUS = "cc0_basis_verified_other_rights_pending"
PUBLIC_DOMAIN_STATUS = "us_public_domain_redistribution_review_required"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise b.BenchmarkError(message)


def text(value: object, label: str) -> str:
    require(isinstance(value, str) and bool(value.strip()), f"{label} requires nonempty text")
    return value


def validate_collection(directory: Path, *, require_media: bool = True) -> dict:
    """Validate the catalog offline; metadata-only checks work in a clean checkout."""
    root = directory.resolve()
    manifest = b.read_json(root / "manifest.json")
    require(manifest.get("schema_version") == "1.0", "Unsupported candidate schema")
    text(manifest.get("collection_id"), "collection_id")
    candidates = manifest.get("candidates")
    require(isinstance(candidates, list) and bool(candidates), "A nonempty candidates array is required")
    seen_ids, seen_paths = set(), set()
    for candidate in candidates:
        require(isinstance(candidate, dict), "Each candidate must be an object")
        identifier = text(candidate.get("id"), "candidate id")
        require(re.fullmatch(r"C\d{3}", identifier) is not None, "Use stable C001-style candidate IDs")
        require(identifier not in seen_ids, f"Duplicate candidate id: {identifier}")
        seen_ids.add(identifier)
        filename = text(candidate.get("filename"), f"{identifier}.filename")
        path = b.asset_path(root, filename)
        require(path.is_relative_to(root / "media"), f"{identifier}: image must stay under media/")
        require(path not in seen_paths, f"Duplicate candidate path: {filename}")
        seen_paths.add(path)
        require(b.SHA_PATTERN.fullmatch(str(candidate.get("sha256", ""))) is not None, f"{identifier}: invalid SHA-256")
        if require_media:
            data = path.read_bytes()
            b.image_type(data)
            require(b.digest(data) == candidate["sha256"], f"{identifier}: image hash mismatch")
        for field in ("width", "height"):
            value = candidate.get(field)
            require(type(value) is int and value > 0, f"{identifier}: {field} must be a positive integer")
        for field in ("source_page", "original_download_url"):
            b.public_url(candidate.get(field))
        require(candidate.get("download_method", "GET") in ("GET", "POST"), f"{identifier}: unsupported download method")
        for field in ("creator", "title", "staged_context", "visual_description"):
            text(candidate.get(field), f"{identifier}.{field}")
        retrieved = datetime.fromisoformat(text(candidate.get("retrieved_at"), "retrieved_at").replace("Z", "+00:00"))
        require(retrieved.tzinfo is not None, f"{identifier}: retrieval time needs a timezone")
        for field in ("tags", "notices", "transformations"):
            require(isinstance(candidate.get(field), list), f"{identifier}: {field} must be an array")
        for field in ("tags", "notices", "transformations"):
            for value in candidate[field]:
                text(value, f"{identifier}.{field}")
        require(candidate.get("severity") in ("moderate", "strong"), f"{identifier}: invalid severity")
        require(candidate.get("dataset_selection_status") == "pending_review", f"{identifier}: candidates must remain pending_review")
        evidence = candidate.get("rights_evidence")
        require(isinstance(evidence, list) and bool(evidence), f"{identifier}: rights evidence is required")
        for item in evidence:
            require(isinstance(item, dict), f"{identifier}: invalid rights evidence")
            b.public_url(item.get("url"))
            text(item.get("basis_summary"), f"{identifier}.rights_evidence")
        if candidate.get("license") == "CC0-1.0":
            require(candidate.get("license_url") == "https://creativecommons.org/publicdomain/zero/1.0/", f"{identifier}: CC0 needs its exact license URL")
            require(candidate.get("jurisdiction") == "worldwide waiver to extent permitted", f"{identifier}: invalid CC0 scope")
            require(candidate.get("rights_review_status") == CC0_STATUS, f"{identifier}: CC0 does not clear all other rights")
            require(candidate.get("public_domain_basis") is None, f"{identifier}: use the CC0 license field")
        elif candidate.get("license") == "Public domain":
            require(candidate.get("license_url") is None, f"{identifier}: record public-domain evidence instead of a license URL")
            text(candidate.get("public_domain_basis"), f"{identifier}.public_domain_basis")
            require(candidate.get("jurisdiction") == "United States", f"{identifier}: public-domain jurisdiction needs review")
            require(candidate.get("rights_review_status") == PUBLIC_DOMAIN_STATUS, f"{identifier}: U.S. public-domain media needs redistribution review")
        else:
            raise b.BenchmarkError(f"{identifier}: only explicit CC0 or documented public-domain candidates belong here")
        film = candidate.get("film")
        if film is not None:
            require(isinstance(film, dict), f"{identifier}: film must be an object or null")
            timestamp = film.get("timestamp_seconds")
            require(type(timestamp) in (int, float) and math.isfinite(timestamp) and timestamp >= 0, f"{identifier}: invalid film timestamp")
            for field in ("source_version", "scene_id", "shot_id", "extraction_command"):
                text(film.get(field), f"{identifier}.film.{field}")
            require(b.SHA_PATTERN.fullmatch(str(film.get("source_file_sha256", ""))) is not None, f"{identifier}: missing source-film checksum")
    return manifest


def escape(value: object) -> str:
    return html.escape(str(value), quote=True)


def candidate_card(candidate: dict) -> str:
    image = escape(candidate["filename"])
    film = candidate.get("film")
    frame_info = ""
    if film:
        frame_info = f"<p>Frame {escape(film['timestamp_seconds'])}s; scene {escape(film['scene_id'])}; shot {escape(film['shot_id'])}.</p>"
    license_url = candidate.get("license_url")
    license_name = escape(candidate["license"])
    license_label = f'<a href="{escape(license_url)}">{license_name}</a>' if license_url else license_name
    # Some sources use a browser POST form, so a direct GET link cannot download them.
    browser_download = candidate.get("download_method", "GET") == "POST"
    download_url = candidate["source_page"] if browser_download else candidate["original_download_url"]
    download_label = "Open source to download" if browser_download else "Source download"
    return f'''<article class="card" id="{escape(candidate['id'])}">
      <a href="{image}"><img src="{image}" alt="{escape(candidate['visual_description'])}" loading="lazy"></a>
      <div class="details"><h3>{escape(candidate['id'])}: {escape(candidate['title'])}</h3>
      <p>{escape(candidate['visual_description'])}</p>
      <p>Staged context: {escape(candidate['staged_context'])}</p>
      <p>Creator: {escape(candidate['creator'])}</p>
      <p><strong>{escape(candidate['severity'])}</strong> · {escape(', '.join(candidate['tags']))}</p>
      <p>Rights: {license_label}; {escape(candidate['jurisdiction'])}.<br>{escape(candidate['rights_review_status'])}</p>
      <p>Selection: {escape(candidate['dataset_selection_status'])}</p>
      <p>Notices: {escape('; '.join(candidate['notices']))}</p>{frame_info}
      <p><a href="{image}">Full-resolution candidate</a> · <a href="{escape(candidate['source_page'])}">Source record</a> ·
      <a href="{escape(download_url)}">{download_label}</a></p></div></article>'''


def build_gallery(directory: Path) -> Path:
    manifest = validate_collection(directory)
    groups = defaultdict(list)
    for candidate in manifest["candidates"]:
        film = candidate.get("film")
        key = (film["source_file_sha256"], film["scene_id"], film["shot_id"]) if film else None
        groups[key].append(candidate)
    sections = []
    for key, candidates in groups.items():
        heading = "Source photographs" if key is None else f"Film shot: {key[1]} / {key[2]}"
        candidates = sorted(candidates, key=lambda item: item.get("film", {}).get("timestamp_seconds", 0) if item.get("film") else 0)
        sections.append(f'<section><h2>{escape(heading)}</h2><div class="grid">'+"".join(candidate_card(item) for item in candidates)+"</div></section>")
    output = directory.resolve() / "index.html"
    output.write_text(f'''<!doctype html><html lang="en"><meta charset="utf-8">
      <meta name="viewport" content="width=device-width,initial-scale=1"><title>{escape(manifest['collection_id'])}</title>
      <style>body{{font:16px/1.5 system-ui;margin:0;background:#f3f4f6;color:#202124}}main{{max-width:1440px;margin:auto;padding:24px}}
      .grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,320px),1fr));gap:20px}}
      .card{{background:white;border-radius:8px;overflow:hidden}}img{{width:100%;height:300px;object-fit:contain;background:#15171b}}
      .details{{padding:18px;overflow-wrap:anywhere}}.notice{{padding:18px;background:#fff0c4}}a{{color:#174b9b}}h2{{margin-top:36px}}</style>
      <main><h1>{escape(manifest['collection_id'])}</h1><p>{len(manifest['candidates'])} candidates. All await review.</p>
      <p class="notice">Contains staged blood, prosthetic wounds and fictional film violence. This is a local review collection, not a benchmark dataset.
      U.S.-only public-domain claims require review before public redistribution. Copyright status does not clear likeness, endorsement or other rights.
      U.S. military imagery does not imply Department of Defense endorsement.</p>
      <p><a href="manifest.json">Machine-readable provenance</a> · <a href="ATTRIBUTION.md">Attribution and notices</a> ·
      <a href="discovery.json">Other licensed discoveries</a> · <a href="skipped-sources.json">Skipped sources</a></p>
      {''.join(sections)}</main></html>''', encoding="utf-8")
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("validate", "gallery"))
    parser.add_argument("collection", type=Path)
    parser.add_argument("--metadata-only", action="store_true", help="Validate catalog structure without ignored local media")
    args = parser.parse_args(argv)
    try:
        require(not (args.command == "gallery" and args.metadata_only), "Gallery requires the real local media")
        if args.command == "gallery":
            print(build_gallery(args.collection))
        else:
            manifest = validate_collection(args.collection, require_media=not args.metadata_only)
            print(f"Validated {len(manifest['candidates'])} candidates; media checked: {not args.metadata_only}")
        return 0
    except (b.BenchmarkError, OSError, ValueError) as exc:
        print(f"Error: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
