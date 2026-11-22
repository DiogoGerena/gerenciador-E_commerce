import base64
import re
import time
from datetime import date
from pathlib import Path

import pandas as pd
import requests
import streamlit as st

try:
    from app.erp_ui import apply_erp_theme, render_app_shell
    from app.erp_modules import render_module
    from app.xano_client import (
        criar_produto,
        extrair_id_produto,
        listar_categorias_ativas,
        listar_produtos,
        resolver_categoria_por_nome,
        xano_login,
    )
except ModuleNotFoundError:  # pragma: no cover - compatibilidade com execução direta
    from erp_ui import apply_erp_theme, render_app_shell
    from erp_modules import render_module
    from xano_client import (
        criar_produto,
        extrair_id_produto,
        listar_categorias_ativas,
        listar_produtos,
        resolver_categoria_por_nome,
        xano_login,
    )


st.set_page_config(
    page_title="CodBar ERP",
    page_icon="📦",
    layout="wide",
)

apply_erp_theme()

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


def nivel_acesso_perfil(perfil):
    nome = str(perfil or "").strip().lower()
    if nome == "adm":
        return 2
    if nome == "aux.ecommerce":
        return 1
    return 0


def pode_administrar(perfil):
    return nivel_acesso_perfil(perfil) >= 2


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


if "login_stage" not in st.session_state:
    st.session_state["login_stage"] = "welcome"

if "login_error_message" not in st.session_state:
    st.session_state["login_error_message"] = ""

if "clear_login_form" not in st.session_state:
    st.session_state["clear_login_form"] = False

if "clear_login_password" not in st.session_state:
    st.session_state["clear_login_password"] = False

if st.session_state["clear_login_form"]:
    st.session_state["login_email"] = ""
    st.session_state["login_password"] = ""
    st.session_state["clear_login_form"] = False
elif st.session_state["clear_login_password"]:
    st.session_state["login_password"] = ""
    st.session_state["clear_login_password"] = False


def render_login_notice(mensagem, tipo="error"):
    if tipo == "error":
        st.error(mensagem, icon="⚠️")
    else:
        st.info(mensagem)


