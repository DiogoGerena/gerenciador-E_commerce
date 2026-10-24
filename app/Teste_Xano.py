
import streamlit as st
from xano_client import xano_request

st.set_page_config(page_title="Teste Xano", page_icon="🔌")

st.title("Teste de conexão com o Xano")

if st.button("Consultar produtos"):
    try:
        produtos = xano_request(
            "GET",
            "/product",
            params={
                "name": "",
                "category_id": 1,
                "status": "ativo",
            },
        )

        st.success("Resposta recebida do Xano!")
        st.json(produtos)

    except Exception as erro:
        st.error(f"Não foi possível consultar os produtos: {erro}")
