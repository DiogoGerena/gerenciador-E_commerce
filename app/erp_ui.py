import html
from contextlib import contextmanager

import pandas as pd
import streamlit as st


CSS = """
<style>
:root {
    --bg: #F3F0E8;
    --bg-soft: #FAF5EA;
    --surface: #FFFFFF;
    --surface-alt: #FBF9F4;
    --surface-muted: #F8F4EE;
    --border: #DED8CE;
    --border-strong: #CFC7BA;
    --primary: #C96A2B;
    --primary-strong: #A95335;
    --primary-soft: #F8E7A0;
    --secondary: #F2C94C;
    --text: #302D29;
    --muted: #716B63;
    --success: #71947A;
    --warning: #E4B83F;
    --danger: #DC2626;
    --shadow: rgba(48, 45, 41, 0.06);
}

html, body, [data-testid="stAppViewContainer"] {
    background: var(--bg);
    color: var(--text);
    font-family: "Segoe UI", Arial, sans-serif;
}

.stApp {
    background: var(--bg);
    color: var(--text);
}

.block-container {
    padding-top: 0.35rem !important;
    padding-left: 0.75rem !important;
    padding-right: 0.75rem !important;
    padding-bottom: 0.25rem !important;
    max-width: 100% !important;
}

h1, h2, h3, h4, h5, h6 {
    color: var(--text);
    letter-spacing: -0.02em;
    margin: 0;
}

p {
    margin: 0;
}

.demo-badge {
    display: inline-flex;
    align-items: center;
    padding: 0.25rem 0.55rem;
    border-radius: 999px;
    background: #FFF4E6;
    border: 1px solid #F4D2AE;
    color: var(--primary-strong);
    font-size: 0.64rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-bottom: 0.7rem;
}

.erp-shell {
    display: grid;
    grid-template-columns: 240px minmax(0, 1fr);
    min-height: calc(100vh - 0.5rem);
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 18px;
    overflow: hidden;
    box-shadow: 0 12px 24px rgba(36, 36, 36, 0.04);
}

.erp-sidebar {
    background: linear-gradient(180deg, #FFF9F0 0%, #F8F0E5 100%);
    padding: 1rem 0.8rem 0.9rem;
    border-right: 1px solid var(--border);
}

.erp-brand {
    display: flex;
    align-items: center;
    gap: 0.55rem;
    padding: 0.2rem 0.35rem 0.8rem;
    margin-bottom: 0.8rem;
    border-bottom: 1px solid var(--border);
}

.erp-brand-mark {
    width: 28px;
    height: 28px;
    border-radius: 8px;
    background: rgba(232,117,34,0.12);
    border: 1px solid rgba(232,117,34,0.2);
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--primary-strong);
    font-size: 0.68rem;
    font-weight: 800;
    letter-spacing: 0.06em;
}

.erp-brand-name {
    color: var(--text);
    font-size: 0.74rem;
    font-weight: 800;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}

.erp-nav {
    display: flex;
    flex-direction: column;
    gap: 0.3rem;
}

.erp-nav-button {
    width: 100%;
    border: 1px solid transparent;
    background: transparent;
    color: var(--text);
    border-radius: 10px;
    text-align: left;
    padding: 0.68rem 0.72rem;
    font-size: 0.76rem;
    font-weight: 600;
    transition: all 0.15s ease;
}

.erp-nav-button:hover {
    background: rgba(232,117,34,0.08);
    border-color: rgba(232,117,34,0.15);
}

.erp-nav-button.active {
    background: rgba(232,117,34,0.14);
    border-color: rgba(232,117,34,0.18);
    color: var(--primary-strong);
}

.erp-nav-spacer {
    margin-top: auto;
    padding-top: 0.8rem;
    border-top: 1px solid var(--border);
}

[data-testid="stSidebar"] .stButton > button {
    width: 100%;
    background: transparent;
    border: 1px solid transparent;
    color: var(--text);
    border-radius: 10px;
    padding: 0.68rem 0.72rem;
    text-align: left;
    font-size: 0.76rem;
    font-weight: 600;
    box-shadow: none;
    transition: all 0.15s ease;
}

[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(232,117,34,0.08);
    border-color: rgba(232,117,34,0.15);
    color: var(--primary-strong);
}

[data-testid="stSidebar"] .stButton > button:focus:not(:active) {
    box-shadow: 0 0 0 3px rgba(232,117,34,0.12);
    border-color: rgba(232,117,34,0.18);
}

.erp-main {
    display: flex;
    flex-direction: column;
    min-width: 0;
    background: var(--bg);
}

.erp-topbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    padding: 0.7rem 1rem;
    background: var(--surface);
    border-bottom: 1px solid var(--border);
}

.erp-topbar-title {
    font-size: 0.82rem;
    font-weight: 800;
    color: var(--primary-strong);
    letter-spacing: 0.08em;
    text-transform: uppercase;
}

.erp-topbar-actions {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: 0.75rem;
    flex-wrap: wrap;
}

.erp-search {
    background: var(--surface-alt);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 0.54rem 0.75rem;
    min-width: 220px;
    color: var(--muted);
    font-size: 0.75rem;
}

.erp-pill {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    background: var(--surface-alt);
    border: 1px solid var(--border);
    border-radius: 999px;
    padding: 0.28rem 0.6rem;
    font-size: 0.66rem;
    font-weight: 700;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.06em;
}

.erp-avatar {
    width: 28px;
    height: 28px;
    border-radius: 50%;
    background: var(--primary-soft);
    border: 1px solid #F3D9B9;
    color: var(--primary-strong);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.72rem;
    font-weight: 700;
}

.erp-page {
    padding: 1rem;
    min-width: 0;
}

.erp-breadcrumb {
    display: flex;
    align-items: center;
    gap: 0.35rem;
    color: var(--muted);
    font-size: 0.68rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 0.7rem;
}

.erp-page-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 1rem;
    margin-bottom: 1rem;
    padding: 1rem 1.1rem;
    border: 1px solid var(--border);
    border-radius: 14px;
    background: var(--surface);
    box-shadow: 0 3px 12px rgba(48, 45, 41, 0.025);
}

.erp-page-header h1 {
    font-size: 1.5rem;
    font-weight: 800;
    color: var(--text);
    margin-bottom: 0.2rem;
}

.erp-page-subtitle {
    color: var(--muted);
    font-size: 0.83rem;
}

.erp-button,
.stButton > button {
    border: 1px solid var(--primary);
    background: var(--primary);
    color: #fff;
    padding: 0.62rem 0.9rem;
    border-radius: 10px;
    font-size: 0.76rem;
    font-weight: 700;
    min-height: 36px;
}

.erp-button.secondary,
.stButton button[kind="secondary"] {
    background: var(--surface);
    border: 1px solid var(--border);
    color: var(--text);
}

.erp-button.ghost {
    background: transparent;
    color: var(--text);
    border: 1px solid var(--border);
}

.erp-button.danger {
    background: var(--danger);
    border-color: var(--danger);
}

.erp-panel {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    overflow: hidden;
}

.erp-panel-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem;
    padding: 0.8rem 0.9rem;
    border: 1px solid var(--border);
    border-left: 3px solid var(--primary);
    border-radius: 9px 9px 0 0;
    background: linear-gradient(90deg, #F8E7A0 0%, #FBF9F4 100%);
}

.erp-panel-title {
    font-size: 0.72rem;
    font-weight: 800;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--primary-strong);
}

.erp-panel-body {
    padding: 0.9rem;
}

.erp-kpis {
    display: grid;
    grid-template-columns: repeat(5, minmax(0, 1fr));
    gap: 0.8rem;
    margin-bottom: 1rem;
}

.erp-kpi {
    background: linear-gradient(180deg, #FFFFFF 0%, #FBF9F4 100%);
    border: 1px solid var(--border);
    border-left: 4px solid var(--primary);
    border-radius: 12px;
    padding: 0.8rem 0.85rem;
    min-height: 118px;
    box-shadow: 0 2px 8px rgba(48, 45, 41, 0.025);
}

.erp-kpi-label {
    font-size: 0.65rem;
    color: var(--muted);
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}

.erp-kpi-value {
    font-size: 1.38rem;
    font-weight: 800;
    color: var(--primary-strong);
    line-height: 1.3;
    margin: 0.38rem 0 0.3rem;
}

.erp-kpi-trend {
    font-size: 0.72rem;
    font-weight: 700;
    color: var(--success);
}

.erp-grid {
    display: grid;
    gap: 1rem;
}

.erp-grid.two {
    grid-template-columns: 1.5fr 1fr;
}

.erp-grid.three {
    grid-template-columns: repeat(3, minmax(0, 1fr));
}

.erp-form-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.9rem 1rem;
}

.erp-field {
    display: flex;
    flex-direction: column;
    gap: 0.38rem;
}

.erp-field label {
    font-size: 0.72rem;
    font-weight: 600;
    color: var(--text);
}

.erp-field input,
.erp-field select,
.erp-field textarea {
    width: 100%;
    min-height: 38px;
    border-radius: 10px;
    border: 1px solid var(--border);
    background: var(--surface);
    color: var(--text);
    padding: 0.62rem 0.7rem;
    font: inherit;
}

.erp-field textarea {
    min-height: 88px;
    resize: vertical;
}

.erp-section {
    margin-top: 1rem;
}

.erp-toolbar {
    display: flex;
    align-items: center;
    gap: 0.7rem;
    flex-wrap: wrap;
    margin-bottom: 0.8rem;
}

.erp-filter {
    display: inline-flex;
    align-items: center;
    padding: 0.58rem 0.75rem;
    border: 1px solid var(--border);
    border-radius: 10px;
    background: var(--surface);
    color: var(--muted);
    font-size: 0.75rem;
}

.erp-table-wrap {
    overflow: auto;
}

.erp-table {
    width: 100%;
    border-collapse: collapse;
    min-width: 680px;
}

.erp-table th {
    background: #FFF1B8;
    color: #262626;
    font-size: 0.68rem;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    font-weight: 600;
    padding: 0.72rem 0.75rem;
    border-bottom: 1px solid #E7E7E3;
    text-align: left;
}

.erp-table td {
    padding: 0.72rem 0.75rem;
    border-bottom: 1px solid #E7E7E3;
    font-size: 0.76rem;
    color: var(--text);
}

.erp-table tbody tr:nth-child(odd) td {
    background: #FFFFFF;
}

.erp-table tbody tr:nth-child(even) td {
    background: #F0F0ED;
}

.erp-table tbody tr:hover td {
    background: #FFFBEA;
}

.erp-status {
    display: inline-flex;
    align-items: center;
    padding: 0.24rem 0.5rem;
    border-radius: 999px;
    font-size: 0.66rem;
    font-weight: 700;
    letter-spacing: 0.04em;
    text-transform: uppercase;
}

.erp-status.ok {
    background: rgba(59, 124, 95, 0.08);
    color: var(--success);
}

.erp-status.warn {
    background: rgba(201, 138, 42, 0.08);
    color: var(--warning);
}

.erp-status.alert {
    background: rgba(200, 79, 79, 0.08);
    color: var(--danger);
}

@media (max-width: 980px) {
    .erp-shell {
        grid-template-columns: 1fr;
    }

    .erp-sidebar {
        border-right: none;
        border-bottom: 1px solid rgba(255,255,255,0.08);
    }

    .erp-kpis {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .erp-grid.two,
    .erp-grid.three,
    .erp-form-grid {
        grid-template-columns: 1fr;
    }
}

@media (max-width: 640px) {
    .erp-kpis {
        grid-template-columns: 1fr;
    }

    .erp-page-header {
        flex-direction: column;
        align-items: flex-start;
    }

    .erp-topbar {
        flex-direction: column;
        align-items: flex-start;
    }

    .erp-search {
        min-width: 0;
        width: 100%;
    }
}

.stApp:has(.st-key-erp-app-shell),
.stApp:has(.st-key-erp-xano-test) {
    --bg: #F3F0E8;
    --bg-soft: #FAF8F3;
    --surface: #FFFFFF;
    --surface-alt: #FAF8F3;
    --surface-muted: #F7F4EE;
    --border: #DED8CE;
    --border-strong: #CFC7BA;
    --primary: #C96A2B;
    --primary-strong: #A95320;
    --primary-soft: #F6EED6;
    --secondary: #E8D28A;
    --text: #302D29;
    --muted: #716B63;
    --success: #16A34A;
    --danger: #DC2626;
    background: var(--bg);
    color: var(--text);
}

[data-testid="stAppViewContainer"]:has(.st-key-erp-app-shell),
[data-testid="stAppViewContainer"]:has(.st-key-erp-xano-test) {
    background: #F3F0E8;
}

.stApp:has(.st-key-erp-app-shell) .block-container,
.stApp:has(.st-key-erp-xano-test) .block-container {
    padding: 0.25rem 0.75rem 0.75rem !important;
}

.stApp:has(.st-key-erp-app-shell) [data-testid="stSidebar"] {
    background: #FAF8F3;
    border-right: 1px solid #DED8CE;
}

.stApp:has(.st-key-erp-app-shell) [data-testid="stSidebar"] > div:first-child {
    background: #FAF8F3;
}

.stApp:has(.st-key-erp-app-shell) [data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
    gap: 0.4rem;
}

.stApp:has(.st-key-erp-app-shell) [data-testid="stSidebar"] .erp-brand {
    padding: 0.35rem 0.4rem 0.85rem;
    margin-bottom: 0.65rem;
    border-color: #DED8CE;
}

.stApp:has(.st-key-erp-app-shell) [data-testid="stSidebar"] .erp-brand-mark {
    background: #F6EED6;
    border-color: #E8D28A;
    color: #A95320;
}

.stApp:has(.st-key-erp-app-shell) [data-testid="stSidebar"] .erp-brand-name {
    font-size: 0.82rem;
    letter-spacing: 0.045em;
}

.stApp:has(.st-key-erp-app-shell) [data-testid="stSidebar"] button[data-testid^="stBaseButton-"] {
    min-height: 40px;
    padding: 0.55rem 0.75rem;
    border-radius: 8px;
    font-size: 0.84rem;
    text-align: left;
}

.stApp:has(.st-key-erp-app-shell) [data-testid="stSidebar"] button[data-testid="stBaseButton-primary"] {
    background: #F6EED6;
    border-color: #E8D28A;
    color: #704018;
    box-shadow: inset 3px 0 #C96A2B;
}

.stApp:has(.st-key-erp-app-shell) [data-testid="stSidebar"] button[data-testid="stBaseButton-primary"]:hover {
    background: #E8D28A;
    border-color: #D8C27A;
}

.stApp:has(.st-key-erp-app-shell) [data-testid="stSidebar"] button[data-testid="stBaseButton-secondary"] {
    background: transparent;
    border-color: transparent;
    color: #302D29;
}

.stApp:has(.st-key-erp-app-shell) [data-testid="stSidebar"] button[data-testid="stBaseButton-secondary"]:hover {
    background: #FAF8F3;
    border-color: #DED8CE;
    color: #A95320;
}

.st-key-erp-app-shell {
    min-height: calc(100vh - 1rem);
    color: var(--text);
}

.st-key-erp-xano-test {
    max-width: 960px;
    margin: 1rem auto;
    padding: 1.5rem;
    color: var(--text);
    background: #FAF8F3;
    border: 1px solid #DED8CE;
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(48, 45, 41, 0.035);
}

.st-key-erp-xano-test > [data-testid="stVerticalBlock"] {
    gap: 0.8rem;
}

.st-key-erp-xano-test h1 {
    font-size: clamp(1.4rem, 2vw, 1.75rem);
    line-height: 1.25;
    color: #302D29;
}

.st-key-erp-xano-test button[data-testid^="stBaseButton-"] {
    min-height: 40px;
    border-radius: 7px;
    font-size: 0.9rem;
}

.st-key-erp-xano-test button[data-testid="stBaseButton-primary"] {
    background: #C96A2B;
    border-color: #C96A2B;
    color: #FFFFFF;
}

.st-key-erp-xano-test button[data-testid^="stBaseButton-"]:focus-visible {
    outline: 3px solid rgba(201, 106, 43, 0.28);
    outline-offset: 2px;
}

.st-key-erp-xano-test button[data-testid="stBaseButton-primary"]:hover {
    background: #A95320;
    border-color: #A95320;
}

.st-key-erp-app-shell > [data-testid="stVerticalBlock"] {
    gap: 0 !important;
}

.st-key-erp-app-shell .erp-topbar {
    min-height: 56px;
    padding: 0.6rem 1.25rem;
    background: linear-gradient(90deg, #F2C94C 0%, #F8E7A0 35%, #FBF9F4 100%);
    border-bottom-color: #DED8CE;
    box-shadow: 0 1px 3px rgba(48, 45, 41, 0.04);
}

.st-key-erp-app-shell .erp-topbar-title {
    color: #302D29;
    font-size: 0.9rem;
    letter-spacing: 0.015em;
    text-transform: none;
}

.st-key-erp-app-shell .erp-search {
    background: #FFFFFF;
    border-color: #DED8CE;
    color: #716B63;
}

.st-key-erp-app-shell .erp-pill {
    background: #FAF8F3;
    border-color: #DED8CE;
    color: #716B63;
}

.st-key-erp-app-shell .erp-user {
    display: flex;
    align-items: center;
    gap: 0.55rem;
    color: #302D29;
    font-size: 0.78rem;
    font-weight: 600;
}

.st-key-erp-app-shell .erp-avatar {
    flex: 0 0 32px;
    width: 32px;
    height: 32px;
    background: #F6EED6;
    border-color: #E8D28A;
    color: #A95320;
}

.st-key-erp-page {
    margin: 0.85rem 1rem 1rem;
    padding: 1.1rem 1.25rem 1.35rem;
    min-width: 0;
    background: linear-gradient(180deg, #FBF9F4 0%, #F7F3ED 100%);
    border: 1px solid #DED8CE;
    border-radius: 14px;
    box-shadow: 0 2px 8px rgba(48, 45, 41, 0.035);
}

.st-key-erp-page > [data-testid="stVerticalBlock"] {
    gap: 0.8rem;
}

.st-key-erp-page .demo-badge {
    margin-bottom: 0;
    background: #F6EED6;
    border-color: #E8D28A;
    color: #704018;
}

.st-key-erp-page-header {
    padding-bottom: 0.75rem;
    border-bottom: 1px solid #DED8CE;
}

.st-key-erp-page-header > [data-testid="stVerticalBlock"] {
    gap: 0.3rem;
}

.st-key-erp-page-header .erp-breadcrumb {
    margin-bottom: 0.1rem;
    color: #716B63;
}

.st-key-erp-page-header h1 {
    font-size: clamp(1.35rem, 2vw, 1.7rem);
    line-height: 1.25;
    font-weight: 700;
    color: #302D29;
}

.st-key-erp-page-header .erp-page-subtitle {
    color: #716B63;
    font-size: 0.9rem;
    line-height: 1.45;
}

.st-key-erp-page-header [data-testid="stHorizontalBlock"] {
    align-items: center;
    gap: 0.6rem;
}

.st-key-erp-page .erp-panel-header {
    padding: 0.7rem 0.85rem;
    background: #FAF8F3;
    border: 1px solid #DED8CE;
    border-left: 3px solid #C96A2B;
    border-radius: 8px;
}

.st-key-erp-page .erp-panel-title {
    color: #302D29;
    font-size: 0.77rem;
    letter-spacing: 0.035em;
}

.st-key-erp-page .erp-kpi {
    border-color: #DED8CE;
    border-radius: 10px;
    box-shadow: 0 1px 3px rgba(48, 45, 41, 0.035);
}

.st-key-erp-page .erp-kpi-label,
.st-key-erp-page .erp-kpi-trend {
    letter-spacing: 0.035em;
}

.st-key-erp-page [data-testid="stDataFrame"],
.st-key-erp-page [data-testid="stVegaLiteChart"],
.st-key-erp-page [data-testid="stArrowVegaLiteChart"],
.st-key-erp-page [data-testid="stLineChart"],
.st-key-erp-page [data-testid="stBarChart"] {
    border: 1px solid #DED8CE;
    border-radius: 8px;
    background: #F7F4EE;
}

.st-key-erp-page [data-testid="stTextInput"] input,
.st-key-erp-page [data-testid="stNumberInput"] input,
.st-key-erp-page [data-testid="stDateInput"] input,
.st-key-erp-page [data-testid="stTextArea"] textarea,
.st-key-erp-page [data-baseweb="select"] > div {
    border-color: #DED8CE;
    border-radius: 7px;
    background: #F7F4EE;
}

.st-key-erp-page [data-testid="stTextInput"] input,
.st-key-erp-page [data-testid="stNumberInput"] input,
.st-key-erp-page [data-testid="stDateInput"] input,
.st-key-erp-page [data-testid="stTextArea"] textarea,
.st-key-erp-page [data-baseweb="select"] [role="combobox"] {
    color: #302D29 !important;
    color-scheme: light;
    caret-color: #C96A2B;
}

.st-key-erp-page [data-testid="stTextInput"] input::placeholder,
.st-key-erp-page [data-testid="stNumberInput"] input::placeholder,
.st-key-erp-page [data-testid="stDateInput"] input::placeholder,
.st-key-erp-page [data-testid="stTextArea"] textarea::placeholder {
    color: #716B63 !important;
    opacity: 1;
}

.st-key-erp-page [data-testid="stSelectbox"] [role="group"],
.st-key-erp-page [data-testid="stMultiSelect"] [role="group"] {
    background: #F7F4EE;
    border: 1px solid #DED8CE;
    border-radius: 7px;
}

.st-key-erp-page [data-testid="stSelectbox"] [role="combobox"],
.st-key-erp-page [data-testid="stMultiSelect"] [role="combobox"] {
    background: transparent !important;
    border: 0 !important;
    color: #302D29 !important;
}

.st-key-erp-page [data-testid="stSelectbox"] button[aria-label="Open"],
.st-key-erp-page [data-testid="stMultiSelect"] button[aria-label="Open"] {
    color: #716B63;
}

.st-key-erp-page [data-testid="stWidgetLabel"],
.st-key-erp-page [data-testid="stWidgetLabel"] * {
    color: #302D29 !important;
}

.st-key-erp-page [data-testid="stTextInput"] input:focus,
.st-key-erp-page [data-testid="stNumberInput"] input:focus,
.st-key-erp-page [data-testid="stDateInput"] input:focus,
.st-key-erp-page [data-testid="stTextArea"] textarea:focus {
    border-color: #C96A2B;
    box-shadow: 0 0 0 2px rgba(201, 106, 43, 0.18);
}

.st-key-erp-page button[data-testid^="stBaseButton-"] {
    min-height: 40px;
    border-radius: 7px;
    font-size: 0.84rem;
    font-weight: 650;
}

.st-key-erp-page button[data-testid="stBaseButton-primary"] {
    background: #C96A2B;
    border-color: #C96A2B;
    color: #FFFFFF;
}

.st-key-erp-page button[data-testid="stBaseButton-secondary"] {
    background: #FFFFFF;
    border-color: #DED8CE;
    color: #302D29;
}

.st-key-erp-page button[data-testid="stBaseButton-secondary"]:hover {
    background: #FAF8F3;
    border-color: #CFC7BA;
}

.st-key-erp-page button[data-testid="stBaseButton-tertiary"] {
    background: #E8D28A;
    border-color: #E8D28A;
    color: #302D29;
}

.st-key-erp-page button[data-testid^="stBaseButton-"]:focus-visible,
.stApp:has(.st-key-erp-app-shell) [data-testid="stSidebar"] button[data-testid^="stBaseButton-"]:focus-visible {
    outline: 3px solid rgba(201, 106, 43, 0.28);
    outline-offset: 2px;
}

.st-key-erp-page button[data-testid="stBaseButton-primary"]:hover {
    background: #A95320;
    border-color: #A95320;
}

.st-key-erp-page button[data-testid="stBaseButton-tertiary"]:hover {
    background: #D8C27A;
    border-color: #D8C27A;
}

.st-key-erp-page button[data-testid^="stBaseButton-"]:active:not(:disabled),
.stApp:has(.st-key-erp-app-shell) [data-testid="stSidebar"] button[data-testid^="stBaseButton-"]:active:not(:disabled),
.st-key-erp-xano-test button[data-testid^="stBaseButton-"]:active:not(:disabled) {
    transform: translateY(1px);
}

.st-key-erp-page button[data-testid^="stBaseButton-"]:disabled {
    background: #EEE8DE;
    border-color: #DED8CE;
    color: #716B63;
}

.st-key-erp-page button[data-testid^="stBaseButton-"],
.stApp:has(.st-key-erp-app-shell) [data-testid="stSidebar"] button[data-testid^="stBaseButton-"],
.st-key-erp-xano-test button[data-testid^="stBaseButton-"] {
    min-width: 6rem;
    padding: 0.55rem 0.9rem;
    transition: color 0.15s ease, background-color 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease;
}

.st-key-erp-page button[data-testid="stBaseButton-elementToolbar"] {
    min-width: 40px;
    min-height: 40px;
    padding: 0.35rem;
    border-radius: 7px;
    background: transparent;
    border-color: transparent;
    color: #716B63;
}

.st-key-erp-page button[data-testid="stBaseButton-elementToolbar"]:hover {
    background: #FAF8F3;
    border-color: #DED8CE;
    color: #A95320;
}

.st-key-erp-page button[data-testid="stBaseButton-elementToolbar"]:focus-visible {
    outline: 3px solid rgba(201, 106, 43, 0.28);
    outline-offset: 2px;
}

.st-key-erp-page button[data-testid^="stBaseButton-"]:active:not(:disabled),
.stApp:has(.st-key-erp-app-shell) [data-testid="stSidebar"] button[data-testid^="stBaseButton-"]:active:not(:disabled),
.st-key-erp-xano-test button[data-testid^="stBaseButton-"]:active:not(:disabled) {
    transform: none;
}

.st-key-erp-page [data-testid="stTextInput"] input:disabled,
.st-key-erp-page [data-testid="stNumberInput"] input:disabled,
.st-key-erp-page [data-testid="stDateInput"] input:disabled,
.st-key-erp-page [data-testid="stTextArea"] textarea:disabled {
    background: #EEE8DE;
    color: #716B63;
}

.st-key-erp-page [data-testid="stSelectbox"] [aria-disabled="true"],
.st-key-erp-page [data-testid="stMultiSelect"] [aria-disabled="true"] {
    background: #EEE8DE;
    color: #716B63;
}

.st-key-erp-page [data-baseweb="select"] > div,
.st-key-erp-page [data-baseweb="select"] [role="combobox"] {
    color: #302D29;
}

.stApp:has(.st-key-erp-app-shell) [data-baseweb="popover"],
.stApp:has(.st-key-erp-xano-test) [data-baseweb="popover"],
body:has(.st-key-erp-app-shell) [data-baseweb="popover"],
body:has(.st-key-erp-xano-test) [data-baseweb="popover"] {
    color-scheme: light;
}

body:has(.st-key-erp-app-shell) [data-testid="stSelectboxVirtualDropdown"],
body:has(.st-key-erp-xano-test) [data-testid="stSelectboxVirtualDropdown"] {
    background: #FFFFFF !important;
    border: 1px solid #DED8CE !important;
    border-radius: 8px;
    box-shadow: 0 6px 18px rgba(41, 37, 33, 0.12);
    color: #302D29 !important;
    color-scheme: light;
}

body:has(.st-key-erp-app-shell) [data-testid="stSelectboxVirtualDropdown"] [role="listbox"],
body:has(.st-key-erp-xano-test) [data-testid="stSelectboxVirtualDropdown"] [role="listbox"] {
    background: #FFFFFF !important;
    color: #302D29 !important;
}

body:has(.st-key-erp-app-shell) [data-testid="stSelectboxVirtualDropdown"] [role="option"],
body:has(.st-key-erp-xano-test) [data-testid="stSelectboxVirtualDropdown"] [role="option"] {
    background: #FFFFFF !important;
    color: #302D29 !important;
}

body:has(.st-key-erp-app-shell) [data-testid="stSelectboxVirtualDropdown"] [role="option"]:hover,
body:has(.st-key-erp-xano-test) [data-testid="stSelectboxVirtualDropdown"] [role="option"]:hover {
    background: #FAF8F3 !important;
}

body:has(.st-key-erp-app-shell) [data-testid="stSelectboxVirtualDropdown"] [aria-selected="true"],
body:has(.st-key-erp-xano-test) [data-testid="stSelectboxVirtualDropdown"] [aria-selected="true"] {
    background: #F6EED6 !important;
    color: #704018 !important;
}

body:has(.st-key-erp-app-shell) [data-testid="stDateInputCalendar"],
body:has(.st-key-erp-xano-test) [data-testid="stDateInputCalendar"] {
    background: #FFFFFF !important;
    border: 1px solid #DED8CE !important;
    border-radius: 8px;
    box-shadow: 0 6px 18px rgba(41, 37, 33, 0.12);
    color: #302D29 !important;
    color-scheme: light;
}

body:has(.st-key-erp-app-shell) [data-testid="stDateInputCalendar"] button,
body:has(.st-key-erp-xano-test) [data-testid="stDateInputCalendar"] button {
    background: transparent;
    border-color: transparent;
    color: #302D29 !important;
}

body:has(.st-key-erp-app-shell) [data-testid="stDateInputCalendar"] button:hover,
body:has(.st-key-erp-xano-test) [data-testid="stDateInputCalendar"] button:hover {
    background: #FAF8F3;
}

body:has(.st-key-erp-app-shell) [data-testid="stDateInputCalendar"] th,
body:has(.st-key-erp-xano-test) [data-testid="stDateInputCalendar"] th {
    color: #716B63 !important;
}

body:has(.st-key-erp-app-shell) [data-testid="stDateInputCalendar"] [aria-selected="true"],
body:has(.st-key-erp-xano-test) [data-testid="stDateInputCalendar"] [aria-selected="true"] {
    background: #C96A2B !important;
    color: #FFFFFF !important;
}

.stApp:has(.st-key-erp-app-shell) [data-baseweb="popover"] [role="listbox"],
.stApp:has(.st-key-erp-xano-test) [data-baseweb="popover"] [role="listbox"],
body:has(.st-key-erp-app-shell) [data-baseweb="popover"] [role="listbox"],
body:has(.st-key-erp-xano-test) [data-baseweb="popover"] [role="listbox"] {
    background: #FFFFFF;
    border: 1px solid #DED8CE;
    border-radius: 8px;
    box-shadow: 0 6px 18px rgba(41, 37, 33, 0.12);
    color: #302D29;
}

.stApp:has(.st-key-erp-app-shell) [data-baseweb="popover"] [role="option"],
.stApp:has(.st-key-erp-xano-test) [data-baseweb="popover"] [role="option"],
body:has(.st-key-erp-app-shell) [data-baseweb="popover"] [role="option"],
body:has(.st-key-erp-xano-test) [data-baseweb="popover"] [role="option"] {
    background: #FFFFFF;
    color: #302D29;
}

.stApp:has(.st-key-erp-app-shell) [data-baseweb="popover"] [role="option"]:hover,
.stApp:has(.st-key-erp-xano-test) [data-baseweb="popover"] [role="option"]:hover,
body:has(.st-key-erp-app-shell) [data-baseweb="popover"] [role="option"]:hover,
body:has(.st-key-erp-xano-test) [data-baseweb="popover"] [role="option"]:hover {
    background: #FAF8F3;
}

.stApp:has(.st-key-erp-app-shell) [data-baseweb="popover"] [aria-selected="true"],
.stApp:has(.st-key-erp-xano-test) [data-baseweb="popover"] [aria-selected="true"],
body:has(.st-key-erp-app-shell) [data-baseweb="popover"] [aria-selected="true"],
body:has(.st-key-erp-xano-test) [data-baseweb="popover"] [aria-selected="true"] {
    background: #F6EED6;
    color: #704018;
}

.st-key-erp-page [data-testid="stDataFrame"] {
    color-scheme: light;
    --gdg-bg-cell: #FFFFFF;
    --gdg-bg-cell-medium: #FAF8F3;
    --gdg-bg-header: #F3F0E8;
    --gdg-bg-header-hover: #F2EBDD;
    --gdg-bg-header-has-focus: #F6EED6;
    --gdg-bg-search-result: #F6EED6;
    --gdg-border-color: #DED8CE;
    --gdg-horizontal-border-color: #DED8CE;
    --gdg-text-dark: #302D29;
    --gdg-text-medium: #716B63;
    --gdg-text-light: #716B63;
    --gdg-text-bubble: #302D29;
    --gdg-accent-color: #C96A2B;
    --gdg-link-color: #A95320;
    --gdg-font-family: "Segoe UI", Arial, sans-serif;
}

.st-key-erp-page [data-testid="stVegaLiteChart"] svg,
.st-key-erp-page [data-testid="stArrowVegaLiteChart"] svg {
    background: #FAF8F3 !important;
    color-scheme: light;
}

.st-key-erp-page [data-testid="stVegaLiteChart"] svg text,
.st-key-erp-page [data-testid="stArrowVegaLiteChart"] svg text {
    fill: #302D29 !important;
}

.st-key-erp-page [data-testid="stVegaLiteChart"] svg .role-axis-grid line,
.st-key-erp-page [data-testid="stArrowVegaLiteChart"] svg .role-axis-grid line {
    stroke: #DED8CE !important;
}

.st-key-erp-page [data-testid="stVegaLiteChart"] svg .role-axis-domain,
.st-key-erp-page [data-testid="stArrowVegaLiteChart"] svg .role-axis-domain {
    stroke: #CFC7BA !important;
}

.st-key-erp-page [data-testid="stDataFrame"] [data-testid="glideDataEditor"],
.st-key-erp-page [data-testid="stDataFrame"] canvas {
    color-scheme: light;
}

.st-key-erp-page [data-testid="stDataFrame"] button,
.st-key-erp-page [data-testid="stVegaLiteChart"] button,
.st-key-erp-page [data-testid="stArrowVegaLiteChart"] button,
.st-key-erp-page [data-testid="stLineChart"] button,
.st-key-erp-page [data-testid="stBarChart"] button {
    color: #302D29;
}

.st-key-erp-page [data-testid="stAlert"] {
    border-radius: 8px;
}

.st-key-erp-page [data-testid="stAlert"][kind="success"],
.st-key-erp-xano-test [data-testid="stAlert"][kind="success"] {
    border-left: 3px solid #16A34A;
}

.st-key-erp-page [data-testid="stAlert"][kind="error"],
.st-key-erp-xano-test [data-testid="stAlert"][kind="error"] {
    border-left: 3px solid #DC2626;
}

.st-key-erp-page [data-testid="stAlert"][kind="warning"],
.st-key-erp-xano-test [data-testid="stAlert"][kind="warning"] {
    border-left: 3px solid #D97706;
}

@media (max-width: 760px) {
    .st-key-erp-xano-test {
        margin: 0.55rem 0.35rem;
        padding: 0.85rem 0.75rem 1rem;
        border-radius: 9px;
    }

    .st-key-erp-page {
        margin: 0.55rem 0.35rem;
        padding: 0.85rem 0.75rem 1rem;
        border-radius: 9px;
    }

    .st-key-erp-app-shell .erp-topbar {
        padding: 0.7rem 0.85rem;
    }

    .st-key-erp-app-shell .erp-topbar-actions {
        width: 100%;
        justify-content: flex-start;
        gap: 0.5rem;
    }

    .st-key-erp-app-shell .erp-search {
        min-width: 0;
        flex: 1 1 100%;
    }
}

@media (max-width: 980px) {
    .st-key-erp-page [data-testid="stHorizontalBlock"] {
        flex-wrap: wrap;
        align-items: flex-start;
    }

    .st-key-erp-page [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
        flex: 1 1 280px !important;
        min-width: min(100%, 280px);
        width: auto !important;
    }

    .st-key-erp-page [data-testid="stDataFrame"] {
        max-width: 100%;
    }
}

:root {
    color-scheme: light;
    --cb-bg: #F7F7F4;
    --cb-bg: oklch(0.97 0.005 100);
    --cb-surface: #FFFFFF;
    --cb-surface: oklch(1 0 0);
    --cb-surface-muted: #F8F8F6;
    --cb-surface-muted: oklch(0.98 0.003 100);
    --cb-border: #E5E5DF;
    --cb-border: oklch(0.93 0.008 100);
    --cb-border-strong: #D7D7CE;
    --cb-border-strong: oklch(0.88 0.01 100);
    --cb-text: #242424;
    --cb-text: oklch(0.24 0 0);
    --cb-muted: #6B6B66;
    --cb-muted: oklch(0.54 0.005 100);
    --cb-yellow: #F2C94C;
    --cb-yellow: oklch(0.82 0.15 91);
    --cb-yellow-strong: #E5B72F;
    --cb-yellow-strong: oklch(0.79 0.15 88);
    --cb-yellow-soft: #FFF7D8;
    --cb-yellow-soft: oklch(0.98 0.04 98);
    --cb-green: #25764D;
    --cb-green: oklch(0.52 0.13 157);
    --cb-red: #B42318;
    --cb-red: oklch(0.48 0.18 29);
    --cb-shadow: 0 8px 24px rgba(32, 32, 24, 0.06);
    --cb-radius-sm: 8px;
    --cb-radius-md: 12px;
    --cb-radius-lg: 16px;
}

.stApp:has(.st-key-erp-app-shell) {
    --bg: var(--cb-bg);
    --surface: var(--cb-surface);
    --surface-muted: var(--cb-surface-muted);
    --border: var(--cb-border);
    --text: var(--cb-text);
    --muted: var(--cb-muted);
    --primary: var(--cb-yellow);
    --primary-strong: var(--cb-yellow-strong);
    background: var(--cb-bg) !important;
    color: var(--cb-text);
}

.stApp:has(.st-key-erp-app-shell) [data-testid="stAppViewContainer"],
.stApp:has(.st-key-erp-app-shell) [data-testid="stMain"] {
    background: var(--cb-bg) !important;
}

.stApp:has(.st-key-erp-app-shell) [data-testid="stHeader"] {
    background: rgba(247, 247, 244, 0.92);
}

.stApp:has(.st-key-erp-app-shell) [data-testid="stSidebar"] {
    background: var(--cb-surface) !important;
    border-right: 1px solid var(--cb-border);
    box-shadow: 4px 0 16px rgba(32, 32, 24, 0.025);
}

.stApp:has(.st-key-erp-app-shell) [data-testid="stSidebar"] > div:first-child {
    background: var(--cb-surface) !important;
}

.stApp:has(.st-key-erp-app-shell) .main .block-container {
    max-width: 1680px;
    padding: 1.15rem clamp(0.9rem, 2.3vw, 2rem) 2.25rem;
}

.stApp:has(.st-key-erp-app-shell) [data-testid="stSidebar"] .erp-brand {
    gap: 0.72rem;
    margin: 0.25rem 0 1.45rem;
}

.stApp:has(.st-key-erp-app-shell) [data-testid="stSidebar"] .erp-brand-mark {
    width: 2.55rem;
    height: 2.55rem;
    border-radius: 0.85rem;
    background: var(--cb-yellow);
    color: var(--cb-text);
    box-shadow: 0 4px 10px rgba(184, 142, 17, 0.16);
    font-weight: 850;
}

.stApp:has(.st-key-erp-app-shell) [data-testid="stSidebar"] .erp-brand-name {
    color: var(--cb-text);
    font-size: 1.12rem;
    font-weight: 780;
    letter-spacing: -0.035em;
}

.stApp:has(.st-key-erp-app-shell) [data-testid="stSidebar"] .erp-nav-heading {
    margin: 1rem 0 0.35rem;
    color: var(--cb-muted);
    font-size: 0.67rem;
    font-weight: 750;
    letter-spacing: 0.095em;
    text-transform: uppercase;
}

.stApp:has(.st-key-erp-app-shell) [data-testid="stSidebar"] [data-testid="stButton"] {
    margin: 0.08rem 0;
}

.stApp:has(.st-key-erp-app-shell) [data-testid="stSidebar"] [data-testid="stButton"] button {
    min-height: 2.55rem;
    justify-content: flex-start;
    border: 1px solid transparent;
    border-radius: var(--cb-radius-sm);
    box-shadow: none;
    font-weight: 580;
    text-align: left;
    transition: background-color 140ms ease, border-color 140ms ease;
}

.stApp:has(.st-key-erp-app-shell) [data-testid="stSidebar"] [data-testid="stButton"] button[kind="secondary"] {
    background: transparent;
    color: #4F4F49;
}

.stApp:has(.st-key-erp-app-shell) [data-testid="stSidebar"] [data-testid="stButton"] button[kind="secondary"]:hover {
    background: var(--cb-surface-muted);
    border-color: var(--cb-border);
    color: var(--cb-text);
}

.stApp:has(.st-key-erp-app-shell) [data-testid="stSidebar"] [data-testid="stButton"] button[kind="primary"] {
    background: var(--cb-yellow);
    border-color: var(--cb-yellow);
    color: var(--cb-text);
    font-weight: 720;
}

.stApp:has(.st-key-erp-app-shell) [data-testid="stSidebar"] button[data-testid="stBaseButton-primary"] {
    background: var(--cb-yellow) !important;
    border-color: var(--cb-yellow) !important;
    color: var(--cb-text) !important;
}

.stApp:has(.st-key-erp-app-shell) [data-testid="stSidebar"] button[data-testid="stBaseButton-primary"]:hover {
    background: var(--cb-yellow-strong) !important;
    border-color: var(--cb-yellow-strong) !important;
}

.stApp:has(.st-key-erp-app-shell) [data-testid="stSidebar"] .erp-account-card {
    display: flex;
    align-items: center;
    gap: 0.7rem;
    margin: 1.1rem 0 0.5rem;
    padding: 0.75rem;
    border: 1px solid var(--cb-border);
    border-radius: var(--cb-radius-md);
    background: var(--cb-surface-muted);
}

.stApp:has(.st-key-erp-app-shell) [data-testid="stSidebar"] .erp-account-avatar {
    display: grid;
    width: 2.2rem;
    height: 2.2rem;
    flex: 0 0 auto;
    place-items: center;
    border-radius: 50%;
    background: var(--cb-yellow-soft);
    color: #5B4700;
    font-size: 0.82rem;
    font-weight: 750;
}

.stApp:has(.st-key-erp-app-shell) [data-testid="stSidebar"] .erp-account-name {
    overflow: hidden;
    color: var(--cb-text);
    font-size: 0.8rem;
    font-weight: 650;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.stApp:has(.st-key-erp-app-shell) [data-testid="stSidebar"] .erp-account-role {
    margin-top: 0.1rem;
    color: var(--cb-muted);
    font-size: 0.7rem;
}

.st-key-erp-app-shell .erp-topbar {
    min-height: 4rem;
    margin-bottom: 1rem;
    padding: 0.85rem 1.15rem;
    border: 1px solid var(--cb-border);
    border-radius: var(--cb-radius-md);
    background: var(--cb-surface);
    box-shadow: 0 2px 8px rgba(32, 32, 24, 0.025);
}

.st-key-erp-app-shell .erp-topbar-title {
    color: var(--cb-text);
    font-size: 0.98rem;
    font-weight: 700;
    letter-spacing: -0.015em;
}

.st-key-erp-app-shell .erp-topbar-subtitle {
    margin-top: 0.12rem;
    color: var(--cb-muted);
    font-size: 0.76rem;
}

.st-key-erp-page {
    margin: 0.45rem 0 1rem;
    padding: clamp(1rem, 2vw, 1.75rem);
    border: 1px solid var(--cb-border);
    border-radius: var(--cb-radius-lg);
    background: var(--cb-surface);
    box-shadow: var(--cb-shadow);
}

.st-key-erp-page h1,
.st-key-erp-page h2,
.st-key-erp-page h3,
.st-key-erp-page h4 {
    color: var(--cb-text);
    letter-spacing: -0.025em;
}

.st-key-erp-page p,
.st-key-erp-page label,
.st-key-erp-page [data-testid="stMarkdownContainer"] {
    color: var(--cb-text);
}

.st-key-erp-page .stCaption,
.st-key-erp-page [data-testid="stCaptionContainer"] {
    color: var(--cb-muted);
}

.st-key-erp-page [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"] {
    scroll-margin-top: 1rem;
}

.st-key-erp-page [data-testid="stForm"] {
    padding: clamp(0.85rem, 1.6vw, 1.3rem);
    border: 1px solid var(--cb-border);
    border-radius: var(--cb-radius-md);
    background: var(--cb-surface);
}

.st-key-erp-page [data-testid="stTextInput"] input,
.st-key-erp-page [data-testid="stNumberInput"] input,
.st-key-erp-page [data-testid="stTextArea"] textarea,
.st-key-erp-page [data-testid="stDateInput"] input,
.st-key-erp-page [data-testid="stSelectbox"] [data-baseweb="select"] > div,
.st-key-erp-page [data-testid="stMultiSelect"] [data-baseweb="select"] > div {
    border-color: var(--cb-border-strong);
    border-radius: var(--cb-radius-sm);
    background: var(--cb-surface);
}

.st-key-erp-page [data-testid="stTextInput"] input:focus,
.st-key-erp-page [data-testid="stNumberInput"] input:focus,
.st-key-erp-page [data-testid="stTextArea"] textarea:focus,
.st-key-erp-page [data-testid="stDateInput"] input:focus {
    border-color: #9B780E;
    box-shadow: 0 0 0 1px #9B780E;
}

.st-key-erp-page [data-testid="stButton"] button,
.st-key-erp-page [data-testid="stFormSubmitButton"] button,
[data-testid="stDialog"] [data-testid="stButton"] button {
    min-height: 2.45rem;
    border-radius: var(--cb-radius-sm);
    font-weight: 650;
    transition: transform 120ms ease, box-shadow 120ms ease, background-color 120ms ease;
}

.st-key-erp-page [data-testid="stButton"] button[kind="primary"],
.st-key-erp-page [data-testid="stFormSubmitButton"] button[kind="primary"],
[data-testid="stDialog"] [data-testid="stButton"] button[kind="primary"] {
    border-color: var(--cb-yellow);
    background: var(--cb-yellow);
    color: var(--cb-text);
    box-shadow: 0 2px 4px rgba(128, 99, 14, 0.12);
}

.st-key-erp-page button[data-testid="stBaseButton-primary"],
.st-key-erp-page button[data-testid="stBaseButton-primaryFormSubmit"],
[data-testid="stDialog"] button[data-testid="stBaseButton-primary"] {
    border-color: var(--cb-yellow) !important;
    background: var(--cb-yellow) !important;
    color: var(--cb-text) !important;
}

.st-key-erp-page [data-testid="stButton"] button[kind="primary"]:hover,
.st-key-erp-page [data-testid="stFormSubmitButton"] button[kind="primary"]:hover,
[data-testid="stDialog"] [data-testid="stButton"] button[kind="primary"]:hover {
    border-color: var(--cb-yellow-strong);
    background: var(--cb-yellow-strong);
    box-shadow: 0 4px 10px rgba(128, 99, 14, 0.16);
    transform: translateY(-1px);
}

.st-key-erp-page button[data-testid="stBaseButton-primary"]:hover,
.st-key-erp-page button[data-testid="stBaseButton-primaryFormSubmit"]:hover,
[data-testid="stDialog"] button[data-testid="stBaseButton-primary"]:hover {
    border-color: var(--cb-yellow-strong) !important;
    background: var(--cb-yellow-strong) !important;
    color: var(--cb-text) !important;
}

.st-key-erp-page [data-testid="stButton"] button[kind="secondary"],
.st-key-erp-page [data-testid="stFormSubmitButton"] button[kind="secondary"],
[data-testid="stDialog"] [data-testid="stButton"] button[kind="secondary"] {
    border-color: var(--cb-border-strong);
    background: var(--cb-surface);
    color: var(--cb-text);
}

.st-key-erp-page [data-testid="stButton"] button:focus-visible,
.st-key-erp-page [data-testid="stFormSubmitButton"] button:focus-visible {
    outline: 3px solid rgba(155, 120, 14, 0.35);
    outline-offset: 2px;
}

.st-key-erp-page [data-testid="stMetric"] {
    min-height: 6rem;
    padding: 1rem;
    border: 1px solid var(--cb-border);
    border-radius: var(--cb-radius-md);
    background: var(--cb-surface);
    box-shadow: 0 2px 7px rgba(32, 32, 24, 0.025);
}

.st-key-erp-page [data-testid="stMetricLabel"] {
    color: var(--cb-muted);
    font-weight: 560;
}

.st-key-erp-page [data-testid="stMetricValue"] {
    color: var(--cb-text);
    font-weight: 740;
    letter-spacing: -0.04em;
}

.st-key-erp-page [data-testid="stDataFrame"] {
    overflow: hidden;
    border: 1px solid var(--cb-border);
    border-radius: var(--cb-radius-md);
    background: var(--cb-surface);
    --gdg-bg-cell: #FFFFFF;
    --gdg-bg-cell-medium: #FAFAF8;
    --gdg-bg-header: #F5F5F1;
    --gdg-bg-header-hover: #EFEFE8;
    --gdg-bg-header-has-focus: #FFF4C9;
    --gdg-bg-search-result: #FFF4C9;
    --gdg-border-color: #E5E5DF;
    --gdg-horizontal-border-color: #E5E5DF;
    --gdg-text-dark: #242424;
    --gdg-text-medium: #6B6B66;
    --gdg-text-light: #6B6B66;
    --gdg-text-bubble: #242424;
    --gdg-accent-color: #E5B72F;
    --gdg-link-color: #775B00;
    --gdg-font-family: "Segoe UI", Arial, sans-serif;
}

.st-key-erp-page [data-testid="stDataFrame"] [data-testid="data-grid-canvas"] {
    --gdg-bg-cell: #FFFFFF !important;
    --gdg-bg-cell-medium: #FAFAF8 !important;
    --gdg-bg-header: #F5F5F1 !important;
    --gdg-bg-header-hover: #EFEFE8 !important;
    --gdg-bg-header-has-focus: #FFF4C9 !important;
    --gdg-bg-search-result: #FFF4C9 !important;
    --gdg-border-color: #E5E5DF !important;
    --gdg-horizontal-border-color: #E5E5DF !important;
    --gdg-text-dark: #242424 !important;
    --gdg-text-medium: #6B6B66 !important;
    --gdg-text-light: #6B6B66 !important;
    --gdg-text-bubble: #242424 !important;
    --gdg-accent-color: #E5B72F !important;
    --gdg-link-color: #775B00 !important;
}

.st-key-erp-page [data-testid="stVegaLiteChart"],
.st-key-erp-page [data-testid="stArrowVegaLiteChart"],
.st-key-erp-page [data-testid="stLineChart"],
.st-key-erp-page [data-testid="stBarChart"] {
    overflow: hidden;
    border: 1px solid var(--cb-border);
    border-radius: var(--cb-radius-md);
    background: var(--cb-surface);
}

.st-key-erp-page [data-testid="stVegaLiteChart"] svg,
.st-key-erp-page [data-testid="stArrowVegaLiteChart"] svg {
    background: var(--cb-surface) !important;
}

.st-key-erp-page [data-testid="stVegaLiteChart"] svg text,
.st-key-erp-page [data-testid="stArrowVegaLiteChart"] svg text {
    fill: #4F4F49 !important;
}

.st-key-erp-page [data-testid="stVegaLiteChart"] svg .role-axis-grid line,
.st-key-erp-page [data-testid="stArrowVegaLiteChart"] svg .role-axis-grid line {
    stroke: var(--cb-border) !important;
}

.st-key-erp-page [data-testid="stAlert"] {
    border: 1px solid var(--cb-border);
    border-radius: var(--cb-radius-md);
}

.st-key-erp-page [data-testid="stAlert"][kind="success"] {
    border-left: 4px solid var(--cb-green);
}

.st-key-erp-page [data-testid="stAlert"][kind="warning"] {
    border-left: 4px solid #9A6700;
}

.st-key-erp-page [data-testid="stAlert"][kind="error"] {
    border-left: 4px solid var(--cb-red);
}

body:has(.st-key-erp-app-shell) [data-testid="stSelectboxVirtualDropdown"] [aria-selected="true"] {
    background: var(--cb-yellow-soft) !important;
    color: #5B4700 !important;
}

body:has(.st-key-erp-app-shell) [data-testid="stDateInputCalendar"] [aria-selected="true"] {
    background: var(--cb-yellow) !important;
    color: var(--cb-text) !important;
}

.st-key-erp-page .erp-panel-header,
.st-key-erp-page [class*="erp-panel-header"] {
    border-bottom-color: var(--cb-border);
}

.st-key-erp-page .erp-panel-title {
    color: var(--cb-text);
    font-weight: 700;
}

[data-testid="stDialog"] [role="dialog"] {
    border: 1px solid var(--cb-border);
    border-radius: var(--cb-radius-lg);
    background: var(--cb-surface);
    box-shadow: 0 24px 70px rgba(24, 24, 20, 0.2);
}

[data-testid="stDialog"] [role="dialog"] p,
[data-testid="stDialog"] [role="dialog"] strong,
[data-testid="stDialog"] [role="dialog"] [data-testid="stMarkdownContainer"] {
    color: var(--cb-text) !important;
}

[data-testid="stToast"] {
    border: 1px solid var(--cb-border);
    border-left: 4px solid var(--cb-yellow-strong);
    border-radius: var(--cb-radius-md);
    background: var(--cb-surface);
    box-shadow: var(--cb-shadow);
}

.cb-skeleton {
    display: block;
    overflow: hidden;
    border-radius: var(--cb-radius-sm);
    background: linear-gradient(90deg, #F0F0EB 25%, #FAFAF7 45%, #F0F0EB 65%);
    background-size: 240% 100%;
    animation: cb-skeleton-shimmer 1.35s ease-in-out infinite;
}

.cb-skeleton-row {
    height: 0.85rem;
    margin: 0.9rem 0;
}

.cb-skeleton-card {
    height: 6rem;
    border: 1px solid var(--cb-border);
    border-radius: var(--cb-radius-md);
}

.cb-skeleton-table {
    height: 17rem;
    border: 1px solid var(--cb-border);
    border-radius: var(--cb-radius-md);
}

@keyframes cb-skeleton-shimmer {
    to { background-position: -240% 0; }
}

@media (prefers-reduced-motion: reduce) {
    .cb-skeleton {
        animation: none;
    }

    .st-key-erp-page [data-testid="stButton"] button,
    .st-key-erp-page [data-testid="stFormSubmitButton"] button {
        transition: none;
    }
}

@media (max-width: 760px) {
    .stApp:has(.st-key-erp-app-shell) .main .block-container {
        padding: 0.65rem 0.55rem 1.25rem;
    }

    .st-key-erp-page {
        margin: 0.35rem 0 0.75rem;
        padding: 0.9rem 0.75rem 1.1rem;
        border-radius: var(--cb-radius-md);
    }

    .st-key-erp-app-shell .erp-topbar {
        min-height: 3.5rem;
        padding: 0.7rem 0.8rem;
    }
}

[data-testid="stDataFrame"],
[data-testid="stDataEditor"] {
    overflow-x: auto !important;
    overscroll-behavior-x: contain;
    touch-action: pan-x pan-y;
    color-scheme: light !important;
    --gdg-bg-cell: #FFFFFF;
    --gdg-bg-cell-medium: #F0F0ED;
    --gdg-bg-header: #FFF1B8;
    --gdg-bg-header-hover: #FFF0BF;
    --gdg-bg-header-has-focus: #FFF0BF;
    --gdg-bg-search-result: #FFF1B8;
    --gdg-border-color: #E7E7E3;
    --gdg-horizontal-border-color: #E7E7E3;
    --gdg-text-dark: #262626;
    --gdg-text-medium: #707070;
    --gdg-text-light: #707070;
    --gdg-text-bubble: #262626;
    --gdg-accent-color: #D7AA16;
    --gdg-link-color: #775B00;
    --gdg-font-family: "Segoe UI", Arial, sans-serif;
}

[data-testid="stDataFrame"] [data-testid="data-grid-canvas"],
[data-testid="stDataEditor"] [data-testid="data-grid-canvas"],
[data-testid="stDataFrame"] [data-testid="glideDataEditor"],
[data-testid="stDataEditor"] [data-testid="glideDataEditor"] {
    color-scheme: light !important;
    --gdg-bg-cell: #FFFFFF !important;
    --gdg-bg-cell-medium: #F0F0ED !important;
    --gdg-bg-header: #FFF1B8 !important;
    --gdg-bg-header-hover: #FFF0BF !important;
    --gdg-bg-header-has-focus: #FFF0BF !important;
    --gdg-bg-search-result: #FFF1B8 !important;
    --gdg-border-color: #E7E7E3 !important;
    --gdg-horizontal-border-color: #E7E7E3 !important;
    --gdg-text-dark: #262626 !important;
    --gdg-text-medium: #707070 !important;
    --gdg-text-light: #707070 !important;
    --gdg-text-bubble: #262626 !important;
    --gdg-accent-color: #D7AA16 !important;
    --gdg-link-color: #775B00 !important;
}

[data-testid="stDataFrame"] canvas,
[data-testid="stDataEditor"] canvas {
    color-scheme: light !important;
}

[data-testid="stTable"] {
    max-width: 100%;
    overflow-x: auto;
    overscroll-behavior-x: contain;
    touch-action: pan-x pan-y;
    scrollbar-color: #D8D5CB #FAFAF7;
    scrollbar-width: thin;
}

[data-testid="stTable"] table {
    background: #FFFFFF;
    color: #262626;
    border-collapse: separate;
    border-spacing: 0;
}

[data-testid="stTable"] thead th {
    position: sticky;
    top: 0;
    z-index: 1;
    background: #FFF1B8;
    color: #262626;
    border-bottom: 1px solid #E7E7E3;
}

[data-testid="stTable"] tbody tr:nth-child(odd) td {
    background: #FFFFFF;
}

[data-testid="stTable"] tbody tr:nth-child(even) td {
    background: #F0F0ED;
}

[data-testid="stTable"] tbody tr:hover td {
    background: #FFFBEA;
}

.st-key-erp-app-shell .erp-topbar {
    position: sticky;
    top: 0;
    z-index: 40;
}

.cb-status-badge {
    display: inline-flex;
    align-items: center;
    min-height: 1.65rem;
    padding: 0.2rem 0.65rem;
    border: 1px solid transparent;
    border-radius: 999px;
    font-size: 0.78rem;
    font-weight: 650;
    line-height: 1.2;
}

.cb-status-badge.is-active {
    border-color: #B9DDC3;
    background: #EAF6ED;
    color: #28643A;
}

.cb-status-badge.is-inactive {
    border-color: #E7D7D2;
    background: #F7EEEB;
    color: #7A4236;
}

.cb-status-badge.is-neutral {
    border-color: #E7DCA9;
    background: #FFF8DE;
    color: #6A5600;
}

@supports (animation-timeline: view()) {
    @media (prefers-reduced-motion: no-preference) {
        .st-key-erp-page [data-testid="stMetric"],
        .st-key-erp-page [data-testid="stVegaLiteChart"],
        .st-key-erp-page [data-testid="stArrowVegaLiteChart"],
        .st-key-erp-page [data-testid="stLineChart"],
        .st-key-erp-page [data-testid="stBarChart"] {
            animation: cb-scroll-reveal linear both;
            animation-timeline: view();
            animation-range: entry 0% entry 24%;
        }

        @keyframes cb-scroll-reveal {
            from {
                opacity: 0.82;
                transform: translateY(8px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
    }
}

@supports (animation-timeline: scroll(root block)) {
    @media (prefers-reduced-motion: no-preference) {
        .stApp:has(.st-key-erp-app-shell)::after {
            position: fixed;
            z-index: 999;
            top: 0;
            left: 0;
            width: 100%;
            height: 3px;
            background: #F2C94C;
            content: "";
            pointer-events: none;
            transform: scaleX(0);
            transform-origin: left center;
            animation: cb-scroll-progress auto linear;
            animation-timeline: scroll(root block);
        }

        @keyframes cb-scroll-progress {
            to {
                transform: scaleX(1);
            }
        }
    }
}

@media (prefers-reduced-motion: reduce) {
    .st-key-erp-page [data-testid="stMetric"],
    .st-key-erp-page [data-testid="stVegaLiteChart"],
    .st-key-erp-page [data-testid="stArrowVegaLiteChart"],
    .st-key-erp-page [data-testid="stLineChart"],
    .st-key-erp-page [data-testid="stBarChart"] {
        animation: none !important;
        transform: none !important;
    }
}

@media (max-width: 760px) {
    .st-key-erp-app-shell .erp-topbar {
        top: 0;
    }
}

.stApp button[data-testid^="stBaseButton-"],
[data-testid="stDialog"] button[data-testid^="stBaseButton-"] {
    min-height: 2.4rem;
    border: 1px solid #E2E2DC !important;
    border-radius: 0.55rem;
    background: #FFFFFF !important;
    color: #333333 !important;
    font-weight: 600 !important;
    box-shadow: none;
    transition:
        background-color 120ms ease,
        border-color 120ms ease,
        box-shadow 120ms ease,
        transform 120ms ease;
}

.stApp button[data-testid="stBaseButton-primary"],
.stApp button[data-testid="stBaseButton-primaryFormSubmit"],
[data-testid="stDialog"] button[data-testid="stBaseButton-primary"] {
    border-color: #E5B72F !important;
    background: #F2C94C !important;
    color: #262626 !important;
}

.stApp button[data-testid="stBaseButton-secondary"],
.stApp button[data-testid="stBaseButton-secondaryFormSubmit"],
[data-testid="stDialog"] button[data-testid="stBaseButton-secondary"] {
    border-color: #E2E2DC !important;
    background: #FFFFFF !important;
    color: #333333 !important;
}

.stApp button[data-testid="stBaseButton-tertiary"],
[data-testid="stDialog"] button[data-testid="stBaseButton-tertiary"] {
    border-color: #E2E2DC !important;
    background: #FFFFFF !important;
    color: #333333 !important;
}

.stApp button[data-testid="stBaseButton-primary"]:hover,
.stApp button[data-testid="stBaseButton-primaryFormSubmit"]:hover,
[data-testid="stDialog"] button[data-testid="stBaseButton-primary"]:hover {
    border-color: #D7AA16 !important;
    background: #E5B72F !important;
    color: #262626 !important;
}

.stApp button[data-testid="stBaseButton-secondary"]:hover,
.stApp button[data-testid="stBaseButton-secondaryFormSubmit"]:hover,
.stApp button[data-testid="stBaseButton-tertiary"]:hover,
.stApp button[data-testid="stBaseButton-elementToolbar"]:hover,
[data-testid="stDialog"] button[data-testid="stBaseButton-secondary"]:hover,
[data-testid="stDialog"] button[data-testid="stBaseButton-tertiary"]:hover {
    border-color: #E2D9B6 !important;
    background: #FFF6D9 !important;
    color: #262626 !important;
}

.stApp button[data-testid="stBaseButton-primary"]:active:not(:disabled),
.stApp button[data-testid="stBaseButton-primaryFormSubmit"]:active:not(:disabled),
[data-testid="stDialog"] button[data-testid="stBaseButton-primary"]:active:not(:disabled) {
    border-color: #C79B12 !important;
    background: #DDB329 !important;
    color: #262626 !important;
}

.stApp button[data-testid="stBaseButton-secondary"]:active:not(:disabled),
.stApp button[data-testid="stBaseButton-secondaryFormSubmit"]:active:not(:disabled),
[data-testid="stDialog"] button[data-testid="stBaseButton-secondary"]:active:not(:disabled) {
    background: #F0F0ED !important;
}

.stApp button[data-testid^="stBaseButton-"]:active:not(:disabled),
[data-testid="stDialog"] button[data-testid^="stBaseButton-"]:active:not(:disabled) {
    transform: translateY(1px);
}

.stApp button[data-testid^="stBaseButton-"]:focus-visible,
[data-testid="stDialog"] button[data-testid^="stBaseButton-"]:focus-visible {
    outline: 3px solid rgba(155, 120, 14, 0.4) !important;
    outline-offset: 2px;
}

.stApp button[data-testid^="stBaseButton-"]:disabled,
.stApp button[data-testid^="stBaseButton-"][aria-disabled="true"],
[data-testid="stDialog"] button[data-testid^="stBaseButton-"]:disabled {
    border-color: #E2E2DC !important;
    background: #F0F0ED !important;
    color: #707070 !important;
    cursor: not-allowed;
    box-shadow: none;
    transform: none;
}

.stApp .st-key-inativar_produto button[data-testid^="stBaseButton-"],
.stApp .st-key-inativar_fornecedor button[data-testid^="stBaseButton-"] {
    border-color: #E8B8B4 !important;
    background: #FCE8E6 !important;
    color: #8A2C24 !important;
}

.stApp .st-key-inativar_produto button[data-testid^="stBaseButton-"]:hover,
.stApp .st-key-inativar_fornecedor button[data-testid^="stBaseButton-"]:hover {
    border-color: #D99A94 !important;
    background: #F6D3CF !important;
    color: #7A211B !important;
}

.stApp .st-key-inativar_produto button[data-testid^="stBaseButton-"]:disabled,
.stApp .st-key-inativar_fornecedor button[data-testid^="stBaseButton-"]:disabled {
    border-color: #E2E2DC !important;
    background: #F0F0ED !important;
    color: #707070 !important;
}

@media (prefers-reduced-motion: reduce) {
    .stApp button[data-testid^="stBaseButton-"],
    [data-testid="stDialog"] button[data-testid^="stBaseButton-"] {
        transition: none;
    }
}

.stApp [data-testid="stTextInputRootElement"] {
    border-color: #E2E2DC !important;
    background: #FFFFFF !important;
    color: #262626 !important;
    color-scheme: light;
}

.stApp [data-testid="stTextInputRootElement"] input {
    background: transparent !important;
    color: #262626 !important;
    color-scheme: light;
}

.stApp [data-testid="stTextInputRootElement"] button[aria-label="Show password"],
.stApp [data-testid="stTextInputRootElement"] button[aria-label="Hide password"] {
    border: 0 !important;
    border-radius: 0.4rem;
    background: #FFFFFF !important;
    color: #707070 !important;
}

.stApp [data-testid="stTextInputRootElement"] button[aria-label="Show password"]:hover,
.stApp [data-testid="stTextInputRootElement"] button[aria-label="Hide password"]:hover {
    background: #FFF6D9 !important;
    color: #262626 !important;
}

.stApp [data-testid="stTextInputRootElement"] button[aria-label="Show password"]:focus-visible,
.stApp [data-testid="stTextInputRootElement"] button[aria-label="Hide password"]:focus-visible {
    outline: 3px solid rgba(155, 120, 14, 0.4) !important;
    outline-offset: -2px;
}

.stApp [data-testid="stNumberInput"] button,
.stApp [data-testid="stDateInput"] button,
.stApp [data-testid="stSelectbox"] button[aria-label="Open"],
.stApp [data-testid="stMultiSelect"] button[aria-label="Open"] {
    border-color: #E2E2DC !important;
    background: #FFFFFF !important;
    color: #707070 !important;
}

.stApp [data-testid="stNumberInput"] button:hover,
.stApp [data-testid="stDateInput"] button:hover,
.stApp [data-testid="stSelectbox"] button[aria-label="Open"]:hover,
.stApp [data-testid="stMultiSelect"] button[aria-label="Open"]:hover {
    background: #FFF6D9 !important;
    color: #262626 !important;
}
</style>
"""


