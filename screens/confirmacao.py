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
from core import biblioteca
from core import conferencia
from core import pendencias
from core import quesitos as camada1_quesitos
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


def _lacunas_institucionais(exame: Exame) -> list[dict]:
    """Redações que faltam para este laudo e que a biblioteca pode aprender."""
    from templates.identificacao_substancia import boilerplate as texto_fixo

    colecoes = st.session_state["colecoes"]
    lacunas: list[dict] = []

    for item in colecoes.get("exames_realizados", []):
        nome = str(item.get("nome_teste", "")).strip()
        substancia = str(item.get("substancia", "")).strip()
        if not nome:
            continue
        chave_par = (texto_fixo.normaliza(nome), texto_fixo.chave_substancia(substancia))
        if texto_fixo.RESULTADOS_POR_ENSAIO.get(chave_par):
            continue
        identificador = biblioteca.chave(nome, substancia)
        if biblioteca.buscar("resultado", identificador):
            continue
        if any(l["id"] == identificador for l in lacunas):
            continue
        lacunas.append(
            {
                "tipo": "resultado",
                "id": identificador,
                "rotulo": f"Seção 4 — {nome}" + (f" para {substancia}" if substancia else ""),
                "ajuda": (
                    "Parágrafo que descreve como o ensaio foi conduzido e o que "
                    "ele mostrou, como o Instituto redige."
                ),
                "titulo_sugerido": f"Análise por {nome.lower()}",
            }
        )

    for item in colecoes.get("exames_realizados", []):
        if str(item.get("resultado", "")).strip().lower() != "positivo":
            continue
        substancia = str(item.get("substancia", "")).strip()
        if not substancia:
            continue
        chave_sub = texto_fixo.chave_substancia(substancia)
        identificador = biblioteca.chave(substancia)
        for tipo, rotulo, fonte, ajuda in (
            (
                "proscricao",
                f"Quesito 03 — texto legal de {substancia}",
                texto_fixo.PROSCRICAO_POR_SUBSTANCIA,
                "Texto de proscrição: portaria, lista e condição legal da substância.",
            ),
            (
                "natureza",
                f"Quesito 01 — construção da resposta para {substancia}",
                texto_fixo.NATUREZA_POR_SUBSTANCIA,
                "Use {forma} onde entra a forma do material. Ex.: "
                "'A substância {forma} trata-se de ...'",
            ),
        ):
            if fonte.get(chave_sub) or biblioteca.buscar(tipo, identificador):
                continue
            if any(l["id"] == identificador and l["tipo"] == tipo for l in lacunas):
                continue
            lacunas.append(
                {"tipo": tipo, "id": identificador, "rotulo": rotulo, "ajuda": ajuda}
            )

    return lacunas


def _painel_biblioteca(exame: Exame) -> None:
    """Onde o perito escreve a redação institucional que falta — uma vez só."""
    lacunas = _lacunas_institucionais(exame)
    if not lacunas:
        contagem = biblioteca.resumo()
        st.success(
            "Toda a redação institucional deste laudo já existe. Biblioteca: "
            + ", ".join(f"{v} {k}" for k, v in contagem.items() if v)
            + "." if any(contagem.values()) else
            "Toda a redação institucional deste laudo já existe."
        )
        return

    st.warning(
        f"{len(lacunas)} trecho(s) de redação institucional não existem ainda. "
        "Sem eles a minuta sai com marcador vermelho. Escreva uma vez aqui e a "
        "ferramenta reaproveita nos próximos laudos — o texto fica com a sua "
        "autoria, nunca é gerado por modelo."
    )

    autor = st.session_state["admin"].get("perito_designado", "")
    for lacuna in lacunas:
        with st.expander(lacuna["rotulo"], expanded=False):
            st.caption(lacuna["ajuda"])
            titulo = ""
            if lacuna["tipo"] == "resultado":
                titulo = st.text_input(
                    "Título da subseção",
                    value=lacuna.get("titulo_sugerido", ""),
                    key=f"bib_titulo_{lacuna['tipo']}_{lacuna['id']}",
                )
            texto = st.text_area(
                "Redação",
                key=f"bib_texto_{lacuna['tipo']}_{lacuna['id']}",
                height=140,
            )
            if st.button(
                "Salvar na biblioteca",
                key=f"bib_salvar_{lacuna['tipo']}_{lacuna['id']}",
                disabled=not texto.strip(),
            ):
                conteudo = {"texto": texto.strip()}
                if lacuna["tipo"] == "resultado":
                    conteudo["titulo"] = titulo.strip() or lacuna["rotulo"]
                biblioteca.salvar(lacuna["tipo"], lacuna["id"], conteudo, autor)
                st.rerun()


