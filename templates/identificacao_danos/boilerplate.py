"""CAMADA 2 — texto fixo do laudo de Verificação de Danos.

Transcrito dos laudos reais das demandas 00016037-31 (cela de presídio
arrombada) e 00016160-22 (ponte ferroviária pichada), Instituto de
Criminalística / Departamento de Polícia Técnico-Científica da PC-PI. Nada
aqui foi redigido: é cópia, com os pontos que variam trocados por marcadores.

**Os dois laudos são do mesmo perito.** Como a camada 2 de identificação de
substância, que nasceu de um laudo só, esta nasce da escrita de um redator
apenas — o que ela não cobre vira ``[PENDENTE: ...]`` à vista, nunca texto
preenchido por semelhança.

Diferenças de estrutura em relação aos outros dois tipos, todas observadas nos
originais:

- o cabeçalho diz DEPARTAMENTO DE POLÍCIA **TÉCNICO-**CIENTÍFICA, e o
  INSTITUTO DE CRIMINALÍSTICA vem depois dele, não antes;
- há ``2. DO OBJETIVO DA PERÍCIA``, seção que não existe nos outros;
- a seção de exames tem duas subseções fixas — ``Do Local`` e
  ``Das Constatações (Danos)`` — e não uma por item examinado;
- as imagens vão no corpo, intercaladas, com legenda "IMAGEM 01: ...";
- o rodapé da assinatura abrevia "Mat.:" onde os outros escrevem "Matrícula:".

Três pontos em que esta transcrição se afasta do papel, todos decididos em
2026-08-30 e registrados aqui para que ninguém os descubra como surpresa:

1. os originais grafam "DO OBJETIVO DA PARÍCIA" nos dois laudos; corrigido
   para "PERÍCIA";
2. os dois originais **discordam de si mesmos** na concordância de
   "subscrit_": o laudo do ofício (masculino) escreve "subscrita", e o da
   requisição (feminino) escreve "subscrito" — invertido nos dois. É resíduo
   de reaproveitamento de modelo, não convenção; aqui as três flexões
   ("datado", "recebido", "subscrito") acompanham o artigo que o perito
   escreveu no documento de solicitação;
3. o laudo da cela abre as constatações com "apontados como sendo
   **supostamente** de interesse pericial" e o da ponte sem o advérbio. A
   moldura ficou com a forma sem "supostamente"; quem quiser a outra escreve
   na tela de confirmação.
"""

from __future__ import annotations

import unicodedata

CABECALHO = (
    "GOVERNO DO ESTADO DO PIAUÍ",
    "SECRETARIA DE SEGURANÇA PÚBLICA",
    "POLÍCIA CIVIL DO ESTADO DO PIAUÍ",
    "DEPARTAMENTO DE POLÍCIA TÉCNICO-CIENTÍFICA",
    "INSTITUTO DE CRIMINALÍSTICA",
)

TITULO = "LAUDO DE EXAME PERICIAL"
SUBTITULO = "(PERÍCIAS EXTERNAS)"

#: Os dois laudos abrem o preâmbulo com a mesma moldura; o que muda é o gênero
#: do documento de solicitação ("do ofício ... datado" contra "da requisição ...
#: datada"), resolvido em ``campos_extras`` a partir do artigo que o perito
#: escreveu, e a finalidade, que ele escolhe entre as duas formas transcritas.
PREAMBULO = (
    "Em {data_exame_extenso}, no INSTITUTO DE CRIMINALÍSTICA do DEPARTAMENTO DE "
    "POLÍCIA TÉCNICO-CIENTÍFICA da POLÍCIA CIVIL DO ESTADO DO PIAUÍ, fora "
    "recebida solicitação da {orgao_solicitante}, formalizada por meio "
    "{documento_solicitacao}, {datado} de {data_documento_extenso}, {recebido} "
    "às {hora_recebimento} do mesmo dia, {subscrito} pelo {subscritor}, para "
    "proceder a {finalidade}, demanda para a qual fora designado pela Direção, "
    "{o_perito_criminal} {peritos_designados}, descrevendo com verdade e com "
    "todas as circunstâncias tudo quanto possa interessar."
)

#: Formas transcritas da finalidade. O perito escolhe; a ferramenta não decide
#: por ele qual descreve o exame que ele fez.
FINALIDADES = (
    "Exame Pericial para Verificação de Danos",
    "Exame Pericial em Local para Verificação de Danos",
)

HISTORICO = (
    "Ao ser comunicado pela {orgao_solicitante}, no dia "
    "{data_exame_extenso}, às {hora_comunicacao}, {o_perito_criminal} "
    "{peritos_designados} deslocou-se para o local da ocorrência "
    "{endereco_local}, lá chegando às {hora_chegada} do mesmo dia, "
    "{recepcao}passando de imediato a proceder aos exames técnicos "
    "necessários, os quais serão descritos nos tópicos seguintes."
)

