import re
import time
from datetime import date

import pandas as pd
import requests
import streamlit as st

from xano_client import (
    criar_categoria,
    criar_fornecedor,
    criar_produto,
    ajustar_estoque,
    consultar_venda,
    consultar_metricas_vendas,
    criar_chave_idempotencia_venda,
    editar_categoria,
    editar_fornecedor,
    editar_produto,
    erro_xano_indica_duplicidade,
    extrair_id_produto,
    inativar_categoria,
    inativar_fornecedor,
    inativar_produto,
    listar_categorias,
    listar_fornecedores,
    listar_entradas_estoque,
    listar_movimentacoes,
    listar_produtos,
    listar_vendas,
    nivel_acesso_perfil,
    pode_administrar,
    resolver_categoria_por_nome,
    registrar_devolucao,
    registrar_entrada_estoque,
    registrar_perda_ou_avaria,
    registrar_venda,
    xano_login,
)


st.set_page_config(
    page_title="CodBar - Controle Financeiro e Estoque",
    page_icon="📦",
    layout="wide",
)

st.title("📦 CodBar - Controle Financeiro e Estoque")


for key, default in (
    ("auth_token", None),
    ("auth_user", None),
    ("auth_at", None),
):
    if key not in st.session_state:
        st.session_state[key] = default


def limpar_sessao():
    st.session_state["auth_token"] = None
    st.session_state["auth_user"] = None
    st.session_state["auth_at"] = None


def normalizar_perfil(usuario):
    if not isinstance(usuario, dict):
        return None
    perfil = usuario.get("role") or usuario.get("profile") or usuario.get("perfil")
    nome = str(perfil or "").strip().lower()
    if nome in {"adm", "admin", "administrator"}:
        return "Adm"
    if nome in {
        "aux.ecommerce",
        "aux_ecommerce",
        "aux ecommerce",
        "auxiliar",
        "auxiliar ecommerce",
        "operacional",
    }:
        return "aux.ecommerce"
    if nome in {"member", "membro"}:
        return "member"
    return None


def sessao_autenticada():
    token = st.session_state.get("auth_token")
    usuario = st.session_state.get("auth_user")
    auth_at = st.session_state.get("auth_at")
    if not token or not isinstance(usuario, dict) or normalizar_perfil(usuario) is None:
        return False
    if auth_at is not None and time.time() - float(auth_at) >= 24 * 60 * 60:
        limpar_sessao()
        st.warning("Sua sessão expirou após 24 horas. Entre novamente.")
        return False
    return True


def exibir_erro_api(erro):
    resposta = getattr(erro, "response", None)
    if resposta is None:
        st.error("A requisição falhou sem uma resposta HTTP.")
        return
    st.error(f"Falha na comunicação com o Xano (HTTP {resposta.status_code}).")
    try:
        detalhe = resposta.json()
    except ValueError:
        detalhe = None

    campos_sensiveis = {
        "token",
        "authtoken",
        "accesstoken",
        "password",
        "authorization",
        "secret",
        "apikey",
    }

    def sanitizar(valor):
        if isinstance(valor, dict):
            return {
                str(chave): "[redigido]"
                if str(chave).lower().replace("_", "") in campos_sensiveis
                else sanitizar(item)
                for chave, item in valor.items()
            }
        if isinstance(valor, list):
            return [sanitizar(item) for item in valor]
        if isinstance(valor, str):
            valor = re.sub(r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]+", r"\1[redigido]", valor)
            return re.sub(
                r"(?i)(password|senha|token|authorization)\s*[:=]\s*[^,;\s]+",
                r"\1=[redigido]",
                valor,
            )
        return valor

    detalhe = sanitizar(detalhe)
    if isinstance(detalhe, (dict, list)):
        st.write("**Detalhes retornados pelo Xano:**")
        st.json(detalhe)
    else:
        st.info("O Xano não retornou detalhes estruturados para este erro.")


def extrair_lista(payload, chaves):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for chave in chaves:
            valor = payload.get(chave)
            if isinstance(valor, list):
                return valor
    return []


def confirmar_lista(payload, contexto):
    if payload is None:
        raise ValueError(f"O Xano não respondeu ao consultar {contexto}.")
    if isinstance(payload, (dict, list)):
        return extrair_lista(payload, ("data", "items", "results", "rows"))
    raise ValueError(f"O Xano retornou uma resposta inválida ao consultar {contexto}.")


def id_registro(item):
    if not isinstance(item, dict):
        return None
    for chave in ("id", "category_id", "supplier_id", "product_id"):
        valor = item.get(chave)
        if isinstance(valor, int) and valor > 0:
            return valor
        if isinstance(valor, str) and valor.isdigit():
            return int(valor)
    return None


def formatar_moeda_brl(valor):
    if valor is None:
        return "—"
    inteiro, centavos = f"{valor:,.2f}".split(".")
    return f"R$ {inteiro.replace(',', '.')},{centavos}"


def formatar_percentual(valor):
    if valor is None:
        return "—"
    inteiro, decimais = f"{valor:,.2f}".split(".")
    return f"{inteiro.replace(',', '.')},{decimais}%"


if not sessao_autenticada():
    with st.form("login_form"):
        email = st.text_input("E-mail")
        password = st.text_input("Senha", type="password")
        submitted = st.form_submit_button("Entrar")

    if submitted:
        if not email.strip() or not password:
            st.warning("Informe e-mail e senha para autenticar.")
        else:
            try:
                resultado = xano_login(email.strip(), password)
                token = resultado.get("authToken")
                usuario = resultado.get("user")
                perfil = normalizar_perfil(usuario)
                if not token:
                    st.error("O Xano não retornou um token de autenticação.")
                elif not isinstance(usuario, dict):
                    st.error("O Xano não retornou os dados do usuário.")
                elif perfil is None:
                    st.error("Perfil do usuário ausente ou não reconhecido.")
                elif nivel_acesso_perfil(perfil) < 1:
                    st.error("Este perfil não possui nível operacional.")
                else:
                    usuario = dict(usuario)
                    usuario["role"] = perfil
                    st.session_state["auth_token"] = token
                    st.session_state["auth_user"] = usuario
                    st.session_state["auth_at"] = time.time()
                    st.rerun()
            except requests.HTTPError as erro:
                exibir_erro_api(erro)
            except (ValueError, RuntimeError) as erro:
                st.error(f"Não foi possível autenticar: {erro}")
            except requests.RequestException:
                st.error("Não foi possível conectar ao Xano.")
