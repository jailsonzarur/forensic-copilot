"""Verificação de pendências da CAMADA 1.

Uma pendência é um campo obrigatório que o perito ainda não informou. Ela vira
uma pergunta dirigida; nunca um valor preenchido por conta própria. Enquanto
houver pendência, o fluxo não avança.
"""

from __future__ import annotations

from dataclasses import dataclass

from config.schema import Colecao, Exame, Slot


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


def pendencias_da_colecao(colecao: Colecao, itens: list[dict]) -> list[Pendencia]:
    encontradas: list[Pendencia] = []
    for indice, item in enumerate(_itens_efetivos(colecao, itens), start=1):
        for slot in colecao.slots:
            if slot.exigido_em(item) and not str(item.get(slot.chave, "")).strip():
                encontradas.append(Pendencia(colecao, indice, slot))
    return encontradas


def todas(exame: Exame, colecoes: dict[str, list[dict]]) -> list[Pendencia]:
    encontradas: list[Pendencia] = []
    for colecao in exame.colecoes:
        encontradas += pendencias_da_colecao(colecao, colecoes.get(colecao.chave, []))
    return encontradas


def completo(exame: Exame, colecoes: dict[str, list[dict]], fechadas: list[str]) -> bool:
    """Camada 1 completa: sem pendência e nenhuma coleção em aberto."""
    if todas(exame, colecoes):
        return False
    return all(colecao.chave in fechadas for colecao in exame.colecoes)


def resumo(exame: Exame, colecoes: dict[str, list[dict]]) -> tuple[int, int]:
    """(campos obrigatórios preenchidos, total de campos obrigatórios)."""
    preenchidos = total = 0
    for colecao in exame.colecoes:
        itens = colecoes.get(colecao.chave, [])
        for item in _itens_efetivos(colecao, itens):
            for slot in colecao.slots:
                if not slot.exigido_em(item):
                    continue
                total += 1
                if str(item.get(slot.chave, "")).strip():
                    preenchidos += 1
    return preenchidos, total
