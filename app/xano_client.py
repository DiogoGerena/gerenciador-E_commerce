
import requests
import streamlit as st


def xano_request(method, endpoint, **kwargs):
    """Envia uma requisição autenticada para a API do Xano."""

    base_url = st.secrets["XANO_API_URL"].rstrip("/")
    token = st.secrets["XANO_API_TOKEN"]

    url = f"{base_url}/{endpoint.lstrip('/')}"

    headers = kwargs.pop("headers", {})
    headers["Authorization"] = f"Bearer {token}"

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

    return response.json()
