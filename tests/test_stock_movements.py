import os
import unittest
from unittest.mock import Mock, patch

import requests
from streamlit.testing.v1 import AppTest

import app.erp_modules as erp_modules
import app.xano_client as xano_client


class StockMovementClientTests(unittest.TestCase):
    def test_lists_movements_without_optional_filters(self):
        response = {"movements": []}
        with patch.object(
            xano_client,
            "xano_request",
            return_value=response,
        ) as request:
            result = xano_client.listar_movimentacoes_estoque(
                token="session-token",
            )

        self.assertIs(result, response)
        request.assert_called_once_with(
            "GET",
            "/stock-movement",
            token="session-token",
            params={},
        )

    def test_passes_supported_filters_without_transforming_timestamps(self):
        response = {
            "movements": [{"backend_field": "value"}],
            "pagination_metadata": {"page": 2},
        }
        with patch.object(
            xano_client,
            "xano_request",
            return_value=response,
        ) as request:
            result = xano_client.listar_movimentacoes_estoque(
                token="session-token",
                product_id=14,
                movement_type="backend-enum-value",
                start_date="backend timestamp start",
                end_date="backend timestamp end",
                page=2,
                per_page=25,
            )

        self.assertIs(result, response)
        request.assert_called_once_with(
            "GET",
            "/stock-movement",
            token="session-token",
            params={
                "product_id": 14,
                "movement_type": "backend-enum-value",
                "start_date": "backend timestamp start",
                "end_date": "backend timestamp end",
                "page": 2,
                "per_page": 25,
            },
        )

    def test_sends_only_the_filters_that_were_provided(self):
        requests_by_filter = (
            ({"product_id": 14}, {"product_id": 14}),
            (
                {"movement_type": "known-enum-value"},
                {"movement_type": "known-enum-value"},
            ),
            (
                {"start_date": "start", "end_date": "end"},
                {"start_date": "start", "end_date": "end"},
            ),
            (
                {"page": 1, "per_page": 20},
                {"page": 1, "per_page": 20},
            ),
        )
        for filters, expected_params in requests_by_filter:
            with self.subTest(filters=filters), patch.object(
                xano_client,
                "xano_request",
                return_value={"movements": []},
            ) as request:
                xano_client.listar_movimentacoes_estoque(
                    token="session-token",
                    **filters,
                )

            self.assertEqual(request.call_args.kwargs["params"], expected_params)

    def test_omits_blank_optional_filters(self):
        with patch.object(
            xano_client,
            "xano_request",
            return_value={"movements": []},
        ) as request:
            xano_client.listar_movimentacoes_estoque(
                token="session-token",
                movement_type=" ",
                start_date="",
                end_date="  ",
            )

        self.assertEqual(request.call_args.kwargs["params"], {})

    def test_rejects_invalid_integer_parameters_without_request(self):
        invalid_filters = (
            {"product_id": 0},
            {"product_id": True},
            {"page": 0},
            {"page": True},
            {"per_page": 0},
            {"per_page": -1},
            {"per_page": 101},
            {"per_page": True},
        )
        with patch.object(xano_client, "xano_request") as request:
            for filters in invalid_filters:
                with self.subTest(filters=filters):
                    with self.assertRaises(ValueError):
                        xano_client.listar_movimentacoes_estoque(
                            token="session-token",
                            **filters,
                        )

        request.assert_not_called()

    def test_accepts_items_and_normalizes_it_for_existing_callers(self):
        response = {
            "items": [{"id": 7}],
            "pagination": {"page": 3},
        }
        with patch.object(
            xano_client,
            "xano_request",
            return_value=response,
        ):
            result = xano_client.listar_movimentacoes_estoque(
                token="session-token",
            )

        self.assertIsNot(result, response)
        self.assertEqual(result["movements"], response["items"])
        self.assertEqual(result["items"], response["items"])
        self.assertEqual(result["pagination"], {"page": 3})

    def test_accepts_per_page_limits(self):
        for per_page in (1, 100):
            with self.subTest(per_page=per_page), patch.object(
                xano_client,
                "xano_request",
                return_value={"movements": []},
            ) as request:
                xano_client.listar_movimentacoes_estoque(
                    token="session-token",
                    per_page=per_page,
                )

            self.assertEqual(
                request.call_args.kwargs["params"],
                {"per_page": per_page},
            )

    def test_requires_movements_list_and_object_records(self):
        invalid_responses = (
            None,
            [],
            {},
            {"movements": None},
            {"movements": [None]},
            {"items": [None]},
        )
        with patch.object(xano_client, "xano_request") as request:
            for response in invalid_responses:
                with self.subTest(response=response):
                    request.return_value = response
                    with self.assertRaisesRegex(ValueError, "GET /stock-movement"):
                        xano_client.listar_movimentacoes_estoque(
                            token="session-token",
                        )

    def test_propagates_http_errors_and_timeouts(self):
        failures = [
            requests.Timeout("request timed out"),
        ]
        for status_code in (401, 403, 500):
            response = requests.Response()
            response.status_code = status_code
            failures.append(requests.HTTPError(response=response))

        for error in failures:
            with self.subTest(error=str(error)):
                with patch.object(
                    xano_client,
                    "xano_request",
                    side_effect=error,
                ):
                    with self.assertRaises(type(error)):
                        xano_client.listar_movimentacoes_estoque(
                            token="session-token",
                        )

    def test_routes_get_to_configured_group_url_with_session_auth(self):
        response = Mock()
        response.content = b'{"movements":[]}'
        response.json.return_value = {"movements": []}
        response.raise_for_status.return_value = None
        environment = {
            "XANO_API_URL": "https://default.example/api:default",
            "XANO_RESOURCES_URL": "https://resources.example/api:resources",
            "XANO_STOCK_MOVEMENTS_URL": "https://movement.example/api:movements",
            "XANO_API_TOKEN": "configured-token",
        }
        with patch.dict(os.environ, environment, clear=True), patch.object(
            xano_client.st,
            "secrets",
            {},
            create=True,
        ), patch(
            "app.xano_client.requests.request",
            return_value=response,
        ) as request:
            xano_client.listar_movimentacoes_estoque(
                token="session-token",
                page=2,
            )

        self.assertEqual(request.call_args.kwargs["method"], "GET")
        self.assertEqual(
            request.call_args.kwargs["url"],
            "https://movement.example/api:movements/stock-movement",
        )
        self.assertEqual(
            request.call_args.kwargs["headers"]["Authorization"],
            "Bearer session-token",
        )
        self.assertEqual(request.call_args.kwargs["params"], {"page": 2})

    def test_requires_configured_group_url_without_request(self):
        environment = {
            "XANO_API_URL": "https://default.example/api:default",
            "XANO_RESOURCES_URL": "https://resources.example/api:resources",
        }
        with patch.dict(os.environ, environment, clear=True), patch.object(
            xano_client.st,
            "secrets",
            {},
            create=True,
        ), patch(
            "app.xano_client.requests.request",
        ) as request:
            with self.assertRaisesRegex(
                ValueError,
                "XANO_STOCK_MOVEMENTS_URL não está configurada",
            ):
                xano_client.listar_movimentacoes_estoque(
                    token="session-token",
                )

        request.assert_not_called()


