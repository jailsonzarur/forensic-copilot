"""Verificação de pendências da CAMADA 1.

Uma pendência é um campo obrigatório que o perito ainda não informou. Ela vira
uma pergunta dirigida; nunca um valor preenchido por conta própria. Enquanto
houver pendência, o fluxo não avança.
"""

from __future__ import annotations

from dataclasses import dataclass

from config.schema import Colecao, Exame, Slot
from core.redacao import tem_redacao


@dataclass(frozen=True)
class Pendencia:
    colecao: Colecao
    indice: int
    slot: Slot

    def pergunta(self, total_itens: int) -> str:
        """Pergunta dirigida, prefixada pelo item quando há mais de um."""
        base = self.slot.pergunta or f"Qual o valor de {self.slot.label}?"
        if total_itens > 1 or self.indice > 1:
            return f"{self.colecao.label_singular} {self.indice} — {base}"
        return base

    def rotulo(self) -> str:
        return f"{self.colecao.label_singular} {self.indice} — {self.slot.label}"


def _itens_efetivos(colecao: Colecao, itens: list[dict]) -> list[dict]:
    """Itens reais mais os itens vazios que o mínimo da coleção ainda exige."""
    faltam = max(colecao.minimo - len(itens), 0)
    return [*itens, *({} for _ in range(faltam))]


def _exigido(slot: Slot, item: dict, so_conversa: bool) -> bool:
    """O slot precisa estar preenchido agora?"""
    if so_conversa and not slot.na_conversa:
        return False  # confirmado pelo perito na tela de confirmação
    if slot.exigido_sem_redacao:
        # Só se cobra o relato de procedimento quando não há parágrafo pronto.
        return not tem_redacao(
            str(item.get("nome_teste", "")), str(item.get("substancia", ""))
        )
    return slot.exigido_em(item)


def pendencias_da_colecao(
    colecao: Colecao, itens: list[dict], so_conversa: bool = False
) -> list[Pendencia]:
    encontradas: list[Pendencia] = []
    for indice, item in enumerate(_itens_efetivos(colecao, itens), start=1):
        for slot in colecao.slots:
            if _exigido(slot, item, so_conversa) and not str(item.get(slot.chave, "")).strip():
                encontradas.append(Pendencia(colecao, indice, slot))
    return encontradas


def todas(
    exame: Exame, colecoes: dict[str, list[dict]], so_conversa: bool = False
) -> list[Pendencia]:
    encontradas: list[Pendencia] = []
    for colecao in exame.colecoes:
        encontradas += pendencias_da_colecao(
            colecao, colecoes.get(colecao.chave, []), so_conversa
        )
    return encontradas


def completo(
    exame: Exame,
    colecoes: dict[str, list[dict]],
    fechadas: list[str],
    so_conversa: bool = False,
) -> bool:
    """Camada 1 completa: sem pendência e nenhuma coleção em aberto."""
    if todas(exame, colecoes, so_conversa):
        return False
    return all(colecao.chave in fechadas for colecao in exame.colecoes)


def resumo(exame: Exame, colecoes: dict[str, list[dict]]) -> tuple[int, int]:
    """(campos obrigatórios preenchidos, total de campos obrigatórios)."""
    preenchidos = total = 0
    for colecao in exame.colecoes:
        itens = colecoes.get(colecao.chave, [])
        for item in _itens_efetivos(colecao, itens):
            for slot in colecao.slots:
                if not _exigido(slot, item, so_conversa=False):
                    continue
                total += 1
                if str(item.get(slot.chave, "")).strip():
                    preenchidos += 1
    return preenchidos, total
