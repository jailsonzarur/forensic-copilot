"""Tela 5 — minuta gerada.

Última parada: o perito vê o que foi montado, baixa o .docx, revisa no Word,
edita e assina. A responsabilidade legal pelo conteúdo é dele.
"""

from __future__ import annotations

from datetime import date

import streamlit as st

from config.schema import Exame
from core import documento as montador
from core.state import TELA_CONFIRMACAO, TELA_SELECAO, exame_atual, ir_para


def _nome_arquivo(admin: dict) -> str:
    bruto = (admin.get("numero_laudo") or admin.get("numero_demanda") or "laudo").strip()
    limpo = "".join(c if c.isalnum() else "_" for c in bruto).strip("_")
    return f"minuta_{limpo or 'laudo'}_{date.today().isoformat()}.docx"


def render() -> None:
    exame: Exame | None = exame_atual()
    if exame is None:
        ir_para(TELA_SELECAO)
        st.rerun()
        return

    admin = st.session_state["admin"]
    colecoes = st.session_state["colecoes"]
    derivados = st.session_state["derivados"]
    imagens = st.session_state["imagens"]

    st.header("Minuta")
    st.caption(
        "Documento montado com o que você confirmou. É uma MINUTA: revise no "
        "editor, complete o que estiver assinalado e assine."
    )

    quesitos = st.session_state["quesitos"]
    respostas = st.session_state["respostas_quesitos"]
    pendencias = montador.pendencias_do_texto(
        admin, colecoes, derivados, quesitos, respostas
    )
    if pendencias:
        st.warning(
            "A minuta sai com marcadores em vermelho onde falta redação transcrita "
            "de laudo real:\n\n"
            + "\n".join(f"- {p}" for p in pendencias)
            + "\n\nEsses trechos precisam da sua redação antes de assinar."
        )

    try:
        arquivo = montador.em_bytes(
            montador.montar(
                admin, colecoes, derivados, imagens, quesitos, respostas, exame=exame
            )
        )
    except Exception as erro:  # falha de montagem é da ferramenta, não do perito
        st.error(f"Falha da ferramenta ao montar o documento: {erro}")
        if st.button("Voltar à confirmação"):
            ir_para(TELA_CONFIRMACAO)
            st.rerun()
        return

    st.download_button(
        "Baixar minuta (.docx)",
        data=arquivo,
        file_name=_nome_arquivo(admin),
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        type="primary",
    )
    st.caption(f"{len(arquivo) // 1024} KB · {len(imagens)} imagem(ns) embutida(s)")

    with st.expander("Conferir o que foi para o documento", expanded=True):
        for chave, rotulo in (
            ("numero_laudo", "Laudo n°"),
            ("numero_demanda", "Demanda"),
        ):
            st.write(f"**{rotulo}:** {admin.get(chave, '') or '—'}")
        objeto = exame.colecao_objeto() if exame is not None else None
        st.write(f"**{objeto.label_plural if objeto is not None else 'Materiais'}**")
        for indice, _ in enumerate(
            colecoes.get(objeto.chave if objeto is not None else "materiais", []), start=1
        ):
            chave = f"descricao_material_{indice}"
            st.write(f"{chr(ord('a') + indice - 1)}) " + (derivados.get(chave) or ""))
        st.write("**Conclusão**")
        st.write(derivados.get("conclusao", ""))

    if st.button("Voltar à confirmação"):
        ir_para(TELA_CONFIRMACAO)
        st.rerun()