OBJETIVO = (
    "O objetivo do presente exame encontra-se explícito nos quesitos formulados "
    "pela autoridade requisitante os quais serão, oportunamente, transcritos e "
    "devidamente respondidos."
)

# --------------------------------------------------------------------------
# Seção 3 — Do Local e Das Constatações
# --------------------------------------------------------------------------

TITULO_LOCAL = "Do Local"
TITULO_CONSTATACOES = "Das Constatações (Danos)"

#: Moldura da idoneidade, transcrita. A idônea sai numa frase só; a inidônea
#: exige que o perito diga POR QUÊ — o motivo é achado dele, não texto fixo.
LOCAL_IDONEO = (
    "O local objeto de exame (“Corpo de Delito”) constitui-se de uma área de "
    "natureza {natureza} considerada idônea para efeito de perícia."
)
LOCAL_INIDONEO = (
    "O local objeto de exame (“Corpo de Delito”) constitui-se de uma área de "
    "natureza {natureza} e inidônea para efeito de perícia, uma vez que "
    "{motivo_inidoneidade}."
)

ABERTURA_CONSTATACOES_COM_MEIO = (
    "Os DANOS apontados como sendo de interesse pericial, estão representados "
    "como abaixo descrito, cujos danos, são compatíveis com aqueles produzidos "
    "por {meio_instrumento}:"
)
ABERTURA_CONSTATACOES = (
    "Os DANOS apontados como sendo de interesse pericial, estão representados "
    "como abaixo descrito:"
)
FECHO_CONSTATACOES = (
    "O estado geral de como fora encontrado o ambiente, pelo perito, assim como "
    "os danos acima mencionados, encontra-se reproduzidos nas imagens abaixo."
)

CONCLUSAO = (
    "Em face do exposto, o perito que subscreve o presente laudo de exame, o "
    "conclui afirmando que, efetivamente, o local submetido à perícia, "
    "apresentava DANOS MATERIAIS {resultados}"
)

ABERTURA_QUESITOS = (
    "Assim, passa o perito a transcrever e a responder os quesitos formulados "
    "pela autoridade requisitante, da maneira como segue:"
)

FECHO = (
    "Nada mais havendo a acrescentar, deu-se por findo o presente laudo de exame "
    "pericial que, redigido em {paginas_extenso} ({paginas_numero}) página(s), "
    "segue assinado pelo seu relator."
)

ASSINATURA = "DOCUMENTO ASSINADO DIGITALMENTE"
CARGO = "PERITO CRIMINAL"
#: Os laudos de danos abreviam onde os outros escrevem "Matrícula:".
RODAPE_MATRICULA = "{classe} – Mat.: {matricula}"

LEGENDA_FOTO = "IMAGEM {numero}: {descricao}"

PENDENTE = "[PENDENTE: {o_que}]"

#: Padrões transcritos dos dois laudos reais, por pergunta normalizada.
#:
#: Só entra REMISSÃO ou resposta que não afirme achado. "Houve dano(s)?" →
#: "sim" NÃO entra: é a conclusão pericial do caso, e oferecê-la pronta seria
#: plantar no laudo um achado que o perito não relatou. O mesmo vale para
#: "houve emprego de substância inflamável ou explosiva?" → "não".
RESPOSTAS_CONHECIDAS: dict[str, str] = {
    "podem os senhores peritos determinarem a extensao do(s) dano(s)?": (
        "Vide tópico 3. DOS EXAMES, item 3.2. Das Constatações (Danos)."
    ),
    "qual o meio e quais os instrumentos empregados?": "Vide bojo do presente laudo.",
    "houve subtracao de agregados ou acessorios do objeto examinado?": "Prejudicada.",
    "houve subtracao de agregados ou acessorios do objeto danificado?": "Prejudicada.",
    "qual o valor do objeto danificado?": "Prejudicada.",
    "qual o valor provavel do prejuizo?": "Idem resposta ao quesito anterior.",
    "ha outros detalhes julgados uteis?": "Vide bojo do presente laudo.",
    "ha outros dados julgados uteis?": "Vide bojo do presente laudo.",
}

#: Conjunto do laudo 00016037-31 (Corregedoria PM, art. 321 do CPPM).
QUESITOS_DA_REQUISICAO_MODELO = (
    "Houve dano(s)?",
    "Qual o(s) instrumento(s) ou meio(s) que o(s) produziu(am)?",
    "Qual a natureza do(s) dano(s) causado(s)?",
    "Podem os senhores peritos determinarem a extensão do(s) dano(s)?",
    "Houve subtração de agregados ou acessórios do objeto examinado?",
    "Há outros detalhes julgados úteis?",
)

#: Conjunto do laudo 00016160-22 (Central de Flagrantes). Guardado porque um
#: laudo de danos recebe um ou outro, e a lista certa vem da requisição.
QUESITOS_CENTRAL_DE_FLAGRANTES = (
    "Houve destruição, inutilização ou deterioração da coisa submetida a exame?",
    "Qual o meio e quais os instrumentos empregados?",
    "Houve emprego de substância inflamável ou explosiva?",
    "Qual o valor do objeto danificado?",
    "Qual o valor provável do prejuízo?",
    "Há outros dados julgados úteis?",
)


