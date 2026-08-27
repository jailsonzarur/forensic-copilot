"""Tela 2 — a requisição da autoridade.

O laudo pericial não nasce do nada: nasce da requisição de um delegado, que
descreve o material apreendido e **formula os quesitos**. Aqui o documento é
anexado e lido, e o que ele contiver é PROPOSTO para o formulário.

Proposto, não preenchido: numa digitalização, a leitura é feita por modelo e
já se mostrou capaz de reescrever um quesito inteiro sem avisar. O perito tem
o papel na mão — quem confirma é ele.
"""

from __future__ import annotations

import streamlit as st

from config.schema import Exame
from core import requisicao as leitor
from core.llm import chave_configurada
from core.state import TELA_ADMIN, TELA_SELECAO, exame_atual, ir_para
from templates.identificacao_substancia import boilerplate


def _aviso_de_confianca(leitura: leitor.Leitura) -> None:
    if leitura.nivel == "exata":
        st.success(
            "Lido da camada de texto do PDF — é o texto exato do documento, sem "
            "OCR no meio. Confira mesmo assim."
        )
        return

    if leitura.nivel == "ocr":
        giros = ", ".join(f"{g}°" for g in leitura.rotacoes if g)
        detalhe = f" A página foi endireitada ({giros})." if giros else ""
        st.warning(
            "**Lido por OCR do documento digitalizado.**" + detalhe + " O OCR erra "
            "trocando caracteres — troca de letra, `@` que vira outra coisa, "
            "acento perdido. Esse tipo de erro fica visível na transcrição abaixo: "
            "leia-a de olho no papel antes de confirmar."
        )
        return

    st.error(
        f"**Sem OCR nesta máquina — leitura feita pelo modelo, {leitura.passes} "
        "vezes e cruzada.** Este é o caminho mais frágil: em teste com uma "
        "requisição real, três leituras devolveram três redações diferentes para "
        "o mesmo quesito e nenhuma batia com o papel. Instale o Tesseract "
        "(`brew install tesseract tesseract-lang`) para uma leitura melhor. "
        "**Confira campo por campo contra o documento.**"
    )


def _campos_propostos(exame: Exame, leitura: leitor.Leitura) -> dict[str, str]:
    st.subheader("Campos encontrados")
    if not leitura.campos:
        st.caption("Nenhum campo pôde ser transcrito com segurança.")
        return {}

    rotulos = {c.chave: c for c in exame.campos_admin}
    aceitos: dict[str, str] = {}
    for chave, valor in leitura.campos.items():
        campo = rotulos.get(chave)
        if campo is None:
            continue
        novo = st.text_input(
            campo.label,
            value=valor,
            key=f"req_campo_{chave}",
            help="Apague se não corresponder ao documento.",
        )
        trecho = leitura.trechos.get(chave, "")
        if trecho:
            st.caption(f"Lido de: «{trecho}»")
        if novo.strip():
            aceitos[chave] = novo.strip()
    return aceitos


def _quesitos_propostos(leitura: leitor.Leitura) -> list[str]:
    st.subheader("Quesitos formulados pela autoridade")
    st.caption(
        "São as perguntas que o laudo tem que responder. Copie do documento "
        "palavra por palavra — quesito errado faz o laudo responder o que "
        "ninguém perguntou."
    )

    base = leitura.quesitos or [""] * 6
    perguntas: list[str] = []
    for posicao, pergunta in enumerate(base, start=1):
        instavel = not pergunta.strip()
        rotulo = f"Quesito {posicao:02d}" + (" — leitura falhou, transcreva" if instavel else "")
        texto = st.text_area(
            rotulo,
            value=pergunta,
            key=f"req_quesito_{posicao}",
            height=80,
        )
        if texto.strip():
            perguntas.append(texto.strip())
            if not leitor.boilerplate.RESPOSTAS_CONHECIDAS.get(
                boilerplate.normaliza(texto.strip())
            ):
                st.caption(
                    "Sem padrão de resposta transcrito de laudo real — você "
                    "responde este quesito na confirmação."
                )
    return perguntas