def apply_erp_theme():
    st.markdown(CSS, unsafe_allow_html=True)


def _estilos_linhas_tabela(frame):
    styles = pd.DataFrame("", index=frame.index, columns=frame.columns)
    for row_position in range(len(frame.index)):
        background = "#FFFFFF" if row_position % 2 == 0 else "#F0F0ED"
        styles.iloc[row_position, :] = (
            f"background-color: {background}; color: #262626; "
            "border-bottom: 1px solid #E7E7E3;"
        )
    return styles


def render_dataframe(dataframe, **kwargs):
    if isinstance(dataframe, pd.DataFrame):
        dataframe = (
            dataframe.style
            .apply(_estilos_linhas_tabela, axis=None)
            .set_table_styles(
                [
                    {
                        "selector": "th",
                        "props": [
                            ("background-color", "#FFF1B8"),
                            ("color", "#262626"),
                            ("font-weight", "600"),
                            ("border-bottom", "1px solid #E7E7E3"),
                        ],
                    }
                ]
            )
        )
    return st.dataframe(dataframe, **kwargs)


def show_toast(message, level="success"):
    icons = {
        "success": ":material/check_circle:",
        "info": ":material/info:",
        "warning": ":material/warning:",
        "error": ":material/error:",
    }
    st.toast(str(message), icon=icons.get(level, icons["info"]))