def _painel_conferencia() -> bool:
    """Confronta o declarado na requisição com o descrito pelo perito.

    Devolve se há divergência. A ferramenta aponta; quem interpreta é o perito.
    """
    requisicao = st.session_state.get("requisicao") or {}
    declarados = requisicao.get("itens_declarados") or []
    materiais = st.session_state["colecoes"].get("materiais", [])

    observacoes = conferencia.comparar(declarados, materiais)
    for observacao in observacoes:
        if observacao.tipo == "divergencia":
            st.error(observacao.texto)
        elif observacao.tipo == "confere":
            st.success(observacao.texto)
        else:
            st.info(observacao.texto)

    if declarados:
        with st.expander("O que a autoridade declarou enviar", expanded=False):
            st.caption(
                "Palavras do delegado, incluindo a suspeita dele. Não entra no "
                "laudo — está aqui só para a conferência."
            )
            for item in declarados:
                st.write(f"- **{item.get('quantidade') or '?'}** — {item['texto']}")

    return conferencia.ha_divergencia(observacoes)


def _edita_quesitos(exame: Exame) -> None:
    """Quesitos: a pergunta é da autoridade, a resposta é do perito."""
    perguntas = st.session_state["quesitos"]
    respostas = st.session_state["respostas_quesitos"]
    if not perguntas:
        st.warning("Nenhum quesito transcrito da requisição — o laudo ficaria sem responder nada.")
        return

    montados = camada1_quesitos.montar(
        perguntas, st.session_state["colecoes"], st.session_state["derivados"], respostas
    )
    for quesito in montados:
        st.markdown(f"**{quesito.numero} – {quesito.pergunta}**")
        chave = f"quesito_resposta_{quesito.numero}"
        vigente = st.session_state.get(chave)
        automatica = quesito.resposta if not respostas.get(quesito.numero) else ""
        if vigente is None:
            st.session_state[chave] = respostas.get(quesito.numero) or quesito.resposta
        texto = st.text_area(
            f"Resposta ao quesito {quesito.numero}",
            key=chave,
            label_visibility="collapsed",
            height=90,
        )
        respostas[quesito.numero] = texto
        if quesito.padrao_conhecido:
            st.caption("Padrão de resposta transcrito de laudo real.")
        else:
            st.caption(
                "Quesito sem padrão transcrito — esta resposta é sua. "
                "Enquanto ficar como PENDENTE, sai em vermelho no documento."
            )


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

    st.subheader("Redação institucional")
    st.caption(
        "Texto que o Instituto usa e que nenhum modelo pode escrever: ele "
        "declara como o exame foi conduzido."
    )
    _painel_biblioteca(exame)

    st.subheader("Conferência com a requisição")
    st.caption(
        "Cadeia de custódia: o que a autoridade declarou ter enviado contra o "
        "que você descreveu na bancada."
    )
    divergencia = _painel_conferencia()

    st.subheader("Quesitos")
    st.caption(
        "As perguntas vêm da requisição da autoridade; as respostas, do exame. "
        "O laudo responde a estas perguntas e a mais nenhuma."
    )
    _edita_quesitos(exame)

    st.subheader("Campos derivados")
    st.caption(
        "Montados a partir do que você informou, para você confirmar ou reescrever."
    )
    _edita_derivados(exame)

    st.divider()
    faltando = pendencias.todas(exame, st.session_state["colecoes"])
    sem_quesito = not st.session_state["quesitos"]
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
    if sem_quesito:
        impedimentos.append("Nenhum quesito transcrito da requisição")

    if divergencia:
        ciente = st.checkbox(
            "Estou ciente da divergência com a requisição e assumo a descrição "
            "acima como a correta.",
            key="ciente_divergencia",
        )
        if not ciente:
            impedimentos.append(
                "Divergência com a requisição ainda não reconhecida"
            )

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
