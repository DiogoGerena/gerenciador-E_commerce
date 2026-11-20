import math
import os
import uuid
from datetime import datetime
from decimal import Decimal, InvalidOperation
from urllib.parse import urlparse

import requests
import streamlit as st


def _build_api_url(base_url, endpoint):
    """Constrói a URL da API sem duplicar prefixos do Xano."""
    base = str(base_url or "").strip().rstrip("/")
    if not base:
        raise ValueError("XANO_API_URL não está configurada.")

    rota = str(endpoint or "").strip()
    if not rota:
        return base

    path_base = urlparse(base).path.rstrip("/")
    path_rota = rota.lstrip("/")

    if path_base and path_rota.startswith(path_base.lstrip("/")):
        path_rota = path_rota[len(path_base.lstrip("/")) :].lstrip("/")

    if not path_rota:
        return base

    return f"{base}/{path_rota}"


def _get_streamlit_secret(name):
    """Lê um segredo do Streamlit, validando a configuração."""
    secrets = getattr(st, "secrets", None)

    if secrets is None:
        return None

    if not hasattr(secrets, "get"):
        raise RuntimeError(
            "Configuração inválida de st.secrets: "
            "o objeto de segredos não possui o método get()."
        )

    value = secrets.get(name)

    if value is None or value == "":
        return None

    return str(value)


def get_xano_config():
    """Obtém as URLs do Xano e um token opcional."""
    base_url = os.getenv("XANO_API_URL") or _get_streamlit_secret("XANO_API_URL")
    auth_base_url = (
        os.getenv("XANO_AUTH_URL")
        or _get_streamlit_secret("XANO_AUTH_URL")
        or base_url
    )
    categories_base_url = (
        os.getenv("XANO_CATEGORIES_URL")
        or _get_streamlit_secret("XANO_CATEGORIES_URL")
        or os.getenv("XANO_RESOURCES_URL")
        or _get_streamlit_secret("XANO_RESOURCES_URL")
        or base_url
    )
    products_base_url = (
        os.getenv("XANO_PRODUCTS_URL")
        or _get_streamlit_secret("XANO_PRODUCTS_URL")
        or os.getenv("XANO_RESOURCES_URL")
        or _get_streamlit_secret("XANO_RESOURCES_URL")
        or base_url
    )
    suppliers_base_url = (
        os.getenv("XANO_SUPPLIERS_URL")
        or _get_streamlit_secret("XANO_SUPPLIERS_URL")
        or os.getenv("XANO_RESOURCES_URL")
        or _get_streamlit_secret("XANO_RESOURCES_URL")
        or base_url
    )
    stock_entries_base_url = (
        os.getenv("XANO_STOCK_ENTRIES_URL")
        or _get_streamlit_secret("XANO_STOCK_ENTRIES_URL")
        or base_url
    )
    stock_movements_base_url = (
        os.getenv("XANO_STOCK_MOVEMENTS_URL")
        or _get_streamlit_secret("XANO_STOCK_MOVEMENTS_URL")
        or base_url
    )
    sales_base_url = (
        os.getenv("XANO_SALES_URL")
        or _get_streamlit_secret("XANO_SALES_URL")
        or base_url
    )
    token = os.getenv("XANO_API_TOKEN") or _get_streamlit_secret("XANO_API_TOKEN")

    if not base_url:
        raise ValueError("XANO_API_URL não está configurada.")

    return {
        "base_url": base_url.rstrip("/"),
        "auth_base_url": auth_base_url.rstrip("/"),
        "categories_base_url": categories_base_url.rstrip("/"),
        "products_base_url": products_base_url.rstrip("/"),
        "suppliers_base_url": suppliers_base_url.rstrip("/"),
        "stock_entries_base_url": stock_entries_base_url.rstrip("/"),
        "stock_movements_base_url": stock_movements_base_url.rstrip("/"),
        "sales_base_url": sales_base_url.rstrip("/"),
        "resources_base_url": categories_base_url.rstrip("/"),
        "token": token,
    }


def normalizar_perfil_usuario(user_data):
    if not isinstance(user_data, dict):
        return None

    candidatos = [
        user_data.get("profile"),
        user_data.get("perfil"),
        user_data.get("role"),
        user_data.get("tipo_perfil"),
    ]

    for candidato in candidatos:
        if candidato is None:
            continue

        nome = str(candidato).strip().lower()

        if nome in {"adm", "admin", "administrator"}:
            return "Adm"

        if nome in {
            "auxiliar",
            "operacional",
            "aux.ecommerce",
            "aux_ecommerce",
            "aux ecommerce",
            "auxiliar ecommerce",
            "auxiliar_ecommerce",
        }:
            return "aux.ecommerce"

        if nome in {"member", "membro"}:
            return "member"

    return None


def nivel_acesso_perfil(perfil):
    """Converte perfis reconhecidos em níveis operacionais do Xano."""
    perfil_normalizado = normalizar_perfil_usuario({"profile": perfil})
    if perfil_normalizado in {"Adm", "admin"}:
        return 2
    if perfil_normalizado in {"aux.ecommerce", "member"}:
        return 1
    return 0


def pode_administrar(perfil):
    return nivel_acesso_perfil(perfil) >= 2


