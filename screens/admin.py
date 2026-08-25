"""Tela 2 — formulário administrativo.

Transcrição pura: o perito digita o que está no procedimento. Nada aqui passa
pelo LLM e nenhum campo vem pré-preenchido — inclusive a data, que começa vazia
para não gravar um valor que o perito não conferiu.
"""

from __future__ import annotations

from datetime import date

import streamlit as st

from config.schema import CampoAdmin, Exame
from core.state import TELA_CONVERSA, TELA_SELECAO, exame_atual, ir_para


def _renderiza_campo(campo: CampoAdmin, valores: dict) -> object:
    label = campo.label + (" *" if campo.obrigatorio else "")
    salvo = valores.get(campo.chave)

    if campo.tipo == "data":
        inicial = date.fromisoformat(salvo) if salvo else None
        return st.date_input(label, value=inicial, format="DD/MM/YYYY", help=campo.ajuda or None)
    if campo.tipo == "texto_longo":
        return st.text_area(label, value=salvo or "", help=campo.ajuda or None)
    if campo.tipo == "select":
        opcoes = ["", *campo.opcoes]
        indice = opcoes.index(salvo) if salvo in opcoes else 0
        return st.selectbox(label, options=opcoes, index=indice, help=campo.ajuda or None)
    return st.text_input(
        label,
        value=salvo or "",
        placeholder=campo.placeholder or None,
        help=campo.ajuda or None,
    )


def _normaliza(valor: object) -> str:
    if valor is None:
        return ""
    if isinstance(valor, date):
        return valor.isoformat()
    return str(valor).strip()


def render() -> None:
    exame: Exame | None = exame_atual()
    if exame is None:
        ir_para(TELA_SELECAO)
        st.rerun()
        return

    st.header("Dados administrativos")
    st.caption(f"{exame.label} — campos marcados com * são obrigatórios.")

    valores = st.session_state["admin"]

    with st.form("form_admin"):
        colunas = st.columns(2)
        coletado: dict[str, object] = {}
        for i, campo in enumerate(exame.campos_admin):
            with colunas[i % 2]:
                coletado[campo.chave] = _renderiza_campo(campo, valores)

        esquerda, direita = st.columns([1, 1])
        voltar = esquerda.form_submit_button("Voltar")
        avancar = direita.form_submit_button("Continuar", type="primary")

    if voltar:
        st.session_state["admin"] = {k: _normaliza(v) for k, v in coletado.items()}
        ir_para(TELA_SELECAO)
        st.rerun()

    if avancar:
        normalizado = {k: _normaliza(v) for k, v in coletado.items()}
        st.session_state["admin"] = normalizado
        faltando = [
            c.label for c in exame.campos_admin if c.obrigatorio and not normalizado.get(c.chave)
        ]
        if faltando:
            st.error("Pendências no formulário: " + ", ".join(faltando))
        else:
            ir_para(TELA_CONVERSA)
            st.rerun()
