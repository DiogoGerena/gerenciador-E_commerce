import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

import app.erp_modules as erp_modules


class StockPageDataTruthTests(unittest.TestCase):
    def _render_stock_page(self, payload):
        products = erp_modules._normalizar_produtos_para_saldo(payload)
        with patch.object(
            erp_modules,
            "_render_formulario_entrada_estoque",
        ), patch.object(
            erp_modules,
            "_render_historico_movimentacoes",
        ), patch.object(
            erp_modules,
            "_consultar_saldo_estoque",
            return_value=("success", products, None),
        ), patch.object(
            erp_modules.st,
            "altair_chart",
        ) as chart:
            app = AppTest.from_string(
                "import app.erp_modules as erp_modules\n"
                "erp_modules.render_estoque()"
            )
            app.session_state["auth_token"] = "mock-session-token"
            app.run()
            app.button(key="consulta_saldo_estoque").click().run()

        return app, chart

    def _product(self, product_id=1, **fields):
        return {
            "id": product_id,
            "name": f"Produto {product_id}",
            **fields,
        }

    def test_unconfirmed_balance_api_is_not_replaced_with_demo_data(self):
        with patch.object(
            erp_modules,
            "_render_formulario_entrada_estoque",
        ), patch.object(
            erp_modules,
            "_render_historico_movimentacoes",
        ):
            app = AppTest.from_string(
                "import app.erp_modules as erp_modules\n"
                "erp_modules.render_estoque()"
            ).run()

        self.assertEqual(app.exception, [])
        self.assertEqual(len(app.button), 1)
        self.assertEqual(app.button[0].key, "consulta_saldo_estoque")
        self.assertTrue(app.button[0].disabled)
        self.assertTrue(
            any(
                "A consulta de saldo será executada" in item.value
                for item in app.caption
            )
        )
        self.assertEqual(len(app.dataframe), 0)
        rendered = str(app)
        for demo_product in (
            "Notebook Pro",
            "Camiseta Premium",
            "Batedeira Deluxe",
            "Smartwatch X",
            "Garrafa Térmica",
        ):
            self.assertNotIn(demo_product, rendered)
        self.assertNotIn("Salvar movimentação", rendered)
        self.assertNotIn("Consulta pendente", rendered)

    def test_complete_product_data_calculates_indicators(self):
        products = erp_modules._normalizar_produtos_para_saldo(
            [
                self._product(
                    stock_quantity=20,
                    average_cost=10,
                    min_stock=5,
                )
            ]
        )
        metrics = erp_modules._calcular_indicadores_estoque(products)

        self.assertEqual(metrics["total_produtos"], 1)
        self.assertEqual(metrics["total_unidades"], 20)
        self.assertEqual(metrics["produtos_baixos"], 0)
        self.assertEqual(metrics["produtos_sem_estoque"], 0)
        self.assertEqual(metrics["valor_estoque"], 200)
        self.assertEqual(products[0]["situacao"], "Normal")

    def test_missing_quantity_is_unavailable_not_zero(self):
        products = erp_modules._normalizar_produtos_para_saldo(
            [
                self._product(
                    average_cost=10,
                    min_stock=5,
                )
            ]
        )
        metrics = erp_modules._calcular_indicadores_estoque(products)

        self.assertIsNone(products[0]["stock_quantity"])
        self.assertEqual(products[0]["stock_quantity_status"], "unavailable")
        self.assertEqual(products[0]["situacao"], "Indeterminado")
        self.assertIsNone(metrics["total_unidades"])
        self.assertEqual(metrics["produtos_quantidade_incompleta"], 1)

    def test_missing_average_cost_does_not_make_inventory_value_zero(self):
        products = erp_modules._normalizar_produtos_para_saldo(
            [
                self._product(
                    stock_quantity=4,
                    min_stock=2,
                )
            ]
        )
        metrics = erp_modules._calcular_indicadores_estoque(products)

        self.assertEqual(products[0]["stock_quantity"], 4)
        self.assertIsNone(products[0]["valor_estimado"])
        self.assertEqual(products[0]["average_cost_status"], "unavailable")
        self.assertIsNone(metrics["valor_estoque"])
        self.assertEqual(metrics["produtos_valor_incompleto"], 1)

    def test_missing_minimum_makes_positive_quantity_indeterminate(self):
        products = erp_modules._normalizar_produtos_para_saldo(
            [
                self._product(
                    stock_quantity=4,
                    average_cost=10,
                )
            ]
        )
        metrics = erp_modules._calcular_indicadores_estoque(products)

        self.assertEqual(products[0]["situacao"], "Indeterminado")
        self.assertEqual(
            metrics["produtos_classificacao_indeterminada"],
            1,
        )

    def test_invalid_cost_in_mixed_data_makes_inventory_total_unavailable(self):
        products = erp_modules._normalizar_produtos_para_saldo(
            [
                self._product(
                    product_id=1,
                    stock_quantity=2,
                    average_cost=3,
                    min_stock=1,
                ),
                self._product(
                    product_id=2,
                    stock_quantity=4,
                    average_cost="invalid",
                    min_stock=1,
                ),
            ]
        )
        metrics = erp_modules._calcular_indicadores_estoque(products)

        self.assertEqual(products[0]["valor_estimado"], 6)
        self.assertEqual(products[1]["average_cost_status"], "invalid")
        self.assertIsNone(products[1]["valor_estimado"])
        self.assertEqual(products[1]["valor_estimado_status"], "invalid")
        self.assertIsNone(metrics["valor_estoque"])
        self.assertEqual(metrics["produtos_valor_incompleto"], 1)

    def test_invalid_minimum_with_positive_quantity_is_indeterminate(self):
        products = erp_modules._normalizar_produtos_para_saldo(
            [
                self._product(
                    stock_quantity=4,
                    average_cost=10,
                    min_stock="invalid",
                )
            ]
        )
        metrics = erp_modules._calcular_indicadores_estoque(products)

        self.assertEqual(products[0]["min_stock_status"], "invalid")
        self.assertEqual(products[0]["situacao"], "Indeterminado")
        self.assertEqual(metrics["produtos_classificacao_indeterminada"], 1)
        self.assertEqual(metrics["produtos_baixos"], 0)

    def test_quantity_equal_to_minimum_is_low_stock(self):
        products = erp_modules._normalizar_produtos_para_saldo(
            [
                self._product(
                    stock_quantity=5,
                    average_cost=10,
                    min_stock=5,
                )
            ]
        )
        metrics = erp_modules._calcular_indicadores_estoque(products)

        self.assertEqual(products[0]["situacao"], "Estoque baixo")
        self.assertEqual(metrics["produtos_baixos"], 1)

    def test_negative_quantity_preserves_current_no_stock_classification(self):
        products = erp_modules._normalizar_produtos_para_saldo(
            [
                self._product(
                    stock_quantity=-2,
                    average_cost=3,
                    min_stock=0,
                )
            ]
        )
        metrics = erp_modules._calcular_indicadores_estoque(products)

        self.assertEqual(products[0]["stock_quantity"], -2)
        self.assertEqual(products[0]["stock_quantity_status"], "valid")
        self.assertEqual(products[0]["situacao"], "Sem estoque")
        self.assertEqual(metrics["total_unidades"], -2)
        self.assertEqual(metrics["produtos_sem_estoque"], 1)

    def test_invalid_numeric_values_are_identified_not_coerced(self):
        products = erp_modules._normalizar_produtos_para_saldo(
            [
                self._product(
                    stock_quantity="not-a-number",
                    average_cost=float("inf"),
                    min_stock=True,
                )
            ]
        )

        self.assertIsNone(products[0]["stock_quantity"])
        self.assertEqual(products[0]["stock_quantity_status"], "invalid")
        self.assertEqual(products[0]["average_cost_status"], "invalid")
        self.assertEqual(products[0]["min_stock_status"], "invalid")
        self.assertEqual(products[0]["valor_estimado_status"], "invalid")
        self.assertEqual(products[0]["situacao"], "Indeterminado")

    def test_zero_quantity_and_cost_are_preserved_as_valid(self):
        products = erp_modules._normalizar_produtos_para_saldo(
            [
                self._product(
                    stock_quantity=0,
                    average_cost=0,
                )
            ]
        )
        metrics = erp_modules._calcular_indicadores_estoque(products)

        self.assertEqual(products[0]["stock_quantity"], 0)
        self.assertEqual(products[0]["average_cost"], 0)
        self.assertEqual(products[0]["valor_estimado"], 0)
        self.assertEqual(products[0]["situacao"], "Sem estoque")
        self.assertEqual(metrics["total_unidades"], 0)
        self.assertEqual(metrics["valor_estoque"], 0)

    def test_empty_product_list_shows_empty_state_without_demo_data(self):
        app, chart = self._render_stock_page([])

        self.assertEqual(app.exception, [])
        self.assertTrue(
            any("Nenhum produto ativo" in item.value for item in app.info)
        )
        self.assertEqual(len(app.dataframe), 0)
        chart.assert_not_called()
        rendered = str(app)
        self.assertNotIn("Notebook Pro", rendered)
        self.assertNotIn("R$ 482.450", rendered)

    def test_mixed_data_does_not_present_partial_totals_or_zero_bars(self):
        app, chart = self._render_stock_page(
            [
                self._product(
                    product_id=1,
                    stock_quantity=20,
                    average_cost=10,
                    min_stock=5,
                ),
                self._product(
                    product_id=2,
                    average_cost=4,
                    min_stock=2,
                ),
                self._product(
                    product_id=3,
                    stock_quantity=4,
                    min_stock=1,
                ),
                self._product(
                    product_id=4,
                    stock_quantity=3,
                    average_cost=2,
                ),
            ]
        )

        self.assertEqual(app.exception, [])
        output = " ".join(
            str(item.value)
            for item in (*app.metric, *app.warning, *app.caption, *app.info)
        )
        self.assertIn("Indisponível", output)
        self.assertIn("2 produto(s)", output)
        self.assertIn("classificação indeterminada", output)
        self.assertEqual(len(app.dataframe), 1)
        self.assertIn("Indisponível", str(app.dataframe[0].value))

        charts = [call.args[0] for call in chart.call_args_list]
        self.assertEqual(len(charts), 3)
        quantity_chart = charts[0].data
        self.assertEqual(quantity_chart["Produto"].tolist(), ["Produto 1", "Produto 3", "Produto 4"])
        value_chart = charts[2].data
        self.assertEqual(value_chart["Produto"].tolist(), ["Produto 1", "Produto 4"])
        self.assertEqual(value_chart["Valor estimado"].tolist(), [200, 6])

    def test_zero_values_remain_visible_in_inventory_charts(self):
        app, chart = self._render_stock_page(
            [
                self._product(
                    stock_quantity=0,
                    average_cost=0,
                )
            ]
        )

        self.assertEqual(app.exception, [])
        charts = [call.args[0] for call in chart.call_args_list]
        self.assertEqual(charts[0].data["Quantidade"].tolist(), [0])
        self.assertEqual(charts[2].data["Valor estimado"].tolist(), [0])

    def test_situation_chart_counts_indeterminate_products(self):
        app, chart = self._render_stock_page(
            [
                self._product(
                    product_id=1,
                    stock_quantity=0,
                ),
                self._product(
                    product_id=2,
                    stock_quantity=3,
                    min_stock=3,
                ),
                self._product(
                    product_id=3,
                    stock_quantity=5,
                    min_stock=2,
                ),
                self._product(
                    product_id=4,
                    stock_quantity=4,
                    min_stock="invalid",
                ),
                self._product(
                    product_id=5,
                    min_stock=1,
                ),
            ]
        )

        self.assertEqual(app.exception, [])
        charts = [call.args[0] for call in chart.call_args_list]
        situation_chart = charts[1].data
        self.assertEqual(
            situation_chart["Situação"].tolist(),
            ["Sem estoque", "Estoque baixo", "Normal", "Indeterminado"],
        )
        self.assertEqual(situation_chart["Quantidade"].tolist(), [1, 1, 1, 2])

    def test_overflow_numeric_value_is_invalid_without_breaking_stock_page(self):
        app, chart = self._render_stock_page(
            [
                self._product(
                    stock_quantity=10**10000,
                    average_cost=2,
                    min_stock=1,
                )
            ]
        )

        self.assertEqual(app.exception, [])
        self.assertTrue(
            any("Indisponível" == metric.value for metric in app.metric)
        )
        self.assertTrue(
            any(
                "quantidade indisponível ou inválida para 1 produto(s)"
                in warning.value
                for warning in app.warning
            )
        )
        self.assertIn("Inválido", str(app.dataframe[0].value))
        charts = [call.args[0] for call in chart.call_args_list]
        self.assertEqual(len(charts), 1)
        self.assertEqual(
            charts[0].data["Situação"].tolist(),
            ["Sem estoque", "Estoque baixo", "Normal", "Indeterminado"],
        )
        self.assertEqual(charts[0].data["Quantidade"].tolist(), [0, 0, 0, 1])

    def test_all_unknown_numeric_values_render_empty_charts(self):
        app, chart = self._render_stock_page(
            [
                self._product(),
                self._product(
                    product_id=2,
                    stock_quantity=None,
                    average_cost=None,
                    min_stock=None,
                ),
            ]
        )
        self.assertEqual(app.exception, [])
        self.assertTrue(
            any("Não há quantidades conhecidas" in item.value for item in app.info)
        )
        self.assertTrue(
            any("Não há valores conhecidos" in item.value for item in app.info)
        )
        self.assertEqual(chart.call_count, 1)

    def test_historico_movimentacoes_uses_friendly_labels(self):
        movements = [
            {
                "created_at": "2024-01-05T08:30:00Z",
                "movement_type": "inbound",
                "quantity": 7,
                "quantity_before": 3,
                "quantity_after": 10,
                "unit_cost": 12.5,
                "reference_type": "supplier",
                "reference_id": "FOR-77",
                "product_name": "Produto X",
            }
        ]

        dataframe = erp_modules._normalizar_movimentacoes_para_tabela(movements)

        self.assertIn("Tipo de movimentação", dataframe.columns)
        self.assertEqual(dataframe.iloc[0]["Tipo de movimentação"], "Entrada")
        self.assertEqual(dataframe.iloc[0]["Quantidade"], 7.0)
        self.assertTrue(str(dataframe.iloc[0]["Data da movimentação"]).startswith("05/01/2024"))


if __name__ == "__main__":
    unittest.main()
