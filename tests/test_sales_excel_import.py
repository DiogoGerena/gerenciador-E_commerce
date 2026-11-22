import hashlib
import unittest
from datetime import date, datetime, timezone
from io import BytesIO
from unittest.mock import Mock, patch
from uuid import UUID

from openpyxl import Workbook, load_workbook
import requests
from streamlit.testing.v1 import AppTest

import app.erp_modules as erp_modules
from app.sales_excel_import import (
    COST_COLUMNS,
    ITEM_COLUMNS,
    ProductLookupError,
    build_sale_payload,
    create_sales_template,
    parse_sales_workbook,
    resolve_sale_products,
)
from app.xano_client import OperacaoVendaInconclusivaError


def _workbook_content(items, costs=()):
    workbook = Workbook()
    item_sheet = workbook.active
    item_sheet.title = "Itens"
    cost_sheet = workbook.create_sheet("Custos")
    item_sheet.append(ITEM_COLUMNS)
    cost_sheet.append(COST_COLUMNS)
    for row in items:
        item_sheet.append(row)
    for row in costs:
        cost_sheet.append(row)
    output = BytesIO()
    workbook.save(output)
    workbook.close()
    return output.getvalue()


def _item_row(
    *,
    order="PED-1",
    channel="Loja online",
    sale_date="2026-03-15T12:30:00Z",
    sku="SKU-7",
    product_id=7,
    quantity=2,
    price=10.5,
    discount=1.0,
    notes="Pedido de teste",
):
    return (
        order,
        channel,
        sale_date,
        sku,
        product_id,
        quantity,
        price,
        discount,
        notes,
    )


def _cost_row(
    *,
    order="PED-1",
    channel="Loja online",
    cost_type="embalagem",
    amount=2.5,
    description="Caixa",
):
    return (order, channel, cost_type, amount, description)


