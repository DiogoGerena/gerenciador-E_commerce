import math
import os
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
    resources_base_url = (
        os.getenv("XANO_RESOURCES_URL")
        or _get_streamlit_secret("XANO_RESOURCES_URL")
        or base_url
    )
    token = os.getenv("XANO_API_TOKEN") or _get_streamlit_secret("XANO_API_TOKEN")

    if not base_url:
        raise ValueError("XANO_API_URL não está configurada.")

    return {
        "base_url": base_url.rstrip("/"),
        "auth_base_url": auth_base_url.rstrip("/"),
        "resources_base_url": resources_base_url.rstrip("/"),
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
            "aux.ecommerce",
            "aux_ecommerce",
            "aux ecommerce",
            "auxiliar ecommerce",
            "auxiliar_ecommerce",
        }:
            return "aux.ecommerce"

        if nome in {"auxiliar", "operacional"}:
            return "aux.ecommerce"

    return None


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
    """Executa uma requisição à API do Xano."""
    config = get_xano_config()

    if isinstance(endpoint, str) and endpoint.startswith("/auth/"):
        base_url = config["auth_base_url"]
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


def mapear_payload_produto(
    *,
    name,
    description,
    category_id,
    min_stock,
    sale_price,
    status,
    sku="",
):
    """Valida e mapeia os campos do cadastro documentados localmente.

    A correspondência entre estes nomes e os inputs do POST remoto ainda precisa
    ser confirmada no painel do Xano antes de considerar a integração concluída.
    """
    name = str(name or "").strip()
    description = str(description or "").strip()
    status = str(status or "").strip()

    if not name:
        raise ValueError("Informe o nome do produto.")
    if not description:
        raise ValueError("Informe a descrição do produto.")
    if not status:
        raise ValueError("Informe a situação do produto.")
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
        "description": description,
        "category_id": category_id,
        "min_stock": min_stock,
        "sale_price": float(sale_price),
        "status": status,
    }

    sku = str(sku or "").strip()
    payload["sku"] = sku

    return payload


def criar_produto(
    token,
    *,
    name,
    description,
    category_id,
    min_stock,
    sale_price,
    status,
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

    return xano_request(
        "POST",
        "/product",
        token=token,
        json=payload,
    )


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