def extrair_token_login(payload):
    if not isinstance(payload, dict):
        return None

    for chave in ("token", "access_token", "accessToken", "authToken", "jwt"):
        valor = payload.get(chave)
        if isinstance(valor, str) and valor.strip():
            return valor.strip()

    nested = payload.get("data")
    if isinstance(nested, dict):
        for chave in ("token", "access_token", "accessToken", "authToken", "jwt"):
            valor = nested.get(chave)
            if isinstance(valor, str) and valor.strip():
                return valor.strip()

    return None


def extrair_usuario_autenticado(payload):
    if not isinstance(payload, dict):
        return None

    for chave in ("user", "data", "usuario", "userData"):
        candidato = payload.get(chave)
        if isinstance(candidato, dict) and any(
            campo in candidato
            for campo in ("id", "email", "name", "profile", "perfil", "role")
        ):
            return dict(candidato)

    if any(
        campo in payload
        for campo in ("id", "email", "name", "profile", "perfil", "role")
    ):
        return dict(payload)

    return None


def autenticar_usuario_resposta(payload):
    """Valida token e perfil a partir de uma resposta com os dados do usuário."""
    token = extrair_token_login(payload)
    usuario = extrair_usuario_autenticado(payload)

    if not token or usuario is None:
        return {
            "ok": False,
            "token": None,
            "user": None,
            "error": "Credenciais inválidas ou resposta de autenticação incompleta.",
        }

    perfil = normalizar_perfil_usuario(usuario)
    if not perfil:
        return {
            "ok": False,
            "token": None,
            "user": None,
            "error": "Perfil do usuário ausente ou não reconhecido.",
        }

    usuario["profile"] = perfil

    return {
        "ok": True,
        "token": token,
        "user": usuario,
        "error": None,
    }


def xano_request(method, endpoint, token=None, **kwargs):
    """Executa uma requisi??o ? API do Xano."""
    config = get_xano_config()

    endpoint_str = str(endpoint or "")
    lower_endpoint = endpoint_str.lower()

    if lower_endpoint.startswith("/auth/"):
        base_url = config["auth_base_url"]
    elif lower_endpoint.startswith("/category"):
        base_url = config["categories_base_url"]
    elif lower_endpoint.startswith("/product"):
        base_url = config["products_base_url"]
    elif lower_endpoint.startswith("/supplier"):
        base_url = config["suppliers_base_url"]
    elif lower_endpoint.startswith("/stock-entry"):
        base_url = config["stock_entries_base_url"]
    elif lower_endpoint.startswith("/stock-movement"):
        base_url = config["stock_movements_base_url"]
    elif lower_endpoint.startswith("/sale"):
        base_url = config["sales_base_url"]
    else:
        base_url = config["resources_base_url"]

    url = _build_api_url(base_url, endpoint)

    headers = kwargs.pop("headers", {}).copy()
    auth_token = token or config["token"]

    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"

    response = requests.request(
        method=method,
        url=url,
        headers=headers,
        timeout=20,
        **kwargs,
    )

    response.raise_for_status()

    if not response.content:
        return None

    try:
        return response.json()
    except ValueError:
        return response.text


def listar_produtos(token=None, *, name=None, category_id=None, status=None, **kwargs):
    """Pesquisa produtos no Xano conforme o contrato observado.

    O endpoint de produtos usa a condição `db:product.name includes input:name` e
    exige autenticação. Os filtros `category_id` e `status` só devem ser enviados
    quando o cliente tiver confirmação explícita de que o valor foi informado pelo
    usuário ou pelo contexto da tela; não assumimos que omití-los implica listagem
    global.
    """
    params = {}

    if name is not None and str(name).strip() != "":
        params["name"] = str(name).strip()

    if category_id is not None:
        params["category_id"] = category_id

    if status is not None:
        params["status"] = status

    for chave, valor in kwargs.items():
        if valor is not None:
            params[chave] = valor

    return xano_request("GET", "/product", token=token, params=params)


def extrair_categorias(payload):
    """Extrai categorias ativas em um formato consistente para a interface."""
    if isinstance(payload, list):
        itens = payload
    elif isinstance(payload, dict):
        lista = None
        for chave in ("categories", "data", "items", "results", "rows"):
            valor = payload.get(chave)
            if isinstance(valor, list):
                lista = valor
                break
        itens = lista or []
    else:
        return []

    categorias = []
    for item in itens:
        if not isinstance(item, dict):
            continue

        categoria_id = item.get("id")
        nome = item.get("name")
        status = item.get("status")

        if categoria_id is None or nome is None:
            continue

        nome = str(nome).strip()
        if not nome:
            continue

        if isinstance(status, str) and status.strip().lower() != "ativo":
            continue

        try:
            categoria_id = int(categoria_id)
        except (TypeError, ValueError):
            continue

        categorias.append({
            "id": categoria_id,
            "name": nome,
            "status": status,
        })

    return categorias


def listar_categorias_ativas(token=None):
    """Busca apenas as categorias ativas confirmadas pelo contrato do Xano."""
    payload = xano_request(
        "GET",
        "/category",
        token=token,
        params={"status": "ativo"},
    )

    categorias = extrair_categorias(payload)
    if not categorias:
        raise ValueError("Nenhuma categoria ativa disponível para seleção.")

    return categorias


