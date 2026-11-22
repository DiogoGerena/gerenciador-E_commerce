import os
import unittest
from datetime import datetime, timezone
from unittest.mock import Mock, patch
from uuid import UUID

import requests

import app.xano_client as xano_client


class XanoSalesClientTests(unittest.TestCase):
    SALE_IDEMPOTENCY_KEY = "123e4567-e89b-42d3-a456-426614174000"

    def setUp(self):
        self._env_patch = patch.dict(
            os.environ,
            {"XANO_API_URL": "https://example.test/api:default"},
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
        self.sale_response = {
            "sale": {
                "id": 41,
                "sales_channel": "Canal personalizado",
                "order_number": "PED-41",
            },
            "items": [{"product_id": 7, "quantity": 2}],
            "costs": [{"cost_type": "embalagem", "amount": 1.25}],
            "financial_summary": {
                "gross_amount": 40.0,
                "discount_amount": 2.0,
                "net_revenue": 38.0,
                "total_cmv": 20.0,
                "total_costs": 1.25,
                "result": 16.75,
                "profit_margin_percent": 44.08,
            },
        }
        self.page_response = {
            "itemsReceived": 1,
            "curPage": 1,
            "nextPage": None,
            "prevPage": None,
            "offset": 0,
            "itemsTotal": 1,
            "pageTotal": 1,
            "items": [{"id": 41, "sales_channel": "Canal personalizado"}],
        }

    def tearDown(self):
        self._secrets_patch.stop()
        self._env_patch.stop()

    @staticmethod
    def _response(payload, *, content=b"json"):
        response = Mock()
        response.status_code = 200
        response.content = content
        response.json.return_value = payload
        response.headers = {}
        return response

    def _sale_payload(self, **overrides):
        payload = {
            "idempotency_key": self.SALE_IDEMPOTENCY_KEY,
            "sales_channel": "Canal personalizado",
            "order_number": "PED-41",
            "items": [
                {
                    "product_id": 7,
                    "quantity": 2,
                    "unit_sale_price": 20.0,
                    "discount_amount": 2.0,
                }
            ],
            "costs": [],
        }
        payload.update(overrides)
        return payload

    def test_derives_sales_group_from_configured_xano_origin(self):
        config = xano_client.get_xano_config()
        self.assertEqual(
            config["sales_base_url"],
            "https://example.test/api:EjdVpi9b",
        )

        with patch(
            "app.xano_client.requests.request",
            return_value=self._response(self.sale_response),
        ) as request:
            xano_client.criar_venda(
                "session-token",
                self._sale_payload(),
            )

        self.assertEqual(
            request.call_args.kwargs["url"],
            "https://example.test/api:EjdVpi9b/sale",
        )
        self.assertEqual(
            request.call_args.kwargs["headers"]["Authorization"],
            "Bearer session-token",
        )

    def test_explicit_sales_url_from_environment_takes_priority(self):
        os.environ["XANO_SALES_URL"] = "https://sales.example/api:EjdVpi9b/"
        config = xano_client.get_xano_config()
        self.assertEqual(
            config["sales_base_url"],
            "https://sales.example/api:EjdVpi9b",
        )

    def test_explicit_sales_url_can_come_from_streamlit_secrets(self):
        with patch.object(
            xano_client.st,
            "secrets",
            {
                "XANO_API_URL": "https://example.test/api:default",
                "XANO_SALES_URL": "https://sales.example/api:EjdVpi9b",
            },
            create=True,
        ):
            config = xano_client.get_xano_config()

        self.assertEqual(
            config["sales_base_url"],
            "https://sales.example/api:EjdVpi9b",
        )

    def test_create_sends_only_supported_fields_and_preserves_values(self):
        payload = self._sale_payload(
            sale_date="2026-11-16T22:00:00Z",
            notes="Venda teste",
            costs=[
                {
                    "cost_type": "embalagem",
                    "description": "Caixa",
                    "amount": 1.25,
                },
                {"cost_type": "impostos", "amount": 2},
            ],
        )

        with patch(
            "app.xano_client.requests.request",
            return_value=self._response(self.sale_response),
        ) as request:
            result = xano_client.criar_venda("session-token", payload)

        self.assertEqual(result, self.sale_response)
        call = request.call_args.kwargs
        self.assertEqual(call["method"], "POST")
        self.assertEqual(
            call["url"],
            "https://example.test/api:EjdVpi9b/sale",
        )
        self.assertEqual(
            call["json"],
            {
                "idempotency_key": self.SALE_IDEMPOTENCY_KEY,
                "sales_channel": "Canal personalizado",
                "order_number": "PED-41",
                "sale_date": int(
                    datetime(
                        2026,
                        11,
                        16,
                        22,
                        tzinfo=timezone.utc,
                    ).timestamp()
                    * 1000
                ),
                "notes": "Venda teste",
                "items": [
                    {
                        "product_id": 7,
                        "quantity": 2,
                        "unit_sale_price": 20.0,
                        "discount_amount": 2.0,
                    }
                ],
                "costs": [
                    {
                        "cost_type": "embalagem",
                        "description": "Caixa",
                        "amount": 1.25,
                    },
                    {"cost_type": "impostos", "amount": 2},
                ],
            },
        )

    def test_create_rejects_seconds_timestamp_before_http(self):
        payload = self._sale_payload(sale_date=1773577800)
        with patch("app.xano_client.requests.request") as request:
            with self.assertRaisesRegex(ValueError, "milissegundos"):
                xano_client.criar_venda("session-token", payload)
        request.assert_not_called()

    def test_create_preserves_unix_milliseconds(self):
        timestamp_ms = 1773577800000
        payload = self._sale_payload(sale_date=timestamp_ms)
        with patch(
            "app.xano_client.requests.request",
            return_value=self._response(self.sale_response),
        ) as request:
            xano_client.criar_venda("session-token", payload)

        self.assertEqual(request.call_args.kwargs["json"]["sale_date"], timestamp_ms)

    def test_create_rejects_response_date_in_seconds_as_inconclusive(self):
        response_body = {
            **self.sale_response,
            "sale": {
                **self.sale_response["sale"],
                "sale_date": 1773577800,
            },
        }
        with patch(
            "app.xano_client.requests.request",
            return_value=self._response(response_body),
        ) as request:
            with self.assertRaises(
                xano_client.RespostaVendaInconclusivaError
            ):
                xano_client.criar_venda(
                    "session-token",
                    self._sale_payload(sale_date=1773577800000),
                )

        request.assert_called_once()

    def test_create_omits_optional_fields_but_sends_empty_costs(self):
        payload = self._sale_payload(
            order_number=None,
            sale_date=None,
            notes=None,
            costs=[],
        )
        payload["items"][0]["discount_amount"] = None

        with patch(
            "app.xano_client.requests.request",
            return_value=self._response(self.sale_response),
        ) as request:
            xano_client.criar_venda("session-token", payload)

        self.assertEqual(
            request.call_args.kwargs["json"],
            {
                "idempotency_key": self.SALE_IDEMPOTENCY_KEY,
                "sales_channel": "Canal personalizado",
                "items": [
                    {
                        "product_id": 7,
                        "quantity": 2,
                        "unit_sale_price": 20.0,
                    }
                ],
                "costs": [],
            },
        )

    def test_create_rejects_missing_or_null_costs_before_http(self):
        missing_costs = self._sale_payload()
        missing_costs.pop("costs")
        for payload in (missing_costs, self._sale_payload(costs=None)):
            with self.subTest(payload=payload):
                with patch("app.xano_client.requests.request") as request:
                    with self.assertRaisesRegex(ValueError, "costs.*lista"):
                        xano_client.criar_venda("session-token", payload)
                request.assert_not_called()

    def test_create_supports_multiple_items_and_costs(self):
        payload = self._sale_payload(
            items=[
                {"product_id": 7, "quantity": 2, "unit_sale_price": 20},
                {"product_id": 8, "quantity": 1, "unit_sale_price": 10},
            ],
            costs=[
                {"cost_type": "frete_saida", "amount": 5},
                {"cost_type": "outros", "description": "Taxa", "amount": 1},
            ],
        )
        with patch(
            "app.xano_client.requests.request",
            return_value=self._response(self.sale_response),
        ) as request:
            xano_client.criar_venda("session-token", payload)

        sent = request.call_args.kwargs["json"]
        self.assertEqual(len(sent["items"]), 2)
        self.assertEqual(len(sent["costs"]), 2)

    def test_create_rejects_invalid_payloads_before_http(self):
        invalid_payloads = (
            {},
            self._sale_payload(items=[]),
            self._sale_payload(items=[{"product_id": 1, "quantity": 1}]),
            self._sale_payload(
                items=[
                    {
                        "product_id": 1,
                        "quantity": 0,
                        "unit_sale_price": 1,
                    }
                ]
            ),
            self._sale_payload(
                items=[
                    {
                        "product_id": True,
                        "quantity": 1,
                        "unit_sale_price": 1,
                    }
                ]
            ),
            self._sale_payload(
                items=[
                    {
                        "product_id": 1,
                        "quantity": 1,
                        "unit_sale_price": -0.01,
                    }
                ]
            ),
            self._sale_payload(
                items=[
                    {
                        "product_id": 1,
                        "quantity": 1,
                        "unit_sale_price": 1,
                        "discount_amount": 1.01,
                    }
                ]
            ),
            self._sale_payload(
                items=[
                    {
                        "product_id": 1,
                        "quantity": 1,
                        "unit_sale_price": 1,
                        "discount_amount": float("inf"),
                    }
                ]
            ),
            self._sale_payload(
                items=[
                    {
                        "product_id": 1,
                        "quantity": 1,
                        "unit_sale_price": 1,
                        "description": "extra",
                    }
                ]
            ),
            self._sale_payload(
                costs=[{"cost_type": "inventado", "amount": 1}]
            ),
            self._sale_payload(
                costs=[{"cost_type": "impostos", "amount": -1}]
            ),
            self._sale_payload(customer_id=12),
            self._sale_payload(idempotency_key="not-a-uuid"),
            self._sale_payload(
                idempotency_key="123e4567-e89b-12d3-a456-426614174000"
            ),
            self._sale_payload(idempotency_key=None),
        )

        with patch("app.xano_client.requests.request") as request:
            for payload in invalid_payloads:
                with self.subTest(payload=payload):
                    with self.assertRaises(ValueError):
                        xano_client.criar_venda("session-token", payload)

        request.assert_not_called()

    def test_create_requires_uuid_v4_key_at_sale_level(self):
        payload = self._sale_payload()
        payload["items"][0]["idempotency_key"] = self.SALE_IDEMPOTENCY_KEY
        with patch("app.xano_client.requests.request") as request:
            with self.assertRaisesRegex(ValueError, "campos não aceitos"):
                xano_client.criar_venda("session-token", payload)
        request.assert_not_called()

        payload = self._sale_payload()
        with patch(
            "app.xano_client.requests.request",
            return_value=self._response(self.sale_response),
        ) as request:
            xano_client.criar_venda("session-token", payload)
        sent = request.call_args.kwargs["json"]
        self.assertEqual(sent["idempotency_key"], self.SALE_IDEMPOTENCY_KEY)
        self.assertEqual(UUID(sent["idempotency_key"]).version, 4)
        self.assertNotIn("idempotency_key", sent["items"][0])

    def test_create_requires_session_token_without_http(self):
        with patch("app.xano_client.requests.request") as request:
            with self.assertRaisesRegex(ValueError, "sessão"):
                xano_client.criar_venda(None, self._sale_payload())
        request.assert_not_called()

    def test_create_rejects_incomplete_response_as_unconfirmed(self):
        invalid_responses = (
            None,
            "invalid response",
            {},
            {**self.sale_response, "sale": None},
            {**self.sale_response, "sale": {"id": 0}},
            {**self.sale_response, "items": None},
            {**self.sale_response, "costs": None},
            {
                **self.sale_response,
                "financial_summary": {
                    key: value
                    for key, value in self.sale_response[
                        "financial_summary"
                    ].items()
                    if key != "total_cmv"
                },
            },
            {
                **self.sale_response,
                "financial_summary": {
                    **self.sale_response["financial_summary"],
                    "result": "not numeric",
                },
            },
        )
        with patch("app.xano_client.requests.request") as request:
            for payload in invalid_responses:
                with self.subTest(payload=payload):
                    request.return_value = self._response(payload)
                    with self.assertRaises(
                        xano_client.RespostaVendaInconclusivaError
                    ):
                        xano_client.criar_venda(
                            "session-token",
                            self._sale_payload(),
                        )

    def test_create_malformed_json_is_not_success(self):
        response = self._response(None)
        response.json.side_effect = ValueError("invalid json")
        response.text = "{invalid-json"

        with patch(
            "app.xano_client.requests.request",
            return_value=response,
        ):
            with self.assertRaises(
                xano_client.RespostaVendaInconclusivaError
            ):
                xano_client.criar_venda(
                    "session-token",
                    self._sale_payload(),
                )

    def test_create_timeout_and_connection_failure_are_inconclusive_without_retry(self):
        for error in (
            requests.Timeout("timed out"),
            requests.ConnectionError("offline"),
        ):
            with self.subTest(error=error):
                with patch(
                    "app.xano_client.requests.request",
                    side_effect=error,
                ) as request:
                    with self.assertRaises(
                        xano_client.OperacaoVendaInconclusivaError
                    ) as caught:
                        xano_client.criar_venda(
                            "session-token",
                            self._sale_payload(),
                        )

                self.assertIs(caught.exception.__cause__, error)
                request.assert_called_once()

    def test_http_errors_during_create_are_propagated_without_retry(self):
        response = self._response({"message": "invalid"}, content=b"error")
        failure = requests.HTTPError(response=response)
        response.raise_for_status.side_effect = failure
        with patch(
            "app.xano_client.requests.request",
            return_value=response,
        ) as request:
            with self.assertRaises(requests.HTTPError):
                xano_client.criar_venda(
                    "session-token",
                    self._sale_payload(),
                )
        request.assert_called_once()

    def test_list_requires_channel_and_defaults_to_documented_pagination(self):
        with patch(
            "app.xano_client.requests.request",
            return_value=self._response(self.page_response),
        ) as request:
            result = xano_client.listar_vendas(
                "session-token",
                sales_channel="Loja",
            )

        self.assertEqual(result, self.page_response)
        call = request.call_args.kwargs
        self.assertEqual(call["method"], "GET")
        self.assertEqual(
            call["url"],
            "https://example.test/api:EjdVpi9b/sale",
        )
        self.assertEqual(
            call["params"],
            {
                "sales_channel": "Loja",
                "page": 1,
                "per_page": 20,
            },
        )
        self.assertEqual(
            call["headers"]["Authorization"],
            "Bearer session-token",
        )

    def test_list_without_channel_fails_before_http(self):
        with patch("app.xano_client.requests.request") as request:
            with self.assertRaisesRegex(ValueError, "sales_channel é obrigatório"):
                xano_client.listar_vendas("session-token")
        request.assert_not_called()

    def test_list_forwards_filters_and_dates_without_conversion(self):
        with patch(
            "app.xano_client.requests.request",
            return_value=self._response(self.page_response),
        ) as request:
            xano_client.listar_vendas(
                "session-token",
                sales_channel="  Shopee  ",
                order_number="PED-22",
                status="registrada",
                start_date="2026-11-01T00:00:00Z",
                end_date="2026-11-16T23:59:59Z",
                page=3,
                per_page=100,
            )

        self.assertEqual(
            request.call_args.kwargs["params"],
            {
                "page": 3,
                "per_page": 100,
                "sales_channel": "Shopee",
                "order_number": "PED-22",
                "status": "registrada",
                "start_date": "2026-11-01T00:00:00Z",
                "end_date": "2026-11-16T23:59:59Z",
            },
        )

    def test_list_rejects_invalid_filters_and_pagination_before_http(self):
        invalid_options = (
            {"page": 0},
            {"page": True},
            {"per_page": 0},
            {"per_page": 101},
            {"per_page": False},
            {"sales_channel": ""},
            {"sales_channel": "   "},
            {"status": "pending"},
            {"status": []},
            {"sales_channel": 5},
            {"order_number": []},
        )
        with patch("app.xano_client.requests.request") as request:
            for options in invalid_options:
                with self.subTest(options=options):
                    with self.assertRaises(ValueError):
                        xano_client.listar_vendas(
                            "session-token",
                            **options,
                        )
        request.assert_not_called()

    def test_list_rejects_incomplete_or_malformed_envelopes(self):
        invalid_responses = (
            None,
            [],
            {},
            {**self.page_response, "items": {}},
            {**self.page_response, "curPage": True},
            {
                key: value
                for key, value in self.page_response.items()
                if key != "itemsTotal"
            },
        )
        with patch("app.xano_client.requests.request") as request:
            for payload in invalid_responses:
                with self.subTest(payload=payload):
                    request.return_value = self._response(payload)
                    with self.assertRaises(ValueError):
                        xano_client.listar_vendas(
                            "session-token",
                            sales_channel="Loja",
                        )

    def test_list_requires_session_token(self):
        with patch("app.xano_client.requests.request") as request:
            with self.assertRaisesRegex(ValueError, "sessão"):
                xano_client.listar_vendas(None)
        request.assert_not_called()

    def test_get_detail_uses_id_and_validates_matching_record(self):
        with patch(
            "app.xano_client.requests.request",
            return_value=self._response(self.sale_response),
        ) as request:
            result = xano_client.consultar_venda("session-token", "41")

        self.assertEqual(result, self.sale_response)
        call = request.call_args.kwargs
        self.assertEqual(call["method"], "GET")
        self.assertEqual(
            call["url"],
            "https://example.test/api:EjdVpi9b/sale/41",
        )
        self.assertEqual(
            call["headers"]["Authorization"],
            "Bearer session-token",
        )

    def test_get_detail_rejects_invalid_id_without_http(self):
        with patch("app.xano_client.requests.request") as request:
            for sale_id in (None, 0, -1, True, "not-an-id"):
                with self.subTest(sale_id=sale_id):
                    with self.assertRaises(ValueError):
                        xano_client.consultar_venda(
                            "session-token",
                            sale_id,
                        )
        request.assert_not_called()

    def test_get_detail_rejects_incomplete_or_mismatched_response(self):
        invalid_responses = (
            {},
            {**self.sale_response, "sale": {"id": 42}},
            {**self.sale_response, "financial_summary": None},
            {**self.sale_response, "items": [{"product_id": 1}, None]},
        )
        with patch("app.xano_client.requests.request") as request:
            for payload in invalid_responses:
                with self.subTest(payload=payload):
                    request.return_value = self._response(payload)
                    with self.assertRaises(
                        xano_client.RespostaVendaInconclusivaError
                    ):
                        xano_client.consultar_venda(
                            "session-token",
                            41,
                        )

    def test_get_detail_http_error_is_propagated(self):
        response = self._response({"message": "not found"}, content=b"error")
        failure = requests.HTTPError(response=response)
        response.raise_for_status.side_effect = failure
        with patch(
            "app.xano_client.requests.request",
            return_value=response,
        ) as request:
            with self.assertRaises(requests.HTTPError):
                xano_client.consultar_venda("session-token", 404)
        request.assert_called_once()


if __name__ == "__main__":
    unittest.main()
