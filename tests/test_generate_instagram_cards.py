import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from PIL import Image, ImageStat

import generate_instagram_cards as subject


class PublicCardRenderingTests(unittest.TestCase):
    def test_parse_rate_treats_three_digits_after_comma_as_thousands(self):
        self.assertEqual(2670, subject.parse_rate("2,670"))
        self.assertEqual(2600, subject.parse_rate("2.600"))
        self.assertEqual(2.6, subject.parse_rate("2,60"))

    def test_display_place_prefers_specific_branch_id_over_exchange_house(self):
        item = {"exchange_house": "puntoDollar", "id": "PuntoDollar Barranquilla"}

        self.assertEqual("PuntoDollar Barranquilla", subject.display_place(item))

    def test_public_renderer_renders_svg_content_into_jpeg(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            day_dir = repo_root / "instagram_cards" / "2026-05-10"
            day_dir.mkdir(parents=True)
            svg_path = day_dir / "sample.svg"
            svg_path.write_text(
                "\n".join(
                    [
                        '<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1350" viewBox="0 0 1080 1350">',
                        '<rect width="1080" height="1350" fill="#0b1220"/>',
                        '<rect x="100" y="100" width="880" height="1150" fill="#f8fafc"/>',
                        '<text x="140" y="220" fill="#0f172a" font-size="64">Visible card</text>',
                        "</svg>",
                    ]
                ),
                encoding="utf-8",
            )
            manifest = {
                "date": "2026-05-10",
                "cards": [
                    {
                        "type": "city_rates",
                        "city": "Bogota",
                        "path": "instagram_cards/2026-05-10/sample.svg",
                    }
                ],
            }

            public_dir, _ = subject.render_public_cards(repo_root, day_dir, manifest)

            image = Image.open(public_dir / "sample.jpg").convert("RGB")
            mean = ImageStat.Stat(image).mean
            self.assertLess(sum(mean) / len(mean), 245)

    def test_cleanup_removes_only_dated_card_folders_older_than_three_weeks(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            cards_root = Path(temp_dir) / "instagram_cards"
            cards_root.mkdir()
            old_dir = cards_root / "2026-04-21"
            cutoff_dir = cards_root / "2026-04-22"
            recent_dir = cards_root / "2026-05-13"
            non_date_dir = cards_root / "drafts"
            for folder in (old_dir, cutoff_dir, recent_dir, non_date_dir):
                folder.mkdir()
                (folder / "marker.txt").write_text("keep track", encoding="utf-8")

            removed = subject.cleanup_old_card_dirs(cards_root, date(2026, 5, 13))

            self.assertEqual([old_dir], removed)
            self.assertFalse(old_dir.exists())
            self.assertTrue(cutoff_dir.exists())
            self.assertTrue(recent_dir.exists())
            self.assertTrue(non_date_dir.exists())


if __name__ == "__main__":
    unittest.main()
