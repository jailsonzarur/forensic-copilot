"""Quesitos — a pergunta que a autoridade formulou na requisição.

Camada 1: transcrição. O perito (ou a extração da requisição) traz a lista, e
cada pergunta recebe o padrão de resposta já transcrito de laudo real. Pergunta
sem padrão conhecido não ganha resposta escolhida por semelhança: fica pendente
para o perito redigir.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from config.schema import Exame
from core import derivados as camada3
from core import templates as texto_fixo


@dataclass
class Quesito:
    numero: str
    pergunta: str
    resposta: str = ""
    #: True quando a resposta saiu de padrão transcrito; False quando é do perito.
    padrao_conhecido: bool = False


#: Marca que o perito aceitou o padrão do Instituto para aquele quesito. Fica
#: como marca, não como texto: assim a resposta continua acompanhando os dados
#: se ele corrigir uma substância depois.
PADRAO_ACEITO = "__padrão__"


#: Enumerador com que a requisição lista os quesitos: "a)", "b.", "1 -", "I)".
#: O laudo renumera como 01, 02, então o prefixo não pode ir junto do texto —
#: nem atrapalhar o casamento com o padrão de resposta transcrito.
#:
#: Os traços vêm em todas as formas: hífen no ofício nativo, meia-risca e
#: travessão na requisição digitalizada. Faltar uma delas deixa o número
#: colado na pergunta.
#: O hífen fica por ÚLTIMO na classe: no meio, ele vira intervalo e come os
#: outros caracteres.
_TRACOS = "\u2010\u2011\u2012\u2013\u2014\u2015\u2212-"
_ENUMERADOR = re.compile(rf"^\s*[a-zA-Z0-9]{{1,3}}\s*[).:{_TRACOS}]\s+")


def sem_enumerador(pergunta: str) -> str:
    return _ENUMERADOR.sub("", str(pergunta)).strip()


def _chave(pergunta: str) -> str:
    return texto_fixo.boilerplate(None).normaliza(sem_enumerador(pergunta)).strip()


def padrao_de_resposta(pergunta: str, exame: Exame | None = None) -> str:
    """Modelo de resposta transcrito, ou string vazia se a pergunta é nova.

    O conjunto de padrões é do TIPO DE EXAME: "Vide item 2. EXAMES" existe no
    laudo veicular e não no de substância.
    """
    conhecidas = texto_fixo.texto(exame, "RESPOSTAS_CONHECIDAS", {})
    return conhecidas.get(_chave(pergunta), "")


class _Preenchimento(dict):
    """Marcadores do padrão de resposta, calculados só quando o texto os pede."""

    def __init__(self, colecoes: dict, derivados: dict):
        super().__init__()
        self._colecoes = colecoes
        self._derivados = derivados

    def __missing__(self, chave: str) -> str:
        if chave == "natureza":
            return self._derivados.get(camada3.CHAVE_NATUREZA) or camada3.natureza(
                self._colecoes
            )
        if chave == "proscricao":
            return self._derivados.get(camada3.CHAVE_PROSCRICAO) or camada3.proscricao(
                self._colecoes
            )
        return ""


def responder(
    pergunta: str,
    colecoes: dict[str, list[dict]],
    derivados: dict,
    exame: Exame | None = None,
) -> tuple[str, bool]:
    """(resposta preenchida, se veio de padrão conhecido)."""
    modelo = padrao_de_resposta(pergunta, exame)
    if not modelo:
        return (
            camada3.PENDENTE.format(o_que=f"resposta ao quesito: {pergunta}"),
            False,
        )
    return modelo.format_map(_Preenchimento(colecoes, derivados)), True


def numerar(perguntas: list[str]) -> list[Quesito]:
    """Transforma as perguntas transcritas em quesitos numerados 01, 02, ..."""
    return [
        Quesito(numero=f"{i:02d}", pergunta=sem_enumerador(pergunta))
        for i, pergunta in enumerate(perguntas, start=1)
        if pergunta and sem_enumerador(pergunta)
    ]


def montar(
    perguntas: list[str],
    colecoes: dict[str, list[dict]],
    derivados: dict,
    respostas_do_perito: dict[str, str] | None = None,
    exame: Exame | None = None,
) -> list[Quesito]:
    """Quesitos prontos para o documento, com a resposta do perito prevalecendo."""
    escritas = respostas_do_perito or {}
    prontos: list[Quesito] = []
    for quesito in numerar(perguntas):
        resposta, conhecido = responder(quesito.pergunta, colecoes, derivados, exame)
        propria = str(escritas.get(quesito.numero, "")).strip()
        quesito.padrao_conhecido = conhecido
        if propria and propria != PADRAO_ACEITO:
            quesito.resposta = propria
        else:
            quesito.resposta = resposta
        prontos.append(quesito)
    return prontos


def respondido(numero: str, respostas: dict[str, str]) -> bool:
    return bool(str(respostas.get(numero, "")).strip())


def pendentes(perguntas: list[str], respostas: dict[str, str]) -> list[Quesito]:
    """Quesitos que o perito ainda não respondeu nem confirmou."""
    return [q for q in numerar(perguntas) if not respondido(q.numero, respostas)]


def sem_padrao(perguntas: list[str], exame: Exame | None = None) -> list[str]:
    """Perguntas para as quais não há resposta transcrita de laudo real."""
    return [
        p.strip() for p in perguntas if p.strip() and not padrao_de_resposta(p, exame)
    ]
