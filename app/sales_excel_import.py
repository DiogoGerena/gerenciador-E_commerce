from decimal import Decimal, InvalidOperation
from io import BytesIO
import math
from zipfile import BadZipFile

try:
    from app.sale_dates import sale_date_to_unix_milliseconds
except ModuleNotFoundError:  # pragma: no cover - compatibilidade com execução direta
    from sale_dates import sale_date_to_unix_milliseconds

from openpyxl import Workbook, load_workbook
from openpyxl.comments import Comment
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils.exceptions import InvalidFileException
from openpyxl.worksheet.datavalidation import DataValidation


ITEM_COLUMNS = (
    "numero_pedido",
    "canal_venda",
    "data_venda",
    "sku",
    "id_produto",
    "quantidade",
    "preco_unitario",
    "desconto_item",
    "observacoes",
)
COST_COLUMNS = (
    "numero_pedido",
    "canal_venda",
    "tipo_custo",
    "valor",
    "descricao",
)
COST_TYPES = (
    "embalagem",
    "comissao_marketplace",
    "impostos",
    "frete_saida",
    "outros",
)


class ProductLookupError(ValueError):
    pass


def _is_blank(value):
    return value is None or (isinstance(value, str) and not value.strip())


def _add_issue(errors, sale, sheet, row, field, message):
    issue = {
        "sheet": sheet,
        "row": row,
        "order_number": sale.get("order_number") if sale else None,
        "sales_channel": sale.get("sales_channel") if sale else None,
        "field": field,
        "message": message,
    }
    errors.append(issue)
    if sale is not None:
        sale["errors"].append(issue)


def _read_headers(sheet, expected, sheet_name):
    first_row = next(
        sheet.iter_rows(min_row=1, max_row=1, values_only=True),
        None,
    )
    if first_row is None:
        raise ValueError(f"A aba {sheet_name} está sem cabeçalhos.")

    headers = list(first_row)
    while headers and headers[-1] is None:
        headers.pop()
    if not headers or any(not isinstance(value, str) or not value for value in headers):
        raise ValueError(
            f"A aba {sheet_name} deve conter cabeçalhos de texto na primeira linha."
        )

    duplicates = sorted(
        {header for header in headers if headers.count(header) > 1}
    )
    if duplicates:
        raise ValueError(
            f"A aba {sheet_name} contém cabeçalhos duplicados: "
            f"{', '.join(duplicates)}."
        )

    missing = [header for header in expected if header not in headers]
    unknown = [header for header in headers if header not in expected]
    if missing or unknown:
        details = []
        if missing:
            details.append(f"faltam: {', '.join(missing)}")
        if unknown:
            details.append(f"não reconhecidos: {', '.join(unknown)}")
        raise ValueError(
            f"Cabeçalhos inválidos na aba {sheet_name} ({'; '.join(details)})."
        )
    return {header: index for index, header in enumerate(headers)}


def _cell(row, columns, name):
    index = columns[name]
    return row[index] if index < len(row) else None


def _read_text(value, field, *, required):
    if _is_blank(value):
        if required:
            raise ValueError(f"{field} é obrigatório.")
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field} deve ser texto.")
    normalized = value.strip()
    if required and not normalized:
        raise ValueError(f"{field} é obrigatório.")
    return normalized or None


def _read_integer(value, field, *, required, positive=False):
    if _is_blank(value):
        if required:
            raise ValueError(f"{field} é obrigatório.")
        return None
    if isinstance(value, bool):
        raise ValueError(f"{field} deve ser um inteiro.")
    try:
        parsed = Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        raise ValueError(f"{field} deve ser um inteiro.") from None
    if not parsed.is_finite() or parsed != parsed.to_integral_value():
        raise ValueError(f"{field} deve ser um inteiro.")
    number = int(parsed)
    if positive and number < 1:
        raise ValueError(f"{field} deve ser maior ou igual a 1.")
    return number