def resolver_categoria_por_nome(categorias, nome_categoria):
    """Resolve o ID da categoria a partir do nome selecionado na interface."""
    if not isinstance(categorias, list):
        raise ValueError("Lista de categorias inválida.")

    nome = str(nome_categoria or "").strip()
    if not nome:
        raise ValueError("Selecione uma categoria válida.")

    for categoria in categorias:
        if not isinstance(categoria, dict):
            continue
        if str(categoria.get("name", "")).strip() == nome:
            categoria_id = categoria.get("id")
            try:
                return int(categoria_id)
            except (TypeError, ValueError):
                raise ValueError(f"Categoria inválida: {nome}.")

    raise ValueError(f"Categoria não encontrada: {nome}.")


def extrair_id_produto(payload):
    """Extrai um identificador de produto quando a resposta do Xano o incluir."""
    if payload is None:
        return None

    if isinstance(payload, list):
        for item in payload:
            id_produto = extrair_id_produto(item)
            if id_produto is not None:
                return id_produto
        return None

    if not isinstance(payload, dict):
        return None

    for chave in ("id", "product_id", "produto_id"):
        valor = payload.get(chave)
        if isinstance(valor, bool):
            continue
        if isinstance(valor, (int, float)) and math.isfinite(valor):
            return int(valor)
        if isinstance(valor, str):
            valor = valor.strip()
            if valor and valor.lstrip("-").isdigit():
                return int(valor)

    for chave in ("data", "product", "produto", "result", "item"):
        id_produto = extrair_id_produto(payload.get(chave))
        if id_produto is not None:
            return id_produto

    return None


def confirmar_produto_criado(payload):
    """Valida se a resposta do Xano confirma a criação do produto."""
    if payload is None:
        return False

    if isinstance(payload, (str, bytes)):
        return False

    if isinstance(payload, list):
        return any(confirmar_produto_criado(item) for item in payload)

    if not isinstance(payload, dict):
        return False

    id_produto = extrair_id_produto(payload)
    if id_produto is not None:
        return True

    status = payload.get("status")
    if isinstance(status, str):
        status_normalizado = status.strip().lower()
        if status_normalizado in {
            "success",
            "ok",
            "created",
            "created_successfully",
        }:
            return any(
                chave in payload
                for chave in ("data", "product", "produto", "result")
            )

    return False


def erro_xano_indica_duplicidade(erro):
    resposta = getattr(erro, "response", None)
    if resposta is None:
        return False
    try:
        detalhe = resposta.json()
    except ValueError:
        detalhe = getattr(resposta, "text", "")
    return "duplicate record detected" in str(detalhe).casefold()


def mapear_payload_produto(
    *,
    name,
    description="",
    category_id,
    min_stock,
    sale_price,
    status=None,
    sku="",
):
    """Valida e mapeia os campos de criação conforme o contrato do Xano."""
    name = str(name or "").strip()
    if status is not None:
        status = str(status).strip()

    if not name:
        raise ValueError("Informe o nome do produto.")
    if isinstance(category_id, bool) or not isinstance(category_id, int):
        raise ValueError("A categoria deve ser informada por um ID inteiro.")
    if category_id < 1:
        raise ValueError("Selecione um ID de categoria válido.")
    if isinstance(min_stock, bool) or not isinstance(min_stock, int):
        raise ValueError("O estoque mínimo deve ser um número inteiro.")
    if min_stock < 0:
        raise ValueError("O estoque mínimo não pode ser negativo.")
    if (
        isinstance(sale_price, bool)
        or not isinstance(sale_price, (int, float))
        or not math.isfinite(sale_price)
    ):
        raise ValueError("O preço de venda deve ser numérico.")
    if sale_price < 0:
        raise ValueError("O preço de venda não pode ser negativo.")

    payload = {
        "name": name,
        "category_id": category_id,
        "min_stock": min_stock,
        "sale_price": float(sale_price),
    }

    sku = str(sku or "").strip()
    if sku:
        payload["sku"] = sku

    return payload


def criar_produto(
    token,
    *,
    name,
    description="",
    category_id,
    min_stock,
    sale_price,
    status=None,
    sku="",
):
    """Envia o cadastro de produto ao endpoint existente do Xano."""
    if not token:
        raise ValueError("A sessão expirou. Entre novamente para cadastrar.")

    payload = mapear_payload_produto(
        name=name,
        description=description,
        category_id=category_id,
        min_stock=min_stock,
        sale_price=sale_price,
        status=status,
        sku=sku,
    )

    resposta = xano_request(
        "POST",
        "/product",
        token=token,
        json=payload,
    )

    if not confirmar_produto_criado(resposta):
        raise ValueError("O Xano não confirmou a criação do produto.")

    return resposta


def xano_login(email, password):
    """Faz login e busca os dados do usuário autenticado."""
    resposta_login = xano_request(
        "POST",
        "/auth/login",
        json={
            "email": email,
            "password": password,
        },
    )

    token = extrair_token_login(resposta_login)

    if not token:
        raise ValueError("O Xano não retornou um token de autenticação.")

    usuario = xano_request("GET", "/auth/me", token=token)

    if not isinstance(usuario, dict):
        raise ValueError("O Xano não retornou os dados do usuário.")

    return {
        "authToken": token,
        "user": usuario,
    }


