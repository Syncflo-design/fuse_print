"""The sticker printing demo profile: a sticker and label printer, already running.

Demo setup, not product. Run on the Fuse demo site from the Work Order list (menu: Load Sticker
Printing Demo). Every name is fictitious — no prospect's name appears anywhere. Nothing is read
from or written to Intacct.

What it makes:
  * its own company, "Sticker Printing", beside the others, with customer, supplier and item groups
    of the same name, a media store, an ink and consumables store, work in progress, finished
    goods and an offcuts store, and perpetual inventory off: on a live site Intacct keeps the books;
  * media by the square metre (white and clear vinyl, paper label stock, overlaminate), ink by the
    litre and roll cores; three products (round stickers, paper labels on a roll, window decals),
    each with a recipe per 1,000, its route, its standard waste as % Process Loss and, for the
    vinyl ones, the offcut each run puts back into stock;
  * the line: five workstations with hourly rates, an operation for each (Print, Laminate, Cut,
    Weed, Pack), two routes and five operators;
  * six weeks of history: media and ink ordered and received, six jobs run with what each step
    spoiled and why, five of them delivered with their orders closed. One printer operator spoils
    about twice as much at setup as the other, for the report to find;
  * the live steps, made again by any later load once a demo has used them: a works order for
    2,000 round stickers with its five job cards open for the Print Floor, an order each for media
    and for ink waiting to be received, and a finished job's order waiting to be picked;
  * the presenter's Fuse Home: Module Profile "Sticker Printing Presenter", which shows only this
    profile's tiles, with this app's tile hidden from every other presenter. Given a presenter
    login that already exists, that login is put on it and defaulted to the company. The login's
    roles are never touched: on the demo site nothing may stop on a permission.

History is made once. A later load leaves it alone and only restores the live steps, so the stock
the history built is never moved twice. Restore the master backup when the stock runs low.
"""

from datetime import datetime, timedelta

import frappe
from frappe.utils import flt, get_datetime, getdate, nowdate

from fuse_print import floor, registry

COMPANY = "Sticker Printing"
ABBR = "STK"
GROUP = "Sticker Printing"
PROFILE = "Sticker Printing Presenter"
PRESENTER = "sticker_printing@syncflo.co.za"
# What the presenter's Fuse Home keeps. Every other key on the site is hidden from it.
KEEP = {registry.MODULE_KEY, "material_request", "receiving", "boms", "planning", "works_orders", "shop_floor",
	"stock_control", "picking", "support"}

MEDIA = f"Media Store - {ABBR}"
INKS = f"Ink and Consumables - {ABBR}"
WIP = f"Work In Progress - {ABBR}"
FG = f"Finished Goods - {ABBR}"
OFFCUTS = f"Offcuts - {ABBR}"

SQM, LITRE, EACH, NOS = "Square Meter", "Litre", "Each", "Nos"

# (name, unit, store, rate). Rates are illustrative.
MATERIALS = {
	"STK-VWG-1370": ("White gloss vinyl, 1370 mm roll", SQM, MEDIA, 38.00),
	"STK-VCL-1370": ("Clear vinyl, 1370 mm roll", SQM, MEDIA, 44.00),
	"STK-PAP-1000": ("Semi-gloss paper label stock, 1000 mm roll", SQM, MEDIA, 14.50),
	"STK-LAM-1370": ("Gloss overlaminate, 1370 mm roll", SQM, MEDIA, 22.00),
	"STK-INK-CMYK": ("Eco-solvent ink, CMYK", LITRE, INKS, 1250.00),
	"STK-CORE-76": ("76 mm cardboard core", EACH, INKS, 3.50),
}
# Offcuts: the roll-width trim and roll ends a vinyl run leaves, good for small jobs. Each finished
# run puts them into the offcuts store at a quarter of the media's value, which takes that off
# the cost of the run. (name, unit, store, rate)
OFFCUT_ITEMS = {
	"STK-VWG-OFF": ("White gloss vinyl offcut, reusable", SQM, OFFCUTS, 9.50),
	"STK-VCL-OFF": ("Clear vinyl offcut, reusable", SQM, OFFCUTS, 11.00),
}

