# Staged violence reference candidates

This collection is a review pool, separate from every `datasets/` revision. All
entries remain `pending_review`; inclusion here does not select an image for the
benchmark or authorize public redistribution. Source rights are recorded in
[manifest.json](manifest.json) and [ATTRIBUTION.md](ATTRIBUTION.md). The repository
license does not replace third-party media rights.

The active pool contains 20 color photographs: one StockSnap CC0 photograph, two
Commons CC0 photographs and 17 U.S. government training photographs. Eighteen
show strong practical-effects violence and two are moderate comparisons. The five
original-film frames are excluded for inadequate image quality; their IDs and
exclusion reasons remain in the catalog. Screening labels are not provider scores.

## Local review

The actual images belong under this folder's ignored `media/` directory. A clean
checkout contains the catalog and tools, not the downloaded media. From the
repository root:

```bash
python3 candidate_review.py validate reference-candidates/violence-harvest-v1 --metadata-only
python3 candidate_review.py validate reference-candidates/violence-harvest-v1
python3 candidate_review.py gallery reference-candidates/violence-harvest-v1
```

The second command requires the exact local files and checks container structure
and SHA-256. Recorded dimensions were measured by decoding the actual files;
the standard-library validator checks their field types but does not decode
pixels. The last command creates ignored `index.html`. Open it locally to browse
the previews, staged context, rights notices and full-resolution candidate links.
Each card also links its source record and source download. The StockSnap source
uses a browser POST download, so its download link opens the photo page.

For browser testing, serve only this collection folder, never the repository root
or an environment file:

```bash
python3 -m http.server 8766 --bind 127.0.0.1 --directory reference-candidates/violence-harvest-v1
```

Open `http://127.0.0.1:8766/`. The gallery is static and works without JavaScript.
Neighboring film frames are grouped by source checksum, scene and shot; each
current frame comes from a distinct shot. It provides no approval controls.

## Provenance and reproduction

`original_download_url` identifies the exact retrieved image or film encode.
Photographs are byte-for-byte copies of the downloaded source files except C014,
whose source contains trailing bytes after the PNG end marker. Its staged copy
removes only those trailing bytes, preserving every image chunk and decoded pixel.
The original checksum, size and transformation remain in the manifest and the full
original remains in the ignored cache. Commons
records include a pinned description revision, file timestamp and verified source
SHA-1. SHA-256 and dimensions describe the staged candidate bytes, not a preview.
No canonical photograph was cropped, resized or retouched.

Film downloads stay in ignored `runs/reference-harvest/cache/`. Each film entry
records its source encode, dimensions, file size, SHA-256, requested seek time,
actual decoded frame timestamp, scene, shot, FFmpeg version and extraction command.
Use the recorded encode and verify its checksum before reproducing a frame. The
commands decode at source resolution to lossless PNG with no crop, colorization,
relighting or generated material. `showinfo` with `-copyts` supplies the first
decoded frame's absolute presentation timestamp. Diagnostic scouting thumbnails
are not canonical candidate files. Full movies must never be committed.

Review attribution and the exact source record before downloading or reusing any
candidate. Respect source throttling and unavailable sources. Do not replace a
missing file with a similar image or a placeholder. The validator deliberately
does not fetch URLs or execute extraction commands from the manifest.

## Rights boundaries and sourcing gaps

Three files have explicit CC0 dedications. Other likeness, privacy, publicity,
trademark and stage-production rights remain unreviewed. The 17 public-domain
claims are scoped to the United States, covering the government photographs. The maintainer accepts the U.S.-only copyright basis for the photo comparison;
other jurisdictions and noncopyright rights remain unverified.

Military imagery retains simulated-training context and the applicable
nonendorsement notice. It must not be presented as a real attack or as endorsement
of Segmind or a competing provider. Candidate C011 has an unverified subject age. C020 depicts a mannequin limb
wound on a litter; its source caption about securing straps matches the scene. The photographs favor wound
effects and casualty aftermath over active combat. Clearer color stabbing and
shooting action remains a sourcing gap; the rejected film frames are not used to fill that gap. Any future benchmark
selection must separately assess identity, adult-subject requirements, confounds
from mannequins or makeup application, jurisdiction and redistribution rights.

[discovery.json](discovery.json) records promising CC BY or CC BY-SA sources as
metadata only. Their files were not downloaded, and their visual suitability is
unverified. [skipped-sources.json](skipped-sources.json) records unavailable or
unsuitable paths, visual exclusions and resolved retrieval problems. Neither file
is a hidden replacement pool for the published benchmark.
