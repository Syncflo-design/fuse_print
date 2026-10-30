"""Put a site's print-waste configuration in step with this version of the app.

Idempotent: it runs on install, on every migrate, and by hand (`fuse_print.install.after_install`,
System Manager) when a Frappe Cloud deploy skips after_migrate.
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from fuse_print import registry
from fuse_print.waste import REASONS

# On the job card, under ERPNext's own quantities. Prefixed `fp_`, so they are plainly this app's.
CUSTOM_FIELDS = {
	"Job Card": [
		{"fieldname": "fp_waste_qty", "fieldtype": "Float", "label": "Waste at this Step",
			"insert_after": "total_completed_qty", "read_only": 1, "no_copy": 1,
			"description": "What this workstation spoiled: what reached it, less what it passed on. "
			"Process Loss counts every step before this one as well."},
		{"fieldname": "fp_waste_reason", "fieldtype": "Select", "label": "Waste Reason",
			"options": "\n" + "\n".join(REASONS), "insert_after": "fp_waste_qty", "no_copy": 1,
			"in_standard_filter": 1, "description": "Needed before submitting when this step spoiled anything."},
		{"fieldname": "fp_waste_note", "fieldtype": "Small Text", "label": "Operator's Note",
			"insert_after": "fp_waste_reason", "no_copy": 1,
			"description": "In the operator's words, typed or spoken on the Print Floor."},
	],
}


@frappe.whitelist()
def after_install():
	# Only over HTTP. The same function is the after_install and after_migrate hook, where there
	# is no session to check and a refusal would take the whole migrate down.
	if frappe.request:
		frappe.only_for("System Manager")

	create_custom_fields(CUSTOM_FIELDS, ignore_validate=True)
	switches = _sync_switches()
	frappe.db.commit()
	return {"custom_fields": sum(len(fields) for fields in CUSTOM_FIELDS.values()), "switches": switches}


def _sync_switches():
	"""Get this app's switch into Active Modules now, not at the next migrate."""
	try:
		from fuse_core import modules

		modules.sync_modules()
	except Exception:
		frappe.log_error(title="Fuse Print: could not seed the module switch", message=frappe.get_traceback())
		return None
	return [module["key"] for module in registry.get_modules()]
