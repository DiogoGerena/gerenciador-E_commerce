
import os
import tempfile
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

import app.xano_client as xano_client


class XanoConfigTestCase(unittest.TestCase):
    def setUp(self):
        xano_environment = {
            key: ""
            for key in (
                "XANO_API_URL",
                "XANO_AUTH_URL",
                "XANO_RESOURCES_URL",
                "XANO_CATEGORIES_URL",
                "XANO_PRODUCTS_URL",
                "XANO_SUPPLIERS_URL",
                "XANO_STOCK_ENTRIES_URL",
                "XANO_STOCK_MOVEMENTS_URL",
                "XANO_SALES_URL",
                "XANO_API_TOKEN",
            )
        }
        self._env_patch = patch.dict(os.environ, xano_environment)
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

    def test_project_dotenv_is_loaded_from_project_root_not_current_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir) / "project"
            other_directory = Path(temp_dir) / "outside"
            project_root.mkdir()
            other_directory.mkdir()
            (project_root / ".env").write_text(
                "XANO_API_URL=https://dotenv.example/api:resources\n"
                "XANO_API_TOKEN=unit-test-token\n",
                encoding="utf-8",
            )

            previous_directory = os.getcwd()
            try:
                with patch.dict(os.environ, {}, clear=True), patch.object(
                    xano_client,
                    "DOTENV_PATH",
                    project_root / ".env",
                ):
                    os.chdir(other_directory)
                    xano_client._load_project_environment()
                    with patch("app.xano_client.requests.request") as request:
                        request.return_value.status_code = 200
                        request.return_value.content = b"{}"
                        request.return_value.json.return_value = {}
                        config = xano_client.get_xano_config()
                        xano_client.xano_request("GET", "/product")
            finally:
                os.chdir(previous_directory)

        self.assertEqual(config["base_url"], "https://dotenv.example/api:resources")
        self.assertTrue(config["token"])
        authorization = request.call_args.kwargs["headers"]["Authorization"]
        self.assertTrue(authorization.startswith("Bearer "))
        self.assertTrue(authorization[len("Bearer ") :].strip())

    def test_process_environment_takes_priority_over_project_dotenv(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            dotenv_path = Path(temp_dir) / ".env"
            dotenv_path.write_text(
                "XANO_API_URL=https://dotenv.example/api:resources\n"
                "XANO_API_TOKEN=dotenv-test-token\n",
                encoding="utf-8",
            )
            with patch.dict(
                os.environ,
                {
                    "XANO_API_URL": "https://process.example/api:resources",
                    "XANO_API_TOKEN": "process-test-token",
                },
                clear=True,
            ), patch.object(xano_client, "DOTENV_PATH", dotenv_path):
                xano_client._load_project_environment()
                config = xano_client.get_xano_config()

        self.assertEqual(config["base_url"], "https://process.example/api:resources")
        self.assertEqual(config["token"], "process-test-token")

    def test_protected_request_without_token_fails_before_http(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(
            xano_client.st,
            "secrets",
            {"XANO_API_URL": "https://example.test/api:resources"},
            create=True,
        ), patch("app.xano_client.requests.request") as request:
            with self.assertRaisesRegex(ValueError, "Token Xano ausente"):
                xano_client.xano_request("GET", "/product")

        request.assert_not_called()

    def test_login_without_token_does_not_send_authorization_header(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(
            xano_client.st,
            "secrets",
            {"XANO_API_URL": "https://example.test/api:auth"},
            create=True,
        ), patch("app.xano_client.requests.request") as request:
            request.return_value.status_code = 200
            request.return_value.content = b"{}"
            request.return_value.json.return_value = {}
            xano_client.xano_request(
                "POST",
                "/auth/login",
                json={"email": "user@example.test", "password": "test-only"},
            )

        headers = request.call_args.kwargs["headers"]
        self.assertNotIn("Authorization", headers)

    def test_authorization_header_is_bearer_and_nonempty(self):
        with patch.dict(
            os.environ,
            {"XANO_API_URL": "https://example.test/api:resources"},
            clear=True,
        ), patch.object(
            xano_client.st,
            "secrets",
            {},
            create=True,
        ), patch("app.xano_client.requests.request") as request:
            request.return_value.status_code = 200
            request.return_value.content = b"{}"
            request.return_value.json.return_value = {}
            xano_client.xano_request("GET", "/product", token="unit-test-token")

        authorization = request.call_args.kwargs["headers"]["Authorization"]
        self.assertTrue(authorization.startswith("Bearer "))
        self.assertTrue(authorization[len("Bearer ") :].strip())
        self.assertNotIn("None", authorization)

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
            "Bearer " + "jwt-token",
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
            "Bearer " + "jwt-login",
        )
        self.assertEqual(
            mock_request.call_args_list[2].kwargs["headers"]["Authorization"],
            "Bearer " + "jwt-category",
        )
        self.assertEqual(
            mock_request.call_args_list[3].kwargs["headers"]["Authorization"],
            "Bearer " + "jwt-product",
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

    def test_supplier_requests_use_configured_base_and_preserve_legacy_fallback(self):
        with patch.dict(
            os.environ,
            {
                "XANO_API_URL": "https://example.test/api:default",
                "XANO_SUPPLIERS_URL": "https://example.test/api:suppliers/",
            },
            clear=True,
        ):
            with patch.object(xano_client.st, "secrets", {}, create=True):
                config = xano_client.get_xano_config()
                self.assertEqual(
                    config["suppliers_base_url"],
                    "https://example.test/api:suppliers",
                )
                with patch("app.xano_client.requests.request") as request:
                    request.return_value.status_code = 200
                    request.return_value.content = b"[]"
                    request.return_value.json.return_value = []

                    self.assertEqual(
                        xano_client.listar_fornecedores(
                            token="session-token",
                        ),
                        [],
                    )

        self.assertEqual(
            request.call_args.kwargs["url"],
            "https://example.test/api:suppliers/supplier",
        )
        self.assertEqual(
            request.call_args.kwargs["headers"]["Authorization"],
            "Bearer session-token",
        )
        self.assertEqual(
            request.call_args.kwargs["params"],
            {"status": "ativo"},
        )

        with patch.dict(
            os.environ,
            {"XANO_API_URL": "https://example.test/api:default"},
            clear=True,
        ):
            with patch.object(xano_client.st, "secrets", {}, create=True):
                self.assertEqual(
                    xano_client.get_xano_config()["suppliers_base_url"],
                    xano_client.SUPPLIERS_BASE_URL,
                )

    def test_dynamic_supplier_and_product_paths_use_their_own_bases(self):
        bases = {
            "XANO_API_URL": "https://example.test/api:default",
            "XANO_PRODUCTS_URL": "https://example.test/api:products",
            "XANO_SUPPLIERS_URL": "https://example.test/api:suppliers",
        }
        with patch.dict(os.environ, bases, clear=True):
            with patch.object(xano_client.st, "secrets", {}, create=True):
                with patch("app.xano_client.requests.request") as request:
                    request.return_value.status_code = 200
                    request.return_value.content = (
                        b'{"id":1,"name":"Registro","category_id":3,'
                        b'"min_stock":0,"sale_price":0,"status":"ativo",'
                        b'"stock_quantity":0,"average_cost":0}'
                    )
                    request.return_value.json.return_value = {
                        "id": 1,
                        "name": "Registro",
                        "category_id": 3,
                        "min_stock": 0,
                        "sale_price": 0,
                        "status": "ativo",
                        "stock_quantity": 0,
                        "average_cost": 0,
                    }
                    xano_client.consultar_produto("product-token", 1)
                    xano_client.consultar_fornecedor("supplier-token", 1)

        calls = request.call_args_list
        self.assertEqual(
            [call.kwargs["url"] for call in calls],
            [
                "https://example.test/api:products/product/1",
                "https://example.test/api:suppliers/supplier/1",
            ],
        )
        self.assertEqual(
            [call.kwargs["headers"]["Authorization"] for call in calls],
            ["Bearer product-token", "Bearer supplier-token"],
        )

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
        created_product = {
            "id": 12,
            "name": "Produto de teste",
            "category_id": 2,
            "min_stock": 0,
            "sale_price": 12.5,
            "sku": "",
            "description": None,
        }
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
                    mock_request.return_value.content = b'{"id":12,"name":"Produto de teste","category_id":2,"min_stock":0,"sale_price":12.5,"sku":"","description":null}'
                    mock_request.return_value.json.return_value = created_product

                    result = xano_client.criar_produto(
                        token="user-token",
                        name="Produto de teste",
                        category_id=2,
                        min_stock=0,
                        sale_price=12.5,
                    )

        self.assertEqual(result, created_product)
        self.assertEqual(mock_request.call_args.kwargs["method"], "POST")
        self.assertEqual(
            mock_request.call_args.kwargs["url"],
            "https://example.test/api:resources/product",
        )
        self.assertEqual(
            mock_request.call_args.kwargs["json"],
            {
                "name": "Produto de teste",
                "category_id": 2,
                "min_stock": 0,
                "sale_price": 12.5,
            },
        )
        self.assertEqual(
            mock_request.call_args.kwargs["headers"]["Authorization"],
            "Bearer " + "user-token",
        )

    def test_create_product_does_not_send_description(self):
        created_product = {
            "id": 12,
            "name": "Produto sem descrição",
            "category_id": 2,
            "min_stock": 0,
            "sale_price": 12.5,
            "sku": "SKU-12",
        }
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
                    mock_request.return_value.content = b'{"id":12,"name":"Produto sem descri\\u00e7\\u00e3o","category_id":2,"min_stock":0,"sale_price":12.5,"sku":"SKU-12","description":null}'
                    mock_request.return_value.json.return_value = created_product

                    result = xano_client.criar_produto(
                        token="user-token",
                        name="Produto sem descrição",
                        category_id=2,
                        min_stock=0,
                        sale_price=12.5,
                        sku=" SKU-12 ",
                        description="",
                    )

        self.assertEqual(result, created_product)
        self.assertNotIn(
            "description",
            mock_request.call_args.kwargs["json"],
        )
        self.assertEqual(
            mock_request.call_args.kwargs["json"]["sku"],
            "SKU-12",
        )

    def test_create_product_sends_a_nonempty_sku(self):
        payload = xano_client.mapear_payload_produto(
            name="Produto com SKU",
            sku="SKU-123",
            category_id=2,
            min_stock=0,
            sale_price=12.5,
        )

        self.assertEqual(payload["sku"], "SKU-123")

    def test_create_product_rejects_invalid_fields_before_request(self):
        invalid_products = (
            {"name": " ", "category_id": 1, "min_stock": 0, "sale_price": 12.5},
            {"name": "Produto", "category_id": 0, "min_stock": 0, "sale_price": 12.5},
            {"name": "Produto", "category_id": 1, "min_stock": -1, "sale_price": 12.5},
            {"name": "Produto", "category_id": 1, "min_stock": 0, "sale_price": float("nan")},
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
                    for payload in (
                        None,
                        {},
                        {"id": 12},
                        {"status": "success"},
                        {"status": "success", "data": {"id": 12}},
                        {"product": {"id": 12, "name": "Produto"}},
                        {"name": "Produto", "category_id": 1, "min_stock": -1, "sale_price": 2},
                    ):
                        mock_request.return_value.status_code = 200
                        mock_request.return_value.content = b"" if payload is None else b"{}"
                        mock_request.return_value.json.return_value = payload

                        with self.subTest(payload=payload):
                            with self.assertRaisesRegex(
                                xano_client.RespostaCriacaoInconclusivaError,
                                "confirmou",
                            ):
                                xano_client.criar_produto(
                                    token="user-token",
                                    name="Produto",
                                    category_id=1,
                                    min_stock=0,
                                    sale_price=12.5,
                                )

    def test_create_product_accepts_valid_confirmation_payloads(self):
        payload = {
            "id": 15,
            "name": "Produto",
            "category_id": 1,
            "min_stock": 0,
            "sale_price": 12.5,
            "sku": "",
            "description": None,
        }

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
                    mock_request.return_value.content = b'{"id":15,"name":"Produto","category_id":1,"min_stock":0,"sale_price":12.5,"sku":"","description":null}'
                    mock_request.return_value.json.return_value = payload

                    result = xano_client.criar_produto(
                        token="user-token",
                        name="Produto",
                        category_id=1,
                        min_stock=0,
                        sale_price=12.5,
                    )
                    self.assertEqual(result, payload)

    def test_inconclusive_create_response_preserves_status_and_error_message(self):
        response_payload = {"message": "Invalid product response"}

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
                    mock_request.return_value.content = b'{"message":"Invalid product response"}'
                    mock_request.return_value.json.return_value = response_payload

                    with self.assertRaises(
                        xano_client.RespostaCriacaoInconclusivaError
                    ) as caught:
                        xano_client.criar_produto(
                            token="user-token",
                            name="Produto",
                            category_id=1,
                            min_stock=0,
                            sale_price=12.5,
                        )

        self.assertEqual(caught.exception.status_code, 200)
        self.assertEqual(
            caught.exception.backend_message,
            "Invalid product response",
        )

    def test_create_product_confirms_direct_record_without_optional_identifier(self):
        payload = {
            "name": "Produto",
            "category_id": 1,
            "min_stock": 0,
            "sale_price": 12.5,
            "sku": "",
            "description": None,
        }

        self.assertTrue(xano_client.confirmar_produto_criado(payload))
        self.assertFalse(
            xano_client.confirmar_produto_criado(
                {**payload, "id": "invalid-id"}
            )
        )
        self.assertFalse(
            xano_client.confirmar_produto_criado(
                {"status": "success", "data": payload}
            )
        )

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
            "Bearer " + "abc123",
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
                                category_id=1,
                                min_stock=0,
                                sale_price=12.5,
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

    def test_recognizes_operational_and_administrative_profiles(self):
        self.assertEqual(
            xano_client.normalizar_perfil_usuario({"role": "member"}),
            "member",
        )
        self.assertEqual(
            xano_client.normalizar_perfil_usuario({"role": "admin"}),
            "Adm",
        )
        self.assertEqual(
            xano_client.nivel_acesso_perfil("member"),
            1,
        )
        self.assertTrue(
            xano_client.pode_administrar("admin"),
        )
        self.assertFalse(
            xano_client.pode_administrar("aux.ecommerce"),
        )

    def test_category_crud_uses_category_endpoint(self):
        with patch.dict(
            os.environ,
            {"XANO_API_URL": "https://example.test/api:categories"},
            clear=True,
        ):
            with patch("app.xano_client.requests.request") as mock_request:
                mock_request.return_value.status_code = 200
                mock_request.return_value.content = b'{"id": 2}'
                mock_request.return_value.json.return_value = {"id": 2}

                xano_client.criar_categoria(
                    token="abc",
                    name="Eletrônicos",
                    description="Categoria principal",
                )
                xano_client.editar_categoria(
                    2,
                    token="abc",
                    name="Eletrônicos",
                    status="ativo",
                )
                xano_client.inativar_categoria(2, token="abc")

        urls = [call.kwargs["url"] for call in mock_request.call_args_list]
        methods = [call.kwargs["method"] for call in mock_request.call_args_list]
        self.assertEqual(methods, ["POST", "PATCH", "PATCH"])
        self.assertTrue(urls[0].endswith("/category"))
        self.assertTrue(urls[1].endswith("/category/2"))
        self.assertTrue(urls[2].endswith("/category/2/deactivate"))

    def test_supplier_crud_uses_supplier_endpoint_and_fields(self):
        with patch.dict(
            os.environ,
            {
                "XANO_API_URL": "https://example.test/api:default",
                "XANO_SUPPLIERS_URL": "https://example.test/api:suppliers",
            },
            clear=True,
        ):
            with patch("app.xano_client.requests.request") as mock_request:
                mock_request.return_value.status_code = 200
                mock_request.return_value.content = b'{"id": 7}'
                mock_request.return_value.json.side_effect = [
                    {
                        "id": 7,
                        "name": "Fornecedor Teste",
                        "status": "ativo",
                    },
                    {
                        "id": 7,
                        "name": "Fornecedor Atualizado",
                        "status": "ativo",
                    },
                    {
                        "id": 7,
                        "name": "Fornecedor Atualizado",
                        "status": "inativo",
                    },
                ]

                xano_client.criar_fornecedor(
                    token="abc",
                    name="Fornecedor Teste",
                    cnpj="04252011000110",
                )
                xano_client.editar_fornecedor(
                    7,
                    token="abc",
                    name="Fornecedor Atualizado",
                )
                xano_client.inativar_fornecedor(7, token="abc")

        urls = [call.kwargs["url"] for call in mock_request.call_args_list]
        self.assertTrue(urls[0].startswith("https://example.test/api:suppliers/supplier"))
        self.assertTrue(urls[1].endswith("/supplier/7"))
        self.assertTrue(urls[2].endswith("/supplier/7/deactivate"))
        self.assertEqual(
            mock_request.call_args_list[0].kwargs["json"]["cnpj"],
            "04252011000110",
        )

    def test_supplier_listing_always_sends_status_and_supports_all(self):
        with patch.dict(
            os.environ,
            {
                "XANO_API_URL": "https://example.test/api:default",
                "XANO_SUPPLIERS_URL": "https://example.test/api:suppliers",
            },
            clear=True,
        ), patch.object(xano_client.st, "secrets", {}, create=True):
            with patch("app.xano_client.requests.request") as mock_request:
                mock_request.return_value.status_code = 200
                mock_request.return_value.content = b"{}"
                mock_request.return_value.json.side_effect = [
                    {"suppliers": [{"id": 1, "status": "ativo"}]},
                    {"suppliers": [{"id": 1, "status": "ativo"}]},
                    {"suppliers": [{"id": 2, "status": "inativo"}]},
                ]

                ativos = xano_client.listar_fornecedores(
                    token="supplier-token",
                    status="ativo",
                )
                todos = xano_client.listar_fornecedores(
                    token="supplier-token",
                    status="todos",
                    name="fornecedor",
                )

        self.assertEqual(ativos, [{"id": 1, "status": "ativo"}])
        self.assertEqual(
            todos,
            [
                {"id": 1, "status": "ativo"},
                {"id": 2, "status": "inativo"},
            ],
        )
        self.assertEqual(
            mock_request.call_args_list[0].kwargs["params"],
            {"status": "ativo"},
        )
        self.assertEqual(
            mock_request.call_args_list[1].kwargs["params"],
            {"status": "ativo", "name": "fornecedor"},
        )
        self.assertEqual(
            mock_request.call_args_list[2].kwargs["params"],
            {"status": "inativo", "name": "fornecedor"},
        )
        self.assertTrue(
            all(
                call.kwargs["headers"]["Authorization"]
                == "Bearer supplier-token"
                for call in mock_request.call_args_list
            )
        )

    def test_detects_duplicate_record_response(self):
        error = Mock()
        error.response.json.return_value = {"message": "Duplicate record detected"}

        self.assertTrue(xano_client.erro_xano_indica_duplicidade(error))

        error.response.json.return_value = {"message": "Invalid input"}
        self.assertFalse(xano_client.erro_xano_indica_duplicidade(error))

    def test_supplier_listing_handles_empty_result_and_requires_known_status(self):
        with patch.dict(
            os.environ,
            {"XANO_API_URL": "https://example.test/api:default"},
            clear=True,
        ), patch.object(xano_client.st, "secrets", {}, create=True):
            with patch("app.xano_client.requests.request") as mock_request:
                mock_request.return_value.status_code = 200
                mock_request.return_value.content = b"[]"
                mock_request.return_value.json.return_value = []

                self.assertEqual(
                    xano_client.listar_fornecedores(
                        token="supplier-token",
                        status="ativo",
                    ),
                    [],
                )
                with self.assertRaisesRegex(ValueError, "situação válida"):
                    xano_client.listar_fornecedores(token="supplier-token")

        mock_request.assert_called_once()

    def test_supplier_listing_propagates_http_errors(self):
        error = xano_client.requests.HTTPError("HTTP 400")
        with patch.dict(
            os.environ,
            {"XANO_API_URL": "https://example.test/api:default"},
            clear=True,
        ), patch.object(xano_client.st, "secrets", {}, create=True), patch(
            "app.xano_client.requests.request",
            side_effect=error,
        ):
            with self.assertRaises(xano_client.requests.HTTPError):
                xano_client.listar_fornecedores(
                    token="supplier-token",
                    status="ativo",
                )

    def test_product_patch_never_sends_stock_or_average_cost(self):
        with patch.dict(
            os.environ,
            {"XANO_API_URL": "https://example.test/api:products"},
            clear=True,
        ):
            with patch("app.xano_client.requests.request") as mock_request:
                mock_request.return_value.status_code = 200
                mock_request.return_value.content = b'{"id": 12}'
                mock_request.return_value.json.return_value = {
                    "id": 12,
                    "name": "Produto Editado",
                    "category_id": 1,
                    "min_stock": 0,
                    "sale_price": 12.5,
                    "status": "ativo",
                    "stock_quantity": 0,
                    "average_cost": 12.5,
                }

                xano_client.editar_produto(
                    12,
                    token="abc",
                    name="Produto Editado",
                    stock_quantity=99,
                    average_cost=123.45,
                )

        payload = mock_request.call_args.kwargs["json"]
        self.assertEqual(payload, {"name": "Produto Editado"})
        self.assertNotIn("stock_quantity", payload)
        self.assertNotIn("average_cost", payload)

    def test_stock_entry_posts_contract_and_confirms_complete_response(self):
        with patch.dict(
            os.environ,
            {
                "XANO_API_URL": "https://example.test/api:default",
                "XANO_STOCK_ENTRIES_URL": "https://example.test/api:stock",
            },
            clear=True,
        ):
            with patch("app.xano_client.requests.request") as mock_request:
                mock_request.return_value.status_code = 200
                mock_request.return_value.content = b'{}'
                mock_request.return_value.json.return_value = {
                    "entry": {"id": 1},
                    "movement": {"id": 2},
                    "stock_quantity": 100,
                    "average_cost": 8.6,
                }
                result = xano_client.registrar_entrada_estoque(
                    token="abc",
                    product_id=10,
                    supplier_id=3,
                    quantity=100,
                    unit_purchase_cost=8,
                    entry_date="2026-11-20",
                    inbound_freight=50,
                    other_acquisition_costs=10,
                    invoice_number="NF-99881",
                    notes="Lote inicial",
                )
        self.assertEqual(result["stock_quantity"], 100)
        self.assertEqual(mock_request.call_args.kwargs["url"], "https://example.test/api:stock/stock-entry")
        self.assertEqual(
            mock_request.call_args.kwargs["json"],
            {
                "product_id": 10,
                "supplier_id": 3,
                "quantity": 100,
                "unit_purchase_cost": 8.0,
                "entry_date": "2026-11-20",
                "inbound_freight": 50.0,
                "other_acquisition_costs": 10.0,
                "invoice_number": "NF-99881",
                "notes": "Lote inicial",
            },
        )

    def test_stock_entry_rejects_invalid_fields_before_request(self):
        invalid = (
            {"product_id": 0, "supplier_id": 3, "quantity": 1, "unit_purchase_cost": 1, "entry_date": "2026-11-20"},
            {"product_id": 10, "supplier_id": 3, "quantity": 0, "unit_purchase_cost": 1, "entry_date": "2026-11-20"},
            {"product_id": 10, "supplier_id": 3, "quantity": 1, "unit_purchase_cost": 0, "entry_date": "2026-11-20"},
            {"product_id": 10, "supplier_id": 3, "quantity": 1, "unit_purchase_cost": -1, "entry_date": "2026-11-20"},
            {"product_id": 10, "supplier_id": 3, "quantity": 1, "unit_purchase_cost": 1, "entry_date": "20/11/2026"},
        )
        with patch("app.xano_client.requests.request") as mock_request:
            for fields in invalid:
                with self.subTest(fields=fields):
                    with self.assertRaises(ValueError):
                        xano_client.registrar_entrada_estoque(token="abc", **fields)
        mock_request.assert_not_called()

    def test_stock_entry_rejects_incomplete_confirmation(self):
        with patch.dict(
            os.environ,
            {
                "XANO_API_URL": "https://example.test/api:default",
                "XANO_STOCK_ENTRIES_URL": "https://example.test/api:stock",
            },
            clear=True,
        ):
            with patch("app.xano_client.requests.request") as mock_request:
                mock_request.return_value.status_code = 200
                mock_request.return_value.content = b'{}'
                mock_request.return_value.json.return_value = {
                    "entry": {"id": 1},
                    "movement": {"id": 2},
                }
                with self.assertRaisesRegex(ValueError, "saldo ou custo"):
                    xano_client.registrar_entrada_estoque(
                        token="abc",
                        product_id=10,
                        supplier_id=3,
                        quantity=1,
                        unit_purchase_cost=8,
                        entry_date="2026-11-20",
                    )

    def test_stock_entry_pagination_and_detail(self):
        with patch.dict(
            os.environ,
            {
                "XANO_API_URL": "https://example.test/api:default",
                "XANO_STOCK_ENTRIES_URL": "https://example.test/api:stock",
            },
            clear=True,
        ):
            with patch("app.xano_client.requests.request") as mock_request:
                mock_request.return_value.status_code = 200
                mock_request.return_value.content = b'{}'
                mock_request.return_value.json.side_effect = [
                    {"items": [{"id": 1}], "curPage": 1, "perPage": 20, "total": 1},
                    {"id": 1, "product": {"id": 10}, "supplier": {"id": 3}},
                ]
                page = xano_client.listar_entradas_estoque(
                    token="abc",
                    product_id=10,
                    supplier_id=3,
                    start_date="2026-11-01",
                    end_date="2026-11-20",
                    page=1,
                    per_page=20,
                )
                detail = xano_client.consultar_entrada_estoque(1, token="abc")
        self.assertEqual(page["items"][0]["id"], 1)
        self.assertEqual(detail["product"]["id"], 10)
        self.assertEqual(
            mock_request.call_args_list[0].kwargs["params"],
            {
                "product_id": 10,
                "supplier_id": 3,
                "start_date": "2026-11-01",
                "end_date": "2026-11-20",
                "page": 1,
                "per_page": 20,
            },
        )

    def test_movement_pagination_filters_and_detail(self):
        with patch.dict(
            os.environ,
            {
                "XANO_API_URL": "https://example.test/api:default",
                "XANO_STOCK_MOVEMENTS_URL": "https://example.test/api:moves",
            },
            clear=True,
        ):
            with patch("app.xano_client.requests.request") as mock_request:
                mock_request.return_value.status_code = 200
                mock_request.return_value.content = b'{}'
                mock_request.return_value.json.side_effect = [
                    {"movements": [{"id": 5}], "curPage": 1, "perPage": 20, "total": 1},
                    {"id": 5, "product": {"id": 10}},
                ]
                page = xano_client.listar_movimentacoes(
                    token="abc",
                    product_id=10,
                    movement_type="perda",
                    start_date="2026-11-01",
                    end_date="2026-11-20",
                )
                detail = xano_client.consultar_movimentacao(5, token="abc")
        self.assertEqual(page["movements"][0]["id"], 5)
        self.assertEqual(detail["product"]["id"], 10)
        self.assertEqual(
            mock_request.call_args_list[0].kwargs["params"]["movement_type"],
            "perda",
        )

    def test_stock_adjustments_enter_exit_and_loss(self):
        with patch.dict(
            os.environ,
            {
                "XANO_API_URL": "https://example.test/api:default",
                "XANO_STOCK_MOVEMENTS_URL": "https://example.test/api:moves",
            },
            clear=True,
        ):
            with patch("app.xano_client.requests.request") as mock_request:
                mock_request.return_value.status_code = 200
                mock_request.return_value.content = b'{}'
                mock_request.return_value.json.return_value = {"movement": {"id": 8}}

                xano_client.ajustar_estoque(
                    token="abc",
                    product_id=10,
                    adjustment_type="entrada",
                    quantity=5,
                    notes="Inventário",
                )
                xano_client.ajustar_estoque(
                    token="abc",
                    product_id=10,
                    adjustment_type="saida",
                    quantity=2,
                )
                xano_client.registrar_perda_ou_avaria(
                    token="abc",
                    product_id=10,
                    movement_type="perda",
                    quantity=3,
                )
                xano_client.registrar_perda_ou_avaria(
                    token="abc",
                    product_id=10,
                    movement_type="avaria",
                    quantity=1,
                )

        urls = [call.kwargs["url"] for call in mock_request.call_args_list]
        self.assertTrue(urls[0].endswith("/stock-movement/adjustment"))
        self.assertTrue(urls[1].endswith("/stock-movement/adjustment"))
        self.assertTrue(urls[2].endswith("/stock-movement/loss"))
        self.assertTrue(urls[3].endswith("/stock-movement/loss"))
        self.assertEqual(
            mock_request.call_args_list[1].kwargs["json"]["adjustment_type"],
            "saida",
        )

    def test_stock_write_validates_types_and_rejects_insufficient_response(self):
        with patch("app.xano_client.requests.request") as mock_request:
            with self.assertRaises(ValueError):
                xano_client.ajustar_estoque(
                    token="abc",
                    product_id=10,
                    adjustment_type="inventario",
                    quantity=1,
                )
            with self.assertRaises(ValueError):
                xano_client.registrar_perda_ou_avaria(
                    token="abc",
                    product_id=10,
                    movement_type="perda",
                    quantity=0,
                )
        mock_request.assert_not_called()

    def test_client_and_supplier_returns_use_contract_payload(self):
        with patch.dict(
            os.environ,
            {
                "XANO_API_URL": "https://example.test/api:default",
                "XANO_STOCK_MOVEMENTS_URL": "https://example.test/api:moves",
            },
            clear=True,
        ):
            with patch("app.xano_client.requests.request") as mock_request:
                mock_request.return_value.status_code = 200
                mock_request.return_value.content = b'{}'
                mock_request.return_value.json.return_value = {"movement": {"id": 9}}

                xano_client.registrar_devolucao(
                    token="abc",
                    product_id=10,
                    return_type="cliente",
                    reference_id=44,
                    quantity=2,
                    restock_condition=True,
                )
                xano_client.registrar_devolucao(
                    token="abc",
                    product_id=10,
                    return_type="fornecedor",
                    reference_id=7,
                    quantity=1,
                    restock_condition=False,
                )

        first_payload = mock_request.call_args_list[0].kwargs["json"]
        second_payload = mock_request.call_args_list[1].kwargs["json"]
        self.assertEqual(first_payload["reference_id"], 44)
        self.assertTrue(first_payload["restock_condition"])
        self.assertNotIn("sale_item_id", first_payload)
        self.assertEqual(second_payload["reference_id"], 7)
        self.assertNotIn("restock_condition", second_payload)

    def test_stock_connection_and_http_errors_are_propagated(self):
        with patch.dict(
            os.environ,
            {
                "XANO_API_URL": "https://example.test/api:default",
                "XANO_STOCK_MOVEMENTS_URL": "https://example.test/api:moves",
            },
            clear=True,
        ):
            with patch("app.xano_client.requests.request") as mock_request:
                mock_request.side_effect = xano_client.requests.RequestException(
                    "timeout"
                )
                with self.assertRaises(xano_client.requests.RequestException):
                    xano_client.ajustar_estoque(
                        token="abc",
                        product_id=10,
                        adjustment_type="saida",
                        quantity=1,
                    )


    def test_sale_payload_validation_and_multiple_items(self):
        key = xano_client.criar_chave_idempotencia_venda()
        payload = xano_client.validar_payload_venda(
            idempotency_key=key,
            sales_channel="loja",
            items=[
                {
                    "product_id": 10,
                    "quantity": 2,
                    "unit_sale_price": 25.5,
                    "discount_amount": 1,
                },
                {
                    "product_id": 11,
                    "quantity": 1,
                    "unit_sale_price": 10,
                },
            ],
            order_number="PED-1",
            sale_date="2026-11-20",
            costs=[
                {"type": "frete_saida", "amount": 12.5},
                {"type": "impostos", "amount": 3},
            ],
        )
        self.assertEqual(payload["idempotency_key"], key)
        self.assertEqual(len(payload["items"]), 2)
        self.assertEqual(len(payload["costs"]), 2)

    def test_sale_validation_rejects_missing_fields_and_invalid_cost_type(self):
        key = xano_client.criar_chave_idempotencia_venda()
        with self.assertRaisesRegex(ValueError, "canal"):
            xano_client.validar_payload_venda(
                idempotency_key=key,
                sales_channel="",
                items=[{
                    "product_id": 10,
                    "quantity": 1,
                    "unit_sale_price": 5,
                }],
            )
        with self.assertRaisesRegex(ValueError, "Tipo de custo"):
            xano_client.validar_payload_venda(
                idempotency_key=key,
                sales_channel="loja",
                items=[{
                    "product_id": 10,
                    "quantity": 1,
                    "unit_sale_price": 5,
                }],
                costs=[{"type": "desconto_inventado", "amount": 1}],
            )

    def test_register_sale_posts_uuid_and_confirmed_result(self):
        with patch.dict(
            os.environ,
            {
                "XANO_API_URL": "https://example.test/api:default",
                "XANO_SALES_URL": "https://example.test/api:sales",
            },
            clear=True,
        ):
            with patch("app.xano_client.requests.request") as mock_request:
                mock_request.return_value.status_code = 200
                mock_request.return_value.content = b'{}'
                mock_request.return_value.json.return_value = {
                    "sale": {"id": 44, "status": "confirmada"},
                }
                key = xano_client.criar_chave_idempotencia_venda()
                payload = xano_client.validar_payload_venda(
                    idempotency_key=key,
                    sales_channel="loja",
                    items=[{
                        "product_id": 10,
                        "quantity": 2,
                        "unit_sale_price": 25,
                        "discount_amount": 5,
                    }],
                )
                result = xano_client.registrar_venda(
                    token="abc",
                    payload=payload,
                )
        self.assertEqual(result["sale"]["id"], 44)
        call = mock_request.call_args
        self.assertEqual(call.kwargs["url"], "https://example.test/api:sales/sale")
        self.assertEqual(call.kwargs["json"]["idempotency_key"], key)
        self.assertEqual(call.kwargs["method"], "POST")

    def test_register_sale_rejects_incomplete_response(self):
        with patch.dict(
            os.environ,
            {
                "XANO_API_URL": "https://example.test/api:default",
                "XANO_SALES_URL": "https://example.test/api:sales",
            },
            clear=True,
        ):
            with patch("app.xano_client.requests.request") as mock_request:
                mock_request.return_value.status_code = 200
                mock_request.return_value.content = b'{}'
                mock_request.return_value.json.return_value = {}
                key = xano_client.criar_chave_idempotencia_venda()
                payload = xano_client.validar_payload_venda(
                    idempotency_key=key,
                    sales_channel="loja",
                    items=[{
                        "product_id": 10,
                        "quantity": 1,
                        "unit_sale_price": 10,
                    }],
                )
                with self.assertRaisesRegex(ValueError, "confirmou"):
                    xano_client.registrar_venda(token="abc", payload=payload)

    def test_sale_history_filters_pagination_and_detail(self):
        with patch.dict(
            os.environ,
            {
                "XANO_API_URL": "https://example.test/api:default",
                "XANO_SALES_URL": "https://example.test/api:sales",
            },
            clear=True,
        ):
            with patch("app.xano_client.requests.request") as mock_request:
                mock_request.return_value.status_code = 200
                mock_request.return_value.content = b'{}'
                mock_request.return_value.json.side_effect = [
                    {
                        "items": [{"id": 44, "status": "confirmada"}],
                        "curPage": 2,
                        "perPage": 20,
                        "total": 21,
                    },
                    {
                        "sale": {
                            "id": 44,
                        },
                        "items": [{"product_id": 10, "quantity": 2}],
                        "costs": [{"cost_type": "frete_saida", "amount": 12}],
                        "financial_summary": {
                            "gross_amount": 40,
                            "discount_amount": 0,
                            "net_revenue": 40,
                            "total_cmv": 20,
                            "total_costs": 12,
                            "result": 8,
                            "profit_margin_percent": 20,
                        },
                    },
                ]
                history = xano_client.listar_vendas(
                    token="abc",
                    sales_channel="loja",
                    order_number="PED-1",
                    status="confirmada",
                    start_date="2026-11-01",
                    end_date="2026-11-20",
                    page=2,
                    per_page=20,
                )
                detail = xano_client.consultar_venda(44, token="abc")

        self.assertEqual(history["items"][0]["id"], 44)
        self.assertEqual(detail["sale"]["id"], 44)
        self.assertEqual(
            mock_request.call_args_list[0].kwargs["params"],
            {
                "sales_channel": "loja",
                "order_number": "PED-1",
                "status": "confirmada",
                "start_date": "2026-11-01",
                "end_date": "2026-11-20",
                "page": 2,
                "per_page": 20,
            },
        )

    def test_sale_history_rejects_unsupported_payload_shape(self):
        with patch.dict(
            os.environ,
            {
                "XANO_API_URL": "https://example.test/api:default",
                "XANO_SALES_URL": "https://example.test/api:sales",
            },
            clear=True,
        ):
            with patch("app.xano_client.requests.request") as mock_request:
                mock_request.return_value.status_code = 200
                mock_request.return_value.content = b'{}'
                mock_request.return_value.json.return_value = {"unexpected": "shape"}
                with self.assertRaisesRegex(ValueError, "paginada"):
                    xano_client.listar_vendas(token="abc", sales_channel="loja")

    def test_sale_history_sends_required_channel_without_optional_filters(self):
        with patch.dict(
            os.environ,
            {
                "XANO_API_URL": "https://example.test/api:default",
                "XANO_SALES_URL": "https://example.test/api:sales",
            },
            clear=True,
        ), patch.object(xano_client.st, "secrets", {}, create=True):
            with patch("app.xano_client.requests.request") as mock_request:
                mock_request.return_value.status_code = 200
                mock_request.return_value.content = b'{"items":[]}'
                mock_request.return_value.json.return_value = {"items": []}

                result = xano_client.listar_vendas(
                    token="sale-token",
                    sales_channel=" loja ",
                )

        self.assertEqual(result["items"], [])
        self.assertEqual(
            mock_request.call_args.kwargs["params"],
            {"sales_channel": "loja", "page": 1, "per_page": 20},
        )
        self.assertEqual(
            mock_request.call_args.kwargs["headers"]["Authorization"],
            "Bearer sale-token",
        )

    def test_sale_history_requires_channel_instead_of_sending_fake_value(self):
        with patch("app.xano_client.requests.request") as mock_request:
            with self.assertRaisesRegex(ValueError, "exige sales_channel"):
                xano_client.listar_vendas(token="sale-token")

        mock_request.assert_not_called()

    def test_sale_history_propagates_http_errors(self):
        response = Mock()
        response.status_code = 400
        response.raise_for_status.side_effect = xano_client.requests.HTTPError(
            "Missing param: sales_channel",
            response=response,
        )
        with patch.dict(
            os.environ,
            {
                "XANO_API_URL": "https://example.test/api:default",
                "XANO_SALES_URL": "https://example.test/api:sales",
            },
            clear=True,
        ), patch.object(xano_client.st, "secrets", {}, create=True), patch(
            "app.xano_client.requests.request",
            return_value=response,
        ):
            with self.assertRaises(xano_client.requests.HTTPError):
                xano_client.listar_vendas(
                    token="sale-token",
                    sales_channel="loja",
                )

    def test_sale_connection_error_preserves_payload_for_recovery(self):
        key = xano_client.criar_chave_idempotencia_venda()
        payload = xano_client.validar_payload_venda(
            idempotency_key=key,
            sales_channel="loja",
            items=[{
                "product_id": 10,
                "quantity": 1,
                "unit_sale_price": 10,
            }],
        )
        with patch.dict(
            os.environ,
            {
                "XANO_API_URL": "https://example.test/api:default",
                "XANO_SALES_URL": "https://example.test/api:sales",
            },
            clear=True,
        ):
            with patch("app.xano_client.requests.request") as mock_request:
                mock_request.side_effect = xano_client.requests.Timeout(
                    "timeout"
                )
                with self.assertRaises(xano_client.requests.Timeout):
                    xano_client.registrar_venda(token="abc", payload=payload)
        self.assertEqual(payload["idempotency_key"], key)
        mock_request.assert_called_once()


if __name__ == "__main__":
    unittest.main()
