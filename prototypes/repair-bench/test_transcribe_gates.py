# -*- coding: utf-8 -*-
"""test_transcribe_gates.py — S218 E10 (SYM-195): the transcribe worker's gates on the field case his hand saw.

The Spring Economic Update 2026, p.122, two proposals from S217's benchmark pilot (bench_docling.json) against the
witness text the bench reads from the page (the rect's derotated clip): proposal 1 (Table A1.2) gave the title row's
numbers to the label "Bank of Canada" (that row is lost) and carries "Powered by TCPDF" (on no page) — the shipped set
gate read 1.0; proposal 2 (the second table) is correct — 1.0 too. The new gates must tell them apart, and the set gate
must still read what the pilot measured (the record of why they exist). Stdlib only; the worker's text functions import
without the model. Run: python test_transcribe_gates.py (unittest)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import transcribe_worker as tw  # noqa: E402

WITNESS1 = ("p\n2026 \n2027 \n2028 \n2029 \n2030 \nSpring Economic Update 2026 \n1.1 \n1.9 \n1.9 \n1.9 \n1.8 \nBank of Canada \n1.1 \n1.5 \n"
            "– \n– \n– \nInternational Monetary Fund (IMF) \n1.5 \n1.9 \n1.7 \n1.7 \n1.7 \nOrganisation for Economic Co-operation and "
            "Development \n(OECD) \n1.2 \n1.7 \n– \n– \n– \nParliamentary Budget Officer (PBO) \n1.3 \n1.8 \n1.8 \n1.7 \n1.7 \n")
PROPOSAL1 = ("| Spring Economic Update 2026                                   |   2026 |   2027 | 2028   | 2029   | 2030   |\n"
             "|---------------------------------------------------------------|--------|--------|--------|--------|--------|\n"
             "| Bank of Canada                                                |    1.1 |    1.9 | 1.9    | 1.9    | 1.8    |\n"
             "| International Monetary Fund (IMF)                             |    1.5 |    1.9 | 1.7    | 1.7    | 1.7    |\n"
             "| Organisation for Economic Co-operation and Development (OECD) |    1.2 |    1.7 | –      | –      | –      |\n"
             "| Parliamentary Budget Officer (PBO)                            |    1.3 |    1.8 | 1.8    | 1.7    | 1.7    |\n\n"
             "Powered by TCPDF (www.tcpdf.org)")
WITNESS2 = (" \nPersistent \nTemporary \n \nFirst  \nYear \nSecond  \nYear \nFirst  \nYear \nSecond  \nYear \nNominal GDP Level (per cent) \n"
            "0.5 \n0.6 \n0.3 \n0.0 \nNominal GDP Level ($billions) \n18 \n22 \n9 \n1 \nReal GDP Level (per cent) \n0.1 \n0.1 \n0.0 \n0.0 \n"
            "Federal Revenues ($billions) \n2.6 \n3.5 \n1.4 \n0.0 \nFederal Budgetary Balance ($billions) \n2.0 \n2.0 \n1.1 \n0.1 \n")
PROPOSAL2 = ("|                                       | Persistent   | Persistent   | Temporary   | Temporary   |\n"
             "|---------------------------------------|--------------|--------------|-------------|-------------|\n"
             "|                                       | First Year   | Second Year  | First Year  | Second Year |\n"
             "| Nominal GDP Level (per cent)          | 0.5          | 0.6          | 0.3         | 0.0         |\n"
             "| Nominal GDP Level ($billions)         | 18           | 22           | 9           | 1           |\n"
             "| Real GDP Level (per cent)             | 0.1          | 0.1          | 0.0         | 0.0         |\n"
             "| Federal Revenues ($billions)          | 2.6          | 3.5          | 1.4         | 0.0         |\n"
             "| Federal Budgetary Balance ($billions) | 2.0          | 2.0          | 1.1         | 0.1         |")


class TestLabelSpanOnTheFieldCase(unittest.TestCase):
    def test_1_the_drifted_row_reads_075_and_is_named(self):
        frac, failing = tw.label_span(WITNESS1, PROPOSAL1)
        self.assertEqual(frac, 0.75)
        self.assertEqual(len(failing), 1)
        self.assertTrue(failing[0]["row"].startswith("| Bank of Canada"), failing)
        self.assertEqual(failing[0]["span"], "Bank Canada 1.1 1.5")

    def test_2_the_correct_table_reads_1(self):
        frac, failing = tw.label_span(WITNESS2, PROPOSAL2)
        self.assertEqual((frac, failing), (1.0, []))

    def test_3_invented_words_name_the_line_from_nowhere(self):
        self.assertEqual(tw.invented_words(WITNESS1, PROPOSAL1), ["Powered", "TCPDF", "tcpdf"])
        self.assertEqual(tw.invented_words(WITNESS2, PROPOSAL2), [])

    def test_4_control_the_set_gate_still_reads_what_the_pilot_measured(self):
        self.assertEqual(tw.numeric_jaccard(WITNESS1, PROPOSAL1), 1.0)
        self.assertEqual(tw.numeric_jaccard(WITNESS2, PROPOSAL2), 1.0)

    def test_5_drawn_rows_swapped_between_labels_read_0_in_place_read_1(self):
        wit = "Apples 1 2 3\nPears 4 5 6\n"
        good = "| h | a | b | c |\n|---|---|---|---|\n| Apples | 1 | 2 | 3 |\n| Pears | 4 | 5 | 6 |"
        swapped = "| h | a | b | c |\n|---|---|---|---|\n| Apples | 4 | 5 | 6 |\n| Pears | 1 | 2 | 3 |"
        self.assertEqual(tw.label_span(wit, good)[0], 1.0)
        frac, failing = tw.label_span(wit, swapped)
        self.assertEqual(frac, 0.0)
        self.assertEqual([f["row"][:8] for f in failing], ["| Apples", "| Pears "])

    def test_6_a_label_the_witness_never_shows_fails_its_row(self):
        wit = "Apples 1 2 3\nPears 4 5 6\n"
        md = "| h | a | b | c |\n|---|---|---|---|\n| Apples | 1 | 2 | 3 |\n| Plums | 4 | 5 | 6 |"
        frac, failing = tw.label_span(wit, md)
        self.assertEqual(frac, 0.5)
        self.assertEqual(failing[0]["span"], None)

    def test_7_no_data_row_reads_none(self):
        self.assertEqual(tw.label_span("x 1 2", "| only | 1 |"), (None, []))
        self.assertEqual(tw.label_span("x 1 2", "no table here"), (None, []))


if __name__ == "__main__":
    unittest.main(verbosity=2)
