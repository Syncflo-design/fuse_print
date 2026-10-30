"""The Print Floor — each step of a run, recorded at its workstation.

For a station PC with a scanner, a tablet or a phone. The operator scans the job ticket that
travels with the run (its barcode is the works order number) or taps the workstation, taps Start,
and at the end says how many good ones went on to the next step and why any were spoiled.

Everything lands on ERPNext's own Job Card: a time log with who and for how long, what the step
passed on, and this app's waste reason and note. ERPNext still decides whether a step may start
(the one before it must be done) and works out the run's process loss. When the last step is done
the run is finished with an ordinary Manufacture entry, which backflushes the materials from the
recipe and puts the good ones into finished goods — the same entry the works order's own Finish
button makes, so fuse_manufacturing posts it where posting is on.
"""

import frappe
from frappe.utils import cint, flt, now_datetime, strip_html
from fuse_manufacturing.floor import added_items, job_card_add_item, mark_added_consumed, run_added_items

from fuse_print.waste import REASONS, received_at, step_waste

# Job cards that are work still to do: not submitted, not a rework card.
OPEN = {"docstatus": 0, "is_corrective_job_card": 0}


def _guard():
	"""Refuse anyone who could not record the step from the desk either."""
	if not frappe.has_permission("Job Card", "write"):
		frappe.throw("You do not have permission to record work on job cards.")


def _company():
	"""The floor shows one company's work: the user's default, as the desk does."""
	return frappe.defaults.get_user_default("Company")


def _open_cards(**filters):
	"""Open job cards the user may see: one works order's, or all of the user's company's."""
	conditions = dict(OPEN, **filters)
	company = _company()
	if company and "work_order" not in filters:
		conditions["company"] = company
	return frappe.get_list(
		"Job Card",
		filters=conditions,
		fields=["name", "work_order", "operation", "workstation", "sequence_id", "operation_row_id", "status",
			"for_quantity", "production_item", "item_name"],
		order_by="expected_start_date asc, work_order asc, sequence_id asc, operation_row_id asc",
	)


def _rank(card):
	"""A step's place in its run: its Sequence ID, or where it is listed when the recipe has none."""
	return cint(card.sequence_id) or cint(card.operation_row_id)


def _next_steps(cards):
	"""The cards whose turn it is: the lowest open step of each works order."""
	first = {}
	for card in cards:
		lowest = first.get(card.work_order)
		if lowest is None or _rank(card) < lowest:
			first[card.work_order] = _rank(card)
	return [card for card in cards if _rank(card) == first.get(card.work_order)]


def _waiting_for(doc):
	"""The step this one is waiting for, or None when it is this step's turn.

	ERPNext checks the order itself only where the recipe gives Sequence IDs; this covers a recipe
	without them as well.
	"""
	if doc.docstatus != 0 or not doc.work_order:
		return None
	ahead = _next_steps(_open_cards(work_order=doc.work_order))
	if not ahead or doc.name in {card.name for card in ahead}:
		return None
	return ahead[0].operation


def _open_log(card):
	"""The time log of a step under way: started, not yet finished."""
	return next((log for log in card.time_logs if log.from_time and not log.to_time), None)


# ──────────────────────────────────────────────────────────────────────────────
# Reading
# ──────────────────────────────────────────────────────────────────────────────


@frappe.whitelist()
def bootstrap():
	"""The floor's home: each workstation with work waiting, the operators and the reasons."""
	_guard()
	stations = {}
	for card in _next_steps(_open_cards()):
		station = stations.setdefault(card.workstation, {"workstation": card.workstation, "operations": [],
			"ready": 0, "running": 0, "sequence": _rank(card)})
		if card.operation not in station["operations"]:
			station["operations"].append(card.operation)
		station["ready"] += 1
		station["running"] += card.status == "Work In Progress"
		station["sequence"] = min(station["sequence"], _rank(card))

	company = _company()
	operators = frappe.get_all(
		"Employee",
		filters={"status": "Active", **({"company": company} if company else {})},
		fields=["name", "employee_name"],
		order_by="employee_name asc",
		limit=200,
	)
	return {
		"company": company,
		"workstations": sorted(stations.values(), key=lambda s: (s["sequence"], s["workstation"])),
		"operators": operators,
		"reasons": REASONS,
	}


