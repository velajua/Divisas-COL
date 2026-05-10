import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageStat

import generate_instagram_cards as subject


class PublicCardRenderingTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
