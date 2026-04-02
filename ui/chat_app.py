"""
Web Fetch Bot — AI-powered web search assistant.
Flow: User query → Search API → AI summarizes results → Chat output

Usage:
    streamlit run chat_app.py
"""

import os
import json
import httpx
import streamlit as st

try:
    from groq import Groq
    HAS_GROQ = True
except ImportError:
    HAS_GROQ = False

st.set_page_config(
    page_title="Fetch",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ------------------------------------------------------------------------------
# Session initialization
# ------------------------------------------------------------------------------
def init_session():
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "key_index" not in st.session_state:
        st.session_state.key_index = 0
    if "settings" not in st.session_state:
        st.session_state.settings = {
            "provider": "groq",
            "ollama_url": "http://localhost:11434",
            "ollama_model": "qwen2.5",
            "groq_keys": "",  # Empty – users must add their own keys
            "groq_model": "meta-llama/llama-4-scout-17b-16e-instruct",
            "search_server": "http://localhost:8000",
            "max_results": 5,
        }
    if "dark_mode" not in st.session_state:
        st.session_state.dark_mode = False


# ------------------------------------------------------------------------------
# Custom CSS – dynamic light/dark theme
# ------------------------------------------------------------------------------
def get_css(dark_mode):
    # Base variables (light)
    if not dark_mode:
        return """
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800&family=DM+Mono:wght@300;400;500&display=swap');

            :root {
                --ink: #0a0908;
                --paper: #f5f0e8;
                --paper-warm: #ede8dc;
                --paper-dim: #ddd8cc;
                --cream: #faf7f2;
                --text-muted: rgba(10,9,8,0.62);
                --rust: #c0392b;
                --rust-deep: #922b21;
                --rust-pale: #e8c4c0;
                --teal: #1a7a6e;
                --teal-pale: #b8d8d5;
                --gold: #c49a1a;
                --gold-pale: #f0e4b0;
                --border: rgba(10,9,8,0.12);
                --border-strong: rgba(10,9,8,0.28);
                --rule-line: rgba(10,9,8,0.04);
                --focus-ring: rgba(10,9,8,0.12);
                --sidebar-shadow: 2px 0 12px rgba(10,9,8,0.06);
                --input-shadow: 0 -4px 24px rgba(10,9,8,0.08), 0 -1px 0 var(--border);
                --status-ok-bg: rgba(26,122,110,0.07);
                --status-ok-border: rgba(26,122,110,0.25);
                --status-err-bg: rgba(192,57,43,0.07);
                --status-err-border: rgba(192,57,43,0.25);
                --status-warn-bg: rgba(196,154,26,0.07);
                --status-warn-border: rgba(196,154,26,0.25);
                --shadow-xs: 0 1px 3px rgba(10,9,8,0.08), 0 1px 2px rgba(10,9,8,0.06);
                --shadow-sm: 0 2px 8px rgba(10,9,8,0.1), 0 1px 3px rgba(10,9,8,0.08);
                --shadow-md: 0 6px 20px rgba(10,9,8,0.12), 0 2px 6px rgba(10,9,8,0.08);
                --shadow-lg: 0 16px 48px rgba(10,9,8,0.16), 0 4px 12px rgba(10,9,8,0.1);
                --font-display: 'Syne', sans-serif;
                --font-mono: 'DM Mono', monospace;
            }
        """
    else:
        # Dark mode variables
        return """
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800&family=DM+Mono:wght@300;400;500&display=swap');

            :root {
                --ink: #e2e8f0;
                --paper: #1e1e2a;
                --paper-warm: #2d2d3a;
                --paper-dim: #3a3a48;
                --cream: #0f0f17;
                --text-muted: rgba(226,232,240,0.68);
                --rust: #f87171;
                --rust-deep: #ef4444;
                --rust-pale: #7f2e2e;
                --teal: #2dd4bf;
                --teal-pale: #115e59;
                --gold: #fbbf24;
                --gold-pale: #854d0e;
                --border: rgba(226,232,240,0.12);
                --border-strong: rgba(226,232,240,0.28);
                --rule-line: rgba(226,232,240,0.07);
                --focus-ring: rgba(226,232,240,0.2);
                --sidebar-shadow: 2px 0 18px rgba(0,0,0,0.45);
                --input-shadow: 0 -6px 24px rgba(0,0,0,0.45), 0 -1px 0 var(--border);
                --status-ok-bg: rgba(45,212,191,0.14);
                --status-ok-border: rgba(45,212,191,0.32);
                --status-err-bg: rgba(248,113,113,0.14);
                --status-err-border: rgba(248,113,113,0.32);
                --status-warn-bg: rgba(251,191,36,0.14);
                --status-warn-border: rgba(251,191,36,0.32);
                --shadow-xs: 0 1px 3px rgba(0,0,0,0.3), 0 1px 2px rgba(0,0,0,0.2);
                --shadow-sm: 0 2px 8px rgba(0,0,0,0.4), 0 1px 3px rgba(0,0,0,0.3);
                --shadow-md: 0 6px 20px rgba(0,0,0,0.5), 0 2px 6px rgba(0,0,0,0.4);
                --shadow-lg: 0 16px 48px rgba(0,0,0,0.6), 0 4px 12px rgba(0,0,0,0.5);
                --font-display: 'Syne', sans-serif;
                --font-mono: 'DM Mono', monospace;
            }
        """


def render_css(dark_mode):
    css = get_css(dark_mode) + """
    * { box-sizing: border-box; margin: 0; padding: 0; }

    .stApp {
        background: var(--cream);
        color: var(--ink);
        font-family: var(--font-display);
    }

    /* Ruled paper texture */
    .stApp::before {
        content: '';
        position: fixed;
        inset: 0;
        background-image:
            repeating-linear-gradient(
                180deg,
                transparent 0px,
                transparent 27px,
                var(--rule-line) 27px,
                var(--rule-line) 28px
            );
        pointer-events: none;
        z-index: 0;
    }

    /* Keep Streamlit chrome minimal and keep settings visible */
    [data-testid="stHeader"] {
        background: transparent !important;
        z-index: 100 !important;
    }

    /* Keep Streamlit settings menu visible on the left */
    #MainMenu {
        visibility: visible !important;
        opacity: 1 !important;
        pointer-events: auto !important;
        position: fixed !important;
        top: 12px !important;
        left: 12px !important;
        z-index: 10000 !important;
        background: var(--paper) !important;
        border: 1px solid var(--border-strong) !important;
        border-radius: 3px !important;
        box-shadow: var(--shadow-sm) !important;
    }

    /* Fallback: if Streamlit renders a collapsed-sidebar control, pin it left */
    [data-testid="stSidebarCollapsedControl"],
    button[aria-label="Show sidebar"] {
        display: flex !important;
        visibility: visible !important;
        opacity: 1 !important;
        position: fixed !important;
        top: 12px !important;
        left: 52px !important;
        right: auto !important;
        z-index: 9999 !important;
        background: var(--paper) !important;
        border: 1px solid var(--border-strong) !important;
        border-radius: 3px !important;
        width: 40px !important;
        height: 40px !important;
        align-items: center !important;
        justify-content: center !important;
        cursor: pointer !important;
        pointer-events: auto !important;
        transition: all 0.2s ease !important;
        box-shadow: var(--shadow-sm) !important;
    }

    [data-testid="stSidebarCollapsedControl"]:hover,
    button[aria-label="Show sidebar"]:hover {
        background: var(--rust) !important;
        border-color: var(--rust) !important;
        transform: scale(1.05) !important;
        box-shadow: var(--shadow-md) !important;
    }

    [data-testid="stSidebarCollapsedControl"] svg,
    button[aria-label="Show sidebar"] svg {
        fill: var(--ink) !important;
        width: 20px !important;
        height: 20px !important;
    }

    footer { display: none !important; }
    .stDeployButton { display: none !important; }

    /* Sidebar: always visible and pinned on the left */
    [data-testid="stSidebar"] {
        width: min(320px, 86vw) !important;
        min-width: min(320px, 86vw) !important;
        max-width: min(320px, 86vw) !important;
        transform: translateX(0) !important;
        background: var(--paper) !important;
        border-right: 2px solid var(--border-strong) !important;
        box-shadow: var(--sidebar-shadow) !important;
    }

    [data-testid="stSidebar"][aria-expanded="false"] {
        transform: translateX(0) !important;
        margin-left: 0 !important;
    }

    [data-testid="stSidebarCollapseButton"] {
        display: none !important;
    }

    [data-testid="stSidebar"] [data-testid="stSidebarContent"] {
        padding: 0 !important;
        background: transparent !important;
    }

    /* Sidebar scrollbar */
    [data-testid="stSidebar"] ::-webkit-scrollbar { width: 4px; }
    [data-testid="stSidebar"] ::-webkit-scrollbar-track { background: transparent; }
    [data-testid="stSidebar"] ::-webkit-scrollbar-thumb { background: var(--border-strong); border-radius: 2px; }

    /* Sidebar header */
    .sb-header {
        padding: 28px 24px 20px;
        border-bottom: 1px solid var(--border);
        background: linear-gradient(180deg, var(--paper-warm) 0%, var(--paper) 100%);
        position: relative;
        overflow: hidden;
    }

    .sb-header::before {
        content: 'SETTINGS';
        position: absolute;
        right: -8px;
        top: 50%;
        transform: translateY(-50%) rotate(90deg);
        font-family: var(--font-mono);
        font-size: 9px;
        font-weight: 500;
        letter-spacing: 4px;
        color: var(--border-strong);
        opacity: 0.5;
    }

    .sb-logo {
        display: flex;
        align-items: center;
        gap: 12px;
    }

    .sb-logo-mark {
        width: 44px;
        height: 44px;
        background: var(--ink);
        border-radius: 3px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-family: var(--font-mono);
        font-size: 18px;
        color: var(--paper);
        font-weight: 300;
        letter-spacing: -2px;
        flex-shrink: 0;
    }

    .sb-logo-text {
        font-family: var(--font-display);
        font-weight: 800;
        font-size: 20px;
        letter-spacing: -0.03em;
        color: var(--ink);
        line-height: 1;
    }

    .sb-logo-sub {
        font-family: var(--font-mono);
        font-size: 10px;
        color: var(--text-muted);
        letter-spacing: 0.05em;
        margin-top: 3px;
    }

    /* Sidebar sections */
    .sb-section {
        padding: 20px 24px;
        border-bottom: 1px solid var(--border);
    }

    .sb-section-label {
        font-family: var(--font-mono);
        font-size: 9px;
        font-weight: 500;
        letter-spacing: 3px;
        text-transform: uppercase;
        color: var(--text-muted);
        margin-bottom: 14px;
        display: flex;
        align-items: center;
        gap: 8px;
    }

    .sb-section-label::after {
        content: '';
        flex: 1;
        height: 1px;
        background: var(--border);
    }

    /* Status pills */
    .status-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 5px 10px;
        border-radius: 2px;
        font-family: var(--font-mono);
        font-size: 11px;
        font-weight: 400;
        border: 1px solid;
        margin-top: 8px;
    }

    .status-pill.ok {
        background: var(--status-ok-bg);
        color: var(--teal);
        border-color: var(--status-ok-border);
    }

    .status-pill.err {
        background: var(--status-err-bg);
        color: var(--rust);
        border-color: var(--status-err-border);
    }

    .status-pill.warn {
        background: var(--status-warn-bg);
        color: var(--gold);
        border-color: var(--status-warn-border);
    }

    .status-dot {
        width: 6px;
        height: 6px;
        border-radius: 50%;
        flex-shrink: 0;
    }

    .status-dot.ok { background: var(--teal); }
    .status-dot.err { background: var(--rust); animation: blink 2s infinite; }
    .status-dot.pulse { background: var(--gold); animation: blink 1s infinite; }

    @keyframes blink { 0%,100% { opacity: 1; } 50% { opacity: 0.3; } }

    /* Main layout */
    .main-wrap {
        max-width: 780px;
        margin: 0 auto;
        padding: 0 24px 140px;
        position: relative;
        z-index: 1;
    }

    /* Page header */
    .page-header {
        padding: 40px 0 32px;
        border-bottom: 2px solid var(--ink);
        margin-bottom: 0;
        display: flex;
        align-items: flex-end;
        justify-content: space-between;
        position: relative;
    }

    .page-header::after {
        content: '';
        position: absolute;
        bottom: -5px;
        left: 0;
        right: 0;
        height: 1px;
        background: var(--ink);
        opacity: 0.15;
    }

    .page-title {
        font-family: var(--font-display);
        font-weight: 800;
        font-size: clamp(32px, 5vw, 52px);
        letter-spacing: -0.04em;
        line-height: 0.9;
        color: var(--ink);
    }

    .page-title span {
        color: var(--rust);
    }

    .page-meta {
        font-family: var(--font-mono);
        font-size: 11px;
        color: var(--text-muted);
        letter-spacing: 0.05em;
        text-align: right;
        line-height: 1.6;
    }

    /* Chat messages */
    .chat-area {
        padding: 32px 0 24px;
    }

    /* Welcome state */
    .welcome-wrap {
        padding: 80px 0 60px;
        text-align: center;
    }

    .welcome-eyebrow {
        font-family: var(--font-mono);
        font-size: 10px;
        letter-spacing: 3px;
        text-transform: uppercase;
        color: var(--text-muted);
        margin-bottom: 20px;
    }

    .welcome-title {
        font-family: var(--font-display);
        font-size: clamp(28px, 4vw, 42px);
        font-weight: 800;
        letter-spacing: -0.04em;
        color: var(--ink);
        margin-bottom: 16px;
        line-height: 1.05;
    }

    .welcome-sub {
        font-family: var(--font-mono);
        font-size: 13px;
        color: var(--text-muted);
        max-width: 400px;
        margin: 0 auto 40px;
        line-height: 1.65;
    }

    .welcome-prompts {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        justify-content: center;
        max-width: 560px;
        margin: 0 auto;
    }

    .prompt-chip {
        padding: 8px 16px;
        border: 1px solid var(--border-strong);
        border-radius: 2px;
        font-family: var(--font-mono);
        font-size: 11px;
        color: var(--text-muted);
        background: var(--paper);
        cursor: pointer;
        transition: all 0.15s ease;
    }

    /* Message rows */
    .msg-row {
        display: flex;
        gap: 16px;
        margin-bottom: 28px;
        animation: fadeUp 0.3s ease;
    }

    @keyframes fadeUp {
        from { opacity: 0; transform: translateY(12px); }
        to { opacity: 1; transform: translateY(0); }
    }

    .msg-row.user { flex-direction: row-reverse; }

    .msg-avatar {
        width: 32px;
        height: 32px;
        border-radius: 2px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-family: var(--font-mono);
        font-size: 10px;
        font-weight: 500;
        letter-spacing: 0.5px;
        flex-shrink: 0;
        margin-top: 2px;
    }

    .msg-avatar.user-av {
        background: var(--ink);
        color: var(--paper);
    }

    .msg-avatar.bot-av {
        background: var(--rust);
        color: white;
    }

    .msg-body { flex: 1; max-width: calc(100% - 48px); }

    .msg-label {
        font-family: var(--font-mono);
        font-size: 9px;
        letter-spacing: 2px;
        text-transform: uppercase;
        color: var(--text-muted);
        margin-bottom: 6px;
    }

    .msg-row.user .msg-label { text-align: right; }

    .user-bubble {
        background: var(--ink);
        color: var(--paper);
        padding: 14px 18px;
        border-radius: 3px;
        font-family: var(--font-display);
        font-size: 14px;
        font-weight: 500;
        line-height: 1.55;
        display: inline-block;
        max-width: 100%;
        box-shadow: var(--shadow-sm);
    }

    .bot-bubble {
        background: var(--paper);
        border: 1px solid var(--border);
        border-left: 3px solid var(--rust);
        padding: 18px 20px;
        border-radius: 0 3px 3px 0;
        font-family: var(--font-display);
        font-size: 14px;
        line-height: 1.7;
        color: var(--ink);
        box-shadow: var(--shadow-xs);
    }

    /* Search results section */
    .results-wrap {
        margin-top: 18px;
        padding-top: 18px;
        border-top: 1px dashed var(--border-strong);
    }

    .results-label {
        font-family: var(--font-mono);
        font-size: 9px;
        letter-spacing: 3px;
        text-transform: uppercase;
        color: var(--text-muted);
        margin-bottom: 12px;
        display: flex;
        align-items: center;
        gap: 8px;
    }

    .results-label::after {
        content: '';
        flex: 1;
        height: 1px;
        background: var(--border);
    }

    .result-item {
        padding: 14px 0;
        border-bottom: 1px solid var(--border);
        display: flex;
        gap: 14px;
        transition: all 0.15s ease;
    }

    .result-item:last-child { border-bottom: none; }

    .result-num {
        font-family: var(--font-mono);
        font-size: 11px;
        color: var(--rust);
        font-weight: 500;
        flex-shrink: 0;
        width: 20px;
        padding-top: 1px;
    }

    .result-content { flex: 1; }

    .result-title {
        font-family: var(--font-display);
        font-size: 13px;
        font-weight: 600;
        color: var(--ink);
        text-decoration: none;
        display: block;
        margin-bottom: 5px;
        letter-spacing: -0.01em;
        line-height: 1.3;
        transition: color 0.15s ease;
    }

    .result-title:hover { color: var(--rust); }

    .result-snippet {
        font-family: var(--font-mono);
        font-size: 11px;
        color: var(--text-muted);
        line-height: 1.6;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }

    .result-src {
        display: inline-block;
        margin-top: 6px;
        font-family: var(--font-mono);
        font-size: 9px;
        letter-spacing: 1px;
        text-transform: uppercase;
        padding: 2px 7px;
        border: 1px solid var(--border-strong);
        border-radius: 1px;
        color: var(--text-muted);
    }

    /* Divider between conversations */
    .msg-divider {
        display: flex;
        align-items: center;
        gap: 12px;
        margin: 4px 0 28px;
    }

    .msg-divider::before, .msg-divider::after {
        content: '';
        flex: 1;
        height: 1px;
        background: var(--border);
    }

    .msg-divider span {
        font-family: var(--font-mono);
        font-size: 9px;
        letter-spacing: 2px;
        color: var(--text-muted);
        text-transform: uppercase;
    }

    /* Thinking */
    .thinking-wrap {
        display: flex;
        gap: 16px;
        margin-bottom: 28px;
    }

    .thinking-body {
        background: var(--paper);
        border: 1px solid var(--border);
        border-left: 3px solid var(--gold);
        padding: 14px 18px;
        border-radius: 0 3px 3px 0;
        display: flex;
        align-items: center;
        gap: 12px;
    }

    .thinking-text {
        font-family: var(--font-mono);
        font-size: 11px;
        color: var(--gold);
        letter-spacing: 0.5px;
    }

    .think-dots {
        display: flex;
        gap: 4px;
    }

    .think-dot {
        width: 5px;
        height: 5px;
        background: var(--gold);
        border-radius: 50%;
        animation: td 1.2s infinite ease-in-out;
    }

    .think-dot:nth-child(2) { animation-delay: 0.2s; }
    .think-dot:nth-child(3) { animation-delay: 0.4s; }

    @keyframes td {
        0%,80%,100% { transform: scale(0.5); opacity: 0.3; }
        40% { transform: scale(1); opacity: 1; }
    }

    /* Fixed chat input */
    [data-testid="stChatInput"] {
        position: fixed !important;
        bottom: 0 !important;
        left: 0 !important;
        right: 0 !important;
        z-index: 999 !important;
        padding: 0 !important;
        background: transparent !important;
    }

    /* The input container */
    [data-testid="stChatInput"] > div {
        max-width: 780px !important;
        margin: 0 auto !important;
        background: var(--paper) !important;
        border: none !important;
        border-top: 2px solid var(--ink) !important;
        border-radius: 0 !important;
        box-shadow: var(--input-shadow) !important;
        padding: 0 !important;
    }

    [data-testid="stChatInput"] textarea {
        font-family: var(--font-display) !important;
        font-size: 14px !important;
        font-weight: 500 !important;
        color: var(--ink) !important;
        background: var(--paper) !important;
        padding: 18px 24px !important;
        border: none !important;
        outline: none !important;
        resize: none !important;
        line-height: 1.5 !important;
        letter-spacing: -0.01em !important;
    }

    [data-testid="stChatInput"] textarea::placeholder {
        color: var(--text-muted) !important;
        font-weight: 400 !important;
    }

    /* Input send button */
    [data-testid="stChatInput"] button {
        background: var(--ink) !important;
        border: none !important;
        border-radius: 2px !important;
        color: var(--paper) !important;
        margin: 10px 12px !important;
        width: 36px !important;
        height: 36px !important;
        transition: all 0.15s ease !important;
    }

    [data-testid="stChatInput"] button:hover {
        background: var(--rust) !important;
        transform: scale(1.05) !important;
    }

    /* Streamlit controls theming */
    .stRadio label {
        font-family: var(--font-mono) !important;
        font-size: 12px !important;
        color: var(--ink) !important;
    }

    .stSelectbox > div > div {
        background: var(--paper) !important;
        border: 1px solid var(--border-strong) !important;
        border-radius: 2px !important;
        font-family: var(--font-mono) !important;
        font-size: 12px !important;
        color: var(--ink) !important;
    }

    [data-baseweb="select"] > div,
    [data-baseweb="base-input"] > div {
        background: var(--paper) !important;
        border-color: var(--border-strong) !important;
        color: var(--ink) !important;
    }

    div[data-baseweb="popover"] {
        background: var(--paper) !important;
        color: var(--ink) !important;
        border: 1px solid var(--border-strong) !important;
    }

    div[data-baseweb="popover"] ul,
    div[data-baseweb="popover"] li,
    div[data-baseweb="popover"] [role="option"] {
        background: var(--paper) !important;
        color: var(--ink) !important;
    }

    .stTextInput input, .stTextArea textarea {
        background: var(--paper) !important;
        border: 1px solid var(--border-strong) !important;
        border-radius: 2px !important;
        font-family: var(--font-mono) !important;
        font-size: 12px !important;
        color: var(--ink) !important;
    }

    .stTextInput input:focus, .stTextArea textarea:focus {
        border-color: var(--ink) !important;
        box-shadow: 0 0 0 2px var(--focus-ring) !important;
        outline: none !important;
    }

    .stSlider [data-baseweb="slider"] [data-testid="stThumbValue"] {
        font-family: var(--font-mono) !important;
        font-size: 11px !important;
    }

    .stButton button {
        background: var(--paper) !important;
        border: 1px solid var(--border-strong) !important;
        border-radius: 2px !important;
        color: var(--ink) !important;
        font-family: var(--font-mono) !important;
        font-size: 11px !important;
        letter-spacing: 0.5px !important;
        padding: 8px 16px !important;
        transition: all 0.15s ease !important;
    }

    .stButton button:hover {
        background: var(--ink) !important;
        color: var(--paper) !important;
        border-color: var(--ink) !important;
    }

    /* Streamlit spinner */
    .stSpinner > div {
        border-color: var(--rust) transparent transparent !important;
    }

    /* Scrollbar main area */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: var(--border-strong); border-radius: 3px; }

    /* Mobile */
    @media (max-width: 768px) {
        .main-wrap { padding: 0 16px 140px; }
        .page-header { flex-direction: column; align-items: flex-start; gap: 10px; }
        .page-meta { text-align: left; }
        .msg-row { gap: 10px; }
        .msg-avatar { width: 26px; height: 26px; font-size: 8px; }
        .welcome-wrap { padding: 48px 0 32px; }
    }
    </style>
    """
    return css


init_session()
settings = st.session_state.settings

# Render CSS with current dark mode
st.markdown(render_css(st.session_state.dark_mode), unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# Helper functions (unchanged except keys removal)
# ------------------------------------------------------------------------------
def get_groq_keys():
    raw = st.session_state.settings.get("groq_keys", "")
    return [k.strip() for k in raw.split("\n") if k.strip()]


def get_next_groq_key():
    keys = get_groq_keys()
    if not keys:
        return None
    idx = st.session_state.key_index % len(keys)
    st.session_state.key_index = idx + 1
    return keys[idx]


def search_web(query: str, server: str, max_results: int):
    endpoints = [f"{server}/search", f"{server}/search/all"]
    for url in endpoints:
        try:
            with httpx.Client(timeout=20) as client:
                params = {"q": query, "max_results": 3 if "/all" in url else max_results}
                resp = client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
                results = data.get("results", [])
                backend = data.get("backend_used", data.get("backends_queried", ["unknown"]))
                if isinstance(backend, list):
                    backend = ", ".join(backend)
                if results:
                    return results[:max_results * 2], backend
        except Exception:
            continue
    return [], "none"


def ai_summarize_groq(query: str, results: list, model: str):
    context = ""
    for i, r in enumerate(results, 1):
        context += f"{i}. {r.get('title', '')}\n   URL: {r.get('url', '')}\n   {r.get('snippet', '')}\n\n"

    api_key = get_next_groq_key()
    if not api_key:
        return None
    client = Groq(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "You are a precise web research assistant. Synthesize the search results into a clear, factual summary. Be direct. Mention key sources. Keep it under 200 words.",
            },
            {"role": "user", "content": f"Query: {query}\n\nResults:\n{context}"},
        ],
        max_tokens=1500,
        temperature=0.3,
    )
    return response.choices[0].message.content


