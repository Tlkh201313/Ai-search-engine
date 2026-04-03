"""
Web Fetch Bot — AI-powered web search assistant.
Flow: User query → Search API → AI summarizes results → Chat output

Usage:
    streamlit run chat_app.py
"""

import httpx
import streamlit as st
from html import escape
from urllib.parse import parse_qs, unquote, urlparse
import time

PHONE_UA_MARKERS = (
    "iphone",
    "android",
    "mobile",
    "windows phone",
    "opera mini",
    "iemobile",
    "ipod",
)


def ua_is_phone(user_agent: str) -> bool:
    return any(marker in (user_agent or "").lower() for marker in PHONE_UA_MARKERS)

try:
    from groq import Groq
    HAS_GROQ = True
except ImportError:
    HAS_GROQ = False

_initial_user_agent = ""
try:
    _headers = getattr(getattr(st, "context", None), "headers", None)
    if _headers:
        _initial_user_agent = _headers.get("user-agent") or _headers.get("User-Agent") or ""
except Exception:
    _initial_user_agent = ""

st.set_page_config(
    page_title="Fetch",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="collapsed" if ua_is_phone(_initial_user_agent) else "expanded",
)

# ------------------------------------------------------------------------------
# Session initialization
# ------------------------------------------------------------------------------
def init_session():
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "key_index" not in st.session_state:
        st.session_state.key_index = 0
    if "exp_ai" not in st.session_state: st.session_state.exp_ai = True
    if "exp_search" not in st.session_state: st.session_state.exp_search = False
    if "exp_advanced" not in st.session_state: st.session_state.exp_advanced = False
    if "exp_status" not in st.session_state: st.session_state.exp_status = False
    if "exp_behavior" not in st.session_state: st.session_state.exp_behavior = False
    default_settings = {
        "show_sources": True,
        "provider": "groq",
        "ollama_url": "http://localhost:11434",
        "ollama_model": "qwen2.5",
        "groq_keys": "",
        "groq_model": "meta-llama/llama-4-scout-17b-16e-instruct",
        "search_server": "http://localhost:8000",
        "max_results": 5,
        "ollama_fast_mode": True,
        "response_mode": "Balanced",
        "temperature": 0.2,
        "max_response_length": "Medium",
        "search_region": "All",
        "auto_scroll": True,
        # Advanced
        "context_results_limit": 0,
        "context_snippet_chars": 0,
        "search_timeout_s": 20,
        "search_all_endpoint_limit": 3,
        "groq_max_tokens": 0,
        "ollama_num_predict": 0,
        "ollama_context_length": 0,
        "ollama_top_p": 0.9,
        "ollama_keep_alive": "20m",
        "ollama_timeout_s": 0,
    }
    if "settings" not in st.session_state:
        st.session_state.settings = default_settings.copy()
    else:
        for key, value in default_settings.items():
            st.session_state.settings.setdefault(key, value)
    if "dark_mode" not in st.session_state:
        st.session_state.dark_mode = False
    if "loading_screen_rendered" not in st.session_state:
        st.session_state.loading_screen_rendered = False
    # Cache for sidebards status to avoid repeated network calls
    if "last_health_check" not in st.session_state:
        st.session_state.last_health_check = 0
        st.session_state.cached_server_ok = False
        st.session_state.cached_ollama_ok = False
        st.session_state.cached_ollama_models = []
    if "cached_ollama_url" not in st.session_state:
        st.session_state.cached_ollama_url = ""
    if "last_ollama_check" not in st.session_state:
        st.session_state.last_ollama_check = 0.0


