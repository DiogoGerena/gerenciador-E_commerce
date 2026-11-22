from copy import deepcopy
import hashlib
import html
import json
import logging
import math
import re
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from uuid import UUID, uuid4

import altair as alt
import pandas as pd
import requests
import streamlit as st

try:
    from app.erp_ui import (
        data_skeleton,
        render_dataframe,
        show_confirmation_dialog,
        show_toast,
    )
    from app.sale_dates import (
        format_sale_date,
        sale_date_from_unix_milliseconds,
        sale_date_to_unix_milliseconds,
    )
    from app.sales_excel_import import (
        ProductLookupError,
        build_sale_payload,
        create_sales_template,
        parse_sales_workbook,
        resolve_sale_products,
    )
    from app.xano_client import (
        USER_ROLES,
        OperacaoUsuarioInconclusivaError,
        OperacaoVendaInconclusivaError,
        RespostaUsuarioInconclusivaError,
        RespostaVendaInconclusivaError,
        RespostaCriacaoInconclusivaError,
        RespostaEntradaEstoqueInconclusivaError,
        RespostaOperacaoInconclusivaError,
        criar_entrada_estoque,
        criar_fornecedor,
        criar_produto,
        criar_usuario,
        criar_venda,
        editar_fornecedor,
        editar_produto,
        get_xano_config,
        inativar_fornecedor,
        inativar_produto,
        listar_categorias_ativas,
        listar_fornecedores,
        listar_movimentacoes_estoque,
        listar_produtos,
        listar_usuarios,
        listar_vendas,
        mapear_payload_entrada_estoque,
        consultar_venda,
        consultar_fornecedor,
        consultar_produto,
        consultar_metricas_vendas,
        validar_cnpj,
        validar_dados_usuario,
    )
except ModuleNotFoundError:  # pragma: no cover - compatibilidade com execução direta
    from erp_ui import (
        data_skeleton,
        render_dataframe,
        show_confirmation_dialog,
        show_toast,
    )
    from sale_dates import (
        format_sale_date,
        sale_date_from_unix_milliseconds,
        sale_date_to_unix_milliseconds,
    )
    from sales_excel_import import (
        ProductLookupError,
        build_sale_payload,
        create_sales_template,
        parse_sales_workbook,
        resolve_sale_products,
    )
    from xano_client import (
        USER_ROLES,
        OperacaoUsuarioInconclusivaError,
        OperacaoVendaInconclusivaError,
        RespostaUsuarioInconclusivaError,
        RespostaVendaInconclusivaError,
        RespostaCriacaoInconclusivaError,
        RespostaEntradaEstoqueInconclusivaError,
        RespostaOperacaoInconclusivaError,
        criar_entrada_estoque,
        criar_fornecedor,
        criar_produto,
        criar_usuario,
        criar_venda,
        editar_fornecedor,
        editar_produto,
        get_xano_config,
        inativar_fornecedor,
        inativar_produto,
        listar_categorias_ativas,
        listar_fornecedores,
        listar_movimentacoes_estoque,
        listar_produtos,
        listar_usuarios,
        listar_vendas,
        mapear_payload_entrada_estoque,
        consultar_venda,
        consultar_fornecedor,
        consultar_produto,
        consultar_metricas_vendas,
        validar_cnpj,
        validar_dados_usuario,
    )

logger = logging.getLogger(__name__)


def _redigir_mensagem_erro_xano(message):
    message = str(message).strip()
    message = re.sub(r"(?i)Bearer\s+\S+", "Bearer [redigido]", message)
    message = re.sub(
        r"(?i)Authorization\s*[:=]\s*(?:Bearer\s+)?\S+"
        r"(?:\s+\[redigido\])?",
        "[cabeçalho de autenticação redigido]",
        message,
    )
    message = re.sub(
        r"(?i)(access[_-]?token|auth[_-]?token)(\s*[:=]\s*|\s+)"
        r"(?:Bearer\s+)?[^\s,;]+",
        r"\1\2[redigido]",
        message,
    )
    message = re.sub(r"<[^>]*>", " ", message)
    message = re.sub(
        r"(?i)\b(password|senha|token|authorization|api[_-]?key|secret)"
        r"(\s*[:=]\s*|\s+)[^\s,;]+",
        r"\1\2[redigido]",
        message,
    )
    message = re.sub(r"(?i)\bBearer\s+\S+", "Bearer [redigido]", message)
    message = re.sub(
        r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
        "[e-mail redigido]",
        message,
        flags=re.IGNORECASE,
    )
    message = re.sub(r"\d{7,}", "[número redigido]", message)
    message = re.sub(r"https?://\S+", "[URL redigida]", message)
    return message[:240]


def _mensagem_erro_xano(
    error,
    method,
    endpoint,
    *,
    sensitive_values=(),
):
    response = getattr(error, "response", None)
    status_code = getattr(response, "status_code", None)
    if status_code is None:
        status_code = getattr(error, "status_code", None)
    details = [
        f"Requisição: {method} {endpoint}",
        f"Exceção: {type(error).__name__}",
    ]
    if isinstance(error, RespostaCriacaoInconclusivaError):
        details.append("Etapa: confirmação da resposta")
    if isinstance(error, RespostaOperacaoInconclusivaError):
        details.append("Etapa: confirmação da resposta")
    if isinstance(error, RespostaUsuarioInconclusivaError):
        details.append("Etapa: confirmação da resposta")
    if status_code is not None:
        details.append(f"HTTP: {status_code}")

    message = getattr(error, "backend_message", None)
    if response is not None:
        try:
            payload = response.json()
        except (ValueError, requests.RequestException):
            payload = None

        if isinstance(payload, dict):
            for key in ("message", "error", "description", "detail"):
                value = payload.get(key)
                if isinstance(value, str) and value.strip():
                    message = value.strip()
                    break

        if not message:
            content_type = getattr(response, "headers", {}).get(
                "Content-Type", ""
            )
            message = getattr(response, "text", "")
    elif not message:
        message = str(error)

    if message:
        safe_message = _redigir_mensagem_erro_xano(message)
        for value in sensitive_values:
            if isinstance(value, str) and value:
                safe_message = safe_message.replace(value, "[redigido]")
        details.append(f"Mensagem: {safe_message}")

    return " · ".join(details)


def _campos_movimentacao_para_diagnostico(movements):
    sensitive_field = re.compile(
        r"email|phone|telefone|address|endereco|cpf|cnpj|token|password|"
        r"senha|authorization|secret|api[_-]?key",
        re.IGNORECASE,
    )
    return sorted(
        {
            str(field)
            for movement in movements
            for field in movement
            if not sensitive_field.search(str(field))
        }
    )


def _render_diagnostico_integracao_movimentacoes():
    with st.expander("Diagnóstico da integração"):
        token = st.session_state.get("auth_token")
        try:
            config = get_xano_config()
        except (RuntimeError, ValueError):
            config = None

        config_found = bool(
            config and config.get("stock_movements_base_url")
        )
        st.write(
            "Token autenticado na sessão: "
            + ("encontrado" if token else "ausente")
        )
        st.write(
            "Configuração da URL do grupo: "
            + ("encontrada" if config_found else "ausente ou incompleta")
        )

        if st.button(
            "Executar diagnóstico (somente GET)",
            key="diagnostico_movimentacoes_submit",
            type="secondary",
        ):
            result = {
                "token_found": bool(token),
                "config_found": config_found,
                "query_executed": False,
            }
            if not token:
                result.update(
                    state="blocked",
                    message="Entre novamente para autenticar a sessão.",
                )
            elif not config_found:
                result.update(
                    state="blocked",
                    message=(
                        "A configuração do Xano está ausente ou incompleta; "
                        "a consulta não foi executada."
                    ),
                )
            else:
                result["query_executed"] = True
                try:
                    response = listar_movimentacoes_estoque(
                        token=token,
                        page=1,
                        per_page=20,
                    )
                except requests.HTTPError as error:
                    status_code = getattr(
                        getattr(error, "response", None),
                        "status_code",
                        None,
                    )
                    classifications = {
                        400: "Parâmetro ou validação rejeitada pelo endpoint.",
                        401: "Autenticação recusada pelo Xano.",
                        403: "Permissão insuficiente no Xano.",
                        404: "Endpoint não encontrado no Xano.",
                    }
                    if status_code is not None and status_code >= 500:
                        classifications[status_code] = (
                            "Erro interno retornado pelo servidor Xano."
                        )
                    result.update(
                        state="error",
                        status_code=status_code,
                        message=" ".join(
                            part
                            for part in (
                                classifications.get(
                                    status_code,
                                    "Falha na consulta GET ao Xano.",
                                ),
                                _mensagem_erro_xano(
                                    error,
                                    "GET",
                                    "/stock-movement",
                                    sensitive_values=(token,),
                                ),
                            )
                            if part
                        ),
                    )
                except requests.RequestException:
                    result.update(
                        state="error",
                        status_code=None,
                        message="Falha de conexão durante a consulta GET.",
                    )
                except (RuntimeError, ValueError):
                    result.update(
                        state="error",
                        status_code=None,
                        message=(
                            "A resposta ou configuração não corresponde "
                            "ao formato esperado."
                        ),
                    )
                else:
                    movements = response["movements"]
                    result.update(
                        state="success",
                        status_code=None,
                        count=len(movements),
                        fields=_campos_movimentacao_para_diagnostico(
                            movements
                        ),
                    )

            st.session_state["diagnostico_movimentacoes_resultado"] = result

        result = st.session_state.get(
            "diagnostico_movimentacoes_resultado"
        )
        if not result:
            st.caption(
                "A consulta só será feita após clicar no botão acima."
            )
            return

        st.write(
            "Token encontrado: "
            + ("sim" if result["token_found"] else "não")
        )
        st.write(
            "Configuração encontrada: "
            + ("sim" if result["config_found"] else "não")
        )
        st.write(
            "Consulta executada: "
            + ("sim" if result["query_executed"] else "não")
        )
        if result["state"] == "blocked":
            st.warning(result["message"])
        elif result["state"] == "error":
            status_code = result.get("status_code")
            st.write(
                "Status HTTP: "
                + (str(status_code) if status_code is not None else "indisponível")
            )
            st.error(result["message"])
        else:
            st.write("Status HTTP: não disponibilizado pela função de consulta.")
            st.success(
                f"Consulta concluída: {result['count']} movimentação(ões)."
            )
            st.write("Campos não sensíveis: " + (
                ", ".join(result["fields"]) if result["fields"] else "nenhum"
            ))


def _normalizar_valor_numerico(item, field):
    if field not in item or item[field] is None:
        return None, "unavailable"

    value = item[field]
    if isinstance(value, bool):
        return None, "invalid"
    try:
        numeric = float(value)
    except (TypeError, ValueError, OverflowError):
        return None, "invalid"
    if not math.isfinite(numeric):
        return None, "invalid"
    return numeric, "valid"


def _contar_registros_produtos(payload):
    if isinstance(payload, list):
        return len(payload)

    if not isinstance(payload, dict):
        return None

    for key in ("products", "data", "items", "results", "rows"):
        value = payload.get(key)
        if isinstance(value, list):
            return len(value)

    if "id" in payload or "name" in payload:
        return 1

    return None


def _calcular_indicadores_estoque(produtos):
    produtos = produtos or []
    total_produtos = len(produtos)
    produtos_quantidade_incompleta = sum(
        1 for item in produtos if item["stock_quantity_status"] != "valid"
    )
    produtos_valor_incompleto = sum(
        1 for item in produtos if item["valor_estimado_status"] != "valid"
    )
    produtos_classificacao_indeterminada = sum(
        1 for item in produtos if item["situacao"] == "Indeterminado"
    )
    total_unidades = (
        None
        if produtos_quantidade_incompleta
        else sum(item["stock_quantity"] for item in produtos)
    )
    produtos_baixos = sum(
        1 for item in produtos if item.get("situacao") == "Estoque baixo"
    )
    produtos_sem_estoque = sum(
        1 for item in produtos if item.get("situacao") == "Sem estoque"
    )
    valor_estoque = (
        None
        if produtos_valor_incompleto
        else sum(item["valor_estimado"] for item in produtos)
    )
    return {
        "total_produtos": total_produtos,
        "total_unidades": total_unidades,
        "produtos_baixos": produtos_baixos,
        "produtos_sem_estoque": produtos_sem_estoque,
        "valor_estoque": valor_estoque,
        "produtos_quantidade_incompleta": produtos_quantidade_incompleta,
        "produtos_valor_incompleto": produtos_valor_incompleto,
        "produtos_classificacao_indeterminada": (
            produtos_classificacao_indeterminada
        ),
    }


def _formatar_valor_estoque(value, status):
    if status == "unavailable":
        return "Indisponível"
    if status == "invalid":
        return "Inválido"
    return f"{value:g}"


def _normalizar_produtos_para_saldo(payload):
    if isinstance(payload, list):
        items = payload
    elif isinstance(payload, dict):
        items = None
        for key in ("products", "data", "items", "results", "rows"):
            candidate = payload.get(key)
            if isinstance(candidate, list):
                items = candidate
                break
        if items is None:
            return None
    else:
        return None

    normalized = []
    for item in items:
        if not isinstance(item, dict):
            return None

        product_id = item.get("id")
        if isinstance(product_id, str) and product_id.strip().isdigit():
            product_id = int(product_id.strip())
        if isinstance(product_id, bool) or not isinstance(product_id, int) or product_id < 1:
            return None

        name = item.get("name")
        if not isinstance(name, str) or not name.strip():
            return None

        sku = item.get("sku")
        if sku is None:
            sku = ""
        elif not isinstance(sku, str):
            return None
        sku = sku.strip()

        stock_quantity, stock_quantity_status = _normalizar_valor_numerico(
            item,
            "stock_quantity",
        )
        min_stock, min_stock_status = _normalizar_valor_numerico(
            item,
            "min_stock",
        )
        average_cost, average_cost_status = _normalizar_valor_numerico(
            item,
            "average_cost",
        )

        if stock_quantity_status != "valid":
            situation = "Indeterminado"
        elif stock_quantity <= 0:
            situation = "Sem estoque"
        elif min_stock_status != "valid":
            situation = "Indeterminado"
        elif stock_quantity <= min_stock:
            situation = "Estoque baixo"
        else:
            situation = "Normal"

        estimated_value = None
        estimated_value_status = "unavailable"
        if (
            stock_quantity_status == "invalid"
            or average_cost_status == "invalid"
        ):
            estimated_value_status = "invalid"
        elif (
            stock_quantity_status == "valid"
            and average_cost_status == "valid"
        ):
            estimated_value = stock_quantity * average_cost
            if math.isfinite(estimated_value):
                estimated_value_status = "valid"
            else:
                estimated_value = None
                estimated_value_status = "invalid"

        normalized.append(
            {
                "id": product_id,
                "produto": name.strip(),
                "sku": sku,
                "stock_quantity": stock_quantity,
                "stock_quantity_status": stock_quantity_status,
                "min_stock": min_stock,
                "min_stock_status": min_stock_status,
                "average_cost": average_cost,
                "average_cost_status": average_cost_status,
                "valor_estimado": estimated_value,
                "valor_estimado_status": estimated_value_status,
                "situacao": situation,
            }
        )

    return normalized


def _consultar_saldo_estoque(token):
    if not token:
        return "error", [], "Sua sessão expirou. Entre novamente para consultar o saldo."

    try:
        response = listar_produtos(token=token, status="ativo")
    except requests.HTTPError as error:
        return "error", [], _mensagem_erro_xano(error, "GET", "/product")
    except requests.RequestException as error:
        return "error", [], _mensagem_erro_xano(error, "GET", "/product")
    except (RuntimeError, ValueError) as error:
        return "error", [], _mensagem_erro_xano(error, "GET", "/product")

    products = _normalizar_produtos_para_saldo(response)
    if products is None:
        return (
            "error",
            [],
            "GET /product retornou um formato inesperado; não foi possível montar o saldo de estoque.",
        )

    return "success", products, None


def _extrair_produtos_para_exibicao(payload):
    if isinstance(payload, list):
        products = payload
    elif isinstance(payload, dict):
        products = None
        for key in ("products", "data", "items", "results", "rows"):
            candidate = payload.get(key)
            if isinstance(candidate, list):
                products = candidate
                break
        if products is None:
            return None
    else:
        return None

    if any(not isinstance(product, dict) or "name" not in product for product in products):
        return None

    allowed_fields = (
        "id",
        "name",
        "description",
        "category_id",
        "min_stock",
        "sale_price",
        "sku",
        "status",
    )
    return [
        {field: product[field] for field in allowed_fields if field in product}
        for product in products
    ]


def _texto_interface(value, fallback="Não informado"):
    if isinstance(value, str):
        return value.strip() or fallback
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    return fallback


def _formatar_valor_monetario_br(value):
    if value is None or value == "" or isinstance(value, bool):
        return "Não informado"
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return "Não informado"
    if not amount.is_finite():
        return "Não informado"
    formatted = format(amount, ",.2f")
    formatted = formatted.replace(",", "\0").replace(".", ",").replace("\0", ".")
    return f"R$ {formatted}"


def _formatar_quantidade_br(value):
    if value is None or value == "" or isinstance(value, bool):
        return "Não informado"
    try:
        quantity = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return "Não informado"
    if not quantity.is_finite():
        return "Não informado"
    formatted = format(quantity, "f")
    if "." in formatted:
        formatted = formatted.rstrip("0").rstrip(".")
    formatted = formatted.replace(".", ",")
    unit = "unidade" if quantity == 1 else "unidades"
    return f"{formatted} {unit}"


def _rotulo_status(status):
    normalized = status.strip().lower() if isinstance(status, str) else ""
    labels = {
        "ativo": "Ativo",
        "active": "Ativo",
        "inativo": "Inativo",
        "inactive": "Inativo",
    }
    return labels.get(
        normalized,
        normalized.replace("_", " ").capitalize() or "Não informado",
    )


def _render_status_badge(status):
    label = _rotulo_status(status)
    normalized = str(status or "").strip().lower()
    badge_class = (
        "is-active"
        if normalized in {"ativo", "active"}
        else "is-inactive"
        if normalized in {"inativo", "inactive"}
        else "is-neutral"
    )
    st.markdown(
        f"<span class='cb-status-badge {badge_class}'>"
        f"{html.escape(label)}</span>",
        unsafe_allow_html=True,
    )


def _nome_categoria_produto(product, categories):
    category_id = product.get("category_id")
    if isinstance(category_id, dict):
        category = category_id
        category_id = category.get("id")
        category_name = category.get("name")
        if isinstance(category_name, str) and category_name.strip():
            return category_name.strip()
    category = product.get("category")
    if isinstance(category, dict):
        category_name = category.get("name")
        if isinstance(category_name, str) and category_name.strip():
            return category_name.strip()
        category_id = category.get("id", category_id)
    for item in categories:
        if str(item.get("id")) == str(category_id):
            name = item.get("name")
            return name.strip() if isinstance(name, str) and name.strip() else "Não informada"
    return "Não informada"


def _tabela_produtos_para_interface(products, categories):
    rows = [
        {
            "Produto": _texto_interface(product.get("name")),
            "SKU": _texto_interface(product.get("sku")),
            "Categoria": _nome_categoria_produto(product, categories),
            "Situação": _rotulo_status(product.get("status")),
            "Estoque mínimo": _formatar_quantidade_br(product.get("min_stock")),
            "Preço de venda": _formatar_valor_monetario_br(
                product.get("sale_price")
            ),
        }
        for product in products
    ]
    return pd.DataFrame(
        rows,
        columns=[
            "Produto",
            "SKU",
            "Categoria",
            "Situação",
            "Estoque mínimo",
            "Preço de venda",
        ],
    )


def _render_detalhe_produto(product, categories):
    st.subheader("Detalhes do produto")
    with st.container(border=True):
        title_column, status_column = st.columns([3, 1])
        with title_column:
            name = _texto_interface(product.get("name"))
            st.markdown(f"#### {html.escape(name)}")
        with status_column:
            st.markdown("**Situação**")
            _render_status_badge(product.get("status"))

        columns = st.columns(3)
        metrics = (
            ("SKU", _texto_interface(product.get("sku"))),
            ("Categoria", _nome_categoria_produto(product, categories)),
            ("Estoque disponível", _formatar_quantidade_br(product.get("stock_quantity"))),
            ("Estoque mínimo", _formatar_quantidade_br(product.get("min_stock"))),
            ("Preço de venda", _formatar_valor_monetario_br(product.get("sale_price"))),
            ("Custo médio", _formatar_valor_monetario_br(product.get("average_cost"))),
        )
        for index, (label, value) in enumerate(metrics):
            with columns[index % len(columns)]:
                st.metric(label, value)

        description = product.get("description")
        st.markdown("**Descrição**")
        st.write(
            description.strip()
            if isinstance(description, str) and description.strip()
            else "Não informada"
        )


def _consultar_produtos_por_nome(
    token,
    name,
    *,
    category_id=None,
    status=None,
):
    name = str(name or "").strip()
    if not name:
        return "empty_query", [], None
    if not token:
        return "error", [], "Sua sessão expirou. Entre novamente para pesquisar produtos."

    filters = {}
    if category_id is not None:
        if (
            isinstance(category_id, bool)
            or not isinstance(category_id, int)
            or category_id < 1
        ):
            return "validation", [], "Selecione uma categoria válida."
        filters["category_id"] = category_id

    if status is not None:
        if not isinstance(status, str):
            return "validation", [], "O status deve ser texto."
        status = status.strip()
        if status:
            filters["status"] = status

    try:
        response = listar_produtos(token=token, name=name, **filters)
    except Exception as error:
        return "error", [], _mensagem_erro_xano(error, "GET", "/product")

    products = _extrair_produtos_para_exibicao(response)
    if products is None:
        return (
            "error",
            [],
            "GET /product retornou um formato não reconhecido. Nenhum resultado foi exibido.",
        )

    return "success", products, None


def _consultar_fornecedores(token, *, name=None, status=None):
    if not token:
        return "error", [], "Sua sessão expirou. Entre novamente para consultar fornecedores."

    filters = {}
    if name is not None and str(name).strip():
        filters["name"] = str(name).strip()
    filters["status"] = str(status or "").strip() or "ativo"

    try:
        return "success", listar_fornecedores(token=token, **filters), None
    except requests.HTTPError as error:
        return "error", [], _mensagem_erro_xano(error, "GET", "/supplier")
    except requests.RequestException as error:
        return "error", [], _mensagem_erro_xano(error, "GET", "/supplier")
    except (RuntimeError, ValueError) as error:
        return "error", [], _mensagem_erro_xano(error, "GET", "/supplier")


def _executar_operacao_cadastral(operation, method, endpoint, *, sensitive_values=()):
    try:
        return "success", operation(), None
    except RespostaOperacaoInconclusivaError as error:
        return (
            "inconclusive",
            None,
            _mensagem_erro_xano(
                error,
                method,
                endpoint,
                sensitive_values=sensitive_values,
            ),
        )
    except requests.HTTPError as error:
        return (
            "error",
            None,
            _mensagem_erro_xano(
                error,
                method,
                endpoint,
                sensitive_values=sensitive_values,
            ),
        )
    except requests.RequestException as error:
        return (
            "error",
            None,
            _mensagem_erro_xano(
                error,
                method,
                endpoint,
                sensitive_values=sensitive_values,
            ),
        )
    except ValueError as error:
        return "validation", None, _redigir_mensagem_erro_xano(error)
    except RuntimeError as error:
        return (
            "error",
            None,
            _mensagem_erro_xano(
                error,
                method,
                endpoint,
                sensitive_values=sensitive_values,
            ),
        )


def _consultar_produto_por_id(token, product_id):
    return _executar_operacao_cadastral(
        lambda: consultar_produto(token, product_id),
        "GET",
        f"/product/{product_id}",
    )


def _salvar_edicao_produto(token, product_id, **fields):
    return _executar_operacao_cadastral(
        lambda: editar_produto(token, product_id, **fields),
        "PATCH",
        f"/product/{product_id}",
    )


def _inativar_produto(token, product_id):
    return _executar_operacao_cadastral(
        lambda: inativar_produto(token, product_id),
        "PATCH",
        f"/product/{product_id}/deactivate",
    )


def _cadastrar_fornecedor(token, **fields):
    return _executar_operacao_cadastral(
        lambda: criar_fornecedor(token, **fields),
        "POST",
        "/supplier",
        sensitive_values=tuple(fields.values()),
    )


def _consultar_fornecedor_por_id(token, supplier_id):
    return _executar_operacao_cadastral(
        lambda: consultar_fornecedor(token, supplier_id),
        "GET",
        f"/supplier/{supplier_id}",
    )


def _salvar_edicao_fornecedor(token, supplier_id, **fields):
    return _executar_operacao_cadastral(
        lambda: editar_fornecedor(token, supplier_id, **fields),
        "PATCH",
        f"/supplier/{supplier_id}",
        sensitive_values=tuple(fields.values()),
    )


