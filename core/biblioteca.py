"""Biblioteca de redação institucional escrita por perito.

A camada 2 sempre veio de um perito redigindo — o laudo em PDF era só o
transporte. Quando não há laudo cobrindo um ensaio ou uma substância, o perito
escreve o parágrafo uma vez e a ferramenta guarda, indexado por ensaio e
substância. O próximo laudo já sai completo.

O que a IA não pode escrever aqui, e por quê: o parágrafo da seção 4 declara
COMO o exame foi conduzido — qual padrão de referência, qual grandeza
comparada. Um modelo escrevendo isso afirma procedimento pericial que ninguém
relatou, num documento que será assinado. Toda entrada aqui tem autor humano
registrado.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from templates.identificacao_substancia import boilerplate

ARQUIVO = (
    Path(__file__).resolve().parent.parent
    / "templates"
    / "identificacao_substancia"
    / "aprendidos.json"
)

#: "resultado" = parágrafo da seção 4 (ensaio + substância);
#: "proscricao" = texto legal do quesito 03 (substância);
#: "natureza"   = construção da resposta do quesito 01 (substância).
#: "referencia" = referência bibliográfica da substância (seção 6).
TIPOS = ("resultado", "proscricao", "natureza", "referencia")


def chave(*partes: str) -> str:
    return "|".join(boilerplate.normaliza(p) for p in partes if p)


def carregar() -> dict:
    if not ARQUIVO.exists():
        return {tipo: {} for tipo in TIPOS}
    try:
        dados = json.loads(ARQUIVO.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {tipo: {} for tipo in TIPOS}
    return {tipo: dados.get(tipo, {}) for tipo in TIPOS}


def buscar(tipo: str, identificador: str) -> dict | None:
    return carregar().get(tipo, {}).get(identificador)


def salvar(tipo: str, identificador: str, conteudo: dict, autor: str) -> None:
    """Grava uma redação, com autoria e data — nunca anônima."""
    if tipo not in TIPOS:
        raise ValueError(f"tipo desconhecido: {tipo}")
    dados = carregar()
    dados[tipo][identificador] = {
        **conteudo,
        "autor": autor.strip() or "não informado",
        "em": date.today().isoformat(),
    }
    ARQUIVO.parent.mkdir(parents=True, exist_ok=True)
    ARQUIVO.write_text(
        json.dumps(dados, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def remover(tipo: str, identificador: str) -> None:
    dados = carregar()
    if dados.get(tipo, {}).pop(identificador, None) is not None:
        ARQUIVO.write_text(
            json.dumps(dados, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


def resumo() -> dict[str, int]:
    dados = carregar()
    return {tipo: len(dados.get(tipo, {})) for tipo in TIPOS}
