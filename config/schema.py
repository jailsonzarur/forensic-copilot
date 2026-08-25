"""Tipos que descrevem um exame no registro.

Um laudo novo = uma entrada nova em ``config.exams.EXAMES``. As telas leem
estes objetos; nada de UI hardcoded por tipo de exame.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

TipoCampo = Literal["texto", "texto_longo", "data", "select"]


@dataclass(frozen=True)
class CampoAdmin:
    """Campo do formulário administrativo — transcrição pura, sem LLM."""

    chave: str
    label: str
    tipo: TipoCampo = "texto"
    obrigatorio: bool = True
    ajuda: str = ""
    placeholder: str = ""
    opcoes: tuple[str, ...] = ()


@dataclass(frozen=True)
class Slot:
    """Campo da CAMADA 1 — coletado na conversa com o perito.

    ``pergunta`` é a pergunta dirigida usada quando o slot vira pendência.
    ``instrucao_extracao`` orienta o extrator JSON sobre o que capturar; ela
    descreve o formato do dado, nunca sugere um valor.
    ``obrigatorio_se`` torna o slot exigível apenas quando outro slot da mesma
    coleção tem determinado valor — ex.: a substância só é exigida quando o
    resultado do exame é positivo.
    """

    chave: str
    label: str
    obrigatorio: bool = True
    pergunta: str = ""
    instrucao_extracao: str = ""
    obrigatorio_se: tuple[str, str] | None = None
    opcoes: tuple[str, ...] = ()

    def exigido_em(self, item: dict) -> bool:
        """O slot é exigível para este item da coleção?"""
        if self.obrigatorio_se is not None:
            chave, valor = self.obrigatorio_se
            return str(item.get(chave, "")).strip().lower() == valor.lower()
        return self.obrigatorio


@dataclass(frozen=True)
class Colecao:
    """Grupo repetível (1..N) de slots — ex.: itens de material, exames."""

    chave: str
    label_singular: str
    label_plural: str
    slots: tuple[Slot, ...]
    minimo: int = 1
    aceita_imagens: bool = False
    pergunta_mais_um: str = ""

    def slot(self, chave: str) -> Slot | None:
        return next((s for s in self.slots if s.chave == chave), None)


@dataclass(frozen=True)
class Exame:
    """Uma entrada do registro: um tipo de laudo."""

    id: str
    label: str
    descricao: str
    campos_admin: tuple[CampoAdmin, ...]
    colecoes: tuple[Colecao, ...] = ()
    disponivel: bool = True
    observacao_indisponivel: str = ""

    def colecao(self, chave: str) -> Colecao | None:
        return next((c for c in self.colecoes if c.chave == chave), None)