class StockMovementHistoryTests(unittest.TestCase):
    def _app(self, token="session-token"):
        app = AppTest.from_string(
            "import app.erp_modules as erp_modules\n"
            "erp_modules._render_historico_movimentacoes()"
        )
        app.session_state["auth_token"] = token
        app.run()
        return app

    def test_renders_real_movement_fields_returned_by_xano(self):
        movement = {"backend_field": "real-value"}
        with patch.object(
            erp_modules,
            "listar_movimentacoes_estoque",
            return_value={"movements": [movement]},
        ) as list_movements:
            app = self._app()
            app.button(key="historico_movimentacoes_submit").click().run()

        self.assertEqual(app.exception, [])
        list_movements.assert_called_once_with(
            token="session-token",
            product_id=None,
            start_date=None,
            end_date=None,
            page=1,
            per_page=20,
        )
        self.assertEqual(len(app.dataframe), 1)
        self.assertIn("real-value", str(app.dataframe[0].value))
        self.assertNotIn("Notebook Pro", str(app.dataframe[0].value))

    def test_renders_items_response(self):
        with patch.object(
            erp_modules,
            "listar_movimentacoes_estoque",
            return_value={"items": [{"id": 8, "product_name": "From Xano"}]},
        ):
            app = self._app()
            app.button(key="historico_movimentacoes_submit").click().run()

        self.assertEqual(app.exception, [])
        self.assertEqual(len(app.dataframe), 1)
        self.assertIn("From Xano", str(app.dataframe[0].value))
        self.assertTrue(
            any("Página 1 · 1 movimentação(ões)" in item.value for item in app.caption)
        )

    def test_next_page_preserves_filters_and_does_not_infer_end_from_count(self):
        movements = [{"id": item} for item in range(100)]
        with patch.object(
            erp_modules,
            "listar_movimentacoes_estoque",
            side_effect=[
                {"movements": movements},
                {"items": [{"id": 101}]},
            ],
        ) as list_movements:
            app = self._app()
            app.number_input(
                key="historico_movimentacoes_product_id"
            ).set_value(14)
            app.text_input(
                key="historico_movimentacoes_start_date"
            ).set_value("start timestamp")
            app.text_input(
                key="historico_movimentacoes_end_date"
            ).set_value("end timestamp")
            app.button(key="historico_movimentacoes_submit").click().run()

            next_button = app.button(key="historico_movimentacoes_next")
            self.assertFalse(next_button.disabled)
            next_button.click().run()

        self.assertEqual(app.exception, [])
        self.assertEqual(
            list_movements.call_args_list[0].kwargs,
            {
                "token": "session-token",
                "product_id": 14,
                "start_date": "start timestamp",
                "end_date": "end timestamp",
                "page": 1,
                "per_page": 20,
            },
        )
        self.assertEqual(
            list_movements.call_args_list[1].kwargs,
            {
                "token": "session-token",
                "product_id": 14,
                "start_date": "start timestamp",
                "end_date": "end timestamp",
                "page": 2,
                "per_page": 20,
            },
        )
        self.assertTrue(
            any("Página 2 · 1 movimentação(ões)" in item.value for item in app.caption)
        )
        self.assertEqual(len(app.dataframe), 1)
        self.assertIn("101", str(app.dataframe[0].value))

    def test_empty_page_still_allows_next_and_reports_page_count(self):
        with patch.object(
            erp_modules,
            "listar_movimentacoes_estoque",
            return_value={"movements": []},
        ):
            app = self._app()
            app.number_input(key="historico_movimentacoes_page").set_value(4)
            app.button(key="historico_movimentacoes_submit").click().run()

        self.assertEqual(app.exception, [])
        self.assertTrue(
            any("Página 4 · 0 movimentação(ões)" in item.value for item in app.caption)
        )
        self.assertFalse(app.button(key="historico_movimentacoes_next").disabled)

    def test_changing_filters_resets_page_to_one(self):
        with patch.object(
            erp_modules,
            "listar_movimentacoes_estoque",
            return_value={"movements": [{"id": 1}]},
        ) as list_movements:
            app = self._app()
            app.button(key="historico_movimentacoes_submit").click().run()
            app.button(key="historico_movimentacoes_next").click().run()
            self.assertEqual(list_movements.call_args.kwargs["page"], 2)

            app.number_input(
                key="historico_movimentacoes_product_id"
            ).set_value(31)
            app.button(key="historico_movimentacoes_submit").click().run()

        self.assertEqual(app.exception, [])
        self.assertEqual(list_movements.call_args.kwargs["product_id"], 31)
        self.assertEqual(list_movements.call_args.kwargs["page"], 1)
        self.assertTrue(
            any("Página 1 · 1 movimentação(ões)" in item.value for item in app.caption)
        )

    def test_reports_empty_history(self):
        with patch.object(
            erp_modules,
            "listar_movimentacoes_estoque",
            return_value={"movements": []},
        ):
            app = self._app()
            app.button(key="historico_movimentacoes_submit").click().run()

        self.assertEqual(app.exception, [])
        self.assertTrue(
            any(
                "Não existem movimentações" in element.value
                for element in app.info
            )
        )
        self.assertEqual(len(app.dataframe), 0)

    def test_reports_api_error_without_showing_fake_history(self):
        response = requests.Response()
        response.status_code = 403
        failure = requests.HTTPError(response=response)
        with patch.object(
            erp_modules,
            "listar_movimentacoes_estoque",
            side_effect=failure,
        ):
            app = self._app()
            app.button(key="historico_movimentacoes_submit").click().run()

        self.assertEqual(app.exception, [])
        self.assertTrue(
            any("não tem permissão" in element.value for element in app.error)
        )
        self.assertEqual(len(app.dataframe), 0)

    def test_reports_http_400_backend_message(self):
        response = requests.Response()
        response.status_code = 400
        response.headers["Content-Type"] = "application/json"
        response._content = (
            b'{"message":"Missing param: movement_type; '
            b'echoed session-token"}'
        )
        failure = requests.HTTPError(response=response)
        with patch.object(
            erp_modules,
            "listar_movimentacoes_estoque",
            side_effect=failure,
        ):
            app = self._app()
            app.button(key="historico_movimentacoes_submit").click().run()

        self.assertEqual(app.exception, [])
        self.assertTrue(
            any(
                "Missing param: movement_type" in item.value
                for item in app.error
            )
        )
        self.assertNotIn(
            "session-token",
            " ".join(item.value for item in app.error),
        )

    def test_handles_expired_session_without_creating_login_flow(self):
        response = requests.Response()
        response.status_code = 401
        failure = requests.HTTPError(response=response)
        with patch.object(
            erp_modules,
            "listar_movimentacoes_estoque",
            side_effect=failure,
        ):
            app = self._app()
            app.button(key="historico_movimentacoes_submit").click().run()

        self.assertEqual(app.exception, [])
        self.assertTrue(
            any("sessão expirou" in element.value for element in app.error)
        )
        self.assertEqual(len(app.dataframe), 0)

    def test_missing_session_token_does_not_call_xano(self):
        with patch.object(
            erp_modules,
            "listar_movimentacoes_estoque",
        ) as list_movements:
            app = self._app(token=None)
            self.assertTrue(
                any("sessão expirou" in element.value for element in app.warning)
            )
            self.assertTrue(
                app.button(key="historico_movimentacoes_submit").disabled
            )

        list_movements.assert_not_called()

    def test_submits_product_period_and_pagination_filters(self):
        with patch.object(
            erp_modules,
            "listar_movimentacoes_estoque",
            return_value={"movements": []},
        ) as list_movements:
            app = self._app()
            app.number_input(
                key="historico_movimentacoes_product_id"
            ).set_value(14)
            app.text_input(
                key="historico_movimentacoes_start_date"
            ).set_value("start timestamp")
            app.text_input(
                key="historico_movimentacoes_end_date"
            ).set_value("end timestamp")
            app.number_input(
                key="historico_movimentacoes_page"
            ).set_value(3)
            app.number_input(
                key="historico_movimentacoes_per_page"
            ).set_value(25)
            app.button(key="historico_movimentacoes_submit").click().run()

        list_movements.assert_called_once_with(
            token="session-token",
            product_id=14,
            start_date="start timestamp",
            end_date="end timestamp",
            page=3,
            per_page=25,
        )
        self.assertEqual(app.exception, [])

    def test_filter_change_resets_page_before_query(self):
        with patch.object(
            erp_modules,
            "listar_movimentacoes_estoque",
            return_value={"movements": []},
        ) as list_movements:
            app = self._app()
            app.number_input(
                key="historico_movimentacoes_product_id"
            ).set_value(14)
            app.number_input(
                key="historico_movimentacoes_page"
            ).set_value(3)
            app.button(key="historico_movimentacoes_submit").click().run()

            app.number_input(
                key="historico_movimentacoes_product_id"
            ).set_value(15)
            app.button(key="historico_movimentacoes_submit").click().run()

        self.assertEqual(list_movements.call_count, 2)
        self.assertEqual(
            list_movements.call_args.kwargs["product_id"],
            15,
        )
        self.assertEqual(list_movements.call_args.kwargs["page"], 1)