# (operation, workstation, workstation type, labour, electricity, depreciation per hour, description)
LINE = [
	("Print", "PR-01 Printer", "Printing", 220, 180, 250, "Wide-format eco-solvent printer, 1.37 m."),
	("Laminate", "LM-01 Laminator", "Laminating", 200, 40, 40, "Cold roll laminator, 1.6 m."),
	("Cut", "CT-01 Cutter", "Cutting", 220, 60, 140, "Contour cutter reading print registration marks."),
	("Weed", "WD-01 Weeding Bench", "Weeding", 160, 0, 20, "Hand weeding and matrix stripping."),
	("Pack", "PK-01 Packing Bench", "Packing", 150, 0, 10, "Counting, rolling, boxing and labelling."),
]
LAMINATED = "Stickers, laminated"
PLAIN = "Labels and decals"
ROUTES = {
	LAMINATED: ["Print", "Laminate", "Cut", "Weed", "Pack"],
	PLAIN: ["Print", "Cut", "Weed", "Pack"],
}

# Per 1,000 finished: materials (code, quantity), offcuts back to stock (code, m²), minutes at
# each step in route order, standard waste % (the recipe's % Process Loss) and the selling price
# of one. Paper labels leave no offcut worth keeping.
ROUND, LABEL, DECAL = "STK-RND-100", "STK-LBL-6040", "STK-WIN-A4"
PRODUCTS = {
	ROUND: {"name": "Round sticker 100 mm, gloss laminated", "route": LAMINATED, "standard": 6, "price": 4.20,
		"materials": [("STK-VWG-1370", 11.03), ("STK-LAM-1370", 11.03), ("STK-INK-CMYK", 0.11)],
		"offcuts": [("STK-VWG-OFF", 0.55)],
		"minutes": [45, 20, 40, 60, 15]},
	LABEL: {"name": "Product label 60 x 40 mm, paper, on roll", "route": PLAIN, "standard": 4, "price": 0.85,
		"materials": [("STK-PAP-1000", 2.71), ("STK-INK-CMYK", 0.027), ("STK-CORE-76", 1)],
		"offcuts": [],
		"minutes": [15, 20, 10, 10]},
	DECAL: {"name": "Window decal A4, clear vinyl, contour cut", "route": PLAIN, "standard": 8, "price": 38.00,
		"materials": [("STK-VCL-1370", 65.5), ("STK-INK-CMYK", 0.655)],
		"offcuts": [("STK-VCL-OFF", 5.25)],
		"minutes": [90, 120, 240, 30]},
}

SUPPLIERS = {"media": "Highveld Media Supplies (Pty) Ltd", "ink": "Inkline Distributors (Pty) Ltd"}
CUSTOMERS = {
	"brew": "Mountain Brew Craft Beer (Pty) Ltd",
	"foods": "Greenleaf Organic Foods (Pty) Ltd",
	"events": "Eventide Events (Pty) Ltd",
	"auto": "Coastal Auto Detailing CC",
	"school": "Hillcrest Preparatory School",
}

# (first name, last name, designation). Fictitious.
OPERATORS = {
	"thabo": ("Thabo", "Nkosi", "Printer Operator"),
	"sipho": ("Sipho", "Mahlangu", "Printer Operator"),
	"anele": ("Anele", "Dube", "Finishing Operator"),
	"ruth": ("Ruth", "Jacobs", "Weeding"),
	"lindiwe": ("Lindiwe", "Mokoena", "Packer"),
}
# Who works each step after printing; the printer is chosen per job.
CREW = {"Laminate": "anele", "Cut": "anele", "Weed": "ruth", "Pack": "lindiwe"}

SETUP, MISPRINT, MEDIA_FAULT = "Setup and colour match", "Misprint", "Media fault"
LAMINATION, REGISTER, WEEDING, END_OF_ROLL, OTHER = (
	"Lamination fault", "Cut out of register", "Weeding damage", "End of roll", "Other")