def _extrair_lista(payload, keys):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in keys:
            value = payload.get(key)
            if isinstance(value, list):
                return value
    return []


def _extrair_registro(payload, id_fields=("id",)):
    if not isinstance(payload, dict):
        return None
    for key in ("data", "item", "result", "category", "product", "supplier"):
        nested = payload.get(key)
        if isinstance(nested, dict):
            payload = nested
            break
    if not any(payload.get(field) is not None for field in id_fields):
        return None
    return payload


def _confirmar_registro(payload):
    return _extrair_registro(payload) is not None


def listar_categorias(token=None, *, status=None, **kwargs):
    params = {}
    if status is not None:
        params["status"] = status
    params.update({key: value for key, value in kwargs.items() if value is not None})
    payload = xano_request("GET", "/category", token=token, params=params)
    return _extrair_lista(payload, ("categories", "data", "items", "results", "rows"))


def consultar_categoria(category_id, token=None):
    if isinstance(category_id, bool) or not str(category_id).isdigit():
        raise ValueError("ID de categoria inválido.")
    payload = xano_request("GET", f"/category/{int(category_id)}", token=token)
    registro = _extrair_registro(payload)
    if registro is None:
        raise ValueError("O Xano não confirmou a consulta da categoria.")
    return registro


def criar_categoria(token=None, *, name, description=""):
    name = str(name or "").strip()
    if not name:
        raise ValueError("Informe o nome da categoria.")
    payload = {"name": name}
    if str(description or "").strip():
        payload["description"] = str(description).strip()
    resposta = xano_request("POST", "/category", token=token, json=payload)
    if not _confirmar_registro(resposta):
        raise ValueError("O Xano não confirmou a criação da categoria.")
    return resposta


def editar_categoria(category_id, token=None, **fields):
    if isinstance(category_id, bool) or not str(category_id).isdigit():
        raise ValueError("ID de categoria inválido.")
    payload = {
        key: value
        for key, value in fields.items()
        if key in {"name", "description", "status"} and value is not None
    }
    resposta = xano_request(
        "PATCH",
        f"/category/{int(category_id)}",
        token=token,
        json=payload,
    )
    if not _confirmar_registro(resposta):
        raise ValueError("O Xano não confirmou a edição da categoria.")
    return resposta


def inativar_categoria(category_id, token=None):
    if isinstance(category_id, bool) or not str(category_id).isdigit():
        raise ValueError("ID de categoria inválido.")
    resposta = xano_request(
        "PATCH",
        f"/category/{int(category_id)}/deactivate",
        token=token,
    )
    if not _confirmar_registro(resposta):
        raise ValueError("O Xano não confirmou a inativação da categoria.")
    return resposta


def listar_fornecedores(token=None, *, status=None, **kwargs):
    if not isinstance(status, str) or status not in {"ativo", "inativo", "todos"}:
        raise ValueError("Informe uma situação válida para consultar fornecedores.")

    statuses = ("ativo", "inativo") if status == "todos" else (status,)
    fornecedores = []
    ids_encontrados = set()
    for situacao in statuses:
        params = {"status": situacao}
        params.update({key: value for key, value in kwargs.items() if value is not None})
        payload = xano_request("GET", "/supplier", token=token, params=params)
        if payload is None:
            continue
        if not isinstance(payload, (dict, list)):
            raise ValueError("O Xano retornou uma resposta inválida para fornecedores.")
        resultado = _extrair_lista(
            payload,
            ("suppliers", "data", "items", "results", "rows"),
        )
        if isinstance(payload, dict) and not any(
            isinstance(payload.get(key), list)
            for key in ("suppliers", "data", "items", "results", "rows")
        ):
            raise ValueError("O Xano não retornou a lista de fornecedores.")

        for fornecedor in resultado:
            if not isinstance(fornecedor, dict):
                fornecedores.append(fornecedor)
                continue
            fornecedor_id = fornecedor.get("id") or fornecedor.get("supplier_id")
            if fornecedor_id is not None:
                if fornecedor_id in ids_encontrados:
                    continue
                ids_encontrados.add(fornecedor_id)
            fornecedores.append(fornecedor)

    return fornecedores


def consultar_fornecedor(supplier_id, token=None):
    if isinstance(supplier_id, bool) or not str(supplier_id).isdigit():
        raise ValueError("ID de fornecedor inválido.")
    payload = xano_request("GET", f"/supplier/{int(supplier_id)}", token=token)
    registro = _extrair_registro(payload)
    if registro is None:
        raise ValueError("O Xano não confirmou a consulta do fornecedor.")
    return registro


def criar_fornecedor(token=None, *, name, contact_name="", cnpj="", email="", phone=""):
    name = str(name or "").strip()
    if not name:
        raise ValueError("Informe o nome do fornecedor.")
    payload = {"name": name}
    for key, value in (
        ("contact_name", contact_name),
        ("cnpj", cnpj),
        ("email", email),
        ("phone", phone),
    ):
        text = str(value or "").strip()
        if text:
            payload[key] = text
    resposta = xano_request("POST", "/supplier", token=token, json=payload)
    if not _confirmar_registro(resposta):
        raise ValueError("O Xano não confirmou a criação do fornecedor.")
    return resposta


