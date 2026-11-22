import unittest
from unittest.mock import patch

import requests
from streamlit.testing.v1 import AppTest

import app.erp_modules as erp_modules


class SalesListScreenTests(unittest.TestCase):
    def _page(self, items, *, page=1, next_page=2, previous_page=None):
        return {
            "itemsReceived": len(items),
            "curPage": page,
            "nextPage": next_page,
            "prevPage": previous_page,
            "offset": (page - 1) * 20,
            "itemsTotal": 21,
            "pageTotal": 2,
            "items": items,
        }

    def _render(self, *, sales_channel=None):
        app = AppTest.from_string(
            "import app.erp_modules as erp_modules\n"
            "erp_modules.render_vendas()"
        )
        app.session_state["auth_token"] = "mock-session-token"
        if sales_channel is not None:
            app.session_state["vendas_list_filter_channel"] = sales_channel
        return app

    def test_sales_screen_loads_real_headers_without_demo_data(self):
        items = [
            {
                "id": 41,
                "sales_channel": "Shopee",
                "order_number": "PED-41",
                "sale_date": 1773577800000,
                "status": "registrada",
            }
        ]
        with patch.object(
            erp_modules,
            "listar_vendas",
            return_value=self._page(items),
        ) as list_sales:
            app = self._render(sales_channel="Shopee").run()

        self.assertEqual(app.exception, [])
        list_sales.assert_called_once_with(
            "mock-session-token",
            sales_channel="Shopee",
            page=1,
            per_page=20,
        )
        self.assertEqual(len(app.dataframe), 1)
        displayed = app.dataframe[0].value.to_string(index=False)
        for value in ("41", "Shopee", "PED-41", "registrada"):
            self.assertIn(value, displayed)
        self.assertIn("2026-03-15T12:30:00.000Z", displayed)
        for demo_value in (
            "Maria Souza",
            "João Lima",
            "Ana Martins",
            "Pedro Rocha",
            "Laura Costa",
        ):
            self.assertNotIn(demo_value, displayed)
        self.assertNotIn("Cliente", app.dataframe[0].value.columns)
        self.assertTrue(
            any("Página 1 de 2" in caption.value for caption in app.caption)
        )

    def test_empty_sales_list_shows_empty_state(self):
        with patch.object(
            erp_modules,
            "listar_vendas",
            return_value=self._page([], next_page=None),
        ) as list_sales:
            app = self._render(sales_channel="Loja").run()

        self.assertEqual(app.exception, [])
        list_sales.assert_called_once()
        self.assertEqual(len(app.dataframe), 0)
        self.assertTrue(
            any(
                "Nenhuma venda encontrada" in message.value
                for message in app.info
            )
        )

    def test_missing_token_does_not_call_xano(self):
        with patch.object(erp_modules, "listar_vendas") as list_sales:
            app = AppTest.from_string(
                "import app.erp_modules as erp_modules\n"
                "erp_modules.render_vendas()"
            ).run()

        self.assertEqual(app.exception, [])
        list_sales.assert_not_called()
        self.assertTrue(
            any("sessão expirou" in message.value for message in app.warning)
        )
        self.assertTrue(app.form_submit_button(key="vendas_list_submit").disabled)

    def test_open_without_channel_waits_for_required_filter(self):
        with patch.object(erp_modules, "listar_vendas") as list_sales:
            app = self._render().run()
            app.form_submit_button(key="vendas_list_submit").click().run()

        self.assertEqual(app.exception, [])
        list_sales.assert_not_called()
        self.assertTrue(
            any("Informe o canal de venda" in item.value for item in app.info)
        )

    def test_filters_are_forwarded_without_date_conversion(self):
        response = self._page([{"id": 41, "sales_channel": "Shopee"}])
        with patch.object(
            erp_modules,
            "listar_vendas",
            side_effect=(response, response),
        ) as list_sales:
            app = self._render(sales_channel="Shopee").run()
            app.text_input(key="vendas_list_filter_channel").set_value(" Shopee ")
            app.text_input(
                key="vendas_list_filter_order_number"
            ).set_value(" PED-41 ")
            app.selectbox(key="vendas_list_filter_status").select(
                "registrada"
            )
            app.text_input(
                key="vendas_list_filter_start_date"
            ).set_value("2026-11-01T00:00:00Z")
            app.text_input(
                key="vendas_list_filter_end_date"
            ).set_value("2026-11-16T23:59:59Z")
            app.form_submit_button(key="vendas_list_submit").click().run()

        self.assertEqual(app.exception, [])
        self.assertEqual(list_sales.call_count, 2)
        self.assertEqual(
            list_sales.call_args.kwargs,
            {
                "page": 1,
                "per_page": 20,
                "sales_channel": "Shopee",
                "order_number": "PED-41",
                "start_date": "2026-11-01T00:00:00Z",
                "end_date": "2026-11-16T23:59:59Z",
                "status": "registrada",
            },
        )
        self.assertEqual(app.session_state["vendas_list_page"], 1)

    def test_new_filter_submission_resets_current_page(self):
        response = self._page([{"id": 41}], page=4, next_page=5, previous_page=3)
        with patch.object(
            erp_modules,
            "listar_vendas",
            side_effect=(response, response),
        ) as list_sales:
            app = self._render(sales_channel="Shopee").run()
            self.assertEqual(app.session_state["vendas_list_page"], 1)
            app.session_state["vendas_list_page"] = 4
            app.text_input(key="vendas_list_filter_channel").set_value("Loja")
            app.form_submit_button(key="vendas_list_submit").click().run()

        self.assertEqual(app.exception, [])
        self.assertEqual(list_sales.call_args.kwargs["page"], 1)

    def test_pagination_preserves_active_filters_and_uses_returned_page(self):
        first_page = self._page(
            [{"id": 41, "sales_channel": "WhatsApp"}],
            page=1,
            next_page=3,
        )
        next_page = self._page(
            [{"id": 63, "sales_channel": "WhatsApp"}],
            page=3,
            next_page=None,
            previous_page=1,
        )
        with patch.object(
            erp_modules,
            "listar_vendas",
            side_effect=(first_page, next_page),
        ) as list_sales:
            app = self._render()
            app.session_state["vendas_list_filter_channel"] = "WhatsApp"
            app.session_state["vendas_list_filter_order_number"] = "P-"
            app.session_state["vendas_list_filter_status"] = "cancelada"
            app.run()
            app.button(key="vendas_list_next").click().run()

        self.assertEqual(app.exception, [])
        self.assertEqual(list_sales.call_count, 2)
        self.assertEqual(
            list_sales.call_args.kwargs,
            {
                "page": 3,
                "per_page": 20,
                "sales_channel": "WhatsApp",
                "order_number": "P-",
                "status": "cancelada",
            },
        )
        self.assertEqual(app.session_state["vendas_list_page"], 3)
        self.assertIn("63", app.dataframe[0].value.to_string(index=False))

    def test_http_authentication_and_permission_errors_are_explained(self):
        for status_code, expected in (
            (401, "sessão expirou"),
            (403, "não tem permissão"),
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
                with patch.object(
                    erp_modules,
                    "listar_vendas",
                    side_effect=error,
                ):
                    app = self._render(sales_channel="Shopee").run()

                self.assertEqual(app.exception, [])
                self.assertTrue(
                    any(expected in message.value for message in app.error)
                )
                self.assertEqual(len(app.dataframe), 0)

    def test_connection_error_shows_failure_without_demo_list(self):
        with patch.object(
            erp_modules,
            "listar_vendas",
            side_effect=requests.ConnectionError("offline"),
        ) as list_sales:
            app = self._render(sales_channel="Shopee").run()

        self.assertEqual(app.exception, [])
        list_sales.assert_called_once()
        self.assertEqual(len(app.dataframe), 0)
        self.assertTrue(
            any(
                "ConnectionError" in message.value
                for message in app.error
            )
        )

    def test_invalid_response_is_not_rendered_as_success(self):
        with patch.object(
            erp_modules,
            "listar_vendas",
            return_value={"items": [], "curPage": 1},
        ):
            app = self._render(sales_channel="Shopee").run()

        self.assertEqual(app.exception, [])
        self.assertEqual(len(app.dataframe), 0)
        self.assertTrue(app.error)


if __name__ == "__main__":
    unittest.main()
