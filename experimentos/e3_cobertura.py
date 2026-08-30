"""Cobertura do laudo oficial pelo laudo gerado — a métrica do E3.

Existe separado porque a métrica precisa ser auditável: qualquer porcentagem
do relatório sai daqui, e as decisões que a definem estão explícitas no código,
não escondidas numa planilha.

    .venv/bin/python -m experimentos.e3_cobertura
"""

from __future__ import annotations

import difflib
import json
import re
import unicodedata
from pathlib import Path

RAIZ = Path(__file__).resolve().parent / "e3"
SAIDA = RAIZ / "resultados" / "e3_cobertura.json"

#: Frase curta demais não é conteúdo: é fragmento de quebra de linha do PDF.
MINIMO_DE_CARACTERES = 40

#: Acima disto a frase do oficial é considerada REPRODUZIDA.
LIMIAR_COBERTA = 0.85
#: Entre este valor e o de cima, PARCIAL — o conteúdo aparece, a redação não bate.
LIMIAR_PARCIAL = 0.50

#: Rodapé de paginação do PDF. Não é conteúdo do laudo: é artefato de quem o
#: imprimiu, e cobrá-lo da ferramenta seria medir o gerador de PDF.
RUIDO_DE_PAGINACAO = re.compile(r"pagina\s*\d+\s*de\s*\d+")

#: Legenda e remissão de imagem ("Imagem 02: ...", "vide foto 03"). Excluídas
#: por decisão registrada: a geração de legenda e de referência a imagem é uma
#: frente própria, ainda não implementada, e mantê-la na conta mediria duas
#: coisas ao mesmo tempo.
REFERENCIA_A_IMAGEM = re.compile(
    r"\b(imagem|imagens|foto|fotos|ilustracao|ilustracoes)\s*\d"
)


def normaliza(texto: str) -> str:
    """Texto comparável: sem acento, sem pontuação, espaço colapsado.

    A extração de PDF quebra linha no meio de palavra e espalha espaços. Sem
    normalizar, a medida seria a do extrator de PDF, não a da ferramenta.
    """
    sem_acento = unicodedata.normalize("NFKD", texto)
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^\w\s]", " ", sem_acento.lower()).split())


def frases(texto: str) -> list[str]:
    """Divide em frases por ponto e ponto-e-vírgula.

    Dois-pontos NÃO divide: "Imagem 2: Mostra o material..." é uma legenda só,
    e quebrá-la fazia metade escapar do filtro de imagens e contar como
    conteúdo ausente. Foi erro real de uma medição anterior.
    """
    partes = re.split(r"(?<=[.;])\s+", " ".join(texto.split()))
    return [
        p for p in (x.strip() for x in partes)
        if len(normaliza(p)) >= MINIMO_DE_CARACTERES
    ]


def mede(oficial: str, gerado: str) -> dict:
    """Compara frase a frase. Cada frase do OFICIAL é procurada no GERADO."""
    consideradas: list[str] = []
    fora_paginacao = fora_imagem = 0
    for f in frases(oficial):
        n = normaliza(f)
        if RUIDO_DE_PAGINACAO.search(n):
            fora_paginacao += 1
        elif REFERENCIA_A_IMAGEM.search(n):
            fora_imagem += 1
        else:
            consideradas.append(f)

    inteiro = normaliza(gerado)
    do_gerado = [normaliza(f) for f in frases(gerado)]

    cobertas: list[str] = []
    parciais: list[str] = []
    ausentes: list[str] = []
    for f in consideradas:
        n = normaliza(f)
        # Primeiro procura a frase inteira no texto todo: a ferramenta pode
        # quebrar parágrafos de forma diferente do PDF, e isso não é ausência.
        if n in inteiro:
            melhor = 1.0
        else:
            melhor = max(
                (difflib.SequenceMatcher(None, n, c).ratio() for c in do_gerado),
                default=0.0,
            )
        if melhor >= LIMIAR_COBERTA:
            cobertas.append(f)
        elif melhor >= LIMIAR_PARCIAL:
            parciais.append(f)
        else:
            ausentes.append(f)

    total = len(consideradas) or 1
    return {
        "frases_no_oficial": len(frases(oficial)),
        "excluidas_paginacao": fora_paginacao,
        "excluidas_imagem": fora_imagem,
        "consideradas": len(consideradas),
        "cobertas": len(cobertas),
        "parciais": len(parciais),
        "ausentes": len(ausentes),
        "pct_coberta": round(len(cobertas) / total, 4),
        "pct_parcial": round(len(parciais) / total, 4),
        "pct_ausente": round(len(ausentes) / total, 4),
        "exemplos_ausentes": [f[:160] for f in ausentes[:6]],
    }


def main() -> int:
    pares = json.loads((RAIZ / "pares.json").read_text(encoding="utf-8"))
    resultados: dict = {}
    for oficial in sorted((RAIZ / "oficiais").glob("*.txt")):
        apelido = oficial.stem
        gerado = RAIZ / "resultados" / f"{apelido}-gerado.txt"
        if not gerado.exists():
            continue
        medida = mede(
            oficial.read_text(encoding="utf-8"), gerado.read_text(encoding="utf-8")
        )
        medida["inedito"] = bool(pares.get(apelido, {}).get("inedito"))
        medida["exame"] = pares.get(apelido, {}).get("exame", "")
        resultados[apelido] = medida
        print(
            f"{apelido:28} {medida['consideradas']:3} frases  "
            f"coberta {medida['pct_coberta']:6.1%}  "
            f"parcial {medida['pct_parcial']:6.1%}  "
            f"ausente {medida['pct_ausente']:6.1%}"
        )
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(json.dumps(resultados, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nbruto em {SAIDA}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
