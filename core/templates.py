"""Carrega o texto fixo (camada 2) do tipo de exame em questão.

Cada exame tem o seu pacote em ``templates/``. Sem isto, todo módulo importava
``templates.identificacao_substancia.boilerplate`` direto, e um segundo tipo de
laudo não teria como existir.
"""

from __future__ import annotations

import importlib
from types import ModuleType

from config.schema import Exame

PADRAO = "identificacao_substancia"


def pacote(exame: Exame | None) -> str:
    if exame is None:
        return PADRAO
    return exame.template or exame.id


def boilerplate(exame: Exame | None) -> ModuleType:
    """Módulo de texto fixo do exame, ou o do laudo de substância."""
    try:
        return importlib.import_module(f"templates.{pacote(exame)}.boilerplate")
    except ModuleNotFoundError:
        return importlib.import_module(f"templates.{PADRAO}.boilerplate")


def texto(exame: Exame | None, nome: str, padrao: str = "") -> str:
    """Uma constante do template, ou ``padrao`` quando o exame não a tem."""
    return getattr(boilerplate(exame), nome, padrao)
