
import os
import unittest
from unittest.mock import patch

import app.xano_client as xano_client


class XanoConfigTestCase(unittest.TestCase):
    def tearDown(self):
        for key in ("XANO_API_URL", "XANO_API_TOKEN"):
            os.environ.pop(key, None)

        if hasattr(xano_client.st, "secrets"):
            delattr(xano_client.st, "secrets")

    def test_environment_variables_take_priority_over_streamlit_secrets(self):
        os.environ["XANO_API_URL"] = "https://env.example/api/"
        os.environ["XANO_API_TOKEN"] = "env-token"

        with patch.object(
            xano_client.st,
            "secrets",
            {
                "XANO_API_URL": "https://secret.example/api/",
                "XANO_API_TOKEN": "secret-token",
            },
            create=True,
        ):
            config = xano_client.get_xano_config()

        self.assertEqual(
            config["base_url"],
            "https://env.example/api",
        )
        self.assertEqual(config["token"], "env-token")

    def test_falls_back_to_streamlit_secrets_when_environment_is_missing(self):
        with patch.object(
            xano_client.st,
            "secrets",
            {
                "XANO_API_URL": "https://secret.example/api/",
                "XANO_API_TOKEN": "secret-token",
            },
            create=True,
        ):
            config = xano_client.get_xano_config()

        self.assertEqual(
            config["base_url"],
            "https://secret.example/api",
        )
        self.assertEqual(config["token"], "secret-token")

    def test_raises_clear_error_when_api_url_is_missing(self):
        with patch.dict(
            os.environ,
            {"XANO_API_TOKEN": "token"},
            clear=True,
        ):
            with patch.object(
                xano_client.st,
                "secrets",
                {},
                create=True,
            ):
                with self.assertRaisesRegex(
                    ValueError,
                    "XANO_API_URL",
                ):
                    xano_client.get_xano_config()

    def test_allows_missing_api_token_for_login(self):
        with patch.dict(
            os.environ,
            {"XANO_API_URL": "https://example.test/api/"},
            clear=True,
        ):
            with patch.object(
                xano_client.st,
                "secrets",
                {"XANO_API_URL": "https://example.test/api/"},
                create=True,
            ):
                config = xano_client.get_xano_config()

        self.assertEqual(
            config["base_url"],
            "https://example.test/api",
        )
        self.assertIsNone(config["token"])

    def test_removes_trailing_slash_from_url(self):
        os.environ["XANO_API_URL"] = "https://example.test/api/"
        os.environ["XANO_API_TOKEN"] = "token"

        config = xano_client.get_xano_config()

        self.assertEqual(
            config["base_url"],
            "https://example.test/api",
        )

    def test_builds_product_url_without_duplicate_prefixes(self):
        base_url = "https://example.test/api:ZQDs0IzN"
        endpoint = "/api:ZQDs0IzN/product"

        self.assertEqual(
            xano_client._build_api_url(base_url, endpoint),
            "https://example.test/api:ZQDs0IzN/product",
        )

    def test_uses_separate_auth_and_resource_bases_when_defined(self):
        os.environ["XANO_API_URL"] = "https://example.test/api:default"
        os.environ["XANO_AUTH_URL"] = "https://example.test/api:auth"
        os.environ["XANO_RESOURCES_URL"] = "https://example.test/api:resources"
        os.environ["XANO_API_TOKEN"] = "token"

        config = xano_client.get_xano_config()

        self.assertEqual(config["auth_base_url"], "https://example.test/api:auth")
        self.assertEqual(config["resources_base_url"], "https://example.test/api:resources")
        self.assertEqual(config["base_url"], "https://example.test/api:default")

    def test_auth_urls_fall_back_to_default_base_when_not_defined(self):
        os.environ["XANO_API_URL"] = "https://example.test/api:default"
        os.environ["XANO_API_TOKEN"] = "token"

        config = xano_client.get_xano_config()

        self.assertEqual(config["auth_base_url"], "https://example.test/api:default")
        self.assertEqual(config["resources_base_url"], "https://example.test/api:default")

    def test_extracts_token_from_login_response(self):
        payload = {
            "token": "abc123",
            "user": {
                "email": "teste@codbar.dev",
                "profile": "Adm",
            },
        }

        self.assertEqual(
            xano_client.extrair_token_login(payload),
            "abc123",
        )

    def test_extracts_user_from_login_response_without_user_key(self):
        payload = {
            "token": "xyz",
            "data": {
                "email": "teste@codbar.dev",
                "perfil": "aux.ecommerce",
            },
        }

        usuario = xano_client.extrair_usuario_autenticado(payload)

        self.assertEqual(usuario["email"], "teste@codbar.dev")
        self.assertEqual(
            xano_client.normalizar_perfil_usuario(usuario),
            "aux.ecommerce",
        )

    def test_login_failure_without_token_or_user(self):
        payload = {"error": "Invalid credentials"}

        autenticacao = xano_client.autenticar_usuario_resposta(payload)

        self.assertFalse(autenticacao["ok"])
        self.assertIsNone(autenticacao["token"])

    def test_missing_profile_blocks_authentication(self):
        payload = {
            "token": "abc",
            "user": {"email": "teste@codbar.dev"},
        }

        autenticacao = xano_client.autenticar_usuario_resposta(payload)

        self.assertFalse(autenticacao["ok"])
        self.assertEqual(
            autenticacao["error"],
            "Perfil do usuário ausente ou não reconhecido.",
        )

    def test_create_product_posts_spec_fields_as_json_with_bearer_token(self):
        with patch.dict(
            os.environ,
            {"XANO_API_URL": "https://example.test/api:resources"},
            clear=True,
        ):
            with patch.object(
                xano_client.st,
                "secrets",
                {"XANO_API_URL": "https://example.test/api:resources"},
                create=True,
            ):
                with patch("app.xano_client.requests.request") as mock_request:
                    mock_request.return_value.status_code = 201
                    mock_request.return_value.content = b'{"id": 12}'
                    mock_request.return_value.json.return_value = {"id": 12}

                    result = xano_client.criar_produto(
                        token="user-token",
                        name="Produto de teste",
                        description="Cadastro acadêmico fictício",
                        category_id=2,
                        min_stock=0,
                        sale_price=12.5,
                        status="ativo",
                    )

        self.assertEqual(result, {"id": 12})
        self.assertEqual(mock_request.call_args.kwargs["method"], "POST")
        self.assertEqual(
            mock_request.call_args.kwargs["url"],
            "https://example.test/api:resources/product",
        )
        self.assertEqual(
            mock_request.call_args.kwargs["json"],
            {
                "name": "Produto de teste",
                "description": "Cadastro acadêmico fictício",
                "category_id": 2,
                "min_stock": 0,
                "sale_price": 12.5,
                "status": "ativo",
                "sku": "",
            },
        )
        self.assertEqual(
            mock_request.call_args.kwargs["headers"]["Authorization"],
            "Bearer user-token",
        )

    def test_create_product_rejects_invalid_fields_before_request(self):
        invalid_products = (
            {"name": " ", "description": "Desc", "category_id": 1, "min_stock": 0, "sale_price": 12.5, "status": "ativo"},
            {"name": "Produto", "description": "Desc", "category_id": 0, "min_stock": 0, "sale_price": 12.5, "status": "ativo"},
            {"name": "Produto", "description": "Desc", "category_id": 1, "min_stock": -1, "sale_price": 12.5, "status": "ativo"},
            {"name": "Produto", "description": "Desc", "category_id": 1, "min_stock": 0, "sale_price": float("nan"), "status": "ativo"},
            {"name": "Produto", "description": "Desc", "category_id": 1, "min_stock": 0, "sale_price": 12.5, "status": "desconhecido"},
        )

        with patch("app.xano_client.requests.request") as mock_request:
            for fields in invalid_products:
                with self.subTest(fields=fields):
                    with self.assertRaises(ValueError):
                        xano_client.criar_produto(token="user-token", **fields)

        mock_request.assert_not_called()

    def test_product_search_helper_only_sends_name_when_explicitly_informed(self):
        with patch.dict(
            os.environ,
            {"XANO_API_URL": "https://example.test/api:resources"},
            clear=True,
        ):
            with patch.object(
                xano_client.st,
                "secrets",
                {"XANO_API_URL": "https://example.test/api:resources"},
                create=True,
            ):
                with patch("app.xano_client.requests.request") as mock_request:
                    mock_request.return_value.status_code = 200
                    mock_request.return_value.content = b"[]"
                    mock_request.return_value.json.return_value = []

                    xano_client.listar_produtos(token="abc123", name="camiseta", category_id=3)

        self.assertEqual(
            mock_request.call_args.kwargs["params"],
            {"name": "camiseta", "category_id": 3},
        )
        self.assertEqual(
            mock_request.call_args.kwargs["headers"]["Authorization"],
            "Bearer abc123",
        )

    def test_product_search_helper_ignores_blank_name_without_sending_it(self):
        with patch.dict(
            os.environ,
            {"XANO_API_URL": "https://example.test/api:resources"},
            clear=True,
        ):
            with patch.object(
                xano_client.st,
                "secrets",
                {"XANO_API_URL": "https://example.test/api:resources"},
                create=True,
            ):
                with patch("app.xano_client.requests.request") as mock_request:
                    mock_request.return_value.status_code = 200
                    mock_request.return_value.content = b"[]"
                    mock_request.return_value.json.return_value = []

                    xano_client.listar_produtos(token="abc123", name="", status="ativo")

        self.assertEqual(
            mock_request.call_args.kwargs["params"],
            {"status": "ativo"},
        )

    def test_http_error_status_codes_are_preserved(self):
        with patch.dict(
            os.environ,
            {"XANO_API_URL": "https://example.test/api:resources"},
            clear=True,
        ):
            with patch.object(
                xano_client.st,
                "secrets",
                {"XANO_API_URL": "https://example.test/api:resources"},
                create=True,
            ):
                with patch("app.xano_client.requests.request") as mock_request:
                    for status_code in (400, 401, 403, 500):
                        mock_response = type(
                            "Response",
                            (),
                            {"status_code": status_code, "content": b"{}"},
                        )()
                        mock_response.raise_for_status = lambda: (_ for _ in ()).throw(
                            xano_client.requests.HTTPError(response=mock_response)
                        )
                        mock_request.return_value = mock_response

                        with self.assertRaises(xano_client.requests.HTTPError):
                            xano_client.criar_produto(
                                token="abc123",
                                name="Produto",
                                description="Descrição",
                                category_id=1,
                                min_stock=0,
                                sale_price=12.5,
                                status="ativo",
                            )

    def test_invalid_streamlit_secrets_object_raises_runtime_error(self):
        with patch.object(
            xano_client.st,
            "secrets",
            object(),
            create=True,
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                r"st\.secrets",
            ):
                xano_client._get_streamlit_secret("XANO_API_URL")


if __name__ == "__main__":
    unittest.main()