# Six jobs, oldest first: (customer, product, quantity, ordered, ran, printer, what each step
# spoiled, why and the operator's note if any, delivered — working days ago). Sipho's setup waste
# runs at about twice Thabo's.
JOBS = [
	("brew", LABEL, 20000, 30, 27, "thabo", [(300, SETUP), (120, REGISTER), (0, None), (0, None)], 26),
	("events", ROUND, 5000, 26, 22, "sipho", [(250, SETUP), (60, LAMINATION, "Laminate creased at the roll splice."),
		(40, REGISTER), (90, WEEDING), (0, None)], 21),
	("auto", DECAL, 400, 20, 17, "thabo", [(12, MISPRINT), (6, REGISTER),
		(18, WEEDING, "Fine lettering tears on the small text. Ask for a heavier font next time."), (0, None)], 16),
	("foods", LABEL, 30000, 15, 11, "sipho", [(900, SETUP, "Brand green took three passes to match the swatch."),
		(210, END_OF_ROLL), (60, WEEDING), (0, None)], 10),
	("school", ROUND, 3000, 9, 6, "thabo", [(90, SETUP), (0, None), (45, REGISTER), (30, WEEDING), (0, None)], 5),
	# Made and not delivered: the order the presenter picks.
	("brew", LABEL, 15000, 6, 3, "sipho", [(600, SETUP), (90, REGISTER), (0, None), (15, OTHER)], None),
]
PICK = JOBS[-1]
# The run the presenter records live.
LIVE = ("events", ROUND, 2000)

# (supplier, [(item, quantity)], working days ago) — what the history receives.
DELIVERIES = [
	("media", [("STK-VWG-1370", 200), ("STK-VCL-1370", 60), ("STK-PAP-1000", 300), ("STK-LAM-1370", 200)], 32),
	("ink", [("STK-INK-CMYK", 6), ("STK-CORE-76", 100)], 31),
	("media", [("STK-PAP-1000", 200)], 13),
]
# What the presenter receives live: media into Media Store, ink into Ink and Consumables.
RECEIVE = {
	"media": [("STK-VWG-1370", 150), ("STK-LAM-1370", 150), ("STK-PAP-1000", 300)],
	"ink": [("STK-INK-CMYK", 4), ("STK-CORE-76", 200)],
}


def is_demo_site():
	"""Only a site whose config sets `fuse_demo_site` is a demo site. A client's never is."""
	return bool(frappe.conf.get("fuse_demo_site"))


def boot(bootinfo):
	bootinfo.fuse_demo_site = is_demo_site()


@frappe.whitelist()
def load(presenter=None):
	frappe.only_for("System Manager")
	if not is_demo_site():
		frappe.throw(
			"The sticker printing demo loads only on the Fuse demo site — set fuse_demo_site in that site's "
			"config. It never loads on a client's site."
		)
	from fuse_print.install import after_install

	after_install()
	_company()
	_masters()
	_line()
	_operators()
	_recipes()
	profiles = _presenter_profiles()
	who = _presenter(presenter) if presenter else None

	history = None
	if not frappe.db.exists("Work Order", {"company": COMPANY, "docstatus": 1}):
		history = _history()
	live = _live()
	frappe.db.commit()
	# Each job card and works order announced itself as it was made. True, and not dozens of
	# pop-ups to show the presenter.
	frappe.clear_messages()
	return {"summary": _summary(history, live, profiles, who)}


# ──────────────────────────────────────────────────────────────────────────────
# Dates
# ──────────────────────────────────────────────────────────────────────────────


def _day(working_days_ago):
	"""The date `working_days_ago` weekdays before today."""
	day = getdate(nowdate())
	counted = 0
	while counted < working_days_ago:
		day -= timedelta(days=1)
		if day.weekday() < 5:
			counted += 1
	return day


def _backdate(doctype, name, on, at="07:45:00"):
	frappe.db.set_value(doctype, name, "creation", f"{on} {at}", update_modified=False)


# ──────────────────────────────────────────────────────────────────────────────
# Masters
# ──────────────────────────────────────────────────────────────────────────────


def _company():
	if not frappe.db.exists("Company", COMPANY):
		frappe.get_doc({
			"doctype": "Company", "company_name": COMPANY, "abbr": ABBR, "country": "South Africa",
			"default_currency": "ZAR", "create_chart_of_accounts_based_on": "Standard Template",
			"chart_of_accounts": "Standard", "enable_perpetual_inventory": 0,
		}).insert(ignore_permissions=True)
	parent = frappe.db.get_value("Warehouse", {"company": COMPANY, "is_group": 1, "parent_warehouse": ("is", "not set")})
	for warehouse in (MEDIA, INKS, WIP, FG, OFFCUTS):
		if not frappe.db.exists("Warehouse", warehouse):
			frappe.get_doc({"doctype": "Warehouse", "warehouse_name": warehouse.rsplit(" - ", 1)[0],
				"company": COMPANY, "parent_warehouse": parent}).insert(ignore_permissions=True)


