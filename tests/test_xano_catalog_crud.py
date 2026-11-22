import unittest
from unittest.mock import patch

import requests

import app.xano_client as xano_client


def product_record(**overrides):
    record = {
        "id": 12,
        "name": "Caneca",
        "category_id": 4,
        "min_stock": 3,
        "sale_price": 12.25,
        "status": "ativo",
        "sku": "CAN-12",
        "description": None,
        "stock_quantity": 8,
        "average_cost": 7.5,
    }
    record.update(overrides)
    return record


class ProductCrudClientTests(unittest.TestCase):
    def test_get_product_by_id_returns_complete_record(self):
        record = product_record(description="Cerâmica")
        with patch.object(xano_client, "xano_request", return_value=record) as request:
            result = xano_client.consultar_produto("session-token", 12)

        self.assertEqual(result, record)
        request.assert_called_once_with("GET", "/product/12", token="session-token")

    def test_get_product_rejects_incomplete_or_malformed_record(self):
        for response in (
            None,
            [],
            {},
            {"id": 12},
            {"id": 12, "name": "Caneca"},
            product_record(id=13),
            product_record(name=""),
            product_record(category_id=None),
            product_record(min_stock=-1),
            product_record(sale_price=float("nan")),
            product_record(status="pending"),
            product_record(status=[]),
            product_record(stock_quantity=None),
            product_record(average_cost=None),
            product_record(stock_quantity="invalid"),
        ):
            with self.subTest(response=response):
                with patch.object(xano_client, "xano_request", return_value=response):
                    with self.assertRaises(
                        xano_client.RespostaOperacaoInconclusivaError
                    ):
                        xano_client.consultar_produto("session-token", 12)

    def test_get_product_allows_absent_or_null_optional_fields(self):
        complete = product_record()
        optional_fields = ("sku", "description")
        absent = dict(complete)
        null_values = dict(complete)
        for field in optional_fields:
            absent.pop(field)
            null_values[field] = None
        responses = (absent, null_values)

        for response in responses:
            with self.subTest(response=response):
                with patch.object(
                    xano_client,
                    "xano_request",
                    return_value=response,
                ):
                    result = xano_client.consultar_produto("session-token", 12)

                self.assertEqual(result, response)

    def test_get_product_propagates_404_and_connection_errors(self):
        for failure in (
            requests.HTTPError(response=type("Response", (), {"status_code": 404})()),
            requests.ConnectionError("offline"),
        ):
            with self.subTest(failure=type(failure).__name__):
                with patch.object(xano_client, "xano_request", side_effect=failure):
                    with self.assertRaises(type(failure)):
                        xano_client.consultar_produto("session-token", 12)

    def test_patch_product_sends_only_supported_non_null_fields(self):
        record = product_record(name="Caneca nova")
        with patch.object(xano_client, "xano_request", return_value=record) as request:
            result = xano_client.editar_produto(
                "session-token",
                12,
                name=" Caneca nova ",
                sku=None,
                category_id=4,
                sale_price=12.25,
                min_stock=3,
                status="ativo",
            )

        self.assertEqual(result, record)
        request.assert_called_once_with(
            "PATCH",
            "/product/12",
            token="session-token",
            json={
                "name": "Caneca nova",
                "category_id": 4,
                "sale_price": 12.25,
                "min_stock": 3,
                "status": "ativo",
            },
        )
        self.assertNotIn("stock_quantity", request.call_args.kwargs["json"])
        self.assertNotIn("average_cost", request.call_args.kwargs["json"])

    def test_patch_product_omits_nulls_and_rejects_forbidden_or_empty_payloads(self):
        record = product_record()
        with patch.object(xano_client, "xano_request", return_value=record) as request:
            xano_client.editar_produto(
                "session-token",
                12,
                name=None,
                sku="",
            )
        self.assertEqual(request.call_args.kwargs["json"], {"sku": ""})

        for fields in (
            {"stock_quantity": 3},
            {"average_cost": 12.0},
            {"description": "not editable"},
            {"name": None},
        ):
            with self.subTest(fields=fields):
                with patch.object(xano_client, "xano_request") as request:
                    with self.assertRaises(ValueError):
                        xano_client.editar_produto(
                            "session-token",
                            12,
                            **fields,
                        )
                request.assert_not_called()

    def test_patch_product_rejects_invalid_fields_and_status_mismatch(self):
        invalid_cases = (
            {"sale_price": -1},
            {"min_stock": -1},
            {"category_id": True},
            {"status": "pending"},
        )
        for fields in invalid_cases:
            with self.subTest(fields=fields):
                with patch.object(xano_client, "xano_request") as request:
                    with self.assertRaises(ValueError):
                        xano_client.editar_produto(
                            "session-token",
                            12,
                            **fields,
                        )
                request.assert_not_called()

        with patch.object(
            xano_client,
            "xano_request",
            return_value=product_record(status="ativo"),
        ):
            with self.assertRaises(xano_client.RespostaOperacaoInconclusivaError):
                xano_client.editar_produto("session-token", 12, status="inativo")

    def test_patch_product_rejects_incomplete_response(self):
        with patch.object(
            xano_client,
            "xano_request",
            return_value={"id": 12},
        ) as request:
            with self.assertRaises(
                xano_client.RespostaOperacaoInconclusivaError
            ):
                xano_client.editar_produto("session-token", 12, name="Caneca")

        request.assert_called_once_with(
            "PATCH",
            "/product/12",
            token="session-token",
            json={"name": "Caneca"},
        )

    def test_deactivate_product_is_bodyless_and_confirms_inactive_record(self):
        record = product_record(status="inativo")
        with patch.object(xano_client, "xano_request", return_value=record) as request:
            result = xano_client.inativar_produto("session-token", 12)

        self.assertEqual(result, record)
        request.assert_called_once_with(
            "PATCH",
            "/product/12/deactivate",
            token="session-token",
        )


