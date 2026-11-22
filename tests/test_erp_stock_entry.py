import unittest
from unittest.mock import patch
from uuid import UUID

import requests
from streamlit.testing.v1 import AppTest

import app.erp_modules as erp_modules
from tests.ui_test_utils import auto_confirm_operations


class StockEntryFormTests(unittest.TestCase):
    def setUp(self):
        auto_confirm_operations(self, erp_modules)
        self.products = [
            {"id": 14, "name": "Caneca", "sku": "CAN-14"},
        ]
        self.suppliers = [
            {
                "id": 29,
                "name": "Fornecedor Real",
                "cnpj": "12345678000190",
            },
            {
                "id": 37,
                "name": "Fornecedor Alternativo",
                "email": "alternativo@example.test",
            },
        ]
        self.confirmation = {
            "entry": {"id": 101},
            "movement": {"id": 202},
            "stock_quantity": 18,
            "average_cost": 7.5,
        }
        self.session_state = {
            "auth_user": {
                "id": 7,
                "email": "operator@example.test",
            }
        }

    def test_supplier_loader_uses_session_and_active_filter(self):
        with patch.object(
            erp_modules,
            "listar_fornecedores",
            return_value=self.suppliers,
        ) as list_suppliers:
            suppliers, error = erp_modules._carregar_fornecedores_entrada(
                "session-token"
            )

        self.assertEqual(suppliers, self.suppliers)
        self.assertIsNone(error)
        list_suppliers.assert_called_once_with(
            token="session-token",
            status="ativo",
        )

    def test_supplier_loader_handles_missing_token_empty_list_and_failures(self):
        with patch.object(erp_modules, "listar_fornecedores") as list_suppliers:
            suppliers, error = erp_modules._carregar_fornecedores_entrada(None)
        self.assertEqual(suppliers, [])
        self.assertIn("sessão", error)
        list_suppliers.assert_not_called()

        with patch.object(erp_modules, "listar_fornecedores", return_value=[]):
            suppliers, error = erp_modules._carregar_fornecedores_entrada(
                "session-token"
            )
        self.assertEqual(suppliers, [])
        self.assertIsNone(error)

        response = requests.Response()
        response.status_code = 403
        failures = (
            requests.HTTPError(response=response),
            requests.ConnectionError("offline"),
            ValueError("resposta inesperada"),
        )
        for failure in failures:
            with self.subTest(failure=type(failure).__name__):
                with patch.object(
                    erp_modules,
                    "listar_fornecedores",
                    side_effect=failure,
                ):
                    suppliers, error = erp_modules._carregar_fornecedores_entrada(
                        "session-token"
                    )
                self.assertEqual(suppliers, [])
                self.assertTrue(error)

    def test_selected_supplier_real_id_is_sent_with_existing_post_fields(self):
        with patch.object(
            erp_modules,
            "criar_entrada_estoque",
            return_value=self.confirmation,
        ) as create:
            state, message, response = erp_modules._enviar_formulario_entrada(
                "session-token",
                self.products,
                self.suppliers,
                product_id=14,
                supplier_id=37,
                quantity=3,
                unit_purchase_cost=8.75,
                entry_date="2026-11-03",
                invoice_number="NF-123",
                notes="Compra mensal",
                inbound_freight=12.5,
                session_state=self.session_state,
            )

        self.assertEqual(state, "success")
        self.assertIn("confirmação", message)
        self.assertEqual(response, self.confirmation)
        create.assert_called_once()
        call = create.call_args
        self.assertEqual(call.args[0], "session-token")
        self.assertEqual(call.kwargs["product_id"], 14)
        self.assertEqual(call.kwargs["supplier_id"], 37)
        self.assertEqual(call.kwargs["quantity"], 3)
        self.assertEqual(call.kwargs["unit_purchase_cost"], 8.75)
        self.assertEqual(call.kwargs["entry_date"], "2026-11-03")
        self.assertEqual(call.kwargs["invoice_number"], "NF-123")
        self.assertEqual(call.kwargs["notes"], "Compra mensal")
        self.assertEqual(call.kwargs["inbound_freight"], 12.5)
        self.assertNotIn("other_acquisition_costs", call.kwargs)
        self.assertEqual(UUID(call.kwargs["idempotency_key"]).version, 4)
        operation = self.session_state[
            erp_modules._ENTRADAS_ESTOQUE_OPERACOES_KEY
        ][call.kwargs["idempotency_key"]]
        self.assertEqual(operation["status"], "confirmed")
        self.assertEqual(operation["payload"]["product_id"], 14)
        self.assertEqual(operation["form_data"]["supplier_id"], 37)

    def test_missing_or_unlisted_supplier_blocks_post(self):
        with patch.object(erp_modules, "criar_entrada_estoque") as create:
            cases = (
                (None, self.suppliers),
                (999, self.suppliers),
                (37, []),
            )
            for supplier_id, suppliers in cases:
                with self.subTest(supplier_id=supplier_id, suppliers=suppliers):
                    state, message, response = erp_modules._enviar_formulario_entrada(
                        "session-token",
                        self.products,
                        suppliers,
                        product_id=14,
                        supplier_id=supplier_id,
                        quantity=1,
                        unit_purchase_cost=0,
                        entry_date="2026-11-03",
                        invoice_number="NF-123",
                        notes="Entrada",
                        session_state=self.session_state,
                    )
                    self.assertEqual(state, "validation")
                    self.assertTrue(message)
                    self.assertIsNone(response)

        create.assert_not_called()

    def test_missing_session_token_blocks_post(self):
        with patch.object(erp_modules, "criar_entrada_estoque") as create:
            state, message, response = erp_modules._enviar_formulario_entrada(
                None,
                self.products,
                self.suppliers,
                product_id=14,
                supplier_id=29,
                quantity=1,
                unit_purchase_cost=0,
                entry_date="2026-11-03",
                invoice_number="NF-123",
                notes="Entrada",
                session_state=self.session_state,
            )

        self.assertEqual(state, "error")
        self.assertIn("sessão", message)
        self.assertIsNone(response)
        create.assert_not_called()

    def test_ambiguous_http_error_keeps_pending_operation_without_retry(self):
        response = requests.Response()
        response.status_code = 502
        error = requests.HTTPError("gateway timeout", response=response)
        with patch.object(
            erp_modules,
            "criar_entrada_estoque",
            side_effect=error,
        ) as create:
            state, message, result = erp_modules._enviar_formulario_entrada(
                "session-token",
                self.products,
                self.suppliers,
                product_id=14,
                supplier_id=29,
                quantity=3,
                unit_purchase_cost=8.75,
                entry_date="2026-11-03",
                invoice_number="NF-123",
                notes="Compra mensal",
                session_state=self.session_state,
            )

            self.assertEqual(state, "inconclusive")
            self.assertIn("não será repetido", message)
            self.assertIsNone(result)
            create.assert_called_once()

            state, _, result = erp_modules._enviar_formulario_entrada(
                "session-token",
                self.products,
                self.suppliers,
                product_id=14,
                supplier_id=29,
                quantity=3,
                unit_purchase_cost=8.75,
                entry_date="2026-11-03",
                invoice_number="NF-123",
                notes="Compra mensal",
                session_state=self.session_state,
            )

        self.assertEqual(state, "blocked")
        self.assertIsNone(result)
        create.assert_called_once()

    def test_streamlit_selection_displays_supplier_and_posts_selected_id(self):
        with patch.object(
            erp_modules,
            "_carregar_fornecedores_entrada",
            return_value=(self.suppliers, None),
        ), patch.object(
            erp_modules,
            "listar_produtos",
            return_value=self.products,
        ), patch.object(
            erp_modules,
            "criar_entrada_estoque",
            return_value=self.confirmation,
        ) as create:
            app = AppTest.from_string(
                "import app.erp_modules as erp_modules\n"
                "erp_modules._render_formulario_entrada_estoque()"
            )
            app.session_state["auth_token"] = "mock-session-token"
            app.session_state["auth_user"] = {
                "id": 7,
                "email": "operator@example.test",
                "profile": "Adm",
            }
            app.session_state["historico_movimentacoes_resultado"] = {
                "state": "success",
                "movements": [{"id": 2}],
            }
            app.session_state["saldo_estoque_resultado"] = {
                "state": "success",
                "items": [{"id": 14}],
            }
            app.run()
            app.text_input(key="entrada_estoque_product_query").set_value("Caneca")
            app.button(key="entrada_estoque_search_products").click().run()

            supplier_select = app.selectbox(key="entrada_estoque_supplier")
            supplier_select.select_index(1)
            app.text_input(key="entrada_estoque_invoice").set_value("NF-123")
            app.text_area(key="entrada_estoque_notes").set_value("Compra mensal")
            app.form_submit_button(key="entrada_estoque_submit").click().run()

        self.assertEqual(app.exception, [])
        self.assertEqual(
            supplier_select.options[1],
            "Fornecedor Alternativo",
        )
        self.assertEqual(supplier_select.value, "Fornecedor Alternativo")
        self.assertEqual(create.call_args.kwargs["supplier_id"], 37)
        self.assertEqual(create.call_args.kwargs["product_id"], 14)
        self.assertNotIn(
            "historico_movimentacoes_resultado",
            app.session_state,
        )
        self.assertNotIn("saldo_estoque_resultado", app.session_state)

    def _create_stock_entry_app(self):
        app = AppTest.from_string(
            "import app.erp_modules as erp_modules\n"
            "erp_modules._render_formulario_entrada_estoque()"
        )
        app.session_state["auth_token"] = "mock-session-token"
        app.session_state["auth_user"] = {
            "id": 7,
            "email": "operator@example.test",
            "profile": "Adm",
        }
        return app

    def _prepare_stock_entry_form(self, app):
        app.run()
        app.text_input(key="entrada_estoque_product_query").set_value("Caneca")
        app.button(key="entrada_estoque_search_products").click().run()
        app.text_input(key="entrada_estoque_invoice").set_value("NF-123")
        app.text_area(key="entrada_estoque_notes").set_value("Compra mensal")

    def test_inconclusive_submission_preserves_snapshot_and_blocks_repeats(self):
        with patch.object(
            erp_modules,
            "_carregar_fornecedores_entrada",
            return_value=(self.suppliers, None),
        ), patch.object(
            erp_modules,
            "listar_produtos",
            return_value=self.products,
        ), patch.object(
            erp_modules,
            "criar_entrada_estoque",
            side_effect=requests.ConnectionError("offline"),
        ) as create:
            app = self._create_stock_entry_app()
            self._prepare_stock_entry_form(app)
            app.form_submit_button(key="entrada_estoque_submit").click().run()

            operations = app.session_state[
                erp_modules._ENTRADAS_ESTOQUE_OPERACOES_KEY
            ]
            self.assertEqual(len(operations), 1)
            key, operation = next(iter(operations.items()))
            original_payload = dict(operation["payload"])
            self.assertEqual(operation["status"], "pending")
            self.assertEqual(operation["idempotency_key"], key)
            self.assertEqual(operation["payload"]["invoice_number"], "NF-123")
            self.assertEqual(operation["payload"]["notes"], "Compra mensal")
            self.assertEqual(operation["form_data"]["product_id"], 14)
            self.assertTrue(operation["message"])
            self.assertEqual(create.call_count, 1)

            app.session_state["entrada_estoque_invoice"] = "NF-ALTERADA"
            app.run()
            self.assertFalse(
                any(
                    button.key == "entrada_estoque_submit"
                    for button in app.form_submit_button
                )
            )
            self.assertEqual(
                app.session_state[
                    erp_modules._ENTRADAS_ESTOQUE_OPERACOES_KEY
                ][key]["idempotency_key"],
                key,
            )
            self.assertEqual(
                app.session_state[
                    erp_modules._ENTRADAS_ESTOQUE_OPERACOES_KEY
                ][key]["payload"],
                original_payload,
            )
            self.assertEqual(create.call_count, 1)

            state, message, response = erp_modules._enviar_formulario_entrada(
                "mock-session-token",
                self.products,
                self.suppliers,
                product_id=14,
                supplier_id=29,
                quantity=1,
                unit_purchase_cost=0,
                entry_date="2026-11-03",
                invoice_number="NF-123",
                notes="Compra mensal",
                session_state=app.session_state,
            )
            self.assertEqual(state, "blocked")
            self.assertIn("resultado desconhecido", message)
            self.assertIsNone(response)
            self.assertEqual(create.call_count, 1)

    def test_pending_operation_is_not_reused_or_removed_after_user_switch(self):
        with patch.object(
            erp_modules,
            "_carregar_fornecedores_entrada",
            return_value=(self.suppliers, None),
        ), patch.object(
            erp_modules,
            "listar_produtos",
            return_value=self.products,
        ), patch.object(
            erp_modules,
            "criar_entrada_estoque",
            side_effect=requests.Timeout("timed out"),
        ) as create:
            app = self._create_stock_entry_app()
            self._prepare_stock_entry_form(app)
            app.form_submit_button(key="entrada_estoque_submit").click().run()
            operations = app.session_state[
                erp_modules._ENTRADAS_ESTOQUE_OPERACOES_KEY
            ]
            key, operation = next(iter(operations.items()))
            original_payload = dict(operation["payload"])

            app.session_state["auth_user"] = {
                "id": 8,
                "email": "other@example.test",
                "profile": "Adm",
            }
            app.run()

            self.assertEqual(create.call_count, 1)
            self.assertEqual(
                app.session_state[
                    erp_modules._ENTRADAS_ESTOQUE_OPERACOES_KEY
                ][key]["status"],
                "pending",
            )
            self.assertEqual(
                app.session_state[
                    erp_modules._ENTRADAS_ESTOQUE_OPERACOES_KEY
                ][key]["owner_identity"],
                "id:7",
            )
            self.assertEqual(
                app.session_state[
                    erp_modules._ENTRADAS_ESTOQUE_OPERACOES_KEY
                ][key]["payload"],
                original_payload,
            )
            self.assertTrue(
                any("usuário original" in item.value for item in app.info)
            )
            self.assertFalse(
                any(item.key == "entrada_estoque_submit" for item in app.button)
            )

    def test_confirmed_response_finishes_operation_and_allows_new_operation(self):
        with patch.object(
            erp_modules,
            "_carregar_fornecedores_entrada",
            return_value=(self.suppliers, None),
        ), patch.object(
            erp_modules,
            "listar_produtos",
            return_value=self.products,
        ), patch.object(
            erp_modules,
            "criar_entrada_estoque",
            return_value=self.confirmation,
        ) as create:
            app = self._create_stock_entry_app()
            self._prepare_stock_entry_form(app)
            app.form_submit_button(key="entrada_estoque_submit").click().run()
            operations = app.session_state[
                erp_modules._ENTRADAS_ESTOQUE_OPERACOES_KEY
            ]
            first_key, first_operation = next(iter(operations.items()))
            self.assertEqual(first_operation["status"], "confirmed")
            self.assertEqual(first_operation["response"], self.confirmation)

            app.form_submit_button(key="entrada_estoque_submit").click().run()
            self.assertEqual(create.call_count, 1)

            app.text_input(key="entrada_estoque_invoice").set_value("NF-124")
            app.text_area(key="entrada_estoque_notes").set_value(
                "Nova entrada independente"
            )
            app.form_submit_button(key="entrada_estoque_submit").click().run()
            self.assertEqual(create.call_count, 2)
            operations = app.session_state[
                erp_modules._ENTRADAS_ESTOQUE_OPERACOES_KEY
            ]
            self.assertEqual(len(operations), 2)
            second_key = next(key for key in operations if key != first_key)
            self.assertNotEqual(second_key, first_key)
            self.assertEqual(operations[second_key]["status"], "confirmed")

    def test_manual_not_found_resolution_preserves_old_operation_and_allows_new_one(self):
        with patch.object(
            erp_modules,
            "_carregar_fornecedores_entrada",
            return_value=(self.suppliers, None),
        ), patch.object(
            erp_modules,
            "listar_produtos",
            return_value=self.products,
        ), patch.object(
            erp_modules,
            "criar_entrada_estoque",
            side_effect=(
                requests.ConnectionError("offline"),
                self.confirmation,
            ),
        ) as create:
            app = self._create_stock_entry_app()
            self._prepare_stock_entry_form(app)
            app.form_submit_button(key="entrada_estoque_submit").click().run()
            operations = app.session_state[
                erp_modules._ENTRADAS_ESTOQUE_OPERACOES_KEY
            ]
            original_key, original_operation = next(iter(operations.items()))
            original_payload = dict(original_operation["payload"])
            app.run()

            app.checkbox(
                key="entrada_estoque_reconciliacao_confirmado"
            ).check().run()
            app.button(
                key="entrada_estoque_reconciliacao_nao_registrada"
            ).click().run()

            operations = app.session_state[
                erp_modules._ENTRADAS_ESTOQUE_OPERACOES_KEY
            ]
            self.assertEqual(
                operations[original_key]["status"],
                "manually_verified_not_found",
            )
            self.assertEqual(operations[original_key]["payload"], original_payload)
            self.assertEqual(create.call_count, 1)

            app.run()
            app.text_input(key="entrada_estoque_invoice").set_value("NF-124")
            app.text_area(key="entrada_estoque_notes").set_value(
                "Nova entrada após conferência"
            )
            app.form_submit_button(key="entrada_estoque_submit").click().run()
            self.assertEqual(create.call_count, 2)
            operations = app.session_state[
                erp_modules._ENTRADAS_ESTOQUE_OPERACOES_KEY
            ]
            new_key = next(key for key in operations if key != original_key)
            self.assertNotEqual(new_key, original_key)
            self.assertEqual(operations[original_key]["payload"], original_payload)
            self.assertEqual(operations[new_key]["status"], "confirmed")

    def test_duplicate_supplier_names_are_disambiguated_with_returned_fields(self):
        suppliers = [
            {"id": 29, "name": "Fornecedor", "cnpj": "123"},
            {"id": 37, "name": "Fornecedor", "email": "fornecedor@example.test"},
        ]

        self.assertEqual(
            erp_modules._rotulo_opcao_entrada(suppliers[0], suppliers),
            "Fornecedor · 123",
        )
        self.assertEqual(
            erp_modules._rotulo_opcao_entrada(suppliers[1], suppliers),
            "Fornecedor · fornecedor@example.test",
        )

    def test_streamlit_does_not_render_submission_without_active_supplier(self):
        with patch.object(
            erp_modules,
            "_carregar_fornecedores_entrada",
            return_value=([], None),
        ), patch.object(
            erp_modules,
            "listar_produtos",
            return_value=self.products,
        ), patch.object(erp_modules, "criar_entrada_estoque") as create:
            app = AppTest.from_string(
                "import app.erp_modules as erp_modules\n"
                "erp_modules._render_formulario_entrada_estoque()"
            )
            app.session_state["auth_token"] = "mock-session-token"
            app.session_state["auth_user"] = {
                "id": 7,
                "email": "operator@example.test",
                "profile": "Adm",
            }
            app.run()

        self.assertEqual(app.exception, [])
        self.assertTrue(any("Nenhum fornecedor ativo" in item.value for item in app.info))
        self.assertEqual(create.call_count, 0)


if __name__ == "__main__":
    unittest.main()
