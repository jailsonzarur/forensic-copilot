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
from core import redacao
from core import referencias as base_referencias
from core import pendencias
from core import quesitos as camada1_quesitos
from core.state import (
    TELA_CONVERSA,
    TELA_DOCUMENTO,
    TELA_SELECAO,
    exame_atual,
    ir_para,
)
from core import templates as texto_fixo


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

    # Grupos repetíveis — quantos peritos assinam varia por caso.
    for grupo in exame.grupos_admin:
        entradas = admin.get(grupo.chave)
        if not isinstance(entradas, list) or not entradas:
            continue
        st.markdown(f"**{grupo.label_plural if hasattr(grupo, 'label_plural') else grupo.label_singular}**")
        for indice, entrada in enumerate(entradas, start=1):
            st.caption(f"{grupo.label_singular} {indice}")
            colunas = st.columns(max(len(grupo.campos), 1))
            for posicao, campo in enumerate(grupo.campos):
                with colunas[posicao % len(colunas)]:
                    atual = entrada.get(campo.chave, "")
                    novo = st.text_input(
                        campo.label + (" *" if campo.obrigatorio else ""),
                        value=atual,
                        key=f"conf_grupo_{grupo.chave}_{indice}_{campo.chave}",
                    )
                    if novo != atual:
                        entrada[campo.chave] = novo


def _escolhe_referencia(slot, indice: int, item: dict) -> None:
    """Referência entre coleções: quem aponta é o perito, não o extrator."""
    alvo = st.session_state["colecoes"].get(slot.referencia_colecao, [])
    # O rótulo do item apontado é do tipo de exame: Material, Veículo, Local.
    exame = exame_atual()
    apontada = exame.colecao(slot.referencia_colecao) if exame is not None else None
    rotulo = apontada.label_singular if apontada is not None else "Item"

    if not alvo:
        st.caption(f"Nenhum {rotulo.lower()} foi descrito ainda.")
        return
    opcoes = [""] + [str(i) for i in range(1, len(alvo) + 1)]
    atual = str(item.get(slot.chave, "")).strip()
    posicao = opcoes.index(atual) if atual in opcoes else 0
    escolhido = st.selectbox(
        slot.label + " *",
        options=opcoes,
        index=posicao,
        format_func=lambda v: f"{rotulo} {v}" if v else "— selecione —",
        key=f"conf_ref_{slot.chave}_{indice}",
    )
    item[slot.chave] = escolhido
    if not escolhido:
        st.caption(f"⚠️ Diga a qual {rotulo.lower()} este item se refere.")