class SupplierCrudClientTests(unittest.TestCase):
    def test_get_supplier_by_id_returns_complete_record(self):
        record = {
            "id": 29,
            "name": "Fornecedor",
            "contact_name": "Contato",
            "cnpj": "04252011000110",
            "email": "supplier@example.test",
            "phone": "11999990000",
            "status": "ativo",
        }
        with patch.object(xano_client, "xano_request", return_value=record) as request:
            result = xano_client.consultar_fornecedor("session-token", 29)

        self.assertEqual(result, record)
        request.assert_called_once_with("GET", "/supplier/29", token="session-token")

    def test_create_supplier_sends_confirmed_fields_and_omits_empty_optional_values(self):
        record = {"id": 29, "name": "Fornecedor", "status": "ativo"}
        with patch.object(xano_client, "xano_request", return_value=record) as request:
            result = xano_client.criar_fornecedor(
                "session-token",
                name=" Fornecedor ",
                contact_name=" ",
                cnpj="",
                email="",
                phone="11999990000",
            )

        self.assertEqual(result, record)
        request.assert_called_once_with(
            "POST",
            "/supplier",
            token="session-token",
            json={"name": "Fornecedor", "phone": "11999990000"},
        )

    def test_create_supplier_requires_name_and_validates_cnpj(self):
        for values in (
            {"name": " "},
            {"name": "Fornecedor", "cnpj": "00.000.000/0000-00"},
        ):
            with self.subTest(values=values):
                with patch.object(xano_client, "xano_request") as request:
                    with self.assertRaises(ValueError):
                        xano_client.criar_fornecedor("session-token", **values)
                request.assert_not_called()

    def test_create_supplier_requires_backend_default_active_status(self):
        with patch.object(
            xano_client,
            "xano_request",
            return_value={"id": 29, "name": "Fornecedor"},
        ):
            with self.assertRaises(
                xano_client.RespostaOperacaoInconclusivaError
            ):
                xano_client.criar_fornecedor(
                    "session-token",
                    name="Fornecedor",
                )

    def test_create_supplier_duplicate_and_invalid_email_errors_propagate(self):
        for message in (
            "Já existe um fornecedor cadastrado com este CNPJ.",
            "Invalid email",
        ):
            response = type(
                "Response",
                (),
                {
                    "status_code": 400,
                    "json": lambda self, message=message: {"message": message},
                },
            )()
            error = requests.HTTPError(response=response)
            with self.subTest(message=message):
                with patch.object(xano_client, "xano_request", side_effect=error):
                    with self.assertRaises(requests.HTTPError):
                        xano_client.criar_fornecedor(
                            "session-token",
                            name="Fornecedor",
                        )

    def test_patch_supplier_omits_nulls_and_sends_only_allowed_fields(self):
        record = {"id": 29, "name": "Fornecedor Atualizado", "status": "ativo"}
        with patch.object(xano_client, "xano_request", return_value=record) as request:
            result = xano_client.editar_fornecedor(
                "session-token",
                29,
                name="Fornecedor Atualizado",
                contact_name=None,
                phone="11999990000",
            )

        self.assertEqual(result, record)
        request.assert_called_once_with(
            "PATCH",
            "/supplier/29",
            token="session-token",
            json={"name": "Fornecedor Atualizado", "phone": "11999990000"},
        )

    def test_patch_supplier_omits_empty_cnpj_and_validates_status(self):
        record = {"id": 29, "name": "Fornecedor", "status": "inativo"}
        with patch.object(xano_client, "xano_request", return_value=record) as request:
            xano_client.editar_fornecedor(
                "session-token",
                29,
                cnpj="",
                status="inativo",
            )
        self.assertEqual(request.call_args.kwargs["json"], {"status": "inativo"})

        with patch.object(xano_client, "xano_request") as request:
            with self.assertRaises(ValueError):
                xano_client.editar_fornecedor(
                    "session-token",
                    29,
                    cnpj="123",
                )
        request.assert_not_called()

    def test_deactivate_supplier_is_bodyless_and_confirms_inactive_record(self):
        record = {"id": 29, "name": "Fornecedor", "status": "inativo"}
        with patch.object(xano_client, "xano_request", return_value=record) as request:
            result = xano_client.inativar_fornecedor("session-token", 29)

        self.assertEqual(result, record)
        request.assert_called_once_with(
            "PATCH",
            "/supplier/29/deactivate",
            token="session-token",
        )

    def test_supplier_operations_propagate_http_and_connection_failures(self):
        failures = (
            requests.HTTPError(response=type("Response", (), {"status_code": 401})()),
            requests.HTTPError(response=type("Response", (), {"status_code": 403})()),
            requests.HTTPError(response=type("Response", (), {"status_code": 404})()),
            requests.ConnectionError("offline"),
        )
        for failure in failures:
            with self.subTest(failure=type(failure).__name__):
                with patch.object(xano_client, "xano_request", side_effect=failure):
                    with self.assertRaises(type(failure)):
                        xano_client.consultar_fornecedor("session-token", 29)


if __name__ == "__main__":
    unittest.main()
