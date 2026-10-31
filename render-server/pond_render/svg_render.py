"""SVG to PNG conversion with external resource fetching disabled."""

from __future__ import annotations

from .cairo_compat import ensure_cairo

ensure_cairo()

import cairosvg  # noqa: E402

MAX_OUTPUT_WIDTH = 4096


class SvgRenderError(ValueError):
    pass


def svg_to_png(
    svg: str | bytes,
    *,
    width: int | None = None,
    background: str | None = "white",
    max_bytes: int = 2_000_000,
) -> bytes:
    """Render an SVG document to PNG bytes.

    cairosvg's default `unsafe=False` mode only follows data: URLs, so an SVG cannot
    make the server fetch internal URLs or read local files.
    """
    data = svg.encode("utf-8") if isinstance(svg, str) else svg
    if not data.strip():
        raise SvgRenderError("SVG is empty")
    if len(data) > max_bytes:
        raise SvgRenderError(f"SVG is too large ({len(data)} bytes, limit {max_bytes})")
    if width is not None and not (16 <= width <= MAX_OUTPUT_WIDTH):
        raise SvgRenderError(f"width must be between 16 and {MAX_OUTPUT_WIDTH}")
    try:
        return cairosvg.svg2png(
            bytestring=data,
            output_width=width,
            background_color=background,
            unsafe=False,
        )
    except SvgRenderError:
        raise
    except Exception as exc:  # cairosvg raises a mix of ValueError/ParseError/TypeError
        raise SvgRenderError(f"Could not render SVG: {type(exc).__name__}: {exc}") from exc
