"""Tela 2 — formulário administrativo.

Transcrição pura: o perito digita o que está no procedimento. Nada aqui passa
pelo LLM e nenhum campo vem pré-preenchido — inclusive a data, que começa vazia
para não gravar um valor que o perito não conferiu.
"""

from __future__ import annotations

from datetime import date

import streamlit as st

from config.schema import CampoAdmin, Exame, GrupoAdmin
from core.state import TELA_CONVERSA, TELA_REQUISICAO, TELA_SELECAO, exame_atual, ir_para


def _renderiza_campo(campo: CampoAdmin, valores: dict, sufixo: str = "") -> object:
    label = campo.label + (" *" if campo.obrigatorio else "")
    salvo = valores.get(campo.chave)
    chave = f"admin_{campo.chave}{sufixo}"

    if campo.tipo == "data":
        inicial = date.fromisoformat(salvo) if salvo else None
        return st.date_input(
            label, value=inicial, format="DD/MM/YYYY", help=campo.ajuda or None, key=chave
        )
    if campo.tipo == "texto_longo":
        return st.text_area(label, value=salvo or "", help=campo.ajuda or None, key=chave)
    if campo.tipo == "select":
        opcoes = ["", *campo.opcoes]
        indice = opcoes.index(salvo) if salvo in opcoes else 0
        return st.selectbox(
            label, options=opcoes, index=indice, help=campo.ajuda or None, key=chave
        )
    return st.text_input(
        label,
        value=salvo or "",
        placeholder=campo.placeholder or None,
        help=campo.ajuda or None,
        key=chave,
    )


def _normaliza(valor: object) -> str:
    if valor is None:
        return ""
    if isinstance(valor, date):
        return valor.isoformat()
    return str(valor).strip()


def _entradas_do_grupo(grupo: GrupoAdmin) -> list[dict]:
    """Lista guardada no estado para um grupo repetível, com o mínimo garantido."""
    admin = st.session_state["admin"]
    entradas = admin.get(grupo.chave)
    if not isinstance(entradas, list):
        entradas = []
    while len(entradas) < max(grupo.minimo, 1):
        entradas.append({})
    admin[grupo.chave] = entradas
    return entradas


def _controles_do_grupo(grupo: GrupoAdmin) -> None:
    """Quantos blocos existem. Fora do formulário, para agir na hora."""
    entradas = _entradas_do_grupo(grupo)
    st.markdown(f"**{grupo.label_singular}**")
    esquerda, direita = st.columns([1, 1])
    limite = grupo.maximo or 99
    if esquerda.button(
        f"Adicionar {grupo.label_singular.lower()}",
        key=f"grupo_mais_{grupo.chave}",
        disabled=len(entradas) >= limite,
    ):
        entradas.append({})
        st.rerun()
    if direita.button(
        "Remover o último",
        key=f"grupo_menos_{grupo.chave}",
        disabled=len(entradas) <= max(grupo.minimo, 1),
    ):
        entradas.pop()
        st.rerun()


def _campos_do_grupo(grupo: GrupoAdmin) -> list[dict]:
    """Renderiza os blocos e devolve o que foi digitado em cada um."""
    entradas = _entradas_do_grupo(grupo)
    coletado: list[dict] = []
    for indice, entrada in enumerate(entradas, start=1):
        rotulo = f"{grupo.label_singular} {indice}" if len(entradas) > 1 else grupo.label_singular
        st.caption(rotulo)
        colunas = st.columns(max(len(grupo.campos), 1))
        valores: dict = {}
        for posicao, campo in enumerate(grupo.campos):
            with colunas[posicao % len(colunas)]:
                valores[campo.chave] = _renderiza_campo(
                    campo, entrada, sufixo=f"_{grupo.chave}_{indice}"
                )
        coletado.append(valores)
    return coletado


def render() -> None:
    exame: Exame | None = exame_atual()
    if exame is None:
        ir_para(TELA_SELECAO)
        st.rerun()
        return

    st.header("Dados administrativos")
    st.caption(f"{exame.label} — campos marcados com * são obrigatórios.")

    valores = st.session_state["admin"]

    for grupo in exame.grupos_admin:
        _controles_do_grupo(grupo)

    with st.form("form_admin"):
        colunas = st.columns(2)
        coletado: dict[str, object] = {}
        for i, campo in enumerate(exame.campos_admin):
            with colunas[i % 2]:
                coletado[campo.chave] = _renderiza_campo(campo, valores)

        coletado_grupos: dict[str, list[dict]] = {}
        for grupo in exame.grupos_admin:
            st.divider()
            coletado_grupos[grupo.chave] = _campos_do_grupo(grupo)

        esquerda, direita = st.columns([1, 1])
        voltar = esquerda.form_submit_button("Voltar")
        avancar = direita.form_submit_button("Continuar", type="primary")

    def _guardar() -> dict:
        normalizado = {k: _normaliza(v) for k, v in coletado.items()}
        for chave, entradas in coletado_grupos.items():
            normalizado[chave] = [
                {k: _normaliza(v) for k, v in entrada.items()} for entrada in entradas
            ]
        st.session_state["admin"] = normalizado
        return normalizado

    if voltar:
        _guardar()
        ir_para(TELA_REQUISICAO)
        st.rerun()

    if avancar:
        normalizado = _guardar()
        faltando = [
            c.label for c in exame.campos_admin if c.obrigatorio and not normalizado.get(c.chave)
        ]
        for grupo in exame.grupos_admin:
            for indice, entrada in enumerate(normalizado.get(grupo.chave, []), start=1):
                for campo in grupo.campos:
                    if campo.obrigatorio and not str(entrada.get(campo.chave, "")).strip():
                        faltando.append(f"{grupo.label_singular} {indice}: {campo.label}")
        if faltando:
            st.error("Pendências no formulário: " + ", ".join(faltando))
        else:
            ir_para(TELA_CONVERSA)
            st.rerun()
