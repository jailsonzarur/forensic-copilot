"""Montagem do .docx — camadas 1 + 2 + 3 no layout do laudo real.

Nenhum texto nasce aqui. O documento é a soma de:
  - camada 1, como o perito ditou e revisou;
  - camada 2, transcrita do laudo SB 1252/2019;
  - camada 3, derivada por regra e **confirmada** na tela anterior.

Onde falta redação transcrita, o documento carrega o marcador
``[PENDENTE: ...]`` à vista, em vermelho. Uma minuta com lacuna assinalada é
honesta; uma minuta com lacuna preenchida por semelhança, não.
"""

from __future__ import annotations

import io

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

from core import derivados as camada3
from core import quesitos as camada1_quesitos
from core import numeros
from templates.identificacao_substancia import boilerplate

FONTE = "Times New Roman"
CORPO = Pt(12)
VERMELHO = RGBColor(0xC0, 0x00, 0x00)
MARCADOR = "[PENDENTE:"


def _paginas(derivados: dict) -> str:
    """Contagem por extenso quando o perito informou; vazio quando não."""
    return numeros.paginas_por_extenso(derivados.get(camada3.CHAVE_PAGINAS, ""))


def _insere_contagem_automatica(paragrafo) -> None:
    """Campo NUMPAGES: o editor de texto conta as páginas ao abrir o arquivo.

    Paginação não existe nesta montagem — quem pagina é o Word. Em vez de pedir
    ao perito que conte e volte, o número entra como campo e sai certo sozinho.
    """
    corrida = paragrafo.add_run()
    abertura = OxmlElement("w:fldChar")
    abertura.set(qn("w:fldCharType"), "begin")
    instrucao = OxmlElement("w:instrText")
    instrucao.set(qn("xml:space"), "preserve")
    instrucao.text = " NUMPAGES "
    separador = OxmlElement("w:fldChar")
    separador.set(qn("w:fldCharType"), "separate")
    provisorio = OxmlElement("w:t")
    provisorio.text = "2"
    fechamento = OxmlElement("w:fldChar")
    fechamento.set(qn("w:fldCharType"), "end")
    for elemento in (abertura, instrucao, separador, provisorio, fechamento):
        corrida._r.append(elemento)


def _paragrafo_fecho(documento: Document, derivados: dict) -> None:
    """Fecho do laudo, com a contagem de páginas por extenso ou automática."""
    extenso = _paginas(derivados)
    if extenso:
        _paragrafo(documento, boilerplate.FECHO.format(paginas_extenso=extenso))
        return

    antes, _, depois = boilerplate.FECHO.partition("{paginas_extenso}")
    paragrafo = documento.add_paragraph()
    paragrafo.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    paragrafo.paragraph_format.space_after = Pt(6)
    paragrafo.add_run(antes)
    _insere_contagem_automatica(paragrafo)
    paragrafo.add_run(depois)


def _configura(documento: Document) -> None:
    estilo = documento.styles["Normal"]
    estilo.font.name = FONTE
    estilo.font.size = CORPO
    for secao in documento.sections:
        secao.top_margin = Cm(2.5)
        secao.bottom_margin = Cm(2.5)
        secao.left_margin = Cm(3.0)
        secao.right_margin = Cm(2.5)


def _paragrafo(
    documento: Document,
    texto: str,
    *,
    alinhamento=WD_ALIGN_PARAGRAPH.JUSTIFY,
    negrito: bool = False,
    espaco_antes: int = 0,
):
    """Parágrafo que destaca em vermelho os trechos ainda pendentes."""
    paragrafo = documento.add_paragraph()
    paragrafo.alignment = alinhamento
    paragrafo.paragraph_format.space_before = Pt(espaco_antes)
    paragrafo.paragraph_format.space_after = Pt(6)

    restante = texto
    while MARCADOR in restante:
        antes, _, depois = restante.partition(MARCADOR)
        if antes:
            corrida = paragrafo.add_run(antes)
            corrida.bold = negrito
        pendencia, _, restante = depois.partition("]")
        alerta = paragrafo.add_run(f"{MARCADOR}{pendencia}]")
        alerta.bold = True
        alerta.font.color.rgb = VERMELHO
    if restante:
        corrida = paragrafo.add_run(restante)
        corrida.bold = negrito
    return paragrafo


