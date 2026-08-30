"""E1 — Fidelidade da extração comparada entre modelos.

Roda os mesmos casos adversariais de ``verificacao/fidelidade.py`` contra cada
modelo do catálogo e grava o resultado bruto em JSON. O relatório em Markdown é
gerado a partir desse JSON por ``experimentos/relatorio.py``, para que se possa
reescrever o texto sem repetir as chamadas — e para que qualquer número do
relatório possa ser conferido contra o dado medido.

    .venv/bin/python -m experimentos.e1_fidelidade [--repeticoes N] [--so apelido]

Cada caso é uma fala incompleta cujo preenchimento "óbvio" viria do
conhecimento de mundo do modelo, não do perito. O que se mede é se as paredes
determinísticas seguram a invenção em cada modelo, e a que custo de tempo.
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parent.parent
load_dotenv(RAIZ / ".env")

from config.exams import obter_exame  # noqa: E402
from core import llm  # noqa: E402
from experimentos import provedores  # noqa: E402
from verificacao.fidelidade import CASOS, avaliar  # noqa: E402

SAIDA = Path(__file__).resolve().parent / "resultados" / "e1_fidelidade.json"


def roda_provedor(provedor, exame, repeticoes: int) -> dict:
    """Roda todos os casos contra um modelo, ``repeticoes`` vezes."""
    llm.usar_provedor(provedor.modelo, provedor.chave, provedor.base_url)
    registros: list[dict] = []
    try:
        for volta in range(1, repeticoes + 1):
            for caso in CASOS:
                llm.zerar_contas()
                inicio = time.monotonic()
                resultado = avaliar(exame, caso)
                decorrido = time.monotonic() - inicio
                contas = llm.contas()
                registros.append(
                    {
                        "volta": volta,
                        "caso": resultado["nome"],
                        "falas": resultado["falas"],
                        "estado": resultado["estado"],
                        "recusas": resultado["recusas"],
                        "problemas": resultado["problemas"],
                        "erro": resultado["erro"],
                        "segundos": round(decorrido, 2),
                        "chamadas": contas["chamadas"],
                        "tokens_entrada": contas["entrada"],
                        "tokens_saida": contas["saida"],
                        "esperas_por_cota": contas.get("esperas_por_cota", 0),
                    }
                )
                marca = "ok" if not resultado["problemas"] else "FALHA"
                print(
                    f"  [{provedor.apelido}] v{volta} {resultado['nome'][:38]:40} "
                    f"{marca:6} {decorrido:6.1f}s",
                    flush=True,
                )
                if provedor.intervalo:
                    time.sleep(provedor.intervalo)
    finally:
        llm.soltar_provedor()
    return {
        "apelido": provedor.apelido,
        "familia": provedor.familia,
        "modelo": provedor.modelo,
        "motivo": provedor.motivo,
        "registros": registros,
    }


def main() -> int:
    analisador = argparse.ArgumentParser()
    analisador.add_argument("--repeticoes", type=int, default=1)
    analisador.add_argument("--so", default="", help="roda só este apelido")
    argumentos = analisador.parse_args()

    exame = obter_exame("identificacao_substancia")
    elenco = provedores.disponiveis()
    if argumentos.so:
        elenco = [p for p in elenco if p.apelido == argumentos.so]
    if not elenco:
        print("Nenhum modelo disponível — falta chave no .env.")
        return 1

    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    # Preserva o que já foi medido: rodar um modelo de cada vez é a forma
    # prática de conviver com limite de cota, e não pode apagar o resto.
    acumulado: dict = {}
    if SAIDA.exists():
        try:
            acumulado = json.loads(SAIDA.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            acumulado = {}
    acumulado.setdefault("execucoes", {})
    acumulado["casos_no_conjunto"] = len(CASOS)
    acumulado["descartados_na_sondagem"] = [
        {"modelo": m, "motivo": r} for m, r in provedores.DESCARTADOS
    ]

    for provedor in elenco:
        print(f"\n=== {provedor.apelido} ({provedor.familia}) ===", flush=True)
        medido = roda_provedor(provedor, exame, argumentos.repeticoes)
        medido["repeticoes"] = argumentos.repeticoes
        medido["medido_em"] = datetime.now().isoformat(timespec="seconds")
        acumulado["execucoes"][provedor.apelido] = medido
        SAIDA.write_text(
            json.dumps(acumulado, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        aprovados = sum(1 for r in medido["registros"] if not r["problemas"])
        print(
            f"  → {aprovados}/{len(medido['registros'])} casos sem invenção",
            flush=True,
        )

    print(f"\nresultado bruto em {SAIDA}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
