"""The Code 128 table and encoding behind the job ticket.

    python -m unittest discover -s fuse_print/tests -t .
"""

import unittest

from fuse_print import barcode


class TestCode128(unittest.TestCase):
	def test_table_shape(self):
		# 107 symbols; each data symbol is 11 modules over 6 elements, the stop 13 over 7.
		self.assertEqual(len(barcode.PATTERNS), 107)
		for value, pattern in enumerate(barcode.PATTERNS[:106]):
			self.assertEqual((len(pattern), sum(map(int, pattern))), (6, 11), value)
		self.assertEqual(sum(map(int, barcode.PATTERNS[106])), 13)

	def test_table_parity_and_uniqueness(self):
		# In Code 128 the bars of every symbol add up to an even number of modules.
		for value, pattern in enumerate(barcode.PATTERNS):
			self.assertEqual(sum(int(w) for w in pattern[0::2]) % 2, 0, value)
		self.assertEqual(len(set(barcode.PATTERNS)), 107)

	def test_check_digit(self):
		# Start B 104; P=48 J=42 J=42 1=17 2=18 3=19 C=35, weighted by position: 879 mod 103 = 55.
		self.assertEqual(barcode.values("PJJ123C"), [104, 48, 42, 42, 17, 18, 19, 35, 55, 106])

	def test_works_order_number(self):
		modules = sum(barcode.widths("MFG-WO-2026-00012"))
		# Start, 17 characters, check and stop: 11 modules each, the stop 13.
		self.assertEqual(modules, 19 * 11 + 13)
		self.assertIn('aria-label="Barcode MFG-WO-2026-00012"', barcode.fp_barcode("MFG-WO-2026-00012"))

	def test_refuses_what_set_b_cannot_carry(self):
		with self.assertRaises(ValueError):
			barcode.values("")
		with self.assertRaises(ValueError):
			barcode.values("Tyre\n1")


if __name__ == "__main__":
	unittest.main()
