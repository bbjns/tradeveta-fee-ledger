"""Reconcile TradeVeta forex and gold deal fees with posted rebates from local CSVs."""

import argparse
import csv
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_EVEN, localcontext
from pathlib import Path
import re


DEAL_COLUMNS = ("deal_id", "period_id", "symbol", "currency", "lots", "commission", "fee")
REBATE_COLUMNS = ("rebate_id", "period_id", "currency", "amount", "status")
DECIMAL = re.compile(r"[0-9]{1,18}(?:\.[0-9]{1,18})?")
CURRENCY = re.compile(r"[A-Z]{3}")
ZERO = Decimal(0)


@dataclass
class Totals:
    lots: Decimal = ZERO
    commission: Decimal = ZERO
    fees: Decimal = ZERO
    posted: Decimal = ZERO
    pending: Decimal = ZERO


def rows(path, columns):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream, strict=True)
        header = reader.fieldnames or []
        if len(header) != len(columns) or set(header) != set(columns):
            raise ValueError(f"{path}: expected CSV columns {', '.join(columns)}")
        identifiers = set()
        for row in reader:
            where = f"{path}:{reader.line_num}"
            if None in row or any(value is None or not value.strip() for value in row.values()):
                raise ValueError(f"{where}: expected a value for every CSV column")
            row = {key: value.strip() for key, value in row.items()}
            identifier = row[columns[0]]
            if identifier in identifiers:
                raise ValueError(f"{where}: duplicate {columns[0]} {identifier!r}")
            identifiers.add(identifier)
            yield where, row


def amount(row, key, where):
    value = row[key]
    if not DECIMAL.fullmatch(value):
        raise ValueError(f"{where}: {key} must be a non-negative decimal")
    return Decimal(value)


def reconcile(deals, rebates):
    periods = {}
    statement = None
    for where, row in rows(deals, DEAL_COLUMNS):
        key = (row["symbol"], row["currency"])
        if statement is None:
            statement = key
        if key != statement:
            raise ValueError(f"{where}: all deals must use one symbol and one currency per run")
        if not CURRENCY.fullmatch(row["currency"]):
            raise ValueError(f"{where}: currency must be a three-letter uppercase code")
        lots = amount(row, "lots", where)
        if lots == ZERO:
            raise ValueError(f"{where}: lots must be greater than zero")
        total = periods.setdefault(row["period_id"], Totals())
        total.lots += lots
        total.commission += amount(row, "commission", where)
        total.fees += amount(row, "fee", where)

    if statement is None:
        raise ValueError(f"{deals}: no deals to reconcile")

    symbol, currency = statement
    for where, row in rows(rebates, REBATE_COLUMNS):
        if row["currency"] != currency:
            raise ValueError(f"{where}: rebate currency must be {currency}")
        if row["period_id"] not in periods:
            raise ValueError(f"{where}: settlement period {row['period_id']!r} has no matching deals")
        rebate = amount(row, "amount", where)
        total = periods[row["period_id"]]
        if row["status"] == "posted":
            total.posted += rebate
        elif row["status"] == "pending":
            total.pending += rebate
        else:
            raise ValueError(f"{where}: status must be posted or pending")

    return symbol, currency, periods


def print_report(symbol, currency, periods):
    print(f"Symbol: {symbol!r}")
    for period_id, total in periods.items():
        gross = total.commission + total.fees
        net = gross - total.posted
        per_lot = (net / total.lots).quantize(Decimal("0.00000001"))
        rate = format(per_lot, "f").rstrip("0").rstrip(".") if per_lot else "0"
        print(f"Period: {period_id!r}")
        print(f"  Executed lots:       {total.lots:f}")
        print(f"  Commission:          {total.commission:f} {currency}")
        print(f"  Other deal fees:     {total.fees:f} {currency}")
        print(f"  Gross deal charges:  {gross:f} {currency}")
        print(f"  Posted rebates:      {total.posted:f} {currency}")
        print(f"  Pending rebates:     {total.pending:f} {currency}")
        print(f"  Net deal charges:    {net:f} {currency}")
        print(f"  Net per executed lot: {rate} {currency}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--deals", type=Path, required=True, help="deal CSV in TradeVeta format")
    parser.add_argument("--rebates", type=Path, required=True, help="rebate CSV in TradeVeta format")
    args = parser.parse_args()
    try:
        with localcontext() as context:
            context.prec = 60
            context.rounding = ROUND_HALF_EVEN
            print_report(*reconcile(args.deals, args.rebates))
    except (OSError, csv.Error, ValueError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