def editar_fornecedor(supplier_id, token=None, **fields):
    if isinstance(supplier_id, bool) or not str(supplier_id).isdigit():
        raise ValueError("ID de fornecedor inválido.")
    allowed = {"name", "contact_name", "cnpj", "email", "phone", "status"}
    payload = {
        key: value
        for key, value in fields.items()
        if key in allowed and value is not None
    }
    resposta = xano_request(
        "PATCH",
        f"/supplier/{int(supplier_id)}",
        token=token,
        json=payload,
    )
    if not _confirmar_registro(resposta):
        raise ValueError("O Xano não confirmou a edição do fornecedor.")
    return resposta


def inativar_fornecedor(supplier_id, token=None):
    if isinstance(supplier_id, bool) or not str(supplier_id).isdigit():
        raise ValueError("ID de fornecedor inválido.")
    resposta = xano_request(
        "PATCH",
        f"/supplier/{int(supplier_id)}/deactivate",
        token=token,
    )
    if not _confirmar_registro(resposta):
        raise ValueError("O Xano não confirmou a inativação do fornecedor.")
    return resposta


def consultar_produto(product_id, token=None):
    if isinstance(product_id, bool) or not str(product_id).isdigit():
        raise ValueError("ID de produto inválido.")
    payload = xano_request("GET", f"/product/{int(product_id)}", token=token)
    registro = _extrair_registro(payload)
    if registro is None:
        raise ValueError("O Xano não confirmou a consulta do produto.")
    return registro


def editar_produto(product_id, token=None, **fields):
    if isinstance(product_id, bool) or not str(product_id).isdigit():
        raise ValueError("ID de produto inválido.")
    allowed = {"name", "sku", "category_id", "sale_price", "min_stock", "status"}
    payload = {
        key: value
        for key, value in fields.items()
        if key in allowed and value is not None
    }
    payload.pop("stock_quantity", None)
    payload.pop("average_cost", None)
    if not payload:
        raise ValueError("Informe pelo menos um campo válido para editar.")
    resposta = xano_request(
        "PATCH",
        f"/product/{int(product_id)}",
        token=token,
        json=payload,
    )
    if not _confirmar_registro(resposta):
        raise ValueError("O Xano não confirmou a edição do produto.")
    return resposta


def inativar_produto(product_id, token=None):
    if isinstance(product_id, bool) or not str(product_id).isdigit():
        raise ValueError("ID de produto inválido.")
    resposta = xano_request(
        "PATCH",
        f"/product/{int(product_id)}/deactivate",
        token=token,
    )
    if not _confirmar_registro(resposta):
        raise ValueError("O Xano não confirmou a inativação do produto.")
    return resposta


def _validar_id_inteiro(valor, nome):
    if isinstance(valor, bool):
        raise ValueError(f"{nome} deve ser um inteiro válido.")
    try:
        inteiro = int(valor)
    except (TypeError, ValueError):
        raise ValueError(f"{nome} deve ser um inteiro válido.") from None
    if inteiro < 1:
        raise ValueError(f"{nome} deve ser maior que zero.")
    return inteiro


def _validar_quantidade(valor):
    if isinstance(valor, bool):
        raise ValueError("A quantidade deve ser um inteiro maior ou igual a 1.")
    try:
        inteiro = int(valor)
    except (TypeError, ValueError):
        raise ValueError("A quantidade deve ser um inteiro maior ou igual a 1.") from None
    if inteiro < 1:
        raise ValueError("A quantidade deve ser um inteiro maior ou igual a 1.")
    return inteiro


def _validar_decimal(valor, nome, permitir_zero=True):
    if isinstance(valor, bool):
        raise ValueError(f"{nome} deve ser numérico.")
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        raise ValueError(f"{nome} deve ser numérico.") from None
    if not math.isfinite(numero):
        raise ValueError(f"{nome} deve ser um número finito.")
    if numero < 0:
        raise ValueError(f"{nome} não pode ser negativo.")
    if not permitir_zero and numero == 0:
        raise ValueError(f"{nome} deve ser maior que zero.")
    return numero