def _inativar_fornecedor(token, supplier_id):
    return _executar_operacao_cadastral(
        lambda: inativar_fornecedor(token, supplier_id),
        "PATCH",
        f"/supplier/{supplier_id}/deactivate",
    )


def _carregar_fornecedores_entrada(token):
    if not token:
        return [], "Sua sessão expirou. Entre novamente para carregar fornecedores."

    try:
        return listar_fornecedores(token=token, status="ativo"), None
    except requests.HTTPError as error:
        return [], _mensagem_erro_xano(error, "GET", "/supplier")
    except requests.RequestException as error:
        return [], _mensagem_erro_xano(error, "GET", "/supplier")
    except (RuntimeError, ValueError) as error:
        return [], _mensagem_erro_xano(error, "GET", "/supplier")


def _extrair_produtos_para_entrada(payload):
    if isinstance(payload, list):
        products = payload
    elif isinstance(payload, dict):
        products = next(
            (
                payload[key]
                for key in ("products", "data", "items", "results", "rows")
                if isinstance(payload.get(key), list)
            ),
            None,
        )
        if products is None:
            return None
    else:
        return None

    normalized = []
    for product in products:
        if not isinstance(product, dict):
            return None
        product_id = product.get("id")
        if isinstance(product_id, str) and product_id.strip().isdigit():
            product_id = int(product_id.strip())
        name = product.get("name")
        if (
            isinstance(product_id, bool)
            or not isinstance(product_id, int)
            or product_id < 1
            or not isinstance(name, str)
            or not name.strip()
        ):
            return None
        normalized_product = {"id": product_id, "name": name.strip()}
        sku = product.get("sku")
        if sku is not None:
            if not isinstance(sku, str):
                return None
            if sku.strip():
                normalized_product["sku"] = sku.strip()
        normalized.append(normalized_product)
    return normalized


def _consultar_produtos_para_entrada(token, name):
    name = str(name or "").strip()
    if not name:
        return "validation", [], "Informe um nome para pesquisar produtos."
    if not token:
        return "error", [], "Sua sessão expirou. Entre novamente para pesquisar produtos."

    try:
        payload = listar_produtos(token=token, name=name)
    except requests.HTTPError as error:
        return "error", [], _mensagem_erro_xano(error, "GET", "/product")
    except requests.RequestException as error:
        return "error", [], _mensagem_erro_xano(error, "GET", "/product")
    except (RuntimeError, ValueError) as error:
        return "error", [], _mensagem_erro_xano(error, "GET", "/product")

    products = _extrair_produtos_para_entrada(payload)
    if products is None:
        return (
            "error",
            [],
            "GET /product retornou uma resposta inesperada; nenhum produto foi exibido.",
        )
    return "success", products, None


def _normalizar_movimentacoes_para_tabela(movements):
    def format_timestamp(value):
        if value in (None, "", " "):
            return "—"
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return "—"
            if text.endswith("Z"):
                text = text[:-1] + "+00:00"
            try:
                parsed = pd.Timestamp(text)
            except (TypeError, ValueError):
                return text
            return parsed.strftime("%d/%m/%Y %H:%M")
        try:
            return pd.Timestamp(value).strftime("%d/%m/%Y %H:%M")
        except (TypeError, ValueError):
            return str(value)

    def format_decimal(value):
        if value in (None, "", " "):
            return "—"
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return str(value)
        if math.isnan(numeric):
            return "—"
        return numeric

    def format_movement_type(value):
        normalized = str(value or "").strip()
        if not normalized:
            return "Não informado"
        normalized_key = normalized.casefold().replace(" ", "_")
        labels = {
            "inbound": "Entrada",
            "entrada": "Entrada",
            "stock_in": "Entrada",
            "outbound": "Saída",
            "saida": "Saída",
            "stock_out": "Saída",
            "adjustment": "Ajuste",
            "ajuste": "Ajuste",
            "manual_adjustment": "Ajuste",
            "reservation": "Reserva",
            "reserva": "Reserva",
            "cancelled": "Cancelada",
            "cancelada": "Cancelada",
            "return": "Devolução",
            "devolucao": "Devolução",
        }
        return labels.get(normalized_key, normalized)

    rows = []
    known_keys = {
        "created_at",
        "movement_date",
        "date",
        "movement_type",
        "movement",
        "type",
        "quantity",
        "quantity_before",
        "quantity_after",
        "unit_cost",
        "unit_price",
        "reference_type",
        "reference_kind",
        "reference_id",
        "reference",
        "document_number",
        "product_name",
        "product",
        "product_id",
    }
    for movement in movements or []:
        if not isinstance(movement, dict):
            continue
        row = {
            "Data da movimentação": format_timestamp(
                movement.get("created_at")
                or movement.get("movement_date")
                or movement.get("date")
            ),
            "Tipo de movimentação": format_movement_type(
                movement.get("movement_type")
                or movement.get("movement")
                or movement.get("type")
            ),
            "Quantidade": format_decimal(
                movement.get("quantity")
            ),
            "Quantidade anterior": format_decimal(
                movement.get("quantity_before")
            ),
            "Quantidade posterior": format_decimal(
                movement.get("quantity_after")
            ),
            "Custo unitário": format_decimal(
                movement.get("unit_cost")
                or movement.get("unit_price")
            ),
            "Tipo de referência": str(
                movement.get("reference_type")
                or movement.get("reference_kind")
                or "—"
            ),
            "Referência": str(
                movement.get("reference_id")
                or movement.get("reference")
                or movement.get("document_number")
                or "—"
            ),
            "Produto": str(
                movement.get("product_name")
                or movement.get("product")
                or movement.get("product_id")
                or "—"
            ),
        }
        extras = []
        for key, value in movement.items():
            if key not in known_keys:
                extras.append(f"{key}: {value}")
        if extras:
            row["Dados adicionais"] = " | ".join(extras)
        rows.append(row)
    return pd.DataFrame(rows)


def _render_historico_movimentacoes():
    if st.checkbox("Mostrar diagnóstico técnico do Xano", value=False, key="show_xano_debug"):
        _render_diagnostico_integracao_movimentacoes()
    st.markdown(
        "<div class='erp-panel-header'><div class='erp-panel-title'>"
        "Histórico real de movimentações</div></div>",
        unsafe_allow_html=True,
    )
    token = st.session_state.get("auth_token")

    def active_filter_values():
        return (
            st.session_state.get("historico_movimentacoes_product_id", 0),
            st.session_state.get("historico_movimentacoes_start_date", ""),
            st.session_state.get("historico_movimentacoes_end_date", ""),
            st.session_state.get("historico_movimentacoes_per_page", 20),
        )

    def prepare_query():
        filter_values = active_filter_values()
        previous_values = st.session_state.get(
            "historico_movimentacoes_filtros"
        )
        if previous_values is not None and filter_values != previous_values:
            st.session_state["historico_movimentacoes_page"] = 1
        st.session_state["historico_movimentacoes_filtros"] = filter_values

    def navigate_page(direction):
        page_key = "historico_movimentacoes_page"
        current_page = int(st.session_state.get(page_key, 1))
        st.session_state[page_key] = max(1, current_page + direction)
        st.session_state["historico_movimentacoes_consultar"] = True

    with st.form("historico_movimentacoes_form"):
        filters = st.columns(2)
        with filters[0]:
            product_id = st.number_input(
                "ID do produto (opcional)",
                min_value=0,
                value=0,
                step=1,
                help="Use 0 para consultar sem filtro por produto.",
                key="historico_movimentacoes_product_id",
            )
            start_date = st.text_input(
                "Data inicial (timestamp)",
                help="Informe o formato aceito pelo endpoint do Xano.",
                key="historico_movimentacoes_start_date",
            )
        with filters[1]:
            page = st.number_input(
                "Página",
                min_value=1,
                step=1,
                key="historico_movimentacoes_page",
            )
            end_date = st.text_input(
                "Data final (timestamp)",
                help="Informe o formato aceito pelo endpoint do Xano.",
                key="historico_movimentacoes_end_date",
            )
        per_page = st.number_input(
            "Registros por página",
            min_value=1,
            max_value=100,
            value=20,
            step=1,
            key="historico_movimentacoes_per_page",
        )
        submitted = st.form_submit_button(
            "Consultar movimentações",
            type="secondary",
            disabled=not token,
            on_click=prepare_query,
            key="historico_movimentacoes_submit",
        )
    navigation_requested = st.session_state.pop(
        "historico_movimentacoes_consultar",
        False,
    )
    submitted = submitted or navigation_requested
    st.caption(
        "O filtro por tipo de movimentação fica indisponível até confirmar "
        "os valores aceitos pelo enum do Xano."
    )

    if not token:
        st.warning("Sua sessão expirou. Entre novamente para consultar o histórico.")
        return

    if submitted:
        params = {
            "product_id": int(product_id) if product_id else None,
            "start_date": start_date or None,
            "end_date": end_date or None,
            "page": int(page),
            "per_page": int(per_page),
        }
        try:
            with data_skeleton("table"), st.spinner(
                "Consultando movimentações no Xano..."
            ):
                response = listar_movimentacoes_estoque(token=token, **params)
            if not isinstance(response, dict):
                raise ValueError(
                    "O Xano retornou uma estrutura inválida de movimentações."
                )
            movements = response.get("movements")
            if not isinstance(movements, list):
                movements = response.get("items")
            if not isinstance(movements, list) or any(
                not isinstance(movement, dict) for movement in movements
            ):
                raise ValueError(
                    "O Xano retornou uma estrutura inválida de movimentações."
                )
        except requests.HTTPError as error:
            status_code = getattr(
                getattr(error, "response", None),
                "status_code",
                None,
            )
            backend_message = _mensagem_erro_xano(
                error,
                "GET",
                "/stock-movement",
                sensitive_values=(token,),
            )
            if status_code == 401:
                prefix = (
                    "Sua sessão expirou ou não foi aceita pelo Xano. "
                    "Entre novamente para consultar o histórico."
                )
            elif status_code == 403:
                prefix = (
                    "Seu perfil não tem permissão para consultar movimentações."
                )
            else:
                prefix = ""
            message = " · ".join(
                part for part in (prefix, backend_message) if part
            )
            st.session_state["historico_movimentacoes_resultado"] = {
                "state": "error",
                "message": message,
            }
        except requests.RequestException as error:
            st.session_state["historico_movimentacoes_resultado"] = {
                "state": "error",
                "message": _mensagem_erro_xano(
                    error,
                    "GET",
                    "/stock-movement",
                    sensitive_values=(token,),
                ),
            }
        except (RuntimeError, ValueError) as error:
            st.session_state["historico_movimentacoes_resultado"] = {
                "state": "error",
                "message": _mensagem_erro_xano(
                    error,
                    "GET",
                    "/stock-movement",
                    sensitive_values=(token,),
                ),
            }
        else:
            st.session_state["historico_movimentacoes_resultado"] = {
                "state": "success",
                "response": response,
                "movements": movements,
                "page": int(page),
                "per_page": int(per_page),
            }

    result = st.session_state.get("historico_movimentacoes_resultado")
    if not result:
        st.info("Consulte o Xano para carregar o histórico de movimentações.")
    elif result["state"] == "error":
        st.error(result["message"])
    else:
        st.caption(
            f"Página {result['page']} · {len(result['movements'])} "
            "movimentação(ões) retornada(s)"
        )
        if result["movements"]:
            dataframe = _normalizar_movimentacoes_para_tabela(
                result["movements"]
            )
            render_dataframe(dataframe, width="stretch", hide_index=True)
        else:
            st.info("Não existem movimentações para os filtros selecionados.")

        navigation = st.columns(2)
        with navigation[0]:
            st.button(
                "Página anterior",
                disabled=result["page"] <= 1,
                key="historico_movimentacoes_previous",
                on_click=navigate_page,
                args=(-1,),
            )
        with navigation[1]:
            st.button(
                "Próxima página",
                key="historico_movimentacoes_next",
                on_click=navigate_page,
                args=(1,),
            )


_ENTRADAS_ESTOQUE_OPERACOES_KEY = "entradas_estoque_operacoes"
_ENTRADA_ESTOQUE_WIDGET_KEYS = (
    "entrada_estoque_product",
    "entrada_estoque_supplier",
    "entrada_estoque_quantity",
    "entrada_estoque_unit_cost",
    "entrada_estoque_date",
    "entrada_estoque_invoice",
    "entrada_estoque_notes",
    "entrada_estoque_freight",
    "entrada_estoque_other_costs",
)


def _identidade_usuario_entrada_estoque(usuario):
    if not isinstance(usuario, dict):
        return None

    for field in ("id", "user_id", "userId"):
        value = usuario.get(field)
        if isinstance(value, bool) or value is None:
            continue
        identifier = str(value).strip()
        if identifier:
            return f"id:{identifier}"

    email = usuario.get("email")
    if isinstance(email, str) and email.strip():
        return f"email:{email.strip().casefold()}"

    return None


def _obter_operacoes_entrada_estoque(session_state=None):
    state = st.session_state if session_state is None else session_state
    operations = state.get(_ENTRADAS_ESTOQUE_OPERACOES_KEY)
    if operations is None:
        operations = {}
        state[_ENTRADAS_ESTOQUE_OPERACOES_KEY] = operations
    if not isinstance(operations, dict):
        raise RuntimeError("O estado das entradas de estoque está inválido.")
    if any(not isinstance(operation, dict) for operation in operations.values()):
        raise RuntimeError("O histórico de entradas de estoque está inválido.")
    return state, operations


def _operacao_entrada_estoque_pendente(session_state=None):
    _, operations = _obter_operacoes_entrada_estoque(session_state)
    pending = [
        operation
        for operation in operations.values()
        if operation.get("status") == "pending"
    ]
    if len(pending) > 1:
        raise RuntimeError(
            "Há mais de uma entrada de estoque pendente nesta sessão."
        )
    return pending[0] if pending else None


def _resolver_operacao_entrada_estoque(
    idempotency_key,
    *,
    owner_identity,
    outcome,
    note="",
    session_state=None,
):
    if outcome not in {"recorded", "not_found"}:
        raise ValueError("O resultado da conferência manual é inválido.")

    _, operations = _obter_operacoes_entrada_estoque(session_state)
    operation = operations.get(idempotency_key)
    if (
        not isinstance(operation, dict)
        or operation.get("status") != "pending"
        or operation.get("owner_identity") != owner_identity
    ):
        return False

    operation["status"] = (
        "manually_verified_recorded"
        if outcome == "recorded"
        else "manually_verified_not_found"
    )
    operation["resolution"] = {
        "outcome": outcome,
        "owner_identity": owner_identity,
        "note": str(note or "").strip(),
    }
    operation["message"] = (
        "Resultado conferido manualmente no Xano. O POST original não foi "
        "reenviado; a operação original foi preservada no histórico."
    )
    return True


def _enviar_formulario_entrada(
    token,
    produtos,
    fornecedores,
    *,
    product_id,
    supplier_id,
    quantity,
    unit_purchase_cost,
    entry_date,
    invoice_number,
    notes,
    idempotency_key=None,
    inbound_freight=None,
    other_acquisition_costs=None,
    session_state=None,
):
    state, operations = _obter_operacoes_entrada_estoque(session_state)
    if _operacao_entrada_estoque_pendente(state) is not None:
        return (
            "blocked",
            "Há uma entrada com resultado desconhecido. Verifique-a no Xano "
            "antes de iniciar outro lançamento.",
            None,
        )

    owner_identity = _identidade_usuario_entrada_estoque(
        state.get("auth_user")
    )
    if not owner_identity:
        return (
            "validation",
            "Não foi possível identificar o usuário autenticado. "
            "Nenhuma entrada foi enviada.",
            None,
        )

    product_ids = {
        product.get("id")
        for product in produtos
        if isinstance(product, dict)
    }
    supplier_ids = {
        supplier.get("id")
        for supplier in fornecedores
        if isinstance(supplier, dict)
    }
    if (
        isinstance(product_id, bool)
        or not isinstance(product_id, int)
        or product_id < 1
    ):
        return "validation", "Selecione um produto válido.", None
    if (
        isinstance(supplier_id, bool)
        or not isinstance(supplier_id, int)
        or supplier_id < 1
    ):
        return "validation", "Selecione um fornecedor ativo válido.", None
    if product_id not in product_ids:
        return "validation", "Selecione um produto válido.", None
    if supplier_id not in supplier_ids:
        return "validation", "Selecione um fornecedor ativo válido.", None
    if not str(invoice_number or "").strip():
        return "validation", "Informe o número da nota fiscal.", None
    if not str(notes or "").strip():
        return "validation", "Informe as observações da entrada.", None

    if not token:
        return "error", "Sua sessão expirou. Entre novamente para registrar.", None

    if idempotency_key is None:
        idempotency_key = str(uuid4())

    form_data = {
        "product_id": product_id,
        "supplier_id": supplier_id,
        "quantity": quantity,
        "unit_purchase_cost": unit_purchase_cost,
        "entry_date": entry_date,
        "invoice_number": str(invoice_number).strip(),
        "notes": str(notes).strip(),
        "inbound_freight": inbound_freight,
        "other_acquisition_costs": other_acquisition_costs,
    }
    try:
        payload = mapear_payload_entrada_estoque(
            idempotency_key=idempotency_key,
            **form_data,
        )
    except ValueError as error:
        return "validation", str(error), None

    if idempotency_key in operations:
        return (
            "blocked",
            "Esta chave já pertence a uma operação registrada e não pode "
            "ser reutilizada.",
            None,
        )

    operation = {
        "idempotency_key": idempotency_key,
        "owner_identity": owner_identity,
        "form_data": deepcopy(form_data),
        "payload": deepcopy(payload),
        "status": "pending",
        "message": (
            "O resultado do envio ainda não foi confirmado. "
            "Não reenvie; confira a entrada no Xano."
        ),
        "error": None,
        "response": None,
        "resolution": None,
    }
    operations[idempotency_key] = operation

    def mark_pending(error):
        message = _mensagem_erro_xano(error, "POST", "/stock-entry")
        logger.warning("%s", message)
        operation["status"] = "pending"
        operation["error"] = message
        operation["message"] = (
            message
            + " · Resultado desconhecido. O envio não será repetido. "
            "Confira manualmente a chave e os dados no Xano antes de "
            "liberar outro lançamento."
        )
        return "inconclusive", operation["message"], None

    try:
        response = criar_entrada_estoque(token, **deepcopy(payload))
    except RespostaEntradaEstoqueInconclusivaError as error:
        return mark_pending(error)
    except requests.HTTPError as error:
        return mark_pending(error)
    except requests.RequestException as error:
        return mark_pending(error)
    except (RuntimeError, ValueError) as error:
        return mark_pending(error)

    operation["status"] = "confirmed"
    operation["message"] = "Entrada registrada com confirmação do serviço."
    operation["response"] = deepcopy(response)
    return "success", "Entrada registrada com confirmação do serviço.", response


def _rotulo_opcao_entrada(item, items):
    name = item["name"]
    matches = [
        candidate
        for candidate in items
        if candidate["name"].casefold() == name.casefold()
    ]
    if len(matches) < 2:
        return name

    identifier = item.get("cnpj") or item.get("email") or item.get("sku")
    if not identifier:
        identifier = f"ID {item['id']}"
    return f"{name} · {identifier}"


def _custo_opcional(text, label):
    text = str(text or "").strip()
    if not text:
        return None, None
    try:
        value = float(text)
    except ValueError:
        return None, f"{label} deve ser um valor numérico."
    if not math.isfinite(value) or value < 0:
        return None, f"{label} deve ser maior ou igual a zero."
    return value, None


def _render_operacao_entrada_estoque_pendente(operation, owner_identity):
    st.error(
        "Há uma entrada de estoque cujo resultado não foi confirmado. "
        "Nenhum novo lançamento será enviado até a conferência."
    )
    if owner_identity != operation.get("owner_identity"):
        st.info(
            "A operação pertence a outra identidade autenticada. "
            "Entre com o usuário original para conferir o resultado."
        )
        return

    st.warning(operation.get("message") or "Confira a operação no Xano.")
    st.caption("Chave da operação original")
    st.code(operation["idempotency_key"])
    st.json(operation["payload"])
    st.info(
        "Não há reconciliação automática comprovada. A conferência abaixo "
        "não reenvia o POST; ela apenas registra sua verificação manual no Xano."
    )

    conferido = st.checkbox(
        "Conferi a chave e os dados da operação no Xano",
        key="entrada_estoque_reconciliacao_confirmado",
    )
    observacao = st.text_input(
        "Observação da conferência (opcional)",
        key="entrada_estoque_reconciliacao_observacao",
    )
    resolution_columns = st.columns(2)
    with resolution_columns[0]:
        registrada = st.button(
            "Confirmar: entrada localizada",
            disabled=not conferido,
            key="entrada_estoque_reconciliacao_registrada",
        )
    with resolution_columns[1]:
        nao_registrada = st.button(
            "Confirmar: não localizada",
            disabled=not conferido,
            key="entrada_estoque_reconciliacao_nao_registrada",
        )

    if registrada or nao_registrada:
        outcome = "recorded" if registrada else "not_found"
        resolved = _resolver_operacao_entrada_estoque(
            operation["idempotency_key"],
            owner_identity=owner_identity,
            outcome=outcome,
            note=observacao,
        )
        if not resolved:
            st.error(
                "A operação não pôde ser liberada. Confira novamente o estado "
                "e a identidade autenticada."
            )
            return
        st.success(
            "Conferência registrada. A operação original foi preservada; "
            "nenhum POST foi repetido."
        )
        st.rerun()


