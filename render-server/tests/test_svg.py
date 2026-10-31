import pytest

from pond_render.svg_render import SvgRenderError, svg_to_png

SVG = '<svg xmlns="http://www.w3.org/2000/svg" width="200" height="100"><rect x="10" y="10" width="180" height="80" fill="#4a90d9"/></svg>'


def test_svg_to_png_basic():
    png = svg_to_png(SVG)
    assert png.startswith(b"\x89PNG")


def test_svg_width_override():
    png = svg_to_png(SVG, width=400)
    assert png.startswith(b"\x89PNG")
    # PNG IHDR width is bytes 16..20
    assert int.from_bytes(png[16:20], "big") == 400


def test_svg_rejects_empty_and_garbage():
    with pytest.raises(SvgRenderError):
        svg_to_png("   ")
    with pytest.raises(SvgRenderError):
        svg_to_png("<not-svg>")


def test_svg_too_large():
    with pytest.raises(SvgRenderError):
        svg_to_png(SVG, max_bytes=10)


def test_svg_external_image_not_fetched():
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="50" height="50">'
           '<image xlink:href="http://127.0.0.1:1/never.png" width="50" height="50"/></svg>')
    # Either rendered without the image or refused; it must never hang on a network fetch.
    try:
        png = svg_to_png(svg)
        assert png.startswith(b"\x89PNG")
    except SvgRenderError:
        pass
