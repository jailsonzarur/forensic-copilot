"""Tela 3 — conversa de slot-filling (CAMADA 1).

O perito descreve; o extrator transcreve para o schema; o que faltar vira
pergunta dirigida. O avanço só libera quando não há pendência.
"""

from __future__ import annotations

import streamlit as st

from config.schema import Colecao, Exame
from core import conversa as controlador
from core import pendencias
from core.llm import chave_configurada, modelo
from core.state import (
    TELA_ADMIN,
    TELA_CONFIRMACAO,
    TELA_SELECAO,
    exame_atual,
    ir_para,
)


def _inicia_conversa(exame: Exame) -> None:
    if st.session_state["mensagens"]:
        return
    colecoes = st.session_state["colecoes"]
    fechadas = st.session_state["colecoes_fechadas"]
    st.session_state["fala_atual"] = controlador.proxima_fala(exame, colecoes, fechadas)
    st.session_state["mensagens"].append(
        {"role": "assistant", "content": controlador.saudacao(exame, colecoes, fechadas)}
    )


def _envia(exame: Exame, texto: str) -> None:
    st.session_state["mensagens"].append({"role": "user", "content": texto})
    resultado = controlador.processar(
        exame,
        st.session_state["colecoes"],
        st.session_state["colecoes_fechadas"],
        texto,
        st.session_state.get("fala_atual"),
    )
    st.session_state["fala_atual"] = resultado.fala
    st.session_state["ultima_extracao"] = resultado.bruto
    st.session_state["mensagens"].append(
        {
            "role": "assistant",
            "content": controlador.resposta_do_assistente(resultado),
        }
    )


def _tabela_colecao(colecao: Colecao, itens: list[dict]) -> None:
    if not itens:
        st.caption(f"Nenhum {colecao.label_singular.lower()} registrado.")
        return
    for indice, item in enumerate(itens, start=1):
        faltando = [
            s.label
            for s in colecao.slots
            if s.exigido_em(item) and not str(item.get(s.chave, "")).strip()
        ]
        marcador = "⚠️" if faltando else "✓"
        st.markdown(f"**{marcador} {colecao.label_singular} {indice}**")
        st.dataframe(
            {
                "Campo": [s.label for s in colecao.slots],
                "Valor": [item.get(s.chave, "") for s in colecao.slots],
            },
            hide_index=True,
            width="stretch",
        )
        if faltando:
            st.caption("Falta: " + ", ".join(faltando))


def _painel_estado(exame: Exame) -> None:
    colecoes = st.session_state["colecoes"]
    fechadas = st.session_state["colecoes_fechadas"]

    preenchidos, total = pendencias.resumo(exame, colecoes)
    st.progress(preenchidos / total if total else 0.0)
    st.caption(f"{preenchidos} de {total} campos obrigatórios preenchidos")

    for colecao in exame.colecoes:
        itens = colecoes.get(colecao.chave, [])
        st.subheader(colecao.label_plural)
        _tabela_colecao(colecao, itens)
        if colecao.chave in fechadas:
            st.caption(f"Encerrado — o perito informou que não há mais {colecao.label_plural.lower()}.")
            if st.button(
                f"Adicionar {colecao.label_singular.lower()}",
                key=f"reabrir_{colecao.chave}",
                help="Use se algum item ficou de fora ou a conversa encerrou cedo demais.",
            ):
                colecoes.setdefault(colecao.chave, []).append({})
                fechadas.remove(colecao.chave)
                fala = controlador.proxima_fala(exame, colecoes, fechadas)
                st.session_state["fala_atual"] = fala
                st.session_state["mensagens"].append(
                    {"role": "assistant", "content": fala.texto}
                )
                st.rerun()

    with st.expander("Última resposta bruta do extrator", expanded=False):
        st.caption(f"Modelo: {modelo()}")
        st.code(st.session_state.get("ultima_extracao") or "(nenhuma chamada ainda)", language="json")


def render() -> None:
    exame: Exame | None = exame_atual()
    if exame is None:
        ir_para(TELA_SELECAO)
        st.rerun()
        return

    st.header("Conversa")
    st.caption(
        f"{exame.label} — descreva o que você examinou. Só é registrado o que você "
        "disser; para corrigir um campo, basta informá-lo de novo."
    )

    with st.expander("Dados administrativos transcritos", expanded=False):
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

    if not chave_configurada():
        st.error(
            "OPENAI_API_KEY não encontrada. Copie o .env.example para .env e preencha "
            "a chave — sem ela a extração não roda."
        )
        if st.button("Voltar"):
            ir_para(TELA_ADMIN)
            st.rerun()
        return

    _inicia_conversa(exame)

    coluna_chat, coluna_estado = st.columns([3, 2], gap="large")

    with coluna_chat:
        for mensagem in st.session_state["mensagens"]:
            with st.chat_message(mensagem["role"]):
                st.markdown(mensagem["content"])

        texto = st.chat_input("Descreva o material ou o exame realizado…")
        if texto:
            with st.spinner("Registrando…"):
                _envia(exame, texto)
            st.rerun()

    with coluna_estado:
        st.markdown("### Estado coletado")
        _painel_estado(exame)

    completo = pendencias.completo(
        exame, st.session_state["colecoes"], st.session_state["colecoes_fechadas"]
    )
    st.divider()
    esquerda, direita = st.columns([1, 1])
    if esquerda.button("Voltar"):
        ir_para(TELA_ADMIN)
        st.rerun()
    if direita.button(
        "Avançar para confirmação",
        type="primary",
        disabled=not completo,
        help=None if completo else "Ainda há campos obrigatórios sem resposta.",
    ):
        ir_para(TELA_CONFIRMACAO)
        st.rerun()
