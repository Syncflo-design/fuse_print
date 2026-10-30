"""The step arithmetic, without a site. Run: python -m unittest discover -s fuse_print/tests -t ."""

import sys
import types
import unittest

# waste.py imports frappe for its hooks; the arithmetic under test needs only flt.
if "frappe" not in sys.modules:
	frappe = types.ModuleType("frappe")
	utils = types.ModuleType("frappe.utils")
	utils.flt = lambda value, precision=None: float(value or 0)
	frappe.utils = utils
	sys.modules["frappe"] = frappe
	sys.modules["frappe.utils"] = utils

from fuse_print.waste import step_waste  # noqa: E402


class StepWaste(unittest.TestCase):
	def test_first_step_spoils_what_it_did_not_pass_on(self):
		self.assertEqual(step_waste(10000, 9800), 200)

	def test_a_later_step_counts_only_its_own(self):
		"""Laminate received 9,800 from Print and passed on 9,700: 100, not ERPNext's running 300."""
		self.assertEqual(step_waste(9800, 9700), 100)

	def test_a_clean_step_spoils_nothing(self):
		self.assertEqual(step_waste(9700, 9700), 0)

	def test_never_below_nothing(self):
		self.assertEqual(step_waste(9700, 9750), 0)

	def test_steps_add_up_to_erpnexts_run_loss(self):
		"""What each step spoiled adds up to the largest process loss, which ERPNext books on the run."""
		run, passed = 10000, [9800, 9700, 9660, 9570, 9570]
		received = [run] + passed[:-1]
		spoiled = [step_waste(r, p) for r, p in zip(received, passed, strict=True)]
		self.assertEqual(sum(spoiled), run - passed[-1])


if __name__ == "__main__":
	unittest.main()