def _leaf_group(doctype, field, parent_field):
	if frappe.db.exists(doctype, GROUP):
		return
	root = frappe.db.get_value(doctype, {"is_group": 1, parent_field: ("is", "not set")}, "name")
	frappe.get_doc({"doctype": doctype, field: GROUP, parent_field: root, "is_group": 0}).insert(ignore_permissions=True)


def _masters():
	_leaf_group("Customer Group", "customer_group_name", "parent_customer_group")
	_leaf_group("Supplier Group", "supplier_group_name", "parent_supplier_group")
	_leaf_group("Item Group", "item_group_name", "parent_item_group")

	territory = "South Africa" if frappe.db.exists("Territory", "South Africa") else frappe.get_all(
		"Territory", filters={"is_group": 0}, pluck="name", limit=1)[0]
	for customer in CUSTOMERS.values():
		if not frappe.db.get_value("Customer", {"customer_name": customer}):
			frappe.get_doc({"doctype": "Customer", "customer_name": customer, "customer_group": GROUP,
				"territory": territory, "customer_type": "Company"}).insert(ignore_permissions=True)
	for supplier in SUPPLIERS.values():
		if not frappe.db.get_value("Supplier", {"supplier_name": supplier}):
			frappe.get_doc({"doctype": "Supplier", "supplier_name": supplier, "supplier_group": GROUP,
				"supplier_type": "Company", "country": "South Africa"}).insert(ignore_permissions=True)

	for code, (name, uom, store, rate) in MATERIALS.items():
		_item(code, name, uom=uom, warehouse=store, purchase=1, valuation_rate=rate)
	for code, (name, uom, store, rate) in OFFCUT_ITEMS.items():
		_item(code, name, uom=uom, warehouse=store, valuation_rate=rate)
	for code, spec in PRODUCTS.items():
		_item(code, spec["name"], uom=NOS, warehouse=FG, sales=1)


def _item(code, name, *, uom, warehouse, purchase=0, sales=0, valuation_rate=None):
	if frappe.db.exists("Item", code):
		return
	doc = frappe.get_doc({
		"doctype": "Item", "item_code": code, "item_name": name, "description": name, "item_group": GROUP,
		"stock_uom": uom, "is_stock_item": 1, "include_item_in_manufacturing": 1,
		"is_purchase_item": purchase, "is_sales_item": sales, "valuation_rate": valuation_rate or 0,
	})
	doc.append("item_defaults", {"company": COMPANY, "default_warehouse": warehouse})
	doc.insert(ignore_permissions=True)


def _line():
	"""Workstations with their hourly costs, an operation for each, and the two routes."""
	for component in ("Labour", "Electricity", "Depreciation"):
		if not frappe.db.exists("Workstation Operating Component", component):
			frappe.get_doc({"doctype": "Workstation Operating Component", "component_name": component}).insert(
				ignore_permissions=True)

	for operation, workstation, kind, labour, power, depreciation, description in LINE:
		if not frappe.db.exists("Workstation Type", kind):
			frappe.get_doc({"doctype": "Workstation Type", "workstation_type": kind}).insert(ignore_permissions=True)
		if not frappe.db.exists("Workstation", workstation):
			doc = frappe.get_doc({"doctype": "Workstation", "workstation_name": workstation, "workstation_type": kind,
				"production_capacity": 1, "description": description})
			for component, cost in (("Labour", labour), ("Electricity", power), ("Depreciation", depreciation)):
				if cost:
					doc.append("workstation_costs", {"operating_component": component, "operating_cost": cost})
			doc.insert(ignore_permissions=True)
		if not frappe.db.exists("Operation", operation):
			frappe.get_doc({"doctype": "Operation", "name": operation, "workstation": workstation}).insert(
				ignore_permissions=True)

	stations = {operation: workstation for operation, workstation, *_ in LINE}
	for route, operations in ROUTES.items():
		if frappe.db.exists("Routing", route):
			continue
		# The minutes per 1,000 of the first product on this route, so a recipe that picks the route
		# up in the form gets times that make sense.
		minutes = next(spec["minutes"] for spec in PRODUCTS.values() if spec["route"] == route)
		doc = frappe.get_doc({"doctype": "Routing", "routing_name": route})
		for sequence, (operation, time_in_mins) in enumerate(zip(operations, minutes, strict=True), start=1):
			doc.append("operations", {"operation": operation, "workstation": stations[operation],
				"sequence_id": sequence, "time_in_mins": time_in_mins})
		doc.insert(ignore_permissions=True)


