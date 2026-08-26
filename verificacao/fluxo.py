"""Verifica o controlador da conversa sem tocar na API.

Um extrator falso devolve JSON controlado — inclusive JSON malformado de
propósito — para checar que o merge descarta o que tem que descartar e que a
sequência de perguntas respeita a ordem das coleções.

    .venv/bin/python -m verificacao.fluxo
"""

from __future__ import annotations

from config.exams import obter_exame
from core import conversa, pendencias


def _stub(resposta: dict):
    def extrator(exame, colecoes, mensagem, pergunta_pendente="", alvo=""):
        return resposta, "<stub>"

    return extrator


def main() -> int:
    exame = obter_exame("identificacao_substancia")
    colecoes: dict[str, list[dict]] = {}
    fechadas: list[str] = []
    falhas: list[str] = []

    def passo(msg: str, resposta: dict, fala):
        resultado = conversa.processar(
            exame, colecoes, fechadas, msg, fala, extrator=_stub(resposta)
        )
        print(f"\n>>> {msg}")
        print(conversa.resposta_do_assistente(resultado, msg))
        return resultado.fala

    def checa(condicao: bool, descricao: str):
        if not condicao:
            falhas.append(descricao)
            print(f"    ❌ {descricao}")

    fala = conversa.proxima_fala(exame, colecoes, fechadas)
    checa(fala.texto.startswith("Qual a massa"), "abertura devia perguntar a massa")

    fala = passo(
        "eram 15 gramas, erva prensada esverdeada, em 2 invólucros plásticos",
        {
            "materiais": [
                {
                    "indice": 1,
                    "campos": {
                        "massa_liquida_valor": "15",
                        "massa_liquida_unidade": "gramas",
                        "forma_fisica": "erva prensada",
                        "coloracao": "esverdeada",
                        "acondicionamento_quantidade": "2",
                        "acondicionamento_tipo": "invólucros plásticos",
                    },
                }
            ]
        },
        fala,
    )
    checa(
        fala.tipo == conversa.CONFIRMAR_MAIS,
        "material completo devia levar a 'há mais algum material?', não à próxima coleção",
    )

    # Lixo que o validador tem que descartar por inteiro.
    fala = passo(
        "mais alguma coisa?",
        {
            "materiais": [
                {
                    "indice": 1,
                    "campos": {
                        "observacoes": "não informado",
                        "peso_bruto": "30 g",
                        "coloracao": "",
                    },
                }
            ],
            "inexistente": [{"indice": 1, "campos": {"x": "y"}}],
        },
        fala,
    )
    item = colecoes["materiais"][0]
    checa(not item.get("observacoes"), "'não informado' não pode virar valor")
    checa("peso_bruto" not in item, "slot fora do schema não pode entrar")
    checa("inexistente" not in colecoes, "coleção fora do schema não pode entrar")
    checa(len(colecoes["materiais"]) == 1, "pergunta ambígua não pode abrir item novo")

    fala = passo("sim", {}, fala)
    checa(len(colecoes["materiais"]) == 2, "'sim' devia abrir o Material 2")

    fala = passo(
        "20 g de pó branco, 1 invólucro plástico",
        {
            "materiais": [
                {
                    "indice": 2,
                    "campos": {
                        "massa_liquida_valor": "20",
                        "massa_liquida_unidade": "g",
                        "forma_fisica": "pó",
                        "coloracao": "branco",
                        "acondicionamento_quantidade": "1",
                        "acondicionamento_tipo": "invólucro plástico",
                    },
                }
            ]
        },
        fala,
    )

    # A negativa fecha a coleção sem sequer chamar o modelo.
    fala = passo(
        "não, é só isso",
        {"materiais": [{"indice": 3, "campos": {"coloracao": "azul"}}]},
        fala,
    )
    checa("materiais" in fechadas, "'não, é só isso' devia encerrar os materiais")
    checa(len(colecoes["materiais"]) == 2, "negativa não pode criar item nem chamar o modelo")

    fala = passo(
        "fiz o Fast Blue B no material 1",
        {
            "exames_realizados": [
                {
                    "indice": 1,
                    "campos": {
                        "nome_teste": "Fast Blue B",
                        "item_material": "Material 1",
                        "resultado": "deu certo",
                    },
                }
            ]
        },
        fala,
    )
    checa(
        not colecoes["exames_realizados"][0].get("resultado"),
        "resultado fora do conjunto fechado devia ser descartado",
    )

    fala = passo(
        "POSITIVO",
        {"exames_realizados": [{"indice": 1, "campos": {"resultado": "POSITIVO"}}]},
        fala,
    )
    checa(
        colecoes["exames_realizados"][0].get("resultado") == "positivo",
        "resultado devia ser normalizado para a forma canônica",
    )
    checa("substância" in fala.texto.lower(), "positivo devia exigir a substância")

    fala = passo(
        "THC",
        {"exames_realizados": [{"indice": 1, "campos": {"substancia": "THC"}}]},
        fala,
    )
    fala = passo("não", {}, fala)

    checa(
        pendencias.completo(exame, colecoes, fechadas),
        "camada 1 devia estar completa ao fim",
    )
    checa(fala.tipo == conversa.COMPLETO, "fala final devia ser a de conclusão")

    print("\n" + "=" * 60)
    if falhas:
        print(f"{len(falhas)} FALHA(S):")
        for f in falhas:
            print(" -", f)
        return 1
    print("FLUXO OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
