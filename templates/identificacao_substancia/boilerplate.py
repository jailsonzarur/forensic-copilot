"""CAMADA 2 — texto fixo do laudo de Identificação de Substância.

Transcrito do laudo real SB 1252/2019 (demanda 00024529-28), Instituto de
Criminalística da PC-PI. Nada aqui foi redigido: é cópia, com os pontos que
variam trocados por marcadores ``{campo}``.

Os outros três laudos ainda não chegaram. Por isso a descrição técnica só
existe para os dois ensaios que aparecem neste — análise botânica e CCD — e o
texto de proscrição só para Cannabis sativa L. e cocaína. Ensaio ou substância
fora dessa lista vira PENDÊNCIA visível no documento, para o perito redigir.
Preencher por semelhança seria inventar procedimento pericial.
"""

from __future__ import annotations

import unicodedata

PENDENTE = ""

CABECALHO = (
    "GOVERNO DO ESTADO DO PIAUÍ",
    "SECRETARIA DE SEGURANÇA PÚBLICA",
    "POLÍCIA CIVIL DO ESTADO DO PIAUÍ",
    "DEPARTAMENTO DE POLÍCIA TÉCNICO-CIENTÍFICA",
    "INSTITUTO DE CRIMINALÍSTICA",
)

TITULO = "LAUDO DE EXAME PERICIAL"
SUBTITULO = "(QUÍMICA FORENSE)"

PREAMBULO = (
    "Em {data_exame_extenso}, no INSTITUTO DE CRIMINALÍSTICA vinculado ao "
    "DEPARTAMENTO DE POLÍCIA TÉCNICO-CIENTÍFICA da POLÍCIA CIVIL DO ESTADO DO "
    "PIAUÍ, foi recebida solicitação da {orgao_solicitante}, formalizada por meio "
    "do {documento_solicitacao}, datada de {data_documento}, para proceder a "
    "Identificação de Substância(s). A demanda foi encaminhada para o Setor de "
    "Química Forense, sendo posteriormente designado o Perito Criminal "
    "{perito_designado}, que passa a relatar e descrever com verdade e com todas "
    "as circunstâncias que encontrar e, bem assim, esclarecer, quando possível, "
    "tudo quanto possa interessar à Justiça."
)

HISTORICO = (
    "Fora protocolado no Laboratório de Análises sob o n° {protocolo_sbs}, "
    "acompanhado de requisição de exame pericial as substâncias descritas a "
    "seguir, referente ao {tipo_procedimento} Nº {numero_procedimento}, "
    "envolvendo {envolvido}, conforme solicitação."
)

HISTORICO_FECHO = (
    "Atendendo à solicitação supramencionada e de acordo com a demanda, o Perito "
    "Criminal procedeu à análise do material encaminhado para exame pericial."
)

LEGENDA_FOTO = "Foto do material periciado"

CONCLUSAO = (
    "Face aos resultados obtidos após as análises realizadas, o Perito que "
    "subscreve o presente Laudo o conclui afirmando que as substâncias "
    "encaminhadas a exame apresentaram resultados {resultados}."
)

ABERTURA_QUESITOS = (
    "Assim, passa o perito a transcrever e a responder os quesitos formulados, "
    "da maneira como segue:"
)

#: Respostas já transcritas de laudo real, indexadas pela pergunta normalizada.
#:
#: Os quesitos NÃO são texto institucional: são a pergunta que o delegado
#: formulou na requisição, e mudam a cada caso. O que é transcrito aqui é o
#: PADRÃO DE RESPOSTA que o Instituto dá a cada pergunta conhecida. Quesito que
#: não estiver aqui é respondido pelo perito — vira PENDÊNCIA, nunca uma
#: resposta escolhida por semelhança.
RESPOSTAS_CONHECIDAS: dict[str, str] = {
    "qual a natureza do material apresentado a exame?": "{natureza}",
    "quais suas caracteristicas e peso exato?": (
        "Vide tópico IDENTIFICAÇÃO E DESCRIÇÃO DO MATERIAL."
    ),
    "o material apresentado para exame possui propriedade psicotropica ou que "
    "determine dependencia fisica e/ou psiquica?": "Sim. {proscricao}",
    "o material apresentado para exame possui propriedade psicotropica ou que "
    "determine dependencia fisica ou psiquica?": "Sim. {proscricao}",
    "caso afirmativo, causa dependencia fisica ou psiquica?": "Sim.",
    "sao substancias venenosas?": "Não se aplica.",
    "ha outros dados julgados uteis?": "Sem elementos.",
}

#: Conjunto que apareceu na requisição do laudo SB 1252/2019 (Ofício 152/2019-DRO).
#: Serve como ponto de partida quando não há requisição anexada — o perito
#: confere contra o papel dele antes de seguir.
QUESITOS_DA_REQUISICAO_MODELO = (
    "Qual a natureza do material apresentado a exame?",
    "Quais suas características e peso exato?",
    "O material apresentado para exame possui propriedade psicotrópica ou que "
    "determine dependência física e/ou psíquica?",
    "Caso afirmativo, causa dependência física ou psíquica?",
    "São substâncias venenosas?",
    "Há outros dados julgados úteis?",
)