class StockMovementDiagnosticTests(unittest.TestCase):
    def _app(self, token="session-token"):
        app = AppTest.from_string(
            "import app.erp_modules as erp_modules\n"
            "erp_modules._render_diagnostico_integracao_movimentacoes()"
        )
        app.session_state["auth_token"] = token
        app.run()
        return app

    def _click_diagnostic(self, app):
        app.button(key="diagnostico_movimentacoes_submit").click().run()
        self.assertEqual(app.exception, [])

    def _rendered_text(self, app):
        return " ".join(
            str(element.value)
            for name in (
                "markdown",
                "caption",
                "success",
                "error",
                "warning",
                "info",
            )
            for element in getattr(app, name, [])
        )

    def test_missing_session_token_does_not_query_xano(self):
        with patch.object(
            erp_modules,
            "get_xano_config",
            return_value={"stock_movements_base_url": "https://xano.example"},
        ), patch.object(
            erp_modules,
            "listar_movimentacoes_estoque",
        ) as list_movements:
            app = self._app(token=None)
            self._click_diagnostic(app)

        list_movements.assert_not_called()
        self.assertFalse(
            app.session_state["diagnostico_movimentacoes_resultado"][
                "query_executed"
            ]
        )

    def test_missing_movement_url_does_not_query_xano(self):
        with patch.object(
            erp_modules,
            "get_xano_config",
            return_value={"stock_movements_base_url": None},
        ), patch.object(
            erp_modules,
            "listar_movimentacoes_estoque",
        ) as list_movements:
            app = self._app()
            self._click_diagnostic(app)

        list_movements.assert_not_called()
        self.assertFalse(
            app.session_state["diagnostico_movimentacoes_resultado"][
                "config_found"
            ]
        )

    def test_success_reports_count_and_only_non_sensitive_field_names(self):
        response = {
            "movements": [
                {
                    "id": 12,
                    "product_id": 8,
                    "customer_email": "private@example.com",
                    "token": "do-not-display",
                }
            ]
        }
        with patch.object(
            erp_modules,
            "get_xano_config",
            return_value={"stock_movements_base_url": "https://xano.example"},
        ), patch.object(
            erp_modules,
            "listar_movimentacoes_estoque",
            return_value=response,
        ) as list_movements:
            app = self._app()
            list_movements.assert_not_called()
            self._click_diagnostic(app)

        list_movements.assert_called_once_with(
            token="session-token",
            page=1,
            per_page=20,
        )
        output = self._rendered_text(app)
        self.assertIn("1 movimentação(ões)", output)
        self.assertIn("id, product_id", output)
        self.assertNotIn("private@example.com", output)
        self.assertNotIn("do-not-display", output)
        self.assertNotIn("customer_email", output)

    def test_empty_response_reports_zero_movements(self):
        with patch.object(
            erp_modules,
            "get_xano_config",
            return_value={"stock_movements_base_url": "https://xano.example"},
        ), patch.object(
            erp_modules,
            "listar_movimentacoes_estoque",
            return_value={"movements": []},
        ):
            app = self._app()
            self._click_diagnostic(app)

        output = self._rendered_text(app)
        self.assertIn("0 movimentação(ões)", output)
        self.assertIn("Campos não sensíveis: nenhum", output)

    def test_http_400_preserves_sanitized_backend_message(self):
        response = Mock()
        response.status_code = 400
        response.json.return_value = {
            "message": (
                "Missing param: movement_type; "
                "Authorization: Bearer session-secret-token; echoed session-token"
            )
        }
        failure = requests.HTTPError(response=response)
        with patch.object(
            erp_modules,
            "get_xano_config",
            return_value={"stock_movements_base_url": "https://xano.example"},
        ), patch.object(
            erp_modules,
            "listar_movimentacoes_estoque",
            side_effect=failure,
        ):
            app = self._app()
            self._click_diagnostic(app)

        output = self._rendered_text(app)
        self.assertIn("400", output)
        self.assertIn("Missing param: movement_type", output)
        self.assertNotIn("session-secret-token", output)
        self.assertNotIn("session-token", output)
        self.assertNotIn("Authorization", output)

    def test_http_error_classifies_authentication_and_permission(self):
        for status_code, expected in (
            (401, "Autenticação recusada"),
            (403, "Permissão insuficiente"),
        ):
            with self.subTest(status_code=status_code):
                response = Mock()
                response.status_code = status_code
                response.json.return_value = {"message": "Request denied"}
                failure = requests.HTTPError(response=response)
                with patch.object(
                    erp_modules,
                    "get_xano_config",
                    return_value={
                        "stock_movements_base_url": "https://xano.example"
                    },
                ), patch.object(
                    erp_modules,
                    "listar_movimentacoes_estoque",
                    side_effect=failure,
                ):
                    app = self._app()
                    self._click_diagnostic(app)

                output = self._rendered_text(app)
                self.assertIn(str(status_code), output)
                self.assertIn(expected, output)
                self.assertIn("Request denied", output)

    def test_http_error_uses_limited_sanitized_text_when_json_is_invalid(self):
        response = Mock()
        response.status_code = 400
        response.json.side_effect = ValueError("invalid json")
        response.text = (
            "<html>Missing param: product_id "
            "Authorization: Bearer hidden-session-token</html>"
        )
        response.headers = {"Content-Type": "text/html"}
        failure = requests.HTTPError(response=response)
        with patch.object(
            erp_modules,
            "get_xano_config",
            return_value={"stock_movements_base_url": "https://xano.example"},
        ), patch.object(
            erp_modules,
            "listar_movimentacoes_estoque",
            side_effect=failure,
        ):
            app = self._app()
            self._click_diagnostic(app)

        output = self._rendered_text(app)
        self.assertIn("Missing param: product_id", output)
        self.assertNotIn("hidden-session-token", output)
        self.assertNotIn("<html>", output)

    def test_http_error_reports_status_without_backend_details(self):
        response = requests.Response()
        response.status_code = 403
        failure = requests.HTTPError(
            "Authorization: Bearer should-not-display",
            response=response,
        )
        with patch.object(
            erp_modules,
            "get_xano_config",
            return_value={"stock_movements_base_url": "https://xano.example"},
        ), patch.object(
            erp_modules,
            "listar_movimentacoes_estoque",
            side_effect=failure,
        ):
            app = self._app()
            self._click_diagnostic(app)

        output = self._rendered_text(app)
        self.assertIn("403", output)
        self.assertIn("Permissão insuficiente", output)
        self.assertNotIn("should-not-display", output)

    def test_connection_error_message_is_not_exposed(self):
        failure = requests.ConnectionError("token=should-not-display")
        with patch.object(
            erp_modules,
            "get_xano_config",
            return_value={"stock_movements_base_url": "https://xano.example"},
        ), patch.object(
            erp_modules,
            "listar_movimentacoes_estoque",
            side_effect=failure,
        ):
            app = self._app()
            self._click_diagnostic(app)

        output = self._rendered_text(app)
        self.assertIn("Falha de conexão", output)
        self.assertNotIn("should-not-display", output)


if __name__ == "__main__":
    unittest.main()
