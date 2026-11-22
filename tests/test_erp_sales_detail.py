import unittest
from unittest.mock import patch

import requests
from streamlit.testing.v1 import AppTest

import app.erp_modules as erp_modules


class SalesDetailScreenTests(unittest.TestCase):
    def _page(self, items, *, page=1, next_page=None, previous_page=None):
        return {
            "itemsReceived": len(items),
            "curPage": page,
            "nextPage": next_page,
            "prevPage": previous_page,
            "offset": (page - 1) * 20,
            "itemsTotal": len(items),
            "pageTotal": page,
            "items": items,
        }

    def _detail(self, sale_id=41):
        return {
            "sale": {
                "id": sale_id,
                "sales_channel": "Shopee",
                "order_number": "PED-41",
                "sale_date": 1773577800000,
                "status": "registrada",
            },
            "items": [
                {
                    "product_id": 8,
                    "quantity": 2,
                    "unit_sale_price": 17.5,
                    "historical_unit_cost": 9.25,
                }
            ],
            "costs": [
                {
                    "cost_type": "embalagem",
                    "description": "Caixa",
                    "amount": 2.5,
                }
            ],
            "financial_summary": {
                "gross_amount": 35.0,
                "discount_amount": 1.0,
                "net_revenue": 34.0,
                "total_cmv": 18.5,
                "total_costs": 2.5,
                "result": 13.0,
                "profit_margin_percent": 38.24,
            },
        }

    def _render(self, *, token="mock-session-token", response=None):
        app = AppTest.from_string(
            "import app.erp_modules as erp_modules\n"
            "erp_modules.render_vendas()"
        )
        if token:
            app.session_state["auth_token"] = token
            app.session_state["vendas_list_filter_channel"] = "Shopee"
        if response is not None:
            app.session_state["vendas_list_result"] = {
                "state": "success",
                "response": response,
            }
        return app

    def test_selected_sale_loads_and_displays_backend_detail(self):
        page = self._page([{"id": 41, "sales_channel": "Shopee"}])
        with (
            patch.object(erp_modules, "listar_vendas", return_value=page) as list_sales,
            patch.object(
                erp_modules,
                "consultar_venda",
                return_value=self._detail(),
            ) as get_sale,
        ):
            app = self._render().run()
            app.button(key="vendas_detail_submit").click().run()

        self.assertEqual(app.exception, [])
        list_sales.assert_called_once_with(
            "mock-session-token",
            sales_channel="Shopee",
            page=1,
            per_page=20,
        )
        get_sale.assert_called_once_with("mock-session-token", 41)
        self.assertFalse(app.json)
        sale_metrics = {metric.label: metric.value for metric in app.metric}
        self.assertEqual(sale_metrics["Pedido"], "PED-41")
        self.assertEqual(sale_metrics["Canal de venda"], "Shopee")
        self.assertEqual(sale_metrics["Data da venda"], "2026-03-15T12:30:00.000Z")
        self.assertEqual(sale_metrics["Receita bruta"], "R$ 35,00")
        self.assertEqual(sale_metrics["Margem de lucro"], "38,24%")
        self.assertEqual(
            list(app.dataframe[1].value.columns),
            [
                "Produto",
                "Quantidade",
                "Preço unitário",
                "Custo histórico unitário",
            ],
        )
        self.assertEqual(
            list(app.dataframe[2].value.columns),
            ["Tipo de custo", "Descrição", "Valor"],
        )

    def test_missing_optional_fields_are_not_filled_with_defaults(self):
        detail = {
            "sale": {"id": 41, "sales_channel": "Loja"},
            "items": [{"product_id": 8, "quantity": 1}],
            "costs": [],
            "financial_summary": {"gross_amount": 12.5},
        }
        page = self._page([{"id": 41}])
        with (
            patch.object(erp_modules, "listar_vendas", return_value=page),
            patch.object(
                erp_modules,
                "consultar_venda",
                return_value=detail,
            ),
        ):
            app = self._render().run()
            app.button(key="vendas_detail_submit").click().run()

        self.assertEqual(app.exception, [])
        self.assertEqual(
            list(app.dataframe[1].value.columns),
            [
                "Produto",
                "Quantidade",
                "Preço unitário",
                "Custo histórico unitário",
            ],
        )
        self.assertEqual(len(app.dataframe), 2)
        self.assertIn(
            ("Receita bruta", "R$ 12,50"),
            [(metric.label, metric.value) for metric in app.metric],
        )
        self.assertFalse(app.json)
        self.assertTrue(
            any("não contém custos" in item.value for item in app.info)
        )

    def test_missing_token_does_not_request_or_show_sale_detail(self):
        page = self._page([{"id": 41}])
        with patch.object(erp_modules, "consultar_venda") as get_sale:
            app = self._render(token=None, response=page).run()

        self.assertEqual(app.exception, [])
        get_sale.assert_not_called()
        self.assertFalse(
            any(button.key == "vendas_detail_submit" for button in app.button)
        )
        self.assertTrue(
            any("sessão expirou" in item.value for item in app.warning)
        )
        self.assertFalse(app.json)

    def test_http_errors_are_explained_without_showing_detail(self):
        for status_code, expected in (
            (401, "sessão expirou"),
            (403, "não tem permissão"),
            (404, "não foi encontrada"),
        ):
            with self.subTest(status_code=status_code):
                response = type(
                    "Response",
                    (),
                    {
                        "status_code": status_code,
                        "json": lambda self: {"message": "Access denied"},
                        "headers": {},
                        "text": "",
                    },
                )()
                error = requests.HTTPError(response=response)
                page = self._page([{"id": 41}])
                with (
                    patch.object(erp_modules, "listar_vendas", return_value=page),
                    patch.object(
                        erp_modules,
                        "consultar_venda",
                        side_effect=error,
                    ) as get_sale,
                ):
                    app = self._render().run()
                    app.button(key="vendas_detail_submit").click().run()

                self.assertEqual(app.exception, [])
                get_sale.assert_called_once_with("mock-session-token", 41)
                self.assertTrue(
                    any(expected in item.value for item in app.error)
                )
                self.assertFalse(app.json)

    def test_connection_error_does_not_render_details(self):
        page = self._page([{"id": 41}])
        with (
            patch.object(erp_modules, "listar_vendas", return_value=page),
            patch.object(
                erp_modules,
                "consultar_venda",
                side_effect=requests.ConnectionError("offline"),
            ),
        ):
            app = self._render().run()
            app.button(key="vendas_detail_submit").click().run()

        self.assertEqual(app.exception, [])
        self.assertFalse(app.json)
        self.assertTrue(
            any("ConnectionError" in item.value for item in app.error)
        )

    def test_invalid_or_mismatched_response_is_not_presented_as_success(self):
        invalid_responses = (
            {"sale": {"id": 41}, "items": [], "costs": []},
            self._detail(sale_id=42),
        )
        for response in invalid_responses:
            with self.subTest(response=response):
                page = self._page([{"id": 41}])
                with (
                    patch.object(erp_modules, "listar_vendas", return_value=page),
                    patch.object(
                        erp_modules,
                        "consultar_venda",
                        return_value=response,
                    ),
                ):
                    app = self._render().run()
                    app.button(key="vendas_detail_submit").click().run()

                self.assertEqual(app.exception, [])
                self.assertFalse(app.json)
                self.assertTrue(app.error)

    def test_closing_details_preserves_list_filters_and_page(self):
        page = self._page(
            [{"id": 41, "sales_channel": "Shopee"}],
            page=3,
            next_page=None,
            previous_page=2,
        )
        with (
            patch.object(erp_modules, "listar_vendas") as list_sales,
            patch.object(
                erp_modules,
                "consultar_venda",
                return_value=self._detail(),
            ) as get_sale,
        ):
            app = self._render(response=page)
            app.session_state["vendas_list_page"] = 3
            app.session_state["vendas_list_filter_channel"] = "Shopee"
            app.run()
            app.button(key="vendas_detail_submit").click().run()
            app.button(key="vendas_detail_close").click().run()

        list_sales.assert_not_called()
        get_sale.assert_called_once_with("mock-session-token", 41)
        self.assertEqual(app.exception, [])
        self.assertEqual(app.session_state["vendas_list_page"], 3)
        self.assertEqual(
            app.session_state["vendas_list_filter_channel"],
            "Shopee",
        )
        self.assertEqual(
            app.session_state["vendas_list_result"]["response"],
            page,
        )
        self.assertNotIn("vendas_detail_result", app.session_state)


if __name__ == "__main__":
    unittest.main()