def registrar_entrada_estoque(
    token,
    *,
    product_id,
    supplier_id,
    quantity,
    unit_purchase_cost,
    entry_date,
    inbound_freight=0,
    other_acquisition_costs=0,
    invoice_number="",
    notes="",
):
    if not token:
        raise ValueError("A sessão expirou. Entre novamente para continuar.")

    product_id = _validar_id_inteiro(product_id, "O produto")
    supplier_id = _validar_id_inteiro(supplier_id, "O fornecedor")
    quantity = _validar_quantidade(quantity)
    unit_purchase_cost = _validar_decimal(
        unit_purchase_cost,
        "O custo unitário de compra",
        permitir_zero=False,
    )
    inbound_freight = _validar_decimal(inbound_freight, "O frete de entrada")
    other_acquisition_costs = _validar_decimal(
        other_acquisition_costs,
        "Os outros custos de aquisição",
    )

    entry_date = str(entry_date or "").strip()
    if not entry_date:
        raise ValueError("Informe a data da entrada.")
    try:
        datetime.strptime(entry_date, "%Y-%m-%d")
    except ValueError:
        raise ValueError("A data da entrada deve usar o formato YYYY-MM-DD.") from None

    payload = {
        "product_id": product_id,
        "supplier_id": supplier_id,
        "quantity": quantity,
        "unit_purchase_cost": unit_purchase_cost,
        "entry_date": entry_date,
        "inbound_freight": inbound_freight,
        "other_acquisition_costs": other_acquisition_costs,
    }
    invoice_number = str(invoice_number or "").strip()
    notes = str(notes or "").strip()
    if invoice_number:
        payload["invoice_number"] = invoice_number
    if notes:
        payload["notes"] = notes

    resposta = xano_request(
        "POST",
        "/stock-entry",
        token=token,
        json=payload,
    )
    if not isinstance(resposta, dict):
        raise ValueError("O Xano não confirmou a entrada de estoque.")

    entry = resposta.get("entry")
    movement = resposta.get("movement")
    if not isinstance(entry, dict) or not isinstance(movement, dict):
        raise ValueError("O Xano não retornou a entrada e movimentação confirmadas.")
    if resposta.get("stock_quantity") is None or resposta.get("average_cost") is None:
        raise ValueError("O Xano não retornou o saldo ou custo médio atualizados.")
    return resposta


def listar_entradas_estoque(
    token=None,
    *,
    product_id=None,
    supplier_id=None,
    start_date=None,
    end_date=None,
    page=1,
    per_page=20,
):
    params = {}
    if product_id is not None:
        params["product_id"] = _validar_id_inteiro(product_id, "O produto")
    if supplier_id is not None:
        params["supplier_id"] = _validar_id_inteiro(supplier_id, "O fornecedor")
    if start_date:
        params["start_date"] = str(start_date).strip()
    if end_date:
        params["end_date"] = str(end_date).strip()
    params["page"] = max(1, int(page))
    params["per_page"] = min(100, max(1, int(per_page)))
    payload = xano_request("GET", "/stock-entry", token=token, params=params)
    if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
        raise ValueError("O Xano retornou uma resposta paginada inválida para entradas.")
    return payload


def consultar_entrada_estoque(entry_id, token=None):
    entry_id = _validar_id_inteiro(entry_id, "O ID da entrada")
    payload = xano_request("GET", f"/stock-entry/{entry_id}", token=token)
    if not isinstance(payload, dict) or not payload:
        raise ValueError("O Xano não confirmou a consulta da entrada.")
    return payload


def listar_movimentacoes(
    token=None,
    *,
    product_id=None,
    movement_type=None,
    start_date=None,
    end_date=None,
    page=1,
    per_page=20,
):
    params = {}
    if product_id is not None:
        params["product_id"] = _validar_id_inteiro(product_id, "O produto")
    if movement_type:
        params["movement_type"] = str(movement_type).strip()
    if start_date:
        params["start_date"] = str(start_date).strip()
    if end_date:
        params["end_date"] = str(end_date).strip()
    params["page"] = max(1, int(page))
    params["per_page"] = min(100, max(1, int(per_page)))
    payload = xano_request("GET", "/stock-movement", token=token, params=params)
    if not isinstance(payload, dict):
        raise ValueError("O Xano retornou uma resposta inválida para movimentações.")
    movimentos = payload.get("movements")
    if movimentos is None:
        movimentos = payload.get("items")
    if not isinstance(movimentos, list):
        raise ValueError("O Xano não retornou a lista paginada de movimentações.")
    return payload


def consultar_movimentacao(movement_id, token=None):
    movement_id = _validar_id_inteiro(movement_id, "O ID da movimentação")
    payload = xano_request("GET", f"/stock-movement/{movement_id}", token=token)
    if not isinstance(payload, dict) or not payload:
        raise ValueError("O Xano não confirmou a consulta da movimentação.")
    return payload


def ajustar_estoque(
    token,
    *,
    product_id,
    adjustment_type,
    quantity,
    notes="",
):
    if not token:
        raise ValueError("A sessão expirou. Entre novamente para continuar.")
    product_id = _validar_id_inteiro(product_id, "O produto")
    quantity = _validar_quantidade(quantity)
    adjustment_type = str(adjustment_type or "").strip().lower()
    if adjustment_type not in {"entrada", "saida"}:
        raise ValueError("O tipo de ajuste deve ser entrada ou saída.")
    payload = {
        "product_id": product_id,
        "adjustment_type": adjustment_type,
        "quantity": quantity,
    }
    notes = str(notes or "").strip()
    if notes:
        payload["notes"] = notes
    resposta = xano_request(
        "POST",
        "/stock-movement/adjustment",
        token=token,
        json=payload,
    )
    if not isinstance(resposta, dict) or not resposta:
        raise ValueError("O Xano não confirmou o ajuste de estoque.")
    return resposta


