"""Tela 4 — confirmação (humano no controle).

Tudo que vai ao documento passa por aqui, editável: os dados administrativos,
a camada 1 coletada na conversa, as imagens e os campos derivados. O perito
revisa, corrige e confirma. Nada é gerado sem essa passagem.
"""

from __future__ import annotations

import hashlib

import streamlit as st

from config.schema import Colecao, Exame
from core import derivados as camada3
from core import pendencias
from core.state import (
    TELA_CONVERSA,
    TELA_DOCUMENTO,
    TELA_SELECAO,
    exame_atual,
    ir_para,
)
from templates.identificacao_substancia import boilerplate


def _edita_admin(exame: Exame) -> None:
    admin = st.session_state["admin"]
    colunas = st.columns(2)
    for i, campo in enumerate(exame.campos_admin):
        with colunas[i % 2]:
            atual = admin.get(campo.chave, "")
            novo = st.text_input(
                campo.label + (" *" if campo.obrigatorio else ""),
                value=atual,
                key=f"conf_admin_{campo.chave}",
            )
            if novo != atual:
                admin[campo.chave] = novo


def _edita_item(colecao: Colecao, indice: int, item: dict) -> None:
    for slot in colecao.slots:
        exigido = slot.exigido_em(item)
        atual = item.get(slot.chave, "")
        novo = st.text_input(
            slot.label + (" *" if exigido else ""),
            value=atual,
            key=f"conf_{colecao.chave}_{indice}_{slot.chave}",
        )
        if novo != atual:
            item[slot.chave] = novo
        if exigido and not str(novo).strip():
            st.caption("⚠️ Campo obrigatório em branco.")


def _imagens_do_material(indice: int) -> list[dict]:
    return [img for img in st.session_state["imagens"] if img["material"] == indice]


def _guarda_imagem(dados: bytes, nome: str, indice_material: int) -> bool:
    """Adiciona a imagem se ela ainda não estiver anexada. Devolve se anexou."""
    assinatura = hashlib.sha256(dados).hexdigest()
    imagens = st.session_state["imagens"]
    if any(img["assinatura"] == assinatura for img in imagens):
        return False
    imagens.append(
        {
            "assinatura": assinatura,
            "nome": nome,
            "dados": dados,
            "material": indice_material,
            "legenda": "",
        }
    )
    return True


def _edita_imagens(colecao: Colecao, indice: int, item: dict) -> None:
    st.markdown("**Imagens**")
    st.caption(
        "Anexo documental: a foto corrobora o texto, nunca é lida pela ferramenta. "
        "Peso, contagem e cor vêm da sua medição, não da imagem."
    )

    enviados = st.file_uploader(
        "Anexar arquivo",
        type=["png", "jpg", "jpeg"],
        accept_multiple_files=True,
        key=f"upload_{colecao.chave}_{indice}",
    )
    for arquivo in enviados or []:
        _guarda_imagem(arquivo.getvalue(), arquivo.name, indice)

    with st.expander("Fotografar agora", expanded=False):
        foto = st.camera_input("Câmera", key=f"camera_{colecao.chave}_{indice}")
        if foto is not None:
            _guarda_imagem(foto.getvalue(), f"foto_material_{indice}.jpg", indice)

    anexadas = _imagens_do_material(indice)
    if not anexadas:
        st.caption("Nenhuma imagem anexada a este material.")
        return

    todas = st.session_state["imagens"]
    for img in anexadas:
        numero = todas.index(img) + 1
        coluna_foto, coluna_texto = st.columns([1, 2])
        with coluna_foto:
            st.image(img["dados"], width="stretch")
        with coluna_texto:
            sugerida = camada3.legenda(item, indice, numero)
            atual = img["legenda"] or sugerida
            nova = st.text_area(
                "Legenda",
                value=atual,
                key=f"legenda_{img['assinatura']}",
                height=100,
            )
            img["legenda"] = nova
            st.caption(
                f"Referência no texto: {camada3.referencia_imagem(numero)} — "
                "montada com os campos que você informou."
            )
            if st.button("Remover imagem", key=f"remove_{img['assinatura']}"):
                todas.remove(img)
                st.rerun()


