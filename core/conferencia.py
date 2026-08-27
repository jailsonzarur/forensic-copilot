"""Conferência entre o requisitado e o examinado — cadeia de custódia.

A autoridade declara o que está enviando ("02 tabletes", "02 trouxinhas"); o
perito descreve o que recebeu e mediu. Se os números não batem, alguma coisa
aconteceu entre a apreensão e a bancada, e isso precisa aparecer antes de o
laudo ser assinado.

A ferramenta **aponta, não conclui**. Divergência pode ter explicação legítima
— o perito consolidou dois invólucros num item, a autoridade contou porções e
o perito contou embalagens. Quem interpreta é ele; o papel daqui é não deixar
passar em silêncio.

Regra que atravessa o módulo: comparar contagem é uma coisa, importar descrição
é outra. Nada do texto da autoridade entra na camada 1.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Observacao:
    """Um ponto que o perito precisa olhar antes de assinar."""

    tipo: str  # "divergencia" | "confere" | "sem_dado"
    texto: str

    @property
    def alerta(self) -> bool:
        return self.tipo == "divergencia"


def _contagens_declaradas(itens: list[dict]) -> list[int]:
    return [
        int(item["quantidade"])
        for item in itens
        if str(item.get("quantidade", "")).isdigit()
    ]


def _contagens_examinadas(materiais: list[dict]) -> list[int]:
    return [
        int(str(m.get("acondicionamento_quantidade", "")).strip())
        for m in materiais
        if str(m.get("acondicionamento_quantidade", "")).strip().isdigit()
    ]


def comparar(itens_declarados: list[dict], materiais: list[dict]) -> list[Observacao]:
    """Confronta o que a autoridade declarou com o que o perito descreveu."""
    if not itens_declarados:
        return [
            Observacao(
                "sem_dado",
                "A requisição não trouxe itens declarados, ou eles não puderam ser "
                "lidos. Sem isso não há conferência de cadeia de custódia — confira "
                "à mão contra o documento.",
            )
        ]

    observacoes: list[Observacao] = []

    if len(itens_declarados) != len(materiais):
        observacoes.append(
            Observacao(
                "divergencia",
                f"A autoridade declarou {len(itens_declarados)} item(ns) de material "
                f"e você descreveu {len(materiais)}.",
            )
        )
    else:
        observacoes.append(
            Observacao(
                "confere",
                f"Quantidade de itens confere: {len(materiais)}.",
            )
        )

    declaradas = _contagens_declaradas(itens_declarados)
    examinadas = _contagens_examinadas(materiais)

    if len(declaradas) < len(itens_declarados):
        observacoes.append(
            Observacao(
                "sem_dado",
                "A autoridade não declarou o número de porções de todos os itens.",
            )
        )
    if len(examinadas) < len(materiais):
        observacoes.append(
            Observacao(
                "sem_dado",
                "Nem todos os materiais têm a quantidade de invólucros registrada.",
            )
        )

    # Comparação por multiconjunto: a ordem dos itens na requisição não precisa
    # ser a mesma em que o perito os descreveu.
    if declaradas and examinadas:
        if sorted(declaradas) == sorted(examinadas):
            observacoes.append(
                Observacao(
                    "confere",
                    "Contagem de porções confere: "
                    + " e ".join(str(n) for n in sorted(declaradas))
                    + ".",
                )
            )
        else:
            observacoes.append(
                Observacao(
                    "divergencia",
                    "Contagem de porções não confere. Declarado pela autoridade: "
                    + ", ".join(str(n) for n in declaradas)
                    + ". Descrito por você: "
                    + ", ".join(str(n) for n in examinadas)
                    + ".",
                )
            )

    total_declarado = sum(declaradas)
    total_examinado = sum(examinadas)
    if declaradas and examinadas and total_declarado != total_examinado:
        observacoes.append(
            Observacao(
                "divergencia",
                f"Total de porções: {total_declarado} declaradas contra "
                f"{total_examinado} examinadas.",
            )
        )

    return observacoes


def ha_divergencia(observacoes: list[Observacao]) -> bool:
    return any(o.alerta for o in observacoes)
