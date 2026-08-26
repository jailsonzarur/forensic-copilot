"""Estado da sessão e navegação entre telas.

O Streamlit re-executa o script inteiro a cada interação: todo estado vive no
``st.session_state`` e nada aqui presume execução linear.
"""

from __future__ import annotations

import streamlit as st

from config.exams import obter_exame
from config.schema import Exame

TELA_SELECAO = "selecao"
TELA_ADMIN = "admin"
TELA_CONVERSA = "conversa"
TELA_CONFIRMACAO = "confirmacao"
TELA_DOCUMENTO = "documento"

# Ordem do fluxo, usada pelo indicador de progresso.
FLUXO = (
    (TELA_SELECAO, "Tipo de exame"),
    (TELA_ADMIN, "Dados administrativos"),
    (TELA_CONVERSA, "Conversa"),
    (TELA_CONFIRMACAO, "Confirmação"),
    (TELA_DOCUMENTO, "Minuta"),
)


def init_state() -> None:
    """Cria as chaves do estado uma única vez."""
    st.session_state.setdefault("tela", TELA_SELECAO)
    st.session_state.setdefault("exame_id", None)
    st.session_state.setdefault("admin", {})
    st.session_state.setdefault("colecoes", {})  # chave -> list[dict] (camada 1)
    st.session_state.setdefault("colecoes_fechadas", [])  # o perito disse "não há mais"
    st.session_state.setdefault("imagens", [])  # anexos documentais
    st.session_state.setdefault("mensagens", [])  # histórico da conversa
    st.session_state.setdefault("fala_atual", None)  # pergunta que está no ar
    st.session_state.setdefault("ultima_extracao", "")  # JSON bruto, para depuração
    st.session_state.setdefault("derivados", {})  # camada 3, confirmada pelo perito


def ir_para(tela: str) -> None:
    st.session_state["tela"] = tela


def definir_exame(exame_id: str) -> None:
    """Fixa o tipo de exame e prepara as coleções da camada 1 vazias."""
    if st.session_state.get("exame_id") != exame_id:
        limpar_laudo()
    st.session_state["exame_id"] = exame_id
    exame = obter_exame(exame_id)
    st.session_state["colecoes"] = {c.chave: [] for c in exame.colecoes}
    st.session_state["colecoes_fechadas"] = []


def exame_atual() -> Exame | None:
    exame_id = st.session_state.get("exame_id")
    return obter_exame(exame_id) if exame_id else None


def limpar_laudo() -> None:
    """Descarta os dados do laudo, preservando a tela atual."""
    st.session_state["admin"] = {}
    st.session_state["colecoes"] = {}
    st.session_state["colecoes_fechadas"] = []
    st.session_state["imagens"] = []
    st.session_state["mensagens"] = []
    st.session_state["fala_atual"] = None
    st.session_state["ultima_extracao"] = ""
    st.session_state["derivados"] = {}


def indice_da_tela(tela: str) -> int:
    for i, (chave, _) in enumerate(FLUXO):
        if chave == tela:
            return i
    return 0