def _edita_derivados(exame: Exame) -> None:
    """Campo derivado acompanha os dados até o perito escrever a versão dele.

    Enquanto o texto exibido for o que a regra montou, ele se atualiza sozinho
    quando a camada 1 muda — conclusão desatualizada num laudo é erro silencioso.
    Depois que o perito edita, o texto dele manda, e a divergência fica à vista
    com a opção de recalcular.
    """
    guardados = st.session_state["derivados"]
    origens = st.session_state.setdefault("derivados_origem", {})
    # O Streamlit proíbe escrever o estado de um widget depois de instanciá-lo,
    # então "recalcular" marca a intenção e o efeito acontece no run seguinte,
    # antes do text_area existir.
    recalcular = st.session_state.setdefault("derivados_recalcular", [])

    for derivado in camada3.montar(exame, st.session_state["colecoes"]):
        chave_widget = f"derivado_{derivado.chave}"
        # O texto vigente é o do widget, não o salvo no render anterior: quando o
        # perito acabou de digitar, só o widget sabe disso.
        vigente = st.session_state.get(chave_widget)
        editado = vigente is not None and vigente != origens.get(derivado.chave)

        forcado = derivado.chave in recalcular
        if forcado:
            recalcular.remove(derivado.chave)
            editado = False

        if not editado:
            guardados[derivado.chave] = derivado.valor
            st.session_state[chave_widget] = derivado.valor
        origens[derivado.chave] = derivado.valor

        st.markdown(f"**{derivado.label}**")
        guardados[derivado.chave] = st.text_area(
            derivado.label,
            key=chave_widget,
            label_visibility="collapsed",
            height=100,
        )
        st.caption(f"Derivado de: {derivado.origem}. {derivado.ajuda}")

        if editado:
            st.caption(f"Texto seu. A regra montaria: {derivado.valor or '(vazio)'}")
            if st.button(
                "Recalcular a partir dos dados",
                key=f"recalcula_{derivado.chave}",
            ):
                recalcular.append(derivado.chave)
                st.rerun()


def render() -> None:
    exame: Exame | None = exame_atual()
    if exame is None:
        ir_para(TELA_SELECAO)
        st.rerun()
        return

    st.header("Confirmação")
    st.caption(
        "Revise e corrija tudo antes de gerar a minuta. O documento sai exatamente "
        "com o que estiver aqui, e a responsabilidade pelo conteúdo é sua."
    )

    with st.expander("Dados administrativos", expanded=False):
        _edita_admin(exame)

    for colecao in exame.colecoes:
        itens = st.session_state["colecoes"].get(colecao.chave, [])
        st.subheader(colecao.label_plural)
        for indice, item in enumerate(itens, start=1):
            with st.expander(f"{colecao.label_singular} {indice}", expanded=True):
                _edita_item(colecao, indice, item)
                if colecao.aceita_imagens:
                    st.divider()
                    _edita_imagens(colecao, indice, item)

    st.subheader("Campos derivados")
    st.caption(
        "Montados a partir do que você informou, para você confirmar ou reescrever."
    )
    _edita_derivados(exame)

    st.divider()
    faltando = pendencias.todas(exame, st.session_state["colecoes"])
    admin_faltando = [
        c.label
        for c in exame.campos_admin
        if c.obrigatorio and not str(st.session_state["admin"].get(c.chave, "")).strip()
    ]
    conclusao_vazia = not str(
        st.session_state["derivados"].get(camada3.CHAVE_CONCLUSAO, "")
    ).strip()

    impedimentos: list[str] = []
    if admin_faltando:
        impedimentos.append("Dados administrativos: " + ", ".join(admin_faltando))
    if faltando:
        impedimentos.append(
            "Campos do exame: " + ", ".join(p.rotulo() for p in faltando)
        )
    if conclusao_vazia:
        impedimentos.append("Conclusão em branco")

    for impedimento in impedimentos:
        st.error(impedimento)

    blocos = boilerplate.blocos_pendentes()
    if blocos:
        st.warning(
            "O texto institucional do laudo ainda não foi transcrito dos laudos "
            "reais — falta: " + ", ".join(blocos) + ". Sem ele a minuta sai "
            "incompleta (Milestone 4)."
        )

    esquerda, direita = st.columns([1, 1])
    if esquerda.button("Voltar à conversa"):
        ir_para(TELA_CONVERSA)
        st.rerun()
    if direita.button(
        "Confirmar e gerar minuta",
        type="primary",
        disabled=bool(impedimentos),
        help="Corrija os campos em falta antes de gerar." if impedimentos else None,
    ):
        ir_para(TELA_DOCUMENTO)
        st.rerun()