def ai_summarize_ollama(query: str, results: list, model: str, ollama_url: str):
    context = ""
    for i, r in enumerate(results, 1):
        context += f"{i}. {r.get('title', '')}\n   URL: {r.get('url', '')}\n   {r.get('snippet', '')}\n\n"

    try:
        with httpx.Client(timeout=60) as client:
            resp = client.post(
                f"{ollama_url}/api/chat",
                json={
                    "model": model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a precise web research assistant. Synthesize the search results into a clear, factual summary. Be direct. Mention key sources. Keep it under 200 words.",
                        },
                        {"role": "user", "content": f"Query: {query}\n\nResults:\n{context}"},
                    ],
                    "stream": False,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("message", {}).get("content", "")
    except Exception:
        return None


# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        """
    <div class="sb-header">
        <div class="sb-logo">
            <div class="sb-logo-mark">◈</div>
            <div>
                <div class="sb-logo-text">Fetch</div>
                <div class="sb-logo-sub">web search bot · v1.0</div>
            </div>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # Dark mode toggle
    st.markdown('<div class="sb-section">', unsafe_allow_html=True)
    if st.button("🌓 Toggle Dark Mode", use_container_width=True):
        st.session_state.dark_mode = not st.session_state.dark_mode
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    # ── AI Provider ─────────────────────────────────────────────────────
    st.markdown("""<div class="sb-section">""", unsafe_allow_html=True)
    st.markdown('<div class="sb-section-label">AI Engine</div>', unsafe_allow_html=True)

    settings["provider"] = st.radio(
        "Provider",
        options=["groq", "ollama"],
        format_func=lambda x: "Groq Cloud" if x == "groq" else "Ollama Local",
        index=0 if settings["provider"] == "groq" else 1,
        label_visibility="collapsed",
    )

    if settings["provider"] == "ollama":
        settings["ollama_url"] = st.text_input(
            "Ollama URL",
            value=settings["ollama_url"],
            placeholder="http://localhost:11434",
        )
        settings["ollama_model"] = st.text_input(
            "Model name",
            value=settings["ollama_model"],
            placeholder="qwen2.5",
        )
        try:
            with httpx.Client(timeout=3) as c:
                r = c.get(f"{settings['ollama_url']}/api/tags")
                if r.status_code == 200:
                    models = [m["name"] for m in r.json().get("models", [])]
                    if models:
                        st.markdown(
                            f'<div class="status-pill ok"><span class="status-dot ok"></span>{len(models)} models available</div>',
                            unsafe_allow_html=True,
                        )
                        if settings["ollama_model"] not in models:
                            settings["ollama_model"] = models[0]
                        settings["ollama_model"] = st.selectbox(
                            "Model",
                            models,
                            index=models.index(settings["ollama_model"])
                            if settings["ollama_model"] in models
                            else 0,
                        )
                    else:
                        st.markdown(
                            '<div class="status-pill warn"><span class="status-dot pulse"></span>No models — run: ollama pull qwen2.5</div>',
                            unsafe_allow_html=True,
                        )
                else:
                    st.markdown(
                        '<div class="status-pill err"><span class="status-dot err"></span>Ollama error</div>',
                        unsafe_allow_html=True,
                    )
        except Exception:
            st.markdown(
                '<div class="status-pill err"><span class="status-dot err"></span>Ollama not running</div>',
                unsafe_allow_html=True,
            )
    else:
        settings["groq_keys"] = st.text_area(
            "API Keys (one per line)",
            value=settings["groq_keys"],
            height=100,
            placeholder="gsk_...\ngsk_...",
        )
        groq_models = [
            "meta-llama/llama-4-scout-17b-16e-instruct",
            "llama-3.1-8b-instant",
            "qwen/qwen3-32b",
            "groq/compound",
            "groq/compound-mini",
            "moonshotai/kimi-k2-instruct",
        ]
        settings["groq_model"] = st.selectbox(
            "Model",
            options=groq_models,
            index=groq_models.index(settings["groq_model"])
            if settings["groq_model"] in groq_models
            else 0,
        )
        keys = get_groq_keys()
        if keys:
            st.markdown(
                f'<div class="status-pill ok"><span class="status-dot ok"></span>{len(keys)} key{"s" if len(keys) > 1 else ""} loaded · auto-rotating</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div class="status-pill err"><span class="status-dot err"></span>No API keys</div>',
                unsafe_allow_html=True,
            )

    st.markdown("</div>", unsafe_allow_html=True)

    # ── Search Server ───────────────────────────────────────────────────
    st.markdown('<div class="sb-section">', unsafe_allow_html=True)
    st.markdown('<div class="sb-section-label">Search Server</div>', unsafe_allow_html=True)

    settings["search_server"] = st.text_input(
        "Server URL",
        value=settings["search_server"],
        placeholder="http://localhost:8000",
    )
    settings["max_results"] = st.slider("Results per query", 1, 10, settings["max_results"])

    st.markdown("</div>", unsafe_allow_html=True)

    # ── Status ──────────────────────────────────────────────────────────
    st.markdown('<div class="sb-section">', unsafe_allow_html=True)
    st.markdown('<div class="sb-section-label">Status</div>', unsafe_allow_html=True)

    server_ok = False
    try:
        with httpx.Client(timeout=3) as c:
            c.get(f"{settings['search_server']}/health")
        server_ok = True
    except Exception:
        pass

    cls = "ok" if server_ok else "err"
    label = "Search server online" if server_ok else "Search server offline"
    st.markdown(
        f'<div class="status-pill {cls}"><span class="status-dot {cls}"></span>{label}</div>',
        unsafe_allow_html=True,
    )

    if settings["provider"] == "ollama":
        ollama_ok = False
        try:
            with httpx.Client(timeout=3) as c:
                c.get(f"{settings['ollama_url']}/api/tags")
            ollama_ok = True
        except Exception:
            pass
        cls2 = "ok" if ollama_ok else "err"
        label2 = "Ollama online" if ollama_ok else "Ollama offline"
        st.markdown(
            f'<div class="status-pill {cls2}"><span class="status-dot {cls2}"></span>{label2}</div>',
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)

    # ── Actions ─────────────────────────────────────────────────────────
    st.markdown('<div class="sb-section">', unsafe_allow_html=True)
    if st.button("Clear conversation", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


# ─── Main Content ─────────────────────────────────────────────────────────────
st.markdown('<div class="main-wrap">', unsafe_allow_html=True)

msg_count = len([m for m in st.session_state.messages if m["role"] == "user"])
st.markdown(
    f"""
<div class="page-header">
    <div class="page-title">Web<span>.</span>Fetch</div>
    <div class="page-meta">
        <div>AI-powered search</div>
        <div style="margin-top:2px;opacity:0.6;">{msg_count} quer{"ies" if msg_count != 1 else "y"} this session</div>
    </div>
</div>
""",
    unsafe_allow_html=True,
)

st.markdown('<div class="chat-area">', unsafe_allow_html=True)

# Welcome screen
if not st.session_state.messages:
    st.markdown(
        """
    <div class="welcome-wrap">
        <div class="welcome-eyebrow">◈ Web Fetch Bot</div>
        <div class="welcome-title">Ask anything.<br>Get answers.</div>
        <div class="welcome-sub">
            I search the web and synthesize results using AI.
            Type a question below to get started.
        </div>
        <div class="welcome-prompts">
            <div class="prompt-chip">Latest AI news</div>
            <div class="prompt-chip">Python best practices 2025</div>
            <div class="prompt-chip">Top open source projects</div>
            <div class="prompt-chip">How does X work?</div>
            <div class="prompt-chip">Recent research on Y</div>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

# Render messages
for i, msg in enumerate(st.session_state.messages):
    if msg["role"] == "user":
        st.markdown(
            f"""
        <div class="msg-row user">
            <div class="msg-avatar user-av">YOU</div>
            <div class="msg-body">
                <div class="msg-label">You</div>
                <div class="user-bubble">{msg["content"]}</div>
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

    else:
        provider_label = "OLLAMA" if msg.get("provider") == "ollama" else "GROQ"
        backend = msg.get("backend", "")
        backend_str = f" · via {backend}" if backend and backend != "none" else ""

        results_html = ""
        if msg.get("results"):
            results_html = '<div class="results-wrap"><div class="results-label">Sources</div>'
            for j, r in enumerate(msg["results"], 1):
                title = r.get("title", "No title")
                url = r.get("url", "")
                snippet = r.get("snippet", "")
                source = r.get("source", "")
                link = f'<a class="result-title" href="{url}" target="_blank" rel="noopener">{title}</a>' if url else f'<div class="result-title">{title}</div>'
                results_html += f"""
                <div class="result-item">
                    <div class="result-num">{j:02d}</div>
                    <div class="result-content">
                        {link}
                        {'<div class="result-snippet">' + snippet + '</div>' if snippet else ''}
                        {'<span class="result-src">' + source + '</span>' if source else ''}
                    </div>
                </div>"""
            results_html += "</div>"

        summary = msg.get("ai_summary", "")

        st.markdown(
            f"""
        <div class="msg-row">
            <div class="msg-avatar bot-av">AI</div>
            <div class="msg-body">
                <div class="msg-label">{provider_label}{backend_str}</div>
                <div class="bot-bubble">
                    {summary}
                    {results_html}
                </div>
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

        # Divider between conversation pairs (not after last)
        if i < len(st.session_state.messages) - 1:
            st.markdown('<div class="msg-divider"><span>· · ·</span></div>', unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)  # chat-area
st.markdown("</div>", unsafe_allow_html=True)  # main-wrap

# ─── Chat Input ───────────────────────────────────────────────────────────────
if prompt := st.chat_input("Search the web... e.g. 'Latest news about Claude AI'"):
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.spinner("Searching..."):
        results, backend = search_web(prompt, settings["search_server"], settings["max_results"])

    if results:
        with st.spinner("Synthesizing results..."):
            summary = None
            if settings["provider"] == "ollama":
                summary = ai_summarize_ollama(prompt, results, settings["ollama_model"], settings["ollama_url"])
            else:
                summary = ai_summarize_groq(prompt, results, settings["groq_model"])

        if not summary:
            summary = f"Found {len(results)} results but the AI couldn't respond. Check your {settings['provider']} settings."
    else:
        summary = "No results found. Try a different query or check if the search server is running."
        results = []

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": prompt,
            "ai_summary": summary,
            "results": results,
            "backend": backend,
            "provider": settings["provider"],
        }
    )

    st.rerun()
