import unittest
from datetime import date
from decimal import Decimal
from unittest.mock import Mock, patch

import requests
from streamlit.testing.v1 import AppTest

import app.erp_modules as erp_modules


def sale_page(items, *, page=1, page_total=1, items_total=None):
    if items_total is None:
        items_total = len(items)
    return {
        "itemsReceived": len(items),
        "curPage": page,
        "nextPage": page + 1 if page < page_total else None,
        "prevPage": page - 1 if page > 1 else None,
        "offset": (page - 1) * 100,
        "itemsTotal": items_total,
        "pageTotal": page_total,
        "items": items,
    }


def sale_detail(
    sale_id,
    *,
    sales_channel="Shopee",
    sale_date="2026-11-16T12:00:00Z",
    gross_amount=40.0,
    net_revenue=38.0,
    total_cmv=20.0,
    total_costs=1.25,
    result=16.75,
    margin=44.08,
):
    return {
        "sale": {
            "id": sale_id,
            "sales_channel": sales_channel,
            "order_number": f"ORDER-{sale_id}",
            "sale_date": sale_date,
            "status": "registrada",
        },
        "items": [{"product_id": 7, "quantity": 2}],
        "costs": [{"cost_type": "embalagem", "amount": total_costs}],
        "financial_summary": {
            "gross_amount": gross_amount,
            "discount_amount": gross_amount - net_revenue,
            "net_revenue": net_revenue,
            "total_cmv": total_cmv,
            "total_costs": total_costs,
            "result": result,
            "profit_margin_percent": margin,
        },
    }


def product_record(product_id=1, **overrides):
    product = {
        "id": product_id,
        "name": f"Produto real {product_id}",
        "sku": f"SKU-{product_id}",
        "stock_quantity": 8,
        "min_stock": 10,
        "average_cost": 5.5,
    }
    product.update(overrides)
    return product