def _sem_documento(exame: Exame) -> None:
    st.caption(
        "Sem requisição anexada, o formulário começa vazio e os quesitos entram "
        "como o conjunto que apareceu na requisição do laudo de referência — "
        "confira contra o seu papel antes de seguir."
    )
    if st.button("Preencher na mão, sem anexar"):
        st.session_state["quesitos"] = list(boilerplate.QUESITOS_DA_REQUISICAO_MODELO)
        st.session_state["requisicao"] = {"origem": "não anexada", "texto": ""}
        ir_para(TELA_ADMIN)
        st.rerun()


def render() -> None:
    exame: Exame | None = exame_atual()
    if exame is None:
        ir_para(TELA_SELECAO)
        st.rerun()
        return

    st.header("Requisição")
    st.caption(
        "Anexe o ofício ou requisição que originou o exame. Dele saem os "
        "quesitos e parte do formulário. O que não estiver no documento fica "
        "vazio — nada é preenchido por suposição."
    )

    arquivo = st.file_uploader(
        "Requisição (PDF ou imagem)",
        type=["pdf", "png", "jpg", "jpeg"],
        key="upload_requisicao",
    )

    if arquivo is not None and st.button("Ler requisição", type="primary"):
        if not chave_configurada() and not arquivo.name.lower().endswith(".pdf"):
            st.error("Ler imagem exige OPENAI_API_KEY configurada.")
        else:
            with st.spinner("Lendo o documento…"):
                leitura = leitor.ler(exame, arquivo.getvalue(), arquivo.name)
            st.session_state["leitura_requisicao"] = leitura

    leitura: leitor.Leitura | None = st.session_state.get("leitura_requisicao")
    if leitura is None:
        _sem_documento(exame)
        if st.button("Voltar"):
            ir_para(TELA_SELECAO)
            st.rerun()
        return

    if leitura.erro:
        st.error(f"Falha da ferramenta ao ler o documento: {leitura.erro}")
        _sem_documento(exame)
        return

    _aviso_de_confianca(leitura)

    if leitura.incertos:
        st.warning(
            "Variou entre as leituras e por isso não foi proposto:\n"
            + "\n".join(f"- {i}" for i in leitura.incertos)
        )
    if leitura.descartados:
        st.info(
            "Descartado por não conferir com o texto do documento: "
            + ", ".join(leitura.descartados)
        )

    with st.expander("Transcrição completa", expanded=False):
        st.text(leitura.texto or "(vazio)")

    campos = _campos_propostos(exame, leitura)

    if leitura.itens_declarados:
        st.subheader("Material declarado pela autoridade")
        st.caption(
            "Isto é o que o delegado diz estar enviando, com as palavras dele — "
            "inclusive as suspeitas (\"aparentemente maconha\"). **Não entra no "
            "laudo e não preenche nada.** Serve só para conferir a contagem "
            "contra o que você receber na bancada."
        )
        for item in leitura.itens_declarados:
            quantidade = item.get("quantidade") or "?"
            st.write(f"- **{quantidade}** — {item['texto']}")

    perguntas = _quesitos_propostos(leitura)

    st.divider()
    esquerda, direita = st.columns([1, 1])
    if esquerda.button("Voltar"):
        ir_para(TELA_SELECAO)
        st.rerun()
    if direita.button(
        "Confirmar e seguir",
        type="primary",
        disabled=not perguntas,
        help=None if perguntas else "Transcreva ao menos um quesito.",
    ):
        st.session_state["admin"].update(campos)
        st.session_state["quesitos"] = perguntas
        st.session_state["requisicao"] = {
            "origem": leitura.origem,
            "nivel": leitura.nivel,
            "texto": leitura.texto,
            "incertos": leitura.incertos,
            "itens_declarados": leitura.itens_declarados,
        }
        ir_para(TELA_ADMIN)
        st.rerun()
