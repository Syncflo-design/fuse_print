"""What this app contributes to Fuse: its switch and its two tiles.

Kept apart from install.py: these are read on every Fuse Home load, by other apps, and that call
has no business importing set-up code.

The key is permanent. Renaming it orphans a client's saved setting and silently switches the
module back on.
"""

MODULE_KEY = "fp_waste"

MODULES = [
	{
		"key": MODULE_KEY,
		"label": "Print: Floor and Waste",
		"description": "The Print Floor, where each step of a run is started and finished at its workstation on "
		"a phone, tablet or scanner, with what it spoiled and why; and the Print Waste report: what the waste "
		"costs by job, workstation, operator and reason, against each product's standard.",
	},
]

# Lucide "printer" and "scissors", inner SVG only — fuse_theme wraps them. The emoji is what Fuse
# Home draws where it does not draw stroked icons, which is why both are given.
PRINTER = (
	'<path d="M6 9V2h12v7"></path><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2">'
	'</path><rect x="6" y="14" width="12" height="8"></rect>'
)
SCISSORS = (
	'<circle cx="6" cy="6" r="3"></circle><path d="M8.12 8.12 12 12"></path><path d="M20 4 8.12 15.88"></path>'
	'<circle cx="6" cy="18" r="3"></circle><path d="M14.8 14.8 20 20"></path>'
)


def get_modules():
	return [dict(module) for module in MODULES]


def get_tiles():
	return [
		{
			"key": "fp_floor",
			"module": MODULE_KEY,
			"label": "Print Floor",
			"blurb": "Each step at its workstation: scan the ticket, say what was good and what was spoiled",
			"icon": "🖨️",
			"svg": PRINTER,
			"route": ["fuse-print-floor"],
			"roles": ["Manufacturing User", "Manufacturing Manager", "System Manager"],
		},
		{
			"key": "fp_waste",
			"module": MODULE_KEY,
			"label": "Print Waste",
			"blurb": "What was spoiled, where, why, and what it cost",
			"icon": "✂️",
			"svg": SCISSORS,
			"route": ["query-report", "Print Waste"],
			"roles": ["Manufacturing User", "Manufacturing Manager", "Stock Controller", "System Manager"],
		},
	]
