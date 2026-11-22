import unittest
from unittest.mock import Mock, patch

import requests
from streamlit.testing.v1 import AppTest

import app.erp_modules as erp_modules
import app.xano_client as xano_client
from tests.ui_test_utils import auto_confirm_operations


class ProductFormSubmissionTests(unittest.TestCase):
    def setUp(self):
        self.categories = [
            {"id": 27, "name": "Casa", "status": "ativo"},
            {"id": 31, "name": "Eletrônicos", "status": "ativo"},
        ]
        self.values = {
            "nome": "Produto de teste",
            "categoria_id": 31,
            "estoque_minimo": 4,
            "preco_venda": 24.9,
            "sku": "SKU-TESTE",
        }

    def test_category_loader_uses_session_token(self):
        with patch.object(
            erp_modules,
            "listar_categorias_ativas",
            return_value=self.categories,
        ) as list_categories:
            categories, error = erp_modules._carregar_categorias_produto(
                "session-token"
            )

        self.assertEqual(categories, self.categories)
        self.assertIsNone(error)
        list_categories.assert_called_once_with(token="session-token")

    def test_category_loader_blocks_missing_token_and_unavailable_categories(self):
        with patch.object(erp_modules, "listar_categorias_ativas") as list_categories:
            categories, error = erp_modules._carregar_categorias_produto(None)

        self.assertEqual(categories, [])
        self.assertIn("sessão", error.lower())
        list_categories.assert_not_called()

        with patch.object(
            erp_modules,
            "listar_categorias_ativas",
            side_effect=ValueError("Nenhuma categoria ativa"),
        ):
            categories, error = erp_modules._carregar_categorias_produto(
                "session-token"
            )

        self.assertEqual(categories, [])
        self.assertTrue(error)

    def test_category_loader_surfaces_http_and_network_failures(self):
        for failure in (
            requests.HTTPError("rejected"),
            requests.ConnectionError("offline"),
        ):
            with self.subTest(failure=type(failure).__name__):
                with patch.object(
                    erp_modules,
                    "listar_categorias_ativas",
                    side_effect=failure,
                ):
                    categories, error = erp_modules._carregar_categorias_produto(
                        "session-token"
                    )

                self.assertEqual(categories, [])
                self.assertTrue(error)

    def test_success_sends_only_supported_fields_and_real_category_id(self):
        with patch.object(erp_modules, "criar_produto", return_value={"id": 42}) as create:
            state, message = erp_modules._enviar_formulario_produto(
                "session-token",
                self.categories,
                **self.values,
            )

        self.assertEqual(state, "success")
        self.assertIn("confirmação", message)
        create.assert_called_once_with(
            token="session-token",
            name="Produto de teste",
            category_id=31,
            min_stock=4,
            sale_price=24.9,
            sku="SKU-TESTE",
        )

    def test_required_field_validation_does_not_call_client(self):
        invalid_values = (
            {**self.values, "nome": " "},
            {**self.values, "categoria_id": 999},
            {**self.values, "estoque_minimo": -1},
            {**self.values, "preco_venda": float("inf")},
        )

        with patch.object(erp_modules, "criar_produto") as create:
            for values in invalid_values:
                with self.subTest(values=values):
                    state, message = erp_modules._enviar_formulario_produto(
                        "session-token",
                        self.categories,
                        **values,
                    )
                    self.assertEqual(state, "validation")
                    self.assertTrue(message)

        create.assert_not_called()

    def test_missing_session_token_does_not_call_client(self):
        with patch.object(erp_modules, "criar_produto") as create:
            state, message = erp_modules._enviar_formulario_produto(
                None,
                self.categories,
                **self.values,
            )

        self.assertEqual(state, "error")
        self.assertIn("sessão", message.lower())
        create.assert_not_called()

    def test_backend_failures_and_inconclusive_response_never_succeed(self):
        cases = (
            (requests.HTTPError("rejected"), "error"),
            (requests.ConnectionError("offline"), "error"),
            (xano_client.RespostaCriacaoInconclusivaError("unconfirmed"), "inconclusive"),
            (ValueError("invalid input"), "validation"),
        )
        for failure, expected_state in cases:
            with self.subTest(failure=type(failure).__name__):
                with patch.object(erp_modules, "criar_produto", side_effect=failure):
                    state, message = erp_modules._enviar_formulario_produto(
                        "session-token",
                        self.categories,
                        **self.values,
                    )

                self.assertEqual(state, expected_state)
                self.assertNotEqual(state, "success")
                self.assertTrue(message)

    def test_http_create_failure_includes_safe_status_and_xano_message(self):
        response = Mock()
        response.status_code = 403
        response.json.return_value = {
            "message": "Role Adm required; token=secret-value user@example.com"
        }
        failure = requests.HTTPError(response=response)

        with self.assertLogs(erp_modules.logger, level="WARNING") as captured:
            with patch.object(erp_modules, "criar_produto", side_effect=failure):
                state, message = erp_modules._enviar_formulario_produto(
                    "session-token",
                    self.categories,
                    **self.values,
                )

        self.assertEqual(state, "error")
        self.assertIn("POST /product", message)
        self.assertIn("HTTP: 403", message)
        self.assertIn("Role Adm required", message)
        self.assertNotIn("secret-value", message)
        self.assertNotIn("user@example.com", message)
        self.assertNotIn("secret-value", captured.output[0])

    def test_inconclusive_success_http_response_shows_safe_status_and_message(self):
        failure = xano_client.RespostaCriacaoInconclusivaError(
            "unconfirmed",
            status_code=200,
            backend_message="Invalid response for token=secret-value user@example.com",
        )

        with self.assertLogs(erp_modules.logger, level="WARNING") as captured:
            with patch.object(erp_modules, "criar_produto", side_effect=failure):
                state, message = erp_modules._enviar_formulario_produto(
                    "session-token",
                    self.categories,
                    **self.values,
                )

        self.assertEqual(state, "inconclusive")
        self.assertIn("Etapa: confirmação da resposta", message)
        self.assertIn("HTTP: 200", message)
        self.assertIn("Invalid response", message)
        self.assertIn("não foi confirmado", message)
        self.assertNotIn("secret-value", message)
        self.assertNotIn("user@example.com", message)
        self.assertNotIn("secret-value", captured.output[0])

    def test_product_search_passes_name_and_keeps_only_confirmed_fields(self):
        response = {
            "products": [
                {
                    "id": 18,
                    "name": "Caneca",
                    "description": "Cerâmica",
                    "category_id": 27,
                    "min_stock": 3,
                    "sale_price": 19.9,
                    "sku": "CAN-18",
                    "status": "ativo",
                    "customer_email": "private@example.com",
                }
            ]
        }
        with patch.object(
            erp_modules,
            "listar_produtos",
            return_value=response,
        ) as list_products:
            status, products, error = erp_modules._consultar_produtos_por_nome(
                "session-token",
                " Caneca ",
            )

        self.assertEqual(status, "success")
        self.assertIsNone(error)
        self.assertEqual(
            products,
            [
                {
                    "id": 18,
                    "name": "Caneca",
                    "description": "Cerâmica",
                    "category_id": 27,
                    "min_stock": 3,
                    "sale_price": 19.9,
                    "sku": "CAN-18",
                    "status": "ativo",
                }
            ],
        )
        list_products.assert_called_once_with(
            token="session-token",
            name="Caneca",
        )

    def test_product_search_passes_only_selected_category_and_nonempty_status(self):
        with patch.object(
            erp_modules,
            "listar_produtos",
            return_value={"products": []},
        ) as list_products:
            status, products, error = erp_modules._consultar_produtos_por_nome(
                "session-token",
                "Caneca",
                category_id=31,
                status=" inativo ",
            )

        self.assertEqual(status, "success")
        self.assertEqual(products, [])
        self.assertIsNone(error)
        list_products.assert_called_once_with(
            token="session-token",
            name="Caneca",
            category_id=31,
            status="inativo",
        )

    def test_product_search_omits_blank_status_and_rejects_invalid_category(self):
        with patch.object(
            erp_modules,
            "listar_produtos",
            return_value=[],
        ) as list_products:
            result = erp_modules._consultar_produtos_por_nome(
                "session-token",
                "Caneca",
                status="  ",
            )
            invalid = erp_modules._consultar_produtos_por_nome(
                "session-token",
                "Caneca",
                category_id=True,
            )

        self.assertEqual(result, ("success", [], None))
        self.assertEqual(invalid[0], "validation")
        self.assertTrue(invalid[2])
        list_products.assert_called_once_with(token="session-token", name="Caneca")

    def test_product_search_accepts_xano_as_self_list_response(self):
        products = [{"name": "Caneca", "sale_price": 19.9}]
        with patch.object(
            erp_modules,
            "listar_produtos",
            return_value=products,
        ) as list_products:
            status, result, error = erp_modules._consultar_produtos_por_nome(
                "session-token",
                "Caneca",
            )

        self.assertEqual(status, "success")
        self.assertEqual(result, products)
        self.assertIsNone(error)
        list_products.assert_called_once_with(token="session-token", name="Caneca")

    def test_empty_product_search_does_not_call_xano(self):
        with patch.object(erp_modules, "listar_produtos") as list_products:
            status, products, error = erp_modules._consultar_produtos_por_nome(
                "session-token",
                "   ",
            )

        self.assertEqual(status, "empty_query")
        self.assertEqual(products, [])
        self.assertIsNone(error)
        list_products.assert_not_called()

    def test_product_search_returns_zero_results_as_success(self):
        with patch.object(
            erp_modules,
            "listar_produtos",
            return_value={"products": []},
        ) as list_products:
            status, products, error = erp_modules._consultar_produtos_por_nome(
                "session-token",
                "Caneca",
            )

        self.assertEqual(status, "success")
        self.assertEqual(products, [])
        self.assertIsNone(error)
        list_products.assert_called_once_with(token="session-token", name="Caneca")

    def test_product_search_preserves_safe_http_error_details(self):
        response = Mock()
        response.status_code = 403
        response.json.return_value = {"message": "Access denied"}
        with patch.object(
            erp_modules,
            "listar_produtos",
            side_effect=requests.HTTPError(response=response),
        ) as list_products:
            status, products, error = erp_modules._consultar_produtos_por_nome(
                "session-token",
                "Caneca",
            )

        self.assertEqual(status, "error")
        self.assertEqual(products, [])
        self.assertIn("GET /product", error)
        self.assertIn("HTTP: 403", error)
        self.assertIn("Access denied", error)
        list_products.assert_called_once_with(token="session-token", name="Caneca")