def _operators():
	for first, last, designation in OPERATORS.values():
		if frappe.db.exists("Employee", {"first_name": first, "last_name": last, "company": COMPANY}):
			continue
		if not frappe.db.exists("Designation", designation):
			frappe.get_doc({"doctype": "Designation", "designation_name": designation}).insert(ignore_permissions=True)
		frappe.get_doc({
			"doctype": "Employee", "first_name": first, "last_name": last, "company": COMPANY,
			"designation": designation, "gender": "Prefer not to say", "date_of_birth": "1990-03-01",
			"date_of_joining": "2022-02-01", "status": "Active",
		}).insert(ignore_permissions=True)


def _employee(key):
	first, last, _ = OPERATORS[key]
	return frappe.db.get_value("Employee", {"first_name": first, "last_name": last, "company": COMPANY})


def _recipes():
	"""A recipe per product, per 1,000: materials from their stores, the route, the standard waste."""
	stations = {operation: workstation for operation, workstation, *_ in LINE}
	for code, spec in PRODUCTS.items():
		if frappe.db.exists("BOM", {"item": code, "is_default": 1, "docstatus": 1}):
			continue
		bom = frappe.new_doc("BOM")
		bom.update({"item": code, "company": COMPANY, "quantity": 1000, "is_active": 1, "is_default": 1,
			"with_operations": 1, "routing": spec["route"], "rm_cost_as_per": "Valuation Rate",
			"process_loss_percentage": spec["standard"]})
		for material, qty in spec["materials"]:
			bom.append("items", {"item_code": material, "qty": qty, "uom": MATERIALS[material][1],
				"source_warehouse": MATERIALS[material][2]})
		# ERPNext v16 calls a by-product a secondary item. "Scrap" sends it to the works order's
		# scrap warehouse, the offcuts store, valued at its own rate.
		for offcut, qty in spec["offcuts"]:
			bom.append("secondary_items", {"item_code": offcut, "secondary_item_type": "Scrap", "qty": qty,
				"stock_qty": qty, "uom": SQM, "stock_uom": SQM, "conversion_factor": 1,
				"valuation_type": "Valuation Rate"})
		for sequence, (operation, minutes) in enumerate(zip(ROUTES[spec["route"]], spec["minutes"], strict=True), start=1):
			bom.append("operations", {"operation": operation, "workstation": stations[operation],
				"sequence_id": sequence, "time_in_mins": minutes})
		bom.insert(ignore_permissions=True)
		bom.submit()


def _bom(code):
	return frappe.db.get_value("BOM", {"item": code, "is_default": 1, "docstatus": 1}, "name")


# ──────────────────────────────────────────────────────────────────────────────
# Documents
# ──────────────────────────────────────────────────────────────────────────────


def _party(doctype, name):
	field = "customer_name" if doctype == "Customer" else "supplier_name"
	return frappe.db.get_value(doctype, {field: name}) or name


def _purchase_order(supplier_key, lines, on):
	"""A purchase order. Each line goes to its material's own store, which is where it is received."""
	order = frappe.new_doc("Purchase Order")
	order.update({"supplier": _party("Supplier", SUPPLIERS[supplier_key]), "company": COMPANY,
		"transaction_date": on, "schedule_date": on + timedelta(days=3)})
	for code, qty in lines:
		order.append("items", {"item_code": code, "qty": qty, "rate": MATERIALS[code][3],
			"warehouse": MATERIALS[code][2], "schedule_date": on + timedelta(days=3)})
	order.insert(ignore_permissions=True)
	order.submit()
	_backdate("Purchase Order", order.name, on, "09:00:00")
	return order.name


def _receive(order, on):
	from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_receipt

	receipt = make_purchase_receipt(order)
	receipt.update({"posting_date": on, "posting_time": "10:30:00", "set_posting_time": 1})
	receipt.insert(ignore_permissions=True)
	receipt.submit()
	_backdate("Purchase Receipt", receipt.name, on, "10:30:00")
	return receipt.name


