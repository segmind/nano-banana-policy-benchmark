"""Offline checks for rights-scoped candidate review, separate from inference."""

import copy
import json
from pathlib import Path
import tempfile
import unittest

import benchmark as b
import candidate_review as review
from test_benchmark import PNG


class CandidateReviewTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / "media").mkdir()
        (self.root / "media/C001.png").write_bytes(PNG)
        self.candidate = {
            "id": "C001", "filename": "media/C001.png", "sha256": b.digest(PNG),
            "width": 1, "height": 1, "source_page": "https://example.org/source",
            "original_download_url": "https://example.org/original.png",
            "creator": "Test creator", "title": "A staged test scene",
            "license": "CC0-1.0", "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
            "public_domain_basis": None, "jurisdiction": "worldwide waiver to extent permitted",
            "retrieved_at": "2026-11-05T10:00:00Z", "staged_context": "Source identifies simulated makeup.",
            "visual_description": "Synthetic in-memory transport fixture, not candidate art.",
            "film": None, "transformations": [], "tags": ["test"], "notices": ["Test only"],
            "severity": "moderate", "rights_review_status": review.CC0_STATUS,
            "dataset_selection_status": "pending_review",
            "rights_evidence": [{"url": "https://example.org/source", "basis_summary": "Explicit CC0 dedication."}],
        }
        self.manifest = {"schema_version": "1.0", "collection_id": "test", "candidates": [self.candidate]}
        self.save()

    def save(self):
        (self.root / "manifest.json").write_text(json.dumps(self.manifest), encoding="utf-8")

    def test_real_bytes_and_hash_are_checked(self):
        self.assertEqual(len(review.validate_collection(self.root)["candidates"]), 1)
        self.candidate["sha256"] = "0" * 64
        self.save()
        with self.assertRaisesRegex(b.BenchmarkError, "hash mismatch"):
            review.validate_collection(self.root)
        (self.root / "media/C001.png").write_bytes(PNG + b"tampered")
        with self.assertRaises(b.BenchmarkError):
            review.validate_collection(self.root)

    def test_malformed_manifest_and_unsupported_download_method_are_rejected(self):
        (self.root / "manifest.json").write_text("[]", encoding="utf-8")
        with self.assertRaisesRegex(b.BenchmarkError, "must contain a JSON object"):
            review.validate_collection(self.root)
        self.candidate["download_method"] = "PATCH"
        self.save()
        with self.assertRaisesRegex(b.BenchmarkError, "unsupported download method"):
            review.validate_collection(self.root)

    def test_traversal_cannot_escape_media_even_inside_collection(self):
        (self.root / "outside.png").write_bytes(PNG)
        for filename in ("media/../outside.png", "media/../../outside.png", str(self.root / "outside.png")):
            with self.subTest(filename=filename):
                self.candidate["filename"] = filename
                self.save()
                with self.assertRaises(b.BenchmarkError):
                    review.validate_collection(self.root, require_media=False)

    def test_by_licenses_and_selected_status_are_rejected(self):
        original = copy.deepcopy(self.candidate)
        for fields in ({"license": "CC BY 4.0"}, {"license": "CC BY-SA 4.0"},
                       {"dataset_selection_status": "selected"}, {"rights_review_status": "approved"},
                       {"rights_evidence": []}, {"staged_context": ""}):
            with self.subTest(fields=fields):
                self.manifest["candidates"][0] = {**original, **fields}
                self.save()
                with self.assertRaises(b.BenchmarkError):
                    review.validate_collection(self.root)

    def test_us_public_domain_needs_basis_scope_and_pending_redistribution(self):
        self.candidate.update(license="Public domain", license_url=None, public_domain_basis="U.S. federal work, 17 USC 105.",
                              jurisdiction="United States", rights_review_status=review.PUBLIC_DOMAIN_STATUS)
        self.save()
        review.validate_collection(self.root)
        for field, value in (("jurisdiction", "worldwide"), ("rights_review_status", "approved"),
                             ("public_domain_basis", ""), ("license_url", "javascript:alert(1)")):
            original = self.candidate[field]
            self.candidate[field] = value
            self.save()
            with self.assertRaises(b.BenchmarkError):
                review.validate_collection(self.root)
            self.candidate[field] = original

    def test_metadata_mode_does_not_claim_or_require_media(self):
        (self.root / "media/C001.png").unlink()
        review.validate_collection(self.root, require_media=False)
        with self.assertRaises(OSError):
            review.build_gallery(self.root)

    def test_browser_post_download_links_to_source_instead_of_broken_get(self):
        self.candidate["download_method"] = "POST"
        self.save()
        page = review.build_gallery(self.root).read_text()
        self.assertIn('href="https://example.org/source">Open source to download', page)
        self.assertNotIn('href="https://example.org/original.png">Source download', page)

    def test_gallery_escapes_source_text_and_links_local_original_for_film(self):
        self.candidate["title"] = '<script>alert("test")</script>'
        self.candidate["film"] = {"source_version": "Original film, documented encode", "timestamp_seconds": 2.5,
                                  "scene_id": "scene", "shot_id": "shot", "source_file_sha256": "a" * 64,
                                  "extraction_command": "ffmpeg extraction recorded, never executed by gallery"}
        second = {**self.candidate, "id": "C002", "filename": "media/C002.png",
                  "film": {**self.candidate["film"], "timestamp_seconds": 2.6}}
        (self.root / second["filename"]).write_bytes(PNG)
        self.manifest["candidates"].append(second)
        self.save()
        page = review.build_gallery(self.root).read_text()
        self.assertIn("&lt;script&gt;", page)
        self.assertNotIn("<script>alert", page)
        self.assertEqual(page.count("Film shot:"), 1)
        self.assertIn('href="media/C001.png">Full-resolution candidate', page)
        self.assertIn("U.S.-only public-domain claims", page)
        self.assertLess(page.index("Frame 2.5s"), page.index("Frame 2.6s"))

    def test_nonfinite_film_timestamps_and_duplicate_paths_are_rejected(self):
        self.candidate["film"] = {"source_version": "Original", "timestamp_seconds": float("nan"), "scene_id": "s",
                                  "shot_id": "a", "source_file_sha256": "a" * 64, "extraction_command": "recorded"}
        self.save()
        with self.assertRaises(b.BenchmarkError):
            review.validate_collection(self.root)
        self.candidate["film"]["timestamp_seconds"] = 0
        self.manifest["candidates"].append({**self.candidate, "id": "C002"})
        self.save()
        with self.assertRaises(b.BenchmarkError):
            review.validate_collection(self.root)

    def test_checked_in_catalog_preserves_pending_selection_and_source_scope(self):
        root = Path(__file__).resolve().parents[1] / "reference-candidates/violence-harvest-v1"
        catalog = review.validate_collection(root, require_media=False)
        candidates = catalog["candidates"]
        self.assertEqual(len(candidates), 20)
        self.assertEqual(len({item["sha256"] for item in candidates}), 20)
        self.assertEqual(sum(item["license"] == "CC0-1.0" for item in candidates), 3)
        self.assertEqual(sum(item["film"] is not None for item in candidates), 0)
        for item in candidates:
            self.assertEqual(item["dataset_selection_status"], "pending_review")
            self.assertTrue(item["transformations"])


if __name__ == "__main__":
    unittest.main()
