from pathlib import Path

from divisas_voiceover_xtts_clean.generate_voiceover import load_txt_chunks


def test_load_txt_chunks_keeps_lines_separate_and_splits_long_lines(tmp_path: Path):
    txt_path = tmp_path / "summary.txt"
    txt_path.write_text(
        "\n".join(
            [
                "El Gobierno paga caro.",
                "",
                "La izquierda vende relato, no confianza fiscal.",
                "Sin ajuste real el mercado castiga la deuda y el peso queda sin defensa.",
            ]
        ),
        encoding="utf-8",
    )

    chunks = load_txt_chunks(txt_path, max_chars=55)

    assert chunks == [
        "El Gobierno paga caro.",
        "La izquierda vende relato, no confianza fiscal.",
        "Sin ajuste real el mercado castiga la deuda y el peso",
        "queda sin defensa.",
    ]
