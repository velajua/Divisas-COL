import argparse
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

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
            {"group": "cities", "public_path": "instagram_cards/2026-05-10/public/country-00.jpg", "caption": "Cover"},
            {"public_path": "instagram_cards/2026-05-10/public/bogota-01.jpg", "caption": "Bogota caption"},
            {"public_path": "instagram_cards/2026-05-10/public/bogota-02.jpg", "caption": "Bogota caption"},
            {"public_path": "instagram_cards/2026-05-10/public/medellin-01.jpg", "caption": "Medellin caption"},
            {"public_path": "instagram_cards/2026-05-10/public/newsletter.jpg", "caption": "Newsletter caption"},
        ]

        groups = instagram_publish.group_posts_for_instagram(posts)

        self.assertEqual(["cities", "bogota", "medellin", "newsletter"], [group["key"] for group in groups])
        self.assertEqual(["country-00.jpg"], [Path(post["public_path"]).name for post in groups[0]["posts"]])
        self.assertEqual(["bogota-01.jpg", "bogota-02.jpg"], [Path(post["public_path"]).name for post in groups[1]["posts"]])
        self.assertEqual("Bogota caption", groups[1]["caption"])
        self.assertFalse(groups[1]["single"])
        self.assertTrue(groups[3]["single"])

    def test_filters_already_published_groups_from_state(self):
        groups = [
            {"key": "barranquilla", "posts": [{"image_url": "a"}], "single": False},
            {"key": "bogota", "posts": [{"image_url": "b"}], "single": False},
        ]
        state = {"published_groups": ["barranquilla"]}

        remaining = instagram_publish.filter_unpublished_groups(groups, state)

        self.assertEqual(["bogota"], [group["key"] for group in remaining])

    def test_select_groups_filters_requested_keys_case_insensitively(self):
        groups = [
            {"key": "barranquilla", "posts": []},
            {"key": "medellin", "posts": []},
        ]

        selected = instagram_publish.select_groups(groups, ["Medellin"])

        self.assertEqual(["medellin"], [group["key"] for group in selected])

    def test_publish_state_round_trip_preserves_group_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "publish-state.json"
            instagram_publish.save_publish_state(
                path,
                {"published_groups": ["barranquilla", "barranquilla", "bogota"]},
            )

            state = instagram_publish.load_publish_state(path)

            self.assertEqual(["barranquilla", "bogota"], state["published_groups"])

    def test_parser_accepts_date_option_without_subcommands(self):
        args = instagram_publish.parse_args(["--date", "2026-05-10"])

        self.assertEqual("2026-05-10", args.date)

    def test_parser_accepts_reset_state_flag(self):
        args = instagram_publish.parse_args(["--reset-state"])

        self.assertTrue(args.reset_state)

    def test_parser_accepts_group_flag(self):
        args = instagram_publish.parse_args(["--group", "medellin"])

        self.assertEqual(["medellin"], args.group)

    def test_extracts_cloudflare_tunnel_url(self):
        line = "INF +--------------------------------------------------------------------------------------------+ https://abc-def.trycloudflare.com"

        self.assertEqual("https://abc-def.trycloudflare.com", instagram_publish.extract_tunnel_url(line))

    def test_sanitizes_caption_to_instagram_hashtag_limit(self):
        caption = "Body " + " ".join(f"#tag{i}" for i in range(35))

        sanitized = instagram_publish.sanitize_caption(caption)

        self.assertEqual(30, sanitized.count("#"))

    def test_container_poll_defaults_are_longer_and_backoff(self):
        sleeps = []

        def fake_sleep(seconds):
            sleeps.append(seconds)
            raise StopIteration

        def fake_status(container_id, token):
            return {"status_code": "IN_PROGRESS"}

        with patch.object(instagram_publish, "media_container_status", side_effect=fake_status), patch.object(
            instagram_publish.time, "sleep", side_effect=fake_sleep
        ):
            with self.assertRaises(StopIteration):
                instagram_publish.wait_for_container_finished("123", "token", timeout_seconds=25, poll_seconds=20)

        self.assertEqual([20], sleeps)


if __name__ == "__main__":
    unittest.main()
