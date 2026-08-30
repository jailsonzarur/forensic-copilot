"""Catálogo de modelos medidos nos experimentos.

Não usamos LangChain de propósito. Quase todo provedor expõe endpoint
compatível com a API da OpenAI, então trocar de família é trocar ``base_url``,
credencial e nome do modelo — o mesmo cliente serve para todos. Uma camada de
abstração a mais esconderia justamente as diferenças que estes experimentos
existem para medir: recusa de ``temperature`` fixa, suporte a modo JSON,
latência e limite de requisições.

O elenco abaixo foi definido por SONDAGEM, não por catálogo: cada modelo aqui
respondeu a uma chamada real em 2026-08-30. Ver ``resultados/`` para o que a
sondagem descartou e por quê.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

#: Endpoint do Gemini compatível com a API da OpenAI.
GEMINI = "https://generativelanguage.googleapis.com/v1beta/openai/"


@dataclass(frozen=True)
class Provedor:
    """Um modelo a ser medido."""

    apelido: str
    familia: str
    modelo: str
    variavel_chave: str
    base_url: str = ""
    #: Segundos de espera entre chamadas. O free tier do Gemini limita
    #: requisições por minuto e responde 429; espaçar é mais barato que apanhar.
    intervalo: float = 0.0
    #: Por que este modelo está no experimento.
    motivo: str = ""

    @property
    def chave(self) -> str:
        return os.getenv(self.variavel_chave, "")

    @property
    def disponivel(self) -> bool:
        return bool(self.chave)


CATALOGO = (
    # ---- família GPT (OpenAI), conta com faturamento ativo
    Provedor(
        apelido="gpt-4o",
        familia="GPT",
        modelo="gpt-4o",
        variavel_chave="OPENAI_API_KEY",
        motivo="linha de base da geração 4 — citado no plano de trabalho",
    ),
    Provedor(
        apelido="gpt-4.1",
        familia="GPT",
        modelo="gpt-4.1",
        variavel_chave="OPENAI_API_KEY",
        motivo="geração 4 mais recente, para separar geração de versão",
    ),
    Provedor(
        apelido="gpt-5.1",
        familia="GPT",
        modelo="gpt-5.1",
        variavel_chave="OPENAI_API_KEY",
        motivo="geração 5 — testa se o salto de geração muda a fidelidade",
    ),
    Provedor(
        apelido="gpt-5.2",
        familia="GPT",
        modelo="gpt-5.2",
        variavel_chave="OPENAI_API_KEY",
        motivo="geração 5 mais recente disponível na conta",
    ),
    # ---- família Gemini (Google), conta SEM faturamento (free tier)
    Provedor(
        apelido="gemini-3.5-flash-lite",
        familia="Gemini",
        modelo="gemini-3.5-flash-lite",
        variavel_chave="GEMINI_API_KEY",
        base_url=GEMINI,
        intervalo=4.0,
        motivo="o mais rápido da sondagem (1,0 s) — testa o piso de custo",
    ),
    Provedor(
        apelido="gemini-3.5-flash",
        familia="Gemini",
        modelo="gemini-3.5-flash",
        variavel_chave="GEMINI_API_KEY",
        base_url=GEMINI,
        intervalo=4.0,
        motivo="flash intermediário",
    ),
    Provedor(
        apelido="gemini-3.6-flash",
        familia="Gemini",
        modelo="gemini-3.6-flash",
        variavel_chave="GEMINI_API_KEY",
        base_url=GEMINI,
        intervalo=4.0,
        motivo=(
            "sucessor que o próprio Google indica na mensagem de aposentadoria "
            "do gemini-2.5-flash"
        ),
    ),
    Provedor(
        apelido="gemini-3.7-flash",
        familia="Gemini",
        modelo="gemini-3.7-flash",
        variavel_chave="GEMINI_API_KEY",
        base_url=GEMINI,
        intervalo=4.0,
        motivo=(
            "o mais novo da família; a sondagem mediu 144 s numa chamada trivial, "
            "e confirmar isso sob carga é resultado por si só"
        ),
    ),
)

#: Modelos que a sondagem de 2026-08-30 descartou, com o motivo. Ficam
#: registrados porque "não testamos" e "não dá para testar" são coisas
#: diferentes, e o relatório precisa distinguir as duas.
DESCARTADOS = (
    (
        "gemini-2.5-flash",
        "aposentado: 404 com a mensagem 'This model is no longer available to "
        "new users. Please update your code to use models/gemini-3.6-flash'",
    ),
    ("gemini-2.5-pro", "aposentado, mesma mensagem"),
    ("gemini-2.5-flash-lite", "aposentado, mesma mensagem"),
    (
        "gemini-3.1-pro-preview",
        "429 na primeira chamada: os modelos Pro não têm cota no free tier",
    ),
    (
        "gemini-flash-latest",
        "respondeu em 89 s a uma chamada trivial; é apelido móvel, o que torna "
        "o experimento irreprodutível",
    ),
)


def disponiveis() -> list[Provedor]:
    return [p for p in CATALOGO if p.disponivel]


def ausentes() -> list[Provedor]:
    return [p for p in CATALOGO if not p.disponivel]
