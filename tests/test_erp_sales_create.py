import unittest
from datetime import date, datetime, timezone
from unittest.mock import patch
from uuid import UUID

import requests
from streamlit.testing.v1 import AppTest

import app.erp_modules as erp_modules
import app.xano_client as xano_client
from tests.ui_test_utils import auto_confirm_operations


class SalesCreateScreenTests(unittest.TestCase):
    def setUp(self):
        auto_confirm_operations(self, erp_modules)

    def _page(self, items=None):
        items = items or []
        return {
            "itemsReceived": len(items),
            "curPage": 1,
            "nextPage": None,
            "prevPage": None,
            "offset": 0,
            "itemsTotal": len(items),
            "pageTotal": 1,
            "items": items,
        }

    def _sale_response(self):
        return {
            "sale": {
                "id": 91,
                "sales_channel": "Canal livre",
                "order_number": "PED-91",
            },
            "items": [
                {
                    "product_id": 7,
                    "quantity": 2,
                    "unit_sale_price": 12.5,
                }
            ],
            "costs": [],
            "financial_summary": {
                "gross_amount": 25.0,
                "discount_amount": 0.0,
                "net_revenue": 25.0,
                "total_cmv": 11.0,
                "total_costs": 0.0,
                "result": 14.0,
                "profit_margin_percent": 56.0,
            },
        }

    @staticmethod
    def _http_error(status_code, message):
        response = type(
            "Response",
            (),
            {
                "status_code": status_code,
                "json": lambda self: {"message": message},
                "headers": {},
                "text": message,
            },
        )()
        return requests.HTTPError(response=response)

    def _render(self, *, token="mock-session-token", seed=None):
        app = AppTest.from_string(
            "import app.erp_modules as erp_modules\n"
            "erp_modules.render_vendas()"
        )
        if token:
            app.session_state["auth_token"] = token
        app.session_state["vendas_list_result"] = {
            "state": "success",
            "response": self._page(),
        }
        for key, value in (seed or {}).items():
            app.session_state[key] = value
        return app

    def _selected_product_seed(self, *, item_ids=(1,)):
        seed = {
            "vendas_create_sales_channel": "Canal livre",
            "vendas_create_items": [{"id": item_id} for item_id in item_ids],
            "vendas_create_next_item_id": max(item_ids, default=0) + 1,
            "vendas_create_costs": [],
            "vendas_create_next_cost_id": 1,
        }
        for item_id in item_ids:
            prefix = f"vendas_create_item_{item_id}_"
            seed.update(
                {
                    f"{prefix}products": [
                        {"id": 7, "name": "Produto real", "sku": "PR-7"},
                        {"id": 8, "name": "Outro produto", "sku": "PR-8"},
                    ],
                    f"{prefix}product_id": 7,
                    f"{prefix}quantity": "2",
                    f"{prefix}unit_sale_price": "12.5",
                    f"{prefix}discount_amount": "",
                }
            )
        return seed

    def test_missing_authentication_disables_create_and_product_search(self):
        with (
            patch.object(erp_modules, "criar_venda") as create_sale,
            patch.object(erp_modules, "listar_produtos") as list_products,
        ):
            app = self._render(token=None).run()

        self.assertEqual(app.exception, [])
        self.assertTrue(app.button(key="vendas_create_submit").disabled)
        self.assertTrue(
            app.button(key="vendas_create_item_1_search_submit").disabled
        )
        self.assertTrue(
            any("sessão expirou" in warning.value for warning in app.warning)
        )
        create_sale.assert_not_called()
        list_products.assert_not_called()

    def test_empty_catalog_does_not_allow_selecting_a_fake_product(self):
        with patch.object(erp_modules, "listar_produtos", return_value=[]):
            app = self._render().run()
            app.text_input(
                key="vendas_create_item_1_product_search"
            ).set_value("inexistente")
            app.button(key="vendas_create_item_1_search_submit").click().run()

        self.assertEqual(app.exception, [])
        self.assertTrue(app.selectbox(key="vendas_create_item_1_product_id").disabled)
        self.assertTrue(
            any("Nenhum produto encontrado" in info.value for info in app.info)
        )

    def test_search_selects_real_catalog_id_and_sends_it(self):
        catalog = [{"id": 73, "name": "Produto Xano", "sku": "PX-73"}]
        with (
            patch.object(
                erp_modules,
                "listar_produtos",
                return_value=catalog,
            ) as list_products,
            patch.object(
                erp_modules,
                "criar_venda",
                return_value=self._sale_response(),
            ) as create_sale,
            patch.object(
                erp_modules,
                "listar_vendas",
                return_value=self._page(),
            ),
        ):
            app = self._render().run()
            app.text_input(
                key="vendas_create_item_1_product_search"
            ).set_value("Produto Xano")
            app.button(key="vendas_create_item_1_search_submit").click().run()
            app.selectbox(key="vendas_create_item_1_product_id").select(73)
            app.text_input(
                key="vendas_create_item_1_quantity"
            ).set_value("1")
            app.text_input(
                key="vendas_create_item_1_unit_sale_price"
            ).set_value("8.75")
            app.text_input(
                key="vendas_create_sales_channel"
            ).set_value("Canal livre")
            app.button(key="vendas_create_submit").click().run()

        self.assertEqual(app.exception, [])
        list_products.assert_called_once_with(
            token="mock-session-token",
            name="Produto Xano",
        )
        self.assertEqual(
            create_sale.call_args.args[0],
            "mock-session-token",
        )
        self.assertEqual(
            create_sale.call_args.args[1]["items"],
            [
                {
                    "product_id": 73,
                    "quantity": 1,
                    "unit_sale_price": 8.75,
                }
            ],
        )
        self.assertEqual(create_sale.call_args.args[1]["costs"], [])

    def test_multiple_items_are_preserved_in_payload(self):
        seed = self._selected_product_seed(item_ids=(1, 2))
        seed["vendas_create_item_2_product_id"] = 8
        seed["vendas_create_item_2_unit_sale_price"] = "20"
        with (
            patch.object(
                erp_modules,
                "criar_venda",
                return_value=self._sale_response(),
            ) as create_sale,
            patch.object(
                erp_modules,
                "listar_vendas",
                return_value=self._page(),
            ),
        ):
            app = self._render(seed=seed).run()
            app.button(key="vendas_create_submit").click().run()

        self.assertEqual(app.exception, [])
        self.assertEqual(
            create_sale.call_args.args[1]["items"],
            [
                {
                    "product_id": 7,
                    "quantity": 2,
                    "unit_sale_price": 12.5,
                },
                {
                    "product_id": 8,
                    "quantity": 2,
                    "unit_sale_price": 20.0,
                },
            ],
        )

    def test_add_and_remove_item_preserves_remaining_item(self):
        with patch.object(erp_modules, "listar_produtos", return_value=[]):
            app = self._render().run()
            app.button(key="vendas_create_add_item").click().run()

            app.session_state["vendas_create_item_1_products"] = [
                {"id": 7, "name": "Produto A"}
            ]
            app.session_state["vendas_create_item_1_product_id"] = 7
            app.session_state["vendas_create_item_2_products"] = [
                {"id": 8, "name": "Produto B"}
            ]
            app.session_state["vendas_create_item_2_product_id"] = 8
            app.session_state["vendas_create_item_2_quantity"] = "3"
            app.session_state["vendas_create_item_2_unit_sale_price"] = "6"
            app.run()
            app.button(key="vendas_create_item_1_remove").click().run()

        self.assertEqual(app.exception, [])
        self.assertNotIn("vendas_create_item_1_quantity", app.session_state)
        self.assertEqual(
            app.session_state["vendas_create_item_2_quantity"],
            "3",
        )
        self.assertEqual(
            app.session_state["vendas_create_items"],
            [{"id": 2}],
        )

    def test_quantity_must_be_positive_integer(self):
        for quantity in ("0", "-1", "1.5", "abc"):
            with self.subTest(quantity=quantity):
                with patch.object(erp_modules, "criar_venda") as create_sale:
                    app = self._render(
                        seed=self._selected_product_seed()
                    ).run()
                    app.text_input(
                        key="vendas_create_item_1_quantity"
                    ).set_value(quantity)
                    app.button(key="vendas_create_submit").click().run()

                create_sale.assert_not_called()
                self.assertTrue(
                    any("quantidade" in item.value for item in app.error)
                )

    def test_unit_price_validation_blocks_missing_negative_or_non_finite(self):
        for price in ("", "-1", "NaN", "inf", "texto"):
            with self.subTest(price=price):
                seed = self._selected_product_seed()
                seed["vendas_create_item_1_unit_sale_price"] = price
                with patch.object(erp_modules, "criar_venda") as create_sale:
                    app = self._render(seed=seed).run()
                    app.button(key="vendas_create_submit").click().run()

                create_sale.assert_not_called()
                self.assertTrue(app.error)

    def test_discount_validation_blocks_negative_or_non_finite(self):
        for discount in ("-1", "NaN", "inf", "texto", "25.01"):
            with self.subTest(discount=discount):
                seed = self._selected_product_seed()
                seed["vendas_create_item_1_discount_amount"] = discount
                with patch.object(erp_modules, "criar_venda") as create_sale:
                    app = self._render(seed=seed).run()
                    app.button(key="vendas_create_submit").click().run()

                create_sale.assert_not_called()
                self.assertTrue(app.error)

    def test_costs_can_be_added_removed_and_sent_globally(self):
        seed = self._selected_product_seed()
        seed["vendas_create_costs"] = [{"id": 1}, {"id": 2}]
        seed["vendas_create_next_cost_id"] = 3
        seed.update(
            {
                "vendas_create_cost_1_cost_type": "impostos",
                "vendas_create_cost_1_description": "Tributo",
                "vendas_create_cost_1_amount": "2.5",
                "vendas_create_cost_2_cost_type": "frete_saida",
                "vendas_create_cost_2_amount": "3",
            }
        )
        with (
            patch.object(
                erp_modules,
                "criar_venda",
                return_value=self._sale_response(),
            ) as create_sale,
            patch.object(
                erp_modules,
                "listar_vendas",
                return_value=self._page(),
            ),
        ):
            app = self._render(seed=seed).run()
            app.button(key="vendas_create_submit").click().run()

        self.assertEqual(app.exception, [])
        self.assertEqual(
            create_sale.call_args.args[1]["costs"],
            [
                {
                    "cost_type": "impostos",
                    "amount": 2.5,
                    "description": "Tributo",
                },
                {
                    "cost_type": "frete_saida",
                    "amount": 3.0,
                },
            ],
        )

    def test_remove_cost_preserves_other_cost(self):
        seed = self._selected_product_seed()
        seed["vendas_create_costs"] = [{"id": 1}, {"id": 2}]
        seed["vendas_create_next_cost_id"] = 3
        with patch.object(erp_modules, "listar_produtos", return_value=[]):
            app = self._render(seed=seed).run()
            app.button(key="vendas_create_cost_1_remove").click().run()

        self.assertEqual(app.exception, [])
        self.assertEqual(
            app.session_state["vendas_create_costs"],
            [{"id": 2}],
        )

    def test_invalid_cost_type_is_rejected_by_payload_builder(self):
        state = {
            "vendas_create_sales_channel": "Loja",
            "vendas_create_items": [{"id": 1}],
            "vendas_create_item_1_product_id": 7,
            "vendas_create_item_1_quantity": "1",
            "vendas_create_item_1_unit_sale_price": "5",
            "vendas_create_costs": [{"id": 1}],
            "vendas_create_cost_1_cost_type": "cliente",
            "vendas_create_cost_1_amount": "1",
        }
        with patch.object(erp_modules.st, "session_state", state):
            with self.assertRaisesRegex(ValueError, "tipo válido"):
                erp_modules._construir_payload_venda_interface()

    def test_sale_without_costs_includes_empty_costs_array_in_payload(self):
        with patch.object(
            erp_modules.st,
            "session_state",
            {
                "vendas_create_sales_channel": "Loja",
                "vendas_create_items": [{"id": 1}],
                "vendas_create_item_1_product_id": 7,
                "vendas_create_item_1_quantity": "1",
                "vendas_create_item_1_unit_sale_price": "5",
                "vendas_create_item_1_discount_amount": "",
                "vendas_create_costs": [],
            },
        ):
            payload = erp_modules._construir_payload_venda_interface()

        self.assertEqual(payload["costs"], [])
        self.assertNotIn("sale_date", payload)
        self.assertNotIn("discount_amount", payload["items"][0])

    def test_manual_current_and_historical_dates_use_unix_milliseconds(self):
        today = date.today()
        cases = (
            (
                today.isoformat(),
                int(
                    datetime(
                        today.year,
                        today.month,
                        today.day,
                        tzinfo=timezone.utc,
                    ).timestamp()
                    * 1000
                ),
            ),
            (
                "2020-05-01T10:30:45.123-03:00",
                int(
                    datetime(
                        2020,
                        5,
                        1,
                        13,
                        30,
                        45,
                        123000,
                        tzinfo=timezone.utc,
                    ).timestamp()
                    * 1000
                ),
            ),
        )
        for entered_date, expected in cases:
            with self.subTest(entered_date=entered_date):
                seed = self._selected_product_seed()
                seed["vendas_create_sale_date"] = entered_date
                with patch.object(erp_modules.st, "session_state", seed):
                    payload = erp_modules._construir_payload_venda_interface()

                self.assertEqual(payload["sale_date"], expected)
                self.assertGreater(payload["sale_date"], 100_000_000_000)

    def test_manual_seconds_timestamp_is_rejected(self):
        seed = self._selected_product_seed()
        seed["vendas_create_sale_date"] = "1773577800"
        with patch.object(erp_modules.st, "session_state", seed):
            with self.assertRaisesRegex(ValueError, "milissegundos"):
                erp_modules._construir_payload_venda_interface()

    def test_payload_contains_only_documented_fields_and_preserves_date(self):
        seed = self._selected_product_seed()
        seed.update(
            {
                "vendas_create_order_number": " PED-1 ",
                "vendas_create_sale_date": "2026-11-17T22:00:00Z",
                "vendas_create_notes": " Nota ",
                "vendas_list_filter_channel": "Marketplace",
                "vendas_list_filter_order_number": "PED",
                "vendas_list_filter_status": "registrada",
            }
        )
        with (
            patch.object(
                erp_modules,
                "criar_venda",
                return_value=self._sale_response(),
            ) as create_sale,
            patch.object(
                erp_modules,
                "listar_vendas",
                return_value=self._page(),
            ),
        ):
            app = self._render(seed=seed).run()
            app.button(key="vendas_create_submit").click().run()

        self.assertEqual(app.exception, [])
        self.assertEqual(
            create_sale.call_args.args[1],
            {
                "idempotency_key": create_sale.call_args.args[1][
                    "idempotency_key"
                ],
                "sales_channel": "Canal livre",
                "order_number": "PED-1",
                "sale_date": int(
                    datetime(
                        2026,
                        11,
                        17,
                        22,
                        tzinfo=timezone.utc,
                    ).timestamp()
                    * 1000
                ),
                "notes": "Nota",
                "items": [
                    {
                        "product_id": 7,
                        "quantity": 2,
                        "unit_sale_price": 12.5,
                    }
                ],
                "costs": [],
            },
        )
        self.assertEqual(
            UUID(create_sale.call_args.args[1]["idempotency_key"]).version,
            4,
        )
        self.assertNotIn(
            "idempotency_key",
            create_sale.call_args.args[1]["items"][0],
        )
        self.assertNotIn("customer", create_sale.call_args.args[1])
        self.assertNotIn("client", create_sale.call_args.args[1])
        self.assertNotIn("status", create_sale.call_args.args[1])

    def test_payload_fingerprint_is_stable_and_preserves_wire_semantics(self):
        payload = {
            "sales_channel": "Canal livre",
            "items": [
                {"product_id": 7, "quantity": 1, "unit_sale_price": 1},
                {"product_id": 8, "quantity": 1, "unit_sale_price": 2},
                {"product_id": 7, "quantity": 1, "unit_sale_price": 1},
                {"product_id": 9, "quantity": 1, "unit_sale_price": 3},
            ],
        }
        reordered_keys = {
            "items": [
                {"unit_sale_price": 1, "quantity": 1, "product_id": 7},
                {"unit_sale_price": 2, "quantity": 1, "product_id": 8},
                {"unit_sale_price": 1, "quantity": 1, "product_id": 7},
                {"unit_sale_price": 3, "quantity": 1, "product_id": 9},
            ],
            "sales_channel": "Canal livre",
        }

        fingerprint = erp_modules._fingerprint_payload_venda_interface(
            payload
        )
        self.assertEqual(
            fingerprint,
            erp_modules._fingerprint_payload_venda_interface(reordered_keys),
        )
        self.assertEqual(
            fingerprint,
            erp_modules._fingerprint_payload_venda_interface(
                {**payload, "idempotency_key": "ignored"}
            ),
        )
        self.assertNotEqual(
            fingerprint,
            erp_modules._fingerprint_payload_venda_interface(
                {**payload, "sale_date": None}
            ),
        )
        self.assertNotEqual(
            fingerprint,
            erp_modules._fingerprint_payload_venda_interface(
                {
                    **payload,
                    "items": list(reversed(payload["items"])),
                }
            ),
        )
        self.assertNotEqual(
            fingerprint,
            erp_modules._fingerprint_payload_venda_interface(
                {**payload, "items": payload["items"][:-1]}
            ),
        )
        self.assertNotEqual(
            erp_modules._fingerprint_payload_venda_interface(
                {
                    **payload,
                    "items": [
                        {
                            "product_id": 7,
                            "quantity": 1,
                            "unit_sale_price": 1.0,
                        },
                        payload["items"][1],
                    ],
                }
            ),
            fingerprint,
        )

    def test_success_shows_backend_financial_values_and_refreshes_list(self):
        seed = self._selected_product_seed()
        seed["vendas_list_page"] = 4
        with (
            patch.object(
                erp_modules,
                "criar_venda",
                return_value=self._sale_response(),
            ) as create_sale,
            patch.object(
                erp_modules,
                "listar_vendas",
                return_value=self._page([{"id": 91}]),
            ) as list_sales,
        ):
            app = self._render(seed=seed).run()
            app.button(key="vendas_create_submit").click().run()

        self.assertEqual(app.exception, [])
        create_sale.assert_called_once()
        list_sales.assert_called_once()
        self.assertEqual(list_sales.call_args.kwargs["page"], 1)
        self.assertEqual(
            list_sales.call_args.kwargs["sales_channel"],
            "Canal livre",
        )
        self.assertEqual(
            app.session_state["vendas_list_filter_channel"],
            "Canal livre",
        )
        self.assertTrue(
            any("Venda registrada" in item.value for item in app.success)
        )
        summary = [
            frame.value
            for frame in app.dataframe
            if "total_cmv" in frame.value.columns
        ]
        self.assertEqual(summary[0].loc[0, "total_cmv"], 11.0)
        self.assertEqual(app.session_state["vendas_create_sales_channel"], "")
        self.assertNotIn("vendas_create_idempotency_key", app.session_state)
        self.assertNotIn(
            "vendas_create_payload_fingerprint",
            app.session_state,
        )
        self.assertEqual(
            app.session_state["vendas_list_page"],
            1,
        )

    def test_http_401_and_403_are_reported_without_success(self):
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
                    "criar_venda",
                    side_effect=error,
                ) as create_sale:
                    app = self._render(
                        seed=self._selected_product_seed()
                    ).run()
                    app.button(key="vendas_create_submit").click().run()

                self.assertEqual(app.exception, [])
                create_sale.assert_called_once()
                self.assertTrue(
                    any(expected in item.value for item in app.error)
                )
                self.assertFalse(app.success)

    def test_definitive_validation_error_does_not_show_success(self):
        with patch.object(
            erp_modules,
            "criar_venda",
            side_effect=ValueError("product_id rejected"),
        ) as create_sale:
            app = self._render(seed=self._selected_product_seed()).run()
            app.button(key="vendas_create_submit").click().run()

        create_sale.assert_called_once()
        self.assertTrue(app.error)
        self.assertFalse(app.success)
        self.assertIn(
            "vendas_create_sales_channel",
            app.session_state,
        )

    def test_inconclusive_operation_blocks_automatic_retry_and_preserves_form(self):
        seed = self._selected_product_seed()
        with patch.object(
            erp_modules,
            "criar_venda",
            side_effect=xano_client.OperacaoVendaInconclusivaError(
                "Não foi possível confirmar."
            ),
        ) as create_sale:
            app = self._render(seed=seed).run()
            app.button(key="vendas_create_submit").click().run()

        create_sale.assert_called_once()
        idempotency_key = app.session_state["vendas_create_idempotency_key"]
        self.assertEqual(UUID(idempotency_key).version, 4)
        self.assertEqual(
            create_sale.call_args.args[1]["idempotency_key"],
            idempotency_key,
        )
        self.assertTrue(app.button(key="vendas_create_submit").disabled)
        self.assertTrue(app.session_state["vendas_create_inconclusive"])
        self.assertEqual(
            app.session_state["vendas_create_item_1_unit_sale_price"],
            "12.5",
        )
        self.assertFalse(app.success)
        self.assertTrue(
            any("Não inicie outra venda" in item.value for item in app.error)
        )
        self.assertEqual(
            app.session_state["vendas_create_operation_status"],
            "inconclusive",
        )
        reconcile = app.button(key="vendas_create_reconcile_pending")
        self.assertFalse(reconcile.disabled)

    def test_incomplete_response_is_inconclusive_and_does_not_refresh_list(self):
        incomplete = {"sale": {"id": 91}, "items": [], "costs": []}
        with (
            patch.object(
                erp_modules,
                "criar_venda",
                return_value=incomplete,
            ) as create_sale,
            patch.object(erp_modules, "listar_vendas") as list_sales,
        ):
            app = self._render(
                seed=self._selected_product_seed()
            ).run()
            app.button(key="vendas_create_submit").click().run()

        create_sale.assert_called_once()
        list_sales.assert_not_called()
        self.assertTrue(app.session_state["vendas_create_inconclusive"])
        self.assertFalse(app.success)

    def test_connection_failure_is_inconclusive_without_retry(self):
        with patch.object(
            erp_modules,
            "criar_venda",
            side_effect=xano_client.OperacaoVendaInconclusivaError(
                "Timeout."
            ),
        ) as create_sale:
            app = self._render(
                seed=self._selected_product_seed()
            ).run()
            app.button(key="vendas_create_submit").click().run()

        create_sale.assert_called_once()
        self.assertTrue(app.session_state["vendas_create_inconclusive"])
        self.assertTrue(
            UUID(app.session_state["vendas_create_idempotency_key"]).version
            == 4
        )
        self.assertFalse(app.success)

    def test_reconciliation_reuses_original_key_and_payload(self):
        with patch.object(
            erp_modules,
            "criar_venda",
            side_effect=[
                xano_client.OperacaoVendaInconclusivaError("Timeout."),
                self._sale_response(),
            ],
        ) as create_sale, patch.object(
            erp_modules,
            "listar_vendas",
            return_value=self._page(),
        ):
            app = self._render(
                seed=self._selected_product_seed()
            ).run(timeout=10)
            app.button(key="vendas_create_submit").click().run(timeout=10)
            first_key = app.session_state["vendas_create_idempotency_key"]
            original_payload = app.session_state[
                "vendas_create_operation_payload"
            ].copy()
            create_sale.assert_called_once()

            app.text_input(
                key="vendas_create_item_1_unit_sale_price"
            ).set_value("99").run(timeout=10)
            self.assertTrue(app.button(key="vendas_create_submit").disabled)
            app.button(
                key="vendas_create_reconcile_pending"
            ).click().run(timeout=10)

        self.assertEqual(app.exception, [])
        self.assertEqual(create_sale.call_count, 2)
        self.assertEqual(
            create_sale.call_args_list[1].args[1],
            {**original_payload, "idempotency_key": first_key},
        )
        self.assertEqual(
            create_sale.call_args_list[0].args[1]["idempotency_key"],
            first_key,
        )
        self.assertEqual(
            create_sale.call_args_list[0].args[1]["items"][0][
                "unit_sale_price"
            ],
            12.5,
        )
        self.assertEqual(
            app.session_state["vendas_create_operation_status"],
            "completed",
        )
        self.assertNotIn(
            "vendas_create_idempotency_key",
            app.session_state,
        )
        self.assertTrue(app.success)

    def test_inconclusive_results_keep_pending_snapshot_when_form_changes(self):
        scenarios = (
            (
                "timeout",
                xano_client.OperacaoVendaInconclusivaError("Timeout."),
            ),
            (
                "connection",
                xano_client.OperacaoVendaInconclusivaError("Connection lost."),
            ),
            (
                "incomplete",
                {"sale": {"id": 91}, "items": [], "costs": []},
            ),
        )
        for scenario, result in scenarios:
            with self.subTest(scenario=scenario):
                with patch.object(
                    erp_modules,
                    "criar_venda",
                    side_effect=(
                        result if isinstance(result, Exception) else None
                    ),
                    return_value=(
                        None if isinstance(result, Exception) else result
                    ),
                ) as create_sale:
                    app = self._render(
                        seed=self._selected_product_seed()
                    ).run(timeout=10)
                    app.button(key="vendas_create_submit").click().run(
                        timeout=10
                    )
                    original_key = app.session_state[
                        "vendas_create_idempotency_key"
                    ]
                    original_payload = app.session_state[
                        "vendas_create_operation_payload"
                    ].copy()

                    app.text_input(
                        key="vendas_create_item_1_unit_sale_price"
                    ).set_value("77").run(timeout=10)

                create_sale.assert_called_once()
                self.assertTrue(
                    app.button(key="vendas_create_submit").disabled
                )
                reconcile = app.button(
                    key="vendas_create_reconcile_pending"
                )
                self.assertFalse(reconcile.disabled)
                self.assertEqual(
                    app.session_state["vendas_create_idempotency_key"],
                    original_key,
                )
                self.assertEqual(
                    app.session_state["vendas_create_operation_payload"],
                    original_payload,
                )
                self.assertEqual(
                    app.session_state["vendas_create_operation_status"],
                    "inconclusive",
                )
                self.assertEqual(
                    app.session_state["vendas_create_item_1_unit_sale_price"],
                    "77",
                )

    def test_new_operation_is_released_only_after_confirmed_reconciliation(self):
        catalog = [{"id": 7, "name": "Produto real", "sku": "PR-7"}]
        with (
            patch.object(
                erp_modules,
                "criar_venda",
                side_effect=[
                    xano_client.OperacaoVendaInconclusivaError("Timeout."),
                    self._sale_response(),
                    self._sale_response(),
                ],
            ) as create_sale,
            patch.object(
                erp_modules,
                "listar_produtos",
                return_value=catalog,
            ),
            patch.object(
                erp_modules,
                "listar_vendas",
                return_value=self._page(),
            ),
        ):
            app = self._render(
                seed=self._selected_product_seed()
            ).run(timeout=10)
            app.button(key="vendas_create_submit").click().run(timeout=10)
            pending_key = app.session_state["vendas_create_idempotency_key"]

            app.button(
                key="vendas_create_reconcile_pending"
            ).click().run(timeout=10)
            self.assertEqual(
                app.session_state["vendas_create_operation_status"],
                "completed",
            )
            self.assertNotIn(
                "vendas_create_idempotency_key",
                app.session_state,
            )

            app.text_input(
                key="vendas_create_sales_channel"
            ).set_value("Novo canal").run(timeout=10)
            app.text_input(
                key="vendas_create_item_1_product_search"
            ).set_value("Produto real").run(timeout=10)
            app.button(
                key="vendas_create_item_1_search_submit"
            ).click().run(timeout=10)
            app.selectbox(
                key="vendas_create_item_1_product_id"
            ).select(7).run(timeout=10)
            app.text_input(
                key="vendas_create_item_1_quantity"
            ).set_value("1").run(timeout=10)
            app.text_input(
                key="vendas_create_item_1_unit_sale_price"
            ).set_value("10").run(timeout=10)
            app.button(key="vendas_create_submit").click().run(timeout=10)

        self.assertEqual(app.exception, [])
        self.assertEqual(create_sale.call_count, 3)
        first_key, reconciled_key, next_sale_key = [
            call.args[1]["idempotency_key"]
            for call in create_sale.call_args_list
        ]
        self.assertEqual(first_key, pending_key)
        self.assertEqual(reconciled_key, pending_key)
        self.assertNotEqual(next_sale_key, pending_key)

    def test_idempotency_lock_errors_are_specific_and_keep_the_key(self):
        scenarios = (
            ("IDEMPOTENCY_LOCKED", "ainda está processando"),
            (
                "IDEMPOTENCY_CONCURRENT_REQUEST",
                "solicitação concorrente",
            ),
            ("IDEMPOTENCY_LOCK_FAILED", "não conseguiu obter o bloqueio"),
        )
        for error_code, expected_message in scenarios:
            with self.subTest(error_code=error_code):
                with patch.object(
                    erp_modules,
                    "criar_venda",
                    side_effect=self._http_error(400, error_code),
                ) as create_sale:
                    app = self._render(
                        seed=self._selected_product_seed()
                    ).run(timeout=10)
                    app.button(key="vendas_create_submit").click().run(
                        timeout=10
                    )

                create_sale.assert_called_once()
                self.assertTrue(
                    app.session_state["vendas_create_inconclusive"]
                )
                self.assertEqual(
                    app.session_state["vendas_create_idempotency_error_code"],
                    error_code,
                )
                self.assertEqual(
                    create_sale.call_args.args[1]["idempotency_key"],
                    app.session_state["vendas_create_idempotency_key"],
                )
                self.assertTrue(
                    any(expected_message in item.value for item in app.warning)
                )
                self.assertFalse(app.success)

    def test_payload_mismatch_keeps_operation_blocked_when_form_changes(self):
        with patch.object(
            erp_modules,
            "criar_venda",
            side_effect=self._http_error(
                400,
                "IDEMPOTENCY_PAYLOAD_MISMATCH",
            ),
        ) as create_sale:
            app = self._render(
                seed=self._selected_product_seed()
            ).run(timeout=10)
            app.button(key="vendas_create_submit").click().run(timeout=10)
            first_key = app.session_state["vendas_create_idempotency_key"]
            original_payload = app.session_state[
                "vendas_create_operation_payload"
            ].copy()

            self.assertTrue(app.button(key="vendas_create_submit").disabled)
            self.assertEqual(create_sale.call_count, 1)
            self.assertTrue(
                any("associada a outro payload" in item.value for item in app.error)
            )

            app.text_input(
                key="vendas_create_item_1_unit_sale_price"
            ).set_value("13.5").run(timeout=10)
            self.assertTrue(app.button(key="vendas_create_submit").disabled)
            self.assertEqual(create_sale.call_count, 1)

        self.assertEqual(app.exception, [])
        self.assertEqual(
            app.session_state["vendas_create_idempotency_key"],
            first_key,
        )
        self.assertEqual(
            app.session_state["vendas_create_operation_payload"],
            original_payload,
        )
        self.assertEqual(
            app.session_state["vendas_create_operation_status"],
            "inconclusive",
        )
        self.assertFalse(app.success)

    def test_listing_refresh_occurs_only_after_valid_confirmation(self):
        with (
            patch.object(
                erp_modules,
                "criar_venda",
                side_effect=xano_client.RespostaVendaInconclusivaError(
                    "Resposta incompleta."
                ),
            ),
            patch.object(erp_modules, "listar_vendas") as list_sales,
        ):
            app = self._render(
                seed=self._selected_product_seed()
            ).run()
            app.button(key="vendas_create_submit").click().run()

        list_sales.assert_not_called()
        self.assertTrue(app.session_state["vendas_create_inconclusive"])

    def test_success_preserves_active_listing_filters(self):
        seed = self._selected_product_seed()
        seed.update(
            {
                "vendas_list_filter_channel": "Marketplace",
                "vendas_list_filter_order_number": "PED",
                "vendas_list_filter_status": "registrada",
                "vendas_list_filter_start_date": "2026-11-01",
                "vendas_list_filter_end_date": "2026-11-17",
                "vendas_list_per_page": 10,
            }
        )
        with (
            patch.object(
                erp_modules,
                "criar_venda",
                return_value=self._sale_response(),
            ),
            patch.object(
                erp_modules,
                "listar_vendas",
                return_value=self._page(),
            ) as list_sales,
        ):
            app = self._render(seed=seed).run()
            app.button(key="vendas_create_submit").click().run()

        self.assertEqual(app.exception, [])
        self.assertEqual(
            list_sales.call_args.kwargs,
            {
                "page": 1,
                "per_page": 10,
                "sales_channel": "Marketplace",
                "order_number": "PED",
                "start_date": "2026-11-01",
                "end_date": "2026-11-17",
                "status": "registrada",
            },
        )
        for key in (
            "vendas_list_filter_channel",
            "vendas_list_filter_order_number",
            "vendas_list_filter_status",
            "vendas_list_filter_start_date",
            "vendas_list_filter_end_date",
        ):
            self.assertIn(key, app.session_state)


if __name__ == "__main__":
    unittest.main()
