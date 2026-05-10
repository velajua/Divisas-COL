import argparse
import json
import tempfile
import unittest
from pathlib import Path

import instagram_publish


class InstagramPublishWorkflowTests(unittest.TestCase):
    def test_manifest_for_date_uses_public_manifest_in_date_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = root / "instagram_cards" / "2026-05-10" / "public" / "publish-manifest.json"
            manifest.parent.mkdir(parents=True)
            manifest.write_text('{"posts": []}', encoding="utf-8")

            resolved = instagram_publish.publish_manifest_for_date(root, "2026-05-10")

            self.assertEqual(manifest, resolved)

    def test_manifest_for_default_date_uses_bogota_today(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            today = instagram_publish.default_date_label()
            manifest = root / "instagram_cards" / today / "public" / "publish-manifest.json"
            manifest.parent.mkdir(parents=True)
            manifest.write_text('{"posts": []}', encoding="utf-8")

            resolved = instagram_publish.publish_manifest_for_date(root, None)

            self.assertEqual(manifest, resolved)

    def test_groups_carousel_posts_by_first_filename_word_in_manifest_order(self):
        posts = [
            {"public_path": "instagram_cards/2026-05-10/public/bogota-01.jpg", "caption": "Bogota caption"},
            {"public_path": "instagram_cards/2026-05-10/public/bogota-02.jpg", "caption": "Bogota caption"},
            {"public_path": "instagram_cards/2026-05-10/public/medellin-01.jpg", "caption": "Medellin caption"},
            {"public_path": "instagram_cards/2026-05-10/public/newsletter.jpg", "caption": "Newsletter caption"},
        ]

        groups = instagram_publish.group_posts_for_instagram(posts)

        self.assertEqual(["bogota", "medellin", "newsletter"], [group["key"] for group in groups])
        self.assertEqual(["bogota-01.jpg", "bogota-02.jpg"], [Path(post["public_path"]).name for post in groups[0]["posts"]])
        self.assertEqual("Bogota caption", groups[0]["caption"])
        self.assertFalse(groups[0]["single"])
        self.assertTrue(groups[2]["single"])

    def test_parser_accepts_date_option_without_subcommands(self):
        args = instagram_publish.parse_args(["--date", "2026-05-10"])

        self.assertEqual("2026-05-10", args.date)

    def test_extracts_cloudflare_tunnel_url(self):
        line = "INF +--------------------------------------------------------------------------------------------+ https://abc-def.trycloudflare.com"

        self.assertEqual("https://abc-def.trycloudflare.com", instagram_publish.extract_tunnel_url(line))

    def test_sanitizes_caption_to_instagram_hashtag_limit(self):
        caption = "Body " + " ".join(f"#tag{i}" for i in range(35))

        sanitized = instagram_publish.sanitize_caption(caption)

        self.assertEqual(30, sanitized.count("#"))


if __name__ == "__main__":
    unittest.main()