def show_confirmation_dialog(title, summary, on_confirm, *, key):
    @st.dialog(title, width="small")
    def dialog():
        st.write("Revise os dados abaixo antes de confirmar.")
        if isinstance(summary, dict):
            for label, value in summary.items():
                st.markdown(f"**{html.escape(str(label))}**")
                st.write(str(value))
        else:
            st.write(str(summary))

        st.divider()
        cancel_column, confirm_column = st.columns(2)
        with cancel_column:
            if st.button(
                "Cancelar",
                key=f"{key}_cancel",
                width="stretch",
            ):
                st.rerun()
        with confirm_column:
            if st.button(
                "Confirmar",
                key=f"{key}_confirm",
                type="primary",
                width="stretch",
            ):
                on_confirm()
                st.rerun()

    dialog()


@contextmanager
def data_skeleton(kind="table", count=4):
    placeholder = st.empty()
    if kind == "cards":
        markup = (
            "<div style='display:grid;grid-template-columns:repeat("
            f"auto-fit,minmax(140px,1fr));gap:0.75rem'>"
            + "".join(
                "<div class='cb-skeleton cb-skeleton-card'></div>"
                for _ in range(max(1, count))
            )
            + "</div>"
        )
    elif kind == "rows":
        markup = "".join(
            "<div class='cb-skeleton cb-skeleton-row'></div>"
            for _ in range(max(1, count))
        )
    else:
        markup = "<div class='cb-skeleton cb-skeleton-table'></div>"
    placeholder.markdown(markup, unsafe_allow_html=True)
    try:
        yield
    finally:
        placeholder.empty()