def _read_amount(value, field, *, required):
    if _is_blank(value):
        if required:
            raise ValueError(f"{field} é obrigatório.")
        return None
    if isinstance(value, bool):
        raise ValueError(f"{field} deve ser um número finito não negativo.")
    text = str(value).strip()
    if "," in text:
        if "." in text or text.count(",") != 1:
            raise ValueError(
                f"{field} deve usar apenas um separador decimal, sem separador de milhar."
            )
        text = text.replace(",", ".")
    try:
        parsed = Decimal(text)
    except (InvalidOperation, ValueError):
        raise ValueError(f"{field} deve ser um número válido.") from None
    if not parsed.is_finite() or parsed < 0:
        raise ValueError(f"{field} deve ser finito e não negativo.")
    number = float(parsed)
    if not math.isfinite(number):
        raise ValueError(f"{field} deve ser finito e não negativo.")
    return parsed


def _timestamp_milliseconds(value):
    return sale_date_to_unix_milliseconds(
        value,
        "data_venda",
    )


def _row_has_values(row):
    return any(not _is_blank(value) for value in row)


def parse_sales_workbook(file_content):
    if not isinstance(file_content, (bytes, bytearray)) or not file_content:
        raise ValueError("O arquivo Excel está vazio.")

    try:
        workbook = load_workbook(
            BytesIO(file_content),
            read_only=True,
            data_only=True,
        )
    except (BadZipFile, InvalidFileException, OSError, ValueError, KeyError) as error:
        raise ValueError("O arquivo não é uma planilha .xlsx válida.") from error

    try:
        required_sheets = {"Itens", "Custos"}
        missing_sheets = required_sheets - set(workbook.sheetnames)
        if missing_sheets:
            raise ValueError(
                "Abas obrigatórias ausentes: "
                + ", ".join(sorted(missing_sheets))
                + "."
            )

        item_sheet = workbook["Itens"]
        cost_sheet = workbook["Custos"]
        item_columns = _read_headers(item_sheet, ITEM_COLUMNS, "Itens")
        cost_columns = _read_headers(cost_sheet, COST_COLUMNS, "Custos")
        errors = []
        sales_by_key = {}
        item_row_count = 0
        cost_row_count = 0

        for row_number, row in enumerate(
            item_sheet.iter_rows(min_row=2, values_only=True),
            start=2,
        ):
            if not _row_has_values(row):
                continue
            item_row_count += 1

            order_number = None
            sales_channel = None
            try:
                order_number = _read_text(
                    _cell(row, item_columns, "numero_pedido"),
                    "numero_pedido",
                    required=True,
                )
            except ValueError as error:
                _add_issue(errors, None, "Itens", row_number, "numero_pedido", str(error))
            try:
                sales_channel = _read_text(
                    _cell(row, item_columns, "canal_venda"),
                    "canal_venda",
                    required=True,
                )
            except ValueError as error:
                _add_issue(errors, None, "Itens", row_number, "canal_venda", str(error))
            if order_number is None or sales_channel is None:
                continue

            group_key = (sales_channel, order_number)
            sale = sales_by_key.get(group_key)
            if sale is None:
                sale = {
                    "sales_channel": sales_channel,
                    "order_number": order_number,
                    "sale_date": None,
                    "notes": None,
                    "items": [],
                    "costs": [],
                    "item_rows": [],
                    "errors": [],
                    "_header_signature": None,
                }
                sales_by_key[group_key] = sale

            try:
                raw_date = _cell(row, item_columns, "data_venda")
                sale_date = (
                    None if _is_blank(raw_date) else _timestamp_milliseconds(raw_date)
                )
                date_signature = ("valid", sale_date)
            except ValueError as error:
                sale_date = None
                date_signature = ("invalid", repr(raw_date))
                _add_issue(errors, sale, "Itens", row_number, "data_venda", str(error))

            try:
                notes = _read_text(
                    _cell(row, item_columns, "observacoes"),
                    "observacoes",
                    required=False,
                )
                notes_signature = ("valid", notes)
            except ValueError as error:
                notes = None
                notes_signature = (
                    "invalid",
                    repr(_cell(row, item_columns, "observacoes")),
                )
                _add_issue(errors, sale, "Itens", row_number, "observacoes", str(error))

            signature = (date_signature, notes_signature)
            if sale["_header_signature"] is None:
                sale["_header_signature"] = signature
                sale["sale_date"] = sale_date
                sale["notes"] = notes
            elif sale["_header_signature"] != signature:
                _add_issue(
                    errors,
                    sale,
                    "Itens",
                    row_number,
                    "data_venda/observacoes",
                    "Data e observações devem ser consistentes em todas as linhas do pedido.",
                )
            sale["item_rows"].append(row_number)

            row_item = {"source_row": row_number}
            row_valid = True
            try:
                row_item["sku"] = _read_text(
                    _cell(row, item_columns, "sku"),
                    "sku",
                    required=False,
                )
            except ValueError as error:
                row_valid = False
                _add_issue(errors, sale, "Itens", row_number, "sku", str(error))
            try:
                row_item["product_id"] = _read_integer(
                    _cell(row, item_columns, "id_produto"),
                    "id_produto",
                    required=False,
                    positive=True,
                )
            except ValueError as error:
                row_valid = False
                _add_issue(errors, sale, "Itens", row_number, "id_produto", str(error))

            if row_valid and row_item.get("sku") is None and row_item.get("product_id") is None:
                row_valid = False
                _add_issue(
                    errors,
                    sale,
                    "Itens",
                    row_number,
                    "sku/id_produto",
                    "Informe sku ou id_produto.",
                )

            try:
                row_item["quantity"] = _read_integer(
                    _cell(row, item_columns, "quantidade"),
                    "quantidade",
                    required=True,
                    positive=True,
                )
            except ValueError as error:
                row_valid = False
                _add_issue(errors, sale, "Itens", row_number, "quantidade", str(error))

            try:
                unit_price = _read_amount(
                    _cell(row, item_columns, "preco_unitario"),
                    "preco_unitario",
                    required=True,
                )
                row_item["unit_sale_price"] = float(unit_price)
            except ValueError as error:
                unit_price = None
                row_valid = False
                _add_issue(
                    errors,
                    sale,
                    "Itens",
                    row_number,
                    "preco_unitario",
                    str(error),
                )

            try:
                discount = _read_amount(
                    _cell(row, item_columns, "desconto_item"),
                    "desconto_item",
                    required=False,
                )
                if discount is not None:
                    row_item["discount_amount"] = float(discount)
            except ValueError as error:
                discount = None
                row_valid = False
                _add_issue(
                    errors,
                    sale,
                    "Itens",
                    row_number,
                    "desconto_item",
                    str(error),
                )

            if (
                unit_price is not None
                and discount is not None
                and "quantity" in row_item
                and discount > unit_price * row_item["quantity"]
            ):
                row_valid = False
                _add_issue(
                    errors,
                    sale,
                    "Itens",
                    row_number,
                    "desconto_item",
                    "desconto_item não pode superar o valor bruto do item.",
                )

            if row_valid:
                sale["items"].append(row_item)

        seen_costs = set()
        for row_number, row in enumerate(
            cost_sheet.iter_rows(min_row=2, values_only=True),
            start=2,
        ):
            if not _row_has_values(row):
                continue
            cost_row_count += 1

            try:
                order_number = _read_text(
                    _cell(row, cost_columns, "numero_pedido"),
                    "numero_pedido",
                    required=True,
                )
            except ValueError as error:
                _add_issue(errors, None, "Custos", row_number, "numero_pedido", str(error))
                continue
            try:
                sales_channel = _read_text(
                    _cell(row, cost_columns, "canal_venda"),
                    "canal_venda",
                    required=True,
                )
            except ValueError as error:
                _add_issue(errors, None, "Custos", row_number, "canal_venda", str(error))
                continue

            group_key = (sales_channel, order_number)
            sale = sales_by_key.get(group_key)
            row_cost = {}
            row_valid = True
            try:
                cost_type = _read_text(
                    _cell(row, cost_columns, "tipo_custo"),
                    "tipo_custo",
                    required=True,
                )
                if cost_type not in COST_TYPES:
                    raise ValueError(
                        "tipo_custo deve ser um dos valores permitidos pelo Xano."
                    )
                row_cost["cost_type"] = cost_type
            except ValueError as error:
                row_valid = False
                _add_issue(errors, sale, "Custos", row_number, "tipo_custo", str(error))

            try:
                amount = _read_amount(
                    _cell(row, cost_columns, "valor"),
                    "valor",
                    required=True,
                )
                row_cost["amount"] = float(amount)
            except ValueError as error:
                row_valid = False
                _add_issue(errors, sale, "Custos", row_number, "valor", str(error))

            try:
                description = _read_text(
                    _cell(row, cost_columns, "descricao"),
                    "descricao",
                    required=False,
                )
                if description is not None:
                    row_cost["description"] = description
            except ValueError as error:
                row_valid = False
                _add_issue(errors, sale, "Custos", row_number, "descricao", str(error))

            if sale is None:
                row_valid = False
                _add_issue(
                    errors,
                    None,
                    "Custos",
                    row_number,
                    "numero_pedido/canal_venda",
                    "Não existe venda correspondente para este custo.",
                )

            if row_valid:
                duplicate_key = (
                    group_key,
                    row_cost["cost_type"],
                    amount,
                    row_cost.get("description"),
                )
                if duplicate_key in seen_costs:
                    _add_issue(
                        errors,
                        sale,
                        "Custos",
                        row_number,
                        "linha",
                        "Custo duplicado; cada custo deve ser informado uma única vez.",
                    )
                else:
                    seen_costs.add(duplicate_key)
                    sale["costs"].append(row_cost)

        sales = list(sales_by_key.values())
        for sale in sales:
            if not sale["items"] and not sale["errors"]:
                _add_issue(
                    errors,
                    sale,
                    "Itens",
                    None,
                    "items",
                    "A venda deve conter pelo menos um item válido.",
                )
            gross = sum(
                Decimal(str(item["unit_sale_price"])) * item["quantity"]
                for item in sale["items"]
            )
            discount = sum(
                Decimal(str(item.get("discount_amount", 0)))
                for item in sale["items"]
            )
            sale["gross_amount"] = float(gross)
            sale["discount_amount"] = float(discount)
            sale["additional_costs"] = sum(
                Decimal(str(cost["amount"])) for cost in sale["costs"]
            )
            sale["additional_costs"] = float(sale["additional_costs"])
            sale.pop("_header_signature", None)
            sale["valid"] = not sale["errors"]

        return {
            "sales": sales,
            "errors": errors,
            "item_rows": item_row_count,
            "cost_rows": cost_row_count,
            "total_items": sum(len(sale["items"]) for sale in sales),
            "total_costs": sum(len(sale["costs"]) for sale in sales),
        }
    finally:
        workbook.close()


