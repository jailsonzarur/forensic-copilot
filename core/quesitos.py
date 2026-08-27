"""Quesitos — a pergunta que a autoridade formulou na requisição.

Camada 1: transcrição. O perito (ou a extração da requisição) traz a lista, e
cada pergunta recebe o padrão de resposta já transcrito de laudo real. Pergunta
sem padrão conhecido não ganha resposta escolhida por semelhança: fica pendente
para o perito redigir.
"""

from __future__ import annotations

from dataclasses import dataclass

from core import derivados as camada3
from templates.identificacao_substancia import boilerplate


@dataclass
class Quesito:
    numero: str
    pergunta: str
    resposta: str = ""
    #: True quando a resposta saiu de padrão transcrito; False quando é do perito.
    padrao_conhecido: bool = False


def _chave(pergunta: str) -> str:
    return boilerplate.normaliza(pergunta).strip()


def padrao_de_resposta(pergunta: str) -> str:
    """Modelo de resposta transcrito, ou string vazia se a pergunta é nova."""
    return boilerplate.RESPOSTAS_CONHECIDAS.get(_chave(pergunta), "")


def responder(pergunta: str, colecoes: dict[str, list[dict]], derivados: dict) -> tuple[str, bool]:
    """(resposta preenchida, se veio de padrão conhecido)."""
    modelo = padrao_de_resposta(pergunta)
    if not modelo:
        return (
            camada3.PENDENTE.format(o_que=f"resposta ao quesito: {pergunta}"),
            False,
        )
    preenchimento = {
        "natureza": derivados.get(camada3.CHAVE_NATUREZA) or camada3.natureza(colecoes),
        "proscricao": derivados.get(camada3.CHAVE_PROSCRICAO) or camada3.proscricao(colecoes),
    }
    return modelo.format(**preenchimento), True


def numerar(perguntas: list[str]) -> list[Quesito]:
    """Transforma as perguntas transcritas em quesitos numerados 01, 02, ..."""
    return [
        Quesito(numero=f"{i:02d}", pergunta=pergunta.strip())
        for i, pergunta in enumerate(perguntas, start=1)
        if pergunta and pergunta.strip()
    ]


def montar(
    perguntas: list[str],
    colecoes: dict[str, list[dict]],
    derivados: dict,
    respostas_do_perito: dict[str, str] | None = None,
) -> list[Quesito]:
    """Quesitos prontos para o documento, com a resposta do perito prevalecendo."""
    escritas = respostas_do_perito or {}
    prontos: list[Quesito] = []
    for quesito in numerar(perguntas):
        resposta, conhecido = responder(quesito.pergunta, colecoes, derivados)
        propria = escritas.get(quesito.numero, "")
        if propria.strip():
            quesito.resposta = propria
            quesito.padrao_conhecido = conhecido
        else:
            quesito.resposta = resposta
            quesito.padrao_conhecido = conhecido
        prontos.append(quesito)
    return prontos


def sem_padrao(perguntas: list[str]) -> list[str]:
    """Perguntas para as quais não há resposta transcrita de laudo real."""
    return [p.strip() for p in perguntas if p.strip() and not padrao_de_resposta(p)]
