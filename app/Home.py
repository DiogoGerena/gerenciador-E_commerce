import re

import pandas as pd
import requests
import streamlit as st

from xano_client import (
    criar_produto,
    extrair_id_produto,
    listar_categorias_ativas,
    listar_produtos,
    resolver_categoria_por_nome,
    xano_login,
)


st.set_page_config(
    page_title="Controle Financeiro e Estoque",
    page_icon="📦",
    layout="wide",
)

st.title("📦 Controle Financeiro e Estoque")
st.write(
    "Aplicação de gestão de estoque e análise financeira para e-commerce."
)


# Inicialização da sessão
if "auth_token" not in st.session_state:
    st.session_state["auth_token"] = None

if "auth_user" not in st.session_state:
    st.session_state["auth_user"] = None


def limpar_sessao():
    st.session_state["auth_token"] = None
    st.session_state["auth_user"] = None


def normalizar_perfil(usuario):
    if not isinstance(usuario, dict):
        return None

    perfil = (
        usuario.get("profile")
        or usuario.get("perfil")
        or usuario.get("role")
    )

    if perfil is None:
        return None

    perfil = str(perfil).strip().lower()

    if perfil in {"adm", "admin", "administrator"}:
        return "Adm"

    if perfil in {
        "aux.ecommerce",
        "aux_ecommerce",
        "aux ecommerce",
        "auxiliar ecommerce",
        "auxiliar_ecommerce",
    }:
        return "aux.ecommerce"

    return None


def sessao_autenticada():
    token = st.session_state.get("auth_token")
    usuario = st.session_state.get("auth_user")

    return bool(
        token
        and isinstance(usuario, dict)
        and normalizar_perfil(usuario)
    )


def extrair_produtos(payload):
    """Extrai a lista de produtos dos formatos conhecidos."""
    if isinstance(payload, list):
        return payload

    if isinstance(payload, dict):
        for chave in ("products", "data", "items", "results", "rows"):
            valor = payload.get(chave)

            if isinstance(valor, list):
                return valor

    return []


def exibir_erro_api(erro):
    """Exibe detalhes do erro HTTP sem mostrar o token."""
    resposta = getattr(erro, "response", None)

    if resposta is None:
        st.error("A requisição falhou sem uma resposta HTTP.")
        return

    st.error(
        f"Falha na comunicação com o Xano (HTTP {resposta.status_code})."
    )

    try:
        detalhe = resposta.json()
    except ValueError:
        detalhe = None

    def sanitizar(valor):
        if isinstance(valor, dict):
            dados_sanitizados = {}
            campos_sensiveis = {
                "token",
                "authtoken",
                "accesstoken",
                "password",
                "authorization",
                "secret",
                "apikey",
            }
            for chave, item in valor.items():
                chave_normalizada = str(chave).lower().replace("_", "")
                dados_sanitizados[chave] = (
                    "[redigido]"
                    if chave_normalizada in campos_sensiveis
                    else sanitizar(item)
                )
            return dados_sanitizados

        if isinstance(valor, list):
            return [sanitizar(item) for item in valor]

        if isinstance(valor, str):
            valor = re.sub(
                r"(?i)(bearer\s+)[A-Za-z0-9._~+/-]+=*",
                r"\1[redigido]",
                valor,
            )
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


# Tela de login
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
                    st.error(
                        "O Xano não retornou um token de autenticação."
                    )
                elif not isinstance(usuario, dict):
                    st.error(
                        "O Xano não retornou os dados do usuário."
                    )
                elif not perfil:
                    st.error(
                        "O perfil do usuário está ausente ou não é reconhecido."
                    )
                else:
                    usuario = dict(usuario)
                    usuario["profile"] = perfil

                    st.session_state["auth_token"] = token
                    st.session_state["auth_user"] = usuario

                    st.rerun()

            except requests.HTTPError as erro:
                exibir_erro_api(erro)

            except (ValueError, RuntimeError) as erro:
                st.error(f"Não foi possível autenticar: {erro}")

            except requests.RequestException:
                st.error(
                    "Não foi possível conectar ao Xano. "
                    "Verifique a conexão e as URLs configuradas."
                )

            except Exception:
                st.error(
                    "Ocorreu um erro inesperado durante o login. "
                    "Verifique o terminal para investigar."
                )