class SalesExcelParserTests(unittest.TestCase):
    def test_template_has_headers_instructions_and_no_data_rows(self):
        workbook = load_workbook(BytesIO(create_sales_template()), data_only=False)
        try:
            self.assertEqual(workbook.sheetnames, ["Itens", "Custos"])
            self.assertEqual(
                tuple(cell.value for cell in workbook["Itens"][1]),
                ITEM_COLUMNS,
            )
            self.assertEqual(
                tuple(cell.value for cell in workbook["Custos"][1]),
                COST_COLUMNS,
            )
            self.assertEqual(workbook["Itens"].max_row, 1)
            self.assertEqual(workbook["Custos"].max_row, 1)
            self.assertIn("Obrigatório", workbook["Itens"]["E1"].comment.text)
            self.assertIsNotNone(workbook["Custos"]["C1"].comment)
            self.assertEqual(len(workbook["Custos"].data_validations.dataValidation), 1)
        finally:
            workbook.close()

    def test_empty_template_parses_without_errors_or_records(self):
        parsed = parse_sales_workbook(create_sales_template())

        self.assertEqual(parsed["errors"], [])
        self.assertEqual(parsed["sales"], [])
        self.assertEqual(parsed["item_rows"], 0)
        self.assertEqual(parsed["cost_rows"], 0)
        self.assertEqual(parsed["total_items"], 0)
        self.assertEqual(parsed["total_costs"], 0)

    def test_groups_items_and_costs_into_contract_payload(self):
        content = _workbook_content(
            [
                _item_row(),
                _item_row(
                    sku="SKU-8",
                    product_id=8,
                    quantity=1,
                    price=5,
                    discount=None,
                ),
            ],
            [_cost_row()],
        )
        parsed = parse_sales_workbook(content)
        products = {
            7: {"id": 7, "name": "Produto 7", "sku": "SKU-7", "status": "ativo"},
            8: {"id": 8, "name": "Produto 8", "sku": "SKU-8", "status": "ativo"},
        }
        resolve_sale_products(parsed, products.__getitem__)

        self.assertEqual(parsed["errors"], [])
        self.assertEqual(len(parsed["sales"]), 1)
        sale = parsed["sales"][0]
        payload = build_sale_payload(sale)
        expected_date = int(
            datetime(2026, 3, 15, 12, 30, tzinfo=timezone.utc).timestamp() * 1000
        )
        self.assertEqual(payload["sale_date"], expected_date)
        self.assertEqual(payload["sales_channel"], "Loja online")
        self.assertEqual(payload["order_number"], "PED-1")
        self.assertEqual(
            payload["items"],
            [
                {
                    "product_id": 7,
                    "quantity": 2,
                    "unit_sale_price": 10.5,
                    "discount_amount": 1.0,
                },
                {
                    "product_id": 8,
                    "quantity": 1,
                    "unit_sale_price": 5.0,
                },
            ],
        )
        self.assertEqual(
            payload["costs"],
            [
                {
                    "cost_type": "embalagem",
                    "amount": 2.5,
                    "description": "Caixa",
                }
            ],
        )
        self.assertEqual(payload["notes"], "Pedido de teste")

    def test_same_order_number_on_different_channels_is_a_distinct_sale(self):
        parsed = parse_sales_workbook(
            _workbook_content(
                [
                    _item_row(order="PED-1", channel="Loja online"),
                    _item_row(order="PED-1", channel="Marketplace"),
                ]
            )
        )

        self.assertEqual(
            [
                (sale["sales_channel"], sale["order_number"])
                for sale in parsed["sales"]
            ],
            [("Loja online", "PED-1"), ("Marketplace", "PED-1")],
        )

    def test_blank_optional_values_are_omitted_from_payload(self):
        content = _workbook_content(
            [
                _item_row(
                    sale_date=None,
                    sku=None,
                    quantity=1,
                    discount=None,
                    notes=None,
                )
            ]
        )
        parsed = parse_sales_workbook(content)
        resolve_sale_products(
            parsed,
            lambda product_id: {
                "id": product_id,
                "name": "Produto",
                "sku": "SKU-7",
                "status": "ativo",
            },
        )
        payload = build_sale_payload(parsed["sales"][0])

        self.assertEqual(parsed["errors"], [])
        self.assertNotIn("sale_date", payload)
        self.assertNotIn("notes", payload)
        self.assertEqual(payload["costs"], [])
        self.assertNotIn("discount_amount", payload["items"][0])

    def test_numeric_timestamp_as_text_is_read_as_milliseconds(self):
        expected = 1773577800000
        parsed = parse_sales_workbook(
            _workbook_content([_item_row(sale_date=str(expected))])
        )

        self.assertEqual(parsed["sales"][0]["sale_date"], expected)

    def test_numeric_timestamp_in_seconds_is_rejected_not_converted_to_1970(self):
        parsed = parse_sales_workbook(
            _workbook_content([_item_row(sale_date="1773577800")])
        )

        self.assertIsNone(parsed["sales"][0]["sale_date"])
        self.assertFalse(parsed["sales"][0]["valid"])
        self.assertTrue(
            any(
                issue["field"] == "data_venda"
                and "milissegundos" in issue["message"]
                for issue in parsed["errors"]
            )
        )

    def test_sku_without_product_id_is_blocked_by_current_lookup_contract(self):
        parsed = parse_sales_workbook(
            _workbook_content([_item_row(product_id=None)])
        )
        resolve_sale_products(
            parsed,
            lambda product_id: self.fail("SKU não deve iniciar uma consulta"),
        )

        self.assertFalse(parsed["sales"][0]["valid"])
        self.assertTrue(any("não oferece busca por SKU" in issue["message"] for issue in parsed["errors"]))

    def test_product_lookup_rejects_inactive_or_mismatched_sku(self):
        parsed = parse_sales_workbook(_workbook_content([_item_row()]))
        resolve_sale_products(
            parsed,
            lambda product_id: {
                "id": product_id,
                "name": "Produto",
                "sku": "OUTRO-SKU",
                "status": "inativo",
            },
        )

        self.assertFalse(parsed["sales"][0]["valid"])
        self.assertEqual(len(parsed["errors"]), 1)
        self.assertIn("não está ativo", parsed["errors"][0]["message"])

    def test_lookup_failure_is_an_import_validation_error(self):
        parsed = parse_sales_workbook(_workbook_content([_item_row()]))

        def lookup(_product_id):
            raise ProductLookupError("Produto não consultável.")

        resolve_sale_products(parsed, lookup)

        self.assertFalse(parsed["sales"][0]["valid"])
        self.assertIn("Produto não consultável", parsed["errors"][0]["message"])

    def test_required_fields_amounts_discounts_and_costs_are_validated(self):
        parsed = parse_sales_workbook(
            _workbook_content(
                [
                    _item_row(
                        product_id=7,
                        quantity=1.5,
                        price=-1,
                        discount=5,
                    ),
                    _item_row(order="", product_id=8, quantity=1, price=1),
                    _item_row(
                        order="PED-DESCONTO",
                        product_id=8,
                        quantity=1,
                        price=1,
                        discount=5,
                    ),
                ],
                [_cost_row(order="PED-SEM-ITEM")],
            )
        )

        messages = [issue["message"] for issue in parsed["errors"]]
        self.assertTrue(any("numero_pedido é obrigatório" in text for text in messages))
        self.assertTrue(any("deve ser um inteiro" in text for text in messages))
        self.assertTrue(any("não negativo" in text for text in messages))
        self.assertTrue(any("Não existe venda correspondente" in text for text in messages))

    def test_orphan_and_duplicate_cost_rows_are_rejected(self):
        parsed = parse_sales_workbook(
            _workbook_content(
                [_item_row()],
                [_cost_row(), _cost_row(), _cost_row(order="PED-2")],
            )
        )

        messages = [issue["message"] for issue in parsed["errors"]]
        self.assertTrue(any("Custo duplicado" in text for text in messages))
        self.assertTrue(any("Não existe venda correspondente" in text for text in messages))
        self.assertEqual(parsed["cost_rows"], 3)
        self.assertEqual(parsed["total_costs"], 1)

    def test_invalid_headers_and_non_xlsx_are_reported(self):
        with self.assertRaisesRegex(ValueError, "planilha .xlsx válida"):
            parse_sales_workbook(b"not an xlsx")
        workbook = load_workbook(
            BytesIO(_workbook_content([_item_row()])),
        )
        workbook["Itens"]["A1"] = "pedido"
        invalid_content = BytesIO()
        workbook.save(invalid_content)
        workbook.close()
        with self.assertRaisesRegex(ValueError, "Cabeçalhos inválidos"):
            parse_sales_workbook(invalid_content.getvalue())