def _titulo_secao(documento: Document, texto: str) -> None:
    _paragrafo(
        documento,
        texto,
        alinhamento=WD_ALIGN_PARAGRAPH.LEFT,
        negrito=True,
        espaco_antes=12,
    )


def _cabecalho(documento: Document, admin: dict) -> None:
    for linha in boilerplate.CABECALHO:
        _paragrafo(documento, linha, alinhamento=WD_ALIGN_PARAGRAPH.CENTER, negrito=True)

    documento.add_paragraph()
    for rotulo, valor in (
        ("DEMANDA", admin.get("numero_demanda", "")),
        ("LAUDO N°", admin.get("numero_laudo", "")),
    ):
        _paragrafo(
            documento,
            f"{rotulo}        {valor}",
            alinhamento=WD_ALIGN_PARAGRAPH.LEFT,
            negrito=True,
        )

    documento.add_paragraph()
    _paragrafo(
        documento, boilerplate.TITULO, alinhamento=WD_ALIGN_PARAGRAPH.CENTER, negrito=True
    )
    _paragrafo(
        documento, boilerplate.SUBTITULO, alinhamento=WD_ALIGN_PARAGRAPH.CENTER, negrito=True
    )
    documento.add_paragraph()


def _preambulo(documento: Document, admin: dict) -> None:
    _paragrafo(
        documento,
        boilerplate.PREAMBULO.format(
            data_exame_extenso=numeros.data_por_extenso(admin.get("data_exame", "")),
            orgao_solicitante=admin.get("orgao_solicitante", ""),
            documento_solicitacao=admin.get("documento_solicitacao", ""),
            data_documento=numeros.data_curta(admin.get("data_documento", "")),
            perito_designado=admin.get("perito_designado", ""),
        ),
    )


def _historico(documento: Document, admin: dict) -> None:
    _titulo_secao(documento, "1. HISTÓRICO")
    _paragrafo(
        documento,
        boilerplate.HISTORICO.format(
            protocolo_sbs=admin.get("protocolo_sbs", ""),
            tipo_procedimento=admin.get("tipo_procedimento", ""),
            numero_procedimento=admin.get("numero_procedimento", ""),
            envolvido=admin.get("envolvido", ""),
        ),
    )
    _paragrafo(documento, boilerplate.HISTORICO_FECHO)


def _material(
    documento: Document, colecoes: dict, derivados: dict, imagens: list[dict]
) -> None:
    _titulo_secao(documento, "2. IDENTIFICAÇÃO E DESCRIÇÃO DO MATERIAL")

    materiais = colecoes.get("materiais", [])
    for indice, material in enumerate(materiais, start=1):
        chave = f"{camada3.PREFIXO_MATERIAL}{indice}"
        texto = derivados.get(chave) or camada3.descricao_material(material)
        letra = chr(ord("a") + indice - 1)
        _paragrafo(documento, f"{letra}) {texto}")

    if not imagens:
        return

    documento.add_paragraph()
    for imagem in imagens:
        paragrafo = documento.add_paragraph()
        paragrafo.alignment = WD_ALIGN_PARAGRAPH.CENTER
        paragrafo.add_run().add_picture(io.BytesIO(imagem["dados"]), width=Cm(10))
        legenda = imagem.get("legenda") or boilerplate.LEGENDA_FOTO
        _paragrafo(documento, legenda, alinhamento=WD_ALIGN_PARAGRAPH.CENTER)


def _exames(documento: Document, colecoes: dict, derivados: dict) -> None:
    _titulo_secao(documento, "3. EXAMES REALIZADOS")
    _paragrafo(
        documento,
        derivados.get(camada3.CHAVE_EXAMES) or camada3.texto_exames(colecoes),
    )

    _titulo_secao(documento, "4. RESULTADOS OBTIDOS")
    for ordem, secao in enumerate(camada3.resultados_obtidos(colecoes, derivados), start=1):
        _paragrafo(
            documento,
            f"4.{ordem}. {secao['titulo']}",
            alinhamento=WD_ALIGN_PARAGRAPH.LEFT,
            negrito=True,
            espaco_antes=6,
        )
        _paragrafo(documento, secao["texto"])