# Área autenticada
else:
    usuario = st.session_state["auth_user"]
    perfil = normalizar_perfil(usuario)

    st.success(
        f"Usuário autenticado: "
        f"{usuario.get('email', 'usuário')} — perfil {perfil}"
    )

    if st.button("Sair"):
        limpar_sessao()
        st.rerun()

    pagina = st.radio(
        "Área",
        ("Dashboard", "Produtos"),
        horizontal=True,
        key="area_aplicacao",
    )

    if pagina == "Dashboard":
        from datetime import date

        st.divider()
        st.header("Dashboard")
        st.date_input(
            "Período",
            value=(date.today().replace(day=1), date.today()),
            key="periodo_dashboard",
        )
        st.info(
            "Os indicadores financeiros ainda não estão disponíveis: o cliente "
            "Xano não possui consultas configuradas para vendas, itens vendidos "
            "com custo unitário histórico ou custos de venda. O período escolhido "
            "ainda não pode ser aplicado a dados financeiros."
        )
        st.caption(
            "O CMV será calculado pela quantidade válida vendida multiplicada "
            "pelo custo unitário histórico de cada item, conforme as especificações."
        )
        st.stop()

    st.divider()
    st.header("📦 Produtos")

    mensagem_cadastro = st.session_state.pop(
        "mensagem_cadastro_produto",
        None,
    )
    if mensagem_cadastro:
        st.success(mensagem_cadastro)

    st.subheader("Cadastrar produto")
    categorias_disponiveis = st.session_state.get("categorias_produto_ativas")
    if categorias_disponiveis is None:
        try:
            categorias_disponiveis = listar_categorias_ativas(
                token=st.session_state["auth_token"]
            )
            st.session_state["categorias_produto_ativas"] = categorias_disponiveis
        except requests.HTTPError as erro:
            exibir_erro_api(erro)
            categorias_disponiveis = []
        except requests.RequestException:
            st.error("Falha de conexão ao carregar categorias do Xano.")
            categorias_disponiveis = []
        except ValueError as erro:
            st.warning(str(erro))
            categorias_disponiveis = []
        except Exception:
            st.error("Ocorreu um erro inesperado ao carregar as categorias.")
            categorias_disponiveis = []

    with st.form("cadastro_produto"):
        nome_produto = st.text_input("Nome", key="cadastro_nome_produto")
        descricao_produto = st.text_area(
            "Descrição",
            key="cadastro_descricao_produto",
        )
        sku_produto = st.text_input(
            "SKU (opcional)",
            key="cadastro_sku_produto",
        )
        if categorias_disponiveis:
            nomes_categorias = [categoria["name"] for categoria in categorias_disponiveis]
            nome_categoria_produto = st.selectbox(
                "Categoria",
                options=nomes_categorias,
                key="cadastro_nome_categoria_produto",
            )
            categoria_produto_id = resolver_categoria_por_nome(
                categorias_disponiveis,
                nome_categoria_produto,
            )
        else:
            st.warning("Nenhuma categoria ativa disponível no Xano.")
            categoria_produto_id = None
            st.text_input(
                "Categoria",
                value="Indisponível",
                disabled=True,
                key="cadastro_categoria_indisponivel",
            )
        estoque_minimo_produto = st.number_input(
            "Estoque mínimo",
            min_value=0,
            value=0,
            step=1,
            format="%d",
            key="cadastro_estoque_minimo_produto",
        )
        preco_venda_produto = st.number_input(
            "Preço de venda",
            min_value=0.0,
            value=0.0,
            step=0.01,
            key="cadastro_preco_venda_produto",
        )
        cadastrar = st.form_submit_button("Cadastrar produto")

    if cadastrar:
        if categoria_produto_id is None:
            st.warning(
                "Não foi possível cadastrar: nenhuma categoria ativa está disponível."
            )
        else:
            dados_produto = {
                "name": nome_produto,
                "description": descricao_produto,
                "category_id": int(categoria_produto_id),
                "min_stock": int(estoque_minimo_produto),
                "sale_price": float(preco_venda_produto),
                "sku": sku_produto,
            }
            fingerprint_cadastro = tuple(sorted(dados_produto.items()))

            if st.session_state.get("cadastro_produto_enviando"):
                st.warning("Um cadastro já está sendo enviado.")
            elif (
                st.session_state.get("ultimo_cadastro_produto")
                == fingerprint_cadastro
            ):
                st.warning(
                    "Este mesmo cadastro já foi enviado com sucesso nesta sessão. "
                    "Altere os dados para iniciar outro cadastro."
                )
            else:
                st.session_state["cadastro_produto_enviando"] = True
                try:
                    with st.spinner("Enviando cadastro ao Xano..."):
                        produto_criado = criar_produto(
                            token=st.session_state["auth_token"],
                            **dados_produto,
                        )

                    id_produto = extrair_id_produto(produto_criado)
                    mensagem = "Produto cadastrado com sucesso no Xano."
                    if id_produto is not None:
                        mensagem += f" ID: {id_produto}."

                    st.session_state["ultimo_cadastro_produto"] = (
                        fingerprint_cadastro
                    )
                    st.session_state["mensagem_cadastro_produto"] = mensagem
                    st.session_state["nome_filtro_produto"] = str(
                        dados_produto["name"]
                    ).strip()
                    st.session_state["buscar_produto_cadastrado"] = True
                    st.rerun()

                except ValueError as erro:
                    st.warning(str(erro))

                except requests.HTTPError as erro:
                    exibir_erro_api(erro)

                except requests.RequestException:
                    st.error("Falha de conexão ao cadastrar o produto no Xano.")

                except Exception:
                    st.error("Ocorreu um erro inesperado ao cadastrar o produto.")

                finally:
                    st.session_state["cadastro_produto_enviando"] = False

    # Pesquisa somente pelo nome do produto
    with st.form("filtro_produtos"):
        nome_filtro = st.text_input(
            "Pesquisar por nome do produto",
            placeholder="Digite o nome do produto",
            key="nome_filtro_produto",
        )

        buscar = st.form_submit_button("Buscar")

    buscar_produto_cadastrado = st.session_state.pop(
        "buscar_produto_cadastrado",
        False,
    )

    if buscar or buscar_produto_cadastrado:
        nome = nome_filtro.strip()

        if not nome:
            st.warning(
                "Digite o nome de um produto antes de pesquisar."
            )
        else:
            try:
                payload = listar_produtos(
                    token=st.session_state["auth_token"],
                    name=nome,
                )

                produtos = extrair_produtos(payload)

                if not produtos:
                    st.info(
                        "Nenhum produto encontrado para o nome informado."
                    )
                else:
                    registros = []

                    for item in produtos:
                        if not isinstance(item, dict):
                            continue

                        registros.append(
                            {
                                "ID": item.get("id"),
                                "Nome": (
                                    item.get("name")
                                    or item.get("product_name")
                                ),
                                "SKU": item.get("sku"),
                                "Categoria": item.get("category_id"),
                                "Estoque": item.get("stock_quantity"),
                                "Estoque mínimo": item.get("min_stock"),
                                "Preço de venda": item.get("sale_price"),
                                "Custo médio": item.get("average_cost"),
                                "Situação": item.get("status"),
                            }
                        )

                    if registros:
                        df = pd.DataFrame(registros)

                        st.dataframe(
                            df,
                            use_container_width=True,
                            hide_index=True,
                        )
                    else:
                        st.warning(
                            "A API respondeu, mas não retornou "
                            "registros de produtos em formato válido."
                        )

            except requests.HTTPError as erro:
                exibir_erro_api(erro)

            except requests.RequestException:
                st.error(
                    "Falha de conexão ao consultar produtos no Xano."
                )

            except Exception:
                st.error(
                    "Ocorreu um erro inesperado ao carregar os produtos. "
                    "Verifique o terminal para investigar."
                )