# TradeVeta Fee Ledger

Reconcile the explicit commissions, other deal fees, and posted rebates for forex and gold trades from two local CSV files.

Maintained by TradeVeta. [Official TradeVeta website](https://tradeveta.com/) · [TradeVeta trading cost tools](https://tradeveta.com/tools)

## Run the example

Python 3.9 or later. The tool uses the standard library and reads your files locally. It requires no brokerage login, API key, or network access.

```sh
python3 fee_ledger.py --deals examples/deals.csv --rebates examples/rebates.csv
```

```text
Symbol: 'XAUUSD'
Period: 'example-period'
  Executed lots:       1.00
  Commission:          6.50 USD
  Other deal fees:     0.50 USD
  Gross deal charges:  7.00 USD
  Posted rebates:      2.00 USD
  Pending rebates:     0.50 USD
  Net deal charges:    5.00 USD
  Net per executed lot: 5 USD
```

These amounts are illustrative. The 0.50-lot entry and 0.50-lot exit total 1.00 executed lot across both sides. The per-executed-lot figure uses the sum of the individual deal sizes. For a fully matched 0.50-lot round trip in this example, the same 5.00 USD cost is 10.00 USD per round-trip lot.

## Prepare statement data

Process one account, symbol and account currency per run. Convert exports into the UTF-8 format in `examples/` and keep your original statements outside the repository.

| File | Required columns |
| --- | --- |
| Deals | `deal_id,period_id,symbol,currency,lots,commission,fee` |
| Rebates | `rebate_id,period_id,currency,amount,status` |

- Use one row per executed deal. Include entry and exit deals for the period you are checking. Each deal and each rebate credit needs a unique ID within its own file.
- Use non-negative values for charged fees and rebate credits. A broker may show a commission debit as `-3.25`; enter that debit as `3.25`. Enter zero for an absent deal fee. Preserve the source statement when separately classifying refunds or corrections.
- Use the same `period_id` for deals and their matched rebate. When a credit covers several trades, use the exact settlement period. If a credit covers multiple symbols, import only the amount the statement attributes to the symbol. Keep unallocated credits outside the run.
- Mark completed credits `posted` and expected credits `pending`. Use a header-only rebate file if there are no credits. Pending credits are shown separately.

MT5 documents `DEAL_TICKET`, `DEAL_SYMBOL`, `DEAL_VOLUME`, `DEAL_COMMISSION`, and `DEAL_FEE` in its [deal properties reference](https://www.mql5.com/en/docs/constants/tradingconstants/dealproperties). Map the trade records and rebate statement into the included CSV template before running the tool. If your broker charges a separate periodic commission outside the deals, reconcile it separately from this deal-level total.

Gross deal charges equal commission plus other deal fees. Net deal charges subtract only the rebate amounts already posted. The per-executed-lot figure is rounded to eight decimals. Spread, slippage, swap, financing, and trading P&L are outside this calculation.

## Run tests

```sh
python3 -m unittest discover -s tests
```

Released under the [MIT License](LICENSE) by TradeVeta.