def _render_formulario_entrada_estoque():
    st.subheader("Entrada de estoque")
    feedback = st.session_state.pop("entrada_estoque_feedback", None)
    if feedback:
        level, message = feedback
        if level == "warning":
            st.warning(message)
        else:
            st.error(message)
    if st.session_state.pop("entrada_estoque_toast_pending", False):
        show_toast("Entrada registrada com confirmação do serviço.")

    if st.session_state.pop("entrada_estoque_reset_form", False):
        for key in _ENTRADA_ESTOQUE_WIDGET_KEYS:
            st.session_state.pop(key, None)

    token = st.session_state.get("auth_token")
    owner_identity = _identidade_usuario_entrada_estoque(
        st.session_state.get("auth_user")
    )
    pending_operation = _operacao_entrada_estoque_pendente()
    if pending_operation:
        _render_operacao_entrada_estoque_pendente(
            pending_operation,
            owner_identity,
        )
        return
    if not owner_identity:
        st.error(
            "Não foi possível identificar o usuário autenticado. "
            "Nenhuma entrada de estoque pode ser enviada."
        )
        return

    fornecedores, supplier_error = _carregar_fornecedores_entrada(token)
    if supplier_error:
        st.error(supplier_error)
        st.button(
            "Tentar carregar fornecedores novamente",
            key="entrada_estoque_retry_suppliers",
        )
    elif not fornecedores:
        st.info("Nenhum fornecedor ativo está disponível para seleção.")

    search_col, button_col = st.columns([3, 1])
    with search_col:
        product_query = st.text_input(
            "Buscar produto pelo nome",
            key="entrada_estoque_product_query",
            placeholder="Digite o nome do produto",
        )
    with button_col:
        st.write("")
        search_products = st.button(
            "Buscar produtos",
            key="entrada_estoque_search_products",
            disabled=not token,
            type="secondary",
        )

    if search_products:
        state, products, error = _consultar_produtos_para_entrada(
            token,
            product_query,
        )
        st.session_state["entrada_estoque_products"] = (
            products if state == "success" else []
        )
        st.session_state["entrada_estoque_products_state"] = state
        st.session_state["entrada_estoque_products_error"] = error

    products = st.session_state.get("entrada_estoque_products", [])
    product_state = st.session_state.get("entrada_estoque_products_state")
    product_error = st.session_state.get("entrada_estoque_products_error")
    if product_state == "error" and product_error:
        st.error(product_error)
    elif product_state == "validation" and product_error:
        st.info(product_error)
    elif product_state == "success" and not products:
        st.info("Nenhum produto encontrado para essa busca.")

    if not fornecedores or not products:
        if fornecedores:
            st.info("Pesquise um produto para preencher a entrada.")
        return

    with st.form("entrada_estoque_form"):
        product = st.selectbox(
            "Produto",
            products,
            format_func=lambda item: _rotulo_opcao_entrada(item, products),
            key="entrada_estoque_product",
        )
        supplier = st.selectbox(
            "Fornecedor",
            fornecedores,
            format_func=lambda item: _rotulo_opcao_entrada(item, fornecedores),
            key="entrada_estoque_supplier",
        )
        first_row = st.columns(2)
        with first_row[0]:
            quantity = st.number_input(
                "Quantidade recebida",
                min_value=1,
                value=1,
                step=1,
                key="entrada_estoque_quantity",
            )
        with first_row[1]:
            unit_purchase_cost = st.number_input(
                "Custo unitário de aquisição",
                min_value=0.0,
                value=0.0,
                step=0.01,
                key="entrada_estoque_unit_cost",
            )
        second_row = st.columns(2)
        with second_row[0]:
            entry_date = st.date_input(
                "Data da entrada",
                value=date.today(),
                key="entrada_estoque_date",
            )
        with second_row[1]:
            invoice_number = st.text_input(
                "Número da nota fiscal",
                key="entrada_estoque_invoice",
            )
        notes = st.text_area(
            "Observações",
            key="entrada_estoque_notes",
        )
        third_row = st.columns(2)
        with third_row[0]:
            inbound_freight_text = st.text_input(
                "Frete de entrada (opcional)",
                key="entrada_estoque_freight",
                help="Deixe vazio para omitir. Use ponto como separador decimal.",
            )
        with third_row[1]:
            other_costs_text = st.text_input(
                "Outros custos de aquisição (opcional)",
                key="entrada_estoque_other_costs",
                help="Deixe vazio para omitir. Use ponto como separador decimal.",
            )
        submitted = st.form_submit_button(
            "Registrar entrada",
            type="primary",
            disabled=not token,
            width="stretch",
            key="entrada_estoque_submit",
        )

    if submitted:
        st.session_state.pop("entrada_estoque_success", None)
        freight, freight_error = _custo_opcional(
            inbound_freight_text,
            "Frete",
        )
        other_costs, other_costs_error = _custo_opcional(
            other_costs_text,
            "Outros custos",
        )
        validation_error = freight_error or other_costs_error
        if validation_error:
            st.error(validation_error)
            return

        if not str(invoice_number or "").strip():
            st.error("Informe o número da nota fiscal.")
            return
        if not str(notes or "").strip():
            st.error("Informe as observações da entrada.")
            return

        def enviar_entrada_confirmada():
            state, message, response = _enviar_formulario_entrada(
                token,
                products,
                fornecedores,
                product_id=product["id"],
                supplier_id=supplier["id"],
                quantity=quantity,
                unit_purchase_cost=unit_purchase_cost,
                entry_date=entry_date,
                invoice_number=invoice_number,
                notes=notes,
                inbound_freight=freight,
                other_acquisition_costs=other_costs,
            )
            if state == "success":
                st.session_state.pop("historico_movimentacoes_resultado", None)
                st.session_state.pop("saldo_estoque_resultado", None)
                st.session_state["entrada_estoque_success"] = {
                    "owner_identity": owner_identity,
                    "response": response,
                }
                st.session_state["entrada_estoque_toast_pending"] = True
                st.session_state["entrada_estoque_reset_form"] = True
            elif state in {"validation", "error"}:
                st.session_state["entrada_estoque_feedback"] = (
                    "error",
                    message,
                )
            elif state == "inconclusive":
                st.session_state["entrada_estoque_feedback"] = (
                    "warning",
                    message,
                )

        show_confirmation_dialog(
            "Confirmar entrada de estoque",
            {
                "Produto": product["name"],
                "Fornecedor": supplier["name"],
                "Quantidade": quantity,
                "Custo unitário": f"R$ {unit_purchase_cost:,.2f}",
                "Frete": "Não informado" if freight is None else f"R$ {freight:,.2f}",
                "Outros custos": (
                    "Não informado"
                    if other_costs is None
                    else f"R$ {other_costs:,.2f}"
                ),
                "Nota fiscal": invoice_number.strip(),
            },
            enviar_entrada_confirmada,
            key="entrada_estoque_confirmation",
        )
    else:
        last_success = st.session_state.get("entrada_estoque_success")
        response = (
            last_success.get("response")
            if isinstance(last_success, dict)
            and last_success.get("owner_identity") == owner_identity
            else None
        )
        if isinstance(response, dict):
            st.success("Entrada registrada com confirmação do serviço.")
            metrics = st.columns(2)
            metrics[0].metric("Estoque atualizado", response["stock_quantity"])
            metrics[1].metric("Custo médio", f"{response['average_cost']:.2f}")


def _render_diagnostico_leitura_xano():
    with st.expander("Diagnóstico de leitura do Xano"):
        st.caption(
            "Executa somente GET /category e GET /product usando sua sessão atual. "
            "Nenhum registro ou dado de autenticação será exibido."
        )
        token = st.session_state.get("auth_token")
        if st.button(
            "Consultar categorias e produtos",
            disabled=not token,
            key="diagnostico_leitura_xano",
        ):
            resultados = {}
            with data_skeleton("rows", 3), st.spinner("Consultando o Xano..."):
                try:
                    categorias = listar_categorias_ativas(token=token)
                    resultados["categorias"] = ("ok", len(categorias))
                except ValueError as error:
                    if str(error) == "Nenhuma categoria ativa disponível para seleção.":
                        resultados["categorias"] = ("empty", 0)
                    else:
                        resultados["categorias"] = (
                            "error",
                            _mensagem_erro_xano(error, "GET", "/category"),
                        )
                except Exception as error:
                    resultados["categorias"] = (
                        "error",
                        _mensagem_erro_xano(error, "GET", "/category"),
                    )

                etapa = "GET /product"
                try:
                    produtos = listar_produtos(
                        token=token,
                        name="codbar-diagnostic-probe",
                    )
                    quantidade = _contar_registros_produtos(produtos)
                    resultados["produtos"] = (
                        ("ok", quantidade)
                        if quantidade is not None
                        else ("unrecognized", None)
                    )
                except Exception as error:
                    resultados["produtos"] = (
                        "error",
                        _mensagem_erro_xano(error, "GET", "/product"),
                    )

            for label, key in (
                ("Categorias ativas", "categorias"),
                ("Produtos", "produtos"),
            ):
                status, count = resultados[key]
                if status == "empty":
                    st.info(f"{label}: consulta concluída; nenhum registro retornado.")
                elif status == "ok" and count is not None:
                    st.success(
                        f"{label}: consulta concluída; {count} registro(s) retornado(s)."
                    )
                elif status == "unrecognized":
                    st.warning(
                        f"{label}: resposta recebida, mas o formato não foi "
                        "reconhecido; não foi possível confirmar a consulta."
                    )
                else:
                    st.error(f"{label}: {count}")


def render_page_header(
    title,
    subtitle,
    primary_label=None,
    secondary_label=None,
    *,
    primary_action=None,
    secondary_action=None,
    show_actions=False,
):
    with st.container(key="erp-page-header"):
        st.markdown(
            "<div class='erp-breadcrumb'>CodBar / Gestão</div>",
            unsafe_allow_html=True,
        )
        st.markdown(f"<h1>{title}</h1>", unsafe_allow_html=True)
        st.markdown(
            f"<div class='erp-page-subtitle'>{subtitle}</div>",
            unsafe_allow_html=True,
        )
        actions = [
            (primary_label, primary_action, "primary"),
            (secondary_label, secondary_action, "secondary"),
        ]
        available_actions = [
            item for item in actions if item[0] and callable(item[1])
        ]
        if show_actions and available_actions:
            action_columns = st.columns(len(available_actions))
            for column, (label, callback, kind) in zip(
                action_columns,
                available_actions,
            ):
                with column:
                    st.button(
                        label,
                        key=f"header_action_{title}_{label}",
                        type=kind,
                        on_click=callback,
                        use_container_width=True,
                    )


def _carregar_categorias_produto(token):
    if not token:
        return [], "Sua sessão expirou. Entre novamente para carregar categorias."

    try:
        return listar_categorias_ativas(token=token), None
    except requests.HTTPError:
        return [], "Não foi possível carregar as categorias (erro do serviço)."
    except requests.RequestException:
        return [], "Não foi possível carregar as categorias. Verifique a conexão."
    except (RuntimeError, ValueError):
        return [], "Não foi possível carregar categorias ativas."


def _enviar_formulario_produto(
    token,
    categorias,
    *,
    nome,
    categoria_id,
    estoque_minimo,
    preco_venda,
    sku="",
):
    nome = str(nome or "").strip()
    if not nome:
        return "validation", "Informe o nome do produto."

    ids_categorias_ativas = {
        categoria.get("id")
        for categoria in categorias
        if isinstance(categoria, dict)
    }
    if categoria_id not in ids_categorias_ativas:
        return "validation", "Selecione uma categoria ativa válida."

    if isinstance(estoque_minimo, bool) or not isinstance(estoque_minimo, int):
        return "validation", "O estoque mínimo deve ser um número inteiro."
    if estoque_minimo < 0:
        return "validation", "O estoque mínimo não pode ser negativo."

    if (
        isinstance(preco_venda, bool)
        or not isinstance(preco_venda, (int, float))
        or not math.isfinite(preco_venda)
    ):
        return "validation", "Informe um preço de venda válido."
    if preco_venda < 0:
        return "validation", "O preço de venda não pode ser negativo."

    if not token:
        return "error", "Sua sessão expirou. Entre novamente para cadastrar."

    try:
        criar_produto(
            token=token,
            name=nome,
            category_id=categoria_id,
            min_stock=estoque_minimo,
            sale_price=preco_venda,
            sku=str(sku or ""),
        )
    except RespostaCriacaoInconclusivaError as error:
        message = _mensagem_erro_xano(error, "POST", "/product")
        logger.warning("%s", message)
        return (
            "inconclusive",
            message
            + " · O cadastro não foi confirmado. Verifique o produto antes de tentar novamente para evitar duplicidade.",
        )
    except requests.HTTPError as error:
        message = _mensagem_erro_xano(error, "POST", "/product")
        logger.warning("%s", message)
        return "error", message
    except requests.RequestException as error:
        message = _mensagem_erro_xano(error, "POST", "/product")
        logger.warning("%s", message)
        return "error", message
    except ValueError as erro:
        return "validation", str(erro)
    except RuntimeError as error:
        message = _mensagem_erro_xano(error, "POST", "/product")
        logger.warning("%s", message)
        return "error", message

    return "success", "Produto cadastrado com confirmação do serviço."


def _preparar_estado_formulario_produto():
    if not st.session_state.pop("_reset_formulario_produto", False):
        return

    chaves_formulario = (
        "produto_nome",
        "produto_sku",
        "produto_categoria",
        "produto_estoque_minimo",
        "produto_preco_venda",
    )
    for chave in chaves_formulario:
        st.session_state.pop(chave, None)


_ANALYTICS_SCOPE_KEY = "_analytics_auth_scope"
_DASHBOARD_STOCK_KEY = "_dashboard_stock_result"
_DASHBOARD_SALES_KEY = "_dashboard_sales_result"
_DASHBOARD_METRICS_KEY = "_dashboard_metrics_result"
_REPORT_RESULT_KEY = "_reports_result"


def _preparar_escopo_analytics(token):
    scope = hashlib.sha256(token.encode("utf-8")).hexdigest()
    if st.session_state.get(_ANALYTICS_SCOPE_KEY) != scope:
        for key in (
            _DASHBOARD_STOCK_KEY,
            _DASHBOARD_SALES_KEY,
            _DASHBOARD_METRICS_KEY,
            _REPORT_RESULT_KEY,
        ):
            st.session_state.pop(key, None)
        st.session_state[_ANALYTICS_SCOPE_KEY] = scope


def _limite_data_xano(value, *, end=False):
    if not isinstance(value, date):
        raise ValueError("O período deve conter datas válidas.")
    time = "23:59:59" if end else "00:00:00"
    return f"{value.isoformat()}T{time}Z"


def _decimal_financeiro(value, field):
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as error:
        raise ValueError(f"O campo financeiro {field} é inválido.") from error
    if not amount.is_finite():
        raise ValueError(f"O campo financeiro {field} é inválido.")
    return amount


