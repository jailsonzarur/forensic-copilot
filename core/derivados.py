"""CAMADA 3 — campos derivados da camada 1.

Derivar é recombinar o que o perito disse, com as palavras dele. Nada aqui
passa pelo LLM: conclusão e legenda são montadas por regra, exibidas como
rascunho e **confirmadas ou reescritas pelo perito** antes de virar documento.

A redação definitiva (como o laudo real escreve "POSITIVO para Cannabis sativa
L." em vez de "POSITIVO para maconha") é vocabulário institucional — camada 2,
que só entra transcrita dos laudos reais. Traduzir o termo do perito para o
termo técnico aqui seria inventar.
"""

from __future__ import annotations

from dataclasses import dataclass

from config.schema import Exame

CHAVE_CONCLUSAO = "conclusao"


@dataclass(frozen=True)
class Derivado:
    """Um campo da camada 3, com a origem à vista para o perito conferir."""

    chave: str
    label: str
    valor: str
    origem: str
    ajuda: str = ""


def _positivos(colecoes: dict[str, list[dict]]) -> list[str]:
    """Substâncias com resultado positivo, na ordem em que apareceram."""
    encontradas: list[str] = []
    for item in colecoes.get("exames_realizados", []):
        if str(item.get("resultado", "")).strip().lower() != "positivo":
            continue
        substancia = str(item.get("substancia", "")).strip()
        if substancia and substancia not in encontradas:
            encontradas.append(substancia)
    return encontradas


def _testes(colecoes: dict[str, list[dict]]) -> list[str]:
    nomes: list[str] = []
    for item in colecoes.get("exames_realizados", []):
        nome = str(item.get("nome_teste", "")).strip()
        if nome and nome not in nomes:
            nomes.append(nome)
    return nomes


def _lista(itens: list[str]) -> str:
    if len(itens) <= 1:
        return "".join(itens)
    return ", ".join(itens[:-1]) + " e " + itens[-1]


def conclusao(colecoes: dict[str, list[dict]]) -> tuple[str, str]:
    """(texto da conclusão, de onde ele saiu)."""
    positivas = _positivos(colecoes)
    if positivas:
        return (
            f"POSITIVO para {_lista(positivas)}.",
            "substâncias dos exames com resultado positivo",
        )

    testes = _testes(colecoes)
    if testes:
        return (
            f"NEGATIVO nos ensaios realizados: {_lista(testes)}.",
            "nenhum exame com resultado positivo",
        )
    return "", "nenhum exame registrado"


def legenda(material: dict, indice_material: int, numero_imagem: int) -> str:
    """Legenda montada com os campos que o próprio perito informou."""
    partes = [
        p
        for p in (
            str(material.get("forma_fisica", "")).strip(),
            str(material.get("coloracao", "")).strip(),
        )
        if p
    ]
    quantidade = str(material.get("acondicionamento_quantidade", "")).strip()
    tipo = str(material.get("acondicionamento_tipo", "")).strip()
    if quantidade and tipo:
        partes.append(f"{quantidade} {tipo}")
    elif tipo:
        partes.append(tipo)

    descricao = ", ".join(partes)
    base = f"Imagem {numero_imagem:02d}: Fotografia do material {indice_material}"
    return f"{base} — {descricao}." if descricao else f"{base}."


def referencia_imagem(numero_imagem: int) -> str:
    return f"(vide imagem {numero_imagem:02d})"


def montar(exame: Exame, colecoes: dict[str, list[dict]]) -> list[Derivado]:
    """Campos derivados que o perito revisa na tela de confirmação."""
    texto, origem = conclusao(colecoes)
    return [
        Derivado(
            chave=CHAVE_CONCLUSAO,
            label="Conclusão",
            valor=texto,
            origem=origem,
            ajuda=(
                "Montada a partir dos resultados que você registrou, com as suas "
                "palavras. A redação técnica do laudo (nome científico, fórmula "
                "consagrada) é sua — edite à vontade."
            ),
        )
    ]