def _order(customer_key, code, qty, on, po_no):
	order = frappe.new_doc("Sales Order")
	order.update({"customer": _party("Customer", CUSTOMERS[customer_key]), "company": COMPANY,
		"transaction_date": on, "delivery_date": on + timedelta(days=7), "po_no": po_no, "set_warehouse": FG})
	order.append("items", {"item_code": code, "qty": qty, "rate": PRODUCTS[code]["price"], "warehouse": FG,
		"delivery_date": on + timedelta(days=7)})
	order.insert(ignore_permissions=True)
	order.submit()
	_backdate("Sales Order", order.name, on, "10:15:00")
	return order.name


def _work_order(code, qty, on, sales_order):
	"""A works order on the product's recipe. Submitting it opens a job card for every step."""
	order = frappe.new_doc("Work Order")
	order.update({"production_item": code, "bom_no": _bom(code), "qty": qty, "company": COMPANY,
		"fg_warehouse": FG, "wip_warehouse": WIP, "scrap_warehouse": OFFCUTS, "skip_transfer": 1, "use_multi_level_bom": 0,
		"planned_start_date": f"{on} 07:30:00", "sales_order": sales_order})
	order.get_items_and_operations_from_bom()
	order.insert(ignore_permissions=True)
	order.submit()
	_backdate("Work Order", order.name, on)
	return order.name


def _steps(work_order, on, printer, spoiled):
	"""Each step's job card: who ran it, for how long, what it passed on and why it spoiled any."""
	qty = flt(frappe.db.get_value("Work Order", work_order, "qty"))
	cards = frappe.get_all("Job Card", filters={"work_order": work_order, "docstatus": 0},
		pluck="name", order_by="sequence_id asc, operation_row_id asc")
	start = _free_from(on)
	for name, (waste, reason, *note) in zip(cards, spoiled, strict=True):
		card = frappe.get_doc("Job Card", name)
		qty -= waste
		minutes = max(round(flt(card.time_required)), 10)
		end = start + timedelta(minutes=minutes)
		card.posting_date = on
		card.append("time_logs", {"from_time": start, "to_time": end, "time_in_mins": minutes, "completed_qty": qty,
			"employee": _employee(printer if card.operation == "Print" else CREW[card.operation])})
		card.fp_waste_reason = reason
		card.fp_waste_note = note[0] if note else None
		card.save(ignore_permissions=True)
		card.submit()
		start = end + timedelta(minutes=15)


def _free_from(on):
	"""When a run on `on` can start: 07:30, or after the last step this company logged that day.

	A run made again on a day that already has one (the pick order, after a demo has used it)
	must not overlap it, or ERPNext refuses the time logs: the same people, the same machines.
	"""
	first = datetime.combine(on, datetime.min.time()).replace(hour=7, minute=30)
	last = frappe.db.sql(
		"""select max(log.to_time) from `tabJob Card Time Log` log
		join `tabJob Card` card on card.name = log.parent
		where log.parenttype = 'Job Card' and card.company = %s and card.docstatus < 2
			and date(log.from_time) = %s""",
		(COMPANY, on),
	)[0][0]
	return max(first, get_datetime(last) + timedelta(minutes=15)) if last else first


def _finish(work_order, on):
	"""Finish the run as the Print Floor does after its last step: the materials backflushed for all
	of it, the good ones into finished goods."""
	return floor.finish_run(work_order, posting=(on, "16:30:00")).name


def _deliver(sales_order, on):
	"""Deliver what the run made, and close the order: overs and unders are normal in printing."""
	from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note

	work_order = frappe.db.get_value("Work Order", {"sales_order": sales_order, "docstatus": 1}, "name")
	made = flt(frappe.db.get_value("Work Order", work_order, "produced_qty"))
	note = make_delivery_note(sales_order)
	note.update({"posting_date": on, "posting_time": "14:00:00", "set_posting_time": 1})
	for row in note.items:
		row.qty = made
		row.warehouse = FG
	note.insert(ignore_permissions=True)
	note.submit()
	_backdate("Delivery Note", note.name, on, "14:00:00")
	frappe.get_doc("Sales Order", sales_order).update_status("Closed")
	return note.name


