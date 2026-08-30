"""Verificação de pendências da CAMADA 1.

Uma pendência é um campo obrigatório que o perito ainda não informou. Ela vira
uma pergunta dirigida; nunca um valor preenchido por conta própria. Enquanto
houver pendência, o fluxo não avança.
"""

from __future__ import annotations

from dataclasses import dataclass

from config.schema import Colecao, Etapa, Exame, Slot
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
    """Camada 1 completa por DADOS — encerramento é sinal, não gate.

    Cada coleção obrigatória tem itens suficientes com todos os campos
    obrigatórios preenchidos. O perito não precisa dizer "não há mais" pra
    avançar; se sobrou item, ele adiciona pelo painel.
    """
    if todas(exame, colecoes, so_conversa):
        return False
    for colecao in exame.colecoes:
        if not _etapa_de_colecao_completa(colecao, colecoes, fechadas):
            return False
    return True


def resumo(
    exame: Exame, colecoes: dict[str, list[dict]], so_conversa: bool = False
) -> tuple[int, int]:
    """(campos obrigatórios preenchidos, total de campos obrigatórios)."""
    preenchidos = total = 0
    for colecao in exame.colecoes:
        itens = colecoes.get(colecao.chave, [])
        for item in _itens_efetivos(colecao, itens):
            for slot in colecao.slots:
                if not _exigido(slot, item, so_conversa):
                    continue
                total += 1
                if str(item.get(slot.chave, "")).strip():
                    preenchidos += 1
    return preenchidos, total


def _etapa_de_colecao_completa(
    colecao: Colecao,
    colecoes: dict[str, list[dict]],
    fechadas: list[str],
) -> bool:
    """A coleção-mãe desta etapa tem dados suficientes pra prosseguir.

    Regra permissiva: se todos os campos obrigatórios dos itens registrados
    estão preenchidos E temos pelo menos ``colecao.minimo`` itens, a etapa
    está logicamente completa — a conversa segue pra próxima etapa mesmo sem
    o perito dizer "não há mais". Ele pode adicionar itens depois via o
    painel de estado se lembrar de algo.

    Encerramento explícito (``fechadas``) continua sendo um sinal que o agente
    pode registrar quando o perito diz "acabou", pra não perguntar "algo
    mais?" desnecessariamente. Mas não é gate: o fluxo é ditado pelos DADOS.
    """
    itens = colecoes.get(colecao.chave, [])
    if len(itens) < colecao.minimo:
        return False
    if pendencias_da_colecao(colecao, itens, so_conversa=True):
        return False
    # Vinculadas: cada item da coleção-mãe precisa ter pelo menos ``minimo``
    # filhos (ex.: cada material precisa ter ao menos 1 exame realizado).
    if colecao.vinculada_a:
        itens_mae = colecoes.get(colecao.vinculada_a, [])
        for indice_mae in range(1, len(itens_mae) + 1):
            filhos = [
                item for item in itens
                if str(item.get("item_material", "")).strip() == str(indice_mae)
            ]
            if len(filhos) < colecao.minimo:
                return False
    return True


def _etapa_de_quesitos_completa(
    quesitos: list[str], respostas: dict[str, str]
) -> bool:
    from core import quesitos as camada1_quesitos
    return not camada1_quesitos.pendentes(quesitos, respostas)


def etapa_atual(
    exame: Exame,
    colecoes: dict[str, list[dict]],
    fechadas: list[str],
    quesitos: list[str],
    respostas: dict[str, str],
) -> Etapa | None:
    """Primeira etapa não completa, na ordem declarada pelo tipo de laudo.

    O agente é 100% conversacional, mas o roteiro é nosso: esta função calcula
    determinísticamente onde a conversa está, para que o prompt possa avisar o
    agente e ele não pule pra frente. Devolve None quando tudo está pronto.
    """
    for etapa in exame.etapas:
        if etapa.quesitos:
            if not _etapa_de_quesitos_completa(quesitos, respostas):
                return etapa
            continue
        colecao = exame.colecao(etapa.colecao)
        if colecao is None:
            continue
        if not _etapa_de_colecao_completa(colecao, colecoes, fechadas):
            return etapa
    return None