@frappe.whitelist()
def queue(workstation):
	"""The steps whose turn it is at one workstation."""
	_guard()
	cards = [card for card in _next_steps(_open_cards()) if card.workstation == workstation]
	if not cards:
		return []
	customers = _customers({card.work_order for card in cards})
	return [{
		"name": card.name,
		"operation": card.operation,
		"work_order": card.work_order,
		"item_code": card.production_item,
		"item_name": card.item_name,
		"customer": customers.get(card.work_order),
		"run": flt(card.for_quantity),
		"running": card.status == "Work In Progress",
	} for card in cards]


@frappe.whitelist()
def find(term):
	"""What a scan or a typed number names: a job card, or a works order's step whose turn it is.

	The ticket's barcode is the works order number. Typed, the last digits are enough when only
	one open works order ends with them.
	"""
	_guard()
	term = (term or "").strip().upper()
	if not term:
		frappe.throw("Scan the job ticket, or type the end of the works order number.")
	if frappe.db.exists("Job Card", term):
		return term

	work_order = term if frappe.db.exists("Work Order", term) else None
	if not work_order:
		filters = {"docstatus": 1, "status": ("in", ("Not Started", "In Process")), "name": ("like", f"%{term}")}
		if _company():
			filters["company"] = _company()
		matches = frappe.get_list("Work Order", filters=filters, pluck="name", limit=5)
		if not matches:
			frappe.throw(f"No open works order ends with {term}.", title="Not found")
		if len(matches) > 1:
			frappe.throw(f"{len(matches)} works orders end with {term}. Type more of the number.", title="Which one?")
		work_order = matches[0]

	steps = _next_steps(_open_cards(work_order=work_order))
	if not steps:
		frappe.throw(f"Every step of {work_order} is done.", title="Nothing to do")
	return steps[0].name


@frappe.whitelist()
def step(name):
	"""One step, as the step screen shows it."""
	_guard()
	doc = frappe.get_doc("Job Card", name)
	doc.check_permission("read")
	log = _open_log(doc) if doc.docstatus == 0 else None
	return {
		"name": doc.name,
		"docstatus": doc.docstatus,
		"operation": doc.operation,
		"workstation": doc.workstation,
		"work_order": doc.work_order,
		"item_code": doc.production_item,
		"item_name": doc.item_name,
		"customer": _customers({doc.work_order}).get(doc.work_order),
		"run": flt(doc.for_quantity),
		"received": flt(received_at(doc)),
		"waiting_for": _waiting_for(doc),
		"started": str(log.from_time) if log else None,
		"started_by": frappe.db.get_value("Employee", log.employee, "employee_name") if log and log.employee else None,
		"added": added_items(doc),
	}


def _customers(work_orders):
	"""Each works order's customer, through the sales order it was raised for."""
	orders = frappe.get_all("Work Order", filters={"name": ("in", list(work_orders))},
		fields=["name", "sales_order"])
	names = dict(frappe.get_all("Sales Order",
		filters={"name": ("in", [order.sales_order for order in orders if order.sales_order] or [""])},
		fields=["name", "customer_name"], as_list=True))
	return {order.name: names.get(order.sales_order) for order in orders}


# ──────────────────────────────────────────────────────────────────────────────
# Recording
# ──────────────────────────────────────────────────────────────────────────────


@frappe.whitelist(methods=["POST"])
def start(job_card, employee):
	"""Start a step: who is running it, from now."""
	_guard()
	if not employee or not frappe.db.exists("Employee", employee):
		frappe.throw("Say who is working first.")
	doc = frappe.get_doc("Job Card", job_card)
	if doc.docstatus != 0:
		frappe.throw(f"{doc.operation} on {doc.work_order} is already done.")
	if _open_log(doc):
		frappe.throw(f"{doc.operation} on {doc.work_order} is already under way.")
	waiting_for = _waiting_for(doc)
	if waiting_for:
		frappe.throw(f"Finish {waiting_for} on {doc.work_order} before starting {doc.operation}.")
	doc.append("time_logs", {"from_time": now_datetime(), "employee": employee})
	doc.save()
	return step(doc.name)


@frappe.whitelist(methods=["POST"])
def add_item(job_card, item_code, qty, employee=None):
	"""Something used at this step that the recipe does not list. Finishing the run consumes it."""
	_guard()
	job_card_add_item(job_card, item_code, qty, employee)
	return step(job_card)


