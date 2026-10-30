"""Code 128 barcodes for the job ticket, drawn as SVG.

The same encoder as fuse_retread's tyre label, kept here so this app stands on its own. Pure
Python, so the encoding is tested without a site (tests/test_barcode.py). Code set B only: the
ticket carries the works order number (letters, digits and dashes), which is what the Print Floor
looks a scan up by.
"""

from html import escape

# Bar and space widths, in modules, of each Code 128 value 0-106 (103-105 are the start codes,
# 106 the stop). Every symbol starts with a bar.
PATTERNS = (
	"212222", "222122", "222221", "121223", "121322", "131222", "122213", "122312", "132212", "221213",
	"221312", "231212", "112232", "122132", "122231", "113222", "123122", "123221", "223211", "221132",
	"221231", "213212", "223112", "312131", "311222", "321122", "321221", "312212", "322112", "322211",
	"212123", "212321", "232121", "111323", "131123", "131321", "112313", "132113", "132311", "211313",
	"231113", "231311", "112133", "112331", "132131", "113123", "113321", "133121", "313121", "211331",
	"231131", "213113", "213311", "213131", "311123", "311321", "331121", "312113", "312311", "332111",
	"314111", "221411", "431111", "111224", "111422", "121124", "121421", "141122", "141221", "112214",
	"112412", "122114", "122411", "142112", "142211", "241211", "221114", "413111", "241112", "134111",
	"111242", "121142", "121241", "114212", "124112", "124211", "411212", "421112", "421211", "212141",
	"214121", "412121", "111143", "111341", "131141", "114113", "114311", "411113", "411311", "113141",
	"114131", "311141", "411131", "211412", "211214", "211232", "2331112",
)
START_B = 104
STOP = 106
QUIET = 10  # modules of white either side, so a scanner finds the edges


def values(text):
	"""The Code 128 values for `text` in code set B: start, data, check digit, stop."""
	if not text:
		raise ValueError("Nothing to encode.")
	data = []
	for char in text:
		code = ord(char)
		if not 32 <= code <= 127:
			raise ValueError(f"{char!r} cannot go in a Code 128 B barcode.")
		data.append(code - 32)
	check = (START_B + sum(position * value for position, value in enumerate(data, start=1))) % 103
	return [START_B, *data, check, STOP]


def widths(text):
	"""The barcode as a run of widths in modules, bar first, without the quiet zones."""
	return [int(width) for value in values(text) for width in PATTERNS[value]]


def svg(text, height=40):
	"""The barcode as an SVG drawing, one unit per module. Scale it with CSS width."""
	x, bars = QUIET, []
	for i, width in enumerate(widths(text)):
		if i % 2 == 0:
			bars.append(f'<rect x="{x}" y="0" width="{width}" height="{height}"/>')
		x += width
	total = x + QUIET
	return (
		f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {total} {height}" preserveAspectRatio="none" '
		f'shape-rendering="crispEdges" role="img" aria-label="Barcode {escape(text)}">' + "".join(bars) + "</svg>"
	)


def fp_barcode(text):
	"""The barcode for a print format: `{{ fp_barcode(doc.name) }}`. Registered under its own name,
	because every app's Jinja methods share one namespace."""
	return svg(text)
