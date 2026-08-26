"""Gerador de Laudos Periciais com IA — entrypoint e roteador de telas.

A saída da ferramenta é sempre uma MINUTA: o perito revisa, edita e assina.
"""

from __future__ import annotations

import streamlit as st
from dotenv import load_dotenv

from core.state import (
    FLUXO,
    TELA_ADMIN,
    TELA_CONVERSA,
    TELA_SELECAO,
    indice_da_tela,
    init_state,
    ir_para,
    limpar_laudo,
)
from screens import admin, conversa, selecao

load_dotenv()

TELAS = {
    TELA_SELECAO: selecao.render,
    TELA_ADMIN: admin.render,
    TELA_CONVERSA: conversa.render,
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
            "Etapa ainda não implementada. A confirmação entra no Milestone 3 e a "
            "geração do .docx no Milestone 4."
        )
        destino = TELA_CONVERSA if st.session_state.get("exame_id") else TELA_SELECAO
        if st.button("Voltar"):
            ir_para(destino)
            st.rerun()
        return
    render()


if __name__ == "__main__":
    main()
