"""Tela 1 — seleção do tipo de exame.

O select sai do registro (``config.exams``); o tipo escolhido governa todo o
resto do fluxo.
"""

from __future__ import annotations

import streamlit as st

from config.exams import listar_exames
from core.state import TELA_ADMIN, definir_exame, ir_para


def render() -> None:
    st.header("Tipo de exame")
    st.caption("O tipo escolhido define os campos do formulário e as perguntas da conversa.")

    exames = listar_exames()
    disponiveis = [e for e in exames if e.disponivel]
    if not disponiveis:
        st.error("Nenhum tipo de exame cadastrado no registro.")
        return

    ids = [e.id for e in disponiveis]
    atual = st.session_state.get("exame_id")
    indice = ids.index(atual) if atual in ids else 0

    escolhido_id = st.selectbox(
        "Selecione o exame",
        options=ids,
        index=indice,
        format_func=lambda i: next(e.label for e in disponiveis if e.id == i),
    )
    escolhido = next(e for e in disponiveis if e.id == escolhido_id)
    st.info(escolhido.descricao)

    if st.button("Continuar", type="primary"):
        definir_exame(escolhido.id)
        ir_para(TELA_ADMIN)
        st.rerun()
