"""Gerador de Laudos Periciais com IA — entrypoint e roteador de telas.

A saída da ferramenta é sempre uma MINUTA: o perito revisa, edita e assina.
"""

from __future__ import annotations

import streamlit as st
from dotenv import load_dotenv

from core.state import (
    FLUXO,
    TELA_ADMIN,
    TELA_CONFIRMACAO,
    TELA_CONVERSA,
    TELA_DOCUMENTO,
    TELA_REQUISICAO,
    TELA_SELECAO,
    indice_da_tela,
    init_state,
    ir_para,
    limpar_laudo,
    salvar_rascunho,
)
from screens import admin, confirmacao, conversa, documento, requisicao, selecao

load_dotenv()

TELAS = {
    TELA_SELECAO: selecao.render,
    TELA_REQUISICAO: requisicao.render,
    TELA_ADMIN: admin.render,
    TELA_CONVERSA: conversa.render,
    TELA_CONFIRMACAO: confirmacao.render,
    TELA_DOCUMENTO: documento.render,
}


def _sidebar() -> None:
    with st.sidebar:
        st.subheader("Fluxo")
        atual = indice_da_tela(st.session_state["tela"])
        for i, (_, rotulo) in enumerate(FLUXO):
            marcador = "▶" if i == atual else ("✓" if i < atual else "·")
            st.write(f"{marcador} {rotulo}")

        st.divider()
        if st.button("Novo laudo"):
            limpar_laudo()
            st.session_state["exame_id"] = None
            ir_para(TELA_SELECAO)
            st.rerun()

        st.divider()
        st.caption(
            "A ferramenta só reformata o que o perito informou. O documento "
            "gerado é uma minuta sujeita a revisão e assinatura do perito."
        )


def main() -> None:
    st.set_page_config(page_title="Gerador de Laudos Periciais", page_icon="📄", layout="wide")
    init_state()

    st.title("Gerador de Laudos Periciais")
    _sidebar()

    render = TELAS.get(st.session_state["tela"])
    if render is None:
        st.warning(
            "A geração do .docx entra no Milestone 4. Os dados confirmados estão "
            "guardados na sessão."
        )
        destino = TELA_CONFIRMACAO if st.session_state.get("exame_id") else TELA_SELECAO
        if st.button("Voltar"):
            ir_para(destino)
            st.rerun()
        return
    render()
    # Depois de desenhar a tela, o que o perito ditou já está no estado: é a
    # hora certa de gravar. Antes da tela, gravaria a versão velha.
    salvar_rascunho()


if __name__ == "__main__":
    main()
