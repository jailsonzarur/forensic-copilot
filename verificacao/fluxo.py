"""Verifica o controlador da conversa sem tocar na API.

Um extrator falso devolve JSON controlado — inclusive JSON malformado de
propósito — para checar que o merge descarta o que tem que descartar e que a
travessia segue a ordem certa: material, exames DAQUELE material, próximo
material, e só no fim os quesitos da requisição.

    .venv/bin/python -m verificacao.fluxo
"""

from __future__ import annotations

from config.exams import obter_exame
from core import conversa, pendencias

MATERIAL_1 = {
    "massa_liquida_valor": "15",
    "massa_liquida_unidade": "gramas",
    "forma_fisica": "erva prensada",
    "coloracao": "esverdeada",
    "acondicionamento_quantidade": "2",
    "acondicionamento_tipo": "invólucros plásticos",
}
MATERIAL_2 = {
    "massa_liquida_valor": "20",
    "massa_liquida_unidade": "g",
    "forma_fisica": "pó",
    "coloracao": "branco",
    "acondicionamento_quantidade": "1",
    "acondicionamento_tipo": "invólucro plástico",
}


def _stub(resposta: dict):
    def extrator(exame, colecoes, mensagem, pergunta_pendente="", alvo=""):
        return resposta, "<stub>"

    return extrator


def main() -> int:
    exame = obter_exame("identificacao_substancia")
    colecoes: dict[str, list[dict]] = {}
    fechadas: list[str] = []
    quesitos = ["São substâncias venenosas?"]
    respostas: dict[str, str] = {}
    falhas: list[str] = []

    def passo(msg: str, resposta: dict, fala):
        resultado = conversa.processar(
            exame, colecoes, fechadas, msg, fala,
            extrator=_stub(resposta), quesitos=quesitos, respostas=respostas,
        )
        print(f"\n>>> {msg}")
        print(conversa.resposta_do_assistente(resultado))
        return resultado.fala

    def checa(condicao: bool, descricao: str):
        if not condicao:
            falhas.append(descricao)
            print(f"    ❌ {descricao}")

    fala = conversa.proxima_fala(exame, colecoes, fechadas, quesitos, respostas)
    checa(fala.texto.startswith("Qual a massa"), "abertura devia perguntar a massa")

    # --- Material 1
    fala = passo(
        "15 gramas de erva prensada esverdeada em 2 invólucros plásticos",
        {"materiais": [{"indice": 1, "campos": dict(MATERIAL_1)}]},
        fala,
    )
    checa(
        "exame" in fala.texto.lower(),
        "material completo devia levar aos exames DELE, não a 'há mais material?'",
    )

    # Lixo que o validador tem que descartar por inteiro.
    fala = passo(
        "mais alguma coisa?",
        {
            "materiais": [{"indice": 1, "campos": {
                "observacoes": "não informado", "peso_bruto": "30 g", "coloracao": ""}}],
            "inexistente": [{"indice": 1, "campos": {"x": "y"}}],
        },
        fala,
    )
    item = colecoes["materiais"][0]
    checa(not item.get("observacoes"), "'não informado' não pode virar valor")
    checa("peso_bruto" not in item, "slot fora do schema não pode entrar")
    checa("inexistente" not in colecoes, "coleção fora do schema não pode entrar")
    checa(len(colecoes["materiais"]) == 1, "pergunta ambígua não pode abrir item novo")

    # --- Exame do Material 1: valor fora do conjunto fechado é descartado
    fala = passo(
        "fiz a análise botânica",
        {"exames_realizados": [{"indice": 1, "campos": {
            "nome_teste": "Análise botânica", "resultado": "deu certo"}}]},
        fala,
    )
    checa(
        not colecoes["exames_realizados"][0].get("resultado"),
        "resultado fora do conjunto fechado devia ser descartado",
    )
    checa(
        colecoes["exames_realizados"][0].get("item_material") == "1",
        "o exame devia ser vinculado ao material em foco, sem perguntar",
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
        "Cannabis sativa L.",
        {"exames_realizados": [{"indice": 1, "campos": {"substancia": "Cannabis sativa L."}}]},
        fala,
    )
    checa(
        "mais algum exame" in fala.texto.lower(),
        "exame completo devia perguntar por outro exame DESTE material",
    )

    # Negativa fecha os exames deste material sem chamar o modelo.
    fala = passo(
        "não",
        {"exames_realizados": [{"indice": 2, "campos": {"nome_teste": "inventado"}}]},
        fala,
    )
    checa("exames_realizados:1" in fechadas, "devia encerrar os exames do Material 1")
    checa(len(colecoes["exames_realizados"]) == 1, "negativa não pode criar item")
    checa(
        "mais algum material" in fala.texto.lower(),
        "só então devia perguntar por outro material",
    )

    # --- Material 2 e o exame dele
    fala = passo("sim", {}, fala)
    checa(len(colecoes["materiais"]) == 2, "'sim' devia abrir o Material 2")

    fala = passo(
        "20 g de pó branco, 1 invólucro plástico",
        {"materiais": [{"indice": 2, "campos": dict(MATERIAL_2)}]},
        fala,
    )
    fala = passo(
        "Ensaio de Scott Modificado, positivo para cocaína",
        {"exames_realizados": [{"indice": 2, "campos": {
            "nome_teste": "Ensaio de Scott Modificado",
            "resultado": "positivo", "substancia": "cocaína"}}]},
        fala,
    )
    checa(
        colecoes["exames_realizados"][1].get("item_material") == "2",
        "o segundo exame devia ficar preso ao Material 2",
    )
    checa(
        "conduziu" in fala.texto,
        "ensaio sem redação transcrita devia pedir o relato do procedimento",
    )
    fala = passo(
        "usei o reagente de Scott e deu azul",
        {"exames_realizados": [{"indice": 2, "campos": {
            "procedimento": "usei o reagente de Scott e deu azul"}}]},
        fala,
    )
    fala = passo("não", {}, fala)
    fala = passo("não", {}, fala)

    # --- Quesitos da requisição
    checa(fala.tipo == conversa.QUESITO, "no fim, devia perguntar os quesitos")
    fala = passo("confirmo", {}, fala)
    checa(respostas.get("01"), "a confirmação do quesito devia ser gravada")

    faltam = [p.rotulo() for p in pendencias.todas(exame, colecoes)]
    print("\nainda pendente:", faltam or "(nada)")
    checa(not faltam, "nenhum campo obrigatório pode sobrar ao fim da conversa")
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
