
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

    def test_builds_category_url_for_active_categories_with_expected_group(self):
        with patch.object(
            xano_client.st,
            "secrets",
            {
                "XANO_API_URL": "https://x8ki-letl-twmt.n7.xano.io/api:pi5tdncF",
                "XANO_RESOURCES_URL": "https://x8ki-letl-twmt.n7.xano.io/api:pi5tdncF",
                "XANO_AUTH_URL": "https://x8ki-letl-twmt.n7.xano.io/api:ZQDs0IzN",
                "XANO_API_TOKEN": "",
            },
            create=True,
        ):
            with patch("app.xano_client.requests.request") as mock_request:
                mock_request.return_value.status_code = 200
                mock_request.return_value.content = b'[{"id":2,"name":"Informatica","status":"ativo"}]'
                mock_request.return_value.json.return_value = [
                    {"id": 2, "name": "Informatica", "status": "ativo"}
                ]

                xano_client.listar_categorias_ativas(token="jwt-token")

        self.assertEqual(
            mock_request.call_args.kwargs["url"],
            "https://x8ki-letl-twmt.n7.xano.io/api:pi5tdncF/category",
        )
        self.assertEqual(
            mock_request.call_args.kwargs["params"],
            {"status": "ativo"},
        )
        self.assertEqual(
            mock_request.call_args.kwargs["headers"]["Authorization"],
            "Bearer jwt-token",
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

    def test_routes_use_the_expected_operation_specific_base_urls(self):
        with patch.dict(
            os.environ,
            {
                "XANO_API_URL": "https://x8ki-letl-twmt.n7.xano.io/api:pi5tdncF",
                "XANO_AUTH_URL": "https://x8ki-letl-twmt.n7.xano.io/api:ZQDs0IzN",
                "XANO_CATEGORIES_URL": "https://x8ki-letl-twmt.n7.xano.io/api:pi5tdncF",
                "XANO_PRODUCTS_URL": "https://x8ki-letl-twmt.n7.xano.io/api:4FsHXYfS",
                "XANO_API_TOKEN": "token",
            },
            clear=True,
        ):
            with patch.object(
                xano_client.st,
                "secrets",
                {
                    "XANO_API_URL": "https://x8ki-letl-twmt.n7.xano.io/api:pi5tdncF",
                    "XANO_AUTH_URL": "https://x8ki-letl-twmt.n7.xano.io/api:ZQDs0IzN",
                    "XANO_CATEGORIES_URL": "https://x8ki-letl-twmt.n7.xano.io/api:pi5tdncF",
                    "XANO_PRODUCTS_URL": "https://x8ki-letl-twmt.n7.xano.io/api:4FsHXYfS",
                    "XANO_API_TOKEN": "token",
                },
                create=True,
            ):
                with patch("app.xano_client.requests.request") as mock_request:
                    mock_request.return_value.status_code = 200
                    mock_request.return_value.content = b"{}"
                    mock_request.return_value.json.return_value = {}

                    xano_client.xano_request(
                        "POST",
                        "/auth/login",
                        token="jwt-login",
                        json={"email": "user@test.com", "password": "secret"},
                    )
                    xano_client.xano_request(
                        "GET",
                        "/auth/me",
                        token="jwt-me",
                    )
                    xano_client.xano_request(
                        "GET",
                        "/category",
                        token="jwt-category",
                        params={"status": "ativo"},
                    )
                    xano_client.xano_request(
                        "POST",
                        "/product",
                        token="jwt-product",
                        json={"name": "Produto", "category_id": 2},
                    )

        expected_urls = [
            "https://x8ki-letl-twmt.n7.xano.io/api:ZQDs0IzN/auth/login",
            "https://x8ki-letl-twmt.n7.xano.io/api:ZQDs0IzN/auth/me",
            "https://x8ki-letl-twmt.n7.xano.io/api:pi5tdncF/category",
            "https://x8ki-letl-twmt.n7.xano.io/api:4FsHXYfS/product",
        ]

        self.assertEqual(
            [call.kwargs["url"] for call in mock_request.call_args_list],
            expected_urls,
        )
        self.assertEqual(
            mock_request.call_args_list[0].kwargs["headers"]["Authorization"],
            "Bearer jwt-login",
        )
        self.assertEqual(
            mock_request.call_args_list[2].kwargs["headers"]["Authorization"],
            "Bearer jwt-category",
        )
        self.assertEqual(
            mock_request.call_args_list[3].kwargs["headers"]["Authorization"],
            "Bearer jwt-product",
        )
        self.assertEqual(
            mock_request.call_args_list[2].kwargs["params"],
            {"status": "ativo"},
        )

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

    def test_create_product_posts_contract_fields_without_status(self):
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
                "sku": "",
            },
        )
        self.assertEqual(
            mock_request.call_args.kwargs["headers"]["Authorization"],
            "Bearer user-token",
        )

    def test_create_product_allows_empty_description_and_sends_it_in_payload(self):
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
                        name="Produto sem descrição",
                        description="",
                        category_id=2,
                        min_stock=0,
                        sale_price=12.5,
                    )

        self.assertEqual(result, {"id": 12})
        self.assertEqual(
            mock_request.call_args.kwargs["json"]["description"],
            "",
        )

    def test_create_product_rejects_invalid_fields_before_request(self):
        invalid_products = (
            {"name": " ", "description": "Desc", "category_id": 1, "min_stock": 0, "sale_price": 12.5},
            {"name": "Produto", "description": "Desc", "category_id": 0, "min_stock": 0, "sale_price": 12.5},
            {"name": "Produto", "description": "Desc", "category_id": 1, "min_stock": -1, "sale_price": 12.5},
            {"name": "Produto", "description": "Desc", "category_id": 1, "min_stock": 0, "sale_price": float("nan")},
        )

        with patch("app.xano_client.requests.request") as mock_request:
            for fields in invalid_products:
                with self.subTest(fields=fields):
                    with self.assertRaises(ValueError):
                        xano_client.criar_produto(token="user-token", **fields)

        mock_request.assert_not_called()

    def test_create_product_rejects_inconclusive_backend_response(self):
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
                    for payload in (None, {}, {"status": "success"}, {"message": "ok"}):
                        mock_request.return_value.status_code = 200
                        mock_request.return_value.content = b"" if payload is None else b"{}"
                        mock_request.return_value.json.return_value = payload

                        with self.subTest(payload=payload):
                            with self.assertRaisesRegex(ValueError, "confirmou"):
                                xano_client.criar_produto(
                                    token="user-token",
                                    name="Produto",
                                    description="Descrição",
                                    category_id=1,
                                    min_stock=0,
                                    sale_price=12.5,
                                )

    def test_create_product_accepts_valid_confirmation_payloads(self):
        payloads = (
            {"id": 15},
            {"data": {"id": 16}},
            {"product": {"id": 17}},
            {"status": "success", "data": {"id": 18}},
        )

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
                    for payload in payloads:
                        mock_request.return_value.status_code = 201
                        mock_request.return_value.content = b"{}"
                        mock_request.return_value.json.return_value = payload

                        with self.subTest(payload=payload):
                            result = xano_client.criar_produto(
                                token="user-token",
                                name="Produto",
                                description="Descrição",
                                category_id=1,
                                min_stock=0,
                                sale_price=12.5,
                            )
                            self.assertEqual(result, payload)

    def test_list_categories_uses_active_status_and_validates_payload(self):
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
                    mock_request.return_value.content = b'[{"id": 2, "name": "Informatica", "status": "ativo"}, {"id": 3, "name": "Eletronicos", "status": "inativo"}, {"id": 4, "name": "", "status": "ativo"}]'
                    mock_request.return_value.json.return_value = [
                        {"id": 2, "name": "Informatica", "status": "ativo"},
                        {"id": 3, "name": "Eletronicos", "status": "inativo"},
                        {"id": 4, "name": "", "status": "ativo"},
                    ]

                    categorias = xano_client.listar_categorias_ativas(token="abc123")

        self.assertEqual(
            categorias,
            [{"id": 2, "name": "Informatica", "status": "ativo"}],
        )
        self.assertEqual(
            mock_request.call_args.kwargs["params"],
            {"status": "ativo"},
        )
        self.assertTrue(
            mock_request.call_args.kwargs["headers"]["Authorization"].startswith("Bearer ")
        )

    def test_category_name_lookup_returns_real_id(self):
        categorias = [
            {"id": 2, "name": "Informatica", "status": "ativo"},
            {"id": 7, "name": "Móveis", "status": "ativo"},
        ]

        self.assertEqual(
            xano_client.resolver_categoria_por_nome(categorias, "Informatica"),
            2,
        )

    def test_invalid_category_response_raises_value_error(self):
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
                    mock_request.return_value.content = b"{}"
                    mock_request.return_value.json.return_value = {}

                    with self.assertRaisesRegex(ValueError, "Nenhuma categoria ativa"):
                        xano_client.listar_categorias_ativas(token="abc123")

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

    def test_connection_error_is_propagated(self):
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
                    mock_request.side_effect = xano_client.requests.RequestException(
                        "connection failed"
                    )

                    with self.assertRaises(xano_client.requests.RequestException):
                        xano_client.criar_produto(
                            token="abc123",
                            name="Produto",
                            description="Descrição",
                            category_id=1,
                            min_stock=0,
                            sale_price=12.5,
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