def _job(customer_key, code, qty, ordered, ran, printer, spoiled, number):
	"""One job: the customer's order, its works order, every step with its waste, and the finish."""
	order = _order(customer_key, code, qty, ordered, po_no=f"{customer_key.upper()}-{number:04d}")
	work_order = _work_order(code, qty, ran, sales_order=order)
	_steps(work_order, ran, printer, spoiled)
	_finish(work_order, ran)
	return order


# ──────────────────────────────────────────────────────────────────────────────
# Six weeks of history
# ──────────────────────────────────────────────────────────────────────────────


def _history():
	"""Deliveries in, jobs run and jobs delivered, in date order so stock is never back-filled."""
	made = {"receipts": [], "jobs": {}, "deliveries": []}
	# (working days ago, order within the day, what, which). Oldest first; within a day stock comes
	# in before a run uses it, and a run finishes before its delivery.
	events = [(supplier_lines[2], 0, "receive", supplier_lines) for supplier_lines in DELIVERIES]
	events += [(job[4], 1, "run", number) for number, job in enumerate(JOBS, start=1)]
	events += [(job[7], 2, "deliver", number) for number, job in enumerate(JOBS, start=1) if job[7]]
	for days_ago, _, kind, which in sorted(events, key=lambda event: (-event[0], event[1])):
		if kind == "receive":
			supplier, lines, _ = which
			order = _purchase_order(supplier, lines, _day(days_ago + 3))
			made["receipts"].append(_receive(order, _day(days_ago)))
		elif kind == "run":
			customer, code, qty, ordered, ran, printer, spoiled, _ = JOBS[which - 1]
			made["jobs"][which] = _job(customer, code, qty, _day(ordered), _day(ran), printer, spoiled, which)
		else:
			made["deliveries"].append(_deliver(made["jobs"][which], _day(days_ago)))
	return made


# ──────────────────────────────────────────────────────────────────────────────
# The live steps
# ──────────────────────────────────────────────────────────────────────────────


def _live():
	"""What the presenter uses, made again whenever a demo has used it up."""
	today = getdate(nowdate())
	live = {}

	run = frappe.db.get_value("Work Order", {"company": COMPANY, "docstatus": 1, "status": "Not Started"}, "name")
	if not run:
		customer, code, qty = LIVE
		order = _order(customer, code, qty, _day(1), po_no=f"EVT-{today:%m%d}")
		run = _work_order(code, qty, today, sales_order=order)
	live["run"] = run

	live["receive"] = {}
	for supplier, lines in RECEIVE.items():
		party = _party("Supplier", SUPPLIERS[supplier])
		waiting = frappe.db.get_value("Purchase Order", {"company": COMPANY, "supplier": party, "docstatus": 1,
			"per_received": ("<", 100), "status": ("not in", ("Closed", "Completed"))}, "name")
		live["receive"][supplier] = waiting or _purchase_order(supplier, lines, today)

	pick = frappe.db.get_value("Sales Order", {"company": COMPANY, "docstatus": 1, "per_delivered": ("<", 100),
		"status": ("not in", ("Closed", "Completed")), "name": ("in", _finished_orders())}, "name")
	if not pick:
		customer, code, qty, _, _, printer, spoiled, _ = PICK
		pick = _job(customer, code, qty, _day(2), _day(1), printer, spoiled, 99)
	live["pick"] = pick
	return live


def _finished_orders():
	"""Sales orders whose works order has finished, so there is stock to pick for them."""
	return frappe.get_all("Work Order", filters={"company": COMPANY, "status": "Completed",
		"sales_order": ("is", "set")}, pluck="sales_order") or [""]


# ──────────────────────────────────────────────────────────────────────────────
# The presenter
# ──────────────────────────────────────────────────────────────────────────────


def _hidden_keys():
	"""Every Fuse Home key on this site that this profile does not show."""
	keys = set()
	try:
		from fuse_core import modules

		keys.update(module["key"] for module in modules.all_modules())
	except Exception:
		pass
	try:
		from fuse_theme import api

		keys.update(tile.get("module", tile["key"]) for tile in api._all_tiles())
	except Exception:
		pass
	return sorted(keys - KEEP)


