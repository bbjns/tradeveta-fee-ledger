import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest


ROOT = Path(__file__).resolve().parents[1]
DEALS = ROOT / "examples/deals.csv"
REBATES = ROOT / "examples/rebates.csv"
REBATE_HEADER = "rebate_id,period_id,currency,amount,status\n"


class FeeLedgerTest(unittest.TestCase):
    def run_ledger(self, deals=DEALS, rebates=REBATES):
        return subprocess.run(
            [sys.executable, ROOT / "fee_ledger.py", "--deals", deals, "--rebates", rebates],
            capture_output=True, text=True, check=False,
        )

    def test_documented_example_and_pending_rebate(self):
        result = self.run_ledger()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Executed lots:       1.00", result.stdout)
        self.assertIn("Gross deal charges:  7.00 USD", result.stdout)
        self.assertIn("Pending rebates:     0.50 USD", result.stdout)
        self.assertIn("Net deal charges:    5.00 USD", result.stdout)
        self.assertIn("Net per executed lot: 5 USD", result.stdout)
        self.assertIn(result.stdout.strip(), (ROOT / "README.md").read_text(encoding="utf-8"))

    def test_header_only_rebate_file(self):
        with TemporaryDirectory() as work:
            rebates = Path(work) / "rebates.csv"
            rebates.write_text(REBATE_HEADER)
            result = self.run_ledger(rebates=rebates)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Net deal charges:    7.00 USD", result.stdout)

    def test_duplicate_wrong_currency_and_unmatched_rebates(self):
        cases = [
            ("one,example-period,USD,1,posted\n" * 2, "duplicate rebate_id"),
            ("one,example-period,EUR,1,posted\n", "rebate currency must be USD"),
            ("one,unknown,USD,1,posted\n", "has no matching deals"),
        ]
        with TemporaryDirectory() as work:
            rebates = Path(work) / "rebates.csv"
            for rows, error in cases:
                with self.subTest(error=error):
                    rebates.write_text(REBATE_HEADER + rows)
                    result = self.run_ledger(rebates=rebates)
                    self.assertEqual(result.returncode, 2)
                    self.assertEqual(result.stdout, "")
                    self.assertIn(error, result.stderr)

    def test_mixed_symbols_cannot_share_a_lot_calculation(self):
        with TemporaryDirectory() as work:
            deals = Path(work) / "deals.csv"
            deals.write_text(DEALS.read_text().replace("exit,example-period,XAUUSD", "exit,example-period,EURUSD"))
            result = self.run_ledger(deals=deals)
            self.assertEqual(result.returncode, 2)
            self.assertIn("one symbol and one currency", result.stderr)

    def test_settlement_periods_are_kept_separate(self):
        with TemporaryDirectory() as work:
            deals = Path(work) / "deals.csv"
            deals.write_text(DEALS.read_text().replace("exit,example-period", "exit,next-period"))
            result = self.run_ledger(deals=deals)
            self.assertEqual(result.returncode, 0, result.stderr)
            first, second = result.stdout.split("Period: 'next-period'")
            self.assertIn("Net per executed lot: 3 USD", first)
            self.assertIn("Net per executed lot: 7 USD", second)


if __name__ == "__main__":
    unittest.main()