def registrar_perda_ou_avaria(
    token,
    *,
    product_id,
    movement_type,
    quantity,
    notes="",
):
    if not token:
        raise ValueError("A sessão expirou. Entre novamente para continuar.")
    product_id = _validar_id_inteiro(product_id, "O produto")
    quantity = _validar_quantidade(quantity)
    movement_type = str(movement_type or "").strip().lower()
    if movement_type not in {"perda", "avaria"}:
        raise ValueError("O tipo deve ser perda ou avaria.")
    payload = {
        "product_id": product_id,
        "movement_type": movement_type,
        "quantity": quantity,
    }
    notes = str(notes or "").strip()
    if notes:
        payload["notes"] = notes
    resposta = xano_request(
        "POST",
        "/stock-movement/loss",
        token=token,
        json=payload,
    )
    if not isinstance(resposta, dict) or not resposta:
        raise ValueError("O Xano não confirmou o registro de perda ou avaria.")
    return resposta


def registrar_devolucao(
    token,
    *,
    product_id,
    return_type,
    reference_id,
    quantity,
    restock_condition=True,
    notes="",
):
    if not token:
        raise ValueError("A sessão expirou. Entre novamente para continuar.")
    product_id = _validar_id_inteiro(product_id, "O produto")
    reference_id = _validar_id_inteiro(reference_id, "A referência original")
    quantity = _validar_quantidade(quantity)
    return_type = str(return_type or "").strip().lower()
    if return_type not in {"cliente", "fornecedor"}:
        raise ValueError("O tipo de devolução deve ser cliente ou fornecedor.")
    payload = {
        "product_id": product_id,
        "return_type": return_type,
        "reference_id": reference_id,
        "quantity": quantity,
    }
    if return_type == "cliente":
        payload["restock_condition"] = bool(restock_condition)
    notes = str(notes or "").strip()
    if notes:
        payload["notes"] = notes
    resposta = xano_request(
        "POST",
        "/stock-movement/return",
        token=token,
        json=payload,
    )
    if not isinstance(resposta, dict) or not resposta:
        raise ValueError("O Xano não confirmou a devolução.")
    return resposta


ALLOWED_SALE_COST_TYPES = {
    "embalagem",
    "comissao_marketplace",
    "impostos",
    "frete_saida",
    "outros",
}


def criar_chave_idempotencia_venda():
    return str(uuid.uuid4())


def validar_payload_venda(
    *,
    idempotency_key,
    sales_channel,
    items,
    order_number=None,
    sale_date=None,
    notes=None,
    costs=None,
):
    idempotency_key = str(idempotency_key or "").strip()
    try:
        parsed_key = uuid.UUID(idempotency_key)
    except (TypeError, ValueError, AttributeError):
        raise ValueError("A chave de idempotência deve ser um UUID válido.") from None
    if parsed_key.version != 4:
        raise ValueError("A chave de idempotência deve ser UUID versão 4.")

    sales_channel = str(sales_channel or "").strip()
    if not sales_channel:
        raise ValueError("Informe o canal de venda.")
    if not isinstance(items, list) or not items:
        raise ValueError("Informe pelo menos um item na venda.")

    payload_items = []
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("Cada item da venda deve ser um objeto válido.")
        product_id = _validar_id_inteiro(
            item.get("product_id"),
            "O produto",
        )
        quantity = _validar_quantidade(item.get("quantity"))
        unit_sale_price = _validar_decimal(
            item.get("unit_sale_price"),
            "O preço unitário",
        )
        payload_item = {
            "product_id": product_id,
            "quantity": quantity,
            "unit_sale_price": unit_sale_price,
        }
        if item.get("discount_amount") is not None:
            payload_item["discount_amount"] = _validar_decimal(
                item.get("discount_amount"),
                "O desconto",
            )
        payload_items.append(payload_item)

    payload = {
        "idempotency_key": str(parsed_key),
        "sales_channel": sales_channel,
        "items": payload_items,
    }

    order_number = str(order_number or "").strip()
    sale_date = str(sale_date or "").strip()
    notes = str(notes or "").strip()
    if order_number:
        payload["order_number"] = order_number
    if sale_date:
        try:
            datetime.strptime(sale_date, "%Y-%m-%d")
        except ValueError:
            raise ValueError("A data da venda deve usar o formato YYYY-MM-DD.") from None
        payload["sale_date"] = sale_date
    if notes:
        payload["notes"] = notes

    payload_costs = []
    for cost in costs or []:
        if not isinstance(cost, dict):
            raise ValueError("Cada custo adicional deve ser um objeto válido.")
        cost_type = str(cost.get("type") or "").strip()
        if cost_type not in ALLOWED_SALE_COST_TYPES:
            raise ValueError(
                "Tipo de custo inválido. Use embalagem, comissao_marketplace, "
                "impostos, frete_saida ou outros."
            )
        payload_costs.append({
            "type": cost_type,
            "amount": _validar_decimal(cost.get("amount"), "O custo adicional"),
        })
    if payload_costs:
        payload["costs"] = payload_costs
    return payload


