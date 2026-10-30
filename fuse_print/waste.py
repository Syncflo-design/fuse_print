"""Waste at each workstation: what a step spoiled, and why.

ERPNext records a job card's process loss as the run less what that card passed on, so every
step after the first also counts the steps before it. Print spoils 200 of 10,000 and passes on
9,800; Laminate passes on 9,700 and ERPNext gives its loss as 300. That running figure is what
ERPNext needs — the Manufacture entry books the largest one as the run's loss, so the materials
are backflushed for the whole run and the finished stock is the run less the waste.

A printer needs the other figure: what this step spoiled, 100 at Laminate. It is kept alongside
on the job card as `fp_waste_qty`, with the reason for it.
"""

import frappe
from frappe.utils import flt

# Why a step spoiled stock: the options of the job card's reason field and the report's filter.
REASONS = [
	"Setup and colour match",
	"Misprint",
	"Media fault",
	"Lamination fault",
	"Cut out of register",
	"Weeding damage",
	"End of roll",
	"Other",
]


def step_waste(received, passed_on):
	"""What a step spoiled: what reached it, less what it passed on. Never below nothing."""
	return max(flt(received) - flt(passed_on), 0.0)


def set_step_waste(doc, method=None):
	"""Job Card validate: what this step spoiled, once the operator has said what it passed on."""
	if not flt(doc.total_completed_qty):
		doc.fp_waste_qty = 0
		return
	doc.fp_waste_qty = step_waste(received_at(doc), doc.total_completed_qty)


def received_at(doc):
	"""What reached this step: the good output of the step before it, or the whole run for the first.

	Read off the works order's operations, which ERPNext keeps up to date from the submitted job
	cards. One job card per step, as the line runs; a step split over several cards would need
	them added up first. A recipe whose operations have no Sequence ID runs in the order they are
	listed, so the step before is the row above.
	"""
	if doc.work_order and doc.sequence_id:
		previous = frappe.get_all(
			"Work Order Operation",
			filters={"parent": doc.work_order, "sequence_id": ("<", doc.sequence_id)},
			fields=["completed_qty"],
			order_by="sequence_id desc, idx desc",
			limit=1,
		)
		if previous:
			return previous[0].completed_qty
	elif doc.work_order and doc.operation_id:
		rows = frappe.get_all("Work Order Operation", filters={"parent": doc.work_order},
			fields=["name", "completed_qty"], order_by="idx asc")
		names = [row.name for row in rows]
		if doc.operation_id in names and names.index(doc.operation_id):
			return rows[names.index(doc.operation_id) - 1].completed_qty
	return doc.for_quantity


def require_reason(doc, method=None):
	"""Job Card before_submit: waste is not recorded without a reason."""
	if flt(doc.fp_waste_qty) > 0 and not doc.fp_waste_reason:
		frappe.throw(
			f"{doc.operation} spoiled {flt(doc.fp_waste_qty):g}. Choose a waste reason before submitting.",
			title="Waste reason needed",
		)