def _agregar_financas_vendas(sales):
    totals = {
        "gross_amount": Decimal("0"),
        "net_revenue": Decimal("0"),
        "total_cmv": Decimal("0"),
        "total_costs": Decimal("0"),
        "result": Decimal("0"),
    }
    for sale in sales:
        for field in totals:
            totals[field] += sale[field]

    totals = {
        field: value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        for field, value in totals.items()
    }
    totals["gross_profit"] = (
        totals["net_revenue"] - totals["total_cmv"]
    ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    totals["margin_percent"] = (
        None
        if totals["net_revenue"] == 0
        else (
            totals["result"]
            / totals["net_revenue"]
            * Decimal("100")
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    )
    return totals


def _validar_pagina_vendas_analytics(page):
    required_fields = {
        "itemsReceived",
        "curPage",
        "itemsTotal",
        "pageTotal",
        "items",
    }
    if not isinstance(page, dict) or not required_fields.issubset(page):
        raise ValueError("GET /sale retornou uma página incompleta.")
    for field in ("itemsReceived", "curPage", "itemsTotal", "pageTotal"):
        value = page[field]
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError("GET /sale retornou paginação inválida.")
    if not isinstance(page["items"], list) or any(
        not isinstance(item, dict) for item in page["items"]
    ):
        raise ValueError("GET /sale retornou uma lista de itens inválida.")
    return page


def _vendas_com_detalhes_financeiros(
    token,
    sales_channel,
    start_date,
    end_date,
):
    if not isinstance(token, str) or not token.strip():
        return {
            "state": "error",
            "sales": [],
            "summary": None,
            "message": "Sua sessão expirou. Entre novamente para consultar vendas.",
        }
    if not isinstance(sales_channel, str) or not sales_channel.strip():
        return {
            "state": "validation",
            "sales": [],
            "summary": None,
            "message": (
                "Informe o canal de venda: GET /sale exige sales_channel "
                "e não há um filtro global de canais confirmado."
            ),
        }

    channel = sales_channel.strip()
    if any(
        value is not None and not isinstance(value, date)
        for value in (start_date, end_date)
    ):
        return {
            "state": "validation",
            "sales": [],
            "summary": None,
            "message": "O período deve conter datas válidas.",
        }
    if (
        start_date is not None
        and end_date is not None
        and end_date < start_date
    ):
        return {
            "state": "validation",
            "sales": [],
            "summary": None,
            "message": "A data final deve ser igual ou posterior à inicial.",
        }

    start_filter = (
        _limite_data_xano(start_date)
        if start_date is not None
        else None
    )
    end_filter = (
        _limite_data_xano(end_date, end=True)
        if end_date is not None
        else None
    )
    try:
        page_size = 100
        first_page = listar_vendas(
            token,
            sales_channel=channel,
            status="registrada",
            start_date=start_filter,
            end_date=end_filter,
            page=1,
            per_page=page_size,
        )
        first_page = _validar_pagina_vendas_analytics(first_page)
        page_total = first_page["pageTotal"]
        items_total = first_page["itemsTotal"]
        if first_page["curPage"] != 1:
            raise ValueError("GET /sale não retornou a primeira página solicitada.")
        if first_page["itemsReceived"] != len(first_page["items"]):
            raise ValueError("GET /sale retornou uma contagem de itens inconsistente.")

        listed_sales = list(first_page["items"])
        for page_number in range(2, page_total + 1):
            page = listar_vendas(
                token,
                sales_channel=channel,
                status="registrada",
                start_date=start_filter,
                end_date=end_filter,
                page=page_number,
                per_page=page_size,
            )
            page = _validar_pagina_vendas_analytics(page)
            if (
                page["curPage"] != page_number
                or page["pageTotal"] != page_total
                or page["itemsTotal"] != items_total
                or page["itemsReceived"] != len(page["items"])
            ):
                raise ValueError(
                    "A paginação de GET /sale mudou ou retornou dados incompletos."
                )
            listed_sales.extend(page["items"])

        if len(listed_sales) != items_total:
            raise ValueError(
                "GET /sale não retornou todos os registros informados na paginação."
            )

        sale_ids = []
        seen_ids = set()
        for listed_sale in listed_sales:
            if not isinstance(listed_sale, dict):
                raise ValueError("GET /sale contém um registro inválido.")
            sale_id = listed_sale.get("id")
            if isinstance(sale_id, str) and sale_id.strip().isdigit():
                sale_id = int(sale_id.strip())
            if isinstance(sale_id, bool) or not isinstance(sale_id, int) or sale_id < 1:
                raise ValueError("GET /sale contém um identificador inválido.")
            if sale_id in seen_ids:
                raise ValueError("GET /sale retornou vendas duplicadas entre páginas.")
            seen_ids.add(sale_id)
            sale_ids.append((sale_id, listed_sale))

            listed_channel = listed_sale.get("sales_channel")
            if listed_channel is not None and listed_channel != channel:
                raise ValueError("GET /sale retornou uma venda de outro canal.")
            listed_status = listed_sale.get("status")
            if listed_status is not None and listed_status != "registrada":
                raise ValueError("GET /sale retornou uma venda não registrada.")

        sales = []
        for sale_id, listed_sale in sale_ids:
            detail = consultar_venda(token, sale_id)
            sale = detail["sale"]
            sale_channel = sale.get("sales_channel")
            if sale_channel is not None and sale_channel != channel:
                raise ValueError("O detalhe retornado pertence a outro canal.")
            sale_status = sale.get("status")
            if sale_status is not None and sale_status != "registrada":
                raise ValueError("O detalhe retornado não é de uma venda registrada.")

            raw_date = sale.get("sale_date", listed_sale.get("sale_date"))
            sale_date = None
            if raw_date not in (None, ""):
                try:
                    sale_date = sale_date_from_unix_milliseconds(
                        sale_date_to_unix_milliseconds(raw_date)
                    ).date().isoformat()
                except (TypeError, ValueError, OverflowError):
                    sale_date = None

            summary = detail["financial_summary"]
            sales.append(
                {
                    "id": sale_id,
                    "sale_date": sale_date,
                    "sales_channel": channel,
                    "order_number": sale.get(
                        "order_number",
                        listed_sale.get("order_number"),
                    ),
                    "gross_amount": _decimal_financeiro(
                        summary["gross_amount"],
                        "gross_amount",
                    ),
                    "net_revenue": _decimal_financeiro(
                        summary["net_revenue"],
                        "net_revenue",
                    ),
                    "total_cmv": _decimal_financeiro(
                        summary["total_cmv"],
                        "total_cmv",
                    ),
                    "total_costs": _decimal_financeiro(
                        summary["total_costs"],
                        "total_costs",
                    ),
                    "result": _decimal_financeiro(
                        summary["result"],
                        "result",
                    ),
                    "profit_margin_percent": _decimal_financeiro(
                        summary["profit_margin_percent"],
                        "profit_margin_percent",
                    ),
                }
            )

        return {
            "state": "success",
            "sales": sales,
            "summary": _agregar_financas_vendas(sales),
            "has_complete_dates": bool(sales)
            and all(sale["sale_date"] is not None for sale in sales),
            "message": None,
        }
    except requests.HTTPError as error:
        status_code = getattr(
            getattr(error, "response", None),
            "status_code",
            None,
        )
        if status_code == 401:
            message = "A sessão foi recusada pelo Xano. Entre novamente."
        elif status_code == 403:
            message = "O Xano negou a permissão para consultar essas vendas."
        else:
            message = (
                "Falha ao consultar vendas no Xano. "
                + _mensagem_erro_xano(
                    error,
                    "GET",
                    "/sale",
                    sensitive_values=(token,),
                )
            )
        return {"state": "error", "sales": [], "summary": None, "message": message}
    except requests.RequestException as error:
        return {
            "state": "error",
            "sales": [],
            "summary": None,
            "message": (
                "Falha de comunicação ao consultar vendas no Xano. "
                + _mensagem_erro_xano(
                    error,
                    "GET",
                    "/sale",
                    sensitive_values=(token,),
                )
            ),
        }
    except (InvalidOperation, RuntimeError, ValueError) as error:
        return {
            "state": "error",
            "sales": [],
            "summary": None,
            "message": (
                "A consulta financeira não foi calculada porque o Xano "
                "retornou dados inválidos ou incompletos. "
                + _mensagem_erro_xano(
                    error,
                    "GET",
                    "/sale",
                    sensitive_values=(token,),
                )
            ),
        }


def _formatar_moeda_analytics(value):
    return (
        "Indisponível"
        if value is None
        else _formatar_valor_monetario_br(value)
    )


def _indicadores_estoque_analytics(products):
    totals = _calcular_indicadores_estoque(products)
    quantity_missing = totals["produtos_quantidade_incompleta"] > 0
    classification_missing = (
        totals["produtos_classificacao_indeterminada"] > 0
    )
    return {
        **totals,
        "produtos_com_estoque": (
            None
            if quantity_missing
            else sum(
                product["stock_quantity"] > 0
                for product in products
            )
        ),
        "produtos_baixos_exato": (
            None if classification_missing else totals["produtos_baixos"]
        ),
        "produtos_sem_estoque_exato": (
            None if quantity_missing else totals["produtos_sem_estoque"]
        ),
    }


def _tabela_produtos_analytics(products):
    rows = [
        {
            "Produto": product["produto"],
            "SKU": product["sku"] or "-",
            "Quantidade atual": _formatar_valor_estoque(
                product["stock_quantity"],
                product["stock_quantity_status"],
            ),
            "Estoque mínimo": _formatar_valor_estoque(
                product["min_stock"],
                product["min_stock_status"],
            ),
            "Custo médio": _formatar_valor_estoque(
                product["average_cost"],
                product["average_cost_status"],
            ),
            "Valor estimado": _formatar_valor_estoque(
                product["valor_estimado"],
                product["valor_estimado_status"],
            ),
            "Situação": product["situacao"],
        }
        for product in products
    ]
    return pd.DataFrame(
        rows,
        columns=[
            "Produto",
            "SKU",
            "Quantidade atual",
            "Estoque mínimo",
            "Custo médio",
            "Valor estimado",
            "Situação",
        ],
    )


def _render_resumo_estoque_analytics(products, *, dashboard=False):
    metrics_data = _indicadores_estoque_analytics(products)
    if not products:
        st.info("O Xano não retornou produtos ativos para o saldo atual.")

    metrics = st.columns(3)
    metrics[0].metric("Produtos ativos", metrics_data["total_produtos"])
    metrics[1].metric(
        "Produtos com estoque",
        (
            "Indisponível"
            if metrics_data["produtos_com_estoque"] is None
            else metrics_data["produtos_com_estoque"]
        ),
    )
    metrics[2].metric(
        "Estoque baixo",
        (
            "Indisponível"
            if metrics_data["produtos_baixos_exato"] is None
            else metrics_data["produtos_baixos_exato"]
        ),
    )

    metrics = st.columns(3)
    metrics[0].metric(
        "Unidades em estoque",
        (
            "Indisponível"
            if metrics_data["total_unidades"] is None
            else f"{metrics_data['total_unidades']:g}"
        ),
    )
    metrics[1].metric(
        "Sem estoque",
        (
            "Indisponível"
            if metrics_data["produtos_sem_estoque_exato"] is None
            else metrics_data["produtos_sem_estoque_exato"]
        ),
    )
    metrics[2].metric(
        "Valor estimado",
        _formatar_moeda_analytics(metrics_data["valor_estoque"]),
    )

    incomplete_messages = []
    if metrics_data["produtos_quantidade_incompleta"]:
        incomplete_messages.append(
            f"quantidade indisponível ou inválida para "
            f"{metrics_data['produtos_quantidade_incompleta']} produto(s)"
        )
    if metrics_data["produtos_valor_incompleto"]:
        incomplete_messages.append(
            f"valor calculável indisponível para "
            f"{metrics_data['produtos_valor_incompleto']} produto(s)"
        )
    if metrics_data["produtos_classificacao_indeterminada"]:
        incomplete_messages.append(
            f"classificação indeterminada para "
            f"{metrics_data['produtos_classificacao_indeterminada']} "
            "produto(s)"
        )
    if incomplete_messages:
        st.warning("Dados incompletos: " + "; ".join(incomplete_messages) + ".")

    table = _tabela_produtos_analytics(products)
    if products:
        render_dataframe(table, width="stretch", hide_index=True)

        known_quantities = [
            product
            for product in products
            if product["stock_quantity_status"] == "valid"
        ]
        if known_quantities:
            quantity_chart = pd.DataFrame(
                {
                    "Quantidade": [
                        product["stock_quantity"]
                        for product in known_quantities
                    ]
                },
                index=[product["produto"] for product in known_quantities],
            )
            st.bar_chart(
                quantity_chart,
                height=260,
                color="#E5B72F",
            )
        else:
            st.info(
                "Gráfico de quantidades indisponível: nenhum valor de estoque "
                "válido foi retornado."
            )

        situation_counts = pd.Series(
            [product["situacao"] for product in products],
            name="Produtos",
        ).value_counts()
        situation_data = situation_counts.rename_axis("Situação").reset_index()
        situation_chart = (
            alt.Chart(situation_data)
            .mark_bar(cornerRadiusEnd=4)
            .encode(
                x=alt.X("Produtos:Q", title=None),
                y=alt.Y(
                    "Situação:N",
                    title=None,
                    sort=[
                        "Sem estoque",
                        "Estoque baixo",
                        "Normal",
                        "Indeterminado",
                    ],
                ),
                color=alt.Color(
                    "Situação:N",
                    scale=alt.Scale(
                        domain=[
                            "Sem estoque",
                            "Estoque baixo",
                            "Normal",
                            "Indeterminado",
                        ],
                        range=[
                            "#B42318",
                            "#E5B72F",
                            "#25764D",
                            "#8A8A83",
                        ],
                    ),
                    legend=None,
                ),
                tooltip=[
                    alt.Tooltip("Situação:N", title="Situação"),
                    alt.Tooltip("Produtos:Q", title="Produtos"),
                ],
            )
            .properties(height=220, title="Produtos por situação")
            .configure_view(stroke=None)
            .configure_axis(
                labelColor="#4F4F49",
                titleColor="#4F4F49",
                gridColor="#E5E5DF",
            )
            .configure_title(color="#242424", fontSize=14, anchor="start")
        )
        st.altair_chart(situation_chart, use_container_width=True)

        if dashboard:
            alerts = [
                product
                for product in products
                if product["situacao"] in {"Estoque baixo", "Indeterminado"}
            ]
            st.subheader("Atenção ao estoque")
            if alerts:
                render_dataframe(
                    _tabela_produtos_analytics(alerts),
                    width="stretch",
                    hide_index=True,
                )
            else:
                st.info("Nenhum produto abaixo do mínimo foi retornado.")

    return table, metrics_data


def _render_indicadores_financeiros(summary, sale_count):
    metrics = (
        ("Vendas registradas", sale_count),
        ("Receita líquida", _formatar_moeda_analytics(summary["net_revenue"])),
        ("CMV", _formatar_moeda_analytics(summary["total_cmv"])),
        ("Lucro bruto", _formatar_moeda_analytics(summary["gross_profit"])),
        ("Custos adicionais", _formatar_moeda_analytics(summary["total_costs"])),
        ("Resultado após custos", _formatar_moeda_analytics(summary["result"])),
        (
            "Margem do resultado",
            (
                "Indisponível"
                if summary["margin_percent"] is None
                else f"{summary['margin_percent']:.2f}%"
            ),
        ),
    )
    for start in range(0, len(metrics), 4):
        columns = st.columns(min(4, len(metrics) - start))
        for column, (label, value) in zip(columns, metrics[start : start + 4]):
            column.metric(label, value)


def _render_grafico_financeiro_vendas(sales, *, report_type=None):
    if not sales:
        st.info("Não há vendas registradas no período e canal selecionados.")
        return
    if not all(sale["sale_date"] is not None for sale in sales):
        st.info(
            "A evolução por período está indisponível: nem todas as vendas "
            "retornaram sale_date em formato reconhecido."
        )
        return

    chart_columns = {
        "Vendas": ["Receita líquida"],
        "CMV": ["CMV"],
        "Lucro": ["Resultado"],
    }
    selected_columns = chart_columns.get(
        report_type,
        ["Receita líquida", "CMV", "Resultado"],
    )
    fields = {
        "Receita líquida": "net_revenue",
        "CMV": "total_cmv",
        "Resultado": "result",
    }
    rows = []
    for sale in sales:
        row = {"Data": sale["sale_date"]}
        for label in selected_columns:
            try:
                numeric_value = float(sale[fields[label]])
            except (OverflowError, TypeError, ValueError):
                numeric_value = math.inf
            if not math.isfinite(numeric_value):
                st.info(
                    "O gráfico está indisponível porque um valor financeiro "
                    "não pode ser representado com segurança."
                )
                return
            row[label] = numeric_value
        rows.append(row)

    daily = (
        pd.DataFrame(rows)
        .groupby("Data", as_index=True)[selected_columns]
        .sum()
        .sort_index()
    )
    colors = [
        {
            "Receita líquida": "#E5B72F",
            "CMV": "#475569",
            "Resultado": "#25764D",
        }[column]
        for column in selected_columns
    ]
    st.line_chart(daily, height=260, color=colors)


def _tabela_vendas_financeiras(sales, report_type):
    rows = []
    for sale in sales:
        base = {"Venda": sale["id"], "Data": sale["sale_date"] or "Indisponível"}
        if report_type == "Vendas":
            base.update(
                {
                    "Canal": sale["sales_channel"],
                    "Pedido": sale["order_number"] or "Indisponível",
                    "Receita bruta": sale["gross_amount"],
                    "Receita líquida": sale["net_revenue"],
                }
            )
        elif report_type == "CMV":
            base["CMV"] = sale["total_cmv"]
        else:
            base.update(
                {
                    "Receita líquida": sale["net_revenue"],
                    "CMV": sale["total_cmv"],
                    "Custos adicionais": sale["total_costs"],
                    "Resultado": sale["result"],
                    "Margem (%)": sale["profit_margin_percent"],
                }
            )
        rows.append(base)
    return pd.DataFrame(rows)


def render_vision_geral():
    render_page_header(
        "Visão geral",
        "Indicadores operacionais e financeiros consultados no Xano.",
        show_actions=False,
    )
    token = st.session_state.get("auth_token")
    if not isinstance(token, str) or not token.strip():
        st.warning("Sua sessão expirou. Entre novamente para consultar os indicadores.")
        return
    _preparar_escopo_analytics(token)

    today = date.today()
    with st.form("dashboard_filters"):
        columns = st.columns(4)
        with columns[0]:
            start_date = st.date_input(
                "Período inicial das vendas",
                value=today.replace(day=1),
                key="dashboard_start_date",
            )
        with columns[1]:
            end_date = st.date_input(
                "Período final das vendas",
                value=today,
                key="dashboard_end_date",
            )
        with columns[2]:
            sales_channel = st.text_input(
                "Canal de venda",
                key="dashboard_sales_channel",
                help="Obrigatório para GET /sale; informe o canal usado nos registros.",
            )
        with columns[3]:
            sales_status = st.text_input(
                "Status (opcional)",
                key="dashboard_sales_status",
            )
        refresh = st.form_submit_button(
            "Atualizar indicadores",
            key="dashboard_refresh",
        )

    filters = (sales_channel.strip(), sales_status.strip(), start_date, end_date)
    if refresh:
        with data_skeleton("cards", 4), st.spinner(
            "Consultando saldo atual no Xano..."
        ):
            stock_state, products, stock_error = _consultar_saldo_estoque(token)
        st.session_state[_DASHBOARD_STOCK_KEY] = {
            "state": stock_state,
            "products": products,
            "error": stock_error,
        }
        with data_skeleton("table"), st.spinner(
            "Consultando vendas registradas e seus detalhes..."
        ):
            sales_result = _vendas_com_detalhes_financeiros(
                token,
                sales_channel,
                start_date,
                end_date,
            )
        st.session_state[_DASHBOARD_SALES_KEY] = {
            "filters": filters,
            "result": sales_result,
        }
        with data_skeleton("cards", 4), st.spinner(
            "Consultando métricas agregadas do Xano..."
        ):
            try:
                metrics = consultar_metricas_vendas(
                    token=token,
                    sales_channel=sales_channel,
                    status=sales_status,
                    start_date=start_date.isoformat(),
                    end_date=end_date.isoformat(),
                )
                metrics_result = {
                    "state": "success",
                    "metrics": metrics,
                }
            except requests.HTTPError as error:
                metrics_result = {
                    "state": "error",
                    "message": _mensagem_erro_xano(
                        error,
                        "GET",
                        "/sale/metrics",
                        sensitive_values=(token,),
                    ),
                }
            except requests.RequestException:
                metrics_result = {
                    "state": "error",
                    "message": "Falha de comunicação ao consultar GET /sale/metrics.",
                }
            except (ValueError, RuntimeError) as error:
                metrics_result = {
                    "state": "error",
                    "message": str(error),
                }
        st.session_state[_DASHBOARD_METRICS_KEY] = {
            "filters": filters,
            "result": metrics_result,
        }
    elif _DASHBOARD_STOCK_KEY not in st.session_state:
        with data_skeleton("cards", 4), st.spinner(
            "Consultando saldo atual no Xano..."
        ):
            stock_state, products, stock_error = _consultar_saldo_estoque(token)
        st.session_state[_DASHBOARD_STOCK_KEY] = {
            "state": stock_state,
            "products": products,
            "error": stock_error,
        }

    if refresh or _DASHBOARD_METRICS_KEY not in st.session_state:
        if not refresh:
            try:
                metrics = consultar_metricas_vendas(
                    token=token,
                    sales_channel=sales_channel,
                    status=sales_status,
                    start_date=start_date.isoformat(),
                    end_date=end_date.isoformat(),
                )
                metrics_result = {"state": "success", "metrics": metrics}
            except requests.HTTPError as error:
                metrics_result = {
                    "state": "error",
                    "message": _mensagem_erro_xano(
                        error,
                        "GET",
                        "/sale/metrics",
                        sensitive_values=(token,),
                    ),
                }
            except requests.RequestException:
                metrics_result = {
                    "state": "error",
                    "message": "Falha de comunicação ao consultar GET /sale/metrics.",
                }
            except (ValueError, RuntimeError) as error:
                metrics_result = {
                    "state": "error",
                    "message": str(error),
                }
            st.session_state[_DASHBOARD_METRICS_KEY] = {
                "filters": filters,
                "result": metrics_result,
            }

    st.subheader("Estoque atual")
    st.caption(
        "O saldo é a posição atual dos produtos ativos; o período selecionado "
        "aplica-se somente às vendas."
    )
    stock_result = st.session_state[_DASHBOARD_STOCK_KEY]
    if stock_result["state"] == "success":
        _render_resumo_estoque_analytics(
            stock_result["products"],
            dashboard=True,
        )
    else:
        st.error(stock_result["error"])
        st.info("Clique em “Atualizar indicadores” para tentar novamente.")

    st.subheader("Indicadores agregados")
    cached_metrics = st.session_state.get(_DASHBOARD_METRICS_KEY)
    if not cached_metrics or cached_metrics.get("filters") != filters:
        st.info("Aplique os filtros para consultar os indicadores agregados do Xano.")
    else:
        metrics_result = cached_metrics["result"]
        if metrics_result["state"] == "success":
            metrics = metrics_result["metrics"]
            if metrics["sales_count"] == 0:
                st.info("Nenhuma venda encontrada para os filtros selecionados.")
            metricas = (
                ("Quantidade de vendas", str(metrics["sales_count"])),
                ("Itens vendidos", str(metrics["items_count"])),
                ("Faturamento bruto", _formatar_moeda_analytics(metrics["gross_amount"])),
                ("Descontos", _formatar_moeda_analytics(metrics["discount_amount"])),
                ("Receita líquida", _formatar_moeda_analytics(metrics["net_revenue"])),
                ("CMV", _formatar_moeda_analytics(metrics["total_cmv"])),
                ("Custos adicionais", _formatar_moeda_analytics(metrics["total_costs"])),
                ("Resultado", _formatar_moeda_analytics(metrics["result"])),
                (
                    "Margem",
                    "—"
                    if metrics["profit_margin_percent"] is None
                    else f"{metrics['profit_margin_percent']:,.2f}%".replace(".", ","),
                ),
                (
                    "Ticket médio",
                    _formatar_moeda_analytics(metrics["average_ticket"]),
                ),
            )
            for inicio in range(0, len(metricas), 5):
                colunas = st.columns(5)
                for coluna, (rotulo, valor) in zip(
                    colunas,
                    metricas[inicio:inicio + 5],
                ):
                    with coluna:
                        st.metric(rotulo, valor)
        else:
            st.error(metrics_result["message"])
            st.info("Clique em “Atualizar indicadores” para tentar novamente.")

    st.subheader("Desempenho financeiro")
    cached_sales = st.session_state.get(_DASHBOARD_SALES_KEY)
    if not sales_channel.strip():
        st.info(
            "Indicadores financeiros indisponíveis até informar o canal: "
            "GET /sale exige sales_channel."
        )
    elif (
        not cached_sales
        or cached_sales.get("filters") != filters
    ):
        st.info(
            "Aplique os filtros para consultar vendas reais do canal e período selecionados."
        )
    else:
        sales_result = cached_sales["result"]
        if sales_result["state"] == "success":
            _render_indicadores_financeiros(
                sales_result["summary"],
                len(sales_result["sales"]),
            )
            _render_grafico_financeiro_vendas(sales_result["sales"])
        elif sales_result["state"] == "validation":
            st.info(sales_result["message"])
        else:
            st.error(sales_result["message"])
            st.info("Clique em “Atualizar indicadores” para tentar novamente.")


def render_produtos():
    _preparar_estado_formulario_produto()
    mensagem_sucesso = st.session_state.pop(
        "mensagem_sucesso_produtos",
        None,
    )
    feedback_formulario = st.session_state.pop("produto_feedback", None)
    if feedback_formulario:
        nivel, mensagem = feedback_formulario
        if nivel == "inconclusive":
            st.warning(mensagem)
        else:
            st.error(mensagem)
    render_page_header(
        "Produtos",
        "Consulta, cadastro e manutenção do catálogo.",
    )
    token = st.session_state.get("auth_token")
    categorias, erro_categorias = _carregar_categorias_produto(token)
    if erro_categorias:
        st.error(erro_categorias)

    st.markdown(
        "<div class='erp-panel-header'><div class='erp-panel-title'>"
        "Buscar produtos no Xano</div></div>",
        unsafe_allow_html=True,
    )
    with st.form("form_busca_produtos_xano"):
        nome_busca = st.text_input(
            "Nome do produto",
            placeholder="Informe um nome para pesquisar",
            key="busca_produtos_nome",
        )
        opcoes_categoria = ["Todas"] + [
            f"{categoria['name']} (ID {categoria['id']})"
            for categoria in categorias
        ]
        categoria_busca = st.selectbox(
            "Categoria",
            options=opcoes_categoria,
            key="busca_produtos_categoria",
        )
        status_busca = st.text_input(
            "Status",
            placeholder="Valor aceito pelo Xano (opcional)",
            help="Vazio omite o filtro. Informe o status conforme o contrato do Xano.",
            key="busca_produtos_status",
        )
        busca_enviada = st.form_submit_button(
            "Buscar",
            type="primary",
            key="buscar_produtos_submit",
        )

    if busca_enviada:
        categoria_id = None
        if categoria_busca != "Todas":
            categoria_id = categorias[opcoes_categoria.index(categoria_busca) - 1]["id"]
        with data_skeleton("table"):
            estado, produtos_encontrados, erro_busca = (
                _consultar_produtos_por_nome(
                    token,
                    nome_busca,
                    category_id=categoria_id,
                    status=status_busca,
                )
            )
        st.session_state["busca_produtos_resultado"] = {
            "state": estado,
            "name": str(nome_busca or "").strip(),
            "category_id": categoria_id,
            "status": str(status_busca or "").strip(),
            "products": produtos_encontrados,
            "error": erro_busca,
        }

    if st.session_state.pop("recarregar_listagem_produtos", False):
        resultado_anterior = st.session_state.get("busca_produtos_resultado")
        if resultado_anterior:
            with data_skeleton("table"):
                estado, produtos_atualizados, erro_atualizacao = (
                    _consultar_produtos_por_nome(
                        token,
                        resultado_anterior["name"],
                        category_id=resultado_anterior.get("category_id"),
                        status=resultado_anterior.get("status"),
                    )
                )
            st.session_state["busca_produtos_resultado"] = {
                **resultado_anterior,
                "state": estado,
                "products": produtos_atualizados,
                "error": erro_atualizacao,
            }

    resultado_busca = st.session_state.get("busca_produtos_resultado")
    if resultado_busca is None:
        st.info("Informe um nome para pesquisar produtos no Xano.")
    elif resultado_busca["state"] == "empty_query":
        st.info("Informe um nome para pesquisar produtos no Xano.")
    elif resultado_busca["state"] == "error":
        st.error(resultado_busca["error"])
    elif resultado_busca["state"] == "validation":
        st.error(resultado_busca["error"])
    elif not resultado_busca["products"]:
        st.info("Nenhum produto encontrado.")
    else:
        st.caption(
            f"Resultados do Xano para “{resultado_busca['name']}” "
            f"({len(resultado_busca['products'])})."
        )
        render_dataframe(
            _tabela_produtos_para_interface(
                resultado_busca["products"],
                categorias,
            ),
            width="stretch",
            hide_index=True,
        )
        products_with_ids = [
            product
            for product in resultado_busca["products"]
            if isinstance(product.get("id"), int) and not isinstance(product.get("id"), bool)
        ]
        if products_with_ids:
            selected_product = st.selectbox(
                "Produto para consultar ou editar",
                options=products_with_ids,
                format_func=lambda item: (
                    f"{item['name']} (ID {item['id']})"
                ),
                key="produto_selecionado_para_edicao",
            )
            if st.button("Consultar detalhe", key="consultar_detalhe_produto"):
                with data_skeleton("rows", 3):
                    state, record, error = _consultar_produto_por_id(
                        token,
                        selected_product["id"],
                    )
                if state == "success":
                    st.session_state["produto_detalhe_xano"] = record
                    st.session_state.pop("produto_detalhe_erro", None)
                else:
                    st.session_state["produto_detalhe_erro"] = (
                        "A consulta individual não foi confirmada."
                        if state == "inconclusive"
                        else error
                    )

        product_detail = st.session_state.get("produto_detalhe_xano")
        selected_id = (
            selected_product.get("id")
            if products_with_ids
            else None
        )
        if (
            isinstance(product_detail, dict)
            and selected_id is not None
            and product_detail.get("id") != selected_id
        ):
            product_detail = None

        if st.session_state.get("produto_detalhe_erro"):
            st.error(st.session_state.pop("produto_detalhe_erro"))
        if product_detail:
            _render_detalhe_produto(product_detail, categorias)
            status_options = ["ativo", "inativo"]
            current_status = product_detail.get("status")
            status_index = (
                status_options.index(current_status)
                if current_status in status_options
                else 0
            )
            category_options = ["Não alterar"] + [
                f"{item['name']} (ID {item['id']})" for item in categorias
            ]
            with st.form("form_edicao_produto_xano"):
                edit_name = st.text_input(
                    "Nome",
                    value=str(product_detail.get("name", "")),
                    key="editar_produto_nome",
                )
                edit_sku = st.text_input(
                    "SKU",
                    value=str(product_detail.get("sku") or ""),
                    key="editar_produto_sku",
                )
                current_category = product_detail.get("category_id")
                if isinstance(current_category, dict):
                    current_category = current_category.get("id")
                category_index = 0
                for index, category in enumerate(categorias, start=1):
                    if category.get("id") == current_category:
                        category_index = index
                        break
                edit_category = st.selectbox(
                    "Categoria",
                    options=category_options,
                    index=category_index,
                    key="editar_produto_categoria",
                )
                edit_min_stock = st.number_input(
                    "Estoque mínimo",
                    min_value=0,
                    value=max(0, int(product_detail.get("min_stock", 0) or 0)),
                    step=1,
                    key="editar_produto_estoque_minimo",
                )
                edit_sale_price = st.number_input(
                    "Preço de venda",
                    min_value=0.0,
                    value=max(0.0, float(product_detail.get("sale_price", 0) or 0)),
                    step=0.01,
                    key="editar_produto_preco_venda",
                )
                edit_status = st.selectbox(
                    "Status",
                    options=status_options,
                    index=status_index,
                    key="editar_produto_status",
                )
                edit_submitted = st.form_submit_button(
                    "Salvar alterações",
                    key="salvar_edicao_produto",
                )

            if edit_submitted:
                changes = {}
                if edit_name.strip() != str(product_detail.get("name", "")):
                    changes["name"] = edit_name
                if edit_sku.strip() != str(product_detail.get("sku") or ""):
                    changes["sku"] = edit_sku
                if edit_category != "Não alterar":
                    chosen_category = categorias[category_options.index(edit_category) - 1]
                    if chosen_category["id"] != current_category:
                        changes["category_id"] = chosen_category["id"]
                if edit_min_stock != product_detail.get("min_stock"):
                    changes["min_stock"] = edit_min_stock
                if edit_sale_price != product_detail.get("sale_price"):
                    changes["sale_price"] = edit_sale_price
                if edit_status != current_status:
                    changes["status"] = edit_status

                if not changes:
                    st.info("Nenhuma alteração foi informada.")
                elif edit_status == "inativo" and current_status != "inativo":
                    st.error(
                        "Use a ação de inativação com confirmação explícita."
                    )
                else:
                    def salvar_produto_editado():
                        state, record, error = _salvar_edicao_produto(
                            token,
                            product_detail["id"],
                            **changes,
                        )
                        if state == "success":
                            st.session_state["produto_detalhe_xano"] = record
                            st.session_state["mensagem_sucesso_produtos"] = (
                                "Produto atualizado com confirmação do Xano."
                            )
                            st.session_state[
                                "recarregar_listagem_produtos"
                            ] = True
                            st.session_state["produto_toast_pending"] = True
                        else:
                            st.session_state["produto_feedback"] = (
                                state,
                                error,
                            )

                    show_confirmation_dialog(
                        "Confirmar alterações do produto",
                        {
                            "Produto": product_detail.get("name", "Produto"),
                            "Campos alterados": ", ".join(changes),
                        },
                        salvar_produto_editado,
                        key="produto_edit_confirmation",
                    )

            confirm_deactivate = st.checkbox(
                "Confirmo a inativação lógica deste produto",
                key="confirmar_inativacao_produto",
            )
            if st.button(
                "Inativar produto",
                disabled=not confirm_deactivate,
                key="inativar_produto",
            ):
                def inativar_produto_confirmado():
                    state, record, error = _inativar_produto(
                        token,
                        product_detail["id"],
                    )
                    if state == "success":
                        st.session_state["produto_detalhe_xano"] = record
                        st.session_state["mensagem_sucesso_produtos"] = (
                            "Produto inativado com confirmação do Xano."
                        )
                        st.session_state[
                            "recarregar_listagem_produtos"
                        ] = True
                        st.session_state["produto_toast_pending"] = True
                    else:
                        st.session_state["produto_feedback"] = (
                            state,
                            error,
                        )

                show_confirmation_dialog(
                    "Confirmar inativação do produto",
                    {
                        "Produto": product_detail.get("name", "Produto"),
                        "Efeito": "O produto será inativado sem apagar o histórico.",
                    },
                    inativar_produto_confirmado,
                    key="produto_deactivate_confirmation",
                )

    if mensagem_sucesso:
        st.success(mensagem_sucesso)

    st.markdown("<div class='erp-section'></div>", unsafe_allow_html=True)
    st.markdown("<div class='erp-panel-header'><div class='erp-panel-title'>Cadastro de produto</div></div>", unsafe_allow_html=True)

    with st.form("form_cadastro_produto"):
        col1, col2 = st.columns(2)
        with col1:
            nome = st.text_input("Nome do produto", key="produto_nome")
            sku = st.text_input(
                "SKU (opcional)",
                key="produto_sku",
                help="Se informado, o Xano verifica se o SKU já está em uso.",
            )
            categoria = st.selectbox(
                "Categoria",
                options=categorias,
                format_func=lambda item: f"{item['name']} (ID {item['id']})",
                index=None,
                placeholder="Selecione uma categoria ativa",
                disabled=not categorias,
                key="produto_categoria",
            )
        with col2:
            estoque_minimo = st.number_input(
                "Estoque mínimo",
                min_value=0,
                value=5,
                key="produto_estoque_minimo",
            )
            preco_venda = st.number_input(
                "Preço de venda",
                min_value=0.0,
                value=249.0,
                step=1.0,
                key="produto_preco_venda",
            )
        submitted = st.form_submit_button(
            "Salvar produto",
            type="primary",
            width="stretch",
            disabled=not token or not categorias,
            key="salvar_produto_submit",
        )

    if submitted:
        st.session_state.pop("produto_success_message", None)
        categoria_id = categoria.get("id") if categoria else None

        def enviar_produto_confirmado():
            estado, mensagem = _enviar_formulario_produto(
                token,
                categorias,
                nome=nome,
                categoria_id=categoria_id,
                estoque_minimo=estoque_minimo,
                preco_venda=preco_venda,
                sku=sku,
            )
            if estado == "success":
                st.session_state["produto_success_message"] = mensagem
                st.session_state["_reset_formulario_produto"] = True
                st.session_state["busca_produtos_resultado"] = None
                st.session_state["produto_toast_pending"] = True
            else:
                st.session_state["produto_feedback"] = (estado, mensagem)

        show_confirmation_dialog(
            "Confirmar cadastro do produto",
            {
                "Produto": nome.strip() or "Não informado",
                "Categoria": categoria.get("name") if categoria else "Não selecionada",
                "SKU": sku.strip() or "Não informado",
                "Estoque mínimo": estoque_minimo,
                "Preço de venda": f"R$ {preco_venda:,.2f}",
            },
            enviar_produto_confirmado,
            key="produto_create_confirmation",
        )
    elif st.session_state.get("produto_success_message"):
        st.success(st.session_state["produto_success_message"])
    if st.session_state.pop("produto_toast_pending", False):
        show_toast("Produto cadastrado com confirmação do Xano.")


def render_estoque():
    render_page_header(
        "Estoque",
        "Saldo, movimentações e controle de disponibilidade.",
        show_actions=False,
    )
    _render_formulario_entrada_estoque()

    with st.container(key="consulta_saldo_estoque_panel"):
        st.subheader("Consulta de saldo")
        token = st.session_state.get("auth_token")
        if st.button(
            "Consultar saldo",
            type="secondary",
            key="consulta_saldo_estoque",
            disabled=not token,
        ):
            with data_skeleton("cards", 4):
                estado, products, error = _consultar_saldo_estoque(token)
            st.session_state["saldo_estoque_resultado"] = {
                "state": estado,
                "products": products,
                "error": error,
            }
            st.session_state["saldo_estoque_produtos_gerais"] = products

        result = st.session_state.get("saldo_estoque_resultado")
        if result is None:
            st.caption("A consulta de saldo será executada usando os produtos ativos do Xano.")
            return

        if result["state"] == "error":
            st.error(result["error"])
            return

        products = result["products"] or []
        if not products:
            st.info("Nenhum produto ativo foi retornado pelo Xano para o saldo atual.")
            return

        base_products = st.session_state.get("saldo_estoque_produtos_gerais") or products
        metrics_data = _calcular_indicadores_estoque(base_products)

        dataframe = pd.DataFrame(
            [
                {
                    "Produto": item["produto"],
                    "SKU": item["sku"] or "-",
                    "Quantidade atual": _formatar_valor_estoque(
                        item["stock_quantity"],
                        item["stock_quantity_status"],
                    ),
                    "Estoque mínimo": _formatar_valor_estoque(
                        item["min_stock"],
                        item["min_stock_status"],
                    ),
                    "Custo médio": _formatar_valor_estoque(
                        item["average_cost"],
                        item["average_cost_status"],
                    ),
                    "Valor estimado": _formatar_valor_estoque(
                        item["valor_estimado"],
                        item["valor_estimado_status"],
                    ),
                    "Situação": item["situacao"],
                }
                for item in products
            ]
        )

        metrics = st.columns(5)
        metrics[0].metric("Total de produtos", metrics_data["total_produtos"])
        total_unidades = metrics_data["total_unidades"]
        metrics[1].metric(
            "Total de unidades",
            (
                "Indisponível"
                if total_unidades is None
                else f"{total_unidades:g}"
            ),
        )
        metrics[2].metric("Estoque baixo", metrics_data["produtos_baixos"])
        metrics[3].metric("Sem estoque", metrics_data["produtos_sem_estoque"])
        valor_estoque = metrics_data["valor_estoque"]
        metrics[4].metric(
            "Valor estimado",
            (
                "Indisponível"
                if valor_estoque is None
                else f"R$ {valor_estoque:,.2f}"
            ),
        )

        incomplete_messages = []
        if metrics_data["produtos_quantidade_incompleta"]:
            incomplete_messages.append(
                f"quantidade indisponível ou inválida para "
                f"{metrics_data['produtos_quantidade_incompleta']} produto(s)"
            )
        if metrics_data["produtos_valor_incompleto"]:
            incomplete_messages.append(
                f"valor calculável indisponível para "
                f"{metrics_data['produtos_valor_incompleto']} produto(s)"
            )
        if metrics_data["produtos_classificacao_indeterminada"]:
            incomplete_messages.append(
                f"classificação indeterminada para "
                f"{metrics_data['produtos_classificacao_indeterminada']} "
                "produto(s)"
            )
        if incomplete_messages:
            st.warning("Dados incompletos: " + "; ".join(incomplete_messages) + ".")

    chart_data = pd.DataFrame(
        {
            "Produto": [
                item["produto"]
                for item in products
                if item["stock_quantity_status"] == "valid"
            ],
            "Quantidade": [
                item["stock_quantity"]
                for item in products
                if item["stock_quantity_status"] == "valid"
            ],
        }
    )
    chart_situacao = pd.DataFrame(
        {
            "Situação": [
                "Sem estoque",
                "Estoque baixo",
                "Normal",
                "Indeterminado",
            ],
            "Quantidade": [
                sum(1 for item in products if item["situacao"] == "Sem estoque"),
                sum(1 for item in products if item["situacao"] == "Estoque baixo"),
                sum(1 for item in products if item["situacao"] == "Normal"),
                sum(1 for item in products if item["situacao"] == "Indeterminado"),
            ],
        }
    )
    chart_valor = pd.DataFrame(
        {
            "Produto": [
                item["produto"]
                for item in products
                if item["valor_estimado_status"] == "valid"
            ],
            "Valor estimado": [
                item["valor_estimado"]
                for item in products
                if item["valor_estimado_status"] == "valid"
            ],
        }
    )

    def _render_chart_horizontal(df, category_col, value_col, title, color):
        chart = alt.Chart(df).mark_bar(color=color, cornerRadiusEnd=4)
        if category_col == "Situação":
            chart = alt.Chart(df).mark_bar(cornerRadiusEnd=4).encode(
                color=alt.Color(
                    "Situação:N",
                    scale=alt.Scale(
                        domain=[
                            "Sem estoque",
                            "Estoque baixo",
                            "Normal",
                            "Indeterminado",
                        ],
                        range=[
                            "#B42318",
                            "#E5B72F",
                            "#25764D",
                            "#8A8A83",
                        ],
                    ),
                    legend=None,
                )
            )
        chart = (
            chart.encode(
                x=alt.X(f"{value_col}:Q", title=None),
                y=alt.Y(
                    f"{category_col}:N",
                    title=None,
                    sort="-x",
                    axis=alt.Axis(labelLimit=180, labelOverlap=False),
                ),
                tooltip=[
                    alt.Tooltip(f"{category_col}:N", title=title),
                    alt.Tooltip(f"{value_col}:Q", title="Valor", format=",.2f"),
                ],
            )
            .properties(height=max(220, len(df) * 28), title=title)
            .configure_view(stroke=None)
            .configure_axis(
                labelColor="#4F4F49",
                titleColor="#4F4F49",
                gridColor="#E5E5DF",
            )
            .configure_title(color="#242424", fontSize=14, anchor="start")
        )
        st.altair_chart(chart, use_container_width=True)

    left, middle, right = st.columns(3)
    with left:
        st.subheader("Quantidade por produto")
        quantity_missing = metrics_data["produtos_quantidade_incompleta"]
        if quantity_missing:
            st.caption(
                f"{quantity_missing} produto(s) sem quantidade conhecida "
                "foram omitidos do gráfico."
            )
        if chart_data.empty:
            st.info("Não há quantidades conhecidas para gerar este gráfico.")
        else:
            _render_chart_horizontal(
                chart_data,
                "Produto",
                "Quantidade",
                "Quantidade por produto",
                "#E5B72F",
            )
    with middle:
        st.subheader("Distribuição por situação")
        _render_chart_horizontal(
            chart_situacao,
            "Situação",
            "Quantidade",
            "Distribuição por situação",
            "#25764D",
        )
    with right:
        st.subheader("Valor estimado por produto")
        value_missing = metrics_data["produtos_valor_incompleto"]
        if value_missing:
            st.caption(
                f"{value_missing} produto(s) sem valor calculável "
                "foram omitidos do gráfico."
            )
        if chart_valor.empty:
            st.info("Não há valores conhecidos para gerar este gráfico.")
        else:
            _render_chart_horizontal(
                chart_valor,
                "Produto",
                "Valor estimado",
                "Valor estimado por produto",
                "#B88E11",
            )

    st.subheader("Tabela de saldo")
    render_dataframe(dataframe, width="stretch", hide_index=True)

    st.subheader("Histórico e indicadores")
    _render_historico_movimentacoes()

    st.subheader("Movimentação manual")
    st.info(
        "Registro manual de movimentações não está integrado a um endpoint "
        "confirmado. Use a entrada de estoque integrada quando aplicável."
    )


def _normalizar_id_venda_interface(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value > 0:
        return value
    if isinstance(value, str) and value.strip().isdigit():
        normalized = int(value.strip())
        return normalized if normalized > 0 else None
    return None


def _validar_detalhe_venda_interface(response, expected_id):
    if not isinstance(response, dict):
        return False
    sale = response.get("sale")
    if not isinstance(sale, dict):
        return False
    if _normalizar_id_venda_interface(sale.get("id")) != expected_id:
        return False
    if any(
        not isinstance(response.get(field), list)
        or any(not isinstance(item, dict) for item in response[field])
        for field in ("items", "costs")
    ):
        return False
    return isinstance(response.get("financial_summary"), dict)


def _valor_produto_venda_interface(item):
    name = item.get("product_name")
    if not name and isinstance(item.get("product"), dict):
        name = item["product"].get("name")
    if isinstance(name, str) and name.strip():
        return name.strip()
    product_id = item.get("product_id")
    if isinstance(product_id, (int, str)) and not isinstance(product_id, bool):
        return f"Produto {_texto_interface(product_id)}"
    return "Não informado"


def _rotulo_tipo_custo_venda(value):
    labels = {
        "embalagem": "Embalagem",
        "comissao_marketplace": "Comissão do marketplace",
        "impostos": "Impostos",
        "frete_saida": "Frete de saída",
        "outros": "Outros",
    }
    return labels.get(str(value or "").strip().lower(), "Não informado")


def _formatar_percentual_br(value):
    if value is None or value == "" or isinstance(value, bool):
        return "Não informado"
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return "Não informado"
    if not amount.is_finite():
        return "Não informado"
    return f"{format(amount, '.2f').replace('.', ',')}%"


def _render_conteudo_detalhe_venda(response):
    sale = response["sale"]
    st.markdown("#### Dados da venda")
    sale_date = sale.get("sale_date")
    if sale_date not in (None, ""):
        try:
            sale_date = format_sale_date(sale_date)
        except (TypeError, ValueError, OverflowError):
            sale_date = "Data inválida"
    sale_columns = st.columns(4)
    for column, (label, value) in zip(
        sale_columns,
        (
            ("Pedido", _texto_interface(sale.get("order_number"))),
            ("Canal de venda", _texto_interface(sale.get("sales_channel"))),
            ("Data da venda", sale_date or "Não informada"),
        ),
    ):
        with column:
            st.metric(label, value)
    with sale_columns[3]:
        st.markdown("**Situação**")
        _render_status_badge(sale.get("status"))

    st.markdown("#### Itens")
    if response["items"]:
        item_rows = [
            {
                "Produto": _valor_produto_venda_interface(item),
                "Quantidade": _formatar_quantidade_br(item.get("quantity")),
                "Preço unitário": _formatar_valor_monetario_br(
                    item.get("unit_sale_price")
                ),
                "Custo histórico unitário": _formatar_valor_monetario_br(
                    item.get("historical_unit_cost")
                ),
            }
            for item in response["items"]
        ]
        render_dataframe(
            pd.DataFrame(
                item_rows,
                columns=[
                    "Produto",
                    "Quantidade",
                    "Preço unitário",
                    "Custo histórico unitário",
                ],
            ),
            width="stretch",
            hide_index=True,
        )
    else:
        st.info("A resposta não contém itens para esta venda.")

    st.markdown("#### Custos")
    if response["costs"]:
        cost_rows = [
            {
                "Tipo de custo": _rotulo_tipo_custo_venda(
                    cost.get("cost_type")
                ),
                "Descrição": (
                    cost.get("description").strip()
                    if isinstance(cost.get("description"), str)
                    and cost.get("description").strip()
                    else "Não informada"
                ),
                "Valor": _formatar_valor_monetario_br(cost.get("amount")),
            }
            for cost in response["costs"]
        ]
        render_dataframe(
            pd.DataFrame(
                cost_rows,
                columns=["Tipo de custo", "Descrição", "Valor"],
            ),
            width="stretch",
            hide_index=True,
        )
    else:
        st.info("A resposta não contém custos adicionais para esta venda.")

    st.markdown("#### Resumo financeiro retornado pelo Xano")
    summary = response["financial_summary"]
    summary_fields = (
        ("gross_amount", "Receita bruta", _formatar_valor_monetario_br),
        ("discount_amount", "Descontos", _formatar_valor_monetario_br),
        ("net_revenue", "Receita líquida", _formatar_valor_monetario_br),
        ("total_cmv", "CMV", _formatar_valor_monetario_br),
        ("total_costs", "Custos adicionais", _formatar_valor_monetario_br),
        ("result", "Resultado", _formatar_valor_monetario_br),
        ("profit_margin_percent", "Margem de lucro", _formatar_percentual_br),
    )
    displayed_summary = [
        (label, formatter(summary[field]))
        for field, label, formatter in summary_fields
        if field in summary
    ]
    if displayed_summary:
        columns = st.columns(4)
        for index, (label, value) in enumerate(displayed_summary):
            with columns[index % len(columns)]:
                st.metric(label, value)
    else:
        st.info("O resumo financeiro não contém campos disponíveis.")


def _novo_registro_venda_formulario():
    next_item_id = int(st.session_state.get("vendas_create_next_item_id", 1))
    st.session_state["vendas_create_items"] = [{"id": next_item_id}]
    st.session_state["vendas_create_next_item_id"] = next_item_id + 1
    st.session_state["vendas_create_costs"] = []


def _adicionar_item_venda_formulario():
    next_item_id = int(st.session_state["vendas_create_next_item_id"])
    st.session_state["vendas_create_items"].append({"id": next_item_id})
    st.session_state["vendas_create_next_item_id"] = next_item_id + 1


def _remover_item_venda_formulario(item_id):
    st.session_state["vendas_create_items"] = [
        item
        for item in st.session_state["vendas_create_items"]
        if item["id"] != item_id
    ]
    for suffix in (
        "product_search",
        "products",
        "product_id",
        "quantity",
        "unit_sale_price",
        "discount_amount",
    ):
        st.session_state.pop(
            f"vendas_create_item_{item_id}_{suffix}",
            None,
        )


def _adicionar_custo_venda_formulario():
    next_cost_id = int(st.session_state["vendas_create_next_cost_id"])
    st.session_state["vendas_create_costs"].append({"id": next_cost_id})
    st.session_state["vendas_create_next_cost_id"] = next_cost_id + 1


def _remover_custo_venda_formulario(cost_id):
    st.session_state["vendas_create_costs"] = [
        cost
        for cost in st.session_state["vendas_create_costs"]
        if cost["id"] != cost_id
    ]
    for suffix in ("cost_type", "description", "amount"):
        st.session_state.pop(
            f"vendas_create_cost_{cost_id}_{suffix}",
            None,
        )


def _buscar_produtos_para_item_venda(token, item_id):
    query = st.session_state.get(
        f"vendas_create_item_{item_id}_product_search",
        "",
    )
    state, products, error = _consultar_produtos_por_nome(token, query)
    valid_products = []
    if state == "success":
        for product in products:
            product_id = _normalizar_id_venda_interface(product.get("id"))
            name = product.get("name")
            if product_id is not None and isinstance(name, str) and name.strip():
                valid_products.append({**product, "id": product_id})

    products_key = f"vendas_create_item_{item_id}_products"
    selected_key = f"vendas_create_item_{item_id}_product_id"
    st.session_state[products_key] = valid_products
    if st.session_state.get(selected_key) not in {
        product["id"] for product in valid_products
    }:
        st.session_state.pop(selected_key, None)
    st.session_state[f"vendas_create_item_{item_id}_search_state"] = state
    st.session_state[f"vendas_create_item_{item_id}_search_error"] = error


def _parsear_decimal_nao_negativo(value, field_name):
    texto = str(value or "").strip()
    if not texto:
        raise ValueError(f"{field_name} é obrigatório.")
    try:
        numero = float(texto)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{field_name} deve ser um número válido.") from error
    if not math.isfinite(numero) or numero < 0:
        raise ValueError(
            f"{field_name} deve ser um número finito maior ou igual a zero."
        )
    return numero


def _construir_payload_venda_interface():
    sales_channel = st.session_state.get("vendas_create_sales_channel", "")
    if not isinstance(sales_channel, str) or not sales_channel.strip():
        raise ValueError("Informe o canal de venda.")

    payload = {
        "sales_channel": sales_channel.strip(),
        "items": [],
        "costs": [],
    }
    for field in ("order_number", "notes"):
        value = st.session_state.get(f"vendas_create_{field}", "")
        if isinstance(value, str) and value.strip():
            payload[field] = value.strip()

    sale_date = st.session_state.get("vendas_create_sale_date", "")
    if isinstance(sale_date, str) and sale_date.strip():
        payload["sale_date"] = sale_date_to_unix_milliseconds(
            sale_date,
            "Data da venda",
        )

    for item in st.session_state.get("vendas_create_items", []):
        item_id = item["id"]
        prefix = f"vendas_create_item_{item_id}_"
        product_id = _normalizar_id_venda_interface(
            st.session_state.get(f"{prefix}product_id")
        )
        if product_id is None:
            raise ValueError(
                f"Selecione um produto válido no item {item_id}."
            )

        quantity_text = str(
            st.session_state.get(f"{prefix}quantity", "")
        ).strip()
        if not quantity_text.isdigit() or int(quantity_text) < 1:
            raise ValueError(
                f"A quantidade do item {item_id} deve ser um inteiro maior ou igual a 1."
            )

        quantity = int(quantity_text)
        unit_sale_price = _parsear_decimal_nao_negativo(
            st.session_state.get(f"{prefix}unit_sale_price", ""),
            f"Preço unitário do item {item_id}",
        )
        sale_item = {
            "product_id": product_id,
            "quantity": quantity,
            "unit_sale_price": unit_sale_price,
        }
        discount_text = st.session_state.get(
            f"{prefix}discount_amount",
            "",
        )
        if isinstance(discount_text, str) and discount_text.strip():
            discount_amount = _parsear_decimal_nao_negativo(
                discount_text,
                f"Desconto do item {item_id}",
            )
            if discount_amount > unit_sale_price * quantity:
                raise ValueError(
                    f"O desconto do item {item_id} não pode superar o valor bruto."
                )
            sale_item["discount_amount"] = discount_amount
        payload["items"].append(sale_item)

    if not payload["items"]:
        raise ValueError("Adicione pelo menos um item à venda.")

    costs = []
    permitted_cost_types = {
        "embalagem",
        "comissao_marketplace",
        "impostos",
        "frete_saida",
        "outros",
    }
    for cost in st.session_state.get("vendas_create_costs", []):
        cost_id = cost["id"]
        prefix = f"vendas_create_cost_{cost_id}_"
        cost_type = st.session_state.get(f"{prefix}cost_type")
        if cost_type not in permitted_cost_types:
            raise ValueError(f"Selecione um tipo válido para o custo {cost_id}.")
        cost_payload = {
            "cost_type": cost_type,
            "amount": _parsear_decimal_nao_negativo(
                st.session_state.get(f"{prefix}amount", ""),
                f"Valor do custo {cost_id}",
            ),
        }
        description = st.session_state.get(f"{prefix}description", "")
        if isinstance(description, str) and description.strip():
            cost_payload["description"] = description.strip()
        costs.append(cost_payload)
    payload["costs"] = costs

    return payload


def _validar_resposta_criacao_venda_interface(response, payload=None):
    if not isinstance(response, dict):
        return False
    sale = response.get("sale")
    if (
        not isinstance(sale, dict)
        or _normalizar_id_venda_interface(sale.get("id")) is None
    ):
        return False
    if isinstance(payload, dict) and any(
        sale.get(field) != payload.get(field)
        for field in ("sales_channel", "order_number")
    ):
        return False
    for field in ("items", "costs"):
        if not isinstance(response.get(field), list) or any(
            not isinstance(item, dict) for item in response[field]
        ):
            return False
    summary = response.get("financial_summary")
    required_summary_fields = {
        "gross_amount",
        "discount_amount",
        "net_revenue",
        "total_cmv",
        "total_costs",
        "result",
        "profit_margin_percent",
    }
    if (
        not isinstance(summary, dict)
        or not required_summary_fields.issubset(summary)
    ):
        return False
    return all(
        not isinstance(summary[field], bool)
        and isinstance(summary[field], (int, float))
        and (
            not isinstance(summary[field], float)
            or math.isfinite(summary[field])
        )
        for field in required_summary_fields
    )


def _fingerprint_payload_venda_interface(payload):
    fingerprint_payload = {
        key: value
        for key, value in payload.items()
        if key != "idempotency_key"
    }
    serialized = json.dumps(
        fingerprint_payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _obter_chave_idempotencia_venda(
    fingerprint,
    *,
    state=None,
    fingerprint_key="vendas_create_payload_fingerprint",
    idempotency_key="vendas_create_idempotency_key",
):
    state = st.session_state if state is None else state
    existing_key = state.get(idempotency_key)
    if state.get(fingerprint_key) == fingerprint:
        try:
            parsed_key = UUID(existing_key)
        except (AttributeError, TypeError, ValueError):
            parsed_key = None
        if parsed_key is not None and parsed_key.version == 4:
            return str(parsed_key)

    key = str(uuid4())
    state[fingerprint_key] = fingerprint
    state[idempotency_key] = key
    state.pop("vendas_create_idempotency_blocked_fingerprint", None)
    state.pop("vendas_create_idempotency_error_code", None)
    return key


def _codigo_erro_idempotencia_venda(error):
    response = getattr(error, "response", None)
    if getattr(response, "status_code", None) != 400:
        return None
    try:
        payload = response.json()
    except (ValueError, requests.RequestException):
        return None
    if not isinstance(payload, dict):
        return None
    message = payload.get("message")
    if not isinstance(message, str):
        return None
    codes = (
        "IDEMPOTENCY_LOCKED",
        "IDEMPOTENCY_CONCURRENT_REQUEST",
        "IDEMPOTENCY_LOCK_FAILED",
        "IDEMPOTENCY_PAYLOAD_MISMATCH",
    )
    for code in codes:
        if re.search(rf"(?<![A-Z0-9_]){code}(?![A-Z0-9_])", message):
            return code
    return None


VENDAS_EXCEL_SESSION_KEY = "vendas_excel_import_state"


def _consultar_produto_importacao(token, product_id):
    try:
        product = consultar_produto(token, product_id)
    except requests.HTTPError as error:
        raise ProductLookupError(
            _mensagem_erro_xano(
                error,
                "GET",
                f"/product/{product_id}",
                sensitive_values=(token,),
            )
        ) from error
    except requests.RequestException as error:
        raise ProductLookupError(
            _mensagem_erro_xano(
                error,
                "GET",
                f"/product/{product_id}",
                sensitive_values=(token,),
            )
        ) from error
    except (RuntimeError, ValueError) as error:
        raise ProductLookupError(
            _mensagem_erro_xano(
                error,
                "GET",
                f"/product/{product_id}",
                sensitive_values=(token,),
            )
        ) from error
    return product


def _localizar_venda_importacao(token, sales_channel, order_number):
    page = 1
    visited_pages = set()
    start_date = _limite_data_xano(date(1970, 1, 1))
    end_date = _limite_data_xano(date.today(), end=True)
    while True:
        response = listar_vendas(
            token,
            sales_channel=sales_channel,
            order_number=order_number,
            start_date=start_date,
            end_date=end_date,
            page=page,
            per_page=100,
        )
        if not isinstance(response, dict) or not isinstance(
            response.get("items"),
            list,
        ):
            raise ValueError("GET /sale não retornou uma lista válida de vendas.")

        for existing in response["items"]:
            if not {"sales_channel", "order_number", "status"}.issubset(existing):
                raise ValueError(
                    "GET /sale não retornou sales_channel, order_number e status "
                    "necessários para validar duplicidade."
                )
            if not all(
                isinstance(existing[field], str)
                for field in ("sales_channel", "order_number", "status")
            ):
                raise ValueError(
                    "GET /sale retornou campos insuficientes para validar duplicidade."
                )
            if (
                existing["sales_channel"] == sales_channel
                and existing["order_number"] == order_number
                and existing["status"].strip().lower() != "cancelada"
            ):
                return existing

        next_page = response.get("nextPage")
        if next_page is None:
            return None
        if (
            isinstance(next_page, bool)
            or not isinstance(next_page, int)
            or next_page <= page
            or next_page in visited_pages
        ):
            raise ValueError("GET /sale retornou paginação inválida.")
        visited_pages.add(page)
        page = next_page


def _adicionar_erro_importacao_venda(
    state,
    entry,
    *,
    field,
    message,
    status="blocked",
):
    sale = entry["sale"]
    issue = {
        "sheet": "Xano",
        "row": None,
        "order_number": sale["order_number"],
        "sales_channel": sale["sales_channel"],
        "field": field,
        "message": message,
    }
    state["errors"].append(issue)
    sale["errors"].append(issue)
    sale["valid"] = False
    entry["status"] = status
    entry["message"] = message


def _preparar_importacao_vendas_excel(token, content, file_hash, filename):
    state = {
        "file_hash": file_hash,
        "filename": filename,
        "sales": [],
        "errors": [],
        "fatal_error": None,
        "summary": {},
    }
    try:
        parsed = parse_sales_workbook(content)
    except ValueError as error:
        state["fatal_error"] = str(error)
        return state

    if not parsed["errors"]:
        resolve_sale_products(
            parsed,
            lambda product_id: _consultar_produto_importacao(token, product_id),
        )
    state["errors"] = parsed["errors"]
    state["summary"] = {
        key: parsed[key]
        for key in ("item_rows", "cost_rows", "total_items", "total_costs")
    }
    for sale in parsed["sales"]:
        if not sale["valid"]:
            entry_status = "invalid"
            entry_message = None
        elif state["errors"]:
            entry_status = "blocked"
            entry_message = (
                "A validação deste pedido foi bloqueada por erro no arquivo."
            )
        else:
            entry_status = "validating"
            entry_message = None
        entry = {
            "sale": sale,
            "payload": build_sale_payload(sale) if sale["valid"] else None,
            "payload_snapshot": None,
            "fingerprint": None,
            "idempotency_key": None,
            "status": entry_status,
            "message": entry_message,
            "response": None,
        }
        state["sales"].append(entry)

    if not state["errors"]:
        for entry in state["sales"]:
            sale = entry["sale"]
            try:
                existing = _localizar_venda_importacao(
                    token,
                    sale["sales_channel"],
                    sale["order_number"],
                )
            except requests.HTTPError as error:
                message = _mensagem_erro_xano(
                    error,
                    "GET",
                    "/sale",
                    sensitive_values=(token,),
                )
                _adicionar_erro_importacao_venda(
                    state,
                    entry,
                    field="deduplicação",
                    message=message,
                )
            except requests.RequestException as error:
                message = _mensagem_erro_xano(
                    error,
                    "GET",
                    "/sale",
                    sensitive_values=(token,),
                )
                _adicionar_erro_importacao_venda(
                    state,
                    entry,
                    field="deduplicação",
                    message=message,
                )
            except (RuntimeError, ValueError) as error:
                message = _mensagem_erro_xano(
                    error,
                    "GET",
                    "/sale",
                    sensitive_values=(token,),
                )
                _adicionar_erro_importacao_venda(
                    state,
                    entry,
                    field="deduplicação",
                    message=message,
                )
            else:
                if existing is not None:
                    _adicionar_erro_importacao_venda(
                        state,
                        entry,
                        field="numero_pedido",
                        message=(
                            "Já existe uma venda não cancelada com este canal "
                            "e número de pedido."
                        ),
                        status="duplicate",
                    )

    for entry in state["sales"]:
        if entry["status"] == "validating":
            if state["errors"]:
                entry["status"] = "blocked"
                entry["message"] = (
                    "A validação deste pedido foi bloqueada por erro no arquivo."
                )
            else:
                entry["status"] = "ready"

    return state


def _mensagem_falha_importacao_venda(error, token):
    idempotency_error = _codigo_erro_idempotencia_venda(error)
    if idempotency_error == "IDEMPOTENCY_PAYLOAD_MISMATCH":
        message = (
            "O Xano associou a chave a outro payload. A reconciliação está "
            "bloqueada para análise administrativa."
        )
    elif idempotency_error == "IDEMPOTENCY_LOCKED":
        message = "O Xano ainda está processando esta operação."
    elif idempotency_error == "IDEMPOTENCY_CONCURRENT_REQUEST":
        message = "O Xano detectou uma solicitação concorrente."
    elif idempotency_error == "IDEMPOTENCY_LOCK_FAILED":
        message = "O Xano não conseguiu obter o bloqueio de idempotência."
    elif getattr(getattr(error, "response", None), "status_code", None) == 401:
        message = "A sessão expirou ou não foi aceita pelo Xano."
    elif getattr(getattr(error, "response", None), "status_code", None) == 403:
        message = "Seu perfil não tem permissão para registrar vendas."
    else:
        message = "O resultado do POST /sale não foi confirmado."

    details = _mensagem_erro_xano(
        error,
        "POST",
        "/sale",
        sensitive_values=(token,),
    )
    if idempotency_error == "IDEMPOTENCY_PAYLOAD_MISMATCH":
        return f"{message} {details} Não reenvie este pedido."
    return (
        f"{message} {details} A operação permanece pendente; reconcilie "
        "somente com a chave e o payload originais."
    )


def _enviar_venda_importacao(token, entry):
    entry["status"] = "in_progress"
    try:
        response = criar_venda(token, deepcopy(entry["payload_snapshot"]))
        if not _validar_resposta_criacao_venda_interface(
            response,
            entry["payload_snapshot"],
        ):
            raise RespostaVendaInconclusivaError(
                "A resposta do Xano não confirmou o registro da venda."
            )
    except requests.HTTPError as error:
        entry["status"] = (
            "inconclusive"
            if _codigo_erro_idempotencia_venda(error)
            == "IDEMPOTENCY_PAYLOAD_MISMATCH"
            else "pending"
        )
        entry["message"] = _mensagem_falha_importacao_venda(error, token)
    except (
        OperacaoVendaInconclusivaError,
        RespostaVendaInconclusivaError,
        requests.RequestException,
        RuntimeError,
        TypeError,
        ValueError,
    ) as error:
        entry["status"] = "pending"
        entry["message"] = _mensagem_falha_importacao_venda(error, token)
    else:
        entry["status"] = "confirmed"
        entry["response"] = response
        entry["message"] = None


def _executar_lote_vendas_excel(token, state):
    if not token:
        raise ValueError("Entre novamente para importar vendas.")
    if state.get("fatal_error") or state.get("errors") or any(
        not entry["sale"].get("valid") for entry in state.get("sales", [])
    ):
        raise ValueError(
            "Corrija todos os erros da planilha antes de importar qualquer pedido."
        )
    for entry in state["sales"]:
        if entry["status"] != "ready":
            continue
        payload = deepcopy(entry["payload"])
        fingerprint = _fingerprint_payload_venda_interface(payload)
        idempotency_key = _obter_chave_idempotencia_venda(
            fingerprint,
            state=entry,
            fingerprint_key="fingerprint",
            idempotency_key="idempotency_key",
        )
        payload["idempotency_key"] = idempotency_key
        entry["fingerprint"] = fingerprint
        entry["idempotency_key"] = idempotency_key
        entry["payload_snapshot"] = payload
        _enviar_venda_importacao(token, entry)
        st.session_state[VENDAS_EXCEL_SESSION_KEY] = state


def _reconciliar_venda_excel(token, state, entry):
    snapshot = entry.get("payload_snapshot")
    if not isinstance(snapshot, dict) or not isinstance(
        snapshot.get("idempotency_key"),
        str,
    ):
        entry["status"] = "blocked"
        entry["message"] = (
            "A operação pendente não contém a chave e o payload originais; "
            "não é seguro reenviá-la."
        )
        return
    if (
        snapshot["idempotency_key"] != entry.get("idempotency_key")
        or _fingerprint_payload_venda_interface(snapshot)
        != entry.get("fingerprint")
    ):
        entry["status"] = "blocked"
        entry["message"] = (
            "A chave ou o payload da operação pendente foi alterado; "
            "a reconciliação foi bloqueada."
        )
        return
    _enviar_venda_importacao(token, entry)
    st.session_state[VENDAS_EXCEL_SESSION_KEY] = state


def _atualizar_listagem_apos_importacao(state, previous_statuses):
    confirmed_entries = [
        entry
        for index, entry in enumerate(state.get("sales", []))
        if entry.get("status") == "confirmed"
        and previous_statuses[index] != "confirmed"
    ]
    if not confirmed_entries:
        return False

    current_channel = st.session_state.get("vendas_list_filter_channel")
    if not isinstance(current_channel, str) or not current_channel.strip():
        st.session_state["vendas_list_filter_channel"] = confirmed_entries[0][
            "sale"
        ]["sales_channel"]
    st.session_state["vendas_list_page"] = 1
    st.session_state["vendas_list_query_pending"] = True
    return True


def _render_importacao_vendas_excel(token):
    st.subheader("Importação de vendas por Excel")
    if st.session_state.pop("vendas_excel_import_toast_pending", False):
        show_toast("Importação concluída; os resultados foram confirmados pelo Xano.")
    st.caption(
        "Use o modelo com as abas Itens e Custos. id_produto é necessário para "
        "validar o produto; SKU sozinho não pode ser consultado no Xano. A aba "
        "Custos é opcional. Cada grupo canal/pedido gera uma venda; datas sem "
        "fuso são interpretadas como UTC."
    )
    st.download_button(
        "Baixar modelo Excel",
        data=create_sales_template(),
        file_name="modelo_importacao_vendas_codbar.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="vendas_excel_template_download",
    )
    uploaded = st.file_uploader(
        "Selecione uma planilha .xlsx",
        type=["xlsx"],
        key="vendas_excel_file",
    )
    state = st.session_state.get(VENDAS_EXCEL_SESSION_KEY)
    if uploaded is not None:
        if not token:
            st.warning("Entre novamente para validar e importar vendas.")
        else:
            content = uploaded.getvalue()
            file_hash = hashlib.sha256(content).hexdigest()
            pending_statuses = {"pending", "in_progress", "inconclusive"}
            has_pending = isinstance(state, dict) and any(
                entry.get("status") in pending_statuses
                for entry in state.get("sales", [])
            )
            if (
                isinstance(state, dict)
                and state.get("file_hash") != file_hash
                and has_pending
            ):
                st.warning(
                    "Há pedidos pendentes ou bloqueados neste lote. Reconcilie "
                    "usando a chave original ou resolva a pendência antes de "
                    "selecionar outro arquivo."
                )
            elif not isinstance(state, dict) or state.get("file_hash") != file_hash:
                state = _preparar_importacao_vendas_excel(
                    token,
                    content,
                    file_hash,
                    uploaded.name,
                )
                st.session_state[VENDAS_EXCEL_SESSION_KEY] = state

    if not isinstance(state, dict):
        st.info("Selecione uma planilha .xlsx para iniciar.")
        return

    for entry in state.get("sales", []):
        if entry.get("status") == "in_progress":
            entry["status"] = "pending"

    if state.get("fatal_error"):
        st.error(state["fatal_error"])
        return

    summary = state.get("summary", {})
    cost_rows = summary.get("cost_rows", 0)
    total_costs = summary.get("total_costs", 0)
    cost_rows_label = (
        "linha preenchida"
        if cost_rows == 1
        else "linhas preenchidas"
    )
    costs_label = "custo associado" if total_costs == 1 else "custos associados"
    st.write(
        f"Arquivo: **{state.get('filename', 'planilha')}** — "
        f"{len(state.get('sales', []))} pedidos, "
        f"{summary.get('total_items', 0)} itens e "
        f"{cost_rows} {cost_rows_label} na aba Custos, "
        f"{total_costs} {costs_label}."
    )
    if not state.get("sales") and not state.get("errors"):
        st.info("A planilha não contém pedidos. Preencha a aba Itens para iniciar.")
    if state.get("errors"):
        has_xano_query_error = any(
            issue.get("sheet") == "Xano"
            and issue.get("field") == "deduplicação"
            for issue in state["errors"]
        )
        if has_xano_query_error:
            st.error(
                "Não foi possível concluir a consulta de duplicidade no Xano. "
                "Nenhuma venda deste arquivo será enviada até que a consulta "
                "seja concluída."
            )
        else:
            st.error(
                "A validação encontrou problemas. Nenhuma venda deste arquivo "
                "será enviada enquanto houver erros."
            )
        error_rows = [
            {
                "Aba": issue.get("sheet"),
                "Linha": issue.get("row"),
                "Pedido": issue.get("order_number"),
                "Canal": issue.get("sales_channel"),
                "Campo": issue.get("field"),
                "Erro": issue.get("message"),
            }
            for issue in state["errors"]
        ]
        render_dataframe(
            pd.DataFrame(error_rows),
            width="stretch",
            hide_index=True,
        )

    for index, entry in enumerate(state.get("sales", []), start=1):
        sale = entry["sale"]
        label = (
            f"Pedido {sale['order_number']} · {sale['sales_channel']} "
            f"· {entry['status']}"
        )
        with st.expander(
            label,
            expanded=entry["status"] in {"pending", "blocked", "inconclusive"},
        ):
            item_rows = [
                {
                    "Produto": item.get("product_name") or item.get("sku"),
                    "ID": item.get("product_id"),
                    "Quantidade": item.get("quantity"),
                    "Preço unitário": item.get("unit_sale_price"),
                    "Desconto": item.get("discount_amount", 0),
                }
                for item in sale.get("items", [])
            ]
            if item_rows:
                render_dataframe(
                    pd.DataFrame(item_rows),
                    width="stretch",
                    hide_index=True,
                )
            st.write(
                f"Bruto: {sale.get('gross_amount', 0):.2f} · "
                f"Descontos: {sale.get('discount_amount', 0):.2f} · "
                f"Custos adicionais: {sale.get('additional_costs', 0):.2f}"
            )
            if entry.get("message"):
                st.warning(entry["message"])
            if entry["status"] == "confirmed":
                response = entry.get("response", {})
                sale_response = response.get("sale", {})
                st.success(
                    "Venda confirmada pelo Xano"
                    + (
                        f" (ID {sale_response['id']})."
                        if isinstance(sale_response, dict)
                        and sale_response.get("id") is not None
                        else "."
                    )
                )
                render_dataframe(
                    pd.DataFrame([response["financial_summary"]]),
                    width="stretch",
                    hide_index=True,
                )
            elif entry["status"] == "pending" and token:
                if st.button(
                    "Reconciliar com a chave original",
                    key=f"vendas_excel_reconcile_{state['file_hash'][:12]}_{index}",
                ):
                    def reconciliar_venda_confirmada():
                        previous_statuses = [
                            item["status"] for item in state.get("sales", [])
                        ]
                        _reconciliar_venda_excel(token, state, entry)
                        _atualizar_listagem_apos_importacao(
                            state,
                            previous_statuses,
                        )

                    show_confirmation_dialog(
                        "Confirmar reconciliação do pedido",
                        {
                            "Pedido": sale.get("order_number", "Não informado"),
                            "Canal": sale.get("sales_channel", "Não informado"),
                            "Ação": (
                                "Será usada exclusivamente a chave e o payload "
                                "originais desta operação."
                            ),
                        },
                        reconciliar_venda_confirmada,
                        key=f"vendas_excel_reconcile_confirmation_{index}",
                    )

    ready_entries = [
        entry for entry in state.get("sales", []) if entry["status"] == "ready"
    ]
    can_import = (
        bool(token)
        and bool(ready_entries)
        and not state.get("errors")
        and all(entry["sale"].get("valid") for entry in state.get("sales", []))
    )
    if st.button(
        f"Importar {len(ready_entries)} pedido(s) validado(s)",
        type="primary",
        disabled=not can_import,
        key="vendas_excel_import_submit",
    ):
        def importar_vendas_confirmadas():
            previous_statuses = [
                entry["status"] for entry in state.get("sales", [])
            ]
            _executar_lote_vendas_excel(token, state)
            if _atualizar_listagem_apos_importacao(
                state,
                previous_statuses,
            ):
                if all(
                    entry.get("status") == "confirmed"
                    for entry in ready_entries
                ):
                    st.session_state["vendas_excel_import_toast_pending"] = True

        show_confirmation_dialog(
            "Confirmar importação de vendas",
            {
                "Arquivo": state.get("filename", "Planilha"),
                "Pedidos validados": len(ready_entries),
                "Itens": summary.get("total_items", 0),
                "Ação": (
                    "Cada pedido será enviado uma única vez nesta execução. "
                    "Operações com resultado inconclusivo permanecerão "
                    "pendentes para reconciliação."
                ),
            },
            importar_vendas_confirmadas,
            key="vendas_excel_import_confirmation",
        )


def _limpar_estado_formulario_venda():
    for key in list(st.session_state):
        if key.startswith("vendas_create_"):
            st.session_state.pop(key, None)
    st.session_state["vendas_create_items"] = [{"id": 1}]
    st.session_state["vendas_create_next_item_id"] = 2
    st.session_state["vendas_create_costs"] = []
    st.session_state["vendas_create_next_cost_id"] = 1
    st.session_state["vendas_create_operation_status"] = "completed"


def _render_formulario_venda(token, *, page_key, pending_key, clear_detail):
    reset_key = "vendas_create_reset_pending"
    if st.session_state.pop(reset_key, False):
        _limpar_estado_formulario_venda()

    st.session_state.setdefault("vendas_create_items", [{"id": 1}])
    st.session_state.setdefault("vendas_create_next_item_id", 2)
    st.session_state.setdefault("vendas_create_costs", [])
    st.session_state.setdefault("vendas_create_next_cost_id", 1)

    st.markdown(
        "<div class='erp-panel-header'><div class='erp-panel-title'>"
        "Registrar venda</div></div>",
        unsafe_allow_html=True,
    )
    operation_status_key = "vendas_create_operation_status"
    operation_status = st.session_state.setdefault(
        operation_status_key,
        "new",
    )
    if (
        operation_status == "new"
        and st.session_state.get("vendas_create_inconclusive")
    ):
        operation_status = "inconclusive"
        st.session_state[operation_status_key] = operation_status
    status_labels = {
        "new": "Estado da operação: nova",
        "in_progress": "Estado da operação: em andamento",
        "inconclusive": "Estado da operação: inconclusiva",
        "completed": "Estado da operação: concluída",
    }
    st.caption(status_labels.get(operation_status, status_labels["new"]))
    if not token:
        st.warning(
            "Sua sessão expirou. Entre novamente para registrar uma venda."
        )

    st.markdown("#### A. Informações da venda")
    st.text_input(
        "Canal de venda",
        key="vendas_create_sales_channel",
        placeholder="Informe o canal",
    )
    general_columns = st.columns(2)
    with general_columns[0]:
        st.text_input(
            "Número do pedido (opcional)",
            key="vendas_create_order_number",
        )
    with general_columns[1]:
        st.text_input(
            "Data da venda (opcional)",
            key="vendas_create_sale_date",
            placeholder="2026-11-22 ou 2026-11-22T13:45:00-03:00",
            help=(
                "Informe uma data ISO 8601; datas sem fuso são interpretadas "
                "como UTC e convertidas para timestamp Unix em milissegundos. "
                "Se vazio, o campo opcional será omitido."
            ),
        )
    st.text_area(
        "Observações (opcional)",
        key="vendas_create_notes",
    )

    st.markdown("#### B. Produtos da venda")
    for item in st.session_state["vendas_create_items"]:
        item_id = item["id"]
        prefix = f"vendas_create_item_{item_id}_"
        st.markdown(f"**Item {item_id}**")
        search_columns = st.columns([3, 1])
        with search_columns[0]:
            st.text_input(
                f"Pesquisar produto do item {item_id}",
                key=f"{prefix}product_search",
                placeholder="Digite parte do nome cadastrado",
            )
        with search_columns[1]:
            st.button(
                "Buscar produto",
                key=f"{prefix}search_submit",
                disabled=not token,
                on_click=_buscar_produtos_para_item_venda,
                args=(token, item_id),
            )

        products = st.session_state.get(f"{prefix}products", [])
        product_by_id = {product["id"]: product for product in products}
        product_ids = list(product_by_id)
        if not product_ids:
            product_ids = [None]

        def format_product(product_id):
            product = product_by_id.get(product_id)
            if product is None:
                return "Busque e selecione um produto cadastrado"
            sku = product.get("sku")
            suffix = f" · SKU {sku}" if isinstance(sku, str) and sku else ""
            return f"{product['name']}{suffix} (ID {product_id})"

        selected_product_id = st.selectbox(
            f"Produto cadastrado do item {item_id}",
            options=product_ids,
            format_func=format_product,
            key=f"{prefix}product_id",
            disabled=not bool(product_by_id),
        )
        if selected_product_id is not None:
            st.caption(
                f"Produto selecionado: {format_product(selected_product_id)}"
            )

        search_state = st.session_state.get(f"{prefix}search_state")
        if search_state == "empty_query":
            st.info("Informe um nome para pesquisar no catálogo do Xano.")
        elif search_state == "success" and not products:
            st.info("Nenhum produto encontrado para essa pesquisa.")
        elif search_state == "error":
            st.error(
                st.session_state.get(
                    f"{prefix}search_error",
                    "Não foi possível consultar os produtos.",
                )
            )

        item_columns = st.columns([1, 1, 1, 0.6])
        with item_columns[0]:
            st.text_input(
                f"Quantidade do item {item_id}",
                key=f"{prefix}quantity",
                placeholder="Inteiro maior ou igual a 1",
            )
        with item_columns[1]:
            st.text_input(
                f"Preço unitário do item {item_id}",
                key=f"{prefix}unit_sale_price",
                placeholder="Obrigatório",
                help="Valor numérico maior ou igual a zero.",
            )
        with item_columns[2]:
            st.text_input(
                f"Desconto do item {item_id} (opcional)",
                key=f"{prefix}discount_amount",
                placeholder="Em branco = padrão do contrato",
            )
        with item_columns[3]:
            st.button(
                "Remover",
                key=f"{prefix}remove",
                on_click=_remover_item_venda_formulario,
                args=(item_id,),
            )

    st.button(
        "Adicionar produto",
        key="vendas_create_add_item",
        on_click=_adicionar_item_venda_formulario,
    )

    st.markdown("#### C. Custos adicionais globais (opcional)")
    for cost in st.session_state["vendas_create_costs"]:
        cost_id = cost["id"]
        prefix = f"vendas_create_cost_{cost_id}_"
        cost_columns = st.columns([1.2, 1.4, 1, 0.6])
        with cost_columns[0]:
            st.selectbox(
                f"Tipo do custo {cost_id}",
                [
                    "embalagem",
                    "comissao_marketplace",
                    "impostos",
                    "frete_saida",
                    "outros",
                ],
                key=f"{prefix}cost_type",
            )
        with cost_columns[1]:
            st.text_input(
                f"Descrição do custo {cost_id} (opcional)",
                key=f"{prefix}description",
            )
        with cost_columns[2]:
            st.text_input(
                f"Valor do custo {cost_id}",
                key=f"{prefix}amount",
                placeholder="Obrigatório",
            )
        with cost_columns[3]:
            st.button(
                "Remover",
                key=f"{prefix}remove",
                on_click=_remover_custo_venda_formulario,
                args=(cost_id,),
            )
    st.button(
        "Adicionar custo",
        key="vendas_create_add_cost",
        on_click=_adicionar_custo_venda_formulario,
    )

    current_payload = None
    current_fingerprint = None
    current_payload_error = None
    try:
        current_payload = _construir_payload_venda_interface()
        current_fingerprint = _fingerprint_payload_venda_interface(
            current_payload
        )
    except (TypeError, ValueError) as error:
        current_payload_error = str(error)

    inconclusive_key = "vendas_create_inconclusive"
    submitting_key = "vendas_create_submitting"
    operation_status = st.session_state.get(operation_status_key, "new")
    pending_operation = operation_status in {"in_progress", "inconclusive"}
    operation_payload = st.session_state.get("vendas_create_operation_payload")
    operation_key = st.session_state.get("vendas_create_idempotency_key")
    operation_fingerprint = st.session_state.get(
        "vendas_create_payload_fingerprint"
    )
    if pending_operation:
        st.warning(
            "Existe uma venda anterior sem confirmação. Nenhuma nova venda "
            "será enviada até reconciliar essa operação usando a chave e o "
            "payload originais."
        )
        if (
            current_fingerprint is not None
            and operation_fingerprint is not None
            and current_fingerprint != operation_fingerprint
        ):
            st.info(
                "O formulário foi alterado, mas essas mudanças não substituirão "
                "a operação pendente nem serão enviadas. A reconciliação usará "
                "o payload original."
            )
        if not isinstance(operation_payload, dict) or not operation_key:
            st.error(
                "Os dados originais da operação pendente não estão disponíveis "
                "para uma reconciliação segura. O cadastro permanece bloqueado; "
                "é necessária uma análise administrativa."
            )

    reconcile_clicked = st.button(
        "Reconciliar operação pendente com a chave original",
        key="vendas_create_reconcile_pending",
        disabled=(
            not token
            or not pending_operation
            or st.session_state.get(submitting_key, False)
            or not isinstance(operation_payload, dict)
            or not operation_key
        ),
    )
    should_rerun = False
    should_send = False
    submit_clicked = st.button(
        "Registrar venda",
        key="vendas_create_submit",
        type="primary",
        disabled=(
            not token
            or pending_operation
            or st.session_state.get(submitting_key, False)
        ),
    )
    confirmed_action = st.session_state.pop(
        "vendas_create_confirmed_action",
        None,
    )
    if confirmed_action == "reconcile":
        reconcile_clicked = True
    elif confirmed_action == "submit":
        submit_clicked = True

    if reconcile_clicked and confirmed_action != "reconcile":
        show_confirmation_dialog(
            "Confirmar reconciliação da venda",
            {
                "Chave original": operation_key or "Indisponível",
                "Pedido": (
                    operation_payload.get("order_number", "Não informado")
                    if isinstance(operation_payload, dict)
                    else "Indisponível"
                ),
                "Ação": (
                    "Será usado o payload original. Não edite nem substitua "
                    "os dados desta operação."
                ),
            },
            lambda: st.session_state.__setitem__(
                "vendas_create_confirmed_action",
                "reconcile",
            ),
            key="vendas_reconcile_confirmation",
        )
        return

    if submit_clicked and confirmed_action != "submit":
        if not isinstance(current_payload, dict) or current_fingerprint is None:
            st.session_state["vendas_create_feedback"] = {
                "level": "error",
                "message": (
                    current_payload_error
                    or "Revise os dados da venda antes de confirmar."
                ),
            }
            submit_clicked = False
        else:
            summary = {
                "Canal": current_payload.get("sales_channel", "Não informado"),
                "Pedido": current_payload.get("order_number") or "Não informado",
                "Itens": len(current_payload.get("items", [])),
                "Custos adicionais": len(current_payload.get("costs", [])),
                "Observação": (
                    "A venda só será enviada após a confirmação. "
                    "O resultado será considerado concluído somente após "
                    "confirmação do Xano."
                ),
            }

            def confirmar_venda():
                st.session_state["vendas_create_confirmation_payload"] = (
                    deepcopy(current_payload)
                )
                st.session_state[
                    "vendas_create_confirmation_fingerprint"
                ] = current_fingerprint
                st.session_state["vendas_create_confirmed_action"] = "submit"

            show_confirmation_dialog(
                "Confirmar registro da venda",
                summary,
                confirmar_venda,
                key="vendas_create_confirmation",
            )
            return

    if reconcile_clicked or submit_clicked:
        if not token:
            st.session_state["vendas_create_feedback"] = {
                "level": "error",
                "message": (
                    "Sua sessão expirou. Entre novamente para registrar a venda."
                ),
            }
        elif st.session_state.get(submitting_key, False):
            st.session_state["vendas_create_feedback"] = {
                "level": "warning",
                "message": "O registro desta venda já está em andamento.",
            }
        elif reconcile_clicked:
            if not isinstance(operation_payload, dict) or not operation_key:
                st.session_state["vendas_create_feedback"] = {
                    "level": "error",
                    "message": (
                        "A operação pendente não contém chave e payload "
                        "originais válidos para reconciliação."
                    ),
                }
            else:
                payload = deepcopy(operation_payload)
                fingerprint = operation_fingerprint
                idempotency_key = operation_key
                payload["idempotency_key"] = idempotency_key
                st.session_state[operation_status_key] = "in_progress"
                st.session_state[inconclusive_key] = False
                st.session_state[submitting_key] = True
                st.session_state["vendas_create_feedback"] = None
                should_send = True
        else:
            confirmation_payload = st.session_state.pop(
                "vendas_create_confirmation_payload",
                None,
            )
            confirmation_fingerprint = st.session_state.pop(
                "vendas_create_confirmation_fingerprint",
                None,
            )
            if (
                isinstance(confirmation_payload, dict)
                and isinstance(confirmation_fingerprint, str)
            ):
                payload = deepcopy(confirmation_payload)
                fingerprint = confirmation_fingerprint
            else:
                try:
                    payload = _construir_payload_venda_interface()
                    fingerprint = _fingerprint_payload_venda_interface(payload)
                except (TypeError, ValueError) as error:
                    st.session_state["vendas_create_feedback"] = {
                        "level": "error",
                        "message": str(error),
                    }
                    payload = None
                    fingerprint = None

            if payload is not None and fingerprint is not None:
                idempotency_key = _obter_chave_idempotencia_venda(
                    fingerprint
                )
                st.session_state["vendas_create_operation_payload"] = (
                    deepcopy(payload)
                )
                st.session_state[operation_status_key] = "in_progress"
                st.session_state[inconclusive_key] = False
                st.session_state["vendas_create_feedback"] = None
                payload["idempotency_key"] = idempotency_key
                st.session_state[submitting_key] = True
                should_send = True

        if reconcile_clicked and (
            isinstance(operation_payload, dict) and operation_key
        ):
            should_send = True
        if should_send:
            confirmed = False
            try:
                response = criar_venda(token, payload)
                if not _validar_resposta_criacao_venda_interface(response):
                    raise RespostaVendaInconclusivaError(
                        "A resposta do Xano não confirmou todos os dados "
                        "do registro da venda."
                    )
            except OperacaoVendaInconclusivaError as error:
                st.session_state[operation_status_key] = "inconclusive"
                st.session_state[inconclusive_key] = True
                st.session_state["vendas_create_feedback"] = {
                    "level": "warning",
                    "message": (
                        f"{error} A operação continua pendente; reconcilie "
                        "usando a chave original."
                    ),
                }
                should_rerun = True
            except RespostaVendaInconclusivaError as error:
                st.session_state[operation_status_key] = "inconclusive"
                st.session_state[inconclusive_key] = True
                st.session_state["vendas_create_feedback"] = {
                    "level": "warning",
                    "message": (
                        f"{error} A operação continua pendente; reconcilie "
                        "usando a chave original."
                    ),
                }
                should_rerun = True
            except requests.HTTPError as error:
                st.session_state[operation_status_key] = "inconclusive"
                st.session_state[inconclusive_key] = True
                status_code = getattr(
                    getattr(error, "response", None),
                    "status_code",
                    None,
                )
                idempotency_error = _codigo_erro_idempotencia_venda(error)
                if idempotency_error:
                    st.session_state[
                        "vendas_create_idempotency_error_code"
                    ] = idempotency_error
                if idempotency_error in {
                    "IDEMPOTENCY_LOCKED",
                    "IDEMPOTENCY_CONCURRENT_REQUEST",
                    "IDEMPOTENCY_LOCK_FAILED",
                }:
                    messages = {
                        "IDEMPOTENCY_LOCKED": (
                            "O Xano ainda está processando esta operação."
                        ),
                        "IDEMPOTENCY_CONCURRENT_REQUEST": (
                            "O Xano detectou uma solicitação concorrente."
                        ),
                        "IDEMPOTENCY_LOCK_FAILED": (
                            "O Xano não conseguiu obter o bloqueio de idempotência."
                        ),
                    }
                    message = messages[idempotency_error]
                elif idempotency_error == "IDEMPOTENCY_PAYLOAD_MISMATCH":
                    st.session_state[
                        "vendas_create_idempotency_blocked_fingerprint"
                    ] = fingerprint
                    message = (
                        "A chave de idempotência está associada a outro payload "
                        "de venda. A reconciliação continua bloqueada para análise "
                        "administrativa."
                    )
                elif status_code == 401:
                    message = (
                        "A sessão expirou ou não foi aceita pelo Xano."
                    )
                elif status_code == 403:
                    message = (
                        "Seu perfil não tem permissão para registrar vendas."
                    )
                else:
                    message = "O Xano retornou um erro HTTP sem confirmar o resultado."
                details = _mensagem_erro_xano(
                    error,
                    "POST",
                    "/sale",
                    sensitive_values=(token,),
                )
                st.session_state["vendas_create_feedback"] = {
                    "level": (
                        "warning"
                        if idempotency_error
                        in {
                            "IDEMPOTENCY_LOCKED",
                            "IDEMPOTENCY_CONCURRENT_REQUEST",
                            "IDEMPOTENCY_LOCK_FAILED",
                        }
                        else "error"
                    ),
                    "message": (
                        f"{message} {details} A operação permanece pendente; "
                        "reconcilie somente com a chave e o payload originais."
                    ),
                }
                should_rerun = True
            except requests.RequestException as error:
                st.session_state[operation_status_key] = "inconclusive"
                st.session_state[inconclusive_key] = True
                st.session_state["vendas_create_feedback"] = {
                    "level": "warning",
                    "message": (
                        f"{_mensagem_erro_xano(error, 'POST', '/sale', sensitive_values=(token,))} "
                        "A operação permanece pendente; reconcilie usando "
                        "a chave original."
                    ),
                }
                should_rerun = True
            except (TypeError, ValueError, RuntimeError) as error:
                st.session_state[operation_status_key] = "inconclusive"
                st.session_state[inconclusive_key] = True
                st.session_state["vendas_create_feedback"] = {
                    "level": "warning",
                    "message": (
                        f"{_mensagem_erro_xano(error, 'POST', '/sale', sensitive_values=(token,))} "
                        "A operação permanece pendente porque não foi "
                        "confirmada; reconcilie usando a chave original."
                    ),
                }
                should_rerun = True
            else:
                st.session_state["vendas_create_success"] = response
                st.session_state[operation_status_key] = "completed"
                st.session_state["vendas_create_toast_pending"] = True
                st.session_state[reset_key] = True
                st.session_state["vendas_create_feedback"] = None
                st.session_state[page_key] = 1
                st.session_state[pending_key] = True
                clear_detail()
                confirmed = True
            finally:
                st.session_state[submitting_key] = False
            if confirmed or should_rerun:
                st.rerun()

    if st.session_state.get(inconclusive_key):
        st.error(
            "O resultado da venda anterior ainda não foi confirmado. Não inicie "
            "outra venda. Use a ação explícita de reconciliação para reenviar "
            "somente o payload original com a mesma chave; nenhuma tentativa "
            "automática será feita."
        )

    feedback = st.session_state.get("vendas_create_feedback")
    if feedback:
        if feedback["level"] == "error":
            st.error(feedback["message"])
        elif feedback["level"] == "warning":
            st.warning(feedback["message"])

    if should_rerun:
        st.rerun()


def render_vendas():
    render_page_header(
        "Vendas",
        "Consulte vendas reais registradas no Xano.",
    )
    token = st.session_state.get("auth_token")
    created_sale = st.session_state.pop("vendas_create_success", None)
    if st.session_state.pop("vendas_create_toast_pending", False):
        show_toast("Venda registrada com confirmação do Xano.")
    if created_sale:
        current_channel = st.session_state.get("vendas_list_filter_channel")
        sale = created_sale.get("sale")
        created_channel = sale.get("sales_channel") if isinstance(sale, dict) else None
        if (
            not isinstance(current_channel, str)
            or not current_channel.strip()
        ) and isinstance(created_channel, str) and created_channel.strip():
            st.session_state["vendas_list_filter_channel"] = created_channel.strip()

    page_key = "vendas_list_page"
    result_key = "vendas_list_result"
    pending_key = "vendas_list_query_pending"
    detail_id_key = "vendas_detail_selected_id"
    detail_result_key = "vendas_detail_result"
    st.session_state.setdefault(page_key, 1)

    def clear_venda_detail():
        st.session_state.pop(detail_id_key, None)
        st.session_state.pop(detail_result_key, None)

    def submit_vendas_filters():
        st.session_state[page_key] = 1
        st.session_state[pending_key] = True
        clear_venda_detail()

    def navigate_vendas(page):
        st.session_state[page_key] = int(page)
        st.session_state[pending_key] = True
        clear_venda_detail()

    with st.form("vendas_list_filters_form"):
        filtros = st.columns(3)
        with filtros[0]:
            st.text_input(
                "Canal (obrigatório para consultar)",
                key="vendas_list_filter_channel",
                placeholder="Informe o canal de venda",
                help=(
                    "O Xano exige sales_channel na consulta. "
                    "Informe o canal usado na venda."
                ),
            )
        with filtros[1]:
            st.text_input(
                "Número do pedido",
                key="vendas_list_filter_order_number",
                placeholder="Opcional",
            )
        with filtros[2]:
            st.selectbox(
                "Status",
                ["Todos", "registrada", "cancelada"],
                key="vendas_list_filter_status",
            )

        datas = st.columns(2)
        with datas[0]:
            st.text_input(
                "Data inicial (timestamp)",
                key="vendas_list_filter_start_date",
                help="Informe o formato aceito pelo Xano; o valor será enviado sem conversão.",
            )
        with datas[1]:
            st.text_input(
                "Data final (timestamp)",
                key="vendas_list_filter_end_date",
                help="Informe o formato aceito pelo Xano; o valor será enviado sem conversão.",
            )
        st.number_input(
            "Registros por página",
            min_value=1,
            max_value=100,
            value=20,
            step=1,
            key="vendas_list_per_page",
        )
        st.form_submit_button(
            "Consultar vendas",
            type="primary",
            disabled=not token,
            on_click=submit_vendas_filters,
            key="vendas_list_submit",
        )

    if token and result_key not in st.session_state:
        channel = st.session_state.get("vendas_list_filter_channel")
        if isinstance(channel, str) and channel.strip():
            st.session_state[pending_key] = True
        else:
            st.session_state[result_key] = {
                "state": "validation",
                "message": "Informe o canal de venda para consultar as vendas.",
            }

    if st.session_state.pop(pending_key, False):
        if not token:
            st.session_state[result_key] = {
                "state": "error",
                "message": (
                    "Sua sessão expirou. Entre novamente para consultar vendas."
                ),
            }
        elif not str(
            st.session_state.get("vendas_list_filter_channel") or ""
        ).strip():
            st.session_state[result_key] = {
                "state": "validation",
                "message": "Informe o canal de venda para consultar as vendas.",
            }
        else:
            params = {
                "page": int(st.session_state.get(page_key, 1)),
                "per_page": int(st.session_state.get("vendas_list_per_page", 20)),
            }
            for state_key, parameter in (
                ("vendas_list_filter_channel", "sales_channel"),
                ("vendas_list_filter_order_number", "order_number"),
                ("vendas_list_filter_start_date", "start_date"),
                ("vendas_list_filter_end_date", "end_date"),
            ):
                value = st.session_state.get(state_key)
                if isinstance(value, str) and value.strip():
                    params[parameter] = value.strip()
            status = st.session_state.get("vendas_list_filter_status", "Todos")
            if status != "Todos":
                params["status"] = status

            try:
                with data_skeleton("table"), st.spinner(
                    "Consultando vendas no Xano..."
                ):
                    response = listar_vendas(token, **params)
                metadados_obrigatorios = {
                    "curPage",
                    "pageTotal",
                    "itemsTotal",
                    "itemsReceived",
                    "prevPage",
                    "nextPage",
                    "items",
                }
                if (
                    not isinstance(response, dict)
                    or not metadados_obrigatorios.issubset(response)
                    or not isinstance(response["items"], list)
                    or any(
                        not isinstance(item, dict)
                        for item in response["items"]
                    )
                ):
                    raise ValueError(
                        "O Xano retornou uma estrutura inválida de vendas."
                    )
                st.session_state[result_key] = {
                    "state": "success",
                    "response": response,
                }
            except requests.HTTPError as error:
                status_code = getattr(
                    getattr(error, "response", None),
                    "status_code",
                    None,
                )
                if status_code == 401:
                    prefix = (
                        "Sua sessão expirou ou não foi aceita pelo Xano. "
                        "Entre novamente para consultar vendas."
                    )
                elif status_code == 403:
                    prefix = (
                        "Seu perfil não tem permissão para consultar vendas."
                    )
                else:
                    prefix = ""
                message = _mensagem_erro_xano(
                    error,
                    "GET",
                    "/sale",
                    sensitive_values=(token,),
                )
                st.session_state[result_key] = {
                    "state": "error",
                    "message": " · ".join(
                        part for part in (prefix, message) if part
                    ),
                }
            except requests.RequestException as error:
                st.session_state[result_key] = {
                    "state": "error",
                    "message": _mensagem_erro_xano(
                        error,
                        "GET",
                        "/sale",
                        sensitive_values=(token,),
                    ),
                }
            except (RuntimeError, TypeError, ValueError) as error:
                st.session_state[result_key] = {
                    "state": "error",
                    "message": _mensagem_erro_xano(
                        error,
                        "GET",
                        "/sale",
                        sensitive_values=(token,),
                    ),
                }

    result = st.session_state.get(result_key)
    if not token:
        st.warning("Sua sessão expirou. Entre novamente para consultar vendas.")
    elif result is None:
        st.info("Consultando vendas no Xano...")
    elif result["state"] == "validation":
        st.info(result["message"])
    elif result["state"] == "error":
        st.error(result["message"])
    else:
        response = result["response"]
        rows = response["items"]
        st.caption(
            f"Página {response['curPage']} de {response['pageTotal']} · "
            f"{response['itemsTotal']} venda(s) no total · "
            f"{response['itemsReceived']} nesta página"
        )
        if rows:
            display_rows = []
            for item in rows:
                row = dict(item)
                if "sale_date" in row and row["sale_date"] not in (None, ""):
                    try:
                        row["sale_date"] = format_sale_date(row["sale_date"])
                    except (TypeError, ValueError, OverflowError):
                        row["sale_date"] = "Data inválida"
                display_rows.append(row)
            render_dataframe(
                pd.DataFrame(display_rows),
                width="stretch",
                hide_index=True,
            )
        else:
            st.info("Nenhuma venda encontrada para os filtros informados.")

        navegacao = st.columns(2)
        with navegacao[0]:
            st.button(
                "Página anterior",
                key="vendas_list_previous",
                disabled=response["prevPage"] is None,
                on_click=navigate_vendas,
                args=(response["prevPage"] or 1,),
            )
        with navegacao[1]:
            st.button(
                "Próxima página",
                key="vendas_list_next",
                disabled=response["nextPage"] is None,
                on_click=navigate_vendas,
                args=(response["nextPage"] or response["curPage"],),
            )

        venda_ids = list(
            dict.fromkeys(
                sale_id
                for row in rows
                if isinstance(row, dict)
                for sale_id in (
                    _normalizar_id_venda_interface(row.get("id")),
                )
                if sale_id is not None
            )
        )
        if venda_ids:
            st.subheader("Consultar detalhes")
            st.selectbox(
                "Venda",
                options=venda_ids,
                format_func=lambda sale_id: f"Venda {sale_id}",
                key=detail_id_key,
            )
            if st.button(
                "Consultar detalhes da venda",
                key="vendas_detail_submit",
                disabled=not token,
            ):
                if not token:
                    st.session_state[detail_result_key] = {
                        "sale_id": st.session_state[detail_id_key],
                        "state": "error",
                        "message": (
                            "Sua sessão expirou. Entre novamente para "
                            "consultar os detalhes da venda."
                        ),
                    }
                else:
                    sale_id = _normalizar_id_venda_interface(
                        st.session_state[detail_id_key]
                    )
                    try:
                        with data_skeleton("rows", 4), st.spinner(
                            "Consultando detalhes da venda..."
                        ):
                            detail_response = consultar_venda(token, sale_id)
                        if not _validar_detalhe_venda_interface(
                            detail_response,
                            sale_id,
                        ):
                            raise ValueError(
                                "O Xano retornou uma resposta incompleta ou "
                                "incompatível com a venda selecionada."
                            )
                        st.session_state[detail_result_key] = {
                            "sale_id": sale_id,
                            "state": "success",
                            "response": detail_response,
                        }
                    except requests.HTTPError as error:
                        status_code = getattr(
                            getattr(error, "response", None),
                            "status_code",
                            None,
                        )
                        if status_code == 401:
                            prefix = (
                                "Sua sessão expirou ou não foi aceita pelo "
                                "Xano. Entre novamente para consultar vendas."
                            )
                        elif status_code == 403:
                            prefix = (
                                "Seu perfil não tem permissão para consultar "
                                "os detalhes desta venda."
                            )
                        elif status_code == 404:
                            prefix = (
                                "A venda selecionada não foi encontrada no "
                                "Xano."
                            )
                        else:
                            prefix = ""
                        message = _mensagem_erro_xano(
                            error,
                            "GET",
                            f"/sale/{sale_id}",
                            sensitive_values=(token,),
                        )
                        st.session_state[detail_result_key] = {
                            "sale_id": sale_id,
                            "state": "error",
                            "message": " · ".join(
                                part for part in (prefix, message) if part
                            ),
                        }
                    except requests.RequestException as error:
                        st.session_state[detail_result_key] = {
                            "sale_id": sale_id,
                            "state": "error",
                            "message": _mensagem_erro_xano(
                                error,
                                "GET",
                                f"/sale/{sale_id}",
                                sensitive_values=(token,),
                            ),
                        }
                    except (RuntimeError, TypeError, ValueError) as error:
                        st.session_state[detail_result_key] = {
                            "sale_id": sale_id,
                            "state": "error",
                            "message": _mensagem_erro_xano(
                                error,
                                "GET",
                                f"/sale/{sale_id}",
                                sensitive_values=(token,),
                            ),
                        }

            detail_result = st.session_state.get(detail_result_key)
            selected_id = _normalizar_id_venda_interface(
                st.session_state.get(detail_id_key)
            )
            if (
                isinstance(detail_result, dict)
                and detail_result.get("sale_id") == selected_id
            ):
                st.markdown("<div class='erp-section'></div>", unsafe_allow_html=True)
                st.subheader(f"Detalhes da venda {selected_id}")
                if detail_result.get("state") == "success":
                    _render_conteudo_detalhe_venda(
                        detail_result["response"]
                    )
                else:
                    st.error(detail_result["message"])
                if st.button("Fechar detalhes", key="vendas_detail_close"):
                    clear_venda_detail()
        else:
            st.info(
                "Não há identificadores válidos de venda nesta página para "
                "consultar detalhes."
            )

    if created_sale:
        st.success("Venda registrada com confirmação do Xano.")
        st.markdown("#### Resumo financeiro retornado pelo Xano")
        render_dataframe(
            pd.DataFrame([created_sale["financial_summary"]]),
            width="stretch",
            hide_index=True,
        )

    st.markdown("<div class='erp-section'></div>", unsafe_allow_html=True)
    left, right = st.columns([1.2, 0.8])
    with left:
        _render_formulario_venda(
            token,
            page_key=page_key,
            pending_key=pending_key,
            clear_detail=clear_venda_detail,
        )
    with right:
        st.markdown("<div class='erp-panel-header'><div class='erp-panel-title'>Importar arquivo</div></div>", unsafe_allow_html=True)
        _render_importacao_vendas_excel(token)


def render_fornecedores():
    token = st.session_state.get("auth_token")
    mensagem_sucesso = st.session_state.pop(
        "mensagem_sucesso_fornecedores",
        None,
    )
    feedback_formulario = st.session_state.pop(
        "fornecedor_feedback",
        None,
    )
    if feedback_formulario:
        nivel, mensagem = feedback_formulario
        if nivel == "inconclusive":
            st.warning(mensagem)
        else:
            st.error(mensagem)
    if st.session_state.pop("fornecedor_toast_pending", False):
        show_toast("Fornecedor salvo com confirmação do Xano.")
    render_page_header(
        "Fornecedores",
        "Consulte e mantenha os fornecedores no Xano.",
        show_actions=False,
    )
    with st.form("form_busca_fornecedores_xano"):
        nome = st.text_input(
            "Nome do fornecedor",
            placeholder="Filtro opcional",
            key="busca_fornecedores_nome",
        )
        status = st.text_input(
            "Status",
            value="ativo",
            placeholder="Valor aceito pelo Xano (opcional)",
            help="A consulta padrão lista fornecedores ativos; altere para outro status aceito pelo Xano se necessário.",
            key="busca_fornecedores_status",
        )
        consultar = st.form_submit_button(
            "Consultar fornecedores",
            type="primary",
            key="consultar_fornecedores_submit",
        )

    if "consulta_fornecedores_resultado" not in st.session_state and token:
        with data_skeleton("table"):
            estado, fornecedores, erro = _consultar_fornecedores(
                token,
                status=status,
            )
        st.session_state["consulta_fornecedores_resultado"] = {
            "state": estado,
            "suppliers": fornecedores,
            "error": erro,
        }

    if consultar:
        with data_skeleton("table"):
            estado, fornecedores, erro = _consultar_fornecedores(
                st.session_state.get("auth_token"),
                name=nome,
                status=status,
            )
        st.session_state["consulta_fornecedores_resultado"] = {
            "state": estado,
            "suppliers": fornecedores,
            "error": erro,
        }

    if st.session_state.pop("recarregar_listagem_fornecedores", False):
        with data_skeleton("table"):
            estado, fornecedores, erro = _consultar_fornecedores(
                token,
                name=nome,
                status=status,
            )
        st.session_state["consulta_fornecedores_resultado"] = {
            "state": estado,
            "suppliers": fornecedores,
            "error": erro,
        }

    resultado = st.session_state.get("consulta_fornecedores_resultado")
    if resultado is None:
        st.info("Execute a consulta para carregar os fornecedores do Xano.")
    elif resultado["state"] == "error":
        st.error(resultado["error"])
    elif not resultado["suppliers"]:
        st.info("Nenhum fornecedor encontrado.")
    else:
        rows = [
            {
                "Fornecedor": supplier["name"],
                "CNPJ": supplier.get("cnpj", ""),
                "Contato": supplier.get("contact_name", ""),
                "E-mail": supplier.get("email", ""),
                "Telefone": supplier.get("phone", ""),
                "Status": supplier.get("status", ""),
            }
            for supplier in resultado["suppliers"]
        ]
        st.caption(f"{len(rows)} fornecedor(es) retornado(s) pelo Xano.")
        render_dataframe(
            pd.DataFrame(rows),
            width="stretch",
            hide_index=True,
        )

    if mensagem_sucesso:
        st.success(mensagem_sucesso)

    st.markdown("<div class='erp-section'></div>", unsafe_allow_html=True)
    st.subheader("Cadastrar fornecedor")
    with st.form("form_cadastro_fornecedor_xano"):
        create_name = st.text_input("Nome *", key="novo_fornecedor_nome")
        create_contact = st.text_input("Nome do contato", key="novo_fornecedor_contato")
        create_cnpj = st.text_input("CNPJ", key="novo_fornecedor_cnpj")
        create_email = st.text_input("E-mail", key="novo_fornecedor_email")
        create_phone = st.text_input("Telefone", key="novo_fornecedor_telefone")
        create_submit = st.form_submit_button(
            "Cadastrar fornecedor",
            key="cadastrar_fornecedor_submit",
        )

    if create_submit:
        if create_cnpj.strip() and not validar_cnpj(create_cnpj):
            st.error("Informe um CNPJ válido.")
        elif not create_name.strip():
            st.error("Informe o nome do fornecedor.")
        else:
            fields = {
                "name": create_name,
                "contact_name": create_contact,
                "cnpj": create_cnpj,
                "email": create_email,
                "phone": create_phone,
            }

            def cadastrar_fornecedor_confirmado():
                state, record, error = _cadastrar_fornecedor(
                    token,
                    **fields,
                )
                if state == "success":
                    st.session_state["mensagem_sucesso_fornecedores"] = (
                        "Fornecedor cadastrado com confirmação do Xano."
                    )
                    st.session_state["recarregar_listagem_fornecedores"] = True
                    st.session_state["fornecedor_toast_pending"] = True
                else:
                    st.session_state["fornecedor_feedback"] = (
                        state,
                        error,
                    )

            show_confirmation_dialog(
                "Confirmar cadastro do fornecedor",
                {
                    "Fornecedor": create_name.strip(),
                    "Contato": create_contact.strip() or "Não informado",
                    "CNPJ": create_cnpj.strip() or "Não informado",
                    "E-mail": create_email.strip() or "Não informado",
                    "Telefone": create_phone.strip() or "Não informado",
                },
                cadastrar_fornecedor_confirmado,
                key="fornecedor_create_confirmation",
            )

    suppliers_with_ids = []
    if resultado and resultado["state"] == "success":
        suppliers_with_ids = [
            supplier
            for supplier in resultado["suppliers"]
            if isinstance(supplier.get("id"), int)
            and not isinstance(supplier.get("id"), bool)
        ]
    if suppliers_with_ids:
        st.markdown("<div class='erp-section'></div>", unsafe_allow_html=True)
        selected_supplier = st.selectbox(
            "Fornecedor para consultar ou editar",
            options=suppliers_with_ids,
            format_func=lambda item: f"{item['name']} (ID {item['id']})",
            key="fornecedor_selecionado_para_edicao",
        )
        if st.button(
            "Consultar detalhe do fornecedor",
            key="consultar_detalhe_fornecedor",
        ):
            with data_skeleton("rows", 3):
                state, record, error = _consultar_fornecedor_por_id(
                    token,
                    selected_supplier["id"],
                )
            if state == "success":
                st.session_state["fornecedor_detalhe_xano"] = record
                st.session_state.pop("fornecedor_detalhe_erro", None)
            elif state == "inconclusive":
                st.session_state["fornecedor_detalhe_erro"] = (
                    "A consulta individual não foi confirmada."
                )
            else:
                st.session_state["fornecedor_detalhe_erro"] = error

        supplier_detail = st.session_state.get("fornecedor_detalhe_xano")
        if (
            isinstance(supplier_detail, dict)
            and supplier_detail.get("id") != selected_supplier["id"]
        ):
            supplier_detail = None
        if st.session_state.get("fornecedor_detalhe_erro"):
            st.error(st.session_state.pop("fornecedor_detalhe_erro"))

        if supplier_detail:
            st.subheader("Detalhe do fornecedor")
            with st.container(border=True):
                title_column, status_column = st.columns([3, 1])
                with title_column:
                    st.markdown(
                        f"#### {html.escape(_texto_interface(supplier_detail.get('name')))}"
                    )
                with status_column:
                    st.markdown("**Situação**")
                    _render_status_badge(supplier_detail.get("status"))
                supplier_columns = st.columns(3)
                supplier_fields = (
                    ("Contato", supplier_detail.get("contact_name")),
                    ("CNPJ", supplier_detail.get("cnpj")),
                    ("E-mail", supplier_detail.get("email")),
                    ("Telefone", supplier_detail.get("phone")),
                )
                for index, (label, value) in enumerate(supplier_fields):
                    with supplier_columns[index % len(supplier_columns)]:
                        st.metric(label, _texto_interface(value))
            status_options = ["ativo", "inativo"]
            current_status = supplier_detail.get("status", "ativo")
            status_index = (
                status_options.index(current_status)
                if current_status in status_options
                else 0
            )
            with st.form("form_edicao_fornecedor_xano"):
                edit_name = st.text_input(
                    "Nome *",
                    value=_texto_interface(
                        supplier_detail.get("name"),
                        fallback="",
                    ),
                    key="editar_fornecedor_nome",
                )
                edit_contact = st.text_input(
                    "Nome do contato",
                    value=_texto_interface(
                        supplier_detail.get("contact_name"),
                        fallback="",
                    ),
                    key="editar_fornecedor_contato",
                )
                edit_cnpj = st.text_input(
                    "CNPJ",
                    value=_texto_interface(
                        supplier_detail.get("cnpj"),
                        fallback="",
                    ),
                    key="editar_fornecedor_cnpj",
                )
                edit_email = st.text_input(
                    "E-mail",
                    value=_texto_interface(
                        supplier_detail.get("email"),
                        fallback="",
                    ),
                    key="editar_fornecedor_email",
                )
                edit_phone = st.text_input(
                    "Telefone",
                    value=_texto_interface(
                        supplier_detail.get("phone"),
                        fallback="",
                    ),
                    key="editar_fornecedor_telefone",
                )
                edit_status = st.selectbox(
                    "Status",
                    options=status_options,
                    index=status_index,
                    key="editar_fornecedor_status",
                )
                edit_submit = st.form_submit_button(
                    "Salvar alterações do fornecedor",
                    key="salvar_edicao_fornecedor",
                )
            if edit_submit:
                changes = {}
                for field, value, original in (
                    ("name", edit_name, supplier_detail.get("name", "")),
                    ("contact_name", edit_contact, supplier_detail.get("contact_name") or ""),
                    ("cnpj", edit_cnpj, supplier_detail.get("cnpj") or ""),
                    ("email", edit_email, supplier_detail.get("email") or ""),
                    ("phone", edit_phone, supplier_detail.get("phone") or ""),
                ):
                    if value.strip() != original and not (
                        field == "cnpj" and not value.strip()
                    ):
                        changes[field] = value
                if edit_status != current_status:
                    changes["status"] = edit_status

                if not edit_name.strip():
                    st.error("Informe o nome do fornecedor.")
                elif edit_cnpj.strip() and not validar_cnpj(edit_cnpj):
                    st.error("Informe um CNPJ válido.")
                elif not changes:
                    st.info("Nenhuma alteração foi informada.")
                elif edit_status == "inativo" and current_status != "inativo":
                    st.error(
                        "Use a ação de inativação com confirmação explícita."
                    )
                else:
                    def salvar_fornecedor_editado():
                        state, record, error = _salvar_edicao_fornecedor(
                            token,
                            supplier_detail["id"],
                            **changes,
                        )
                        if state == "success":
                            st.session_state["fornecedor_detalhe_xano"] = record
                            st.session_state[
                                "mensagem_sucesso_fornecedores"
                            ] = "Fornecedor atualizado com confirmação do Xano."
                            st.session_state[
                                "recarregar_listagem_fornecedores"
                            ] = True
                            st.session_state["fornecedor_toast_pending"] = True
                        else:
                            st.session_state["fornecedor_feedback"] = (
                                state,
                                error,
                            )

                    show_confirmation_dialog(
                        "Confirmar alterações do fornecedor",
                        {
                            "Fornecedor": supplier_detail.get("name", "Fornecedor"),
                            "Campos alterados": ", ".join(changes),
                        },
                        salvar_fornecedor_editado,
                        key="fornecedor_edit_confirmation",
                    )

            confirm_deactivate = st.checkbox(
                "Confirmo a inativação lógica deste fornecedor",
                key="confirmar_inativacao_fornecedor",
            )
            if st.button(
                "Inativar fornecedor",
                disabled=not confirm_deactivate,
                key="inativar_fornecedor",
            ):
                def inativar_fornecedor_confirmado():
                    state, record, error = _inativar_fornecedor(
                        token,
                        supplier_detail["id"],
                    )
                    if state == "success":
                        st.session_state["fornecedor_detalhe_xano"] = record
                        st.session_state[
                            "mensagem_sucesso_fornecedores"
                        ] = "Fornecedor inativado com confirmação do Xano."
                        st.session_state[
                            "recarregar_listagem_fornecedores"
                        ] = True
                        st.session_state["fornecedor_toast_pending"] = True
                    else:
                        st.session_state["fornecedor_feedback"] = (
                            state,
                            error,
                        )

                show_confirmation_dialog(
                    "Confirmar inativação do fornecedor",
                    {
                        "Fornecedor": supplier_detail.get("name", "Fornecedor"),
                        "Efeito": "O fornecedor será inativado sem apagar o histórico.",
                    },
                    inativar_fornecedor_confirmado,
                    key="fornecedor_deactivate_confirmation",
                )


def render_relatorios():
    render_page_header(
        "Relatórios",
        "Relatórios operacionais e financeiros obtidos do Xano.",
        show_actions=False,
    )
    token = st.session_state.get("auth_token")
    if not isinstance(token, str) or not token.strip():
        st.warning("Sua sessão expirou. Entre novamente para consultar relatórios.")
        return
    _preparar_escopo_analytics(token)

    today = date.today()
    with st.form("reports_filters"):
        columns = st.columns(4)
        with columns[0]:
            start_date = st.date_input(
                "Período inicial",
                value=today.replace(day=1),
                key="reports_start_date",
            )
        with columns[1]:
            end_date = st.date_input(
                "Período final",
                value=today,
                key="reports_end_date",
            )
        with columns[2]:
            report_type = st.selectbox(
                "Tipo",
                options=("Vendas", "CMV", "Lucro", "Estoque"),
                key="reports_type",
            )
        with columns[3]:
            sales_channel = st.text_input(
                "Canal de venda",
                key="reports_sales_channel",
                disabled=report_type == "Estoque",
                help="Obrigatório para relatórios de vendas; GET /sale exige sales_channel.",
            )
        generate = st.form_submit_button(
            "Gerar / atualizar relatório",
            key="reports_generate",
        )

    channel_filter = (
        sales_channel.strip()
        if report_type != "Estoque"
        else ""
    )
    filters = (report_type, start_date, end_date, channel_filter)
    if generate:
        if report_type == "Estoque":
            with data_skeleton("cards", 4), st.spinner(
                "Consultando saldo atual no Xano..."
            ):
                stock_state, products, error = _consultar_saldo_estoque(token)
            result = {
                "state": stock_state,
                "products": products,
                "message": error,
            }
        else:
            with data_skeleton("table"), st.spinner(
                "Consultando vendas e detalhes financeiros no Xano..."
            ):
                result = _vendas_com_detalhes_financeiros(
                    token,
                    sales_channel,
                    start_date,
                    end_date,
                )
        st.session_state[_REPORT_RESULT_KEY] = {
            "filters": filters,
            "result": result,
        }

    cached_report = st.session_state.get(_REPORT_RESULT_KEY)
    if cached_report is None:
        st.info("Selecione os filtros e gere o relatório para consultar o Xano.")
        return
    if cached_report.get("filters") != filters:
        st.info("Os filtros foram alterados. Gere o relatório para atualizar os dados.")
        return

    result = cached_report["result"]
    if result["state"] == "validation":
        st.info(result["message"])
        return
    if result["state"] != "success":
        st.error(
            result.get("message")
            or "Não foi possível consultar os dados no Xano."
        )
        st.info("Revise os filtros ou gere o relatório novamente.")
        return

    if report_type == "Estoque":
        st.caption(
            "Este relatório mostra o saldo atual dos produtos ativos. "
            "O endpoint disponível não fornece posição histórica por período."
        )
        table, _ = _render_resumo_estoque_analytics(result["products"])
        if not table.empty:
            st.download_button(
                "Exportar CSV",
                data=table.to_csv(index=False).encode("utf-8-sig"),
                file_name="relatorio_estoque_xano.csv",
                mime="text/csv",
                key="reports_export_stock",
            )
        return

    sales = result["sales"]
    _render_indicadores_financeiros(result["summary"], len(sales))
    _render_grafico_financeiro_vendas(
        sales,
        report_type=report_type,
    )
    if sales:
        table = _tabela_vendas_financeiras(sales, report_type)
        render_dataframe(table, width="stretch", hide_index=True)
        st.download_button(
            "Exportar CSV",
            data=table.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"relatorio_{report_type.lower()}_xano.csv",
            mime="text/csv",
            key="reports_export_sales",
        )


_USUARIOS_LISTA_STATE_KEY = "usuarios_admin_lista"
_USUARIOS_REFRESH_PENDENTE_KEY = "usuarios_admin_atualizar_lista"
_USUARIOS_EXIGE_REFRESH_KEY = "usuarios_admin_exige_atualizacao"
_USUARIOS_FEEDBACK_KEY = "usuarios_admin_feedback"
_USUARIOS_FORM_VERSION_KEY = "usuarios_admin_form_version"
_USUARIOS_CADASTRO_EM_ANDAMENTO_KEY = "usuarios_admin_cadastro_em_andamento"


def _usuario_tem_perfil_adm_exato(usuario):
    if not isinstance(usuario, dict):
        return False
    perfis = [
        usuario[field]
        for field in ("role", "perfil", "tipo_perfil", "profile")
        if isinstance(usuario.get(field), str) and usuario[field]
    ]
    return bool(perfis) and all(perfil == "Adm" for perfil in perfis)


def _consultar_usuarios_admin(token):
    try:
        return {"ok": True, "users": listar_usuarios(token), "message": None}
    except requests.HTTPError as error:
        status_code = getattr(
            getattr(error, "response", None),
            "status_code",
            None,
        )
        if status_code == 401:
            message = "A sessão expirou. Entre novamente para consultar usuários."
        elif status_code == 403:
            message = "O Xano negou a permissão para consultar usuários."
        else:
            message = (
                "Falha ao consultar usuários no Xano. "
                + _mensagem_erro_xano(
                    error,
                    "GET",
                    "/user",
                    sensitive_values=(token,),
                )
            )
        return {"ok": False, "users": [], "message": message}
    except requests.RequestException as error:
        return {
            "ok": False,
            "users": [],
            "message": (
                "Falha de comunicação ao consultar usuários no Xano. "
                + _mensagem_erro_xano(
                    error,
                    "GET",
                    "/user",
                    sensitive_values=(token,),
                )
            ),
        }
    except (RuntimeError, ValueError) as error:
        return {
            "ok": False,
            "users": [],
            "message": (
                "O Xano não retornou uma lista de usuários válida. "
                + _mensagem_erro_xano(
                    error,
                    "GET",
                    "/user",
                    sensitive_values=(token,),
                )
            ),
        }


def _resposta_indica_email_duplicado(error):
    response = getattr(error, "response", None)
    if getattr(response, "status_code", None) != 400:
        return False
    try:
        payload = response.json()
    except (ValueError, requests.RequestException):
        payload = None

    messages = []
    if isinstance(payload, dict):
        for key in ("message", "error", "description", "detail", "code"):
            value = payload.get(key)
            if isinstance(value, str):
                messages.append(value)
    if not messages:
        response_text = getattr(response, "text", "")
        if isinstance(response_text, str):
            messages.append(response_text)

    combined = " ".join(messages).lower()
    mentions_email = "email" in combined or "e-mail" in combined
    indicates_duplicate = any(
        marker in combined
        for marker in (
            "already exists",
            "already registered",
            "already taken",
            "already in use",
            "already_exists",
            "already_registered",
            "email_exists",
            "duplicate_email",
            "duplicate",
            "unique",
            "unique constraint",
            "já cadastrado",
            "já existe",
            "duplicad",
            "em uso",
        )
    )
    return mentions_email and indicates_duplicate


def _definir_feedback_usuario(level, message):
    st.session_state[_USUARIOS_FEEDBACK_KEY] = {
        "level": level,
        "message": message,
    }


def _processar_cadastro_usuario(form_version, name, email, password, role):
    state = st.session_state
    if state.get(_USUARIOS_CADASTRO_EM_ANDAMENTO_KEY):
        return
    if form_version != state.get(_USUARIOS_FORM_VERSION_KEY, form_version):
        return

    token = state.get("auth_token")
    try:
        if not _usuario_tem_perfil_adm_exato(state.get("auth_user")):
            _definir_feedback_usuario(
                "error",
                "Acesso restrito: somente o perfil Adm pode cadastrar usuários.",
            )
            return
        if not isinstance(token, str) or not token.strip():
            _definir_feedback_usuario(
                "error",
                "A sessão expirou. Entre novamente para cadastrar usuários.",
            )
            return

        try:
            payload = validar_dados_usuario(
                name=name,
                email=email,
                password=password,
                role=role,
            )
        except ValueError as error:
            _definir_feedback_usuario("error", str(error))
            return

        state[_USUARIOS_CADASTRO_EM_ANDAMENTO_KEY] = True
        try:
            criar_usuario(token, **payload)
        except requests.HTTPError as error:
            status_code = getattr(
                getattr(error, "response", None),
                "status_code",
                None,
            )
            details = _mensagem_erro_xano(
                error,
                "POST",
                "/user",
                sensitive_values=(token, email, password),
            )
            if status_code == 400 and _resposta_indica_email_duplicado(error):
                _definir_feedback_usuario(
                    "error",
                    "Este e-mail já está cadastrado. " + details,
                )
            elif status_code == 400:
                _definir_feedback_usuario(
                    "error",
                    "O Xano rejeitou os dados do cadastro. " + details,
                )
            elif status_code == 401:
                _definir_feedback_usuario(
                    "error",
                    "A sessão expirou ou não é válida para cadastrar usuários.",
                )
            elif status_code == 403:
                _definir_feedback_usuario(
                    "error",
                    "O Xano negou a permissão administrativa para este cadastro.",
                )
            else:
                state[_USUARIOS_EXIGE_REFRESH_KEY] = True
                _definir_feedback_usuario(
                    "warning",
                    "O Xano não confirmou o cadastro. Atualize a listagem "
                    "antes de tentar novamente. Não houve reenvio automático. "
                    + details,
                )
        except (
            OperacaoUsuarioInconclusivaError,
            RespostaUsuarioInconclusivaError,
            requests.RequestException,
        ) as error:
            state[_USUARIOS_EXIGE_REFRESH_KEY] = True
            _definir_feedback_usuario(
                "warning",
                "Não foi possível confirmar se o usuário foi cadastrado. "
                "Atualize a listagem antes de tentar novamente. "
                "Não houve reenvio automático. "
                + _mensagem_erro_xano(
                    error,
                    "POST",
                    "/user",
                    sensitive_values=(token, email, password),
                ),
            )
        except (RuntimeError, ValueError) as error:
            _definir_feedback_usuario(
                "error",
                "Não foi possível enviar o cadastro. "
                + _mensagem_erro_xano(
                    error,
                    "POST",
                    "/user",
                    sensitive_values=(token, email, password),
                ),
            )
        else:
            _definir_feedback_usuario(
                "success",
                "Usuário cadastrado com confirmação do Xano.",
            )
            state[_USUARIOS_REFRESH_PENDENTE_KEY] = True
            state[_USUARIOS_EXIGE_REFRESH_KEY] = False
    finally:
        state[_USUARIOS_CADASTRO_EM_ANDAMENTO_KEY] = False
        state[_USUARIOS_FORM_VERSION_KEY] = form_version + 1


def _exibir_feedback_usuario(feedback):
    if not isinstance(feedback, dict):
        return
    level = feedback.get("level")
    message = feedback.get("message", "")
    if level == "success":
        st.success(message)
        show_toast("Usuário cadastrado com confirmação do Xano.")
    elif level == "warning":
        st.warning(message)
    else:
        st.error(message)


def render_usuarios():
    render_page_header(
        "Usuários e permissões",
        "Gestão de acesso e perfis do sistema.",
        show_actions=False,
    )
    usuario = st.session_state.get("auth_user")
    if not _usuario_tem_perfil_adm_exato(usuario):
        st.error("Acesso restrito: somente o perfil Adm pode gerenciar usuários.")
        return

    token = st.session_state.get("auth_token")
    if not isinstance(token, str) or not token.strip():
        st.error("A sessão expirou. Entre novamente para gerenciar usuários.")
        return

    st.subheader("Usuários cadastrados")
    refresh_clicked = st.button(
        "Atualizar listagem",
        key="usuarios_admin_refresh",
    )
    refresh_pending = st.session_state.pop(
        _USUARIOS_REFRESH_PENDENTE_KEY,
        False,
    )
    if (
        _USUARIOS_LISTA_STATE_KEY not in st.session_state
        or refresh_clicked
        or refresh_pending
    ):
        with data_skeleton("table"):
            list_result = _consultar_usuarios_admin(token)
        st.session_state[_USUARIOS_LISTA_STATE_KEY] = list_result
        if list_result["ok"] and st.session_state.get(
            _USUARIOS_EXIGE_REFRESH_KEY
        ):
            st.session_state[_USUARIOS_EXIGE_REFRESH_KEY] = False

    list_result = st.session_state.get(_USUARIOS_LISTA_STATE_KEY, {})
    if list_result.get("ok"):
        users = list_result["users"]
        if users:
            render_dataframe(
                pd.DataFrame(
                    [
                        {
                            "Nome": user["name"],
                            "E-mail": user["email"],
                            "Perfil": user["role"],
                            "Criado em": user["created_at"],
                        }
                        for user in users
                    ]
                ),
                width="stretch",
                hide_index=True,
            )
        else:
            st.info("Nenhum usuário foi retornado pelo Xano.")
    else:
        st.error(
            list_result.get(
                "message",
                "Não foi possível consultar os usuários no Xano.",
            )
        )

    feedback = st.session_state.pop(_USUARIOS_FEEDBACK_KEY, None)
    _exibir_feedback_usuario(feedback)

    requires_refresh = st.session_state.get(_USUARIOS_EXIGE_REFRESH_KEY, False)
    if requires_refresh:
        st.warning(
            "Antes de uma nova tentativa, atualize a listagem para verificar "
            "se o Xano já criou o usuário."
        )

    st.subheader("Cadastrar usuário")
    form_version = st.session_state.setdefault(_USUARIOS_FORM_VERSION_KEY, 0)
    disabled = bool(requires_refresh) or bool(
        st.session_state.get(_USUARIOS_CADASTRO_EM_ANDAMENTO_KEY)
    )
    with st.form(
        key=f"usuarios_admin_form_{form_version}",
        clear_on_submit=False,
    ):
        name = st.text_input("Nome completo")
        email = st.text_input("E-mail")
        password = st.text_input(
            "Senha",
            type="password",
        )
        role = st.selectbox(
            "Perfil",
            options=USER_ROLES,
        )
        submitted = st.form_submit_button(
            "Salvar",
            key=f"usuarios_admin_submit_{form_version}",
            disabled=disabled,
        )
    if submitted:
        show_confirmation_dialog(
            "Confirmar cadastro do usuário",
            {
                "Nome": name.strip() or "Não informado",
                "E-mail": email.strip() or "Não informado",
                "Perfil": role,
                "Senha": "Preenchida; o valor não será exibido.",
            },
            lambda: _processar_cadastro_usuario(
                form_version,
                name,
                email,
                password,
                role,
            ),
            key=f"usuario_create_confirmation_{form_version}",
        )


def render_module(page_name):
    mapping = {
        "Visão geral": render_vision_geral,
        "Produtos": render_produtos,
        "Estoque": render_estoque,
        "Vendas": render_vendas,
        "Fornecedores": render_fornecedores,
        "Relatórios": render_relatorios,
        "Usuários e permissões": render_usuarios,
    }
    mapping.get(page_name, render_vision_geral)()