def render_app_shell(page_title, user_label, page_renderer):
    if "erp_page" not in st.session_state:
        st.session_state["erp_page"] = "Visão geral"

    page = st.session_state.get("erp_page", "Visão geral")
    user = st.session_state.get("auth_user")
    profile = user.get("profile") if isinstance(user, dict) else None
    safe_profile = html.escape(str(profile or "Conta autenticada"))
    safe_user_label = html.escape(str(user_label))
    initials = "".join(part[0] for part in str(user_label).split()[:2]).upper() or "U"
    safe_initials = html.escape(initials)

    with st.sidebar:
        st.markdown(
            "<div class='erp-brand'><div class='erp-brand-mark'>C</div>"
            "<div class='erp-brand-name'>CodBar</div></div>",
            unsafe_allow_html=True,
        )
        nav_groups = [
            (
                "Visão geral",
                [("Visão geral", ":material/dashboard:")],
            ),
            (
                "Operação",
                [
                    ("Produtos", ":material/inventory_2:"),
                    ("Estoque", ":material/warehouse:"),
                    ("Vendas", ":material/receipt_long:"),
                    ("Fornecedores", ":material/local_shipping:"),
                ],
            ),
            (
                "Análise",
                [("Relatórios", ":material/analytics:")],
            ),
            (
                "Acesso",
                [("Usuários e permissões", ":material/manage_accounts:")],
            ),
        ]

        for heading, items in nav_groups:
            st.markdown(
                f"<div class='erp-nav-heading'>{html.escape(heading)}</div>",
                unsafe_allow_html=True,
            )
            for item, icon in items:
                pressed = st.button(
                    item,
                    key=f"nav_{item}",
                    icon=icon,
                    type="primary" if item == page else "secondary",
                    width="stretch",
                )
                if pressed:
                    st.session_state["erp_page"] = item
                    st.rerun()

        st.markdown("<div class='erp-nav-spacer'></div>", unsafe_allow_html=True)
        st.markdown(
            f"""
            <div class='erp-account-card'>
                <div class='erp-account-avatar'>{safe_initials}</div>
                <div style='min-width:0'>
                    <div class='erp-account-name'>{safe_user_label}</div>
                    <div class='erp-account-role'>{safe_profile}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button(
            "Sair",
            key="erp_logout",
            icon=":material/logout:",
            type="secondary",
            width="stretch",
        ):
            st.session_state.pop("auth_token", None)
            st.session_state.pop("auth_user", None)
            st.rerun()

    safe_page = html.escape(str(page))
    safe_page_title = html.escape(str(page_title))

    with st.container(key="erp-app-shell"):
        st.markdown(
            f"""
            <div class='erp-topbar'>
                <div>
                    <div class='erp-topbar-title'>{safe_page}</div>
                    <div class='erp-topbar-subtitle'>{safe_page_title}</div>
                </div>
                <div class='erp-topbar-actions'>
                    <div class='erp-user'>
                        <span>{safe_user_label}</span>
                        <div class='erp-avatar'>{safe_initials}</div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.container(key="erp-page"):
            page_renderer(page)
