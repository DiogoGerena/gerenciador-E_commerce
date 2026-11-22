import math
import os
import re
import uuid
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlparse

import requests
import streamlit as st
from dotenv import load_dotenv

try:
    from app.sale_dates import sale_date_to_unix_milliseconds
except ModuleNotFoundError:  # pragma: no cover - compatibilidade com execução direta
    from sale_dates import sale_date_to_unix_milliseconds


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOTENV_PATH = PROJECT_ROOT / ".env"


def _load_project_environment():
    """Carrega o .env da raiz sem sobrescrever o ambiente do processo."""
    load_dotenv(dotenv_path=DOTENV_PATH, override=False)


_load_project_environment()


STOCK_ENTRY_URL = (
    "https://x8ki-letl-twmt.n7.xano.io/api:stock-entries/stock-entry"
)
SUPPLIERS_BASE_URL = "https://x8ki-letl-twmt.n7.xano.io/api:-ryuPWna"
SUPPLIERS_URL = f"{SUPPLIERS_BASE_URL}/supplier"
SALES_GROUP_ID = "EjdVpi9b"


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
        or SUPPLIERS_BASE_URL
    )
    stock_entries_base_url = (
        os.getenv("XANO_STOCK_ENTRIES_URL")
        or _get_streamlit_secret("XANO_STOCK_ENTRIES_URL")
        or STOCK_ENTRY_URL
    )
    stock_movements_base_url = (
        os.getenv("XANO_STOCK_MOVEMENTS_URL")
        or _get_streamlit_secret("XANO_STOCK_MOVEMENTS_URL")
    )
    sales_base_url = (
        os.getenv("XANO_SALES_URL")
        or _get_streamlit_secret("XANO_SALES_URL")
    )
    if not sales_base_url and base_url:
        parsed_base_url = urlparse(base_url)
        if parsed_base_url.scheme and parsed_base_url.netloc:
            sales_base_url = (
                f"{parsed_base_url.scheme}://{parsed_base_url.netloc}"
                f"/api:{SALES_GROUP_ID}"
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
        "stock_entries_base_url": (
            stock_entries_base_url.rstrip("/") if stock_entries_base_url else None
        ),
        "stock_movements_base_url": (
            stock_movements_base_url.rstrip("/")
            if stock_movements_base_url
            else None
        ),
        "sales_base_url": sales_base_url.rstrip("/") if sales_base_url else None,
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


def _xano_http_request(method, endpoint, token=None, **kwargs):
    config = get_xano_config()

    endpoint_str = str(endpoint or "")
    lower_endpoint = endpoint_str.lower()

    if lower_endpoint.startswith("/auth/"):
        base_url = config["auth_base_url"]
    elif lower_endpoint == "/user" or lower_endpoint.startswith("/user/"):
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
        if not base_url:
            raise ValueError(
                "XANO_STOCK_MOVEMENTS_URL não está configurada para o grupo "
                "de movimentações."
            )
    elif lower_endpoint == "/sale" or lower_endpoint.startswith("/sale/"):
        base_url = config["sales_base_url"]
    else:
        base_url = config["resources_base_url"]

    if endpoint_str == STOCK_ENTRY_URL:
        stock_entries_base_url = config["stock_entries_base_url"]
        if stock_entries_base_url:
            if stock_entries_base_url.lower().endswith("/stock-entry"):
                url = stock_entries_base_url
            else:
                url = _build_api_url(
                    stock_entries_base_url,
                    "/stock-entry",
                )
        else:
            url = endpoint_str
    elif endpoint_str == SUPPLIERS_URL:
        supplier_override = (
            os.getenv("XANO_SUPPLIERS_URL")
            or _get_streamlit_secret("XANO_SUPPLIERS_URL")
        )
        url = (
            _build_api_url(supplier_override, "/supplier")
            if supplier_override
            else SUPPLIERS_URL
        )
    else:
        url = _build_api_url(base_url, endpoint)
    headers = kwargs.pop("headers", {}).copy()
    auth_token = (
        token.strip()
        if isinstance(token, str) and token.strip()
        else config["token"]
    )
    if isinstance(auth_token, str):
        auth_token = auth_token.strip()
        if auth_token.lower().startswith("bearer "):
            auth_token = auth_token[7:].strip()

    is_login_request = (
        str(method).upper() == "POST"
        and lower_endpoint.rstrip("/") == "/auth/login"
    )
    if auth_token:
        headers["Authorization"] = "Bearer " + str(auth_token)
    elif is_login_request:
        headers.pop("Authorization", None)
    else:
        raise ValueError(
            "Token Xano ausente. Faça login para obter uma sessão válida "
            "antes de acessar este endpoint."
        )

    response = requests.request(
        method=method,
        url=url,
        headers=headers,
        timeout=20,
        **kwargs,
    )
    response.raise_for_status()
    return response


def _decode_xano_response(response):
    if not response.content:
        return None

    try:
        return response.json()
    except ValueError:
        return response.text


def _xano_response_error_message(response, payload):
    if isinstance(payload, dict):
        for key in ("message", "error", "description", "detail"):
            message = payload.get(key)
            if isinstance(message, str) and message.strip():
                return message.strip()[:500]

    content_type = getattr(response, "headers", {}).get("Content-Type", "")
    if content_type.lower().startswith("text/plain"):
        message = getattr(response, "text", "")
        return message.strip()[:500] if isinstance(message, str) else None
    return None


def xano_request(method, endpoint, token=None, **kwargs):
    """Execute a request to the Xano API and decode its response."""
    response = _xano_http_request(method, endpoint, token=token, **kwargs)
    return _decode_xano_response(response)


USER_ROLES = ("Adm", "aux.ecommerce")
_USER_EMAIL_PATTERN = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")


class RespostaUsuarioInconclusivaError(ValueError):
    """Indica que a resposta não confirmou os dados do usuário."""


class OperacaoUsuarioInconclusivaError(RuntimeError):
    """Indica que a criação pode ter sido processada sem confirmação."""


def validar_dados_usuario(*, name, email, password, role):
    if not isinstance(name, str) or not name.strip():
        raise ValueError("name é obrigatório.")
    if not isinstance(email, str) or not email.strip():
        raise ValueError("email é obrigatório.")
    email = email.strip()
    if not _USER_EMAIL_PATTERN.fullmatch(email):
        raise ValueError("Informe um e-mail válido.")
    if not isinstance(password, str) or len(password) < 8:
        raise ValueError("password deve ter ao menos 8 caracteres.")
    if not any(character.isalpha() for character in password) or not any(
        character.isdigit() for character in password
    ):
        raise ValueError(
            "password deve conter ao menos uma letra e um número."
        )
    if role not in USER_ROLES:
        raise ValueError("role deve ser 'Adm' ou 'aux.ecommerce'.")
    return {
        "name": name.strip(),
        "email": email,
        "password": password,
        "role": role,
    }


def _exigir_token_usuario(token, operation):
    if not isinstance(token, str) or not token.strip():
        raise ValueError(
            f"A sessão expirou. Entre novamente para {operation} usuários."
        )


def _normalizar_usuario_publico(record):
    required_fields = {"id", "name", "email", "role", "created_at"}
    if not isinstance(record, dict) or not required_fields.issubset(record):
        raise RespostaUsuarioInconclusivaError(
            "A resposta do Xano não contém todos os campos do usuário."
        )

    try:
        user_id = _validar_id_recurso(record["id"], "user.id")
    except ValueError as error:
        raise RespostaUsuarioInconclusivaError(
            "A resposta do Xano não contém um ID de usuário válido."
        ) from error

    normalized = {"id": user_id}
    for field in ("name", "email", "role"):
        value = record[field]
        if not isinstance(value, str) or not value.strip():
            raise RespostaUsuarioInconclusivaError(
                f"A resposta do Xano não contém {field} válido."
            )
        normalized[field] = value.strip()
    if not _USER_EMAIL_PATTERN.fullmatch(normalized["email"]):
        raise RespostaUsuarioInconclusivaError(
            "A resposta do Xano não contém um e-mail válido."
        )

    created_at = record["created_at"]
    if isinstance(created_at, bool) or not isinstance(
        created_at,
        (str, int, float),
    ):
        raise RespostaUsuarioInconclusivaError(
            "A resposta do Xano não contém created_at válido."
        )
    if isinstance(created_at, str) and not created_at.strip():
        raise RespostaUsuarioInconclusivaError(
            "A resposta do Xano não contém created_at válido."
        )
    if isinstance(created_at, float) and not math.isfinite(created_at):
        raise RespostaUsuarioInconclusivaError(
            "A resposta do Xano não contém created_at válido."
        )
    normalized["created_at"] = created_at
    return normalized


def listar_usuarios(token):
    _exigir_token_usuario(token, "consultar")
    response = xano_request("GET", "/user", token=token)
    if not isinstance(response, list):
        raise RespostaUsuarioInconclusivaError(
            "GET /user não retornou uma lista de usuários válida."
        )
    return [_normalizar_usuario_publico(user) for user in response]


def criar_usuario(token, *, name, email, password, role):
    _exigir_token_usuario(token, "cadastrar")
    payload = validar_dados_usuario(
        name=name,
        email=email,
        password=password,
        role=role,
    )
    try:
        response = xano_request(
            "POST",
            "/user",
            token=token,
            json=payload,
        )
    except requests.HTTPError:
        raise
    except requests.RequestException as error:
        raise OperacaoUsuarioInconclusivaError(
            "Não foi possível confirmar se o usuário foi cadastrado. "
            "Atualize a listagem antes de tentar novamente."
        ) from error

    user = _normalizar_usuario_publico(response)
    if (
        user["name"] != payload["name"]
        or user["email"].casefold() != payload["email"].casefold()
        or user["role"] != payload["role"]
    ):
        raise RespostaUsuarioInconclusivaError(
            "A resposta do Xano não corresponde ao usuário enviado."
        )
    return user


class RespostaVendaInconclusivaError(ValueError):
    """Indica que não foi possível confirmar o resultado de uma venda."""


class OperacaoVendaInconclusivaError(RuntimeError):
    """Indica que uma falha de transporte deixou a criação sem confirmação."""


_CAMPOS_FINANCEIROS_VENDA = {
    "gross_amount",
    "discount_amount",
    "net_revenue",
    "total_cmv",
    "total_costs",
    "result",
    "profit_margin_percent",
}
_TIPOS_CUSTO_VENDA = {
    "embalagem",
    "comissao_marketplace",
    "impostos",
    "frete_saida",
    "outros",
}


def _validar_numero_venda(valor, campo, *, permitir_negativo=False):
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        raise ValueError(f"{campo} deve ser um número.")
    if isinstance(valor, float) and not math.isfinite(valor):
        raise ValueError(f"{campo} deve ser finito.")
    if not permitir_negativo and valor < 0:
        raise ValueError(f"{campo} não pode ser negativo.")
    return valor


def _validar_data_venda(valor, campo):
    return sale_date_to_unix_milliseconds(valor, campo)


def _validar_filtro_data_venda(valor, campo):
    if not isinstance(valor, str):
        raise ValueError(f"{campo} deve ser um timestamp em texto.")
    return valor


def _validar_payload_venda(dados):
    if not isinstance(dados, dict):
        raise ValueError("Os dados da venda devem ser um objeto.")

    campos_permitidos = {
        "idempotency_key",
        "sales_channel",
        "order_number",
        "sale_date",
        "notes",
        "items",
        "costs",
    }
    campos_desconhecidos = set(dados) - campos_permitidos
    if campos_desconhecidos:
        raise ValueError("A venda contém campos não aceitos pelo contrato.")

    idempotency_key = dados.get("idempotency_key")
    if not isinstance(idempotency_key, str):
        raise ValueError("idempotency_key deve ser um UUID v4.")
    try:
        parsed_idempotency_key = uuid.UUID(idempotency_key)
    except (AttributeError, ValueError) as error:
        raise ValueError("idempotency_key deve ser um UUID v4.") from error
    if (
        parsed_idempotency_key.version != 4
        or str(parsed_idempotency_key) != idempotency_key.lower()
    ):
        raise ValueError("idempotency_key deve ser um UUID v4.")

    sales_channel = dados.get("sales_channel")
    if not isinstance(sales_channel, str) or not sales_channel.strip():
        raise ValueError("sales_channel deve ser texto não vazio.")

    itens = dados.get("items")
    if not isinstance(itens, list) or not itens:
        raise ValueError("A venda deve conter pelo menos um item.")

    payload = {
        "idempotency_key": idempotency_key,
        "sales_channel": sales_channel.strip(),
        "items": [],
    }

    for campo in ("order_number", "notes"):
        valor = dados.get(campo)
        if valor is not None:
            if not isinstance(valor, str):
                raise ValueError(f"{campo} deve ser texto.")
            payload[campo] = valor

    if dados.get("sale_date") is not None:
        payload["sale_date"] = _validar_data_venda(
            dados["sale_date"],
            "sale_date",
        )

    campos_item_permitidos = {
        "product_id",
        "quantity",
        "unit_sale_price",
        "discount_amount",
    }
    for indice, item in enumerate(itens):
        prefixo = f"items[{indice}]"
        if not isinstance(item, dict):
            raise ValueError(f"{prefixo} deve ser um objeto.")
        if set(item) - campos_item_permitidos:
            raise ValueError(f"{prefixo} contém campos não aceitos.")
        if "product_id" not in item:
            raise ValueError(f"{prefixo}.product_id é obrigatório.")
        if "quantity" not in item:
            raise ValueError(f"{prefixo}.quantity é obrigatório.")
        if "unit_sale_price" not in item:
            raise ValueError(f"{prefixo}.unit_sale_price é obrigatório.")

        product_id = _validar_id_recurso(
            item["product_id"],
            f"{prefixo}.product_id",
        )
        quantity = item["quantity"]
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
            raise ValueError(f"{prefixo}.quantity deve ser um inteiro maior que zero.")

        unit_sale_price = _validar_numero_venda(
            item["unit_sale_price"],
            f"{prefixo}.unit_sale_price",
        )
        payload_item = {
            "product_id": product_id,
            "quantity": quantity,
            "unit_sale_price": unit_sale_price,
        }
        desconto = item.get("discount_amount")
        if desconto is not None:
            desconto = _validar_numero_venda(
                desconto,
                f"{prefixo}.discount_amount",
            )
            if desconto > unit_sale_price * quantity:
                raise ValueError(
                    f"{prefixo}.discount_amount não pode superar o valor bruto do item."
                )
            payload_item["discount_amount"] = desconto
        payload["items"].append(payload_item)

    if "costs" not in dados:
        raise ValueError("costs é obrigatório e deve ser uma lista.")
    custos = dados["costs"]
    if not isinstance(custos, list):
        raise ValueError("costs é obrigatório e deve ser uma lista.")
    campos_custo_permitidos = {"cost_type", "description", "amount"}
    payload["costs"] = []
    for indice, custo in enumerate(custos):
        prefixo = f"costs[{indice}]"
        if not isinstance(custo, dict):
            raise ValueError(f"{prefixo} deve ser um objeto.")
        if set(custo) - campos_custo_permitidos:
            raise ValueError(f"{prefixo} contém campos não aceitos.")
        tipo = custo.get("cost_type")
        if not isinstance(tipo, str) or tipo not in _TIPOS_CUSTO_VENDA:
            raise ValueError(f"{prefixo}.cost_type não é permitido.")
        if "amount" not in custo:
            raise ValueError(f"{prefixo}.amount é obrigatório.")

        payload_custo = {
            "cost_type": tipo,
            "amount": _validar_numero_venda(
                custo["amount"],
                f"{prefixo}.amount",
            ),
        }
        descricao = custo.get("description")
        if descricao is not None:
            if not isinstance(descricao, str):
                raise ValueError(f"{prefixo}.description deve ser texto.")
            payload_custo["description"] = descricao
        payload["costs"].append(payload_custo)

    return payload


def _validar_resumo_financeiro_venda(resumo):
    if not isinstance(resumo, dict) or not _CAMPOS_FINANCEIROS_VENDA.issubset(resumo):
        raise RespostaVendaInconclusivaError(
            "A resposta do Xano não contém o resumo financeiro completo da venda."
        )
    for campo in _CAMPOS_FINANCEIROS_VENDA:
        valor = resumo[campo]
        if (
            isinstance(valor, bool)
            or not isinstance(valor, (int, float))
            or (isinstance(valor, float) and not math.isfinite(valor))
        ):
            raise RespostaVendaInconclusivaError(
                f"A resposta do Xano contém valor financeiro inválido: {campo}."
            )


def _validar_resposta_detalhe_venda(resposta, venda_id=None):
    if not isinstance(resposta, dict):
        raise RespostaVendaInconclusivaError(
            "A resposta do Xano não confirmou os dados da venda."
        )
    venda = resposta.get("sale")
    if not isinstance(venda, dict):
        raise RespostaVendaInconclusivaError(
            "A resposta do Xano não contém o registro da venda."
        )
    try:
        id_retornado = _validar_id_recurso(venda.get("id"), "sale.id")
    except ValueError as error:
        raise RespostaVendaInconclusivaError(
            "A resposta do Xano não contém um identificador válido para a venda."
        ) from error
    if venda_id is not None and id_retornado != venda_id:
        raise RespostaVendaInconclusivaError(
            "A resposta do Xano não corresponde à venda solicitada."
        )
    if venda.get("sale_date") is not None:
        try:
            sale_date_to_unix_milliseconds(venda["sale_date"])
        except (TypeError, ValueError, OverflowError) as error:
            raise RespostaVendaInconclusivaError(
                "A resposta do Xano contém uma data de venda inválida."
            ) from error

    for campo in ("items", "costs"):
        valor = resposta.get(campo)
        if not isinstance(valor, list) or any(
            not isinstance(registro, dict) for registro in valor
        ):
            raise RespostaVendaInconclusivaError(
                f"A resposta do Xano não contém uma lista válida de {campo}."
            )
    _validar_resumo_financeiro_venda(resposta.get("financial_summary"))
    return resposta


def criar_venda(token, dados):
    if not token:
        raise ValueError("A sessão expirou. Entre novamente para registrar vendas.")
    payload = _validar_payload_venda(dados)
    try:
        resposta = xano_request(
            "POST",
            "/sale",
            token=token,
            json=payload,
        )
    except (requests.Timeout, requests.ConnectionError) as error:
        raise OperacaoVendaInconclusivaError(
            "Não foi possível confirmar se a venda foi registrada. "
            "Não repita automaticamente a operação; consulte as vendas antes "
            "de tentar novamente."
        ) from error

    return _validar_resposta_detalhe_venda(resposta)


def _validar_inteiro_paginacao(valor, campo, *, permitir_zero=True):
    minimo = 0 if permitir_zero else 1
    if isinstance(valor, bool) or not isinstance(valor, int) or valor < minimo:
        raise ValueError(f"{campo} deve ser um inteiro maior ou igual a {minimo}.")
    return valor


def _validar_resposta_lista_vendas(resposta):
    if not isinstance(resposta, dict):
        raise ValueError("A resposta paginada de vendas deve ser um objeto.")
    pagination_fields = {
        "itemsReceived",
        "curPage",
        "offset",
        "itemsTotal",
        "pageTotal",
        "nextPage",
        "prevPage",
    }
    if "items" in resposta and "curPage" in resposta and "perPage" in resposta:
        cur_page = resposta.get("curPage")
        per_page = resposta.get("perPage")
        total = resposta.get("total", len(resposta["items"]))
        if (
            isinstance(cur_page, int)
            and isinstance(per_page, int)
            and isinstance(total, int)
            and not isinstance(cur_page, bool)
            and not isinstance(per_page, bool)
            and not isinstance(total, bool)
        ):
            items = resposta["items"]
            if isinstance(items, list):
                page_total = max(1, (total + per_page - 1) // per_page)
                resposta = {
                    "itemsReceived": len(items),
                    "curPage": cur_page,
                    "nextPage": cur_page + 1 if cur_page < page_total else None,
                    "prevPage": cur_page - 1 if cur_page > 1 else None,
                    "offset": (cur_page - 1) * per_page,
                    "itemsTotal": total,
                    "pageTotal": page_total,
                    "items": items,
                }
    if (
        "items" in resposta
        and not pagination_fields.intersection(resposta)
        and isinstance(resposta["items"], list)
    ):
        item_count = len(resposta["items"])
        resposta = {
            "itemsReceived": item_count,
            "curPage": 1,
            "nextPage": None,
            "prevPage": None,
            "offset": 0,
            "itemsTotal": item_count,
            "pageTotal": 1,
            "items": resposta["items"],
        }
    campos_inteiros = {
        "itemsReceived": True,
        "curPage": False,
        "offset": True,
        "itemsTotal": True,
        "pageTotal": True,
    }
    for campo, permitir_zero in campos_inteiros.items():
        if campo not in resposta:
            raise ValueError(f"A resposta paginada não contém {campo}.")
        _validar_inteiro_paginacao(
            resposta[campo],
            campo,
            permitir_zero=permitir_zero,
        )
    for campo in ("nextPage", "prevPage"):
        if campo not in resposta:
            raise ValueError(f"A resposta paginada não contém {campo}.")
        if resposta[campo] is not None:
            _validar_inteiro_paginacao(
                resposta[campo],
                campo,
                permitir_zero=False,
            )
    itens = resposta.get("items")
    if not isinstance(itens, list) or any(
        not isinstance(item, dict) for item in itens
    ):
        raise ValueError("A resposta paginada não contém uma lista válida de vendas.")
    return resposta


def _validar_filtro_venda(valor, campo):
    if valor is None:
        return None
    if isinstance(valor, str):
        return valor.strip() or None
    raise ValueError(f"{campo} deve ser texto.")


def listar_vendas(
    token,
    *,
    sales_channel=None,
    order_number=None,
    status=None,
    start_date=None,
    end_date=None,
    page=1,
    per_page=20,
):
    if not token:
        raise ValueError("A sessão expirou. Entre novamente para consultar vendas.")
    filtro_canal = _validar_filtro_venda(sales_channel, "sales_channel")
    if filtro_canal is None:
        raise ValueError(
            "O endpoint GET /sale exige sales_channel; "
            "sales_channel é obrigatório para consultar vendas."
        )

    parametros = {
        "sales_channel": filtro_canal,
        "page": _validar_inteiro_paginacao(
            page,
            "page",
            permitir_zero=False,
        ),
        "per_page": _validar_inteiro_paginacao(
            per_page,
            "per_page",
            permitir_zero=False,
        ),
    }
    if per_page > 100:
        raise ValueError("per_page não pode ser maior que 100.")

    for campo, valor in (
        ("order_number", order_number),
    ):
        filtro = _validar_filtro_venda(valor, campo)
        if filtro is not None:
            parametros[campo] = filtro

    if status is not None:
        if not isinstance(status, str) or status not in {
            "registrada",
            "confirmada",
            "cancelada",
        }:
            raise ValueError("status deve ser 'registrada' ou 'cancelada'.")
        parametros["status"] = status

    for campo, valor in (("start_date", start_date), ("end_date", end_date)):
        if valor is not None:
            parametros[campo] = _validar_filtro_data_venda(valor, campo)

    resposta = xano_request(
        "GET",
        "/sale",
        token=token,
        params=parametros,
    )
    return _validar_resposta_lista_vendas(resposta)


def consultar_venda(*args, token=None, venda_id=None, sale_id=None):
    if len(args) == 2:
        token, venda_id = args
    elif len(args) == 1:
        if venda_id is None:
            venda_id = args[0]
        else:
            token = args[0]
    elif len(args) > 2:
        raise TypeError("consultar_venda recebeu argumentos em excesso.")
    if venda_id is None:
        venda_id = sale_id
    if not token:
        raise ValueError("A sessão expirou. Entre novamente para consultar vendas.")
    venda_id = _validar_id_recurso(venda_id, "sale_id")
    resposta = xano_request(
        "GET",
        f"/sale/{venda_id}",
        token=token,
    )
    return _validar_resposta_detalhe_venda(resposta, venda_id=venda_id)


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


def _validar_id_recurso(resource_id, field_name):
    if isinstance(resource_id, bool):
        raise ValueError(f"{field_name} deve ser um inteiro positivo.")
    if isinstance(resource_id, str) and resource_id.strip().isdigit():
        resource_id = int(resource_id.strip())
    if not isinstance(resource_id, int) or resource_id < 1:
        raise ValueError(f"{field_name} deve ser um inteiro positivo.")
    return resource_id


def _confirmar_registro_recurso(payload, resource_id, resource_name):
    if not isinstance(payload, dict):
        raise RespostaOperacaoInconclusivaError(
            f"A resposta do Xano para {resource_name} não confirmou o registro."
        )

    returned_id = payload.get("id")
    try:
        returned_id = _validar_id_recurso(returned_id, "id")
    except ValueError as error:
        raise RespostaOperacaoInconclusivaError(
            f"A resposta do Xano para {resource_name} não confirmou o registro."
        ) from error

    if returned_id != resource_id:
        raise RespostaOperacaoInconclusivaError(
            f"A resposta do Xano para {resource_name} não corresponde ao registro solicitado."
        )
    normalized = dict(payload)
    normalized["id"] = returned_id
    return normalized


def _confirmar_produto_recurso(payload, product_id):
    record = _confirmar_registro_recurso(payload, product_id, "produto")

    def is_finite_nonnegative_number(value):
        try:
            return (
                not isinstance(value, bool)
                and isinstance(value, (int, float))
                and math.isfinite(value)
                and value >= 0
            )
        except OverflowError:
            return False

    required_fields = {
        "name",
        "category_id",
        "min_stock",
        "sale_price",
        "status",
        "stock_quantity",
        "average_cost",
    }
    if not required_fields.issubset(record):
        raise RespostaOperacaoInconclusivaError(
            "A resposta do Xano para produto está incompleta."
        )

    if not isinstance(record["name"], str) or not record["name"].strip():
        raise RespostaOperacaoInconclusivaError(
            "A resposta do Xano para produto contém nome inválido."
        )

    category_id = record["category_id"]
    if isinstance(category_id, dict):
        category_id = category_id.get("id")
    try:
        _validar_id_recurso(category_id, "category_id")
    except ValueError as error:
        raise RespostaOperacaoInconclusivaError(
            "A resposta do Xano para produto contém categoria inválida."
        ) from error

    if (
        isinstance(record["min_stock"], bool)
        or not isinstance(record["min_stock"], int)
        or record["min_stock"] < 0
    ):
        raise RespostaOperacaoInconclusivaError(
            "A resposta do Xano para produto contém estoque mínimo inválido."
        )

    if not is_finite_nonnegative_number(record["sale_price"]):
        raise RespostaOperacaoInconclusivaError(
            "A resposta do Xano para produto contém preço inválido."
        )

    if not isinstance(record["status"], str) or record["status"] not in {
        "ativo",
        "inativo",
    }:
        raise RespostaOperacaoInconclusivaError(
            "A resposta do Xano para produto contém status inválido."
        )

    for field in ("sku", "description"):
        value = record.get(field)
        if value is not None and not isinstance(value, str):
            raise RespostaOperacaoInconclusivaError(
                f"A resposta do Xano para produto contém {field} inválido."
            )

    for field in ("stock_quantity", "average_cost"):
        if not is_finite_nonnegative_number(record[field]):
            raise RespostaOperacaoInconclusivaError(
                f"A resposta do Xano para produto contém {field} inválido."
            )

    return record


def consultar_produto(*args, token=None, product_id=None):
    if len(args) == 2:
        token, product_id = args
    elif len(args) == 1:
        if product_id is None:
            product_id = args[0]
        else:
            token = args[0]
    elif len(args) > 2:
        raise TypeError("consultar_produto recebeu argumentos em excesso.")
    if not token:
        raise ValueError("A sessão expirou. Entre novamente para consultar produtos.")
    product_id = _validar_id_recurso(product_id, "product_id")
    payload = xano_request(
        "GET",
        f"/product/{product_id}",
        token=token,
    )
    return _confirmar_produto_recurso(payload, product_id)


def editar_produto(*args, token=None, product_id=None, **fields):
    if len(args) == 2:
        token, product_id = args
    elif len(args) == 1:
        if product_id is None:
            product_id = args[0]
        elif token is None:
            token = args[0]
        else:
            raise TypeError("editar_produto recebeu argumentos duplicados.")
    elif len(args) > 2:
        raise TypeError("editar_produto recebeu argumentos em excesso.")
    if not token:
        raise ValueError("A sessão expirou. Entre novamente para editar produtos.")
    product_id = _validar_id_recurso(product_id, "product_id")

    allowed_fields = {
        "name",
        "sku",
        "category_id",
        "sale_price",
        "min_stock",
        "status",
        "stock_quantity",
        "average_cost",
    }
    unsupported = set(fields) - allowed_fields
    if unsupported:
        raise ValueError("A edição contém campos não aceitos.")

    payload = {}
    for field, value in fields.items():
        if value is None:
            continue
        if field in {"name", "sku"}:
            if not isinstance(value, str):
                raise ValueError(f"{field} deve ser texto.")
            if field == "name" and not value.strip():
                raise ValueError("name não pode ficar vazio.")
            payload[field] = value.strip()
        elif field == "category_id":
            payload[field] = _validar_id_recurso(value, field)
        elif field == "min_stock":
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError("min_stock deve ser um inteiro não negativo.")
            payload[field] = value
        elif field == "sale_price":
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                or value < 0
            ):
                raise ValueError("sale_price deve ser um número não negativo.")
            payload[field] = float(value)
        elif field == "status":
            if value not in {"ativo", "inativo"}:
                raise ValueError("status deve ser 'ativo' ou 'inativo'.")
            payload[field] = value

    if not payload:
        raise ValueError("Informe ao menos um campo cadastral para editar.")

    response = xano_request(
        "PATCH",
        f"/product/{product_id}",
        token=token,
        json=payload,
    )
    record = _confirmar_produto_recurso(response, product_id)
    if "status" in payload and record.get("status") != payload["status"]:
        raise RespostaOperacaoInconclusivaError(
            "A resposta do Xano não confirmou o status atualizado do produto."
        )
    return record


def inativar_produto(*args, token=None, product_id=None):
    if len(args) == 2:
        token, product_id = args
    elif len(args) == 1:
        if product_id is None:
            product_id = args[0]
        else:
            token = args[0]
    elif len(args) > 2:
        raise TypeError("inativar_produto recebeu argumentos em excesso.")
    if not token:
        raise ValueError("A sessão expirou. Entre novamente para inativar produtos.")
    product_id = _validar_id_recurso(product_id, "product_id")
    payload = xano_request(
        "PATCH",
        f"/product/{product_id}/deactivate",
        token=token,
    )
    record = _confirmar_produto_recurso(payload, product_id)
    if record.get("status") != "inativo":
        raise RespostaOperacaoInconclusivaError(
            "A resposta do Xano não confirmou a inativação do produto."
        )
    return record


def listar_movimentacoes_estoque(
    token=None,
    *,
    product_id=None,
    movement_type=None,
    start_date=None,
    end_date=None,
    page=None,
    per_page=None,
):
    """Consulta movimentações; datas e enum são encaminhados sem conversão."""
    params = {}

    if product_id is not None:
        if isinstance(product_id, bool) or not isinstance(product_id, int) or product_id < 1:
            raise ValueError("product_id deve ser um ID inteiro positivo.")
        params["product_id"] = product_id

    if movement_type is not None:
        if not isinstance(movement_type, str):
            raise ValueError("movement_type deve ser texto.")
        movement_type = movement_type.strip()
        if movement_type:
            params["movement_type"] = movement_type

    for field, value in (("start_date", start_date), ("end_date", end_date)):
        if value is not None:
            if not isinstance(value, str):
                raise ValueError(f"{field} deve ser um timestamp em texto.")
            value = value.strip()
            if value:
                params[field] = value

    if page is not None:
        if isinstance(page, bool) or not isinstance(page, int) or page < 1:
            raise ValueError("page deve ser um inteiro positivo.")
        params["page"] = page

    if per_page is not None:
        if (
            isinstance(per_page, bool)
            or not isinstance(per_page, int)
            or not 1 <= per_page <= 100
        ):
            raise ValueError("per_page deve ser um inteiro entre 1 e 100.")
        params["per_page"] = per_page

    payload = xano_request(
        "GET",
        "/stock-movement",
        token=token,
        params=params,
    )
    if not isinstance(payload, dict):
        raise ValueError(
            "GET /stock-movement retornou uma resposta em formato inválido."
        )

    movements = payload.get("movements")
    if not isinstance(movements, list):
        movements = payload.get("items")
    if not isinstance(movements, list):
        raise ValueError(
            "GET /stock-movement retornou uma resposta sem a lista "
            "movements ou items."
        )
    if any(not isinstance(movement, dict) for movement in movements):
        raise ValueError(
            "GET /stock-movement retornou um registro de movimentação inválido."
        )

    if payload.get("movements") is movements:
        return payload

    normalized_payload = dict(payload)
    normalized_payload["movements"] = movements
    return normalized_payload


def extrair_fornecedores(payload):
    """Valida e normaliza a lista direta retornada por GET /supplier."""
    if isinstance(payload, dict):
        if not any(
            isinstance(payload.get(key), list)
            for key in ("suppliers", "data", "items", "results", "rows")
        ):
            raise ValueError("GET /supplier retornou uma lista em formato inválido.")
        payload = _extrair_lista(payload, ("suppliers", "data", "items", "results", "rows"))
    if not isinstance(payload, list):
        raise ValueError("GET /supplier retornou uma lista em formato inválido.")

    fornecedores = []
    for item in payload:
        if not isinstance(item, dict):
            raise ValueError("GET /supplier retornou um fornecedor inválido.")

        fornecedor_id = item.get("id")
        if isinstance(fornecedor_id, bool):
            raise ValueError("GET /supplier retornou um ID de fornecedor inválido.")
        if isinstance(fornecedor_id, str) and fornecedor_id.strip().isdigit():
            fornecedor_id = int(fornecedor_id.strip())
        if not isinstance(fornecedor_id, int) or fornecedor_id < 1:
            raise ValueError("GET /supplier retornou um ID de fornecedor inválido.")

        name = item.get("name")
        if name is not None and (not isinstance(name, str) or not name.strip()):
            raise ValueError("GET /supplier retornou um nome de fornecedor inválido.")

        fornecedor = {"id": fornecedor_id}
        if isinstance(name, str) and name.strip():
            fornecedor["name"] = name.strip()
        for field in ("cnpj", "contact_name", "email", "phone", "status"):
            value = item.get(field)
            if value is not None:
                if not isinstance(value, str):
                    raise ValueError(
                        f"GET /supplier retornou {field} em formato inválido."
                    )
                if value.strip():
                    fornecedor[field] = value.strip()
        fornecedores.append(fornecedor)

    return fornecedores


def listar_fornecedores(token=None, *, name=None, status=None):
    """Lista fornecedores pelo endpoint Xano confirmado."""
    if status is None:
        configured_supplier_url = (
            os.getenv("XANO_SUPPLIERS_URL")
            or _get_streamlit_secret("XANO_SUPPLIERS_URL")
        )
        if configured_supplier_url:
            status = "ativo"
        else:
            raise ValueError("Informe uma situação válida para consultar fornecedores.")
    if not isinstance(status, str) or status not in {"ativo", "inativo", "todos"}:
        raise ValueError("Informe uma situação válida para consultar fornecedores.")

    status_values = ("ativo", "inativo") if status == "todos" else (status,)
    fornecedores = []
    ids_encontrados = set()
    for status_value in status_values:
        params = {"status": status_value}
        if name is not None and str(name).strip():
            params["name"] = str(name).strip()
        payload = xano_request(
            "GET",
            SUPPLIERS_URL,
            token=token,
            params=params,
        )
        for fornecedor in extrair_fornecedores(payload):
            supplier_id = fornecedor.get("id")
            if supplier_id in ids_encontrados:
                continue
            ids_encontrados.add(supplier_id)
            fornecedores.append(fornecedor)
    return fornecedores


def validar_cnpj(value):
    value = str(value or "").strip()
    if not value or any(char not in "0123456789./- " for char in value):
        return False

    digits = "".join(char for char in value if char.isdigit())
    if len(digits) != 14 or len(set(digits)) == 1:
        return False

    def calcular_digito(base, weights):
        total = sum(int(digit) * weight for digit, weight in zip(base, weights))
        remainder = total % 11
        return "0" if remainder < 2 else str(11 - remainder)

    primeiro = calcular_digito(
        digits[:12],
        (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2),
    )
    segundo = calcular_digito(
        digits[:12] + primeiro,
        (6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2),
    )
    return digits[-2:] == primeiro + segundo


def _validar_campos_fornecedor(fields, *, create):
    allowed_fields = {
        "name",
        "contact_name",
        "cnpj",
        "email",
        "phone",
    }
    if not create:
        allowed_fields.add("status")

    unsupported = set(fields) - allowed_fields
    if unsupported:
        raise ValueError("A operação contém campos não aceitos.")

    payload = {}
    for field, value in fields.items():
        if value is None:
            continue
        if field in {"name", "contact_name", "cnpj", "email", "phone"}:
            if not isinstance(value, str):
                raise ValueError(f"{field} deve ser texto.")
            value = value.strip()
            if not value:
                if field == "name" and create:
                    raise ValueError("name é obrigatório.")
                continue
            if field == "name" and not value:
                raise ValueError("name não pode ficar vazio.")
            if field == "cnpj" and not validar_cnpj(value):
                raise ValueError("Informe um CNPJ válido.")
            payload[field] = value
        elif field == "status":
            if value not in {"ativo", "inativo"}:
                raise ValueError("status deve ser 'ativo' ou 'inativo'.")
            payload[field] = value

    if create and "name" not in payload:
        raise ValueError("name é obrigatório.")
    if not create and not payload:
        raise ValueError("Informe ao menos um campo para editar o fornecedor.")
    return payload


def consultar_fornecedor(*args, token=None, supplier_id=None):
    if len(args) == 2:
        token, supplier_id = args
    elif len(args) == 1:
        if supplier_id is None:
            supplier_id = args[0]
        else:
            token = args[0]
    elif len(args) > 2:
        raise TypeError("consultar_fornecedor recebeu argumentos em excesso.")
    if not token:
        raise ValueError("A sessão expirou. Entre novamente para consultar fornecedores.")
    supplier_id = _validar_id_recurso(supplier_id, "supplier_id")
    payload = xano_request(
        "GET",
        f"/supplier/{supplier_id}",
        token=token,
    )
    record = _confirmar_registro_recurso(payload, supplier_id, "fornecedor")
    if not isinstance(record.get("name"), str) or not record["name"].strip():
        raise ValueError("A resposta do Xano para fornecedor não contém nome válido.")
    return record


def criar_fornecedor(
    token,
    *,
    name,
    contact_name=None,
    cnpj=None,
    email=None,
    phone=None,
):
    if not token:
        raise ValueError("A sessão expirou. Entre novamente para cadastrar fornecedores.")
    payload = _validar_campos_fornecedor(
        {
            "name": name,
            "contact_name": contact_name,
            "cnpj": cnpj,
            "email": email,
            "phone": phone,
        },
        create=True,
    )
    response = xano_request(
        "POST",
        "/supplier",
        token=token,
        json=payload,
    )
    if not isinstance(response, dict):
        raise RespostaOperacaoInconclusivaError(
            "A resposta do Xano não confirmou o cadastro do fornecedor."
        )
    try:
        supplier_id = _validar_id_recurso(response.get("id"), "id")
    except ValueError as error:
        raise RespostaOperacaoInconclusivaError(
            "A resposta do Xano não confirmou o cadastro do fornecedor."
        ) from error
    if not isinstance(response.get("name"), str) or not response["name"].strip():
        raise RespostaOperacaoInconclusivaError(
            "A resposta do Xano não confirmou o cadastro do fornecedor."
        )
    if response.get("status") != "ativo":
        raise RespostaOperacaoInconclusivaError(
            "A resposta do Xano não confirmou o status inicial do fornecedor."
        )
    normalized = dict(response)
    normalized["id"] = supplier_id
    return normalized


def editar_fornecedor(*args, token=None, supplier_id=None, **fields):
    if len(args) == 2:
        token, supplier_id = args
    elif len(args) == 1:
        if supplier_id is None:
            supplier_id = args[0]
        else:
            token = args[0]
    elif len(args) > 2:
        raise TypeError("editar_fornecedor recebeu argumentos em excesso.")
    if not token:
        raise ValueError("A sessão expirou. Entre novamente para editar fornecedores.")
    supplier_id = _validar_id_recurso(supplier_id, "supplier_id")
    payload = _validar_campos_fornecedor(fields, create=False)
    response = xano_request(
        "PATCH",
        f"/supplier/{supplier_id}",
        token=token,
        json=payload,
    )
    record = _confirmar_registro_recurso(response, supplier_id, "fornecedor")
    if not isinstance(record.get("name"), str) or not record["name"].strip():
        raise ValueError("A resposta do Xano para fornecedor não contém nome válido.")
    if "status" in payload and record.get("status") != payload["status"]:
        raise RespostaOperacaoInconclusivaError(
            "A resposta do Xano não confirmou o status atualizado do fornecedor."
        )
    return record


def inativar_fornecedor(*args, token=None, supplier_id=None):
    if len(args) == 2:
        token, supplier_id = args
    elif len(args) == 1:
        if supplier_id is None:
            supplier_id = args[0]
        else:
            token = args[0]
    elif len(args) > 2:
        raise TypeError("inativar_fornecedor recebeu argumentos em excesso.")
    if not token:
        raise ValueError("A sessão expirou. Entre novamente para inativar fornecedores.")
    supplier_id = _validar_id_recurso(supplier_id, "supplier_id")
    payload = xano_request(
        "PATCH",
        f"/supplier/{supplier_id}/deactivate",
        token=token,
    )
    record = _confirmar_registro_recurso(payload, supplier_id, "fornecedor")
    if record.get("status") != "inativo":
        raise RespostaOperacaoInconclusivaError(
            "A resposta do Xano não confirmou a inativação do fornecedor."
        )
    return record


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


def confirmar_produto_criado(payload, *, description=None):
    """Confirma o registro direto de produto retornado por POST /product."""
    if not isinstance(payload, dict):
        return False

    name = payload.get("name")
    category_id = payload.get("category_id")
    min_stock = payload.get("min_stock")
    sale_price = payload.get("sale_price")
    if not isinstance(name, str) or not name.strip():
        return False
    if (
        isinstance(category_id, bool)
        or not isinstance(category_id, int)
        or category_id < 1
    ):
        return False
    if isinstance(min_stock, bool) or not isinstance(min_stock, int) or min_stock < 0:
        return False
    if (
        isinstance(sale_price, bool)
        or not isinstance(sale_price, (int, float))
        or not math.isfinite(sale_price)
        or sale_price < 0
    ):
        return False

    if "id" in payload:
        product_id = payload["id"]
        if isinstance(product_id, bool):
            return False
        if isinstance(product_id, int):
            return product_id > 0
        if isinstance(product_id, str):
            return product_id.strip().isdigit() and int(product_id.strip()) > 0
        return False

    return True


class RespostaCriacaoInconclusivaError(ValueError):
    """Indica que a resposta não confirma se o produto foi criado."""


    def __init__(self, message, *, status_code=None, backend_message=None):
        super().__init__(message)
        self.status_code = status_code
        self.backend_message = backend_message


class RespostaOperacaoInconclusivaError(ValueError):
    """Indica que a resposta não confirma o resultado de uma operação cadastral."""


class RespostaEntradaEstoqueInconclusivaError(ValueError):
    """Indica que a resposta não confirma o registro da entrada de estoque."""

    def __init__(self, message, *, status_code=None, backend_message=None):
        super().__init__(message)
        self.status_code = status_code
        self.backend_message = backend_message


def mapear_payload_entrada_estoque(
    *,
    idempotency_key,
    product_id,
    supplier_id,
    quantity,
    unit_purchase_cost,
    entry_date,
    invoice_number,
    notes,
    inbound_freight=None,
    other_acquisition_costs=None,
):
    """Valida e mapeia apenas os campos confirmados do POST de entrada."""
    for field, value in (("product_id", product_id), ("supplier_id", supplier_id)):
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValueError(f"{field} deve ser um ID inteiro positivo.")

    if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
        raise ValueError("quantity deve ser um número inteiro maior que zero.")

    costs = {
        "unit_purchase_cost": unit_purchase_cost,
        "inbound_freight": inbound_freight,
        "other_acquisition_costs": other_acquisition_costs,
    }
    for field, value in costs.items():
        if value is None and field != "unit_purchase_cost":
            continue
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or value < 0
        ):
            raise ValueError(f"{field} deve ser um número não negativo.")

    if isinstance(entry_date, datetime):
        raise ValueError("entry_date deve ser uma data, sem horário.")
    if isinstance(entry_date, date):
        entry_date = entry_date.isoformat()
    elif isinstance(entry_date, str):
        try:
            entry_date = date.fromisoformat(entry_date).isoformat()
        except ValueError as error:
            raise ValueError("entry_date deve ser uma data válida.") from error
    else:
        raise ValueError("entry_date deve ser uma data válida.")

    if not isinstance(invoice_number, str):
        raise ValueError("invoice_number deve ser texto.")
    if not isinstance(notes, str):
        raise ValueError("notes deve ser texto.")

    if not isinstance(idempotency_key, str):
        raise ValueError("idempotency_key deve ser um UUID v4.")
    try:
        parsed_idempotency_key = uuid.UUID(idempotency_key)
    except (AttributeError, ValueError) as error:
        raise ValueError("idempotency_key deve ser um UUID v4.") from error
    if (
        parsed_idempotency_key.version != 4
        or str(parsed_idempotency_key) != idempotency_key.lower()
    ):
        raise ValueError("idempotency_key deve ser um UUID v4.")

    payload = {
        "idempotency_key": idempotency_key,
        "product_id": product_id,
        "supplier_id": supplier_id,
        "quantity": quantity,
        "unit_purchase_cost": float(unit_purchase_cost),
        "entry_date": entry_date,
        "invoice_number": invoice_number,
        "notes": notes,
    }
    for field in ("inbound_freight", "other_acquisition_costs"):
        value = costs[field]
        if value is not None:
            payload[field] = float(value)

    return payload


