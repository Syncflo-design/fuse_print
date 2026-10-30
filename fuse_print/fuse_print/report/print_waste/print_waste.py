"""Print Waste — what each workstation spoiled, why, and what it cost.

One row per submitted job card: what reached the step, what it passed on, what it spoiled and
why. Waste is costed at the run's own recipe: the material cost of one finished item on its bill
of materials, and the media in it. A spoiled sticker has had all of its media printed on, so
that is what each one lost costs.

The summary sets the runs' actual waste against each product's standard, the % Process Loss on
its bill of materials, weighted by run size.
"""

import frappe
from frappe.utils import flt

# Media is whatever a recipe uses by area. ERPNext's own unit name; a site whose units come from
# Intacct may call it something else, and is added here.
MEDIA_UOMS = ("Square Meter",)

COLUMNS = [
	{"fieldname": "posting_date", "label": "Date", "fieldtype": "Date", "width": 95},
	{"fieldname": "work_order", "label": "Works Order", "fieldtype": "Link", "options": "Work Order", "width": 150},
	{"fieldname": "customer", "label": "Customer", "fieldtype": "Data", "width": 170},
	{"fieldname": "item_code", "label": "Product", "fieldtype": "Link", "options": "Item", "width": 120},
	{"fieldname": "operation", "label": "Step", "fieldtype": "Link", "options": "Operation", "width": 90},
	{"fieldname": "workstation", "label": "Workstation", "fieldtype": "Link", "options": "Workstation", "width": 150},
	{"fieldname": "operator", "label": "Operator", "fieldtype": "Data", "width": 130},
	{"fieldname": "received", "label": "Reached Step", "fieldtype": "Float", "precision": 0, "width": 105},
	{"fieldname": "good", "label": "Passed On", "fieldtype": "Float", "precision": 0, "width": 95},
	{"fieldname": "waste", "label": "Spoiled", "fieldtype": "Float", "precision": 0, "width": 85},
	{"fieldname": "waste_pct", "label": "Spoiled %", "fieldtype": "Percent", "width": 90},
	{"fieldname": "reason", "label": "Reason", "fieldtype": "Data", "width": 170},
	{"fieldname": "note", "label": "Operator's Note", "fieldtype": "Data", "width": 220},
	{"fieldname": "media_lost", "label": "Media Lost (m²)", "fieldtype": "Float", "precision": 2, "width": 120},
	{"fieldname": "cost", "label": "Waste Cost", "fieldtype": "Currency", "width": 110},
	{"fieldname": "job_card", "label": "Job Card", "fieldtype": "Link", "options": "Job Card", "width": 120},
]


def execute(filters=None):
	filters = frappe._dict(filters or {})
	cards = _job_cards(filters)
	if not cards:
		return COLUMNS, [], None, None, []

	recipes = _recipes({card.bom_no for card in cards if card.bom_no})
	runs = _runs({card.work_order for card in cards if card.work_order})
	operators = _operators([card.name for card in cards])

	rows = []
	for card in cards:
		recipe = recipes.get(card.bom_no, {})
		run = runs.get(card.work_order, {})
		good, waste = flt(card.total_completed_qty), flt(card.fp_waste_qty)
		received = good + waste
		rows.append({
			"posting_date": card.posting_date,
			"work_order": card.work_order,
			"customer": run.get("customer"),
			"item_code": card.production_item,
			"operation": card.operation,
			"workstation": card.workstation,
			"operator": operators.get(card.name),
			"received": received,
			"good": good,
			"waste": waste,
			"waste_pct": waste / received * 100 if received else 0,
			"reason": card.fp_waste_reason,
			"note": card.fp_waste_note,
			"media_lost": waste * recipe.get("media", 0),
			"cost": waste * recipe.get("cost", 0),
			"job_card": card.name,
		})

	return COLUMNS, rows, None, _chart(rows), _summary(rows, runs, recipes)