REFERENCIAS = (
    "MOFFAT, A. C. (Ed). Clarke's isolation and identification of drugs. "
    "Londres: Pharmaceutical Press, 1986.",
    "UNITED NATIONS, Manual for use by national narcotics laboratories. "
    "Recommended methods for testing cannabis. New York, 1987.",
    "UNITED NATIONS, Manual for use by national narcotics laboratories. "
    "Recommended methods for testing cocaine. New York, 1986.",
)

FECHO = (
    "Nada mais havendo a acrescentar, deu-se por findo o presente laudo de exame "
    "pericial que, redigido em {paginas_extenso} páginas, segue assinado pelo seu "
    "relator."
)

ASSINATURA = "DOCUMENTO ASSINADO DIGITALMENTE"
CARGO = "PERITO CRIMINAL"

# --------------------------------------------------------------------------
# Descrição técnica dos ensaios (seção RESULTADOS OBTIDOS)
# --------------------------------------------------------------------------

#: Chave: (ensaio normalizado, substância normalizada). O laudo real escreve um
#: parágrafo diferente por combinação — o CCD para material vegetal não é o
#: mesmo texto do CCD para material sólido.
RESULTADOS_POR_ENSAIO: dict[tuple[str, str], dict[str, str]] = {
    ("analise botanica", "cannabis sativa l."): {
        "titulo": "Análise botânica",
        "texto": (
            "O material vegetal foi submetido à avaliação visual para caracterizar "
            "o seu perfil botânico, ao final do ensaio constatou-se tratar-se de "
            "Cannabis sativa L.."
        ),
    },
    ("cromatografia em camada delgada (ccd)", "cannabis sativa l."): {
        "titulo": "Análise por cromatografia em camada delgada para o material vegetal",
        "texto": (
            "Na comparação entre os perfis cromatográficos das amostras (padrão e "
            "periciadas) foi possível elucidar a ocorrência de canabinóides na "
            "substância periciada, entre eles o tetraidrocanabinol (THC). Esses "
            "canabinóides são característicos da espécie vegetal Cannabis sativa L.."
        ),
    },
    ("cromatografia em camada delgada (ccd)", "cocaina"): {
        "titulo": "Análise por cromatografia em camada delgada para o material sólido",
        "texto": (
            "A substância sólida foi submetida à cromatografia em camada delgada "
            "(CCD), onde se utilizou um padrão de cocaína para fins comparativos "
            "entre os tempos de retenção das amostras suspeitas e padrão. Nas "
            "amostras submetidas a exame após a CCD, constatou-se a presença do "
            "alcalóide cocaína."
        ),
    },
}

#: Texto legal de proscrição, por substância. Transcrito do quesito 03.
PROSCRICAO_POR_SUBSTANCIA: dict[str, str] = {
    "cannabis sativa l.": (
        "A Cannabis sativa L., apresenta como um dos componentes em sua composição "
        "química, tetraidrocanabinol, o qual apresenta propriedades psicotrópicas. "
        "Conforme RDC que atualiza o anexo da Portaria 344 SVS/MS de 12 de "
        "fevereiro de 1998 esta substância é proscrita no Brasil."
    ),
    "cocaina": (
        "A cocaína, de acordo com a citada resolução, Lista F1, trata-se de um "
        "entorpecente de uso proscrito no Brasil."
    ),
}

#: Como o laudo nomeia cada substância no quesito 01.
NATUREZA_POR_SUBSTANCIA: dict[str, str] = {
    "cannabis sativa l.": "Cannabis sativa Lineu",
    "cocaina": "cocaína",
}

#: Sinônimos que o perito costuma falar na conversa e que apontam para a mesma
#: entrada. Não traduz nada sozinho: só localiza o texto já transcrito, e o
#: perito confirma a redação na tela de confirmação.
SINONIMOS: dict[str, str] = {
    "thc": "cannabis sativa l.",
    "tetraidrocanabinol": "cannabis sativa l.",
    "cannabis": "cannabis sativa l.",
    "cannabis sativa": "cannabis sativa l.",
    "cannabis sativa lineu": "cannabis sativa l.",
    "maconha": "cannabis sativa l.",
    "canabinoides": "cannabis sativa l.",
    "cocaina": "cocaina",
    "cloridrato de cocaina": "cocaina",
    "crack": PENDENTE,
}


def normaliza(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto)
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    return " ".join(sem_acento.lower().split())


def chave_substancia(substancia: str) -> str:
    """Chave canônica da substância, ou string vazia se não houver texto dela."""
    alvo = normaliza(substancia)
    if alvo in PROSCRICAO_POR_SUBSTANCIA:
        return alvo
    return SINONIMOS.get(alvo, "")


def blocos_pendentes() -> list[str]:
    """Blocos de boilerplate ainda não transcritos dos laudos reais."""
    pendencias = []
    if not RESULTADOS_POR_ENSAIO:
        pendencias.append("descrição técnica dos ensaios")
    if not PROSCRICAO_POR_SUBSTANCIA:
        pendencias.append("texto legal de proscrição")
    if not RESPOSTAS_CONHECIDAS:
        pendencias.append("padrão de resposta dos quesitos")
    if not REFERENCIAS:
        pendencias.append("referências bibliográficas")
    return pendencias


#: Ensaios citados no registro para os quais ainda não há texto transcrito.
ENSAIOS_SEM_TEXTO = (
    "Ensaio de Scott Modificado",
    "Ensaio de Fast Blue B",
    "Espectrometria no Infravermelho (FTIR)",
)