# ------------------------------------------------------------------------------
# Custom CSS – dynamic light/dark theme (with larger chat input)
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
                --chat-max-width: 1400px;
                --chat-input-min-height: 220px;
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
                --chat-max-width: 1400px;
                --chat-input-min-height: 220px;
            }
        """


def render_css(dark_mode, is_phone=False):
    css = get_css(dark_mode) + """
    * { 
        box-sizing: border-box; 
        margin: 0; 
        padding: 0; 
        transition: background-color 0.4s ease, color 0.4s ease, border-color 0.4s ease, box-shadow 0.4s ease;
    }

    /* LOADING SCREEN */
    #initial-loading-screen {
        position: fixed;
        inset: 0;
        z-index: 999999;
        background: var(--cream);
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        pointer-events: none;
        animation: loaderAutoDismiss 0.55s ease 4s forwards;
    }
    #initial-loading-screen.hidden {
        opacity: 0 !important;
        visibility: hidden !important;
        transition: all 0.55s ease !important;
    }
    #initial-loading-screen.fade-out {
        opacity: 0 !important;
        visibility: hidden !important;
        transition: all 0.55s ease !important;
    }
    @keyframes loaderAutoDismiss {
        to { opacity: 0; visibility: hidden; pointer-events: none; }
    }
    .loader-icon {
        font-size: 48px;
        color: var(--ink);
        animation: spinRotate 1s infinite cubic-bezier(0.5, 0, 0.5, 1);
        margin-bottom: 16px;
    }
    .loader-text {
        font-family: var(--font-mono);
        font-size: 12px;
        letter-spacing: 2px;
        color: var(--text-muted);
        text-transform: uppercase;
    }
    @keyframes spinRotate {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }

    .stApp {
        background: var(--cream);
        color: var(--ink) !important;
        font-family: var(--font-display);
    }

    /* FIX LIGHT MODE TEXT */
    p, span, div, label, h1, h2, h3, h4, h5, h6, li, ul, ol, button, input, textarea {
        color: var(--ink) !important;
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

    /* Keep Streamlit chrome minimal */
    [data-testid="stHeader"] {
        background: transparent !important;
        z-index: 100 !important;
    }

    #MainMenu { display: none !important; }

    /* Custom Hamburger Settings Button */
    [data-testid="stSidebarCollapsedControl"],
    button[aria-label="Show sidebar"], 
    [data-testid="stSidebarCollapseButton"],
    button[aria-label="Collapse sidebar"] {
        display: flex !important;
        visibility: visible !important;
        opacity: 1 !important;
        position: fixed !important;
        top: 12px !important;
        left: 12px !important;
        right: auto !important;
        z-index: 10001 !important;
        background: var(--paper) !important;
        border: 1px solid var(--border-strong) !important;
        border-radius: 3px !important;
        width: 44px !important;
        height: 44px !important;
        align-items: center !important;
        justify-content: center !important;
        cursor: pointer !important;
        pointer-events: auto !important;
        transition: all 0.3s ease !important;
        box-shadow: var(--shadow-sm) !important;
    }

    [data-testid="stSidebarCollapsedControl"] svg,
    button[aria-label="Show sidebar"] svg,
    [data-testid="stSidebarCollapseButton"] svg,
    button[aria-label="Collapse sidebar"] svg {
        display: none !important;
    }

    [data-testid="stSidebarCollapsedControl"]::after,
    button[aria-label="Show sidebar"]::after,
    [data-testid="stSidebarCollapseButton"]::after,
    button[aria-label="Collapse sidebar"]::after {
        content: '☰';
        font-size: 22px;
        color: var(--ink) !important;
        line-height: 1;
        transition: transform 0.3s ease;
    }

    [data-testid="stSidebarCollapseButton"]::after,
    button[aria-label="Collapse sidebar"]::after {
        content: '✕';
        font-size: 18px;
    }

    [data-testid="stSidebarCollapsedControl"]:hover,
    button[aria-label="Show sidebar"]:hover,
    [data-testid="stSidebarCollapseButton"]:hover,
    button[aria-label="Collapse sidebar"]:hover {
        background: var(--rust) !important;
        border-color: var(--rust) !important;
        transform: scale(1.05) !important;
        box-shadow: var(--shadow-md) !important;
    }
    
    [data-testid="stSidebarCollapsedControl"]:hover::after,
    [data-testid="stSidebarCollapseButton"]:hover::after,
    button[aria-label="Show sidebar"]:hover::after,
    button[aria-label="Collapse sidebar"]:hover::after {
        color: white !important;
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
        margin-left: min(-320px, -86vw) !important;
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
        max-width: var(--chat-max-width);
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
        max-width: var(--chat-max-width) !important;
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
        min-height: var(--chat-input-min-height) !important;
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
        .msg-body { max-width: calc(100% - 36px); }
        .user-bubble, .bot-bubble { font-size: 13px; }
        .result-title { font-size: 12px; }
        .result-snippet { font-size: 10px; }
        [data-testid="stSidebar"] {
            width: min(86vw, 290px) !important;
            min-width: min(86vw, 290px) !important;
            max-width: min(86vw, 290px) !important;
        }
        [data-testid="stChatInput"] > div {
            max-width: 100% !important;
        }
        [data-testid="stChatInput"] textarea {
            font-size: 16px !important;
            padding: 14px 14px !important;
            min-height: 140px !important;
        }
        [data-testid="stChatInput"] button {
            margin: 8px 10px !important;
            width: 34px !important;
            height: 34px !important;
        }
        .welcome-wrap { padding: 48px 0 32px; }
    }
    </style>
    """
    if is_phone:
        css += """
        <style>
        .main-wrap {
            max-width: 100% !important;
            padding: 0 12px 170px !important;
        }
        [data-testid="stChatInput"] > div {
            max-width: 100% !important;
            margin: 0 !important;
        }
        [data-testid="stSidebar"] {
            width: min(84vw, 280px) !important;
            min-width: min(84vw, 280px) !important;
            max-width: min(84vw, 280px) !important;
            transform: none !important;
        }
        [data-testid="stSidebarCollapseButton"] {
            display: flex !important;
        }
        </style>
        """
    return css


# ------------------------------------------------------------------------------
# Helper functions
# ------------------------------------------------------------------------------
SUMMARY_SYSTEM_PROMPT = "explain the topic in 3-5 sentences, mention sources briefly."
DETAILED_SYSTEM_PROMPT = "first gather all relevant info from sources, then write a thorough multi-paragraph explanation with context, analysis, and explicit source citations."
FAST_SYSTEM_PROMPT = "return only 1-2 sentences of pure facts, zero explanation, zero commentary."

def get_mode_params(mode: str, base_max_tokens: int, base_context: int):
    if mode == "Fast":
        return FAST_SYSTEM_PROMPT, 100, max(5, int(base_context * 0.5))
    elif mode == "Detailed":
        return DETAILED_SYSTEM_PROMPT, 1200, int(base_context * 2.0)
    else: # Balanced
        return SUMMARY_SYSTEM_PROMPT, 350, base_context


def get_response_char_limit(length_label: str) -> int:
    if length_label == "Short":
        return 700
    if length_label == "Long":
        return 2200
    return 1200

REDIRECT_QUERY_KEYS = (
    "uddg",
    "url",
    "u",
    "target",
    "dest",
    "destination",
    "redirect",
    "redirect_url",
    "r",
)

KNOWN_REDIRECT_HOSTS = {
    "duckduckgo.com",
    "google.com",
    "bing.com",
    "search.yahoo.com",
    "r.search.yahoo.com",
    "l.facebook.com",
    "lm.facebook.com",
}


def detect_phone_device() -> bool:
    user_agent = ""
    try:
        headers = getattr(getattr(st, "context", None), "headers", None)
        if headers:
            user_agent = headers.get("user-agent") or headers.get("User-Agent") or ""
    except Exception:
        user_agent = ""
    return ua_is_phone(user_agent)


def normalize_result_url(raw_url: str) -> str:
    if not raw_url:
        return ""
    url = str(raw_url).strip()
    if not url:
        return ""
    if url.startswith("//"):
        url = f"https:{url}"
    if "://" not in url and not url.startswith("/") and "." in url.split("/")[0]:
        url = f"https://{url}"
    if url.startswith("/") and "uddg=" in url:
        url = f"https://duckduckgo.com{url}"
    if url.startswith("/"):
        local_params = parse_qs(urlparse(url).query)
        for key in (*REDIRECT_QUERY_KEYS, "q"):
            values = local_params.get(key)
            if not values:
                continue
            candidate = unquote(values[0]).strip()
            if candidate.startswith("//"):
                candidate = f"https:{candidate}"
            if "://" not in candidate and candidate.startswith("www."):
                candidate = f"https://{candidate}"
            if urlparse(candidate).scheme in {"http", "https"}:
                url = candidate
                break

    for _ in range(3):
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            return ""
        host = parsed.netloc.lower()
        if host.startswith("www."):
            host = host[4:]
        query_params = parse_qs(parsed.query)
        unwrapped = ""
        if host in KNOWN_REDIRECT_HOSTS or any(k in query_params for k in REDIRECT_QUERY_KEYS):
            for key in REDIRECT_QUERY_KEYS:
                values = query_params.get(key)
                if not values:
                    continue
                candidate = unquote(values[0]).strip()
                if candidate.startswith("//"):
                    candidate = f"https:{candidate}"
                if "://" not in candidate and candidate.startswith("www."):
                    candidate = f"https://{candidate}"
                candidate_parsed = urlparse(candidate)
                if candidate_parsed.scheme in {"http", "https"}:
                    unwrapped = candidate
                    break
        if not unwrapped or unwrapped == url:
            break
        url = unwrapped
    return url


def normalize_results(results: list) -> list:
    cleaned = []
    seen = set()
    for r in results:
        title = (r.get("title") or "").strip()
        snippet = (r.get("snippet") or "").strip()
        source = (r.get("source") or "").strip()
        url = normalize_result_url(r.get("url", ""))
        key = url or f"{title}|{source}"
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(
            {
                "title": title,
                "url": url,
                "snippet": snippet,
                "source": source,
            }
        )
    return cleaned


def build_results_context(results: list, max_items: int = 6, max_snippet_chars: int = 280):
    lines = []
    for i, r in enumerate(results[:max_items], 1):
        lines.append(
            f"{i}. {r.get('title', '')}\n"
            f"   URL: {r.get('url', '')}\n"
            f"   {(r.get('snippet', '') or '')[:max_snippet_chars]}"
        )
    return "\n\n".join(lines)


def format_summary_text(text: str, max_chars: int = 900) -> str:
    cleaned = (text or "").strip()
    if len(cleaned) <= max_chars:
        return cleaned
    clipped = cleaned[:max_chars].rsplit(" ", 1)[0]
    return f"{clipped}..."


def html_text(text: str) -> str:
    return escape((text or "").strip()).replace("\n", "<br>")


init_session()
settings = st.session_state.settings
is_phone = detect_phone_device()

# Render CSS with current dark mode
st.markdown(render_css(st.session_state.dark_mode, is_phone=is_phone), unsafe_allow_html=True)

# Render loading screen only once – stays until UI is ready
if not st.session_state.loading_screen_rendered:
    st.markdown("""
    <div id="initial-loading-screen">
        <div class="loader-icon">◈</div>
        <div class="loader-text">Loading interface...</div>
    </div>
    <script>
        function removeLoadingScreen() {
            const loader = document.getElementById('initial-loading-screen');
            if (loader) {
                loader.classList.add('fade-out');
                setTimeout(() => loader.remove(), 500);
            }
        }
        // Wait for the chat input to appear
        const observer = new MutationObserver((mutations, obs) => {
            if (document.querySelector('[data-testid="stChatInput"] textarea')) {
                removeLoadingScreen();
                obs.disconnect();
            }
        });
        observer.observe(document.body, { childList: true, subtree: true });
        // Fallback: remove after 5 seconds anyway
        setTimeout(removeLoadingScreen, 5000);
    </script>
    """, unsafe_allow_html=True)
    st.session_state.loading_screen_rendered = True


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


def search_web(query: str, server: str, max_results: int, timeout_s: int = 20, all_endpoint_limit: int = 3):
    endpoints = [f"{server}/search", f"{server}/search/all"]
    for url in endpoints:
        try:
            with httpx.Client(timeout=timeout_s) as client:
                endpoint_max_results = all_endpoint_limit if "/all" in url else max_results
                params = {"q": query, "max_results": max(1, int(endpoint_max_results))}
                resp = client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
                results = normalize_results(data.get("results", []))
                backend = data.get("backend_used", data.get("backends_queried", ["unknown"]))
                if isinstance(backend, list):
                    backend = ", ".join(backend)
                if results:
                    return results[:max_results * 2], backend
        except Exception:
            continue
    return [], "none"


def ai_summarize_groq(
    query: str,
    results: list,
    model: str,
    mode: str,
    temperature: float = 0.2,
    max_tokens_override: int | None = None,
    context_items_override: int | None = None,
    context_snippet_chars: int | None = None,
    response_char_limit: int = 1200,
):
    sys_prompt, default_max_tokens, default_max_items = get_mode_params(mode, 320, 6)
    max_tokens = max_tokens_override if max_tokens_override else default_max_tokens
    max_items = context_items_override if context_items_override else default_max_items
    max_snippet_chars = context_snippet_chars if context_snippet_chars else 280
    context = build_results_context(
        results,
        max_items=max(1, int(max_items)),
        max_snippet_chars=max(80, int(max_snippet_chars)),
    )

    api_key = get_next_groq_key()
    if not api_key:
        return None
    client = Groq(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": sys_prompt,
            },
            {"role": "user", "content": f"Query: {query}\n\nResults:\n{context}"},
        ],
        max_tokens=max(64, int(max_tokens)),
        temperature=temperature,
    )
    return format_summary_text(response.choices[0].message.content, max_chars=max(300, int(response_char_limit)))


def ai_summarize_ollama(
    query: str,
    results: list,
    model: str,
    ollama_url: str,
    mode: str,
    temperature: float = 0.2,
    num_predict_override: int | None = None,
    context_items_override: int | None = None,
    context_snippet_chars: int | None = None,
    context_length_override: int | None = None,
    top_p: float = 0.9,
    keep_alive: str = "20m",
    timeout_s_override: int | None = None,
    response_char_limit: int = 1200,
):
    sys_prompt, default_num_predict, default_max_items = get_mode_params(mode, 320, 8)
    num_predict = num_predict_override if num_predict_override else default_num_predict
    max_items = context_items_override if context_items_override else default_max_items
    max_snippet_chars = context_snippet_chars if context_snippet_chars is not None else (220 if mode == "Fast" else 400)
    context = build_results_context(
        results,
        max_items=max(1, int(max_items)),
        max_snippet_chars=max(80, int(max_snippet_chars)),
    )
    num_ctx = context_length_override if context_length_override else (2048 if mode == "Fast" else (8192 if mode == "Detailed" else 4096))
    options = {
        "temperature": temperature,
        "top_p": max(0.1, min(1.0, float(top_p))),
        "num_predict": max(64, int(num_predict)),
        "num_ctx": max(512, int(num_ctx)),
    }
    timeout_s = timeout_s_override if timeout_s_override else (40 if mode == "Fast" else (120 if mode == "Detailed" else 60))

    try:
        with httpx.Client(timeout=timeout_s) as client:
            resp = client.post(
                f"{ollama_url}/api/chat",
                json={
                    "model": model,
                    "messages": [
                        {
                            "role": "system",
                            "content": sys_prompt,
                        },
                        {"role": "user", "content": f"Query: {query}\n\nResults:\n{context}"},
                    ],
                    "stream": False,
                    "keep_alive": keep_alive or "20m",
                    "options": options,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return format_summary_text(data.get("message", {}).get("content", ""), max_chars=max(300, int(response_char_limit)))
    except Exception:
        return None


def check_search_server_health(url: str) -> bool:
    try:
        with httpx.Client(timeout=3) as c:
            c.get(f"{url}/health")
        return True
    except Exception:
        return False

def check_ollama_health(url: str) -> bool:
    try:
        with httpx.Client(timeout=3) as c:
            c.get(f"{url}/api/tags")
        return True
    except Exception:
        return False

def get_ollama_models(url: str) -> list:
    try:
        with httpx.Client(timeout=3) as c:
            r = c.get(f"{url}/api/tags")
            if r.status_code == 200:
                return [m["name"] for m in r.json().get("models", [])]
    except Exception:
        pass
    return []

def refresh_ollama_cache(url: str, force: bool = False):
    now = time.time()
    normalized_url = (url or "").rstrip("/")
    cached_url = st.session_state.get("cached_ollama_url", "")
    stale = now - st.session_state.get("last_ollama_check", 0.0) > 15
    should_refresh = force or stale or normalized_url != cached_url

    if should_refresh:
        st.session_state.cached_ollama_ok = check_ollama_health(normalized_url)
        st.session_state.cached_ollama_models = get_ollama_models(normalized_url)
        st.session_state.cached_ollama_url = normalized_url
        st.session_state.last_ollama_check = now


def pick_ollama_model(models: list[str], current_model: str) -> str:
    if not models:
        return current_model or ""
    if current_model in models:
        return current_model
    preferred = ["qwen2.5", "qwen3", "llama3.2", "llama3.1", "mistral", "gemma3"]
    model_lut = {m.lower(): m for m in models}
    for base in preferred:
        for name_lc, original in model_lut.items():
            if name_lc == base or name_lc.startswith(base + ":"):
                return original
    return models[0]


# ---- Optimized sidebar: cached status checks ----
# Refresh health cache every 30 seconds (on demand)
def refresh_health_cache():
    now = time.time()
    if now - st.session_state.last_health_check > 30:
        st.session_state.cached_server_ok = check_search_server_health(settings["search_server"])
        refresh_ollama_cache(settings["ollama_url"], force=True)
        st.session_state.last_health_check = now

# Call once per render (lightweight check of timestamp)
refresh_health_cache()


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

    # ── Settings & AI Configuration ─────────────────────────────────────────────
    with st.expander("🤖 AI Engine", expanded=st.session_state.exp_ai):
        settings["provider"] = st.radio(
            "Provider",
            options=["groq", "ollama"],
            format_func=lambda x: "Groq Cloud" if x == "groq" else "Ollama Local",
            index=0 if settings["provider"] == "groq" else 1,
            label_visibility="collapsed",
        )

        modes = ["Fast", "Balanced", "Detailed"]
        settings["response_mode"] = st.selectbox(
            "AI Output Mode (Detail Level)",
            modes,
            index=modes.index(settings.get("response_mode", "Balanced")) if settings.get("response_mode") in modes else 1,
            help="Fast: Direct answer, no AI explanation. Balanced: Fetches info and roughly explains. Detailed: Fetches info and explains deeply."
        )
        
        settings["temperature"] = st.slider(
            "Creativity level", 0.0, 1.0, settings.get("temperature", 0.2), 0.1,
            help="Low = consistent and factual. High = more varied and creative."
        )

        if settings["provider"] == "ollama":
            prev_ollama_url = settings["ollama_url"]
            settings["ollama_url"] = st.text_input(
                "Ollama URL",
                value=settings["ollama_url"],
                placeholder="http://localhost:11434",
            )
            url_changed = settings["ollama_url"] != prev_ollama_url
            refresh_ollama_cache(settings["ollama_url"], force=url_changed)

            # Use cached models (auto-detected)
            models = st.session_state.cached_ollama_models
            if models:
                settings["ollama_model"] = pick_ollama_model(models, settings.get("ollama_model", ""))
                st.markdown(
                    f'<div class="status-pill ok"><span class="status-dot ok"></span>{len(models)} models detected · using {settings["ollama_model"]}</div>',
                    unsafe_allow_html=True,
                )
                settings["ollama_model"] = st.selectbox(
                    "Model (auto-detected)",
                    models,
                    index=models.index(settings["ollama_model"]) if settings["ollama_model"] in models else 0,
                )
            else:
                # Show warning but don't block UI
                st.markdown('<div class="status-pill warn"><span class="status-dot pulse"></span>No models — run: ollama pull qwen2.5</div>', unsafe_allow_html=True)
        else:
            settings["groq_keys"] = st.text_area(
                "API Keys (one per line)",
                value=settings["groq_keys"],
                height=100,
                placeholder="gsk_...\\ngsk_...",
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
                index=groq_models.index(settings["groq_model"]) if settings["groq_model"] in groq_models else 0,
            )
            keys = get_groq_keys()
            if keys:
                st.markdown(f'<div class="status-pill ok"><span class="status-dot ok"></span>{len(keys)} key{"s" if len(keys) > 1 else ""} loaded {"· auto-rotating" if len(keys)>1 else ""}</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="status-pill err"><span class="status-dot err"></span>No API keys</div>', unsafe_allow_html=True)

    with st.expander("🔍 Search Settings", expanded=st.session_state.exp_search):
        settings["search_server"] = st.text_input(
            "Server URL",
            value=settings["search_server"],
            placeholder="http://localhost:8000",
        )
        settings["max_results"] = st.slider("Number of search results", 1, 10, settings["max_results"], help="More results = more info for the AI, but slightly slower")
        
        lengths = ["Short", "Medium", "Long"]
        settings["max_response_length"] = st.selectbox(
            "Answer length", 
            lengths,
            index=lengths.index(settings.get("max_response_length", "Medium")) if settings.get("max_response_length") in lengths else 1,
            help="Controls how much the AI writes"
        )
        
        regions = ["All", "US", "UK", "EU", "Asia"]
        settings["search_region"] = st.selectbox(
            "Search region",
            regions,
            index=regions.index(settings.get("search_region", "All")) if settings.get("search_region") in regions else 0,
            help="Limits results to a specific region"
        )

    with st.expander("🧪 Advanced Settings", expanded=st.session_state.exp_advanced):
        st.caption("Fine-tune context size, generation budget, and timeouts. Use 0 for Auto.")
        settings["context_results_limit"] = st.slider(
            "Context results sent to AI",
            0,
            20,
            int(settings.get("context_results_limit", 0)),
            help="How many search hits are included in the LLM prompt context. 0 = mode default.",
        )
        settings["context_snippet_chars"] = st.slider(
            "Snippet chars per result",
            0,
            1200,
            int(settings.get("context_snippet_chars", 0)),
            step=20,
            help="How much text per result is sent into AI context. 0 = mode default.",
        )
        settings["search_timeout_s"] = st.slider(
            "Search timeout (seconds)",
            5,
            90,
            int(settings.get("search_timeout_s", 20)),
            help="Timeout for calls to the search backend.",
        )
        settings["search_all_endpoint_limit"] = st.slider(
            "/search/all result cap",
            1,
            10,
            int(settings.get("search_all_endpoint_limit", 3)),
            help="Max results requested from fallback /search/all endpoint.",
        )

        if settings["provider"] == "groq":
            settings["groq_max_tokens"] = st.slider(
                "Groq max tokens",
                0,
                4096,
                int(settings.get("groq_max_tokens", 0)),
                step=32,
                help="Upper token budget for Groq responses. 0 = mode default.",
            )
        else:
            settings["ollama_num_predict"] = st.slider(
                "Ollama max output tokens",
                0,
                4096,
                int(settings.get("ollama_num_predict", 0)),
                step=32,
                help="Upper token budget for local Ollama generation. 0 = mode default.",
            )
            settings["ollama_context_length"] = st.slider(
                "Ollama context length",
                0,
                32768,
                int(settings.get("ollama_context_length", 0)),
                step=512,
                help="Larger context can improve quality but uses more RAM/VRAM. 0 = mode default.",
            )
            settings["ollama_top_p"] = st.slider(
                "Ollama top-p",
                0.1,
                1.0,
                float(settings.get("ollama_top_p", 0.9)),
                0.05,
                help="Lower values are more focused; higher values are more diverse.",
            )
            settings["ollama_keep_alive"] = st.text_input(
                "Ollama keep_alive",
                value=settings.get("ollama_keep_alive", "20m"),
                help="How long Ollama should keep the model loaded, e.g. 20m, 1h.",
            )
            settings["ollama_timeout_s"] = st.slider(
                "Ollama timeout (seconds)",
                0,
                240,
                int(settings.get("ollama_timeout_s", 0)),
                help="Timeout for Ollama generation requests. 0 = mode default.",
            )

    with st.expander("🩺 System Status", expanded=st.session_state.exp_status):
        # Use cached server health
        server_ok = st.session_state.cached_server_ok
        cls = "ok" if server_ok else "err"
        label = "Search server online" if server_ok else "Search server offline"
        st.markdown(f'<div class="status-pill {cls}"><span class="status-dot {cls}"></span>{label}</div>', unsafe_allow_html=True)

        if settings["provider"] == "ollama":
            ollama_ok = st.session_state.cached_ollama_ok
            cls2 = "ok" if ollama_ok else "err"
            label2 = "Ollama online" if ollama_ok else "Ollama offline"
            st.markdown(f'<div class="status-pill {cls2}"><span class="status-dot {cls2}"></span>{label2}</div>', unsafe_allow_html=True)

    with st.expander("⚙️ Behavior", expanded=st.session_state.exp_behavior):
        settings["auto_scroll"] = st.toggle("Auto-scroll to bottom", value=settings.get("auto_scroll", True))
        settings["show_sources"] = st.toggle("Show sources below answers", value=settings.get("show_sources", True))

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
        user_text = html_text(msg.get("content", ""))
        st.markdown(
            f"""
        <div class="msg-row user">
            <div class="msg-avatar user-av">YOU</div>
            <div class="msg-body">
                <div class="msg-label">You</div>
                <div class="user-bubble">{user_text}</div>
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

    else:
        provider_label = "OLLAMA" if msg.get("provider") == "ollama" else "GROQ"
        backend = (msg.get("backend", "") or "").strip()
        backend_safe = escape(backend)
        backend_str = f" · via {backend_safe}" if backend and backend != "none" else ""

        results_html = ""
        if msg.get("results") and settings.get("show_sources", True):
            results_html = '<div class="results-wrap"><div class="results-label">Sources</div>'
            for j, r in enumerate(msg["results"], 1):
                title = html_text(r.get("title", "No title"))
                url = normalize_result_url(r.get("url", ""))
                snippet = html_text(r.get("snippet", ""))
                source = html_text(r.get("source", ""))
                safe_url = escape(url, quote=True)
                link = (
                    f'<a class="result-title" href="{safe_url}" target="_blank" rel="noopener noreferrer">{title}</a>'
                    if safe_url
                    else f'<div class="result-title">{title}</div>'
                )
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

        summary = html_text(msg.get("ai_summary", ""))

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

    with st.spinner("Searching and synthesizing..."):
        response_char_limit = get_response_char_limit(settings.get("max_response_length", "Medium"))
        results, backend = search_web(
            prompt,
            settings["search_server"],
            settings["max_results"],
            timeout_s=int(settings.get("search_timeout_s", 20)),
            all_endpoint_limit=int(settings.get("search_all_endpoint_limit", 3)),
        )

        if results:
            summary = None
            if settings["provider"] == "ollama":
                ollama_num_predict = int(settings.get("ollama_num_predict", 0))
                context_results_limit = int(settings.get("context_results_limit", 0))
                context_snippet_chars = int(settings.get("context_snippet_chars", 0))
                ollama_context_length = int(settings.get("ollama_context_length", 0))
                ollama_timeout_s = int(settings.get("ollama_timeout_s", 0))
                summary = ai_summarize_ollama(
                    prompt,
                    results,
                    settings["ollama_model"],
                    settings["ollama_url"],
                    mode=settings.get("response_mode", "Balanced"),
                    temperature=settings.get("temperature", 0.2),
                    num_predict_override=ollama_num_predict if ollama_num_predict > 0 else None,
                    context_items_override=context_results_limit if context_results_limit > 0 else None,
                    context_snippet_chars=context_snippet_chars if context_snippet_chars > 0 else None,
                    context_length_override=ollama_context_length if ollama_context_length > 0 else None,
                    top_p=float(settings.get("ollama_top_p", 0.9)),
                    keep_alive=settings.get("ollama_keep_alive", "20m"),
                    timeout_s_override=ollama_timeout_s if ollama_timeout_s > 0 else None,
                    response_char_limit=response_char_limit,
                )
            else:
                groq_max_tokens = int(settings.get("groq_max_tokens", 0))
                context_results_limit = int(settings.get("context_results_limit", 0))
                context_snippet_chars = int(settings.get("context_snippet_chars", 0))
                summary = ai_summarize_groq(
                    prompt,
                    results,
                    settings["groq_model"],
                    mode=settings.get("response_mode", "Balanced"),
                    temperature=settings.get("temperature", 0.2),
                    max_tokens_override=groq_max_tokens if groq_max_tokens > 0 else None,
                    context_items_override=context_results_limit if context_results_limit > 0 else None,
                    context_snippet_chars=context_snippet_chars if context_snippet_chars > 0 else None,
                    response_char_limit=response_char_limit,
                )

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