def _edita_item(colecao: Colecao, indice: int, item: dict) -> None:
    for slot in colecao.slots:
        if slot.referencia_colecao:
            _escolhe_referencia(slot, indice, item)
            continue
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
            sugerida = camada3.legenda(item, indice, numero, exame_atual())
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
    from templates.identificacao_substancia import boilerplate as texto_substancia

    colecoes = st.session_state["colecoes"]
    lacunas: list[dict] = []

    for item in colecoes.get("exames_realizados", []):
        nome = str(item.get("nome_teste", "")).strip()
        substancia = str(item.get("substancia", "")).strip()
        if not nome:
            continue
        chave_par = (texto_substancia.normaliza(nome), texto_substancia.chave_substancia(substancia))
        if texto_substancia.RESULTADOS_POR_ENSAIO.get(chave_par):
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
                "ensaio": nome,
                "substancia": substancia,
                "procedimento": str(item.get("procedimento", "")).strip(),
            }
        )

    for item in colecoes.get("exames_realizados", []):
        if str(item.get("resultado", "")).strip().lower() != "positivo":
            continue
        substancia = str(item.get("substancia", "")).strip()
        if not substancia:
            continue
        chave_sub = texto_substancia.chave_substancia(substancia)
        identificador = biblioteca.chave(substancia)
        for tipo, rotulo, fonte, ajuda in (
            (
                "proscricao",
                f"Quesito 03 — texto legal de {substancia}",
                texto_substancia.PROSCRICAO_POR_SUBSTANCIA,
                "Texto de proscrição: portaria, lista e condição legal da substância.",
            ),
            (
                "natureza",
                f"Quesito 01 — construção da resposta para {substancia}",
                texto_substancia.NATUREZA_POR_SUBSTANCIA,
                "Use {forma} onde entra a forma do material. Ex.: "
                "'A substância {forma} trata-se de ...'",
            ),
            (
                "referencia",
                f"Seção 6 — referência bibliográfica de {substancia}",
                texto_substancia.REFERENCIAS_POR_SUBSTANCIA,
                "Obra ou manual que embasa o exame desta substância. Só as "
                "referências das substâncias encontradas vão ao laudo.",
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


def _redige_o_que_o_perito_contou(lacunas: list[dict]) -> None:
    """Transforma o relato dado na conversa no parágrafo da seção 4.

    A conversa prometeu: "conte como conduziu que eu redijo o parágrafo". A
    promessa se cumpre aqui, sozinha — sem depender de o perito achar um botão.
    O texto entra neste laudo e fica editável logo abaixo.
    """
    derivados = st.session_state["derivados"]
    falhas = st.session_state.setdefault("redacoes_que_falharam", [])
    refazer = st.session_state.setdefault("redacoes_a_refazer", [])

    for lacuna in lacunas:
        if lacuna["tipo"] != "resultado" or not lacuna.get("procedimento"):
            continue
        chave = camada3.chave_redacao(lacuna["ensaio"], lacuna["substancia"])
        pedido = lacuna["id"] in refazer
        if pedido:
            refazer.remove(lacuna["id"])
            derivados.pop(chave, None)
            st.session_state.pop(f"bib_texto_resultado_{lacuna['id']}", None)
            st.session_state.pop(f"bib_titulo_resultado_{lacuna['id']}", None)
            if chave in falhas:
                falhas.remove(chave)
        if derivados.get(chave) or chave in falhas:
            continue
        with st.spinner(f"Redigindo o parágrafo de {lacuna['ensaio']}…"):
            try:
                proposta, _ = redacao.redigir(
                    lacuna["ensaio"], lacuna["substancia"], lacuna["procedimento"]
                )
                derivados[chave] = proposta
            except Exception as erro:
                falhas.append(chave)
                st.error(
                    "Não consegui redigir o parágrafo a partir do seu relato. "
                    f"Escreva-o abaixo. Detalhe para quem instalou: {erro}"
                )


def _painel_biblioteca(exame: Exame) -> None:
    """Onde o perito escreve a redação institucional que falta — uma vez só."""
    lacunas = _lacunas_institucionais(exame)
    _redige_o_que_o_perito_contou(lacunas)
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
        "ferramenta reaproveita nos próximos laudos. O texto fica com a sua "
        "autoria: a ferramenta nunca escreve isso sozinha."
    )

    autor = st.session_state["admin"].get("perito_designado", "")
    for lacuna in lacunas:
        with st.expander(lacuna["rotulo"], expanded=False):
            st.caption(lacuna["ajuda"])

            chave_texto = f"bib_texto_{lacuna['tipo']}_{lacuna['id']}"
            chave_titulo = f"bib_titulo_{lacuna['tipo']}_{lacuna['id']}"
            relato = lacuna.get("procedimento", "")

            # Redação já feita para este laudo a partir do relato do perito: ela
            # entra no documento mesmo sem ser salva na biblioteca. Semear os
            # campos ANTES de criá-los — o Streamlit proíbe o contrário.
            deste_laudo = None
            if lacuna["tipo"] == "resultado":
                deste_laudo = st.session_state["derivados"].get(
                    camada3.chave_redacao(lacuna["ensaio"], lacuna["substancia"])
                )
            if isinstance(deste_laudo, dict):
                st.session_state.setdefault(chave_texto, deste_laudo.get("texto", ""))
                st.session_state.setdefault(chave_titulo, deste_laudo.get("titulo", ""))

            if deste_laudo:
                st.success(
                    "Escrito a partir do seu relato e **já em uso neste laudo**. "
                    "Revise o texto abaixo; salvar na biblioteca serve para "
                    "reaproveitá-lo nos próximos laudos."
                )
            if relato:
                st.caption(f"Você contou na conversa: «{relato}»")

            titulo = ""
            if lacuna["tipo"] == "resultado":
                titulo = st.text_input(
                    "Título da subseção",
                    key=chave_titulo,
                    placeholder=lacuna.get("titulo_sugerido", ""),
                )
                if relato and st.button(
                    "Escrever de novo a partir do seu relato",
                    key=f"bib_redigir_{lacuna['tipo']}_{lacuna['id']}",
                    help=(
                        "A ferramenta apenas dá forma de laudo ao que VOCÊ contou. "
                        "Ela não acrescenta reagente, fase nem etapa que você não "
                        "citou — leia antes de salvar."
                    ),
                ):
                    st.session_state["redacoes_a_refazer"] = [
                        *st.session_state.get("redacoes_a_refazer", []),
                        lacuna["id"],
                    ]
                    st.rerun()

            texto = st.text_area("Redação", key=chave_texto, height=140)

            if lacuna["tipo"] == "resultado" and texto.strip():
                st.session_state["derivados"][
                    camada3.chave_redacao(lacuna["ensaio"], lacuna["substancia"])
                ] = {
                    "titulo": titulo.strip() or lacuna.get("titulo_sugerido", ""),
                    "texto": texto.strip(),
                }

            if st.button(
                "Salvar na biblioteca",
                key=f"bib_salvar_{lacuna['tipo']}_{lacuna['id']}",
                disabled=not texto.strip(),
                help="Passa a valer para os próximos laudos, com a sua autoria.",
            ):
                conteudo = {"texto": texto.strip()}
                if lacuna["tipo"] == "resultado":
                    conteudo["titulo"] = titulo.strip() or lacuna["rotulo"]
                biblioteca.salvar(lacuna["tipo"], lacuna["id"], conteudo, autor)
                st.rerun()


def _painel_referencias() -> None:
    """Seção 6: o que embasa ESTE exame, não uma bibliografia fixa."""
    colecoes = st.session_state["colecoes"]
    autor = st.session_state["admin"].get("perito_designado", "")

    escolhidas = base_referencias.para_o_laudo(colecoes)
    if escolhidas:
        st.caption("Vão para o laudo, por casarem com as substâncias e ensaios deste caso:")
        for referencia in escolhidas:
            st.write(f"- {referencia.citacao}")
            st.caption(f"  {referencia.descricao}")
    else:
        st.warning("Nenhuma referência confirmada se aplica a este laudo.")

    faltando = base_referencias.substancias_sem_referencia(colecoes)
    if faltando:
        st.error(
            "Sem referência confirmada para: "
            + ", ".join(faltando)
            + ". Sai como pendência em vermelho no documento."
        )

    candidatas = base_referencias.candidatas(colecoes)
    if candidatas:
        st.markdown("**Obras encontradas que ainda não foram conferidas**")
        st.caption(
            "Encontradas em busca na internet. **Ano, edição e código não foram "
            "conferidos** — ferramenta nenhuma deve inventar citação num laudo "
            "assinado. Abra a obra, escreva a citação completa e ela passa a valer."
        )
        for referencia in candidatas:
            with st.expander(referencia.titulo or referencia.id, expanded=False):
                st.caption(referencia.descricao)
                st.caption(f"Onde foi encontrada: {referencia.fonte}")
                citacao = st.text_area(
                    "Citação completa, como o laudo deve imprimir",
                    key=f"ref_citacao_{referencia.id}",
                    height=80,
                )
                if st.button(
                    "Confirmar referência",
                    key=f"ref_confirmar_{referencia.id}",
                    disabled=not citacao.strip(),
                ):
                    base_referencias.confirmar(referencia.id, citacao, autor)
                    st.rerun()

    with st.expander("Acrescentar uma referência própria", expanded=False):
        nova = st.text_area("Citação completa", key="ref_nova_citacao", height=80)
        descricao = st.text_input("Do que ela trata", key="ref_nova_descricao")
        substancias = st.text_input(
            "Substâncias a que se aplica (separadas por vírgula; em branco = vale para todo laudo)",
            key="ref_nova_substancias",
        )
        if st.button("Adicionar à base", disabled=not nova.strip(), key="ref_nova_salvar"):
            base_referencias.adicionar(
                identificador=base_referencias.boilerplate.normaliza(nova)[:40].replace(" ", "-"),
                citacao=nova,
                descricao=descricao,
                substancias=[s.strip() for s in substancias.split(",") if s.strip()],
                autor=autor,
            )
            st.rerun()


def _painel_conferencia() -> bool:
    """Confronta o declarado na requisição com o descrito pelo perito.

    Devolve se há divergência. A ferramenta aponta; quem interpreta é o perito.
    """
    requisicao = st.session_state.get("requisicao") or {}
    declarados = requisicao.get("itens_declarados") or []

    # A coleção conferida é a do objeto examinado, que o tipo de laudo declara.
    # Num laudo de danos a autoridade não envia item nenhum — aponta um local —,
    # então não há contagem a conferir e o painel fica silencioso.
    exame = exame_atual()
    objeto = exame.colecao_objeto() if exame is not None else None
    examinados = st.session_state["colecoes"].get(
        objeto.chave if objeto is not None else "materiais", []
    )

    observacoes = conferencia.comparar(declarados, examinados)
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
    """Quesitos: a pergunta é da autoridade, a resposta é do perito.

    Quando o perito escreveu a resposta na conversa (não confirmou padrão),
    passa por uma formalização que só reformata sem acrescentar fato — mesma
    regra da redação de procedimento. A original fica gravada e visível para
    o perito poder reverter ou editar.
    """
    perguntas = st.session_state["quesitos"]
    respostas = st.session_state["respostas_quesitos"]
    if not perguntas:
        st.warning("Nenhum quesito transcrito da requisição — o laudo ficaria sem responder nada.")
        return

    # Cache: {numero: (bruta, formal)}. A bruta na chave garante que uma edição
    # do perito para outro texto refaça a formalização.
    formalizacoes = st.session_state.setdefault("formalizacoes_quesitos", {})

    montados = camada1_quesitos.montar(
        perguntas, st.session_state["colecoes"], st.session_state["derivados"], respostas
    )
    for quesito in montados:
        st.markdown(f"**{quesito.numero} – {quesito.pergunta}**")
        chave = f"quesito_resposta_{quesito.numero}"
        bruta_perito = str(respostas.get(quesito.numero, "")).strip()
        vale_formalizar = (
            bruta_perito
            and bruta_perito != camada1_quesitos.PADRAO_ACEITO
            and not quesito.padrao_conhecido
        )
        formal = ""
        if vale_formalizar:
            cache = formalizacoes.get(quesito.numero)
            if cache and cache[0] == bruta_perito:
                _, formal = cache
            else:
                with st.spinner(f"Formalizando resposta ao quesito {quesito.numero}…"):
                    try:
                        formal, _ = redacao.formalizar_resposta_quesito(
                            quesito.pergunta, bruta_perito
                        )
                    except Exception as erro:
                        formal = bruta_perito
                        st.warning(
                            f"Não consegui formalizar. Sua resposta segue como escrita. "
                            f"Detalhe: {erro}"
                        )
                formalizacoes[quesito.numero] = (bruta_perito, formal)

        vigente = st.session_state.get(chave)
        if vigente is None:
            st.session_state[chave] = formal or respostas.get(quesito.numero) or quesito.resposta
        texto = st.text_area(
            f"Resposta ao quesito {quesito.numero}",
            key=chave,
            label_visibility="collapsed",
            height=90,
        )
        respostas[quesito.numero] = texto
        if quesito.padrao_conhecido:
            st.caption("Padrão de resposta transcrito de laudo real.")
        elif vale_formalizar and formal and formal != bruta_perito:
            st.caption(
                f"Formalizei sua resposta pra ficar no tom do laudo. "
                f"Original: «{bruta_perito}». Edite se algo divergiu."
            )
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
        "Texto que o Instituto usa. A ferramenta não pode inventá-lo, porque ele "
        "declara como o exame foi conduzido."
    )
    _painel_biblioteca(exame)

    st.subheader("Referências (seção 6)")
    _painel_referencias()

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
    for grupo in exame.grupos_admin:
        for indice, entrada in enumerate(st.session_state["admin"].get(grupo.chave, []), start=1):
            for campo in grupo.campos:
                if campo.obrigatorio and not str(entrada.get(campo.chave, "")).strip():
                    admin_faltando.append(f"{grupo.label_singular} {indice}: {campo.label}")
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

    blocos = texto_fixo.boilerplate(exame).blocos_pendentes()
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