def normaliza(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", str(texto))
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    return " ".join(sem_acento.lower().split())


def chave_substancia(substancia: str) -> str:
    """Este laudo não trata de substâncias; existe para a interface comum."""
    return ""


def blocos_pendentes() -> list[str]:
    return []


def _feminino(documento: str) -> bool:
    """O documento de solicitação é feminino ("da requisição") ou masculino?

    A concordância sai do artigo que o PERITO escreveu, não de um palpite sobre
    o nome do documento: ele digita "do ofício nº X" ou "da requisição nº Y", e
    o resto da frase acompanha. Sem artigo reconhecível, fica no masculino, que
    é a forma do primeiro laudo de referência.
    """
    return normaliza(documento).startswith("da ")


def campos_extras(admin: dict, colecoes: dict, derivados: dict) -> dict:
    """Marcadores que só este laudo usa, calculados do que o perito informou.

    Nada aqui é achado: é concordância gramatical e recomposição de campos que
    o perito já preencheu.
    """
    documento = str(admin.get("documento_solicitacao", ""))
    fem = _feminino(documento)

    local = (colecoes.get("locais") or [{}])[0]
    recepcao = str(local.get("recepcao", "")).strip()

    paginas = str(derivados.get("paginas", "")).strip()

    return {
        "datado": "datada" if fem else "datado",
        "recebido": "recebida" if fem else "recebido",
        "subscrito": "subscrita" if fem else "subscrito",
        "o_perito_criminal": "o Perito Criminal",
        "finalidade": str(admin.get("finalidade", "")).strip() or FINALIDADES[0],
        "endereco_local": str(local.get("endereco_local", "")).strip(),
        "hora_comunicacao": str(local.get("hora_comunicacao", "")).strip(),
        "hora_chegada": str(local.get("hora_chegada", "")).strip(),
        # O trecho da recepção só existe quando alguém recebeu o perito no
        # local; sem isso a frase segue direto, como no primeiro laudo.
        "recepcao": f"onde fora recebido por {recepcao}, " if recepcao else "",
        "paginas_numero": paginas,
    }


def descricao_objeto(item: dict, admin: dict) -> str:
    """Subseção 3.1 — Do Local, na redação dos laudos reais.

    A moldura é transcrita; a descrição do local é do perito, e entra inteira,
    com as palavras dele.
    """
    natureza = str(item.get("natureza", "")).strip()
    idoneidade = normaliza(item.get("idoneidade", ""))
    motivo = str(item.get("motivo_inidoneidade", "")).strip()

    if idoneidade == "inidonea":
        moldura = LOCAL_INIDONEO.format(
            natureza=natureza,
            motivo_inidoneidade=motivo or PENDENTE.format(
                o_que="motivo pelo qual o local é inidôneo para perícia"
            ),
        )
    else:
        moldura = LOCAL_IDONEO.format(natureza=natureza)

    descricao = str(item.get("descricao_local", "")).strip()
    return f"{moldura}\n{descricao}" if descricao else moldura


def texto_constatacoes(colecoes: dict) -> str:
    """Subseção 3.2 — Das Constatações (Danos).

    Um dano por item registrado. Com mais de um, saem numerados como no laudo
    da cela; com um só, sai corrido como no laudo da ponte. A numeração é
    consequência de quantos danos o perito descreveu, não de uma escolha de
    formatação.
    """
    danos = colecoes.get("danos") or []
    local = (colecoes.get("locais") or [{}])[0]
    meio = str(local.get("meio_instrumento", "")).strip()

    abertura = (
        ABERTURA_CONSTATACOES_COM_MEIO.format(meio_instrumento=meio)
        if meio
        else ABERTURA_CONSTATACOES
    )

    descricoes = [str(d.get("descricao", "")).strip() for d in danos]
    descricoes = [d for d in descricoes if d]
    if not descricoes:
        return abertura + "\n" + PENDENTE.format(o_que="descrição dos danos constatados")

    if len(descricoes) == 1:
        corpo = descricoes[0]
    else:
        corpo = "\n".join(
            f"{numero}. {texto};" for numero, texto in enumerate(descricoes, start=1)
        )

    return "\n".join([abertura, corpo, "", FECHO_CONSTATACOES])


def subsecoes(colecoes: dict, admin: dict) -> list[dict]:
    """Subseções fixas de ``3. DOS EXAMES``, na ordem dos laudos reais.

    Aqui a seção não tem uma subseção por item examinado, como no laudo
    veicular: são sempre duas — o local e o que se constatou nele.
    """
    local = (colecoes.get("locais") or [{}])[0]
    return [
        {"titulo": TITULO_LOCAL, "texto": descricao_objeto(local, admin)},
        {"titulo": TITULO_CONSTATACOES, "texto": texto_constatacoes(colecoes)},
    ]
