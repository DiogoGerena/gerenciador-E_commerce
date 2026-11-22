import os
import unittest
from unittest.mock import Mock, patch

import requests

import app.xano_client as xano_client


def user_record(**overrides):
    record = {
        "id": 17,
        "name": "Pessoa Usuária",
        "email": "pessoa@example.test",
        "role": "aux.ecommerce",
        "created_at": "2026-11-21T12:00:00Z",
    }
    record.update(overrides)
    return record


class XanoUsersClientTests(unittest.TestCase):
    def setUp(self):
        self._env_patch = patch.dict(
            os.environ,
            {
                "XANO_API_URL": "https://api.example.test/api:main",
                "XANO_AUTH_URL": "https://auth.example.test/api:ZQDs0IzN",
            },
            clear=True,
        )
        self._env_patch.start()
        self._secrets_patch = patch.object(
            xano_client.st,
            "secrets",
            {},
            create=True,
        )
        self._secrets_patch.start()

    def tearDown(self):
        self._secrets_patch.stop()
        self._env_patch.stop()

    @staticmethod
    def _response(payload, *, content=b"json"):
        response = Mock()
        response.status_code = 200
        response.content = content
        response.json.return_value = payload
        response.headers = {"Content-Type": "application/json"}
        response.text = ""
        response.raise_for_status.return_value = None
        return response

    def test_list_uses_auth_group_and_bearer_token_without_parameters(self):
        with patch(
            "app.xano_client.requests.request",
            return_value=self._response([user_record(password="must-not-return")]),
        ) as request:
            result = xano_client.listar_usuarios("admin-session")

        self.assertEqual(result, [user_record()])
        self.assertNotIn("password", result[0])
        call = request.call_args.kwargs
        self.assertEqual(call["method"], "GET")
        self.assertEqual(call["url"], "https://auth.example.test/api:ZQDs0IzN/user")
        self.assertEqual(
            call["headers"]["Authorization"],
            "Bearer admin-session",
        )
        self.assertNotIn("params", call)
        self.assertNotIn("password", call)

    def test_list_accepts_empty_result_and_rejects_malformed_records(self):
        with patch.object(xano_client, "xano_request", return_value=[]):
            self.assertEqual(xano_client.listar_usuarios("admin-session"), [])

        for response in (
            None,
            {},
            [None],
            [{"id": 17}],
            [user_record(id=0)],
            [user_record(email="invalid")],
            [user_record(created_at=None)],
        ):
            with self.subTest(response=response):
                with patch.object(
                    xano_client,
                    "xano_request",
                    return_value=response,
                ):
                    with self.assertRaises(
                        xano_client.RespostaUsuarioInconclusivaError
                    ):
                        xano_client.listar_usuarios("admin-session")

    def test_list_requires_a_nonempty_token_before_request(self):
        for token in ("", "  ", None):
            with self.subTest(token=token):
                with patch.object(xano_client, "xano_request") as request:
                    with self.assertRaises(ValueError):
                        xano_client.listar_usuarios(token)
                request.assert_not_called()

    def test_list_propagates_http_errors_for_screen_handling(self):
        for status_code in (400, 401, 403, 500):
            response = Mock()
            response.status_code = status_code
            error = requests.HTTPError(response=response)
            with self.subTest(status_code=status_code):
                with patch.object(
                    xano_client,
                    "xano_request",
                    side_effect=error,
                ) as request:
                    with self.assertRaises(requests.HTTPError):
                        xano_client.listar_usuarios("admin-session")
                request.assert_called_once_with(
                    "GET",
                    "/user",
                    token="admin-session",
                )

    def test_create_posts_exact_payload_to_auth_group_and_projects_response(self):
        password = "LocalOnly9"
        response = user_record(
            name="Pessoa Usuária",
            email="pessoa@example.test",
            role="Adm",
            password="unexpected-response-field",
        )
        with patch(
            "app.xano_client.requests.request",
            return_value=self._response(response),
        ) as request:
            result = xano_client.criar_usuario(
                "admin-session",
                name=" Pessoa Usuária ",
                email=" pessoa@example.test ",
                password=password,
                role="Adm",
            )

        self.assertEqual(result, user_record(role="Adm"))
        self.assertNotIn("password", result)
        call = request.call_args.kwargs
        self.assertEqual(call["method"], "POST")
        self.assertEqual(call["url"], "https://auth.example.test/api:ZQDs0IzN/user")
        self.assertEqual(
            call["headers"]["Authorization"],
            "Bearer admin-session",
        )
        self.assertEqual(
            call["json"],
            {
                "name": "Pessoa Usuária",
                "email": "pessoa@example.test",
                "password": password,
                "role": "Adm",
            },
        )
        self.assertNotIn("params", call)

    def test_create_validation_rejects_missing_invalid_or_unsupported_data(self):
        invalid_payloads = (
            {"name": "", "email": "pessoa@example.test", "password": "valid123", "role": "Adm"},
            {"name": "Pessoa", "email": "", "password": "valid123", "role": "Adm"},
            {"name": "Pessoa", "email": "invalid", "password": "valid123", "role": "Adm"},
            {"name": "Pessoa", "email": "pessoa@example.test", "password": "short1", "role": "Adm"},
            {"name": "Pessoa", "email": "pessoa@example.test", "password": "letters-only", "role": "Adm"},
            {"name": "Pessoa", "email": "pessoa@example.test", "password": "valid123", "role": "admin"},
        )
        for payload in invalid_payloads:
            with self.subTest(payload={key: value for key, value in payload.items() if key != "password"}):
                with patch.object(xano_client, "xano_request") as request:
                    with self.assertRaises(ValueError):
                        xano_client.criar_usuario(
                            "admin-session",
                            **payload,
                        )
                request.assert_not_called()

    def test_create_rejects_unconfirmed_response_without_returning_sensitive_fields(self):
        responses = (
            None,
            [],
            {"id": 17},
            user_record(email="another@example.test", role="Adm"),
            user_record(role="Adm", created_at=None),
        )
        for response in responses:
            with self.subTest(response=response):
                with patch.object(
                    xano_client,
                    "xano_request",
                    return_value=response,
                ):
                    with self.assertRaises(
                        xano_client.RespostaUsuarioInconclusivaError
                    ):
                        xano_client.criar_usuario(
                            "admin-session",
                            name="Pessoa Usuária",
                            email="pessoa@example.test",
                            password="LocalOnly9",
                            role="Adm",
                        )

    def test_create_propagates_http_errors_without_retrying(self):
        for status_code in (400, 401, 403, 500):
            response = Mock()
            response.status_code = status_code
            error = requests.HTTPError(response=response)
            with self.subTest(status_code=status_code):
                with patch.object(
                    xano_client,
                    "xano_request",
                    side_effect=error,
                ) as request:
                    with self.assertRaises(requests.HTTPError):
                        xano_client.criar_usuario(
                            "admin-session",
                            name="Pessoa Usuária",
                            email="pessoa@example.test",
                            password="LocalOnly9",
                            role="Adm",
                        )
                request.assert_called_once()

    def test_create_marks_transport_failures_as_inconclusive(self):
        for error in (
            requests.Timeout("timeout"),
            requests.ConnectionError("offline"),
        ):
            with self.subTest(error=type(error).__name__):
                with patch.object(
                    xano_client,
                    "xano_request",
                    side_effect=error,
                ) as request:
                    with self.assertRaises(
                        xano_client.OperacaoUsuarioInconclusivaError
                    ):
                        xano_client.criar_usuario(
                            "admin-session",
                            name="Pessoa Usuária",
                            email="pessoa@example.test",
                            password="LocalOnly9",
                            role="Adm",
                        )
                request.assert_called_once()

    def test_create_rejects_invalid_json_response_as_unconfirmed(self):
        invalid_json_response = self._response(
            None,
            content=b"not-json",
        )
        invalid_json_response.json.side_effect = ValueError("invalid json")
        invalid_json_response.text = "invalid json"
        with patch(
            "app.xano_client.requests.request",
            return_value=invalid_json_response,
        ):
            with self.assertRaises(
                xano_client.RespostaUsuarioInconclusivaError
            ):
                xano_client.criar_usuario(
                    "admin-session",
                    name="Pessoa Usuária",
                    email="pessoa@example.test",
                    password="LocalOnly9",
                    role="Adm",
                )


if __name__ == "__main__":
    unittest.main()
