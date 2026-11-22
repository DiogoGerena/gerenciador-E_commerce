
import streamlit as st

try:
    from app.xano_client import xano_request
    from app.erp_ui import apply_erp_theme
except ModuleNotFoundError:  # pragma: no cover - compatibilidade com execução direta
    from xano_client import xano_request
    from erp_ui import apply_erp_theme

st.set_page_config(page_title="Teste Xano", page_icon="🔌")

apply_erp_theme()

with st.container(key="erp-xano-test"):
    st.title("Teste de conexão com o Xano")

    if st.button("Consultar produtos", type="primary"):
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