def confirmar_entrada_estoque(payload):
    if not isinstance(payload, dict):
        return False

    if not payload.get("entry") or not payload.get("movement"):
        return False

    for field in ("stock_quantity", "average_cost"):
        value = payload.get(field)
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or value < 0
        ):
            return False

    return True


def criar_entrada_estoque(
    token,
    *,
    idempotency_key,
    product_id,
    supplier_id,
    quantity,
    unit_purchase_cost,
    entry_date,
    invoice_number,
    notes,
    inbound_freight=None,
    other_acquisition_costs=None,
):
    """Registra entrada de estoque e exige confirmação explícita do Xano."""
    if not token:
        raise ValueError("A sessão expirou. Entre novamente para registrar.")

    payload = mapear_payload_entrada_estoque(
        idempotency_key=idempotency_key,
        product_id=product_id,
        supplier_id=supplier_id,
        quantity=quantity,
        unit_purchase_cost=unit_purchase_cost,
        entry_date=entry_date,
        invoice_number=invoice_number,
        notes=notes,
        inbound_freight=inbound_freight,
        other_acquisition_costs=other_acquisition_costs,
    )
    response = _xano_http_request(
        "POST",
        STOCK_ENTRY_URL,
        token=token,
        json=payload,
    )
    status_code = getattr(response, "status_code", None)
    resposta = _decode_xano_response(response)

    if (
        not isinstance(status_code, int)
        or status_code < 200
        or status_code >= 300
        or not confirmar_entrada_estoque(resposta)
    ):
        raise RespostaEntradaEstoqueInconclusivaError(
            "O Xano não confirmou o registro da entrada de estoque.",
            status_code=status_code,
            backend_message=_xano_response_error_message(response, resposta),
        )

    return resposta


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
    category_id,
    min_stock,
    sale_price,
    sku="",
    description=None,
):
    """Valida e mapeia os campos de criação conforme o contrato do Xano."""
    name = str(name or "").strip()

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
    category_id,
    min_stock,
    sale_price,
    sku="",
    description=None,
):
    """Envia o cadastro de produto ao endpoint existente do Xano."""
    if not token:
        raise ValueError("A sessão expirou. Entre novamente para cadastrar.")

    payload = mapear_payload_produto(
        name=name,
        category_id=category_id,
        min_stock=min_stock,
        sale_price=sale_price,
        sku=sku,
        description=description,
    )

    response = _xano_http_request(
        "POST",
        "/product",
        token=token,
        json=payload,
    )
    resposta = _decode_xano_response(response)

    if not confirmar_produto_criado(resposta):
        raise RespostaCriacaoInconclusivaError(
            "O Xano n\u00e3o confirmou a cria\u00e7\u00e3o do produto.",
            status_code=getattr(response, "status_code", None),
            backend_message=_xano_response_error_message(response, resposta),
        )

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
