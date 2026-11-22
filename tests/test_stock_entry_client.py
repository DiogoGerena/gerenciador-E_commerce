import os
import unittest
from datetime import date
from unittest.mock import Mock, patch

import requests

import app.xano_client as xano_client


class StockEntryClientTests(unittest.TestCase):
    def setUp(self):
        self.payload = {
            "idempotency_key": "8c0d4aa1-5c23-4d4a-ae15-7d3dfdfb4b20",
            "product_id": 14,
            "supplier_id": 29,
            "quantity": 3,
            "unit_purchase_cost": 8.75,
            "entry_date": "2026-11-03",
            "invoice_number": "NF-123",
            "notes": "Compra mensal",
        }
        self.confirmation = {
            "entry": {"id": 101},
            "movement": {"id": 202},
            "stock_quantity": 18,
            "average_cost": 7.5,
        }
        self._secrets_patch = patch.object(
            xano_client.st,
            "secrets",
            {"XANO_API_URL": "https://example.test/api:resources"},
            create=True,
        )
        self._secrets_patch.start()
        self._env_patch = patch.dict(
            os.environ,
            {"XANO_API_URL": "https://example.test/api:resources"},
            clear=True,
        )
        self._env_patch.start()

    def tearDown(self):
        self._env_patch.stop()
        self._secrets_patch.stop()

    def _response(self, payload=None, *, status_code=201, content=b"response"):
        response = Mock()
        response.status_code = status_code
        response.content = content
        response.json.return_value = payload
        response.headers = {}
        return response

    def _submit(self, **overrides):
        fields = {**self.payload, **overrides}
        return xano_client.criar_entrada_estoque(
            "session-token",
            **fields,
        )

    def test_posts_confirmed_url_payload_and_session_token(self):
        with patch(
            "app.xano_client.requests.request",
            return_value=self._response(self.confirmation),
        ) as request:
            result = self._submit(
                entry_date=date(2026, 11, 3),
                inbound_freight=12.5,
            )

        self.assertEqual(result, self.confirmation)
        call = request.call_args.kwargs
        self.assertEqual(call["method"], "POST")
        self.assertEqual(call["url"], xano_client.STOCK_ENTRY_URL)
        self.assertEqual(
            call["json"],
            {**self.payload, "inbound_freight": 12.5},
        )
        self.assertEqual(call["headers"]["Authorization"], "Bearer session-token")

    def test_omits_optional_costs_when_not_provided(self):
        with patch(
            "app.xano_client.requests.request",
            return_value=self._response(self.confirmation),
        ) as request:
            self._submit()

        self.assertEqual(request.call_args.kwargs["json"], self.payload)
        self.assertNotIn("inbound_freight", request.call_args.kwargs["json"])
        self.assertNotIn(
            "other_acquisition_costs",
            request.call_args.kwargs["json"],
        )

    def test_rejects_invalid_values_without_request(self):
        invalid_values = (
            {"idempotency_key": "not-a-uuid"},
            {"idempotency_key": "11111111-1111-1111-8111-111111111111"},
            {"quantity": 0},
            {"quantity": -1},
            {"unit_purchase_cost": -0.01},
            {"unit_purchase_cost": float("nan")},
            {"inbound_freight": -1},
            {"other_acquisition_costs": float("inf")},
            {"product_id": 0},
            {"supplier_id": True},
            {"entry_date": "not-a-date"},
            {"invoice_number": None},
            {"notes": None},
        )
        with patch("app.xano_client.requests.request") as request:
            for values in invalid_values:
                with self.subTest(values=values):
                    with self.assertRaises(ValueError):
                        self._submit(**values)

        request.assert_not_called()

    def test_requires_session_token_without_request(self):
        with patch("app.xano_client.requests.request") as request:
            with self.assertRaisesRegex(ValueError, "sessão"):
                xano_client.criar_entrada_estoque(None, **self.payload)

        request.assert_not_called()

    def test_accepts_zero_costs_and_serializes_them_as_numbers(self):
        with patch(
            "app.xano_client.requests.request",
            return_value=self._response(self.confirmation),
        ) as request:
            self._submit(inbound_freight=0, other_acquisition_costs=0)

        payload = request.call_args.kwargs["json"]
        self.assertEqual(payload["inbound_freight"], 0.0)
        self.assertEqual(payload["other_acquisition_costs"], 0.0)

    def test_requires_full_confirmation_structure(self):
        invalid_responses = (
            None,
            "not JSON",
            {},
            {**self.confirmation, "entry": None},
            {**self.confirmation, "movement": None},
            {**self.confirmation, "stock_quantity": None},
            {**self.confirmation, "average_cost": "7.5"},
        )
        with patch("app.xano_client.requests.request") as request:
            for payload in invalid_responses:
                with self.subTest(payload=payload):
                    response = self._response(
                        payload,
                        content=b"" if payload is None else b"response",
                    )
                    request.return_value = response
                    with self.assertRaises(
                        xano_client.RespostaEntradaEstoqueInconclusivaError
                    ):
                        self._submit()

            malformed = self._response(
                content=b"{invalid-json",
            )
            malformed.json.side_effect = ValueError("invalid JSON")
            malformed.text = "{invalid-json"
            request.return_value = malformed
            with self.assertRaises(
                xano_client.RespostaEntradaEstoqueInconclusivaError
            ):
                self._submit()

    def test_rejects_non_success_http_status_without_confirmation(self):
        with patch(
            "app.xano_client.requests.request",
            return_value=self._response(self.confirmation, status_code=302),
        ):
            with self.assertRaises(
                xano_client.RespostaEntradaEstoqueInconclusivaError
            ):
                self._submit()

    def test_propagates_http_errors_with_status(self):
        for status_code in (400, 401, 403, 500):
            with self.subTest(status_code=status_code):
                response = self._response(
                    {"message": "request rejected"},
                    status_code=status_code,
                )
                failure = requests.HTTPError(response=response)
                response.raise_for_status.side_effect = failure
                with patch(
                    "app.xano_client.requests.request",
                    return_value=response,
                ):
                    with self.assertRaises(requests.HTTPError) as caught:
                        self._submit()

                self.assertEqual(caught.exception.response.status_code, status_code)

    def test_propagates_connection_failure_without_retry(self):
        with patch(
            "app.xano_client.requests.request",
            side_effect=requests.ConnectionError("offline"),
        ) as request:
            with self.assertRaises(requests.ConnectionError):
                self._submit()

        request.assert_called_once()

    def test_lists_active_suppliers_from_confirmed_endpoint_with_session_token(self):
        suppliers = [
            {
                "id": 29,
                "name": "Fornecedor Real",
                "contact_name": "Contato",
                "cnpj": "12345678000190",
                "email": "supplier@example.test",
                "phone": "11999990000",
                "status": "ativo",
            }
        ]
        with patch(
            "app.xano_client.requests.request",
            return_value=self._response(suppliers, status_code=200),
        ) as request:
            result = xano_client.listar_fornecedores(
                token="session-token",
                status="ativo",
            )

        self.assertEqual(
            result,
            [
                {
                    "id": 29,
                    "name": "Fornecedor Real",
                    "cnpj": "12345678000190",
                    "contact_name": "Contato",
                    "email": "supplier@example.test",
                    "phone": "11999990000",
                    "status": "ativo",
                }
            ],
        )
        call = request.call_args.kwargs
        self.assertEqual(call["method"], "GET")
        self.assertEqual(call["url"], xano_client.SUPPLIERS_URL)
        self.assertEqual(call["params"], {"status": "ativo"})
        self.assertEqual(call["headers"]["Authorization"], "Bearer session-token")

    def test_supplier_list_preserves_empty_list_and_rejects_malformed_response(self):
        with patch(
            "app.xano_client.requests.request",
            return_value=self._response([], status_code=200),
        ):
            self.assertEqual(
                xano_client.listar_fornecedores(
                    token="session-token",
                    status="ativo",
                ),
                [],
            )

        empty_envelope = self._response({"suppliers": []}, status_code=200)
        with patch(
            "app.xano_client.requests.request",
            return_value=empty_envelope,
        ):
            self.assertEqual(
                xano_client.listar_fornecedores(
                    token="session-token",
                    status="ativo",
                ),
                [],
            )

        malformed = self._response({"unexpected": []}, status_code=200)
        with patch(
            "app.xano_client.requests.request",
            return_value=malformed,
        ):
            with self.assertRaisesRegex(ValueError, "lista"):
                xano_client.listar_fornecedores(
                    token="session-token",
                    status="ativo",
                )

    def test_supplier_list_propagates_http_and_connection_failures(self):
        response = self._response({"message": "Unauthorized"}, status_code=401)
        response.raise_for_status.side_effect = requests.HTTPError(response=response)
        with patch(
            "app.xano_client.requests.request",
            return_value=response,
        ):
            with self.assertRaises(requests.HTTPError):
                xano_client.listar_fornecedores(
                    token="session-token",
                    status="ativo",
                )

        with patch(
            "app.xano_client.requests.request",
            side_effect=requests.ConnectionError("offline"),
        ) as request:
            with self.assertRaises(requests.ConnectionError):
                xano_client.listar_fornecedores(
                    token="session-token",
                    status="ativo",
                )
        request.assert_called_once()


if __name__ == "__main__":
    unittest.main()