def registrar_venda(token=None, payload=None, idempotency_key=None, **fields):
    if not token:
        raise ValueError("A sessão expirou. Entre novamente para registrar.")

    if payload is None:
        payload = validar_payload_venda(
            idempotency_key=idempotency_key or criar_chave_idempotencia_venda(),
            sales_channel=fields.get("sales_channel"),
            items=fields.get("items"),
            order_number=fields.get("order_number"),
            sale_date=fields.get("sale_date"),
            notes=fields.get("notes"),
            costs=fields.get("costs"),
        )
    else:
        if not isinstance(payload, dict):
            raise ValueError("O payload da venda deve ser um objeto válido.")
        payload = validar_payload_venda(
            idempotency_key=payload.get("idempotency_key"),
            sales_channel=payload.get("sales_channel"),
            items=payload.get("items"),
            order_number=payload.get("order_number"),
            sale_date=payload.get("sale_date"),
            notes=payload.get("notes"),
            costs=payload.get("costs"),
        )

    resposta = xano_request(
        "POST",
        "/sale",
        token=token,
        json=payload,
    )
    if not isinstance(resposta, dict) or not resposta:
        raise ValueError("O Xano não confirmou o registro da venda.")

    venda = resposta.get("sale")
    if venda is not None:
        if not isinstance(venda, dict) or not venda:
            raise ValueError("O Xano retornou dados incompatíveis para a venda.")
    elif not any(
        chave in resposta
        for chave in ("id", "sale_id", "order_number", "status")
    ):
        raise ValueError("O Xano não retornou uma confirmação compatível da venda.")
    return resposta


def listar_vendas(
    token=None,
    *,
    sales_channel=None,
    order_number=None,
    status=None,
    start_date=None,
    end_date=None,
    page=1,
    per_page=20,
):
    sales_channel = str(sales_channel or "").strip()
    if not sales_channel:
        raise ValueError(
            "O endpoint GET /sale exige sales_channel. "
            "A consulta sem canal depende de suporte do backend."
        )

    params = {}
    params["sales_channel"] = sales_channel
    if order_number:
        params["order_number"] = str(order_number).strip()
    if status:
        params["status"] = str(status).strip()
    if start_date:
        params["start_date"] = str(start_date).strip()
    if end_date:
        params["end_date"] = str(end_date).strip()
    params["page"] = max(1, int(page))
    params["per_page"] = min(100, max(1, int(per_page)))

    payload = xano_request("GET", "/sale", token=token, params=params)
    if isinstance(payload, list):
        return {"items": payload}
    if not isinstance(payload, dict):
        raise ValueError("O Xano retornou uma resposta inválida para vendas.")

    if isinstance(payload.get("items"), list):
        return payload
    if isinstance(payload.get("sales"), list):
        return payload
    raise ValueError(
        "O Xano não retornou uma estrutura paginada compatível para vendas."
    )


def consultar_venda(sale_id, token=None):
    sale_id = _validar_id_inteiro(sale_id, "O ID da venda")
    payload = xano_request("GET", f"/sale/{sale_id}", token=token)
    if not isinstance(payload, dict) or not payload:
        raise ValueError("O Xano não confirmou a consulta da venda.")
    return payload


def consultar_metricas_vendas(
    token=None,
    *,
    sales_channel=None,
    status=None,
    start_date=None,
    end_date=None,
    product_id=None,
    category_id=None,
):
    """Consulta os indicadores agregados de vendas retornados pelo Xano."""
    params = {}
    for nome, valor in (
        ("sales_channel", sales_channel),
        ("status", status),
        ("start_date", start_date),
        ("end_date", end_date),
    ):
        if valor is not None and str(valor).strip():
            params[nome] = str(valor).strip()

    if product_id is not None:
        params["product_id"] = _validar_id_inteiro(product_id, "O produto")
    if category_id is not None:
        params["category_id"] = _validar_id_inteiro(category_id, "A categoria")

    payload = xano_request("GET", "/sale/metrics", token=token, params=params)
    if not isinstance(payload, dict):
        raise ValueError("O Xano retornou uma resposta inválida para métricas de vendas.")

    campos_contagem = ("sales_count", "items_count")
    campos_decimais = (
        "gross_amount",
        "discount_amount",
        "net_revenue",
        "total_cmv",
        "total_costs",
        "result",
        "profit_margin_percent",
        "average_ticket",
    )
    metricas = {}

    for campo in campos_contagem + campos_decimais:
        if campo not in payload:
            raise ValueError(
                f"O Xano não retornou o indicador obrigatório '{campo}'."
            )

        valor = payload[campo]
        if valor is None:
            metricas[campo] = None
            continue
        if isinstance(valor, bool) or not isinstance(valor, (int, float)):
            raise ValueError(
                f"O indicador '{campo}' retornado pelo Xano não é numérico."
            )

        try:
            numero = Decimal(str(valor))
        except (InvalidOperation, ValueError):
            raise ValueError(
                f"O indicador '{campo}' retornado pelo Xano não é numérico."
            ) from None
        if not numero.is_finite():
            raise ValueError(
                f"O indicador '{campo}' retornado pelo Xano não é finito."
            )

        if campo in campos_contagem:
            if numero != numero.to_integral_value():
                raise ValueError(
                    f"O indicador '{campo}' retornado pelo Xano deve ser inteiro."
                )
            metricas[campo] = int(numero)
        else:
            metricas[campo] = numero

    for campo in ("period", "filters"):
        if campo in payload:
            metricas[campo] = payload[campo]

    return metricas
