"""Tela 1 — seleção do tipo de exame.

O select sai do registro (``config.exams``); o tipo escolhido governa todo o
resto do fluxo.
"""

from __future__ import annotations

import streamlit as st

from config.exams import EXAMES, listar_exames
from core import persistencia
from core.state import TELA_REQUISICAO, definir_exame, ir_para, retomar_rascunho


def _rascunhos_salvos() -> None:
    """Laudos em andamento nesta máquina, para o perito retomar de onde parou.

    O laudo é salvo sozinho a cada passo. Isso existe porque fechar a aba, a
    página recarregar ou a ferramenta reiniciar apagava tudo — e recomeçar um
    laudo é a chance de o perito digitar diferente da segunda vez.
    """
    salvos = persistencia.listar()
    if not salvos:
        return

    st.subheader("Continuar um laudo")
    st.caption(
        f"{len(salvos)} laudo(s) em andamento nesta máquina. Ficam salvos aqui "
        "no computador, não saem dele, e você pode descartar quando quiser."
    )

    for rascunho in salvos:
        exame = EXAMES.get(rascunho.exame_id)
        rotulo = exame.label if exame is not None else rascunho.exame_id or "tipo desconhecido"
        with st.container(border=True):
            coluna_texto, coluna_abrir, coluna_apagar = st.columns([4, 1, 1])
            with coluna_texto:
                st.markdown(f"**{rascunho.rotulo}** — {rotulo}")
                st.caption(
                    f"{rascunho.campos_preenchidos} campo(s) preenchido(s) · "
                    f"salvo em {rascunho.quando()}"
                )
            with coluna_abrir:
                if st.button("Continuar", key=f"retomar_{rascunho.id}"):
                    if retomar_rascunho(rascunho.id):
                        st.rerun()
                    else:
                        st.error(
                            "Não consegui abrir este rascunho. O arquivo pode "
                            "estar danificado — avise quem instalou a ferramenta."
                        )
            with coluna_apagar:
                if st.button("Descartar", key=f"descartar_{rascunho.id}"):
                    persistencia.descartar(rascunho.id)
                    st.rerun()

    st.divider()


def render() -> None:
    _rascunhos_salvos()

    st.header("Tipo de exame")
    st.caption("O tipo escolhido define os campos do formulário e as perguntas da conversa.")

    exames = listar_exames()
    disponiveis = [e for e in exames if e.disponivel]
    if not disponiveis:
        st.error("Nenhum tipo de exame está cadastrado na ferramenta.")
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
        ir_para(TELA_REQUISICAO)
        st.rerun()
