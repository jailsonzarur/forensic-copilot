"""Tela 3 — conversa de slot-filling (CAMADA 1).

O perito descreve; o extrator transcreve para o schema; o que faltar vira
pergunta dirigida. O avanço só libera quando não há pendência.
"""

from __future__ import annotations

import streamlit as st

from config.schema import Colecao, Exame
from core import conversa as controlador
from core import pendencias
from core import pergunta as formulador
from core import quesitos as camada1_quesitos
from core.llm import chave_configurada, modelo
from core.state import (
    TELA_ADMIN,
    TELA_CONFIRMACAO,
    TELA_SELECAO,
    exame_atual,
    ir_para,
)


def _fala_para_o_perito(fala: controlador.Fala) -> str:
    """Texto exibido. Só a forma da pergunta passa por leitura automática; o
    que falta continua sendo decidido pela varredura de pendências."""
    if fala.tipo != controlador.PERGUNTA or len(fala.campos_faltando) < 2:
        return fala.texto
    return formulador.formular(fala.rotulo_item, list(fala.campos_faltando), fala.texto)


def _inicia_conversa(exame: Exame) -> None:
    if st.session_state["mensagens"]:
        return
    colecoes = st.session_state["colecoes"]
    fechadas = st.session_state["colecoes_fechadas"]
    quesitos = st.session_state["quesitos"]
    respostas = st.session_state["respostas_quesitos"]
    st.session_state["fala_atual"] = controlador.proxima_fala(
        exame, colecoes, fechadas, quesitos, respostas
    )
    fala = st.session_state["fala_atual"]
    abertura = (
        "Vamos registrar o que você examinou. Pode falar como você fala — eu só "
        "anoto o que você disser, e pergunto o que faltar."
    )
    st.session_state["mensagens"].append(
        {"role": "assistant", "content": f"{abertura}\n\n{_fala_para_o_perito(fala)}"}
    )


def _envia(exame: Exame, texto: str) -> None:
    st.session_state["mensagens"].append({"role": "user", "content": texto})
    resultado = controlador.processar(
        exame,
        st.session_state["colecoes"],
        st.session_state["colecoes_fechadas"],
        texto,
        st.session_state.get("fala_atual"),
        quesitos=st.session_state["quesitos"],
        respostas=st.session_state["respostas_quesitos"],
    )
    st.session_state["fala_atual"] = resultado.fala
    st.session_state["ultima_extracao"] = resultado.bruto
    partes = controlador.resposta_do_assistente(resultado)
    # A fala determinística já está no fim do texto; troca-se só a pergunta.
    natural = _fala_para_o_perito(resultado.fala)
    if natural != resultado.fala.texto:
        partes = partes.replace(resultado.fala.texto, natural)
    st.session_state["mensagens"].append({"role": "assistant", "content": partes})


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

    preenchidos, total = pendencias.resumo(exame, colecoes, so_conversa=True)
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
                help="Use se esqueceu de algum item ou encerrou antes da hora.",
            ):
                colecoes.setdefault(colecao.chave, []).append({})
                fechadas.remove(colecao.chave)
                fala = controlador.proxima_fala(
                    exame, colecoes, fechadas, st.session_state["quesitos"],
                    st.session_state["respostas_quesitos"],
                )
                st.session_state["fala_atual"] = fala
                st.session_state["mensagens"].append(
                    {"role": "assistant", "content": fala.texto}
                )
                st.rerun()

    perguntas = st.session_state["quesitos"]
    if perguntas:
        respondidos = sum(
            1 for q in camada1_quesitos.numerar(perguntas)
            if camada1_quesitos.respondido(q.numero, st.session_state["respostas_quesitos"])
        )
        st.subheader("Quesitos da requisição")
        st.caption(f"{respondidos} de {len(perguntas)} respondidos por você.")

    with st.expander("Detalhes técnicos da última leitura", expanded=False):
        st.caption(
            "Só serve para diagnóstico, se a ferramenta estiver entendendo errado. "
            f"Serviço em uso: {modelo()}."
        )
        st.code(
            st.session_state.get("ultima_extracao") or "(nenhuma leitura ainda)",
            language="json",
        )


def render() -> None:
    exame: Exame | None = exame_atual()
    if exame is None:
        ir_para(TELA_SELECAO)
        st.rerun()
        return

    st.header("Conversa")
    st.caption(
        f"{exame.label} — conte o que você examinou, do seu jeito. Só vai para o "
        "laudo o que você disser. Para corrigir algo, é só falar de novo."
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
            "A ferramenta não está configurada para conversar. Avise quem a instalou: "
            "falta cadastrar a chave de acesso (OPENAI_API_KEY no arquivo .env)."
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

    # so_conversa: a referência entre coleções é escolhida pelo perito na
    # confirmação, então cobrá-la aqui travava o avanço para sempre.
    completo = (
        controlador.proxima_fala(
            exame,
            st.session_state["colecoes"],
            st.session_state["colecoes_fechadas"],
            st.session_state["quesitos"],
            st.session_state["respostas_quesitos"],
        ).tipo
        == controlador.COMPLETO
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