def _conclusao_e_quesitos(
    documento: Document,
    colecoes: dict,
    derivados: dict,
    perguntas: list[str],
    respostas: dict[str, str],
) -> None:
    _titulo_secao(documento, "5. CONCLUSÃO")
    resultados = derivados.get(camada3.CHAVE_CONCLUSAO) or camada3.conclusao(colecoes)[0]
    _paragrafo(documento, boilerplate.CONCLUSAO.format(resultados=resultados.rstrip(".")))

    documento.add_paragraph()
    _paragrafo(documento, boilerplate.ABERTURA_QUESITOS)

    for quesito in camada1_quesitos.montar(perguntas, colecoes, derivados, respostas):
        _paragrafo(
            documento,
            f"{quesito.numero} – {quesito.pergunta}",
            espaco_antes=6,
        )
        _paragrafo(documento, "R – " + quesito.resposta)


def _fecho(documento: Document, admin: dict, derivados: dict, colecoes: dict) -> None:
    _titulo_secao(documento, "6. REFERÊNCIAS")
    for referencia in camada3.referencias(colecoes):
        _paragrafo(documento, referencia)

    documento.add_paragraph()
    _paragrafo_fecho(documento, derivados)

    documento.add_paragraph()
    for linha, negrito in (
        (boilerplate.ASSINATURA, False),
        (admin.get("perito_designado", "").upper(), True),
        (boilerplate.CARGO, False),
    ):
        _paragrafo(documento, linha, alinhamento=WD_ALIGN_PARAGRAPH.CENTER, negrito=negrito)

    classe = admin.get("classe_perito", "").strip()
    matricula = admin.get("matricula", "").strip()
    rodape = f"{classe} – Matrícula: {matricula}" if classe else f"Matrícula: {matricula}"
    _paragrafo(documento, rodape, alinhamento=WD_ALIGN_PARAGRAPH.CENTER)


def montar(
    admin: dict,
    colecoes: dict[str, list[dict]],
    derivados: dict,
    imagens: list[dict] | None = None,
    quesitos: list[str] | None = None,
    respostas_quesitos: dict[str, str] | None = None,
) -> Document:
    documento = Document()
    _configura(documento)
    _cabecalho(documento, admin)
    _preambulo(documento, admin)
    _historico(documento, admin)
    _material(documento, colecoes, derivados, imagens or [])
    _exames(documento, colecoes, derivados)
    _conclusao_e_quesitos(
        documento,
        colecoes,
        derivados,
        quesitos if quesitos is not None else list(boilerplate.QUESITOS_DA_REQUISICAO_MODELO),
        respostas_quesitos or {},
    )
    _fecho(documento, admin, derivados, colecoes)
    return documento


def em_bytes(documento: Document) -> bytes:
    buffer = io.BytesIO()
    documento.save(buffer)
    return buffer.getvalue()


def pendencias_do_texto(
    admin: dict,
    colecoes: dict[str, list[dict]],
    derivados: dict,
    quesitos: list[str] | None = None,
    respostas_quesitos: dict[str, str] | None = None,
) -> list[str]:
    """Marcadores [PENDENTE: ...] que apareceriam no documento."""
    perguntas = (
        quesitos if quesitos is not None else list(boilerplate.QUESITOS_DA_REQUISICAO_MODELO)
    )
    pedacos = [
        *camada3.referencias(colecoes),
        *(
            q.resposta
            for q in camada1_quesitos.montar(
                perguntas, colecoes, derivados, respostas_quesitos or {}
            )
        ),
        derivados.get(camada3.CHAVE_NATUREZA) or camada3.natureza(colecoes),
        derivados.get(camada3.CHAVE_PROSCRICAO) or camada3.proscricao(colecoes),
        *(s["texto"] for s in camada3.resultados_obtidos(colecoes, derivados)),
        *(
            derivados.get(f"{camada3.PREFIXO_MATERIAL}{i}")
            or camada3.descricao_material(m)
            for i, m in enumerate(colecoes.get("materiais", []), start=1)
        ),
    ]
    encontradas: list[str] = []
    for pedaco in pedacos:
        restante = str(pedaco)
        while MARCADOR in restante:
            _, _, depois = restante.partition(MARCADOR)
            pendencia, _, restante = depois.partition("]")
            texto = pendencia.strip()
            if texto not in encontradas:
                encontradas.append(texto)
    return encontradas
