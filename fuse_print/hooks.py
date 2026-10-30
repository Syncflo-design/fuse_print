app_name        = "fuse_print"
app_title       = "Fuse Print"
app_publisher   = "Syncflo"
app_description = "Sticker and label printing for Fuse: waste recorded at each workstation with a reason, and what it costs."
app_email       = "ops@syncflo.co.za"
app_license     = "Proprietary"

# ERPNext for the manufacturing engine; fuse_core for the module switches; fuse_manufacturing for
# Receiving and Picking. Everything here is ERPNext's own Work Order, Job Card and Stock Entry —
# this app adds where the waste happened and why, not a second way to make things.
required_apps = ["erpnext", "fuse_core", "fuse_manufacturing"]

# Both, and fuse_print.install.after_install by hand as well: after_migrate has been seen not to
# fire on a Frappe Cloud deploy. Everything in it is idempotent.
after_install = "fuse_print.install.after_install"
after_migrate = "fuse_print.install.after_install"

# The job ticket's barcode, for the Job Ticket print format. Every app's Jinja methods share one
# namespace, so it goes by a name of its own.
jinja = {"methods": ["fuse_print.barcode.fp_barcode"]}

# The demo loader's menu item, on the demo site only.
doctype_list_js = {"Work Order": "public/js/work_order_list.js"}

doc_events = {
	# ERPNext's own process loss on a job card counts every step before it as well. What this
	# step spoiled is worked out alongside it, and a submit with waste needs a reason.
	"Job Card": {
		"validate": "fuse_print.waste.set_step_waste",
		"before_submit": "fuse_print.waste.require_reason",
	},
}

# How this app reaches Fuse: its switch (Active Modules on Intacct Settings) and its tile on
# Fuse Home. Callables, so the hook values merge as plain strings.
fuse_modules = ["fuse_print.registry.get_modules"]
fuse_tiles = ["fuse_print.registry.get_tiles"]

# Nothing here posts to Intacct of its own. A run is an ordinary Manufacture entry, which
# fuse_manufacturing posts where posting is on.
fuse_processes = []

# Tells the desk whether this is the Fuse demo site, so the demo loader's menu item appears
# there and on no client's site.
extend_bootinfo = "fuse_print.demo.sticker_printing.boot"
