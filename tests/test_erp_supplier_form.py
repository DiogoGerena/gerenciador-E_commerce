import unittest
from unittest.mock import patch

import requests
from streamlit.testing.v1 import AppTest

import app.erp_modules as erp_modules
from tests.ui_test_utils import auto_confirm_operations


class SupplierQueryTests(unittest.TestCase):
    def test_supplier_query_defaults_empty_status_to_active(self):
        with patch.object(
            erp_modules,
            "listar_fornecedores",
            return_value=[],
        ) as list_suppliers:
            result = erp_modules._consultar_fornecedores(
                "session-token",
                name="  ",
                status="",
            )

        self.assertEqual(result, ("success", [], None))
        list_suppliers.assert_called_once_with(
            token="session-token",
            status="ativo",
        )

    def test_supplier_query_sends_only_supported_filters(self):
        suppliers = [{"id": 29, "name": "Fornecedor Real"}]
        with patch.object(
            erp_modules,
            "listar_fornecedores",
            return_value=suppliers,
        ) as list_suppliers:
            result = erp_modules._consultar_fornecedores(
                "session-token",
                name=" Fornecedor ",
                status=" ativo ",
            )

        self.assertEqual(result, ("success", suppliers, None))
        list_suppliers.assert_called_once_with(
            token="session-token",
            name="Fornecedor",
            status="ativo",
        )

    def test_supplier_query_reports_http_and_connection_errors(self):
        http_response = type(
            "Response",
            (),
            {"status_code": 403, "json": lambda self: {"message": "Access denied"}},
        )()
        failures = (
            requests.HTTPError(response=http_response),
            requests.ConnectionError("offline"),
        )

        for failure in failures:
            with self.subTest(failure=type(failure).__name__):
                with patch.object(
                    erp_modules,
                    "listar_fornecedores",
                    side_effect=failure,
                ) as list_suppliers:
                    state, suppliers, message = erp_modules._consultar_fornecedores(
                        "session-token"
                    )

                self.assertEqual(state, "error")
                self.assertEqual(suppliers, [])
                self.assertIn("GET /supplier", message)
                list_suppliers.assert_called_once_with(
                    token="session-token",
                    status="ativo",
                )


