"""Tela 3 — conversa (slot-filling).

PLACEHOLDER do Milestone 1: mostra o que já foi transcrito e o schema da
camada 1 que a conversa vai preencher. O loop de chat com extração de slots
entra no Milestone 2, depois que o schema for validado contra os laudos reais.
"""

from __future__ import annotations

import streamlit as st

from config.schema import Exame
from core.state import TELA_ADMIN, TELA_SELECAO, exame_atual, ir_para


def _painel_admin(exame: Exame) -> None:
    admin = st.session_state["admin"]
    rotulos = {c.chave: c.label for c in exame.campos_admin}
    preenchidos = {rotulos[k]: v for k, v in admin.items() if v}
    if preenchidos:
        st.dataframe(
            {"Campo": list(preenchidos), "Valor": list(preenchidos.values())},
            hide_index=True,
            width="stretch",
        )
    else:
        st.caption("Nenhum dado administrativo transcrito.")


def render() -> None:
    exame: Exame | None = exame_atual()
    if exame is None:
        ir_para(TELA_SELECAO)
        st.rerun()
        return

    st.header("Conversa")
    st.caption(f"{exame.label}")

    with st.expander("Dados administrativos transcritos", expanded=False):
        _painel_admin(exame)

    st.info(
        "Milestone 2 em construção: aqui entra o chat em que o perito descreve o "
        "material e os exames realizados, e o assistente extrai os campos da "
        "camada 1. O schema abaixo é o que será coletado."
    )

    for colecao in exame.colecoes:
        with st.expander(f"{colecao.label_plural} — {len(colecao.slots)} campos", expanded=True):
            st.caption(
                f"Coleção repetível, mínimo de {colecao.minimo} "
                f"{colecao.label_singular.lower()}."
                + ("  Aceita imagens como anexo." if colecao.aceita_imagens else "")
            )
            st.dataframe(
                {
                    "Campo": [s.label for s in colecao.slots],
                    "Obrigatório": [
                        "sim"
                        if s.obrigatorio
                        else (
                            f"se {s.obrigatorio_se[0]} = {s.obrigatorio_se[1]}"
                            if s.obrigatorio_se
                            else "não"
                        )
                        for s in colecao.slots
                    ],
                    "Pergunta dirigida": [s.pergunta for s in colecao.slots],
                },
                hide_index=True,
                width="stretch",
            )

    if st.button("Voltar"):
        ir_para(TELA_ADMIN)
        st.rerun()