class SalesExcelImportFlowTests(unittest.TestCase):
    TOKEN = "session-token"

    def _product(self, token, product_id):
        self.assertEqual(token, self.TOKEN)
        return {
            "id": product_id,
            "name": f"Produto {product_id}",
            "sku": f"SKU-{product_id}",
            "status": "ativo",
        }

    def _empty_sales_page(self):
        return {
            "itemsReceived": 0,
            "curPage": 1,
            "nextPage": None,
            "prevPage": None,
            "offset": 0,
            "itemsTotal": 0,
            "pageTotal": 0,
            "items": [],
        }

    def _sale_response(self, order_number="PED-1"):
        return {
            "sale": {
                "id": 91,
                "sales_channel": "Loja online",
                "order_number": order_number,
            },
            "items": [{"product_id": 7, "quantity": 2}],
            "costs": [],
            "financial_summary": {
                "gross_amount": 21.0,
                "discount_amount": 1.0,
                "net_revenue": 20.0,
                "total_cmv": 11.0,
                "total_costs": 0.0,
                "result": 9.0,
                "profit_margin_percent": 45.0,
            },
        }

    def _prepare(self, *, sales_page=None, items=None, costs=None):
        content = _workbook_content(
            [_item_row()] if items is None else items,
            costs or [],
        )
        with (
            patch.object(erp_modules, "consultar_produto", side_effect=self._product),
            patch.object(
                erp_modules,
                "listar_vendas",
                return_value=sales_page or self._empty_sales_page(),
            ) as list_sales,
        ):
            state = erp_modules._preparar_importacao_vendas_excel(
                self.TOKEN,
                content,
                hashlib.sha256(content).hexdigest(),
                "vendas.xlsx",
            )
        return state, list_sales, content

    def test_preflight_sends_channel_and_order_as_query_filters(self):
        state, list_sales, _content = self._prepare()

        self.assertEqual(state["errors"], [])
        self.assertEqual(state["sales"][0]["status"], "ready")
        list_sales.assert_called_once_with(
            self.TOKEN,
            sales_channel="Loja online",
            order_number="PED-1",
            start_date="1970-01-01T00:00:00Z",
            end_date=f"{date.today().isoformat()}T23:59:59Z",
            page=1,
            per_page=100,
        )

    def test_duplicate_scan_finds_historical_order_across_pages(self):
        first_page = {**self._empty_sales_page(), "nextPage": 2}
        historical_sale = {
            "sales_channel": "Loja online",
            "order_number": "PED-1",
            "status": "registrada",
            "sale_date": "2001-02-03T00:00:00Z",
        }
        second_page = {
            **self._empty_sales_page(),
            "itemsReceived": 1,
            "items": [historical_sale],
        }
        with patch.object(
            erp_modules,
            "listar_vendas",
            side_effect=(first_page, second_page),
        ) as list_sales:
            found = erp_modules._localizar_venda_importacao(
                self.TOKEN,
                "Loja online",
                "PED-1",
            )

        self.assertEqual(found, historical_sale)
        self.assertEqual(list_sales.call_count, 2)
        for page_number, call in enumerate(list_sales.call_args_list, start=1):
            self.assertEqual(
                call.args,
                (self.TOKEN,),
            )
            self.assertEqual(
                call.kwargs,
                {
                    "sales_channel": "Loja online",
                    "order_number": "PED-1",
                    "start_date": "1970-01-01T00:00:00Z",
                    "end_date": f"{date.today().isoformat()}T23:59:59Z",
                    "page": page_number,
                    "per_page": 100,
                },
            )

    def test_duplicate_lookup_http_error_is_shown_as_xano_failure(self):
        content = _workbook_content([_item_row()])
        response = Mock()
        response.status_code = 400
        response.headers = {}
        response.text = ""
        response.json.return_value = {"message": "Missing param: end_date"}
        error = requests.HTTPError(response=response)
        with (
            patch.object(erp_modules, "consultar_produto", side_effect=self._product),
            patch.object(
                erp_modules,
                "listar_vendas",
                side_effect=error,
            ) as list_sales,
        ):
            state = erp_modules._preparar_importacao_vendas_excel(
                self.TOKEN,
                content,
                hashlib.sha256(content).hexdigest(),
                "vendas.xlsx",
            )

        app = AppTest.from_string(
            "import app.erp_modules as erp_modules\n"
            "erp_modules._render_importacao_vendas_excel('session-token')"
        )
        app.session_state[erp_modules.VENDAS_EXCEL_SESSION_KEY] = state
        app = app.run()

        self.assertEqual(app.exception, [])
        self.assertTrue(
            any("consulta de duplicidade no Xano" in item.value for item in app.error)
        )
        displayed_errors = app.dataframe[0].value["Erro"].tolist()
        self.assertTrue(
            any("Missing param: end_date" in message for message in displayed_errors)
        )
        list_sales.assert_called_once_with(
            self.TOKEN,
            sales_channel="Loja online",
            order_number="PED-1",
            start_date="1970-01-01T00:00:00Z",
            end_date=f"{date.today().isoformat()}T23:59:59Z",
            page=1,
            per_page=100,
        )
        self.assertEqual(state["sales"][0]["status"], "blocked")

    def test_orphan_cost_blocks_file_and_keeps_order_out_of_ready_state(self):
        content = _workbook_content(
            [
                _item_row(
                    order="3",
                    channel="Mercado livre",
                    sale_date="2026-11-22T00:00:00Z",
                    sku=None,
                    product_id=21,
                    quantity=5,
                    price=59.99,
                    discount=0,
                )
            ],
            [
                _cost_row(
                    order="EXEMPLO-PEDIDO-001",
                    channel="EXEMPLO-CANAL",
                )
            ],
        )
        with (
            patch.object(erp_modules, "consultar_produto") as get_product,
            patch.object(erp_modules, "listar_vendas") as list_sales,
            patch.object(erp_modules, "criar_venda") as create_sale,
        ):
            state = erp_modules._preparar_importacao_vendas_excel(
                self.TOKEN,
                content,
                hashlib.sha256(content).hexdigest(),
                "Baixar planilha.xlsx",
            )

        self.assertEqual(len(state["errors"]), 1)
        self.assertEqual(
            state["errors"][0],
            {
                "sheet": "Custos",
                "row": 2,
                "order_number": None,
                "sales_channel": None,
                "field": "numero_pedido/canal_venda",
                "message": "Não existe venda correspondente para este custo.",
            },
        )
        self.assertEqual(state["sales"][0]["status"], "blocked")
        self.assertEqual(state["sales"][0]["sale"]["order_number"], "3")
        self.assertEqual(state["summary"]["cost_rows"], 1)
        self.assertEqual(state["summary"]["total_costs"], 0)
        get_product.assert_not_called()
        list_sales.assert_not_called()
        with self.assertRaisesRegex(ValueError, "Corrija todos os erros"):
            erp_modules._executar_lote_vendas_excel(self.TOKEN, state)
        create_sale.assert_not_called()

    def test_preview_distinguishes_cost_rows_from_associated_costs(self):
        state, _list_sales, _content = self._prepare(
            costs=[
                _cost_row(
                    order="EXEMPLO-PEDIDO-001",
                    channel="EXEMPLO-CANAL",
                )
            ]
        )
        app = AppTest.from_string(
            "import app.erp_modules as erp_modules\n"
            "erp_modules._render_importacao_vendas_excel('session-token')"
        )
        app.session_state[erp_modules.VENDAS_EXCEL_SESSION_KEY] = state
        app = app.run()

        self.assertEqual(app.exception, [])
        self.assertTrue(
            any(
                "1 linha preenchida na aba Custos, "
                "0 custos associados"
                in element.value
                for element in app.markdown
            )
        )
        self.assertTrue(app.button(key="vendas_excel_import_submit").disabled)

    def test_existing_non_cancelled_order_blocks_the_whole_import(self):
        existing_page = {
            **self._empty_sales_page(),
            "items": [
                {
                    "id": 55,
                    "sales_channel": "Loja online",
                    "order_number": "PED-1",
                    "status": "registrada",
                }
            ],
        }
        state, _list_sales, _content = self._prepare(sales_page=existing_page)
        session_state = {erp_modules.VENDAS_EXCEL_SESSION_KEY: state}

        with (
            patch.object(erp_modules.st, "session_state", session_state),
            patch.object(erp_modules, "criar_venda") as create_sale,
        ):
            with self.assertRaisesRegex(ValueError, "Corrija todos os erros"):
                erp_modules._executar_lote_vendas_excel(self.TOKEN, state)

        self.assertEqual(state["sales"][0]["status"], "duplicate")
        create_sale.assert_not_called()

    def test_incomplete_duplicate_response_blocks_import(self):
        incomplete_page = {
            **self._empty_sales_page(),
            "items": [
                {
                    "sales_channel": "Loja online",
                    "order_number": "PED-1",
                }
            ],
        }
        state, _list_sales, _content = self._prepare(sales_page=incomplete_page)

        self.assertEqual(state["sales"][0]["status"], "blocked")
        self.assertTrue(state["errors"])

    def test_cancelled_order_does_not_block_reimport(self):
        cancelled_page = {
            **self._empty_sales_page(),
            "items": [
                {
                    "id": 55,
                    "sales_channel": "Loja online",
                    "order_number": "PED-1",
                    "status": "cancelada",
                }
            ],
        }
        state, _list_sales, _content = self._prepare(sales_page=cancelled_page)

        self.assertEqual(state["errors"], [])
        self.assertEqual(state["sales"][0]["status"], "ready")

    def test_import_sends_one_grouped_payload_with_a_uuid_v4(self):
        state, _list_sales, _content = self._prepare()
        session_state = {erp_modules.VENDAS_EXCEL_SESSION_KEY: state}
        with (
            patch.object(erp_modules.st, "session_state", session_state),
            patch.object(
                erp_modules,
                "criar_venda",
                return_value=self._sale_response(),
            ) as create_sale,
        ):
            erp_modules._executar_lote_vendas_excel(self.TOKEN, state)

        self.assertEqual(create_sale.call_count, 1)
        call_token, payload = create_sale.call_args.args
        self.assertEqual(call_token, self.TOKEN)
        self.assertEqual(payload["order_number"], "PED-1")
        self.assertEqual(payload["items"][0]["product_id"], 7)
        self.assertEqual(payload["items"][0]["quantity"], 2)
        self.assertEqual(payload["items"][0]["unit_sale_price"], 10.5)
        self.assertEqual(payload["items"][0]["discount_amount"], 1.0)
        self.assertEqual(payload["costs"], [])
        self.assertEqual(UUID(payload["idempotency_key"]).version, 4)
        self.assertEqual(state["sales"][0]["status"], "confirmed")
        self.assertEqual(state["sales"][0]["response"]["sale"]["id"], 91)

    def test_pending_sale_reconciliation_reuses_exact_key_and_payload(self):
        state, _list_sales, _content = self._prepare()
        session_state = {erp_modules.VENDAS_EXCEL_SESSION_KEY: state}
        with (
            patch.object(erp_modules.st, "session_state", session_state),
            patch.object(
                erp_modules,
                "criar_venda",
                side_effect=[
                    OperacaoVendaInconclusivaError("Timeout."),
                    self._sale_response(),
                ],
            ) as create_sale,
        ):
            erp_modules._executar_lote_vendas_excel(self.TOKEN, state)
            original_snapshot = state["sales"][0]["payload_snapshot"].copy()
            self.assertEqual(state["sales"][0]["status"], "pending")
            erp_modules._reconciliar_venda_excel(
                self.TOKEN,
                state,
                state["sales"][0],
            )

        self.assertEqual(create_sale.call_count, 2)
        self.assertEqual(
            create_sale.call_args_list[0].args[1],
            create_sale.call_args_list[1].args[1],
        )
        self.assertEqual(
            create_sale.call_args_list[1].args[1],
            original_snapshot,
        )
        self.assertEqual(state["sales"][0]["status"], "confirmed")

    def test_confirmed_sale_is_not_sent_again(self):
        state, _list_sales, _content = self._prepare()
        session_state = {erp_modules.VENDAS_EXCEL_SESSION_KEY: state}
        with (
            patch.object(erp_modules.st, "session_state", session_state),
            patch.object(
                erp_modules,
                "criar_venda",
                return_value=self._sale_response(),
            ) as create_sale,
        ):
            erp_modules._executar_lote_vendas_excel(self.TOKEN, state)
            erp_modules._executar_lote_vendas_excel(self.TOKEN, state)

        create_sale.assert_called_once()

    def test_separate_orders_get_separate_posts_and_idempotency_keys(self):
        state, _list_sales, _content = self._prepare(
            items=[
                _item_row(order="PED-1"),
                _item_row(order="PED-2"),
            ]
        )
        session_state = {erp_modules.VENDAS_EXCEL_SESSION_KEY: state}
        with (
            patch.object(erp_modules.st, "session_state", session_state),
            patch.object(
                erp_modules,
                "criar_venda",
                side_effect=[
                    self._sale_response("PED-1"),
                    self._sale_response("PED-2"),
                ],
            ) as create_sale,
        ):
            erp_modules._executar_lote_vendas_excel(self.TOKEN, state)

        self.assertEqual(create_sale.call_count, 2)
        first_payload = create_sale.call_args_list[0].args[1]
        second_payload = create_sale.call_args_list[1].args[1]
        self.assertNotEqual(
            first_payload["idempotency_key"],
            second_payload["idempotency_key"],
        )
        self.assertEqual(
            [entry["status"] for entry in state["sales"]],
            ["confirmed", "confirmed"],
        )

    def test_mismatched_response_does_not_confirm_imported_order(self):
        state, _list_sales, _content = self._prepare()
        session_state = {erp_modules.VENDAS_EXCEL_SESSION_KEY: state}
        with (
            patch.object(erp_modules.st, "session_state", session_state),
            patch.object(
                erp_modules,
                "criar_venda",
                return_value=self._sale_response("OUTRO-PEDIDO"),
            ),
        ):
            erp_modules._executar_lote_vendas_excel(self.TOKEN, state)

        self.assertEqual(state["sales"][0]["status"], "pending")
        self.assertIn("não foi confirmado", state["sales"][0]["message"])

    def test_confirmed_import_refreshes_sales_list_without_changing_filter(self):
        state = {
            "sales": [
                {
                    "status": "confirmed",
                    "sale": {
                        "sales_channel": "Loja online",
                        "order_number": "PED-1",
                    },
                }
            ]
        }
        session_state = {"vendas_list_filter_channel": "Canal filtrado"}

        with patch.object(erp_modules.st, "session_state", session_state):
            refreshed = erp_modules._atualizar_listagem_apos_importacao(
                state,
                ["ready"],
            )

        self.assertTrue(refreshed)
        self.assertEqual(
            session_state["vendas_list_filter_channel"],
            "Canal filtrado",
        )
        self.assertEqual(session_state["vendas_list_page"], 1)
        self.assertTrue(session_state["vendas_list_query_pending"])


if __name__ == "__main__":
    unittest.main()