class SupplierScreenTests(unittest.TestCase):
    def setUp(self):
        auto_confirm_operations(self, erp_modules)

    def test_supplier_screen_uses_xano_data_and_supported_filters(self):
        suppliers = [
            {
                "id": 29,
                "name": "Fornecedor Real",
                "cnpj": "04252011000110",
                "contact_name": "Contato",
                "email": "contato@example.test",
                "phone": "11999990000",
                "status": "ativo",
            }
        ]
        with patch.object(
            erp_modules,
            "listar_fornecedores",
            return_value=suppliers,
        ) as list_suppliers:
            app = AppTest.from_string(
                "import app.erp_modules as erp_modules\n"
                "erp_modules.render_fornecedores()"
            )
            app.session_state["auth_token"] = "mock-session-token"
            app.run()
            self.assertEqual(len(app.dataframe), 1)
            self.assertEqual(
                app.text_input(key="busca_fornecedores_status").value,
                "ativo",
            )
            self.assertEqual(
                list_suppliers.call_args_list[0].kwargs,
                {
                    "token": "mock-session-token",
                    "status": "ativo",
                },
            )

            app.text_input(key="busca_fornecedores_nome").set_value("Fornecedor")
            app.form_submit_button(
                key="consultar_fornecedores_submit"
            ).click().run()

        self.assertEqual(app.exception, [])
        self.assertEqual(
            list_suppliers.call_args_list[1].kwargs,
            {
                "token": "mock-session-token",
                "name": "Fornecedor",
                "status": "ativo",
            },
        )
        self.assertEqual(len(app.dataframe), 1)
        displayed = app.dataframe[0].value.to_string(index=False)
        for value in ("Fornecedor Real", "Contato", "contato@example.test", "11999990000"):
            self.assertIn(value, displayed)
        self.assertNotIn("Alpha Supply", displayed)
        self.assertTrue(
            any("Cadastrar fornecedor" in item.label for item in app.form_submit_button)
        )

    def test_supplier_create_requires_valid_cnpj_and_confirms_backend_response(self):
        created = {"id": 29, "name": "Fornecedor Real", "status": "ativo"}
        with patch.object(
            erp_modules,
            "criar_fornecedor",
            return_value=created,
        ) as create_supplier, patch.object(
            erp_modules,
            "listar_fornecedores",
            return_value=[created],
        ) as list_suppliers:
            app = AppTest.from_string(
                "import app.erp_modules as erp_modules\n"
                "erp_modules.render_fornecedores()"
            )
            app.session_state["auth_token"] = "mock-session-token"
            app.run()
            app.text_input(key="novo_fornecedor_nome").set_value("Fornecedor Real")
            app.text_input(key="novo_fornecedor_cnpj").set_value(
                "04.252.011/0001-10"
            )
            app.form_submit_button(
                key="cadastrar_fornecedor_submit"
            ).click().run()

        self.assertEqual(app.exception, [])
        create_supplier.assert_called_once_with(
            "mock-session-token",
            name="Fornecedor Real",
            contact_name="",
            cnpj="04.252.011/0001-10",
            email="",
            phone="",
        )
        self.assertTrue(
            any("cadastrado com confirmação" in item.value for item in app.success)
        )
        self.assertEqual(list_suppliers.call_count, 2)
        self.assertEqual(
            [call.kwargs for call in list_suppliers.call_args_list],
            [
                {"token": "mock-session-token", "status": "ativo"},
                {"token": "mock-session-token", "status": "ativo"},
            ],
        )
        self.assertEqual(len(app.dataframe), 1)
        self.assertIn(
            "Fornecedor Real",
            app.dataframe[0].value.to_string(index=False),
        )

    def test_supplier_create_rejects_invalid_cnpj_without_client_call(self):
        with patch.object(erp_modules, "criar_fornecedor") as create_supplier:
            app = AppTest.from_string(
                "import app.erp_modules as erp_modules\n"
                "erp_modules.render_fornecedores()"
            )
            app.session_state["auth_token"] = "mock-session-token"
            app.run()
            app.text_input(key="novo_fornecedor_nome").set_value("Fornecedor Real")
            app.text_input(key="novo_fornecedor_cnpj").set_value(
                "00.000.000/0000-00"
            )
            app.form_submit_button(
                key="cadastrar_fornecedor_submit"
            ).click().run()

        self.assertEqual(app.exception, [])
        self.assertTrue(any("CNPJ válido" in item.value for item in app.error))
        create_supplier.assert_not_called()

    def test_supplier_duplicate_cnpj_error_never_shows_success(self):
        response = type(
            "Response",
            (),
            {
                "status_code": 400,
                "json": lambda self: {
                    "message": "Já existe um fornecedor cadastrado com este CNPJ."
                },
            },
        )()
        with patch.object(
            erp_modules,
            "criar_fornecedor",
            side_effect=requests.HTTPError(response=response),
        ):
            app = AppTest.from_string(
                "import app.erp_modules as erp_modules\n"
                "erp_modules.render_fornecedores()"
            )
            app.session_state["auth_token"] = "mock-session-token"
            app.run()
            app.text_input(key="novo_fornecedor_nome").set_value("Fornecedor Real")
            app.text_input(key="novo_fornecedor_cnpj").set_value(
                "04.252.011/0001-10"
            )
            app.form_submit_button(
                key="cadastrar_fornecedor_submit"
            ).click().run()

        self.assertEqual(app.exception, [])
        self.assertEqual(app.success, [])
        self.assertTrue(
            any("Já existe um fornecedor cadastrado" in item.value for item in app.error)
        )

    def test_supplier_detail_and_edit_use_backend_confirmation(self):
        listed = [{"id": 29, "name": "Fornecedor", "status": "ativo"}]
        detail = {
            "id": 29,
            "name": "Fornecedor",
            "contact_name": "Contato",
            "cnpj": "04252011000110",
            "email": "supplier@example.test",
            "phone": "11999990000",
            "status": "ativo",
        }
        updated = {**detail, "name": "Fornecedor Atualizado"}
        with patch.object(
            erp_modules,
            "listar_fornecedores",
            side_effect=[
                listed,
                listed,
                [updated],
            ],
        ) as list_suppliers, patch.object(
            erp_modules,
            "consultar_fornecedor",
            return_value=detail,
        ) as get_supplier, patch.object(
            erp_modules,
            "editar_fornecedor",
            return_value=updated,
        ) as edit_supplier:
            app = AppTest.from_string(
                "import app.erp_modules as erp_modules\n"
                "erp_modules.render_fornecedores()"
            )
            app.session_state["auth_token"] = "mock-session-token"
            app.run()
            app.text_input(key="busca_fornecedores_nome").set_value("Fornecedor")
            app.text_input(key="busca_fornecedores_status").set_value("ativo")
            app.form_submit_button(
                key="consultar_fornecedores_submit"
            ).click().run()
            app.button(key="consultar_detalhe_fornecedor").click().run()
            app.text_input(key="editar_fornecedor_nome").set_value(
                "Fornecedor Atualizado"
            )
            app.form_submit_button(
                key="salvar_edicao_fornecedor"
            ).click().run()

        self.assertEqual(app.exception, [])
        get_supplier.assert_called_once_with("mock-session-token", 29)
        edit_supplier.assert_called_once_with(
            "mock-session-token",
            29,
            name="Fornecedor Atualizado",
        )
        self.assertEqual(list_suppliers.call_count, 3)
        self.assertEqual(
            list_suppliers.call_args_list[-1].kwargs,
            {
                "token": "mock-session-token",
                "name": "Fornecedor",
                "status": "ativo",
            },
        )
        self.assertTrue(
            any("Fornecedor atualizado com confirmação" in item.value for item in app.success)
        )
        self.assertFalse(app.json)
        supplier_metrics = {metric.label: metric.value for metric in app.metric}
        self.assertEqual(supplier_metrics["Contato"], "Contato")
        self.assertEqual(supplier_metrics["CNPJ"], "04252011000110")
        self.assertEqual(supplier_metrics["E-mail"], "supplier@example.test")
        self.assertEqual(supplier_metrics["Telefone"], "11999990000")
        self.assertEqual(len(app.dataframe), 1)
        self.assertIn(
            "Fornecedor Atualizado",
            app.dataframe[0].value.to_string(index=False),
        )
        self.assertNotIn("mensagem_sucesso_fornecedores", app.session_state)

    def test_supplier_deactivation_requires_confirmation_and_refreshes_list(self):
        supplier = {"id": 29, "name": "Fornecedor", "status": "ativo"}
        deactivated = {**supplier, "status": "inativo"}
        with patch.object(
            erp_modules,
            "listar_fornecedores",
            side_effect=[[supplier], [supplier], [deactivated]],
        ), patch.object(
            erp_modules,
            "consultar_fornecedor",
            return_value=supplier,
        ), patch.object(
            erp_modules,
            "inativar_fornecedor",
            return_value=deactivated,
        ) as deactivate:
            app = AppTest.from_string(
                "import app.erp_modules as erp_modules\n"
                "erp_modules.render_fornecedores()"
            )
            app.session_state["auth_token"] = "mock-session-token"
            app.run()
            app.form_submit_button(
                key="consultar_fornecedores_submit"
            ).click().run()
            app.button(key="consultar_detalhe_fornecedor").click().run()
            self.assertTrue(app.button(key="inativar_fornecedor").disabled)
            app.checkbox(key="confirmar_inativacao_fornecedor").check().run()
            app.button(key="inativar_fornecedor").click().run()

        self.assertEqual(app.exception, [])
        deactivate.assert_called_once_with("mock-session-token", 29)
        self.assertTrue(
            any("Fornecedor inativado com confirmação" in item.value for item in app.success)
        )
        self.assertEqual(len(app.dataframe), 1)
        self.assertIn(
            "inativo",
            app.dataframe[0].value.to_string(index=False),
        )
        self.assertNotIn("mensagem_sucesso_fornecedores", app.session_state)

    def test_supplier_edit_errors_never_show_success_or_replace_list(self):
        supplier = {
            "id": 29,
            "name": "Fornecedor",
            "contact_name": "Contato",
            "cnpj": "04252011000110",
            "email": "supplier@example.test",
            "phone": "11999990000",
            "status": "ativo",
        }
        response = type(
            "Response",
            (),
            {
                "status_code": 400,
                "json": lambda self: {
                    "message": "Já existe um fornecedor cadastrado com este CNPJ."
                },
            },
        )()
        failures = (
            requests.HTTPError(response=response),
            erp_modules.RespostaOperacaoInconclusivaError(
                "Resposta incompleta"
            ),
        )

        for failure in failures:
            with self.subTest(failure=type(failure).__name__):
                with patch.object(
                    erp_modules,
                    "listar_fornecedores",
                    return_value=[supplier],
                ), patch.object(
                    erp_modules,
                    "consultar_fornecedor",
                    return_value=supplier,
                ), patch.object(
                    erp_modules,
                    "editar_fornecedor",
                    side_effect=failure,
                ):
                    app = AppTest.from_string(
                        "import app.erp_modules as erp_modules\n"
                        "erp_modules.render_fornecedores()"
                    )
                    app.session_state["auth_token"] = "mock-session-token"
                    app.run()
                    app.text_input(key="busca_fornecedores_nome").set_value(
                        "Fornecedor"
                    )
                    app.text_input(key="busca_fornecedores_status").set_value(
                        "ativo"
                    )
                    app.form_submit_button(
                        key="consultar_fornecedores_submit"
                    ).click().run()
                    app.button(key="consultar_detalhe_fornecedor").click().run()
                    app.text_input(key="editar_fornecedor_nome").set_value(
                        "Fornecedor Atualizado"
                    )
                    app.form_submit_button(
                        key="salvar_edicao_fornecedor"
                    ).click().run()

                self.assertEqual(app.exception, [])
                self.assertEqual(app.success, [])
                self.assertEqual(len(app.dataframe), 1)
                self.assertIn(
                    "Fornecedor",
                    app.dataframe[0].value.to_string(index=False),
                )
                self.assertNotIn(
                    "Fornecedor Atualizado",
                    app.dataframe[0].value.to_string(index=False),
                )
                self.assertNotIn(
                    "mensagem_sucesso_fornecedores",
                    app.session_state,
                )

    def test_supplier_screen_shows_empty_and_error_states(self):
        with patch.object(
            erp_modules,
            "listar_fornecedores",
            return_value=[],
        ):
            empty_app = AppTest.from_string(
                "import app.erp_modules as erp_modules\n"
                "erp_modules.render_fornecedores()"
            )
            empty_app.session_state["auth_token"] = "mock-session-token"
            empty_app.run()
            empty_app.form_submit_button(
                key="consultar_fornecedores_submit"
            ).click().run()

        self.assertEqual(empty_app.exception, [])
        self.assertTrue(
            any("Nenhum fornecedor encontrado" in item.value for item in empty_app.info)
        )
        self.assertEqual(len(empty_app.dataframe), 0)

        with patch.object(
            erp_modules,
            "listar_fornecedores",
            side_effect=requests.ConnectionError("offline"),
        ):
            error_app = AppTest.from_string(
                "import app.erp_modules as erp_modules\n"
                "erp_modules.render_fornecedores()"
            )
            error_app.session_state["auth_token"] = "mock-session-token"
            error_app.run()
            error_app.form_submit_button(
                key="consultar_fornecedores_submit"
            ).click().run()

        self.assertEqual(error_app.exception, [])
        self.assertTrue(
            any("GET /supplier" in item.value for item in error_app.error)
        )
        self.assertEqual(len(error_app.dataframe), 0)


class CnpjValidationTests(unittest.TestCase):
    def test_validates_cnpj_digits_and_common_formatting(self):
        self.assertTrue(erp_modules.validar_cnpj("04252011000110"))
        self.assertTrue(erp_modules.validar_cnpj("04.252.011/0001-10"))

    def test_rejects_invalid_or_repeated_cnpj_digits(self):
        for value in ("", "00.000.000/0000-00", "04.252.011/0001-11", "abc"):
            with self.subTest(value=value):
                self.assertFalse(erp_modules.validar_cnpj(value))


if __name__ == "__main__":
    unittest.main()
