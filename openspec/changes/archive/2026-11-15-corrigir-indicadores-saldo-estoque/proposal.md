## Why

The stock page currently converts missing quantity and inventory value into zero in charts, and can classify a product as normal when its minimum stock is unknown. This makes incomplete Xano data look like confirmed inventory and can mislead operational decisions.

## What Changes

- Preserve the distinction between known zero, unavailable fields, and invalid numeric values when normalizing product stock data.
- Mark inventory totals and classifications as incomplete when required product data is unavailable, rather than presenting partial sums as complete.
- Keep stock charts based on Xano products while excluding unknown values from numeric plots and clearly indicating when chart data is incomplete or unavailable.
- Add mock-based tests for complete, missing, invalid, mixed, zero-valued, and empty product responses.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `dashboard-relatorios`: clarify how stock indicators and reports represent incomplete stock quantity, cost, or minimum-stock data.

The existing `dashboard-relatorios` capability is the correct home because its main specification already defines stock indicators and stock reports. The separate `entradas-estoque-custos` and `movimentacoes-cmv` capabilities cover stock transactions, cost calculations, and integrity rather than presenting stock indicators and reports.

## Impact

- Affects stock normalization, indicator calculation, and chart/table rendering in `app/erp_modules.py`, with focused tests in `tests/test_erp_stock_page.py`.
- Does not change Xano endpoints, payloads, schemas, authentication, or other application modules.
