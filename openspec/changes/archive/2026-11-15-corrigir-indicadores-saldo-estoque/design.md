## Context

See proposal.md - Why. The stock page in `app/erp_modules.py` normalizes numeric product fields, calculates five indicators, and builds three charts from the normalized product list. The Xano product contract is unchanged; the client may return `None` for absent, null, or non-numeric fields, and the page must not imply that these values are zero.

## Goals / Non-Goals

**Goals:**
- Keep known numeric zero distinct from unavailable and invalid field values.
- Make total quantity and inventory value unavailable rather than showing partial sums when any required product value is unknown.
- Report the number of affected products and avoid assigning an unjustified stock classification.
- Keep plots driven by the current Xano response and visually indicate omitted or insufficient data.

**Non-Goals:**
- Change the Xano contract, client endpoints, stock business thresholds, or other application modules.
- Add a new stock state or redefine the existing zero-stock and low-stock rules.
- Change the visual design beyond the existing table, metrics, and chart presentation.

## Decisions

- Preserve the existing normalized product structure and add explicit field-validity/completeness information needed by the page. A numeric zero remains a valid numeric value; absent/null fields remain unavailable; malformed or non-finite values are marked invalid rather than coerced to zero.
- Calculate quantity and value totals only when every product in the active-product response has the fields required for that total. Keep the product count as the count of returned products, and expose separate incompleteness counts for quantity, value, and classification so a partial sum is never labeled as a complete total.
- Classify a known zero quantity as “Sem estoque” even when minimum stock is unavailable. For positive quantities, require a known valid minimum to distinguish low stock from normal; unknown or invalid quantity, or an unknown/invalid minimum for positive quantity, produces an indeterminate classification.
- Build the quantity chart only from products with known valid quantities, the inventory-value chart only from products with a known valid calculated value, and the situation chart from determinate classifications while explicitly counting indeterminate products. If a chart has no usable values, render an explanatory empty state instead of bars with invented zeros.
- Keep the product table as the per-product source of detail, distinguishing unavailable fields from invalid values and preserving valid zeros.
- Add focused unit and Streamlit AppTest coverage using mocked Xano responses; no test in this change calls the live API.

## Risks / Trade-offs

- [Totals become unavailable when one product is incomplete] -> This is intentionally conservative; show the number of affected products and retain per-product values in the table rather than presenting a misleading partial total.
- [Invalid numeric values and absent values have different causes] -> Preserve separate validity states for display and tests, without attempting to repair or infer values.
- [Products can be counted as indeterminate in more than one metric] -> Report incompleteness per affected measure so users can understand why a particular total or classification is unavailable.
- [Existing consumers may rely on numeric totals] -> Keep complete-data calculations unchanged and scope the new unavailable state to incomplete responses.