else:
    usuario = st.session_state["auth_user"]
    perfil = normalizar_perfil(usuario)
    administrador = pode_administrar(perfil)

    st.success(f"Usuário autenticado: {usuario.get('email', 'usuário')} — perfil {perfil}")
    if st.button("Sair"):
        limpar_sessao()
        st.rerun()

    pagina = st.radio(
        "Área",
        ("Dashboard", "Categorias", "Produtos", "Fornecedores", "Estoque", "Vendas"),
        horizontal=True,
        key="area_aplicacao",
    )

    if pagina == "Dashboard":
        st.divider()
        st.header("Dashboard")
        st.subheader("Filtros")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            canal_metricas = st.text_input("Canal", key="sale_filter_channel")
        with col2:
            inicio_metricas = st.date_input(
                "Início",
                value=None,
                key="sale_filter_start",
            )
        with col3:
            fim_metricas = st.date_input(
                "Fim",
                value=None,
                key="sale_filter_end",
            )
        with col4:
            status_metricas = st.text_input(
                "Status (opcional)",
                key="sale_filter_status",
            )

        try:
            with st.spinner("Carregando indicadores financeiros..."):
                metricas = consultar_metricas_vendas(
                    token=st.session_state["auth_token"],
                    sales_channel=canal_metricas,
                    status=status_metricas,
                    start_date=(
                        inicio_metricas.isoformat() if inicio_metricas else None
                    ),
                    end_date=fim_metricas.isoformat() if fim_metricas else None,
                )

            if metricas["sales_count"] == 0:
                st.info("Nenhuma venda encontrada para os filtros selecionados.")

            indicadores = (
                ("Quantidade de vendas", metricas["sales_count"]),
                ("Itens vendidos", metricas["items_count"]),
                ("Faturamento bruto", formatar_moeda_brl(metricas["gross_amount"])),
                ("Descontos", formatar_moeda_brl(metricas["discount_amount"])),
                ("Receita líquida", formatar_moeda_brl(metricas["net_revenue"])),
                ("CMV", formatar_moeda_brl(metricas["total_cmv"])),
                ("Custos adicionais", formatar_moeda_brl(metricas["total_costs"])),
                ("Resultado", formatar_moeda_brl(metricas["result"])),
                ("Margem", formatar_percentual(metricas["profit_margin_percent"])),
                ("Ticket médio", formatar_moeda_brl(metricas["average_ticket"])),
            )
            st.subheader("Indicadores financeiros")
            for inicio in range(0, len(indicadores), 5):
                colunas = st.columns(5)
                for coluna, (rotulo, valor) in zip(
                    colunas,
                    indicadores[inicio : inicio + 5],
                ):
                    with coluna:
                        st.metric(rotulo, valor)
        except requests.HTTPError as erro:
            resposta = getattr(erro, "response", None)
            status_http = getattr(resposta, "status_code", None)
            detalhe_http = f" (HTTP {status_http})" if status_http else ""
            st.error(
                "Não foi possível carregar os indicadores financeiros"
                f"{detalhe_http}. Confirme se GET /sale/metrics está publicado "
                "e acessível no Xano."
            )
        except requests.RequestException:
            st.error(
                "Falha de comunicação ao carregar os indicadores. "
                "Confirme a conexão e a disponibilidade do endpoint no Xano."
            )
        except ValueError as erro:
            st.error(f"Não foi possível carregar os indicadores: {erro}")

    if pagina == "Categorias":
        st.divider()
        st.header("Categorias")
        filtro_status = st.selectbox("Situação", ("ativo", "inativo", "todos"), key="categoria_status")
        try:
            params = {} if filtro_status == "todos" else {"status": filtro_status}
            payload = listar_categorias(token=st.session_state["auth_token"], **params)
            categorias = extrair_lista(payload, ("categories", "data", "items", "results", "rows"))
            if categorias:
                st.dataframe(
                    pd.DataFrame([
                        {
                            "ID": item.get("id"),
                            "Nome": item.get("name"),
                            "Descrição": item.get("description"),
                            "Situação": item.get("status"),
                        }
                        for item in categorias
                        if isinstance(item, dict)
                    ]),
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.info("Nenhuma categoria encontrada.")
        except requests.HTTPError as erro:
            exibir_erro_api(erro)
        except requests.RequestException:
            st.error("Falha de conexão ao listar categorias.")
        except (ValueError, RuntimeError) as erro:
            st.error(str(erro))

        if administrador:
            st.subheader("Cadastrar categoria")
            with st.form("criar_categoria"):
                nome = st.text_input("Nome")
                descricao = st.text_area("Descrição")
                enviar = st.form_submit_button("Cadastrar")
            if enviar:
                try:
                    resposta = criar_categoria(
                        token=st.session_state["auth_token"],
                        name=nome,
                        description=descricao,
                    )
                    if id_registro(resposta if isinstance(resposta, dict) else {}) is not None:
                        st.success("Categoria cadastrada com sucesso.")
                        st.rerun()
                    else:
                        st.error("O Xano não confirmou a criação da categoria.")
                except requests.HTTPError as erro:
                    exibir_erro_api(erro)
                except requests.RequestException:
                    st.error("Falha de conexão ao cadastrar categoria.")
                except (ValueError, RuntimeError) as erro:
                    st.warning(str(erro))

            st.subheader("Editar ou inativar")
            if categorias:
                opcoes = {
                    f"{item.get('id')} - {item.get('name')}": item
                    for item in categorias
                    if isinstance(item, dict) and id_registro(item) is not None
                }
                selecionada = st.selectbox("Categoria", tuple(opcoes), key="categoria_selecionada")
                item = opcoes[selecionada]
                categoria_id = id_registro(item)
                with st.form("editar_categoria"):
                    novo_nome = st.text_input("Nome", value=str(item.get("name") or ""), key="edit_categoria_nome")
                    nova_descricao = st.text_area("Descrição", value=str(item.get("description") or ""), key="edit_categoria_desc")
                    novo_status = st.selectbox("Situação", ("ativo", "inativo"), index=0 if item.get("status") == "ativo" else 1)
                    salvar = st.form_submit_button("Salvar alterações")
                    inativar = st.form_submit_button("Inativar")
                if salvar:
                    try:
                        resposta = editar_categoria(
                            categoria_id,
                            token=st.session_state["auth_token"],
                            name=novo_nome,
                            description=nova_descricao,
                            status=novo_status,
                        )
                        if id_registro(resposta if isinstance(resposta, dict) else {}) is not None:
                            st.success("Categoria editada com sucesso.")
                            st.rerun()
                        else:
                            st.error("O Xano não confirmou a edição da categoria.")
                    except requests.HTTPError as erro:
                        exibir_erro_api(erro)
                    except requests.RequestException:
                        st.error("Falha de conexão ao editar categoria.")
                    except (ValueError, RuntimeError) as erro:
                        st.warning(str(erro))
                if inativar:
                    try:
                        resposta = inativar_categoria(categoria_id, token=st.session_state["auth_token"])
                        if id_registro(resposta if isinstance(resposta, dict) else {}) is not None:
                            st.success("Categoria inativada com sucesso.")
                            st.rerun()
                        else:
                            st.error("O Xano não confirmou a inativação da categoria.")
                    except requests.HTTPError as erro:
                        exibir_erro_api(erro)
                    except requests.RequestException:
                        st.error("Falha de conexão ao inativar categoria.")
                    except (ValueError, RuntimeError) as erro:
                        st.warning(str(erro))

    if pagina == "Produtos":
        st.divider()
        st.header("Produtos")
        nome_filtro = st.text_input("Pesquisar por nome", key="filtro_nome_produto")
        col1, col2 = st.columns(2)
        with col1:
            try:
                categorias = listar_categorias(token=st.session_state["auth_token"], status="ativo")
                categorias = extrair_lista(categorias, ("categories", "data", "items", "results", "rows"))
            except Exception:
                categorias = []
        opcoes_categoria = {"Todas": None}
        opcoes_categoria.update({
            str(item.get("name")): item.get("id")
            for item in categorias
            if isinstance(item, dict) and item.get("id") is not None
        })
        with col1:
            categoria_nome = st.selectbox("Categoria", tuple(opcoes_categoria), key="filtro_categoria_produto")
        with col2:
            status_filtro = st.selectbox("Situação", ("todos", "ativo", "inativo"), key="filtro_status_produto")

        params = {}
        if nome_filtro.strip():
            params["name"] = nome_filtro.strip()
        if opcoes_categoria[categoria_nome] is not None:
            params["category_id"] = opcoes_categoria[categoria_nome]
        if status_filtro != "todos":
            params["status"] = status_filtro

        try:
            payload = listar_produtos(token=st.session_state["auth_token"], **params)
            produtos = extrair_lista(payload, ("products", "data", "items", "results", "rows"))
            if produtos:
                st.dataframe(
                    pd.DataFrame([
                        {
                            "ID": item.get("id"),
                            "Nome": item.get("name"),
                            "SKU": item.get("sku"),
                            "Categoria": item.get("category_id"),
                            "Estoque": item.get("stock_quantity"),
                            "Estoque mínimo": item.get("min_stock"),
                            "Preço": item.get("sale_price"),
                            "Custo médio": item.get("average_cost"),
                            "Situação": item.get("status"),
                        }
                        for item in produtos
                        if isinstance(item, dict)
                    ]),
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.info("Nenhum produto encontrado.")
        except requests.HTTPError as erro:
            exibir_erro_api(erro)
        except requests.RequestException:
            st.error("Falha de conexão ao listar produtos.")
        except (ValueError, RuntimeError) as erro:
            st.error(str(erro))

        if administrador:
            st.subheader("Cadastrar produto")
            if not categorias:
                st.warning("Nenhuma categoria ativa disponível.")
            else:
                with st.form("criar_produto"):
                    nome = st.text_input("Nome")
                    sku = st.text_input("SKU (opcional)")
                    nome_categoria = st.selectbox(
                        "Categoria",
                        [str(item.get("name")) for item in categorias],
                        key="novo_produto_categoria",
                    )
                    preco = st.number_input("Preço de venda", min_value=0.0, step=0.01)
                    estoque_minimo = st.number_input("Estoque mínimo", min_value=0, step=1)
                    enviar = st.form_submit_button("Cadastrar")
                if enviar:
                    try:
                        categoria_id = resolver_categoria_por_nome(categorias, nome_categoria)
                        resposta = criar_produto(
                            token=st.session_state["auth_token"],
                            name=nome,
                            sku=sku,
                            category_id=categoria_id,
                            sale_price=float(preco),
                            min_stock=int(estoque_minimo),
                        )
                        if extrair_id_produto(resposta) is not None:
                            st.success("Produto cadastrado com sucesso.")
                            st.rerun()
                        else:
                            st.error("O Xano não confirmou a criação do produto.")
                    except requests.HTTPError as erro:
                        if erro_xano_indica_duplicidade(erro):
                            st.error(
                                "O Xano recusou o cadastro por duplicidade em um "
                                "campo único. Confira o SKU informado; produtos "
                                "existentes não foram alterados."
                            )
                        else:
                            exibir_erro_api(erro)
                    except requests.RequestException:
                        st.error("Falha de conexão ao cadastrar produto.")
                    except (ValueError, RuntimeError) as erro:
                        st.warning(str(erro))

            st.subheader("Editar ou inativar")
            if produtos:
                opcoes = {
                    f"{item.get('id')} - {item.get('name')}": item
                    for item in produtos
                    if isinstance(item, dict) and id_registro(item) is not None
                }
                selecionado = st.selectbox("Produto", tuple(opcoes), key="produto_selecionado")
                item = opcoes[selecionado]
                produto_id = id_registro(item)
                with st.form("editar_produto"):
                    novo_nome = st.text_input("Nome", value=str(item.get("name") or ""), key="edit_prod_nome")
                    novo_sku = st.text_input("SKU", value=str(item.get("sku") or ""), key="edit_prod_sku")
                    novo_preco = st.number_input(
                        "Preço de venda",
                        min_value=0.0,
                        value=float(item.get("sale_price") or 0),
                        step=0.01,
                        key="edit_prod_preco",
                    )
                    novo_minimo = st.number_input(
                        "Estoque mínimo",
                        min_value=0,
                        value=int(item.get("min_stock") or 0),
                        step=1,
                        key="edit_prod_minimo",
                    )
                    novo_status = st.selectbox(
                        "Situação",
                        ("ativo", "inativo"),
                        index=0 if item.get("status") == "ativo" else 1,
                        key="edit_prod_status",
                    )
                    salvar = st.form_submit_button("Salvar alterações")
                    inativar = st.form_submit_button("Inativar")
                if salvar:
                    try:
                        resposta = editar_produto(
                            produto_id,
                            token=st.session_state["auth_token"],
                            name=novo_nome,
                            sku=novo_sku,
                            sale_price=float(novo_preco),
                            min_stock=int(novo_minimo),
                            status=novo_status,
                        )
                        if id_registro(resposta if isinstance(resposta, dict) else {}) is not None:
                            st.success("Produto editado com sucesso.")
                            st.rerun()
                        else:
                            st.error("O Xano não confirmou a edição do produto.")
                    except requests.HTTPError as erro:
                        exibir_erro_api(erro)
                    except requests.RequestException:
                        st.error("Falha de conexão ao editar produto.")
                    except (ValueError, RuntimeError) as erro:
                        st.warning(str(erro))
                if inativar:
                    try:
                        resposta = inativar_produto(produto_id, token=st.session_state["auth_token"])
                        if id_registro(resposta if isinstance(resposta, dict) else {}) is not None:
                            st.success("Produto inativado com sucesso.")
                            st.rerun()
                        else:
                            st.error("O Xano não confirmou a inativação do produto.")
                    except requests.HTTPError as erro:
                        exibir_erro_api(erro)
                    except requests.RequestException:
                        st.error("Falha de conexão ao inativar produto.")
                    except (ValueError, RuntimeError) as erro:
                        st.warning(str(erro))

    if pagina == "Fornecedores":
        st.divider()
        st.header("Fornecedores")
        status_filtro = st.selectbox("Situação", ("todos", "ativo", "inativo"), key="fornecedor_status")
        try:
            payload = listar_fornecedores(
                token=st.session_state["auth_token"],
                status=status_filtro,
            )
            fornecedores = extrair_lista(payload, ("suppliers", "data", "items", "results", "rows"))
            if fornecedores:
                st.dataframe(
                    pd.DataFrame([
                        {
                            "ID": item.get("id"),
                            "Nome": item.get("name"),
                            "Contato": item.get("contact_name"),
                            "CNPJ": item.get("cnpj"),
                            "E-mail": item.get("email"),
                            "Telefone": item.get("phone"),
                            "Situação": item.get("status"),
                        }
                        for item in fornecedores
                        if isinstance(item, dict)
                    ]),
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.info("Nenhum fornecedor encontrado.")
        except requests.HTTPError as erro:
            exibir_erro_api(erro)
        except requests.RequestException:
            st.error("Falha de conexão ao listar fornecedores.")
        except (ValueError, RuntimeError) as erro:
            st.error(str(erro))

        if administrador:
            st.subheader("Cadastrar fornecedor")
            with st.form("criar_fornecedor"):
                nome = st.text_input("Nome")
                contato = st.text_input("Contato")
                cnpj = st.text_input("CNPJ")
                email = st.text_input("E-mail")
                telefone = st.text_input("Telefone")
                enviar = st.form_submit_button("Cadastrar")
            if enviar:
                try:
                    resposta = criar_fornecedor(
                        token=st.session_state["auth_token"],
                        name=nome,
                        contact_name=contato,
                        cnpj=cnpj,
                        email=email,
                        phone=telefone,
                    )
                    if id_registro(resposta if isinstance(resposta, dict) else {}) is not None:
                        st.success("Fornecedor cadastrado com sucesso.")
                        st.rerun()
                    else:
                        st.error("O Xano não confirmou a criação do fornecedor.")
                except requests.HTTPError as erro:
                    exibir_erro_api(erro)
                except requests.RequestException:
                    st.error("Falha de conexão ao cadastrar fornecedor.")
                except (ValueError, RuntimeError) as erro:
                    st.warning(str(erro))

            st.subheader("Editar ou inativar")
            if fornecedores:
                opcoes = {
                    f"{item.get('id')} - {item.get('name')}": item
                    for item in fornecedores
                    if isinstance(item, dict) and id_registro(item) is not None
                }
                selecionado = st.selectbox("Fornecedor", tuple(opcoes), key="fornecedor_selecionado")
                item = opcoes[selecionado]
                fornecedor_id = id_registro(item)
                with st.form("editar_fornecedor"):
                    novo_nome = st.text_input("Nome", value=str(item.get("name") or ""), key="edit_for_nome")
                    novo_contato = st.text_input("Contato", value=str(item.get("contact_name") or ""), key="edit_for_contato")
                    novo_cnpj = st.text_input("CNPJ", value=str(item.get("cnpj") or ""), key="edit_for_cnpj")
                    novo_email = st.text_input("E-mail", value=str(item.get("email") or ""), key="edit_for_email")
                    novo_telefone = st.text_input("Telefone", value=str(item.get("phone") or ""), key="edit_for_phone")
                    novo_status = st.selectbox(
                        "Situação",
                        ("ativo", "inativo"),
                        index=0 if item.get("status") == "ativo" else 1,
                        key="edit_for_status",
                    )
                    salvar = st.form_submit_button("Salvar alterações")
                    inativar = st.form_submit_button("Inativar")
                if salvar:
                    try:
                        resposta = editar_fornecedor(
                            fornecedor_id,
                            token=st.session_state["auth_token"],
                            name=novo_nome,
                            contact_name=novo_contato,
                            cnpj=novo_cnpj,
                            email=novo_email,
                            phone=novo_telefone,
                            status=novo_status,
                        )
                        if id_registro(resposta if isinstance(resposta, dict) else {}) is not None:
                            st.success("Fornecedor editado com sucesso.")
                            st.rerun()
                        else:
                            st.error("O Xano não confirmou a edição do fornecedor.")
                    except requests.HTTPError as erro:
                        exibir_erro_api(erro)
                    except requests.RequestException:
                        st.error("Falha de conexão ao editar fornecedor.")
                    except (ValueError, RuntimeError) as erro:
                        st.warning(str(erro))
                if inativar:
                    try:
                        resposta = inativar_fornecedor(fornecedor_id, token=st.session_state["auth_token"])
                        if id_registro(resposta if isinstance(resposta, dict) else {}) is not None:
                            st.success("Fornecedor inativado com sucesso.")
                            st.rerun()
                        else:
                            st.error("O Xano não confirmou a inativação do fornecedor.")
                    except requests.HTTPError as erro:
                        exibir_erro_api(erro)
                    except requests.RequestException:
                        st.error("Falha de conexão ao inativar fornecedor.")
                    except (ValueError, RuntimeError) as erro:
                        st.warning(str(erro))

    if pagina == "Estoque":
        st.divider()
        st.header("Estoque")

        try:
            payload_produtos = listar_produtos(token=st.session_state["auth_token"])
            produtos_estoque = extrair_lista(
                payload_produtos,
                ("products", "data", "items", "results", "rows"),
            )
        except requests.HTTPError as erro:
            exibir_erro_api(erro)
            produtos_estoque = []
        except requests.RequestException:
            st.error("Falha de conexão ao carregar produtos.")
            produtos_estoque = []
        except (ValueError, RuntimeError) as erro:
            st.error(str(erro))
            produtos_estoque = []

        try:
            fornecedores_estoque = listar_fornecedores(
                token=st.session_state["auth_token"],
                status="ativo",
            )
        except requests.HTTPError as erro:
            exibir_erro_api(erro)
            fornecedores_estoque = []
        except requests.RequestException:
            st.error("Falha de conexão ao carregar fornecedores.")
            fornecedores_estoque = []
        except (ValueError, RuntimeError) as erro:
            st.error(str(erro))
            fornecedores_estoque = []

        abas = st.tabs([
            "Visão geral",
            "Registrar entrada",
            "Histórico de entradas",
            "Movimentações",
            "Ajustes",
            "Perdas e avarias",
            "Devoluções",
        ])

        with abas[0]:
            st.subheader("Visão geral do estoque")
            produtos_validos = [
                item for item in produtos_estoque
                if isinstance(item, dict)
            ]
            quantidades = []
            baixos = 0
            sem_estoque = 0
            for item in produtos_validos:
                try:
                    quantidade = int(item.get("stock_quantity") or 0)
                    minimo = int(item.get("min_stock") or 0)
                except (TypeError, ValueError):
                    continue
                quantidades.append(quantidade)
                if quantidade == 0:
                    sem_estoque += 1
                if quantidade <= minimo:
                    baixos += 1

            col1, col2, col3 = st.columns(3)
            col1.metric("Produtos", len(produtos_validos))
            col2.metric("Estoque baixo", baixos)
            col3.metric("Sem estoque", sem_estoque)
            st.metric("Itens em estoque", sum(quantidades))

            if produtos_validos:
                st.dataframe(
                    pd.DataFrame([
                        {
                            "ID": item.get("id"),
                            "Nome": item.get("name"),
                            "Saldo": item.get("stock_quantity"),
                            "Estoque mínimo": item.get("min_stock"),
                            "Custo médio": item.get("average_cost"),
                            "Situação": item.get("status"),
                        }
                        for item in produtos_validos
                    ]),
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.info("Nenhum produto disponível para calcular a visão geral.")

        with abas[1]:
            st.subheader("Registrar entrada de mercadorias")
            if not administrador:
                st.warning("Somente perfis Adm e admin podem registrar entradas.")
            elif not produtos_estoque:
                st.warning("Nenhum produto disponível.")
            elif not fornecedores_estoque:
                st.warning("Nenhum fornecedor ativo disponível.")
            else:
                produtos_opcoes = {
                    f"{item.get('id')} - {item.get('name')}": id_registro(item)
                    for item in produtos_estoque
                    if isinstance(item, dict) and id_registro(item) is not None
                }
                fornecedores_opcoes = {
                    f"{item.get('id')} - {item.get('name')}": id_registro(item)
                    for item in fornecedores_estoque
                    if isinstance(item, dict) and id_registro(item) is not None
                }
                with st.form("registrar_entrada_estoque"):
                    produto_nome = st.selectbox(
                        "Produto",
                        tuple(produtos_opcoes),
                        key="entrada_produto",
                    )
                    fornecedor_nome = st.selectbox(
                        "Fornecedor",
                        tuple(fornecedores_opcoes),
                        key="entrada_fornecedor",
                    )
                    quantidade = st.number_input(
                        "Quantidade",
                        min_value=1,
                        step=1,
                        key="entrada_quantidade",
                    )
                    custo_unitario = st.number_input(
                        "Custo unitário de compra",
                        min_value=0.0,
                        step=0.01,
                        key="entrada_custo_unitario",
                    )
                    frete = st.number_input(
                        "Frete de entrada",
                        min_value=0.0,
                        step=0.01,
                        key="entrada_frete",
                    )
                    outros_custos = st.number_input(
                        "Outros custos de aquisição",
                        min_value=0.0,
                        step=0.01,
                        key="entrada_outros_custos",
                    )
                    data_entrada = st.date_input(
                        "Data da entrada",
                        value=date.today(),
                        key="entrada_data",
                    )
                    nota_fiscal = st.text_input(
                        "Número da nota fiscal",
                        key="entrada_nota",
                    )
                    observacoes = st.text_area(
                        "Observações",
                        key="entrada_observacoes",
                    )
                    confirmar_operacao = st.checkbox(
                        "Confirmar o registro desta entrada",
                        key="entrada_confirmar_operacao",
                    )
                    confirmar = st.form_submit_button("Registrar entrada")

                if confirmar and not confirmar_operacao:
                    st.warning("Marque a confirmação antes de enviar a entrada.")
                elif confirmar:
                    try:
                        resposta = registrar_entrada_estoque(
                            token=st.session_state["auth_token"],
                            product_id=produtos_opcoes[produto_nome],
                            supplier_id=fornecedores_opcoes[fornecedor_nome],
                            quantity=int(quantidade),
                            unit_purchase_cost=float(custo_unitario),
                            entry_date=data_entrada.isoformat(),
                            inbound_freight=float(frete),
                            other_acquisition_costs=float(outros_custos),
                            invoice_number=nota_fiscal,
                            notes=observacoes,
                        )
                        st.success("Entrada registrada com sucesso pelo Xano.")
                        st.write(
                            f"Saldo atual: {resposta['stock_quantity']} | "
                            f"Custo médio: {resposta['average_cost']}"
                        )
                        st.rerun()
                    except requests.HTTPError as erro:
                        exibir_erro_api(erro)
                    except requests.RequestException:
                        st.error(
                            "Falha de conexão ao registrar entrada. "
                            "Não tente reenviar automaticamente: confirme o estado no Xano."
                        )
                    except (ValueError, RuntimeError) as erro:
                        st.warning(str(erro))

        with abas[2]:
            st.subheader("Histórico de entradas")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                produto_filtro = st.selectbox(
                    "Produto",
                    ("Todos",) + tuple(
                        f"{item.get('id')} - {item.get('name')}"
                        for item in produtos_estoque
                        if isinstance(item, dict)
                    ),
                    key="entrada_filtro_produto",
                )
            with col2:
                fornecedor_filtro = st.selectbox(
                    "Fornecedor",
                    ("Todos",) + tuple(
                        f"{item.get('id')} - {item.get('name')}"
                        for item in fornecedores_estoque
                        if isinstance(item, dict)
                    ),
                    key="entrada_filtro_fornecedor",
                )
            with col3:
                inicio = st.date_input(
                    "Início",
                    value=None,
                    key="entrada_filtro_inicio",
                )
            with col4:
                fim = st.date_input(
                    "Fim",
                    value=None,
                    key="entrada_filtro_fim",
                )
            try:
                filtros = {}
                if produto_filtro != "Todos":
                    filtros["product_id"] = int(produto_filtro.split(" - ", 1)[0])
                if fornecedor_filtro != "Todos":
                    filtros["supplier_id"] = int(fornecedor_filtro.split(" - ", 1)[0])
                if inicio:
                    filtros["start_date"] = inicio.isoformat()
                if fim:
                    filtros["end_date"] = fim.isoformat()
                pagina_entrada = listar_entradas_estoque(
                    token=st.session_state["auth_token"],
                    page=1,
                    per_page=20,
                    **filtros,
                )
                entradas = pagina_entrada["items"]
                if entradas:
                    st.dataframe(
                        pd.DataFrame([
                            {
                                "ID": item.get("id"),
                                "Produto": (
                                    item.get("product", {}).get("name")
                                    if isinstance(item.get("product"), dict)
                                    else item.get("product_id")
                                ),
                                "Fornecedor": (
                                    item.get("supplier", {}).get("name")
                                    if isinstance(item.get("supplier"), dict)
                                    else item.get("supplier_id")
                                ),
                                "Quantidade": item.get("quantity"),
                                "Custo unitário": item.get("unit_purchase_cost"),
                                "Frete": item.get("inbound_freight"),
                                "Outros custos": item.get("other_acquisition_costs"),
                                "Custo total": item.get("total_acquisition_cost"),
                                "Data": item.get("entry_date"),
                                "Nota fiscal": item.get("invoice_number"),
                            }
                            for item in entradas
                            if isinstance(item, dict)
                        ]),
                        use_container_width=True,
                        hide_index=True,
                    )
                    st.caption(
                        f"Página {pagina_entrada.get('curPage', 1)} de "
                        f"{max(1, ((pagina_entrada.get('total', 0) + 19) // 20))} "
                        f"— {pagina_entrada.get('total', 0)} registro(s)"
                    )
                else:
                    st.info("Nenhuma entrada encontrada.")
            except requests.HTTPError as erro:
                exibir_erro_api(erro)
            except requests.RequestException:
                st.error("Falha de conexão ao consultar entradas.")
            except (ValueError, RuntimeError) as erro:
                st.error(str(erro))

        with abas[3]:
            st.subheader("Movimentações / Kardex")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                produto_mov = st.selectbox(
                    "Produto",
                    ("Todos",) + tuple(
                        f"{item.get('id')} - {item.get('name')}"
                        for item in produtos_estoque
                        if isinstance(item, dict)
                    ),
                    key="mov_filtro_produto",
                )
            with col2:
                tipo_mov = st.selectbox(
                    "Tipo",
                    (
                        "Todos",
                        "entrada",
                        "saida_venda",
                        "ajuste_entrada",
                        "ajuste_saida",
                        "perda",
                        "avaria",
                        "devolucao",
                    ),
                    key="mov_filtro_tipo",
                )
            with col3:
                inicio_mov = st.date_input(
                    "Início",
                    value=None,
                    key="mov_filtro_inicio",
                )
            with col4:
                fim_mov = st.date_input(
                    "Fim",
                    value=None,
                    key="mov_filtro_fim",
                )
            try:
                filtros = {}
                if produto_mov != "Todos":
                    filtros["product_id"] = int(produto_mov.split(" - ", 1)[0])
                if tipo_mov != "Todos":
                    filtros["movement_type"] = tipo_mov
                if inicio_mov:
                    filtros["start_date"] = inicio_mov.isoformat()
                if fim_mov:
                    filtros["end_date"] = fim_mov.isoformat()
                pagina_mov = listar_movimentacoes(
                    token=st.session_state["auth_token"],
                    page=1,
                    per_page=20,
                    **filtros,
                )
                movimentos = pagina_mov.get("movements")
                if movimentos is None:
                    movimentos = pagina_mov.get("items")
                if movimentos:
                    st.dataframe(
                        pd.DataFrame([
                            {
                                "ID": item.get("id"),
                                "Data": item.get("created_at") or item.get("movement_date"),
                                "Produto": (
                                    item.get("product", {}).get("name")
                                    if isinstance(item.get("product"), dict)
                                    else item.get("product_id")
                                ),
                                "Tipo": item.get("movement_type"),
                                "Quantidade": item.get("quantity"),
                                "Saldo anterior": item.get("previous_stock"),
                                "Saldo posterior": item.get("new_stock"),
                                "Custo unitário": item.get("unit_cost"),
                                "Referência": item.get("reference_id"),
                                "Observações": item.get("notes"),
                            }
                            for item in movimentos
                            if isinstance(item, dict)
                        ]),
                        use_container_width=True,
                        hide_index=True,
                    )
                    st.caption(
                        f"Página {pagina_mov.get('curPage', 1)} — "
                        f"{pagina_mov.get('total', len(movimentos))} registro(s)"
                    )
                else:
                    st.info("Nenhuma movimentação encontrada.")
            except requests.HTTPError as erro:
                exibir_erro_api(erro)
            except requests.RequestException:
                st.error("Falha de conexão ao consultar movimentações.")
            except (ValueError, RuntimeError) as erro:
                st.error(str(erro))

        if not administrador:
            with abas[4]:
                st.warning("Somente perfis administrativos podem ajustar estoque.")
            with abas[5]:
                st.warning("Somente perfis administrativos podem registrar perdas ou avarias.")
            with abas[6]:
                st.warning("Somente perfis administrativos podem registrar devoluções.")
        else:
            with abas[4]:
                st.subheader("Ajuste administrativo")
                if produtos_estoque:
                    opcoes = {
                        f"{item.get('id')} - {item.get('name')}": id_registro(item)
                        for item in produtos_estoque
                        if isinstance(item, dict) and id_registro(item) is not None
                    }
                    with st.form("ajuste_estoque"):
                        produto = st.selectbox("Produto", tuple(opcoes))
                        tipo = st.selectbox("Tipo", ("entrada", "saida"))
                        quantidade = st.number_input("Quantidade", min_value=1, step=1)
                        justificativa = st.text_area("Justificativa")
                        confirmar_operacao = st.checkbox(
                            "Confirmar o ajuste antes do envio",
                            key="ajuste_confirmar_operacao",
                        )
                        confirmar = st.form_submit_button("Confirmar ajuste")
                    if confirmar and not confirmar_operacao:
                        st.warning("Marque a confirmação antes de enviar o ajuste.")
                    elif confirmar:
                        try:
                            ajustar_estoque(
                                token=st.session_state["auth_token"],
                                product_id=opcoes[produto],
                                adjustment_type=tipo,
                                quantity=int(quantidade),
                                notes=justificativa,
                            )
                            st.success("Ajuste confirmado pelo Xano.")
                            st.rerun()
                        except requests.HTTPError as erro:
                            exibir_erro_api(erro)
                        except requests.RequestException:
                            st.error("Falha de conexão ao ajustar estoque.")
                        except (ValueError, RuntimeError) as erro:
                            st.warning(str(erro))

            with abas[5]:
                st.subheader("Perdas e avarias")
                if produtos_estoque:
                    opcoes = {
                        f"{item.get('id')} - {item.get('name')}": id_registro(item)
                        for item in produtos_estoque
                        if isinstance(item, dict) and id_registro(item) is not None
                    }
                    with st.form("perda_avaria"):
                        produto = st.selectbox("Produto", tuple(opcoes), key="perda_produto")
                        tipo = st.selectbox("Tipo", ("perda", "avaria"), key="perda_tipo")
                        quantidade = st.number_input(
                            "Quantidade",
                            min_value=1,
                            step=1,
                            key="perda_quantidade",
                        )
                        justificativa = st.text_area(
                            "Justificativa",
                            key="perda_justificativa",
                        )
                        confirmar_operacao = st.checkbox(
                            "Confirmar esta ocorrência antes do envio",
                            key="perda_confirmar_operacao",
                        )
                        confirmar = st.form_submit_button("Confirmar ocorrência")
                    if confirmar and not confirmar_operacao:
                        st.warning("Marque a confirmação antes de registrar a ocorrência.")
                    elif confirmar:
                        try:
                            registrar_perda_ou_avaria(
                                token=st.session_state["auth_token"],
                                product_id=opcoes[produto],
                                movement_type=tipo,
                                quantity=int(quantidade),
                                notes=justificativa,
                            )
                            st.success("Ocorrência confirmada pelo Xano.")
                            st.rerun()
                        except requests.HTTPError as erro:
                            exibir_erro_api(erro)
                        except requests.RequestException:
                            st.error("Falha de conexão ao registrar ocorrência.")
                        except (ValueError, RuntimeError) as erro:
                            st.warning(str(erro))

            with abas[6]:
                st.subheader("Devoluções")
                if produtos_estoque:
                    opcoes = {
                        f"{item.get('id')} - {item.get('name')}": id_registro(item)
                        for item in produtos_estoque
                        if isinstance(item, dict) and id_registro(item) is not None
                    }
                    tipo_devolucao = st.radio(
                        "Tipo",
                        ("Devolução de cliente", "Devolução a fornecedor"),
                        horizontal=True,
                    )
                    with st.form("registrar_devolucao"):
                        produto = st.selectbox(
                            "Produto",
                            tuple(opcoes),
                            key="devolucao_produto",
                        )
                        referencia = st.number_input(
                            "ID da venda original"
                            if tipo_devolucao == "Devolução de cliente"
                            else "ID da entrada original",
                            min_value=1,
                            step=1,
                            key="devolucao_referencia",
                        )
                        quantidade = st.number_input(
                            "Quantidade",
                            min_value=1,
                            step=1,
                            key="devolucao_quantidade",
                        )
                        restock = True
                        if tipo_devolucao == "Devolução de cliente":
                            restock = st.checkbox(
                                "Retornar ao estoque vendável",
                                value=True,
                                key="devolucao_reestoque",
                            )
                        observacoes = st.text_area(
                            "Observações",
                            key="devolucao_observacoes",
                        )
                        confirmar_operacao = st.checkbox(
                            "Confirmar esta devolução antes do envio",
                            key="devolucao_confirmar_operacao",
                        )
                        confirmar = st.form_submit_button("Confirmar devolução")
                    if confirmar and not confirmar_operacao:
                        st.warning("Marque a confirmação antes de registrar a devolução.")
                    elif confirmar:
                        try:
                            registrar_devolucao(
                                token=st.session_state["auth_token"],
                                product_id=opcoes[produto],
                                return_type=(
                                    "cliente"
                                    if tipo_devolucao == "Devolução de cliente"
                                    else "fornecedor"
                                ),
                                reference_id=int(referencia),
                                quantity=int(quantidade),
                                restock_condition=restock,
                                notes=observacoes,
                            )
                            st.success("Devolução confirmada pelo Xano.")
                            st.rerun()
                        except requests.HTTPError as erro:
                            exibir_erro_api(erro)
                        except requests.RequestException:
                            st.error("Falha de conexão ao registrar devolução.")
                        except (ValueError, RuntimeError) as erro:
                            st.warning(str(erro))

    if pagina == "Vendas":
        st.divider()
        st.header("Vendas")
        abas_vendas = st.tabs(["Registrar venda", "Histórico"])

        with abas_vendas[0]:
            st.subheader("Registrar venda")

            if "pending_sale_payload" not in st.session_state:
                st.session_state["pending_sale_payload"] = None
            if "pending_sale_status" not in st.session_state:
                st.session_state["pending_sale_status"] = None

            if st.session_state["pending_sale_payload"] is not None:
                st.warning(
                    "Existe uma operação de venda inconclusiva. "
                    "A chave e o payload original foram preservados."
                )
                st.code(
                    st.session_state["pending_sale_payload"]["idempotency_key"],
                    language="text",
                )
                col_retry, col_discard = st.columns(2)
                with col_retry:
                    tentar_novamente = st.button(
                        "Enviar novamente o mesmo payload",
                        key="sale_retry",
                    )
                with col_discard:
                    descartar = st.button(
                        "Descartar operação inconclusiva",
                        key="sale_discard",
                    )

                if descartar:
                    st.session_state["pending_sale_payload"] = None
                    st.session_state["pending_sale_status"] = None
                    st.rerun()

                if tentar_novamente:
                    try:
                        resposta = registrar_venda(
                            token=st.session_state["auth_token"],
                            payload=st.session_state["pending_sale_payload"],
                        )
                        st.success("Venda confirmada pelo Xano.")
                        st.session_state["pending_sale_payload"] = None
                        st.session_state["pending_sale_status"] = None
                        venda_resultado = resposta.get("sale")
                        if isinstance(venda_resultado, dict):
                            st.json(venda_resultado)
                        else:
                            st.json(resposta)
                    except requests.HTTPError as erro:
                        resposta_http = getattr(erro, "response", None)
                        if resposta_http is not None and resposta_http.status_code == 409:
                            st.error(
                                "Conflito de idempotência: a chave já pertence "
                                "a um payload ou usuário diferente."
                            )
                        else:
                            exibir_erro_api(erro)
                    except requests.RequestException:
                        st.error(
                            "Resultado incerto. Não foi gerada uma nova chave. "
                            "Confirme o estado da venda antes de tentar novamente."
                        )
                    except (ValueError, RuntimeError) as erro:
                        st.warning(str(erro))
            else:
                try:
                    payload_produtos = listar_produtos(
                        token=st.session_state["auth_token"],
                        status="ativo",
                    )
                    produtos_venda = extrair_lista(
                        payload_produtos,
                        ("products", "data", "items", "results", "rows"),
                    )
                except requests.HTTPError as erro:
                    exibir_erro_api(erro)
                    produtos_venda = []
                except requests.RequestException:
                    st.error("Falha de conexão ao carregar produtos.")
                    produtos_venda = []
                except (ValueError, RuntimeError) as erro:
                    st.error(str(erro))
                    produtos_venda = []

                if not produtos_venda:
                    st.warning("Nenhum produto ativo disponível para registrar venda.")
                else:
                    produtos_opcoes = {
                        f"{item.get('id')} - {item.get('name')}": id_registro(item)
                        for item in produtos_venda
                        if isinstance(item, dict) and id_registro(item) is not None
                    }
                    if "sale_item_count" not in st.session_state:
                        st.session_state["sale_item_count"] = 1
                    if "sale_cost_count" not in st.session_state:
                        st.session_state["sale_cost_count"] = 0

                    col_add_item, col_add_cost = st.columns(2)
                    with col_add_item:
                        if st.button("Adicionar item", key="sale_add_item"):
                            st.session_state["sale_item_count"] += 1
                            st.rerun()
                    with col_add_cost:
                        if st.button("Adicionar custo", key="sale_add_cost"):
                            st.session_state["sale_cost_count"] += 1
                            st.rerun()

                    with st.form("registrar_venda"):
                        canal = st.text_input(
                            "Canal de venda",
                            key="sale_channel",
                        )
                        numero_pedido = st.text_input(
                            "Número do pedido (opcional)",
                            key="sale_order_number",
                        )
                        data_venda = st.date_input(
                            "Data da venda (opcional)",
                            value=None,
                            key="sale_date",
                        )
                        observacoes = st.text_area(
                            "Observações (opcional)",
                            key="sale_notes",
                        )

                        itens = []
                        for indice in range(st.session_state["sale_item_count"]):
                            st.markdown(f"**Item {indice + 1}**")
                            produto_nome = st.selectbox(
                                "Produto",
                                tuple(produtos_opcoes),
                                key=f"sale_product_{indice}",
                            )
                            quantidade = st.number_input(
                                "Quantidade",
                                min_value=1,
                                step=1,
                                key=f"sale_quantity_{indice}",
                            )
                            preco = st.number_input(
                                "Preço unitário",
                                min_value=0.0,
                                step=0.01,
                                key=f"sale_price_{indice}",
                            )
                            desconto = st.number_input(
                                "Desconto",
                                min_value=0.0,
                                step=0.01,
                                key=f"sale_discount_{indice}",
                            )
                            itens.append({
                                "product_id": produtos_opcoes[produto_nome],
                                "quantity": int(quantidade),
                                "unit_sale_price": float(preco),
                                "discount_amount": float(desconto),
                            })

                        custos = []
                        tipos_custo = (
                            "embalagem",
                            "comissao_marketplace",
                            "impostos",
                            "frete_saida",
                            "outros",
                        )
                        for indice in range(st.session_state["sale_cost_count"]):
                            st.markdown(f"**Custo adicional {indice + 1}**")
                            tipo_custo = st.selectbox(
                                "Tipo",
                                tipos_custo,
                                key=f"sale_cost_type_{indice}",
                            )
                            valor_custo = st.number_input(
                                "Valor",
                                min_value=0.0,
                                step=0.01,
                                key=f"sale_cost_amount_{indice}",
                            )
                            custos.append({
                                "type": tipo_custo,
                                "amount": float(valor_custo),
                            })

                        confirmar_operacao = st.checkbox(
                            "Confirmar o registro desta venda",
                            key="sale_confirm",
                        )
                        confirmar = st.form_submit_button("Registrar venda")

                    if confirmar and not confirmar_operacao:
                        st.warning("Marque a confirmação antes de enviar a venda.")
                    elif confirmar:
                        chave = criar_chave_idempotencia_venda()
                        payload = {
                            "idempotency_key": chave,
                            "sales_channel": canal,
                            "items": itens,
                        }
                        if numero_pedido:
                            payload["order_number"] = numero_pedido
                        if data_venda is not None:
                            payload["sale_date"] = data_venda.isoformat()
                        if observacoes:
                            payload["notes"] = observacoes
                        if custos:
                            payload["costs"] = custos

                        try:
                            payload = validar_payload_venda(
                                idempotency_key=chave,
                                sales_channel=canal,
                                items=itens,
                                order_number=numero_pedido,
                                sale_date=data_venda.isoformat() if data_venda else None,
                                notes=observacoes,
                                costs=custos,
                            )
                        except (ValueError, RuntimeError) as erro:
                            st.warning(str(erro))
                        else:
                            st.session_state["pending_sale_payload"] = payload
                            st.session_state["pending_sale_status"] = "sending"
                            try:
                                resposta = registrar_venda(
                                    token=st.session_state["auth_token"],
                                    payload=payload,
                                )
                                st.success("Venda confirmada pelo Xano.")
                                st.session_state["pending_sale_payload"] = None
                                st.session_state["pending_sale_status"] = None
                                st.session_state["sale_item_count"] = 1
                                st.session_state["sale_cost_count"] = 0
                                venda_resultado = resposta.get("sale")
                                if isinstance(venda_resultado, dict):
                                    st.json(venda_resultado)
                                else:
                                    st.json(resposta)
                            except requests.HTTPError as erro:
                                resposta_http = getattr(erro, "response", None)
                                if resposta_http is not None and resposta_http.status_code == 409:
                                    st.error(
                                        "Conflito de idempotência. "
                                        "A chave não será regenerada."
                                    )
                                else:
                                    exibir_erro_api(erro)
                            except requests.RequestException:
                                st.error(
                                    "Resultado incerto. Não foi gerada uma nova chave "
                                    "e o payload original foi preservado."
                                )
                            except (ValueError, RuntimeError) as erro:
                                st.warning(str(erro))

        with abas_vendas[1]:
            st.subheader("Histórico de vendas")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                canal_filtro = st.text_input(
                    "Canal",
                    key="sale_filter_channel",
                )
            with col2:
                pedido_filtro = st.text_input(
                    "Número do pedido",
                    key="sale_filter_order",
                )
            with col3:
                inicio_venda = st.date_input(
                    "Início",
                    value=None,
                    key="sale_filter_start",
                )
            with col4:
                fim_venda = st.date_input(
                    "Fim",
                    value=None,
                    key="sale_filter_end",
                )
            status_venda = st.text_input(
                "Status (opcional)",
                key="sale_filter_status",
            )

            try:
                pagina_vendas = listar_vendas(
                    token=st.session_state["auth_token"],
                    sales_channel=canal_filtro,
                    order_number=pedido_filtro,
                    status=status_venda,
                    start_date=inicio_venda.isoformat() if inicio_venda else None,
                    end_date=fim_venda.isoformat() if fim_venda else None,
                    page=1,
                    per_page=20,
                )
                vendas = pagina_vendas.get("items")
                if vendas is None:
                    vendas = pagina_vendas.get("sales")
                if isinstance(vendas, list) and vendas:
                    st.dataframe(
                        pd.DataFrame([
                            {
                                "ID": item.get("id") or item.get("sale_id"),
                                "Canal": item.get("sales_channel"),
                                "Pedido": item.get("order_number"),
                                "Data": item.get("sale_date"),
                                "Status": item.get("status"),
                            }
                            for item in vendas
                            if isinstance(item, dict)
                        ]),
                        use_container_width=True,
                        hide_index=True,
                    )
                    ids_vendas = [
                        item.get("id") or item.get("sale_id")
                        for item in vendas
                        if isinstance(item, dict)
                        and (item.get("id") or item.get("sale_id"))
                    ]
                    if ids_vendas:
                        venda_selecionada = st.selectbox(
                            "Venda para detalhes",
                            ids_vendas,
                            key="sale_detail_id",
                        )
                        if st.button("Consultar detalhes", key="sale_detail_button"):
                            try:
                                detalhe = consultar_venda(
                                    venda_selecionada,
                                    token=st.session_state["auth_token"],
                                )
                                st.subheader("Detalhes da venda")
                                venda_info = detalhe.get("sale")
                                if isinstance(venda_info, dict):
                                    st.json(venda_info)
                                else:
                                    st.json(detalhe)

                                for chave in (
                                    "items",
                                    "costs",
                                    "financial_summary",
                                    "summary",
                                    "gross_amount",
                                    "discounts",
                                    "net_amount",
                                    "cmv",
                                    "costs_amount",
                                    "financial_result",
                                    "margin",
                                ):
                                    if chave in detalhe:
                                        st.write(chave)
                                        st.json(detalhe[chave])
                            except requests.HTTPError as erro:
                                exibir_erro_api(erro)
                            except requests.RequestException:
                                st.error("Falha de conexão ao consultar detalhes.")
                            except (ValueError, RuntimeError) as erro:
                                st.error(str(erro))
                    st.caption(
                        f"Página {pagina_vendas.get('curPage', pagina_vendas.get('page', 1))} "
                        f"— {pagina_vendas.get('total', len(vendas))} registro(s)"
                    )
                else:
                    st.info("Nenhuma venda encontrada.")
            except requests.HTTPError as erro:
                exibir_erro_api(erro)
            except requests.RequestException:
                st.error("Falha de conexão ao consultar vendas.")
            except (ValueError, RuntimeError) as erro:
                st.error(str(erro))
