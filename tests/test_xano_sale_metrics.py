import os
import unittest
from decimal import Decimal
from unittest.mock import Mock, patch

import requests

import app.xano_client as xano_client


def metricas_validas(**overrides):
    metricas = {
        "sales_count": 2,
        "items_count": 2,
        "gross_amount": 299.98,
        "discount_amount": 0,
        "net_revenue": 299.98,
        "total_cmv": 27.89,
        "total_costs": 10,
        "result": 262.09,
        "profit_margin_percent": 87.37,
        "average_ticket": 149.99,
    }
    metricas.update(overrides)
    return metricas


class SaleMetricsTestCase(unittest.TestCase):
    def consultar_com_resposta(self, payload, **filtros):
        response = Mock()
        response.status_code = 200
        response.content = b"{}" if payload is not None else b""
        response.json.return_value = payload
        with patch.dict(
            os.environ,
            {
                "XANO_API_URL": "https://example.test/api:default",
                "XANO_SALES_URL": "https://example.test/api:EjdVpi9b",
            },
            clear=True,
        ):
            with patch.object(xano_client.st, "secrets", {}, create=True):
                with patch(
                    "app.xano_client.requests.request",
                    return_value=response,
                ) as request:
                    metricas = xano_client.consultar_metricas_vendas(
                        token="jwt-metricas",
                        **filtros,
                    )
        return metricas, request

    def test_sends_supported_filters_to_sales_endpoint_with_bearer_token(self):
        _, request = self.consultar_com_resposta(
            metricas_validas(),
            sales_channel=" loja ",
            status=" confirmada ",
            start_date="2026-11-01",
            end_date="2026-11-20",
            product_id=10,
            category_id=3,
        )

        self.assertEqual(
            request.call_args.kwargs["url"],
            "https://example.test/api:EjdVpi9b/sale/metrics",
        )
        self.assertEqual(
            request.call_args.kwargs["headers"]["Authorization"],
            "Bearer jwt-metricas",
        )
        self.assertEqual(
            request.call_args.kwargs["params"],
            {
                "sales_channel": "loja",
                "status": "confirmada",
                "start_date": "2026-11-01",
                "end_date": "2026-11-20",
                "product_id": 10,
                "category_id": 3,
            },
        )

    def test_converts_valid_numeric_metrics_and_preserves_metadata(self):
        payload = metricas_validas(period={"start_date": "2026-11-01"}, filters={})
        metricas, _ = self.consultar_com_resposta(payload)

        self.assertEqual(metricas["sales_count"], 2)
        self.assertEqual(metricas["items_count"], 2)
        self.assertEqual(metricas["gross_amount"], Decimal("299.98"))
        self.assertEqual(metricas["total_cmv"], Decimal("27.89"))
        self.assertEqual(metricas["profit_margin_percent"], Decimal("87.37"))
        self.assertEqual(metricas["period"], payload["period"])
        self.assertEqual(metricas["filters"], payload["filters"])

    def test_preserves_null_values_instead_of_substituting_zero(self):
        payload = metricas_validas(
            discount_amount=None,
            profit_margin_percent=None,
            average_ticket=None,
        )
        metricas, _ = self.consultar_com_resposta(payload)

        self.assertIsNone(metricas["discount_amount"])
        self.assertIsNone(metricas["profit_margin_percent"])
        self.assertIsNone(metricas["average_ticket"])

    def test_returns_real_zero_sales_metrics_for_empty_period(self):
        payload = metricas_validas(
            sales_count=0,
            items_count=0,
            gross_amount=0,
            discount_amount=0,
            net_revenue=0,
            total_cmv=0,
            total_costs=0,
            result=0,
            profit_margin_percent=None,
            average_ticket=None,
        )
        metricas, _ = self.consultar_com_resposta(payload)

        self.assertEqual(metricas["sales_count"], 0)
        self.assertEqual(metricas["items_count"], 0)
        self.assertEqual(metricas["gross_amount"], Decimal("0"))
        self.assertIsNone(metricas["average_ticket"])

    def test_rejects_empty_or_invalid_payload(self):
        for payload in (None, {}, [], {"sales_count": 1}):
            with self.subTest(payload=payload):
                with self.assertRaises(ValueError):
                    self.consultar_com_resposta(payload)

    def test_rejects_non_numeric_metrics(self):
        with self.assertRaisesRegex(ValueError, "não é numérico"):
            self.consultar_com_resposta(
                metricas_validas(net_revenue="não numérico")
            )

    def test_http_errors_are_not_replaced_with_zero_metrics(self):
        response = Mock()
        response.status_code = 404
        response.raise_for_status.side_effect = requests.HTTPError(
            "HTTP 404",
            response=response,
        )
        with patch.dict(
            os.environ,
            {
                "XANO_API_URL": "https://example.test/api:default",
                "XANO_SALES_URL": "https://example.test/api:EjdVpi9b",
            },
            clear=True,
        ), patch.object(xano_client.st, "secrets", {}, create=True), patch(
            "app.xano_client.requests.request",
            return_value=response,
        ):
            with self.assertRaises(requests.HTTPError):
                xano_client.consultar_metricas_vendas(token="jwt-metricas")

    def test_connection_errors_are_propagated(self):
        with patch.dict(
            os.environ,
            {
                "XANO_API_URL": "https://example.test/api:default",
                "XANO_SALES_URL": "https://example.test/api:EjdVpi9b",
            },
            clear=True,
        ), patch.object(xano_client.st, "secrets", {}, create=True), patch(
            "app.xano_client.requests.request",
            side_effect=requests.ConnectionError("indisponível"),
        ):
            with self.assertRaises(requests.ConnectionError):
                xano_client.consultar_metricas_vendas(token="jwt-metricas")


if __name__ == "__main__":
    unittest.main()