# Tela de login
if not sessao_autenticada():
    tela_boas_vindas = st.session_state["login_stage"] == "welcome"
    logo_path = Path(__file__).parent / "assets" / "codbar-logo.jpeg"
    logo_base64 = base64.b64encode(logo_path.read_bytes()).decode("ascii")
    boas_vindas_orbitas_svg = """
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 420 280" fill="none">
            <g stroke="#E5B72F" stroke-opacity=".42" stroke-width="2">
                <path d="M92 8C156 96 254 163 326 130C365 112 391 51 420 20"/>
                <path d="M198 0C129 83 105 145 156 176C218 213 333 173 420 118"/>
                <path d="M276 0C222 98 219 180 273 230C327 279 375 166 410 80"/>
                <path d="M142 0C200 74 298 100 420 91"/>
                <path d="M420 157C324 109 259 50 238 0"/>
                <path d="M188 280C229 199 322 103 420 49"/>
                <path d="M420 221C346 201 275 120 249 58C235 24 247 8 264 0"/>
            </g>
            <circle cx="326" cy="130" r="5.5" fill="#E5B72F"/>
        </svg>
    """
    boas_vindas_orbitas_base64 = base64.b64encode(
        boas_vindas_orbitas_svg.encode("utf-8")
    ).decode("ascii")
    orbitas_base64 = boas_vindas_orbitas_base64

    st.markdown(
        """
        <style>
            :root {
                --auth-bg: #F7F7F4;
                --auth-bg: oklch(0.97 0.005 100);
                --auth-surface: #FFFFFF;
                --auth-surface: oklch(1 0 0);
                --auth-accent: #F2C94C;
                --auth-accent: oklch(0.82 0.15 91);
                --auth-accent-hover: #E5B72F;
                --auth-accent-hover: oklch(0.79 0.15 88);
                --auth-text: #242424;
                --auth-text: oklch(0.24 0 0);
                --auth-muted: #686868;
                --auth-muted: oklch(0.53 0 0);
                --auth-border: #E5E5DF;
                --auth-border: oklch(0.93 0.008 100);
                --auth-focus: rgba(155, 120, 14, 0.24);
            }

            html,
            body,
            [data-testid="stAppViewContainer"] {
                min-height: 100%;
                background: var(--auth-bg);
                color: var(--auth-text);
            }

            .stApp {
                position: relative;
                isolation: isolate;
                min-height: 100svh;
                background: var(--auth-bg);
                color: var(--auth-text);
            }

            .stApp:has(.st-key-codbar-welcome-card) {
                background-color: transparent;
                background-image: none;
            }

            [data-testid="stAppViewContainer"]:has(.st-key-codbar-welcome-card),
            [data-testid="stAppViewContainer"]:has(.st-key-codbar-login-card) {
                background-image: url("data:image/svg+xml;base64,{{ORBIT_SVG_BASE64}}");
                background-position: top right;
                background-size: min(420px, 36vw) auto;
                background-repeat: no-repeat;
            }

            [data-testid="stAppViewContainer"]:has(.st-key-codbar-welcome-card) {
                background-attachment: fixed;
            }

            .block-container {
                width: 100%;
                max-width: 100% !important;
                padding: 0 !important;
                margin: 0 !important;
            }

            [data-testid="stMainBlockContainer"] > div[data-testid="stVerticalBlock"] {
                gap: 0 !important;
            }

            header[data-testid="stHeader"],
            div[data-testid="stDecoration"],
            div[data-testid="stToolbar"],
            div[data-testid="stStatusWidget"] {
                display: none !important;
            }

            .st-key-codbar-auth-page {
                width: min(1120px, calc(100% - 48px));
                min-height: 100svh;
                margin: 0 auto;
                display: flex;
                flex-direction: column;
                gap: 0;
            }

            .st-key-codbar-auth-page > [data-testid="stLayoutWrapper"] {
                flex: 1 0 auto;
                display: flex;
                flex-direction: column;
            }

            .codbar-auth-header {
                min-height: 68px;
                display: flex;
                align-items: center;
                color: var(--auth-text);
                font-size: 0.95rem;
                font-weight: 750;
                letter-spacing: 0.01em;
            }

            .codbar-auth-header img {
                transform: scale(1.25);
                transform-origin: left center;
            }

            .st-key-codbar-auth-page:has(.st-key-codbar-welcome-card) .codbar-auth-header img {
                transform: scale(1.5);
            }

            .st-key-codbar-auth-stage {
                flex: 1 0 auto;
                display: grid;
                grid-template-columns: minmax(0, 1fr);
                place-items: center;
                padding: 0;
                box-sizing: border-box;
            }

            .st-key-codbar-auth-stage > [data-testid="stLayoutWrapper"] {
                flex: 1 0 auto;
                width: 100%;
                display: flex;
                align-items: center;
                justify-content: center;
            }

            .st-key-codbar-auth-stage [data-testid="stLayoutWrapper"] {
                width: 100%;
            }

            .st-key-codbar-welcome-card,
            .st-key-codbar-login-card {
                width: min(100%, 470px);
                margin: auto;
                padding: 32px;
                border: 1px solid var(--auth-border);
                border-radius: 18px;
                background: var(--auth-surface);
                box-shadow: 0 14px 36px rgba(36, 36, 36, 0.07);
            }

            .st-key-codbar-login-card {
                padding: 14px 16px;
            }

            .st-key-codbar-login-card [data-testid="stVerticalBlock"] {
                gap: 0.45rem;
            }

            .codbar-welcome-kicker {
                margin-bottom: 12px;
                color: #775B00;
                font-size: 0.72rem;
                font-weight: 800;
                letter-spacing: 0.1em;
                text-transform: uppercase;
            }

            .codbar-auth-heading {
                margin: 0 0 10px;
                color: var(--auth-text);
                font-size: clamp(1.8rem, 3vw, 2.15rem);
                font-weight: 750;
                line-height: 1.15;
                letter-spacing: -0.04em;
            }

            .codbar-auth-copy {
                margin: 0;
                color: var(--auth-muted);
                font-size: 0.96rem;
                line-height: 1.55;
            }

            .st-key-codbar-welcome-card div[data-testid="stButton"] {
                margin-top: 24px;
            }

            .st-key-codbar-login-card div[data-testid="stTextInput"] {
                margin: 0 0 4px;
            }

            .st-key-codbar-login-card div[data-testid="stTextInput"] > label {
                margin-bottom: 6px;
                color: var(--auth-text);
                font-size: 0.82rem;
                font-weight: 650;
            }

            .st-key-codbar-login-card div[data-testid="stTextInput"] input {
                min-height: 42px;
                border: 1px solid var(--auth-border);
                border-radius: 9px;
                background: #fff;
                color: var(--auth-text);
                font-size: 0.94rem;
                transition: border-color 120ms ease, box-shadow 120ms ease;
            }

            .st-key-codbar-login-card div[data-testid="stTextInput"] input::placeholder {
                color: #8A837C;
            }

            .st-key-codbar-login-card div[data-testid="stTextInput"] input:focus {
                border-color: var(--auth-accent);
                box-shadow: 0 0 0 3px var(--auth-focus);
            }

            .st-key-codbar-login-card div[data-testid="stAlert"] {
                margin: 0 0 4px;
                padding: 0;
                border-radius: 9px;
                font-size: 0.84rem;
                line-height: 1.35;
            }

            .st-key-codbar-login-card [data-testid="stAlertContainer"] {
                padding: 0.55rem 0.7rem;
                border-radius: 9px;
            }

            .st-key-codbar-login-card div[data-testid="stButton"] > button,
            .st-key-codbar-login-card div[data-testid="stFormSubmitButton"] > button {
                min-height: 45px;
                border-radius: 9px;
                font-size: 0.9rem;
                font-weight: 700;
                transition: background-color 120ms ease, border-color 120ms ease, box-shadow 120ms ease;
            }

            .st-key-codbar-login-card button[kind="primary"],
            .st-key-codbar-welcome-card button[kind="primary"] {
                border: 1px solid var(--auth-accent);
                background: var(--auth-accent);
                color: var(--auth-text);
            }

            .st-key-codbar-login-card button[kind="primaryFormSubmit"] {
                border: 1px solid var(--auth-accent);
                background: var(--auth-accent);
                color: var(--auth-text);
            }

            .st-key-codbar-login-card button[kind="primary"]:hover,
            .st-key-codbar-welcome-card button[kind="primary"]:hover {
                border-color: var(--auth-accent-hover);
                background: var(--auth-accent-hover);
            }

            .st-key-codbar-login-card button[kind="primaryFormSubmit"]:hover {
                border-color: var(--auth-accent-hover);
                background: var(--auth-accent-hover);
            }

            .st-key-codbar-login-card button[kind="secondary"] {
                border: 1px solid var(--auth-border);
                background: #fff;
                color: var(--auth-text);
            }

            .st-key-codbar-login-card button[kind="secondaryFormSubmit"] {
                border: 1px solid var(--auth-border);
                background: #fff;
                color: var(--auth-text);
            }

            .st-key-codbar-login-card button:focus-visible,
            .st-key-codbar-welcome-card button:focus-visible,
            .st-key-codbar-login-card input:focus-visible {
                outline: 3px solid var(--auth-focus);
                outline-offset: 2px;
            }

            @media (max-width: 640px) {
                .st-key-codbar-auth-page {
                    width: calc(100% - 32px);
                    min-height: 100svh;
                }

                [data-testid="stAppViewContainer"]:has(.st-key-codbar-welcome-card),
                [data-testid="stAppViewContainer"]:has(.st-key-codbar-login-card) {
                    background-size: min(260px, 64vw) auto;
                }

                [data-testid="stAppViewContainer"]:has(.st-key-codbar-welcome-card) {
                    background-attachment: scroll;
                }

                .codbar-auth-header {
                    min-height: 58px;
                }

                .st-key-codbar-auth-stage {
                    padding: 8px 0;
                }

                .st-key-codbar-welcome-card,
                .st-key-codbar-login-card {
                    width: 100%;
                    padding: 20px 16px;
                    box-sizing: border-box;
                }

                .st-key-codbar-login-card div[data-testid="stHorizontalBlock"] {
                    gap: 0.5rem;
                }
            }

            @media (max-height: 700px) and (min-width: 641px) {
                .codbar-auth-header {
                    min-height: 54px;
                }

                .st-key-codbar-auth-stage {
                    padding: 0;
                }

                .st-key-codbar-welcome-card {
                    padding: 24px;
                }

                .st-key-codbar-login-card {
                    padding: 12px 16px;
                }
            }

            @media (prefers-reduced-motion: reduce) {
                *,
                *::before,
                *::after {
                    scroll-behavior: auto !important;
                    transition-duration: 0.01ms !important;
                }

                [data-testid="stAppViewContainer"]:has(.st-key-codbar-welcome-card) {
                    background-attachment: scroll;
                }
            }
        </style>
        """.replace("{{ORBIT_SVG_BASE64}}", orbitas_base64),
        unsafe_allow_html=True,
    )

    with st.container(key="codbar-auth-page"):
        cabecalho_marca = (
            f'<img src="data:image/jpeg;base64,{logo_base64}" alt="Logo CodBar ERP" '
            'style="display:block;width:125px;height:auto;max-height:68px;object-fit:contain;">'
        )
        st.markdown(
            f'<div class="codbar-auth-header">{cabecalho_marca}</div>',
            unsafe_allow_html=True,
        )

        with st.container(key="codbar-auth-stage"):
            if st.session_state["login_stage"] == "welcome":
                with st.container(key="codbar-welcome-card", border=True):
                    st.markdown(
                        '<div class="codbar-welcome-kicker">Gestão para e-commerce</div>'
                        '<h1 class="codbar-auth-heading">Bem-vindo ao CodBar ERP</h1>'
                        '<p class="codbar-auth-copy">Acompanhe finanças, vendas e estoque em uma interface organizada para apoiar a rotina do seu negócio.</p>',
                        unsafe_allow_html=True,
                    )

                    if st.button(
                        "Acessar sistema",
                        key="welcome_login_button",
                        type="primary",
                        use_container_width=True,
                    ):
                        st.session_state["login_stage"] = "login"
                        st.session_state["login_error_message"] = ""
                        st.rerun()
            else:
                with st.container(key="codbar-login-card", border=True):
                    st.markdown(
                        '<h1 class="codbar-auth-heading">Acesse sua conta</h1>'
                        '<p class="codbar-auth-copy">Entre com seu e-mail e senha para continuar.</p>',
                        unsafe_allow_html=True,
                    )

                    with st.form("login_form", clear_on_submit=False):
                        st.text_input(
                            "E-mail",
                            key="login_email",
                            placeholder="seu@email.com",
                            autocomplete="email",
                        )

                        st.text_input(
                            "Senha",
                            key="login_password",
                            type="password",
                            placeholder="Digite sua senha",
                            autocomplete="current-password",
                        )

                        if st.session_state["login_error_message"]:
                            render_login_notice(
                                st.session_state["login_error_message"],
                                "error",
                            )

                        submit_col, back_col = st.columns([3, 1])
                        with submit_col:
                            submitted = st.form_submit_button(
                                "Entrar",
                                key="login_submit",
                                type="primary",
                                use_container_width=True,
                            )
                        with back_col:
                            voltar = st.form_submit_button(
                                "Voltar",
                                key="login_back",
                                type="secondary",
                                use_container_width=True,
                            )

                    if voltar:
                        st.session_state["login_stage"] = "welcome"
                        st.session_state["login_error_message"] = ""
                        st.session_state["clear_login_form"] = True
                        st.rerun()

                    if submitted:
                        email = st.session_state.get("login_email", "")
                        password = st.session_state.get("login_password", "")

                        if not email.strip() or not password:
                            st.session_state["login_error_message"] = (
                                "Informe e-mail e senha para autenticar."
                            )
                            st.session_state["clear_login_password"] = True
                            st.rerun()

                        try:
                            with st.spinner("Autenticando..."):
                                resultado = xano_login(email.strip(), password)
                            token = resultado.get("authToken")
                            usuario = resultado.get("user")
                            perfil = normalizar_perfil(usuario)

                            if not token or not isinstance(usuario, dict) or not perfil:
                                st.session_state["login_error_message"] = (
                                    "E-mail ou senha incorretos. Confira seus dados e tente novamente."
                                )
                                st.session_state["clear_login_password"] = True
                                st.rerun()

                            usuario = dict(usuario)
                            usuario["profile"] = perfil
                            st.session_state["auth_token"] = token
                            st.session_state["auth_user"] = usuario
                            st.session_state["login_stage"] = "login"
                            st.session_state["login_error_message"] = ""
                            st.session_state["clear_login_form"] = True
                            st.rerun()
                        except requests.HTTPError as erro:
                            resposta = getattr(erro, "response", None)
                            status = getattr(resposta, "status_code", None)
                            corpo = ""
                            if resposta is not None:
                                try:
                                    corpo = str(resposta.text or "")
                                except Exception:
                                    corpo = ""
                            mensagem = str(corpo).lower()
                            if (
                                status == 403
                                or "invalid credentials" in mensagem
                                or "error_code_access_denied" in mensagem
                                or "access denied" in mensagem
                            ):
                                st.session_state["login_error_message"] = (
                                    "E-mail ou senha incorretos. Confira seus dados e tente novamente."
                                )
                                st.session_state["clear_login_password"] = True
                                st.rerun()
                            st.session_state["login_error_message"] = (
                                "Não foi possível conectar ao Xano. Verifique sua conexão e tente novamente."
                            )
                            st.rerun()
                        except (ValueError, RuntimeError) as erro:
                            mensagem = str(erro).lower()
                            if (
                                "credencial" in mensagem
                                or "token" in mensagem
                                or "perfil" in mensagem
                            ):
                                st.session_state["login_error_message"] = (
                                    "E-mail ou senha incorretos. Confira seus dados e tente novamente."
                                )
                                st.session_state["clear_login_password"] = True
                            else:
                                st.session_state["login_error_message"] = (
                                    "Não foi possível autenticar. Verifique os dados informados."
                                )
                            st.rerun()
                        except requests.RequestException:
                            st.session_state["login_error_message"] = (
                                "Não foi possível conectar ao Xano. Verifique sua conexão e tente novamente."
                            )
                            st.rerun()
                        except Exception:
                            st.session_state["login_error_message"] = (
                                "Ocorreu um erro inesperado durante o login. Tente novamente."
                            )
                            st.rerun()

# Área autenticada
else:
    usuario = st.session_state["auth_user"]
    perfil = normalizar_perfil(usuario)
    administrador = pode_administrar(perfil)

    def render_conteudo(pagina):
        render_module(pagina)

    render_app_shell(
        page_title="CodBar ERP",
        user_label=usuario.get("email", "Administrador"),
        page_renderer=render_conteudo,
    )
