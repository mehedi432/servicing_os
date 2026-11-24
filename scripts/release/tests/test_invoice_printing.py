import importlib
import unittest
from decimal import Decimal, ROUND_HALF_UP
from types import ModuleType
from unittest.mock import patch


def flt(value, precision=None):
    number = Decimal(str(value or 0))
    if precision is not None:
        number = number.quantize(Decimal(10) ** -precision, rounding=ROUND_HALF_UP)
    return float(number)


class InvoicePrintingTests(unittest.TestCase):
    def test_displayed_total_and_words_share_the_recorded_rounding(self):
        frappe = ModuleType("frappe")
        utils = ModuleType("frappe.utils")
        utils.flt = flt
        with patch.dict("sys.modules", {"frappe": frappe, "frappe.utils": utils}):
            with patch.object(utils, "money_in_words", return_value="Words", create=True) as words:
                printing = importlib.import_module("servicing_os.invoice_printing")
                invoice = {"grand_total": 2765.50, "rounding_adjustment": 0.50, "rounded_total": 2766}
                self.assertEqual(printing.invoice_document_print_amounts(invoice, "BDT"), {
                    "print_total": 2766.0, "print_rounding_adjustment": 0.50, "amount_in_words": "Words",
                })
                words.assert_called_with(2766.0, "BDT", "Paisa")

                invoice["disable_rounded_total"] = 1
                self.assertEqual(printing.invoice_document_print_amounts(invoice, "BDT")["print_total"], 2765.50)
                words.assert_called_with(2765.50, "BDT", "Paisa")

                credit = printing.invoice_document_print_amounts({"grand_total": -19.25}, "USD")
                self.assertEqual(credit["amount_in_words"], "Minus Words")
                words.assert_called_with(19.25, "USD", None)