def resolve_sale_products(parsed, product_lookup):
    errors = parsed["errors"]
    product_cache = {}

    for sale in parsed["sales"]:
        for item in sale["items"]:
            product_id = item.get("product_id")
            sku = item.get("sku")
            if product_id is None:
                _add_issue(
                    errors,
                    sale,
                    "Itens",
                    item["source_row"],
                    "sku",
                    "O Xano atual não oferece busca por SKU: GET /product exige "
                    "name. Preencha id_produto para validar o produto.",
                )
                continue

            if product_id not in product_cache:
                try:
                    product_cache[product_id] = product_lookup(product_id)
                except ProductLookupError as error:
                    product_cache[product_id] = error
            product = product_cache[product_id]
            if isinstance(product, ProductLookupError):
                _add_issue(
                    errors,
                    sale,
                    "Itens",
                    item["source_row"],
                    "id_produto",
                    str(product),
                )
                continue

            if not isinstance(product, dict) or product.get("id") != product_id:
                _add_issue(
                    errors,
                    sale,
                    "Itens",
                    item["source_row"],
                    "id_produto",
                    "GET /product/{id} não confirmou o produto informado.",
                )
                continue
            if product.get("status") != "ativo":
                _add_issue(
                    errors,
                    sale,
                    "Itens",
                    item["source_row"],
                    "id_produto",
                    "O produto não está ativo no Xano.",
                )
                continue

            product_sku = product.get("sku")
            if sku is not None:
                if not isinstance(product_sku, str) or not product_sku.strip():
                    _add_issue(
                        errors,
                        sale,
                        "Itens",
                        item["source_row"],
                        "sku",
                        "GET /product/{id} não retornou o campo sku necessário "
                        "para comparar SKU e ID.",
                    )
                    continue
                if product_sku.strip() != sku:
                    _add_issue(
                        errors,
                        sale,
                        "Itens",
                        item["source_row"],
                        "sku/id_produto",
                        "O SKU não corresponde ao id_produto informado.",
                    )
                    continue

            item["product_name"] = product.get("name")
            item["resolved_sku"] = product_sku

    sku_product_ids = {}
    for sale in parsed["sales"]:
        for item in sale["items"]:
            sku = item.get("sku") or item.get("resolved_sku")
            product_id = item.get("product_id")
            if isinstance(sku, str) and sku.strip() and product_id is not None:
                sku_product_ids.setdefault(sku.strip(), set()).add(product_id)

    duplicated_skus = {
        sku for sku, product_ids in sku_product_ids.items() if len(product_ids) > 1
    }
    if duplicated_skus:
        for sale in parsed["sales"]:
            for item in sale["items"]:
                sku = item.get("sku") or item.get("resolved_sku")
                if sku in duplicated_skus:
                    _add_issue(
                        errors,
                        sale,
                        "Itens",
                        item["source_row"],
                        "sku",
                        "O mesmo SKU foi associado a mais de um produto na planilha.",
                    )

    for sale in parsed["sales"]:
        sale["valid"] = not sale["errors"]
    return parsed