class ProductFormRenderingTests(unittest.TestCase):
    def setUp(self):
        auto_confirm_operations(self, erp_modules)

    def test_product_screen_empty_search_prompts_without_xano_call(self):
        with patch.object(
            erp_modules,
            "_carregar_categorias_produto",
            return_value=([{"id": 27, "name": "Casa", "status": "ativo"}], None),
        ), patch.object(erp_modules, "listar_produtos") as list_products:
            app = AppTest.from_string(
                "import app.erp_modules as erp_modules\n"
                "erp_modules.render_produtos()"
            )
            app.session_state["auth_token"] = "mock-session-token"
            app.run()
            app.form_submit_button(key="buscar_produtos_submit").click().run()

        self.assertEqual(app.exception, [])
        self.assertTrue(any("Informe um nome" in item.value for item in app.info))
        list_products.assert_not_called()

    def test_product_screen_displays_only_xano_search_fields(self):
        response = {
            "products": [
                {
                    "id": 18,
                    "name": "Caneca",
                    "description": "Cerâmica",
                    "category_id": 27,
                    "min_stock": 3,
                    "sale_price": 19.9,
                    "sku": "CAN-18",
                    "status": "ativo",
                    "customer_email": "private@example.com",
                }
            ]
        }
        with patch.object(
            erp_modules,
            "_carregar_categorias_produto",
            return_value=([{"id": 27, "name": "Casa", "status": "ativo"}], None),
        ), patch.object(
            erp_modules,
            "listar_produtos",
            return_value=response,
        ) as list_products:
            app = AppTest.from_string(
                "import app.erp_modules as erp_modules\n"
                "erp_modules.render_produtos()"
            )
            app.session_state["auth_token"] = "mock-session-token"
            app.run()
            app.text_input(key="busca_produtos_nome").set_value("Caneca")
            app.form_submit_button(key="buscar_produtos_submit").click().run()

        self.assertEqual(app.exception, [])
        self.assertTrue(any("Resultados do Xano" in item.value for item in app.caption))
        self.assertEqual(
            app.session_state["busca_produtos_resultado"]["products"],
            [
                {
                    "id": 18,
                    "name": "Caneca",
                    "description": "Cerâmica",
                    "category_id": 27,
                    "min_stock": 3,
                    "sale_price": 19.9,
                    "sku": "CAN-18",
                    "status": "ativo",
                }
            ],
        )
        self.assertNotIn("private@example.com", str(app.session_state["busca_produtos_resultado"]))
        list_products.assert_called_once_with(token="mock-session-token", name="Caneca")

    def test_product_detail_uses_readable_labels_and_never_renders_raw_object(self):
        product = {
            "id": 18,
            "created_at": "2026-01-02T03:04:05Z",
            "name": "Mouse sem fio USB",
            "sku": "MOU-USB-002",
            "category_id": 27,
            "min_stock": 1,
            "stock_quantity": 52,
            "sale_price": 89.99,
            "average_cost": 9.8,
            "status": "ativo",
            "description": None,
        }
        with patch.object(
            erp_modules,
            "_carregar_categorias_produto",
            return_value=([{"id": 27, "name": "Acessórios"}], None),
        ), patch.object(
            erp_modules,
            "listar_produtos",
            return_value={"products": [product]},
        ), patch.object(
            erp_modules,
            "consultar_produto",
            return_value=product,
        ):
            app = AppTest.from_string(
                "import app.erp_modules as erp_modules\n"
                "erp_modules.render_produtos()"
            )
            app.session_state["auth_token"] = "mock-session-token"
            app.run()
            app.text_input(key="busca_produtos_nome").set_value("Mouse")
            app.form_submit_button(key="buscar_produtos_submit").click().run()
            app.button(key="consultar_detalhe_produto").click().run()

        self.assertEqual(app.exception, [])
        self.assertFalse(app.json)
        self.assertEqual(
            list(app.dataframe[0].value.columns),
            [
                "Produto",
                "SKU",
                "Categoria",
                "Situação",
                "Estoque mínimo",
                "Preço de venda",
            ],
        )
        displayed_metrics = {
            metric.label: metric.value for metric in app.metric
        }
        self.assertEqual(displayed_metrics["SKU"], "MOU-USB-002")
        self.assertEqual(displayed_metrics["Categoria"], "Acessórios")
        self.assertEqual(displayed_metrics["Estoque disponível"], "52 unidades")
        self.assertEqual(displayed_metrics["Estoque mínimo"], "1 unidade")
        self.assertEqual(displayed_metrics["Preço de venda"], "R$ 89,99")
        self.assertEqual(displayed_metrics["Custo médio"], "R$ 9,80")
        self.assertTrue(any("Não informada" in item.value for item in app.markdown))
        self.assertFalse(any("created_at" in item.value for item in app.markdown))

    def test_product_screen_combines_name_category_and_status_filters(self):
        with patch.object(
            erp_modules,
            "_carregar_categorias_produto",
            return_value=(
                [
                    {"id": 27, "name": "Casa", "status": "ativo"},
                    {"id": 31, "name": "Eletrônicos", "status": "ativo"},
                ],
                None,
            ),
        ), patch.object(
            erp_modules,
            "listar_produtos",
            return_value={"products": []},
        ) as list_products:
            app = AppTest.from_string(
                "import app.erp_modules as erp_modules\n"
                "erp_modules.render_produtos()"
            )
            app.session_state["auth_token"] = "mock-session-token"
            app.run()
            app.text_input(key="busca_produtos_nome").set_value("Caneca")
            app.selectbox(key="busca_produtos_categoria").select(
                "Eletrônicos (ID 31)"
            )
            app.text_input(key="busca_produtos_status").set_value("inativo")
            app.form_submit_button(key="buscar_produtos_submit").click().run()

        self.assertEqual(app.exception, [])
        list_products.assert_called_once_with(
            token="mock-session-token",
            name="Caneca",
            category_id=31,
            status="inativo",
        )

    def test_product_screen_shows_zero_result_as_no_products_found(self):
        with patch.object(
            erp_modules,
            "_carregar_categorias_produto",
            return_value=([], None),
        ), patch.object(
            erp_modules,
            "listar_produtos",
            return_value={"products": []},
        ):
            app = AppTest.from_string(
                "import app.erp_modules as erp_modules\n"
                "erp_modules.render_produtos()"
            )
            app.session_state["auth_token"] = "mock-session-token"
            app.run()
            app.text_input(key="busca_produtos_nome").set_value("Sem correspondência")
            app.form_submit_button(key="buscar_produtos_submit").click().run()

        self.assertEqual(app.exception, [])
        self.assertTrue(any("Nenhum produto encontrado" in item.value for item in app.info))
        self.assertEqual(app.error, [])

    def test_product_screen_shows_query_error_not_empty_state(self):
        with patch.object(
            erp_modules,
            "_carregar_categorias_produto",
            return_value=([], None),
        ), patch.object(
            erp_modules,
            "listar_produtos",
            side_effect=requests.ConnectionError("offline"),
        ):
            app = AppTest.from_string(
                "import app.erp_modules as erp_modules\n"
                "erp_modules.render_produtos()"
            )
            app.session_state["auth_token"] = "mock-session-token"
            app.run()
            app.text_input(key="busca_produtos_nome").set_value("Caneca")
            app.form_submit_button(key="buscar_produtos_submit").click().run()

        self.assertEqual(app.exception, [])
        self.assertTrue(any("GET /product" in item.value for item in app.error))
        self.assertFalse(any("Nenhum produto encontrado" in item.value for item in app.info))

    def test_product_detail_edit_and_refresh_use_confirmed_xano_record(self):
        listed = {
            "products": [
                {
                    "id": 18,
                    "name": "Caneca",
                    "category_id": 27,
                    "min_stock": 3,
                    "sale_price": 19.9,
                    "sku": "CAN-18",
                    "status": "ativo",
                }
            ]
        }
        detail = {
            "id": 18,
            "name": "Caneca",
            "description": "Descrição somente leitura",
            "category_id": 27,
            "min_stock": 3,
            "sale_price": 19.9,
            "sku": "CAN-18",
            "status": "ativo",
            "stock_quantity": 20,
            "average_cost": 8.5,
        }
        updated = {**detail, "name": "Caneca Atualizada"}
        with patch.object(
            erp_modules,
            "_carregar_categorias_produto",
            return_value=([{"id": 27, "name": "Casa", "status": "ativo"}], None),
        ), patch.object(
            erp_modules,
            "listar_produtos",
            side_effect=[listed, {"products": [{**listed["products"][0], "name": updated["name"]}]}],
        ) as list_products, patch.object(
            erp_modules,
            "consultar_produto",
            return_value=detail,
        ) as get_product, patch.object(
            erp_modules,
            "editar_produto",
            return_value=updated,
        ) as edit_product:
            app = AppTest.from_string(
                "import app.erp_modules as erp_modules\n"
                "erp_modules.render_produtos()"
            )
            app.session_state["auth_token"] = "mock-session-token"
            app.run()
            app.text_input(key="busca_produtos_nome").set_value("Caneca")
            app.selectbox(key="busca_produtos_categoria").select("Casa (ID 27)")
            app.text_input(key="busca_produtos_status").set_value("ativo")
            app.form_submit_button(key="buscar_produtos_submit").click().run()
            app.button(key="consultar_detalhe_produto").click().run()

            self.assertNotIn(
                "editar_produto_descricao",
                [item.key for item in app.text_area],
            )
            app.text_input(key="editar_produto_nome").set_value("Caneca Atualizada")
            app.form_submit_button(key="salvar_edicao_produto").click().run()

        self.assertEqual(app.exception, [])
        get_product.assert_called_once_with("mock-session-token", 18)
        edit_product.assert_called_once_with(
            "mock-session-token",
            18,
            name="Caneca Atualizada",
        )
        self.assertEqual(list_products.call_count, 2)
        self.assertEqual(
            list_products.call_args_list[-1].kwargs,
            {
                "token": "mock-session-token",
                "name": "Caneca",
                "category_id": 27,
                "status": "ativo",
            },
        )
        self.assertEqual(
            app.session_state["busca_produtos_resultado"]["products"][0]["name"],
            "Caneca Atualizada",
        )
        self.assertEqual(len(app.dataframe), 1)
        self.assertIn(
            "Caneca Atualizada",
            app.dataframe[0].value.to_string(index=False),
        )
        self.assertTrue(
            any("Produto atualizado com confirmação" in item.value for item in app.success)
        )

    def test_product_deactivation_requires_confirmation_and_refreshes_list(self):
        product = {
            "id": 18,
            "name": "Caneca",
            "category_id": 27,
            "min_stock": 3,
            "sale_price": 19.9,
            "sku": "CAN-18",
            "status": "ativo",
        }
        listed = {"products": [product]}
        deactivated = {**product, "status": "inativo"}
        with patch.object(
            erp_modules,
            "_carregar_categorias_produto",
            return_value=([{"id": 27, "name": "Casa", "status": "ativo"}], None),
        ), patch.object(
            erp_modules,
            "listar_produtos",
            side_effect=[listed, {"products": [deactivated]}],
        ), patch.object(
            erp_modules,
            "consultar_produto",
            return_value=product,
        ), patch.object(
            erp_modules,
            "inativar_produto",
            return_value=deactivated,
        ) as deactivate:
            app = AppTest.from_string(
                "import app.erp_modules as erp_modules\n"
                "erp_modules.render_produtos()"
            )
            app.session_state["auth_token"] = "mock-session-token"
            app.run()
            app.text_input(key="busca_produtos_nome").set_value("Caneca")
            app.form_submit_button(key="buscar_produtos_submit").click().run()
            app.button(key="consultar_detalhe_produto").click().run()
            self.assertTrue(app.button(key="inativar_produto").disabled)
            app.checkbox(key="confirmar_inativacao_produto").check().run()
            app.button(key="inativar_produto").click().run()

        self.assertEqual(app.exception, [])
        deactivate.assert_called_once_with("mock-session-token", 18)
        self.assertEqual(
            app.session_state["busca_produtos_resultado"]["products"][0]["status"],
            "inativo",
        )
        self.assertEqual(len(app.dataframe), 1)
        self.assertIn(
            "inativo",
            app.dataframe[0].value.to_string(index=False).lower(),
        )
        self.assertTrue(
            any("Produto inativado com confirmação" in item.value for item in app.success)
        )

    def test_product_edit_errors_never_show_success_or_replace_list(self):
        product = {
            "id": 18,
            "name": "Caneca",
            "category_id": 27,
            "min_stock": 3,
            "sale_price": 19.9,
            "sku": "CAN-18",
            "status": "ativo",
        }
        response = Mock()
        response.status_code = 400
        response.json.return_value = {"message": "SKU duplicado"}
        failures = (
            requests.HTTPError(response=response),
            xano_client.RespostaOperacaoInconclusivaError(
                "Resposta incompleta"
            ),
        )

        for failure in failures:
            with self.subTest(failure=type(failure).__name__):
                with patch.object(
                    erp_modules,
                    "_carregar_categorias_produto",
                    return_value=([{"id": 27, "name": "Casa", "status": "ativo"}], None),
                ), patch.object(
                    erp_modules,
                    "listar_produtos",
                    return_value={"products": [product]},
                ), patch.object(
                    erp_modules,
                    "consultar_produto",
                    return_value=product,
                ), patch.object(
                    erp_modules,
                    "editar_produto",
                    side_effect=failure,
                ):
                    app = AppTest.from_string(
                        "import app.erp_modules as erp_modules\n"
                        "erp_modules.render_produtos()"
                    )
                    app.session_state["auth_token"] = "mock-session-token"
                    app.run()
                    app.text_input(key="busca_produtos_nome").set_value("Caneca")
                    app.form_submit_button(
                        key="buscar_produtos_submit"
                    ).click().run()
                    app.button(key="consultar_detalhe_produto").click().run()
                    app.text_input(key="editar_produto_nome").set_value(
                        "Caneca Atualizada"
                    )
                    app.form_submit_button(
                        key="salvar_edicao_produto"
                    ).click().run()

                self.assertEqual(app.exception, [])
                self.assertEqual(app.success, [])
                self.assertEqual(len(app.dataframe), 1)
                self.assertIn(
                    "Caneca",
                    app.dataframe[0].value.to_string(index=False),
                )
                self.assertNotIn(
                    "Caneca Atualizada",
                    app.dataframe[0].value.to_string(index=False),
                )

    def test_diagnostic_error_includes_stage_status_and_redacted_xano_message(self):
        response = Mock()
        response.status_code = 400
        response.json.return_value = {
            "message": "input:name required for user@example.com token=secret-value"
        }
        error = requests.HTTPError(response=response)

        message = erp_modules._mensagem_erro_xano(error, "GET", "/product")

        self.assertIn("Requisição: GET /product", message)
        self.assertIn("HTTPError", message)
        self.assertIn("HTTP: 400", message)
        self.assertIn("input:name required", message)
        self.assertNotIn("user@example.com", message)
        self.assertNotIn("secret-value", message)

    def test_diagnostic_error_uses_plain_text_response_and_redacts_credentials(self):
        response = Mock()
        response.status_code = 502
        response.json.side_effect = ValueError("not JSON")
        response.headers = {"Content-Type": "text/plain"}
        response.text = "upstream token=private-value user@example.com"

        message = erp_modules._mensagem_erro_xano(
            requests.HTTPError(response=response),
            "GET",
            "/product",
        )

        self.assertIn("Requisição: GET /product", message)
        self.assertIn("HTTP: 502", message)
        self.assertIn("upstream", message)
        self.assertNotIn("private-value", message)
        self.assertNotIn("user@example.com", message)

    def test_diagnostic_network_error_shows_safe_exception_message(self):
        message = erp_modules._mensagem_erro_xano(
            requests.ConnectionError(
                "connection failed for https://example.test?token=private-value"
            ),
            "GET",
            "/product",
        )

        self.assertIn("Requisição: GET /product", message)
        self.assertIn("ConnectionError", message)
        self.assertIn("connection failed", message)
        self.assertNotIn("private-value", message)
        self.assertNotIn("https://example.test", message)

    def test_diagnostic_reports_product_failure_without_showing_records(self):
        response = Mock()
        response.status_code = 400
        response.json.return_value = {"message": "input:name is required"}
        failure = requests.HTTPError(response=response)
        with patch.object(
            erp_modules,
            "listar_categorias_ativas",
            return_value=[{"id": 1, "name": "Casa", "status": "ativo"}],
        ) as list_categories, patch.object(
            erp_modules,
            "listar_produtos",
            side_effect=failure,
        ) as list_products:
            app = AppTest.from_string(
                "import app.erp_modules as erp_modules\n"
                "erp_modules._render_diagnostico_leitura_xano()"
            )
            app.session_state["auth_token"] = "mock-session-token"
            app.run()
            app.button(key="diagnostico_leitura_xano").click().run()

        self.assertEqual(app.exception, [])
        self.assertTrue(any("Requisição: GET /product" in item.value for item in app.error))
        self.assertTrue(any("HTTP: 400" in item.value for item in app.error))
        self.assertTrue(any("Mensagem: input:name is required" in item.value for item in app.error))
        list_categories.assert_called_once_with(token="mock-session-token")
        list_products.assert_called_once_with(
            token="mock-session-token",
            name="codbar-diagnostic-probe",
        )

    def test_diagnostic_reports_zero_products_as_successful_read(self):
        with patch.object(
            erp_modules,
            "listar_categorias_ativas",
            return_value=[{"id": 1, "name": "Casa", "status": "ativo"}],
        ), patch.object(
            erp_modules,
            "listar_produtos",
            return_value={"products": []},
        ) as list_products:
            app = AppTest.from_string(
                "import app.erp_modules as erp_modules\n"
                "erp_modules._render_diagnostico_leitura_xano()"
            )
            app.session_state["auth_token"] = "mock-session-token"
            app.run()
            app.button(key="diagnostico_leitura_xano").click().run()

        self.assertEqual(app.exception, [])
        self.assertTrue(
            any("Produtos: consulta concluída; 0 registro(s)" in item.value for item in app.success)
        )
        self.assertEqual(app.error, [])
        list_products.assert_called_once_with(
            token="mock-session-token",
            name="codbar-diagnostic-probe",
        )

    def test_diagnostic_does_not_report_unrecognized_product_payload_as_success(self):
        private_product_data = {"unexpected": "sensitive product record"}
        with patch.object(
            erp_modules,
            "listar_categorias_ativas",
            return_value=[{"id": 1, "name": "Casa", "status": "ativo"}],
        ), patch.object(
            erp_modules,
            "listar_produtos",
            return_value=private_product_data,
        ):
            app = AppTest.from_string(
                "import app.erp_modules as erp_modules\n"
                "erp_modules._render_diagnostico_leitura_xano()"
            )
            app.session_state["auth_token"] = "mock-session-token"
            app.run()
            app.button(key="diagnostico_leitura_xano").click().run()

        self.assertEqual(app.exception, [])
        self.assertTrue(any("formato não foi reconhecido" in item.value for item in app.warning))
        self.assertFalse(any("sensitive product record" in item.value for item in app.success))

    def test_products_form_renders_only_persisted_fields_when_categories_are_unavailable(self):
        with patch.object(
            erp_modules,
            "_carregar_categorias_produto",
            return_value=([], "Não foi possível carregar categorias ativas."),
        ):
            app = AppTest.from_string(
                "import app.erp_modules as erp_modules\n"
                "erp_modules.render_produtos()"
            )
            app.session_state["auth_token"] = "mock-session-token"
            app.run()

        self.assertEqual(app.exception, [])
        self.assertFalse(any("demonstrativos" in item.value.lower() for item in app.info))
        self.assertTrue(any("categoria" in item.label.lower() for item in app.selectbox))
        labels = {
            item.label.lower()
            for item in list(app.text_input) + list(app.number_input)
        }
        labels.update(item.label.lower() for item in app.text_area)
        self.assertFalse(any("não salvo" in label for label in labels))
        self.assertFalse(any("demonstrativo" in label for label in labels))
        self.assertTrue(any("sku" in label and "opcional" in label for label in labels))
        self.assertTrue(app.form_submit_button(key="salvar_produto_submit").disabled)

    def test_form_submission_sends_description_and_real_category_id(self):
        categories = [{"id": 27, "name": "Casa", "status": "ativo"}]
        with patch.object(
            erp_modules,
            "_carregar_categorias_produto",
            return_value=(categories, None),
        ), patch.object(
            erp_modules,
            "criar_produto",
            return_value={"id": 42},
        ) as create:
            app = AppTest.from_string(
                "import app.erp_modules as erp_modules\n"
                "erp_modules.render_produtos()"
            )
            app.session_state["auth_token"] = "mock-session-token"
            app.run()
            app.text_input(key="produto_nome").set_value("Produto UI")
            app.text_input(key="produto_sku").set_value("SKU-UI")
            app.selectbox(key="produto_categoria").set_value(categories[0])
            app.form_submit_button(key="salvar_produto_submit").click().run()

        self.assertEqual(app.exception, [])
        self.assertTrue(any("confirmação" in item.value.lower() for item in app.success))
        self.assertEqual(app.text_input(key="produto_nome").value, "")
        self.assertIsNone(app.selectbox(key="produto_categoria").value)
        create.assert_called_once_with(
            token="mock-session-token",
            name="Produto UI",
            sku="SKU-UI",
            category_id=27,
            min_stock=5,
            sale_price=249.0,
        )

    def test_form_never_shows_success_for_inconclusive_response(self):
        categories = [{"id": 27, "name": "Casa", "status": "ativo"}]
        with patch.object(
            erp_modules,
            "_carregar_categorias_produto",
            return_value=(categories, None),
        ), patch.object(
            erp_modules,
            "criar_produto",
            side_effect=xano_client.RespostaCriacaoInconclusivaError(
                "unconfirmed"
            ),
        ) as create:
            app = AppTest.from_string(
                "import app.erp_modules as erp_modules\n"
                "erp_modules.render_produtos()"
            )
            app.session_state["auth_token"] = "mock-session-token"
            app.run()
            app.text_input(key="produto_nome").set_value("Produto UI")
            app.selectbox(key="produto_categoria").set_value(categories[0])
            app.form_submit_button(key="salvar_produto_submit").click().run()

        self.assertEqual(app.exception, [])
        self.assertEqual(app.success, [])
        self.assertTrue(any("não foi confirmado" in item.value.lower() for item in app.warning))
        self.assertEqual(app.text_input(key="produto_nome").value, "Produto UI")
        create.assert_called_once()

    def test_form_failure_preserves_values_without_success_message(self):
        categories = [{"id": 27, "name": "Casa", "status": "ativo"}]
        with patch.object(
            erp_modules,
            "_carregar_categorias_produto",
            return_value=(categories, None),
        ), patch.object(
            erp_modules,
            "criar_produto",
            side_effect=requests.ConnectionError("offline"),
        ) as create:
            app = AppTest.from_string(
                "import app.erp_modules as erp_modules\n"
                "erp_modules.render_produtos()"
            )
            app.session_state["auth_token"] = "mock-session-token"
            app.run()
            app.text_input(key="produto_nome").set_value("Produto a retentar")
            app.selectbox(key="produto_categoria").set_value(categories[0])
            app.form_submit_button(key="salvar_produto_submit").click().run()

        self.assertEqual(app.exception, [])
        self.assertEqual(app.success, [])
        self.assertTrue(any("ConnectionError" in item.value for item in app.error))
        self.assertTrue(any("não foi confirmado" not in item.value.lower() for item in app.error))
        self.assertEqual(app.text_input(key="produto_nome").value, "Produto a retentar")
        create.assert_called_once()


if __name__ == "__main__":
    unittest.main()
