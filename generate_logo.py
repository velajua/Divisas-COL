import argparse
from dataclasses import dataclass, replace
from pathlib import Path


@dataclass(frozen=True)
class LogoConfig:
    canvas: int = 512
    corner_radius: int = 92
    background: str = "#0f0e0c"
    gold: str = "#f2d39b"
    white: str = "#ffffff"
    center_x: int = 256
    center_y: int = 256
    d_width: int = 304
    d_height: int = 304
    d_stem: int = 92
    c_radius: int = 72
    c_stroke: int = 28
    dollar_height: int = 108
    dollar_stroke: int = 8
    dollar_bar: int = 36


DEFAULT_CONFIG = LogoConfig()

# python generate_logo.py --center-x 250 --center-y 256 --d-width 350 --d-height 304 --d-stem 50 --c-radius 64 --c-stroke 28 --dollar-height 108 --dollar-stroke 0 --dollar-bar 30

def parse_args():
    parser = argparse.ArgumentParser(description="Generate the Divisas COL logo SVG.")
    parser.add_argument(
        "--output",
        default="html/assets/logo.svg",
        help="Path to write the generated SVG.",
    )
    parser.add_argument("--center-x", type=int, help="Center X for the logo system.")
    parser.add_argument("--center-y", type=int, help="Center Y for the logo system.")
    parser.add_argument("--d-width", type=int, help="Outer D total width.")
    parser.add_argument("--d-height", type=int, help="Outer D total height.")
    parser.add_argument("--d-stem", type=int, help="Outer D stem width.")
    parser.add_argument("--c-radius", type=int, help="Inner C radius.")
    parser.add_argument("--c-stroke", type=int, help="Inner C stroke width.")
    parser.add_argument("--dollar-height", type=int, help="Dollar mark total height.")
    parser.add_argument("--dollar-stroke", type=int, help="Dollar mark stroke width.")
    parser.add_argument("--dollar-bar", type=int, help="Dollar mark bar width.")
    parser.add_argument("--background", help="Background color.")
    parser.add_argument("--gold", help="Primary gold color.")
    parser.add_argument("--white", help="Accent white color.")
    return parser.parse_args()


def config_from_args(args):
    values = {}
    field_map = {
        "center_x": args.center_x,
        "center_y": args.center_y,
        "d_width": args.d_width,
        "d_height": args.d_height,
        "d_stem": args.d_stem,
        "c_radius": args.c_radius,
        "c_stroke": args.c_stroke,
        "dollar_height": args.dollar_height,
        "dollar_stroke": args.dollar_stroke,
        "dollar_bar": args.dollar_bar,
        "background": args.background,
        "gold": args.gold,
        "white": args.white,
    }
    for key, value in field_map.items():
        if value is not None:
            values[key] = value
    return replace(DEFAULT_CONFIG, **values)


def outer_d_path(config: LogoConfig) -> str:
    left = config.center_x - (config.d_width // 2)
    top = config.center_y - (config.d_height // 2)
    right = left + config.d_width
    bottom = top + config.d_height
    stem_right = left + config.d_stem
    mid_y = config.center_y
    return (
        f"M{left} {top}H{left + 120}"
        f"C{right - 54} {top} {right} {mid_y - 60} {right} {mid_y}"
        f"C{right} {mid_y + 60} {right - 54} {bottom} {left + 120} {bottom}"
        f"H{left}V{bottom}H{stem_right}V{top + 78}H{left + 120}"
        f"V{bottom - 78}H{stem_right}V{top}H{left}Z"
    )


def d_counter_path(config: LogoConfig) -> str:
    left = config.center_x - (config.d_width // 2)
    top = config.center_y - (config.d_height // 2)
    x0 = left + config.d_stem + 4
    y0 = top + 48
    x1 = x0 + 54
    y1 = top + config.d_height - 48
    cx = config.center_x + 24
    cy = config.center_y
    rx = 104
    return (
        f"M{x1} {y0 + 2}"
        f"C{cx + 66} {y0 + 2} {cx + rx} {cy - 48} {cx + rx} {cy}"
        f"C{cx + rx} {cy + 48} {cx + 66} {y1 - 2} {x1} {y1 - 2}Z"
    )


def inner_c_path(config: LogoConfig) -> str:
    cx = config.center_x + 34
    cy = config.center_y
    radius = config.c_radius
    top = cy - radius
    bottom = cy + radius
    right = cx + radius
    gap = 22
    return (
        f"M{right - gap} {top + 24}"
        f"A{radius} {radius} 0 1 0 {right - gap} {bottom - 24}"
    )


def dollar_mark_svg(config: LogoConfig) -> str:
    cx = config.center_x + 35
    cy = config.center_y
    half_height = config.dollar_height / 2
    half_bar = config.dollar_bar / 2
    top_bar_y = cy - 22
    bottom_bar_y = cy + 22
    return "\n".join(
        [
            f'  <path id="dollar-mark" d="M{cx} {cy - half_height}V{cy + half_height}" '
            f'stroke="{config.white}" stroke-width="{config.dollar_stroke}" '
            'stroke-linecap="round" fill="none"/>',
            f'  <path d="M{cx - half_bar} {top_bar_y}H{cx + half_bar}" '
            f'stroke="{config.white}" stroke-width="{config.dollar_stroke}" '
            'stroke-linecap="round" fill="none"/>',
            f'  <path d="M{cx - half_bar + 6} {bottom_bar_y}H{cx + half_bar - 6}" '
            f'stroke="{config.white}" stroke-width="{config.dollar_stroke}" '
            'stroke-linecap="round" fill="none"/>',
        ]
    )


def build_logo_svg(config: LogoConfig = DEFAULT_CONFIG) -> str:
    return "\n".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {config.canvas} {config.canvas}" role="img" aria-label="Divisas COL generated logo">',
            f'  <rect width="{config.canvas}" height="{config.canvas}" rx="{config.corner_radius}" fill="{config.background}"/>',
            f'  <path id="outer-d" fill="{config.gold}" d="{outer_d_path(config)}"/>',
            f'  <path id="d-counter" fill="{config.background}" d="{d_counter_path(config)}"/>',
            f'  <path id="inner-c" d="{inner_c_path(config)}" stroke="{config.gold}" stroke-width="{config.c_stroke}" stroke-linecap="round" fill="none"/>',
            dollar_mark_svg(config),
            "</svg>",
        ]
    )


def write_logo(output_path: Path, config: LogoConfig = DEFAULT_CONFIG) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(build_logo_svg(config), encoding="utf-8")


def main():
    args = parse_args()
    config = config_from_args(args)
    write_logo(Path(args.output), config)
    print(f"Generated logo: {args.output}")


if __name__ == "__main__":
    main()
