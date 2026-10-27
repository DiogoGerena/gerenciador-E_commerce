import unittest
from decimal import Decimal

from app.financial_metrics import (
    calcular_cmv,
    calcular_indicadores_financeiros,
)


class FinancialMetricsTestCase(unittest.TestCase):
    def test_cmv_uses_historical_unit_cost_per_sold_quantity(self):
        cmv = calcular_cmv(
            quantidades_vendidas=[2, 3],
            custos_unitarios_historicos=["5.10", "2.50"],
        )

        self.assertEqual(cmv, Decimal("17.70"))

    def test_calculates_revenue_costs_result_and_margin(self):
        indicadores = calcular_indicadores_financeiros(
            receita_vendas="40.00",
            quantidades_vendidas=[2, 3],
            custos_unitarios_historicos=["5.10", "2.50"],
            custos_venda="4.30",
        )

        self.assertEqual(indicadores["receita_vendas"], Decimal("40.00"))
        self.assertEqual(indicadores["cmv"], Decimal("17.70"))
        self.assertEqual(indicadores["custos_venda"], Decimal("4.30"))
        self.assertEqual(
            indicadores["resultado_apos_custos"],
            Decimal("18.00"),
        )
        self.assertEqual(indicadores["margem_percentual"], Decimal("45.00"))

    def test_empty_period_returns_zero_totals_and_not_applicable_margin(self):
        indicadores = calcular_indicadores_financeiros(
            receita_vendas=0,
            quantidades_vendidas=[],
            custos_unitarios_historicos=[],
            custos_venda=0,
        )

        self.assertEqual(indicadores["cmv"], Decimal("0.00"))
        self.assertEqual(
            indicadores["resultado_apos_custos"],
            Decimal("0.00"),
        )
        self.assertIsNone(indicadores["margem_percentual"])

    def test_rejects_mismatched_quantity_and_historical_cost_counts(self):
        with self.assertRaisesRegex(ValueError, "correspondente"):
            calcular_cmv([1, 2], [3.5])

    def test_rejects_negative_quantity_or_cost(self):
        with self.assertRaisesRegex(ValueError, "quantidade"):
            calcular_cmv([-1], [2])

        with self.assertRaisesRegex(ValueError, "custo unitário"):
            calcular_cmv([1], [-2])


if __name__ == "__main__":
    unittest.main()