class SalesAnalyticsTests(unittest.TestCase):
    def test_xano_millisecond_date_is_parsed_for_financial_analytics(self):
        listed_sale = {
            "id": 41,
            "sales_channel": "Shopee",
            "status": "registrada",
            "sale_date": 1773577800000,
        }
        with (
            patch.object(
                erp_modules,
                "listar_vendas",
                return_value=sale_page([listed_sale]),
            ),
            patch.object(
                erp_modules,
                "consultar_venda",
                return_value=sale_detail(41, sale_date=1773577800000),
            ),
        ):
            result = erp_modules._vendas_com_detalhes_financeiros(
                "admin-session",
                "Shopee",
                date(2026, 3, 1),
                date(2026, 3, 31),
            )

        self.assertEqual(result["state"], "success")
        self.assertTrue(result["has_complete_dates"])
        self.assertEqual(result["sales"][0]["sale_date"], "2026-03-15")

    def test_paginates_registered_sales_and_aggregates_confirmed_details(self):
        first = sale_page(
            [
                {
                    "id": 41,
                    "sales_channel": "Shopee",
                    "status": "registrada",
                    "sale_date": "2026-11-16T12:00:00Z",
                }
            ],
            page=1,
            page_total=2,
            items_total=2,
        )
        second = sale_page(
            [
                {
                    "id": 42,
                    "sales_channel": "Shopee",
                    "status": "registrada",
                    "sale_date": "2026-11-17T14:00:00Z",
                }
            ],
            page=2,
            page_total=2,
            items_total=2,
        )
        second_detail = sale_detail(
            42,
            sale_date="2026-11-17T14:00:00Z",
            gross_amount=20.0,
            net_revenue=18.0,
            total_cmv=8.0,
            total_costs=2.0,
            result=8.0,
            margin=44.44,
        )
        with patch.object(
            erp_modules,
            "listar_vendas",
            side_effect=[first, second],
        ) as list_sales:
            with patch.object(
                erp_modules,
                "consultar_venda",
                side_effect=[sale_detail(41), second_detail],
            ) as get_sale:
                result = erp_modules._vendas_com_detalhes_financeiros(
                    "admin-session",
                    " Shopee ",
                    date(2026, 11, 1),
                    date(2026, 11, 30),
                )

        self.assertEqual(result["state"], "success")
        self.assertEqual(len(result["sales"]), 2)
        self.assertTrue(result["has_complete_dates"])
        self.assertEqual(result["summary"]["gross_amount"], Decimal("60.00"))
        self.assertEqual(result["summary"]["net_revenue"], Decimal("56.00"))
        self.assertEqual(result["summary"]["total_cmv"], Decimal("28.00"))
        self.assertEqual(result["summary"]["total_costs"], Decimal("3.25"))
        self.assertEqual(result["summary"]["gross_profit"], Decimal("28.00"))
        self.assertEqual(result["summary"]["result"], Decimal("24.75"))
        self.assertEqual(result["summary"]["margin_percent"], Decimal("44.20"))
        self.assertEqual(list_sales.call_count, 2)
        for page_number, call in enumerate(list_sales.call_args_list, start=1):
            self.assertEqual(
                call.args,
                ("admin-session",),
            )
            self.assertEqual(
                call.kwargs,
                {
                    "sales_channel": "Shopee",
                    "status": "registrada",
                    "start_date": "2026-11-01T00:00:00Z",
                    "end_date": "2026-11-30T23:59:59Z",
                    "page": page_number,
                    "per_page": 100,
                },
            )
        self.assertEqual(
            [call.args for call in get_sale.call_args_list],
            [("admin-session", 41), ("admin-session", 42)],
        )

    def test_empty_sales_are_real_zero_totals_and_an_empty_result(self):
        with patch.object(
            erp_modules,
            "listar_vendas",
            return_value=sale_page([], items_total=0),
        ) as list_sales, patch.object(erp_modules, "consultar_venda") as get_sale:
            result = erp_modules._vendas_com_detalhes_financeiros(
                "admin-session",
                "Shopee",
                date(2026, 11, 1),
                date(2026, 11, 30),
            )

        self.assertEqual(result["state"], "success")
        self.assertEqual(result["sales"], [])
        self.assertEqual(result["summary"]["net_revenue"], Decimal("0.00"))
        self.assertEqual(result["summary"]["total_cmv"], Decimal("0.00"))
        self.assertIsNone(result["summary"]["margin_percent"])
        list_sales.assert_called_once()
        get_sale.assert_not_called()

    def test_missing_channel_and_reversed_period_do_not_call_xano(self):
        with patch.object(erp_modules, "listar_vendas") as list_sales:
            missing_channel = erp_modules._vendas_com_detalhes_financeiros(
                "admin-session",
                "",
                date(2026, 11, 1),
                date(2026, 11, 30),
            )
            reversed_period = erp_modules._vendas_com_detalhes_financeiros(
                "admin-session",
                "Shopee",
                date(2026, 11, 30),
                date(2026, 11, 1),
            )

        self.assertEqual(missing_channel["state"], "validation")
        self.assertIn("sales_channel", missing_channel["message"])
        self.assertEqual(reversed_period["state"], "validation")
        list_sales.assert_not_called()

    def test_incomplete_pagination_or_details_never_produce_partial_metrics(self):
        incomplete_page = {"itemsReceived": 1, "itemsTotal": 1, "items": [{"id": 41}]}
        with patch.object(
            erp_modules,
            "listar_vendas",
            return_value=incomplete_page,
        ):
            result = erp_modules._vendas_com_detalhes_financeiros(
                "admin-session",
                "Shopee",
                date(2026, 11, 1),
                date(2026, 11, 30),
            )

        self.assertEqual(result["state"], "error")
        self.assertIsNone(result["summary"])
        self.assertEqual(result["sales"], [])

        with patch.object(
            erp_modules,
            "listar_vendas",
            return_value=sale_page([{"id": 41}]),
        ):
            with patch.object(
                erp_modules,
                "consultar_venda",
                side_effect=erp_modules.RespostaVendaInconclusivaError(
                    "financial summary incomplete"
                ),
            ):
                result = erp_modules._vendas_com_detalhes_financeiros(
                    "admin-session",
                    "Shopee",
                    date(2026, 11, 1),
                    date(2026, 11, 30),
                )

        self.assertEqual(result["state"], "error")
        self.assertIsNone(result["summary"])
        self.assertEqual(result["sales"], [])

    def test_http_errors_are_clear_and_do_not_expose_token(self):
        response = Mock()
        response.status_code = 401
        error = requests.HTTPError(response=response)
        with patch.object(erp_modules, "listar_vendas", side_effect=error):
            result = erp_modules._vendas_com_detalhes_financeiros(
                "private-session-token",
                "Shopee",
                date(2026, 11, 1),
                date(2026, 11, 30),
            )

        self.assertEqual(result["state"], "error")
        self.assertIn("sessão foi recusada", result["message"])
        self.assertNotIn("private-session-token", result["message"])


