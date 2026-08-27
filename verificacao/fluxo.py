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
        print(conversa.resposta_do_assistente(resultado))
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
    fechadas.remove("materiais")

    # Regressão: o extrator devolve um campo gravado E uma entrada de
    # "nao_registrado" por slot vazio. Não pode virar parede de mensagens
    # repetidas, nem dizer "não registrei nada" depois de "Registrei:".
    fala = passo("sim", {}, fala)
    resposta = conversa.resposta_do_assistente(
        conversa.processar(
            exame,
            colecoes,
            fechadas,
            "um tablete de cocaína",
            fala,
            extrator=_stub(
                {
                    "materiais": [{"indice": 3, "campos": {"forma_fisica": "tablete"}}],
                    "nao_registrado": [
                        {"colecao": "materiais", "slot": chave, "motivo": "sem_dado"}
                        for chave in (
                            "massa_liquida_valor",
                            "massa_liquida_unidade",
                            "coloracao",
                            "acondicionamento_quantidade",
                            "acondicionamento_tipo",
                            "observacoes",
                        )
                    ],
                }
            ),
        )
    )
    print("\n>>> um tablete de cocaína")
    print(resposta)
    checa("Registrei:" in resposta, "devia confirmar o campo gravado")
    checa(
        "não registrei nada" not in resposta.lower(),
        "não pode dizer que não registrou nada logo após registrar",
    )
    checa(
        resposta.count("não trouxe informação") == 0,
        "recusa de mensagem inteira não cabe quando houve registro",
    )
    for linha in resposta.splitlines():
        if linha.strip():
            checa(
                resposta.count(linha) == 1,
                f"linha repetida na resposta: {linha[:50]!r}",
            )
    # Regressão: motivo fora do conjunto e "aproximado" sem palavra de estimativa
    # são erro do extrator. Renomeá-los viraria explicação confiante e falsa, então
    # são descartados e a resposta assume a falha de leitura.
    for rotulo, motivo in (("motivo inventado", "unidade diferente"), ("aproximado sem estimativa", "aproximado")):
        resultado = conversa.processar(
            exame, colecoes, fechadas, "1,2 kg", fala,
            extrator=_stub({"nao_registrado": [{
                "colecao": "materiais", "slot": "massa_liquida_valor",
                "motivo": motivo, "trecho": "1,2 kg",
            }]}),
        )
        resposta = conversa.resposta_do_assistente(resultado)
        print(f"\n>>> [{rotulo}] 1,2 kg")
        print(resposta)
        checa(
            "não vou adivinhar" not in resposta and "estimativa" not in resposta,
            f"{rotulo}: recusa inválida do extrator não podia virar explicação",
        )
        checa(
            "quem não entendeu fui eu" in resposta,
            f"{rotulo}: devia assumir a falha em vez de culpar a mensagem",
        )

    colecoes["materiais"] = colecoes["materiais"][:2]
    fechadas.append("materiais")
    fala = conversa.proxima_fala(exame, colecoes, fechadas)

    fala = passo(
        "fiz a análise botânica",
        {
            "exames_realizados": [
                {
                    "indice": 1,
                    "campos": {
                        "nome_teste": "Análise botânica",
                        "item_material": "Material 1",
                        "resultado": "deu certo",
                    },
                }
            ]
        },
        fala,
    )
    checa(
        not colecoes["exames_realizados"][0].get("item_material"),
        "referência entre coleções não é coletada na conversa: quem aponta é o "
        "perito na confirmação",
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
        {"exames_realizados": [{"indice": 1, "campos": {"substancia": "Cannabis sativa L."}}]},
        fala,
    )

    # Ensaio sem redação transcrita: a conversa pede o relato do procedimento,
    # porque sem ele não há como redigir o parágrafo da seção 4.
    fala = passo("sim", {}, fala)
    fala = passo(
        "fiz o Ensaio de Scott Modificado",
        {"exames_realizados": [{"indice": 2, "campos": {"nome_teste": "Ensaio de Scott Modificado"}}]},
        fala,
    )
    fala = passo(
        "positivo para cocaína",
        {"exames_realizados": [{"indice": 2, "campos": {"resultado": "positivo", "substancia": "cocaína"}}]},
        fala,
    )
    checa(
        "conduziu" in fala.texto,
        "ensaio sem redação transcrita devia pedir o relato do procedimento",
    )
    fala = passo(
        "usei o reagente de Scott e deu azul",
        {"exames_realizados": [{"indice": 2, "campos": {"procedimento": "usei o reagente de Scott e deu azul"}}]},
        fala,
    )
    fala = passo("não", {}, fala)

    checa(
        pendencias.completo(exame, colecoes, fechadas, so_conversa=True),
        "a parte da conversa devia estar completa ao fim",
    )
    faltam = [p.rotulo() for p in pendencias.todas(exame, colecoes)]
    print("\npendente para a confirmação:", faltam)
    checa(
        all("Material examinado" in r for r in faltam),
        "só a referência de material devia sobrar para a confirmação",
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
