"""E3 — Reprodução de laudos reais a partir da fala do perito.

Para cada par requisição↔laudo oficial:

1. lê a REQUISIÇÃO pelo pipeline real (camada de texto ou OCR) e extrai os
   campos administrativos e os quesitos;
2. alimenta o AGENTE de conversa com falas coloquiais do perito, escritas a
   partir dos fatos do laudo oficial mas nunca copiadas dele;
3. monta o ``.docx`` pelo montador real, com as imagens extraídas do laudo;
4. compara o texto gerado contra o texto do laudo oficial.

O que se mede é se a ferramenta REMONTA o documento oficial a partir de fala
solta — o que exercita a camada 2 (templates), a camada 3 (derivações), os
quesitos, a ordem das seções e a numeração por extenso.

    .venv/bin/python -m experimentos.e3_reproducao [--caso apelido]
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import unicodedata
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parent.parent
load_dotenv(RAIZ / ".env")

from config.exams import obter_exame  # noqa: E402
from core import conversa, documento as montador, llm, requisicao as leitor  # noqa: E402
from experimentos.e3.casos import CASOS  # noqa: E402

PASTA = Path(__file__).resolve().parent / "e3"
EXEMPLOS = RAIZ / "laudos_requisicoes_exemplo"
SAIDA = PASTA / "resultados"

#: Modelo escolhido pelo E1: único 21/21, com mediana de 3,1 s.
MODELO = "gpt-5.2"


def normaliza(texto: str) -> str:
    """Texto comparável: sem acento, sem pontuação solta, espaço colapsado.

    A extração de PDF quebra linha no meio de palavra e espalha espaços; sem
    normalizar, a comparação mediria o extrator de PDF, não a ferramenta.
    """
    sem_acento = unicodedata.normalize("NFKD", texto)
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    limpo = re.sub(r"[^\w\s]", " ", sem_acento.lower())
    return " ".join(limpo.split())


def _texto_do_docx(doc) -> str:
    return "\n".join(p.text for p in doc.paragraphs)


def _imagens(apelido: str, limite: int = 4) -> list[dict]:
    """Fotos do próprio laudo oficial, como anexo documental."""
    pasta = PASTA / "imagens"
    arquivos = sorted(pasta.glob(f"{apelido}_*.png"))[:limite]
    return [
        {
            "assinatura": a.stem,
            "nome": a.name,
            "dados": a.read_bytes(),
            "material": 1,
            "legenda": "",
        }
        for a in arquivos
    ]


def roda_caso(apelido: str, caso: dict, pares: dict) -> dict:
    exame = obter_exame(caso["exame"])
    par = pares[apelido]

    # --- 1. requisição pelo pipeline real
    dados = (EXEMPLOS / par["requisicao"]).read_bytes()
    leitura = leitor.ler(exame, dados, par["requisicao"])
    admin = dict(leitura.campos)
    admin.update(caso.get("admin_extra", {}))
    quesitos = list(leitura.quesitos)
    origem_quesitos = "requisição"
    if not quesitos:
        from core import templates as texto_fixo

        quesitos = list(texto_fixo.texto(exame, "QUESITOS_DA_REQUISICAO_MODELO", ()))
        origem_quesitos = "conjunto-modelo do tipo de exame (a leitura não os trouxe)"

    # --- 2. conversa com o agente real
    colecoes: dict[str, list[dict]] = {
        c.chave: [dict(i) for i in caso.get("colecoes_extra", {}).get(c.chave, [])]
        for c in exame.colecoes
    }
    fechadas: list[str] = []
    respostas: dict[str, str] = {}
    historico: list[dict] = []
    turnos: list[dict] = []

    llm.zerar_contas()
    for fala in caso["falas"]:
        resultado = conversa.processar(
            exame, colecoes, fechadas, fala,
            historico=historico, quesitos=quesitos, respostas=respostas,
        )
        turnos.append(
            {
                "perito": fala,
                "assistente": resultado.mensagem,
                "gravou": [a.descricao() for a in resultado.alteracoes],
                "recusou": [r.motivo for r in resultado.recusas],
                "erro": resultado.erro,
            }
        )
        historico.append({"role": "user", "content": fala})
        historico.append({"role": "assistant", "content": resultado.mensagem})
    contas = llm.contas()

    # --- 3. o que o perito confirma na tela de revisão
    respostas.update(caso.get("respostas_quesitos", {}))
    derivados = dict(caso.get("derivados", {}))

    # --- 4. montagem
    imagens = _imagens(apelido)
    doc = montador.montar(
        admin=admin, colecoes=colecoes, derivados=derivados, imagens=imagens,
        quesitos=quesitos, respostas_quesitos=respostas, exame=exame,
    )
    gerado = _texto_do_docx(doc)
    (SAIDA / f"{apelido}-gerado.txt").write_text(gerado, encoding="utf-8")

    # --- 5. comparação com o oficial
    oficial = (PASTA / "oficiais" / f"{apelido}.txt").read_text(encoding="utf-8")
    n_gerado, n_oficial = normaliza(gerado), normaliza(oficial)
    similaridade = difflib.SequenceMatcher(None, n_oficial, n_gerado).ratio()

    presentes, ausentes = [], []
    for fato in caso.get("fatos_esperados", []):
        (presentes if normaliza(fato) in n_gerado else ausentes).append(fato)

    pendencias = montador.pendencias_do_texto(
        admin=admin, colecoes=colecoes, derivados=derivados,
        quesitos=quesitos, respostas_quesitos=respostas, exame=exame,
    )

    return {
        "apelido": apelido,
        "exame": caso["exame"],
        "descricao": caso["descricao"],
        "requisicao": {
            "arquivo": par["requisicao"],
            "origem_leitura": leitura.origem,
            "nivel": leitura.nivel,
            "campos_extraidos": len(leitura.campos),
            "quesitos_extraidos": len(leitura.quesitos),
            "origem_quesitos": origem_quesitos,
            "descartados": leitura.descartados,
        },
        "conversa": {
            "turnos": turnos,
            "campos_gravados": sum(len(t["gravou"]) for t in turnos),
            "chamadas": contas["chamadas"],
            "segundos": round(contas["segundos"], 1),
            "tokens_entrada": contas["entrada"],
            "tokens_saida": contas["saida"],
        },
        "intervencao_do_perito": {
            "campos_admin_preenchidos_a_mao": len(caso.get("admin_extra", {})),
            "quesitos_escritos": sum(
                1 for v in caso.get("respostas_quesitos", {}).values() if v != "__padrão__"
            ),
            "quesitos_por_padrao": sum(
                1 for v in caso.get("respostas_quesitos", {}).values() if v == "__padrão__"
            ),
            "derivados_confirmados": len(caso.get("derivados", {})),
        },
        "comparacao": {
            "similaridade": round(similaridade, 4),
            "caracteres_gerado": len(n_gerado),
            "caracteres_oficial": len(n_oficial),
            "fatos_presentes": presentes,
            "fatos_ausentes": ausentes,
            "pendencias_no_documento": pendencias,
            "imagens_embutidas": len(imagens),
        },
    }


def main() -> int:
    analisador = argparse.ArgumentParser()
    analisador.add_argument("--caso", default="")
    argumentos = analisador.parse_args()

    pares = json.loads((PASTA / "pares.json").read_text(encoding="utf-8"))
    SAIDA.mkdir(parents=True, exist_ok=True)

    escolhidos = {argumentos.caso: CASOS[argumentos.caso]} if argumentos.caso else CASOS
    destino = SAIDA / "e3_reproducao.json"
    acumulado = {}
    if destino.exists():
        try:
            acumulado = json.loads(destino.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            acumulado = {}
    acumulado.setdefault("casos", {})
    acumulado["modelo"] = MODELO
    acumulado["medido_em"] = datetime.now().isoformat(timespec="seconds")

    import os

    llm.usar_provedor(MODELO, os.getenv("OPENAI_API_KEY", ""), "")
    try:
        for apelido, caso in escolhidos.items():
            print(f"\n=== {apelido} — {caso['descricao']} ===", flush=True)
            medido = roda_caso(apelido, caso, pares)
            acumulado["casos"][apelido] = medido
            c = medido["comparacao"]
            print(f"  similaridade com o oficial: {c['similaridade']:.1%}")
            print(f"  fatos presentes: {len(c['fatos_presentes'])}/"
                  f"{len(c['fatos_presentes']) + len(c['fatos_ausentes'])}")
            if c["fatos_ausentes"]:
                print(f"  AUSENTES: {c['fatos_ausentes']}")
            if c["pendencias_no_documento"]:
                print(f"  pendências no documento: {c['pendencias_no_documento']}")
            destino.write_text(
                json.dumps(acumulado, ensure_ascii=False, indent=2), encoding="utf-8"
            )
    finally:
        llm.soltar_provedor()

    print(f"\nbruto em {destino}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