class DashboardAndReportScreenTests(unittest.TestCase):
    @staticmethod
    def _render(function_name, *, token="mock-session-token"):
        app = AppTest.from_string(
            "import app.erp_modules as erp_modules\n"
            f"erp_modules.{function_name}()"
        )
        if token is not None:
            app.session_state["auth_token"] = token
        return app.run()

    def test_dashboard_uses_live_stock_and_does_not_query_sales_without_channel(self):
        normalized_products = erp_modules._normalizar_produtos_para_saldo(
            [product_record()]
        )
        with patch.object(
            erp_modules,
            "_consultar_saldo_estoque",
            return_value=("success", normalized_products, None),
        ) as stock_query:
            with patch.object(erp_modules, "listar_vendas") as list_sales:
                app = self._render("render_vision_geral")

        self.assertEqual(app.exception, [])
        stock_query.assert_called_once_with("mock-session-token")
        list_sales.assert_not_called()
        self.assertTrue(
            any("GET /sale exige sales_channel" in item.value for item in app.info)
        )
        self.assertTrue(
            any(
                item.label == "Produtos ativos" and item.value == "1"
                for item in app.metric
            )
        )
        rendered = str(app)
        self.assertNotIn("Dados de demonstração", rendered)
        self.assertNotIn("Camiseta Premium", rendered)
        self.assertNotIn("251,300", rendered)

    def test_dashboard_displays_financials_from_xano_sale_details(self):
        products = erp_modules._normalizar_produtos_para_saldo(
            [product_record(stock_quantity=0, min_stock=0)]
        )
        with patch.object(
            erp_modules,
            "_consultar_saldo_estoque",
            return_value=("success", products, None),
        ):
            with patch.object(
                erp_modules,
                "listar_vendas",
                return_value=sale_page(
                    [
                        {
                            "id": 41,
                            "sales_channel": "Shopee",
                            "status": "registrada",
                            "sale_date": "2026-11-16T12:00:00Z",
                        }
                    ]
                ),
            ) as list_sales:
                with patch.object(
                    erp_modules,
                    "consultar_venda",
                    return_value=sale_detail(41),
                ):
                    with patch.object(erp_modules.st, "line_chart") as line_chart:
                        app = self._render("render_vision_geral")
                        app.text_input(key="dashboard_sales_channel").set_value(
                            "Shopee"
                        )
                        app.form_submit_button(
                            key="dashboard_refresh"
                        ).click().run()

        self.assertEqual(app.exception, [])
        list_sales.assert_called_once()
        self.assertEqual(list_sales.call_args.kwargs["sales_channel"], "Shopee")
        self.assertEqual(list_sales.call_args.kwargs["status"], "registrada")
        self.assertTrue(
            any(
                item.label == "Receita líquida" and item.value == "R$ 38,00"
                for item in app.metric
            )
        )
        self.assertTrue(
            any(
                item.label == "Resultado após custos" and item.value == "R$ 16,75"
                for item in app.metric
            )
        )
        chart_data = line_chart.call_args.args[0]
        self.assertEqual(chart_data.iloc[0]["Receita líquida"], 38.0)
        self.assertEqual(chart_data.iloc[0]["CMV"], 20.0)
        self.assertEqual(chart_data.iloc[0]["Resultado"], 16.75)
        self.assertNotIn("54.880", str(app))

    def test_report_stock_uses_live_products_and_describes_current_snapshot(self):
        products = erp_modules._normalizar_produtos_para_saldo(
            [product_record(product_id=8, stock_quantity=3)]
        )
        with patch.object(
            erp_modules,
            "_consultar_saldo_estoque",
            return_value=("success", products, None),
        ) as stock_query:
            with patch.object(erp_modules, "listar_vendas") as list_sales:
                app = self._render("render_relatorios")
                app.selectbox(key="reports_type").set_value("Estoque")
                app.form_submit_button(key="reports_generate").click().run()

        self.assertEqual(app.exception, [])
        stock_query.assert_called_once_with("mock-session-token")
        list_sales.assert_not_called()
        self.assertTrue(
            any("saldo atual" in item.value for item in app.caption)
        )
        self.assertIn(
            "Produto real 8",
            app.dataframe[0].value["Produto"].tolist(),
        )
        self.assertNotIn("Notebook Pro", str(app))
        self.assertTrue(app.download_button)

    def test_report_sales_uses_real_sales_and_shows_per_sale_rows(self):
        with patch.object(
            erp_modules,
            "listar_vendas",
            return_value=sale_page(
                [
                    {
                        "id": 41,
                        "sales_channel": "Shopee",
                        "status": "registrada",
                        "sale_date": "2026-11-16T12:00:00Z",
                    }
                ]
            ),
        ) as list_sales:
            with patch.object(
                erp_modules,
                "consultar_venda",
                return_value=sale_detail(41),
            ):
                app = self._render("render_relatorios")
                app.text_input(key="reports_sales_channel").set_value("Shopee")
                app.form_submit_button(key="reports_generate").click().run()

        self.assertEqual(app.exception, [])
        list_sales.assert_called_once()
        self.assertTrue(
            any(
                item.value.loc[0, "Venda"] == 41
                for item in app.dataframe
            )
        )
        self.assertTrue(
            any("ORDER-41" in str(item.value) for item in app.dataframe)
        )
        self.assertTrue(app.download_button)

    def test_missing_session_and_xano_failures_show_no_demo_values(self):
        with patch.object(erp_modules, "_consultar_saldo_estoque") as stock_query:
            with patch.object(erp_modules, "listar_vendas") as list_sales:
                app = self._render("render_vision_geral", token=None)
        stock_query.assert_not_called()
        list_sales.assert_not_called()
        self.assertTrue(any("sessão expirou" in item.value for item in app.warning))

        with patch.object(
            erp_modules,
            "_consultar_saldo_estoque",
            return_value=("error", [], "HTTP 401"),
        ):
            app = self._render("render_vision_geral")
        self.assertTrue(any("HTTP 401" in item.value for item in app.error))
        self.assertNotIn("Dados de demonstração", str(app))


if __name__ == "__main__":
    unittest.main()
