"""Estado da sessão e navegação entre telas.

O Streamlit re-executa o script inteiro a cada interação: todo estado vive no
``st.session_state`` e nada aqui presume execução linear.
"""

from __future__ import annotations

import streamlit as st

from config.exams import obter_exame
from config.schema import Exame
from core import persistencia

TELA_SELECAO = "selecao"
TELA_REQUISICAO = "requisicao"
TELA_ADMIN = "admin"
TELA_CONVERSA = "conversa"
TELA_CONFIRMACAO = "confirmacao"
TELA_DOCUMENTO = "documento"

# Ordem do fluxo, usada pelo indicador de progresso.
FLUXO = (
    (TELA_SELECAO, "Tipo de exame"),
    (TELA_REQUISICAO, "Requisição"),
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
    st.session_state.setdefault("requisicao", None)  # leitura do documento
    st.session_state.setdefault("quesitos", [])  # perguntas da autoridade
    st.session_state.setdefault("respostas_quesitos", {})  # redação do perito
    st.session_state.setdefault("colecoes", {})  # chave -> list[dict] (camada 1)
    st.session_state.setdefault("colecoes_fechadas", [])  # o perito disse "não há mais"
    st.session_state.setdefault("imagens", [])  # anexos documentais
    st.session_state.setdefault("mensagens", [])  # histórico da conversa
    st.session_state.setdefault("fala_atual", None)  # pergunta que está no ar
    st.session_state.setdefault("ultima_extracao", "")  # JSON bruto, para depuração
    st.session_state.setdefault("derivados", {})  # camada 3, confirmada pelo perito
    st.session_state.setdefault("derivados_origem", {})  # último valor vindo da regra
    st.session_state.setdefault("derivados_recalcular", [])  # pedidos de recálculo
    # Identidade do rascunho em disco. Nasce com a sessão para que o laudo
    # sobreviva a fechar a aba desde a primeira tecla, não só depois de salvo.
    st.session_state.setdefault("laudo_id", persistencia.novo_id())
    st.session_state.setdefault("estado_salvo", "")


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


def salvar_rascunho() -> None:
    """Grava o laudo em disco, mas só quando algo mudou.

    Chamada a cada execução do script. O Streamlit re-executa tudo a cada
    clique, então a assinatura do estado evita reescrever o mesmo arquivo
    dezenas de vezes. Falha de disco não pode derrubar a tela: o perito perde a
    rede, não o trabalho da sessão.
    """
    if not st.session_state.get("exame_id"):
        return  # nada a salvar antes de o perito escolher o tipo de exame
    assinatura = persistencia.assinatura_do_estado(st.session_state)
    if not assinatura or assinatura == st.session_state.get("estado_salvo"):
        return
    try:
        persistencia.salvar(st.session_state["laudo_id"], st.session_state)
        st.session_state["estado_salvo"] = assinatura
    except OSError:
        pass


def retomar_rascunho(laudo_id: str) -> bool:
    """Devolve um laudo salvo ao ``session_state``. False se não deu."""
    estado = persistencia.carregar(laudo_id)
    if estado is None:
        return False
    limpar_laudo()
    for chave, valor in estado.items():
        if valor is not None:
            st.session_state[chave] = valor
    st.session_state["laudo_id"] = laudo_id
    st.session_state["estado_salvo"] = persistencia.assinatura_do_estado(st.session_state)
    return True


def limpar_laudo() -> None:
    """Descarta os dados do laudo, preservando a tela atual."""
    st.session_state["admin"] = {}
    st.session_state["requisicao"] = None
    st.session_state["quesitos"] = []
    st.session_state["respostas_quesitos"] = {}
    st.session_state["colecoes"] = {}
    st.session_state["colecoes_fechadas"] = []
    st.session_state["imagens"] = []
    st.session_state["mensagens"] = []
    st.session_state["fala_atual"] = None
    st.session_state["ultima_extracao"] = ""
    st.session_state["derivados"] = {}
    st.session_state["derivados_origem"] = {}
    st.session_state["derivados_recalcular"] = []
    # Um laudo novo é outro rascunho: o anterior fica salvo em disco, intacto.
    st.session_state["laudo_id"] = persistencia.novo_id()
    st.session_state["estado_salvo"] = ""


def indice_da_tela(tela: str) -> int:
    for i, (chave, _) in enumerate(FLUXO):
        if chave == tela:
            return i
    return 0