def _job_cards(filters):
	conditions = {"docstatus": 1, "company": filters.company, "is_corrective_job_card": 0}
	if filters.from_date and filters.to_date:
		conditions["posting_date"] = ("between", [filters.from_date, filters.to_date])
	if filters.workstation:
		conditions["workstation"] = filters.workstation
	if filters.reason:
		conditions["fp_waste_reason"] = filters.reason
	return frappe.get_all(
		"Job Card",
		filters=conditions,
		fields=["name", "posting_date", "work_order", "production_item", "operation", "workstation",
			"total_completed_qty", "fp_waste_qty", "fp_waste_reason", "fp_waste_note", "bom_no", "sequence_id"],
		order_by="posting_date desc, work_order desc, sequence_id asc",
	)


def _recipes(boms):
	"""Per finished item on each recipe: material cost, media in m², and the standard waste %."""
	recipes = {}
	for bom in frappe.get_all("BOM", filters={"name": ("in", list(boms))},
			fields=["name", "quantity", "raw_material_cost", "process_loss_percentage"]):
		per = flt(bom.quantity) or 1
		recipes[bom.name] = {"per": per, "cost": flt(bom.raw_material_cost) / per, "media": 0.0,
			"standard": flt(bom.process_loss_percentage)}
	for line in frappe.get_all("BOM Item", filters={"parent": ("in", list(boms)), "parenttype": "BOM",
			"stock_uom": ("in", MEDIA_UOMS)}, fields=["parent", "stock_qty"]):
		recipe = recipes[line.parent]
		recipe["media"] += flt(line.stock_qty) / recipe["per"]
	return recipes


def _runs(work_orders):
	"""Each works order's run size, recipe and customer."""
	runs = {}
	orders = frappe.get_all("Work Order", filters={"name": ("in", list(work_orders))},
		fields=["name", "qty", "bom_no", "sales_order"])
	customers = dict(frappe.get_all("Sales Order",
		filters={"name": ("in", [order.sales_order for order in orders if order.sales_order])},
		fields=["name", "customer_name"], as_list=True))
	for order in orders:
		runs[order.name] = {"qty": flt(order.qty), "bom": order.bom_no, "customer": customers.get(order.sales_order)}
	return runs


def _operators(job_cards):
	"""Who ran each job card: the first person on its time log."""
	first = {}
	for log in frappe.get_all("Job Card Time Log", filters={"parent": ("in", job_cards), "parenttype": "Job Card",
			"employee": ("is", "set")}, fields=["parent", "employee"], order_by="idx asc"):
		first.setdefault(log.parent, log.employee)
	names = dict(frappe.get_all("Employee", filters={"name": ("in", list(set(first.values())))},
		fields=["name", "employee_name"], as_list=True))
	return {card: names.get(employee) for card, employee in first.items()}


def _chart(rows):
	by_reason = {}
	for row in rows:
		if row["waste"]:
			reason = row["reason"] or "No reason"
			by_reason[reason] = by_reason.get(reason, 0) + row["cost"]
	if not by_reason:
		return None
	ordered = sorted(by_reason.items(), key=lambda item: item[1], reverse=True)
	return {
		"data": {"labels": [reason for reason, _ in ordered],
			"datasets": [{"name": "Waste cost", "values": [round(cost, 2) for _, cost in ordered]}]},
		"type": "bar",
		"fieldtype": "Currency",
	}


def _summary(rows, runs, recipes):
	"""Actual waste against standard over the runs shown, weighted by run size."""
	spoiled = sum(row["waste"] for row in rows)
	shown = {row["work_order"] for row in rows if row["work_order"] in runs}
	run_qty = sum(runs[name]["qty"] for name in shown)
	standard_qty = sum(runs[name]["qty"] * recipes.get(runs[name]["bom"], {}).get("standard", 0) for name in shown)

	actual = spoiled / run_qty * 100 if run_qty else 0
	standard = standard_qty / run_qty if run_qty else 0
	return [
		{"value": len(shown), "label": "Runs", "datatype": "Int"},
		{"value": spoiled, "label": "Spoiled", "datatype": "Float"},
		{"value": actual, "label": "Waste Rate", "datatype": "Percent",
			"indicator": "Red" if actual > standard else "Green"},
		{"value": standard, "label": "Standard", "datatype": "Percent"},
		{"value": sum(row["media_lost"] for row in rows), "label": "Media Lost (m²)", "datatype": "Float"},
		{"value": sum(row["cost"] for row in rows), "label": "Waste Cost", "datatype": "Currency"},
	]