@frappe.whitelist(methods=["POST"])
def finish(job_card, good, reason=None, note=None):
	"""Finish a step: what it passed on, why it spoiled any, and the operator's note.

	The last step of a run also finishes the run. If that cannot be done — usually not enough of a
	material in its store — the step stays recorded and the floor says why; the office finishes the
	run from the works order once the stock is there.
	"""
	_guard()
	doc = frappe.get_doc("Job Card", job_card)
	log = _open_log(doc) if doc.docstatus == 0 else None
	if not log:
		frappe.throw(f"Start {doc.operation} on {doc.work_order} before finishing it.")

	good, received = flt(good), flt(received_at(doc))
	if good <= 0 or good > received:
		frappe.throw(f"Good ones passed on must be more than 0 and no more than the {received:g} that reached "
			f"{doc.operation}.")
	unit = frappe.db.get_value("Work Order", doc.work_order, "stock_uom")
	if good != int(good) and unit and frappe.db.get_value("UOM", unit, "must_be_whole_number"):
		frappe.throw(f"{unit} are counted whole: {good:g} is not a whole number.")
	spoiled = step_waste(received, good)
	if spoiled and reason not in REASONS:
		frappe.throw(f"{doc.operation} spoiled {spoiled:g}. Tap why.", title="Waste reason needed")

	log.to_time = now_datetime()
	log.completed_qty = good
	doc.fp_waste_reason = reason if spoiled else None
	doc.fp_waste_note = (note or "").strip() or None
	doc.save()
	doc.submit()

	result = {"operation": doc.operation, "work_order": doc.work_order, "good": good, "spoiled": spoiled,
		"reason": doc.fp_waste_reason, "next": None, "finished": None, "finish_error": None}
	following = _next_steps(_open_cards(work_order=doc.work_order))
	if following:
		result["next"] = {"operation": following[0].operation, "workstation": following[0].workstation}
	elif _all_steps_done(doc.work_order):
		result.update(_finish_run_safely(doc.work_order))
	return result


def _all_steps_done(work_order):
	"""Every operation of the run has passed something on, and the run is not finished yet."""
	if flt(frappe.db.get_value("Work Order", work_order, "produced_qty")):
		return False
	return not frappe.db.exists("Work Order Operation", {"parent": work_order, "parenttype": "Work Order",
		"completed_qty": 0})


def _finish_run_safely(work_order):
	frappe.db.savepoint("fp_finish_run")
	try:
		entry = finish_run(work_order)
	except Exception as error:
		frappe.db.rollback(save_point="fp_finish_run")
		frappe.clear_messages()
		frappe.log_error(title=f"Print Floor: could not finish {work_order}", message=frappe.get_traceback())
		return {"finish_error": strip_html(str(error)) or error.__class__.__name__}
	finished = [row for row in entry.items if row.is_finished_item]
	return {"finished": {"entry": entry.name, "made": sum(flt(row.qty) for row in finished),
		"warehouse": finished[0].t_warehouse if finished else None}}


def finish_run(work_order, posting=None):
	"""Finish a run: the Manufacture entry for all of it, as the works order's Finish button makes it.

	The entry is for the whole run, so the materials are backflushed for everything that went
	through the line. ERPNext books the job cards' process loss on it, so what reaches finished
	goods is the run less the waste. Anything added at the steps on the floor is consumed with
	it, from the store the run draws from. `posting` is (date, time), for a back-dated finish.
	"""
	from erpnext.manufacturing.doctype.work_order.work_order import make_stock_entry

	qty = frappe.db.get_value("Work Order", work_order, "qty")
	entry = frappe.get_doc(make_stock_entry(work_order, "Manufacture", qty))
	added = run_added_items(work_order)
	if added:
		store = next((row.s_warehouse for row in entry.items if row.s_warehouse), None)
		if not store:
			frappe.throw(f"{work_order} has no store to take the added items from.")
		for line in added:
			entry.append("items", {"item_code": line["item_code"], "qty": line["qty"], "s_warehouse": store})
	if posting:
		entry.update({"posting_date": posting[0], "posting_time": posting[1], "set_posting_time": 1})
	entry.insert()
	entry.submit()
	mark_added_consumed([line["row"] for line in added], entry.name)
	return entry