def build_sale_payload(sale):
    payload = {
        "sales_channel": sale["sales_channel"],
        "order_number": sale["order_number"],
        "costs": [dict(cost) for cost in sale["costs"]],
        "items": [
            {
                key: item[key]
                for key in (
                    "product_id",
                    "quantity",
                    "unit_sale_price",
                    "discount_amount",
                )
                if key in item
            }
            for item in sale["items"]
        ],
    }
    if sale.get("sale_date") is not None:
        payload["sale_date"] = sale["sale_date"]
    if sale.get("notes") is not None:
        payload["notes"] = sale["notes"]
    return payload


def create_sales_template():
    workbook = Workbook()
    items_sheet = workbook.active
    items_sheet.title = "Itens"
    costs_sheet = workbook.create_sheet("Custos")
    header_fill = PatternFill("solid", fgColor="17365D")
    header_font = Font(color="FFFFFF", bold=True)

    for sheet, columns in (
        (items_sheet, ITEM_COLUMNS),
        (costs_sheet, COST_COLUMNS),
    ):
        sheet.append(columns)
        sheet.freeze_panes = "A2"
        sheet.auto_filter.ref = f"A1:{sheet.cell(1, len(columns)).coordinate}2"
        for cell in sheet[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center")

    comments = {
        "data_venda": (
            "Opcional. Informe data Excel ou ISO 8601. Datas sem fuso são "
            "interpretadas como UTC; timestamps numéricos devem estar em ms."
        ),
        "sku": (
            "Opcional. A consulta Xano atual não permite busca por SKU; "
            "id_produto é necessário. Se ambos forem informados, eles serão comparados."
        ),
        "id_produto": (
            "Obrigatório para validar e importar: ID inteiro positivo de um "
            "produto ativo existente no Xano."
        ),
        "quantidade": "Inteiro maior ou igual a 1.",
        "preco_unitario": (
            "Obrigatório; número finito não negativo. Use célula numérica; "
            "texto decimal pode usar vírgula, sem separador de milhar."
        ),
        "desconto_item": "Opcional; não pode superar quantidade x preço_unitario.",
        "numero_pedido": "Texto obrigatório; linhas com mesmo canal/pedido são agrupadas.",
        "canal_venda": "Texto obrigatório; linhas do mesmo pedido devem repetir o canal.",
        "observacoes": "Opcional; deve ser igual em todas as linhas do pedido.",
    }
    for index, column in enumerate(ITEM_COLUMNS, start=1):
        if column in comments:
            items_sheet.cell(1, index).comment = Comment(
                comments[column],
                "CodBar",
            )
    cost_comments = {
        "numero_pedido": "Texto obrigatório; deve corresponder a um pedido da aba Itens.",
        "canal_venda": "Texto obrigatório; deve corresponder ao pedido da aba Itens.",
        "tipo_custo": "Obrigatório. Valores aceitos: " + ", ".join(COST_TYPES),
        "valor": "Obrigatório; número finito não negativo.",
        "descricao": "Opcional; texto descritivo do custo.",
    }
    for index, column in enumerate(COST_COLUMNS, start=1):
        costs_sheet.cell(1, index).comment = Comment(
            cost_comments[column],
            "CodBar",
        )

    items_sheet.column_dimensions["A"].width = 24
    items_sheet.column_dimensions["B"].width = 22
    items_sheet.column_dimensions["C"].width = 30
    items_sheet.column_dimensions["D"].width = 24
    items_sheet.column_dimensions["E"].width = 18
    items_sheet.column_dimensions["F"].width = 14
    items_sheet.column_dimensions["G"].width = 18
    items_sheet.column_dimensions["H"].width = 18
    items_sheet.column_dimensions["I"].width = 42
    costs_sheet.column_dimensions["A"].width = 24
    costs_sheet.column_dimensions["B"].width = 22
    costs_sheet.column_dimensions["C"].width = 28
    costs_sheet.column_dimensions["D"].width = 18
    costs_sheet.column_dimensions["E"].width = 42

    for column in ("A", "B", "C", "D", "I"):
        for cell in items_sheet[column][1:]:
            cell.number_format = "@"
    for column in ("F",):
        for cell in items_sheet[column][1:]:
            cell.number_format = "0"
    for column in ("G", "H"):
        for cell in items_sheet[column][1:]:
            cell.number_format = "0.00"
    for cell in costs_sheet["D"][1:]:
        cell.number_format = "0.00"
    for column in ("A", "B", "C", "E"):
        for cell in costs_sheet[column][1:]:
            cell.number_format = "@"

    cost_validation = DataValidation(
        type="list",
        formula1=f'"{",".join(COST_TYPES)}"',
        allow_blank=False,
    )
    cost_validation.error = "Selecione uma categoria permitida pelo Xano."
    cost_validation.errorTitle = "Tipo de custo inválido"
    cost_validation.showErrorMessage = True
    costs_sheet.add_data_validation(cost_validation)
    cost_validation.add("C2:C1000")

    quantity_validation = DataValidation(
        type="whole",
        operator="greaterThanOrEqual",
        formula1="1",
        allow_blank=False,
    )
    quantity_validation.error = "Quantidade deve ser um inteiro maior ou igual a 1."
    quantity_validation.showErrorMessage = True
    items_sheet.add_data_validation(quantity_validation)
    quantity_validation.add("F2:F1000")

    output = BytesIO()
    workbook.save(output)
    workbook.close()
    return output.getvalue()