def _write_profile(doc):
	"""Write the Module Profile straight to the database, then clear any lock on it.

	A normal save queues a job and locks the profile, and a load that fails afterwards leaves that
	lock behind: every retry stops at "Document Queued". The presenter login is set up directly in
	_presenter, so the queued job is not needed.
	"""
	if doc.is_new():
		doc.name = doc.get("module_profile_name")
		doc.db_insert()
	else:
		doc.db_update()
	for table in doc.meta.get_table_fields():
		frappe.db.delete(table.options, {"parent": doc.name, "parenttype": doc.doctype, "parentfield": table.fieldname})
		for row in doc.get(table.fieldname):
			row.parent = doc.name
			row.db_insert()
	frappe.get_doc(doc.doctype, doc.name).unlock()


def _presenter_profiles():
	"""The Module Profile that keeps the presenter's Fuse Home to this industry's tiles.

	A launcher preference, not a permission: it blocks no module and grants or removes no role. On
	the demo site nothing the presenter tries may stop on a permission.
	"""
	hidden_field = frappe.get_meta("Module Profile").has_field("fuse_hidden_modules")
	module_profile = frappe.get_doc("Module Profile", PROFILE) if frappe.db.exists("Module Profile", PROFILE) else \
		frappe.get_doc({"doctype": "Module Profile", "module_profile_name": PROFILE})
	module_profile.set("block_modules", [])
	if hidden_field:
		module_profile.fuse_hidden_modules = "\n".join(_hidden_keys())
	_write_profile(module_profile)

	# The waste tile leaves every other presenter's Fuse Home, so each industry sees only its own.
	others = []
	if hidden_field:
		for name, text in frappe.get_all("Module Profile", filters={"name": ["!=", PROFILE]},
				fields=["name", "fuse_hidden_modules"], as_list=True):
			lines = [line.strip() for line in (text or "").replace(",", "\n").splitlines() if line.strip()]
			if lines and registry.MODULE_KEY not in lines:
				frappe.db.set_value("Module Profile", name, "fuse_hidden_modules", "\n".join(lines + [registry.MODULE_KEY]))
				others.append(name)
	return f"{PROFILE} (module profile)" + (f"; waste tile hidden from {', '.join(others)}" if others else "")


def _presenter(email):
	"""Put an existing login on the presenter's Fuse Home and default it to the company.

	Leaves the login's roles and permissions alone: who may do what on the demo site is set on the
	login by a person, and the loader never narrows it. Never creates a login either.
	"""
	email = (email or "").strip()
	# The Module Profile hides other industries' tiles. Not on the account running the loader or on
	# Administrator, whose Fuse Home has to show everything.
	if email in ("Administrator", frappe.session.user):
		frappe.throw(f"{email} is the account running the load. Use the presenter login.", title="Not a presenter login")
	if not frappe.db.exists("User", email):
		frappe.throw(f"There is no user {email}. Create the login first, then load again.", title="No such user")
	user = frappe.get_doc("User", email)
	user.module_profile = PROFILE
	user.save(ignore_permissions=True)
	# A default, not a User Permission: new documents open on the company, and nothing the presenter
	# opens is refused.
	frappe.defaults.set_user_default("Company", COMPANY, email)
	return email


def _summary(history, live, profiles, who):
	lines = []
	if history:
		lines.append(f"History loaded: {len(history['receipts'])} deliveries in, {len(history['jobs'])} jobs run "
			f"with their waste, {len(history['deliveries'])} delivered.")
	else:
		lines.append("History was already loaded and was left as it was.")
	lines.append(f"<b>Run it live</b>: works order <b>{live['run']}</b>, 2,000 round stickers for Eventide Events, "
		"five steps open. Print its <b>Job Ticket</b> (Print, Job Ticket) and scan it on the <b>Print Floor</b>.")
	lines.append(f"<b>Receive</b>: media order <b>{live['receive']['media']}</b> into Media Store, ink order "
		f"<b>{live['receive']['ink']}</b> into Ink and Consumables.")
	lines.append(f"<b>Pick</b>: sales order <b>{live['pick']}</b> from Finished Goods.")
	lines.append("<b>Report</b>: Print Waste, on Fuse Home.")
	lines.append(f"Presenter profiles: {profiles}." + (f"<br>Presenter login: {who}." if who else
		"<br>No presenter login given: create one, then load again with it to put it on the profile."))
	return "<br>".join(lines)
