import sys
import time
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

import requests
from streamlit.testing.v1 import AppTest

import app.xano_client as xano_client


class FinancialDashboardTestCase(unittest.TestCase):
    def test_dashboard_no_sales_filters_values_and_api_error_states(self):
        app = AppTest.from_file(
            str(Path(__file__).resolve().parents[1] / "app" / "Home.py")
        )
        app.session_state["auth_token"] = "jwt-dashboard"
        app.session_state["auth_user"] = {
            "email": "teste@example.test",
            "role": "Adm",
        }
        app.session_state["auth_at"] = time.time()
        metricas_sem_vendas = {
            "sales_count": 0,
            "items_count": 0,
            "gross_amount": 0,
            "discount_amount": 0,
            "net_revenue": 0,
            "total_cmv": 0,
            "total_costs": 0,
            "result": 0,
            "profit_margin_percent": None,
            "average_ticket": None,
        }
        metricas_reais = {
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

        with patch.dict(sys.modules, {"xano_client": xano_client}):
            with patch.object(
                xano_client,
                "consultar_metricas_vendas",
                return_value=metricas_sem_vendas,
            ) as consultar:
                app.run()

                self.assertFalse(app.exception)
                self.assertIn(
                    "Nenhuma venda encontrada para os filtros selecionados.",
                    [mensagem.value for mensagem in app.info],
                )
                self.assertEqual(len(app.metric), 10)
                self.assertEqual(app.metric[0].value, "0")
                self.assertEqual(app.metric[2].value, "R$ 0,00")
                self.assertEqual(app.metric[8].value, "—")

                app.session_state["sale_filter_channel"] = "loja"
                app.session_state["sale_filter_status"] = "confirmada"
                app.session_state["sale_filter_start"] = date(2026, 11, 1)
                app.session_state["sale_filter_end"] = date(2026, 11, 20)
                consultar.return_value = metricas_reais
                app.run()

                self.assertFalse(app.exception)
                self.assertEqual(
                    consultar.call_args.kwargs,
                    {
                        "token": "jwt-dashboard",
                        "sales_channel": "loja",
                        "status": "confirmada",
                        "start_date": "2026-11-01",
                        "end_date": "2026-11-20",
                    },
                )
                self.assertEqual(app.metric[2].value, "R$ 299,98")
                self.assertEqual(app.metric[7].value, "R$ 262,09")
                self.assertEqual(app.metric[8].value, "87,37%")

                consultar.side_effect = requests.ConnectionError(
                    "serviço indisponível"
                )
                app.run()

                self.assertFalse(app.exception)
                self.assertTrue(app.error)
                self.assertEqual(len(app.metric), 0)
                self.assertNotIn(
                    "jwt-dashboard",
                    " ".join(mensagem.value for mensagem in app.error),
                )


if __name__ == "__main__":
    unittest.main()
