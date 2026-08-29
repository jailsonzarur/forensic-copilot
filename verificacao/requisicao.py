"""Verifica a leitura da requisição sem chamar a API.

O que importa aqui não é acertar a transcrição — é o que a ferramenta faz
quando a transcrição erra. Foi medido neste projeto: três leituras da mesma
requisição digitalizada devolveram três redações diferentes para o mesmo
quesito, e nenhuma batia com o papel.

    .venv/bin/python -m verificacao.requisicao
"""

from __future__ import annotations

from config.exams import obter_exame
from core import ocr
from core import quesitos as camada1_quesitos
from core import requisicao as leitor

#: Quesitos como o OCR os devolveu na requisição real, com o ruído incluído
#: ("possuí" em vez de "possui"). O casamento com o padrão de resposta não pode
#: quebrar por causa disso.
QUESITOS_COM_RUIDO = (
    "Qual a natureza do material apresentado a exame?",
    "Quais suas características e peso exato?",
    "O material apresentado para exame possuí propriedade psicotrópica ou que "
    "determine dependência física ou psíquica?",
    "Caso afirmativo, causa dependência física ou psíquica?",
    "São substâncias venenosas?",
    "Há outros dados julgados úteis?",
)

TEXTO = """10ª DELEGACIA REGIONAL DE POLÍCIA CIVIL - OEIRAS/PI
Ofício n.º 152/2019-DRO
Oeiras/PI, 23 de abril de 2019
requisitar EXAME PERICIAL no material apreendido em poder do nacional:
VALTERLY SILVA DOS SANTOS ("TERLY"); Ref. IP N° 030/2019-DRO;
02 (dois) tabletes de uma substância esbranquiçada, com características
semelhantes à pasta base de cocaína;
a) Qual a natureza do material apresentado a exame?
b) São substâncias venenosas?
"""


def _leitura(campos: dict, quesitos: list[str]) -> leitor.Leitura:
    return leitor.Leitura(
        texto=TEXTO,
        campos={k: v[0] for k, v in campos.items()},
        trechos={k: v[1] for k, v in campos.items()},
        quesitos=list(quesitos),
    )


def main() -> int:
    exame = obter_exame("identificacao_substancia")
    falhas: list[str] = []

    def checa(condicao: bool, descricao: str) -> None:
        if not condicao:
            falhas.append(descricao)
            print(f"    ❌ {descricao}")

    # 1. Valor sem citação conferível é descartado, não gravado.
    operacoes = {
        "admin": {
            "orgao_solicitante": {
                "valor": "10ª DELEGACIA REGIONAL DE POLÍCIA CIVIL - OEIRAS/PI",
                "trecho": "10ª DELEGACIA REGIONAL DE POLÍCIA CIVIL - OEIRAS/PI",
            },
            "perito_designado": {"valor": "Fulano", "trecho": "Fulano"},
            "envolvido": {"valor": "JOÃO INVENTADO", "trecho": "JOÃO INVENTADO"},
        },
        "quesitos": [
            "Qual a natureza do material apresentado a exame?",
            "Quesito que o modelo inventou e não está no papel?",
        ],
    }
    import core.requisicao as modulo

    original = modulo.chamar_json
    modulo.chamar_json = lambda sistema, instrucao: (operacoes, "<stub>")
    try:
        leitura = leitor.extrair(exame, TEXTO)
    finally:
        modulo.chamar_json = original

    print("campos aceitos:", leitura.campos)
    print("descartados:", leitura.descartados)
    checa("orgao_solicitante" in leitura.campos, "valor com citação real devia entrar")
    checa("envolvido" not in leitura.campos, "citação que não existe no texto devia ser descartada")
    checa(
        "perito_designado" not in leitura.campos,
        "campo que só o Instituto atribui não pode vir da requisição",
    )
    checa(len(leitura.quesitos) == 1, "quesito inventado devia ser descartado")

    # 2. Divergência entre passes vira leitura incerta, não valor.
    estavel = ("Ofício n.º 152/2019-DRO", "Ofício n.º 152/2019-DRO")
    leituras = [
        _leitura(
            {"documento_solicitacao": estavel, "envolvido": ("VALTERLY SILVA DOS SANTOS", "VALTERLY")},
            ["Qual a natureza do material apresentado a exame?", "Caso afirmativo, causa dependência física ou psíquica?"],
        ),
        _leitura(
            {"documento_solicitacao": estavel, "envolvido": ("VALTERY SILVA DOS SANTOS", "VALTERY")},
            ["Qual a natureza do material apresentado a exame?", "Caso positivo, qual a classificação da substância?"],
        ),
        _leitura(
            {"documento_solicitacao": estavel, "envolvido": ("VALTERLY S. DOS SANTOS", "VALTERLY S.")},
            ["Qual a natureza do material apresentado a exame?", "Caso positivo, essa substância é entorpecente?"],
        ),
    ]
    final = leitor._consolidar(leituras, exame)
    print("\nconsolidado -> campos:", final.campos)
    print("consolidado -> quesitos:", final.quesitos)
    print("consolidado -> incertos:", final.incertos)

    checa(
        final.campos.get("documento_solicitacao") == "Ofício n.º 152/2019-DRO",
        "valor idêntico nos três passes devia ser proposto",
    )
    checa("envolvido" not in final.campos, "nome que variou entre passes não pode virar valor")
    checa(
        any("Envolvido" in i for i in final.incertos),
        "o que variou devia ser sinalizado como leitura incerta",
    )
    checa(final.quesitos[0].startswith("Qual a natureza"), "quesito estável devia passar")
    checa(final.quesitos[1] == "", "quesito que variou não pode ser proposto")
    checa(
        any("quesito 02" in i for i in final.incertos),
        "o quesito instável devia ser sinalizado",
    )
    checa(not final.confiavel, "leitura de imagem nunca é marcada como confiável")

    # 3. Contagem diferente de quesitos entre passes derruba a lista inteira.
    curto = _leitura({}, ["Só um quesito?"])
    final = leitor._consolidar([leituras[0], curto], exame)
    checa(
        not final.quesitos and any("lista de quesitos" in i for i in final.incertos),
        "número de quesitos divergente devia invalidar a lista",
    )

    # 4. Ruído de OCR não pode quebrar o casamento com o padrão de resposta.
    montados = camada1_quesitos.montar(
        list(QUESITOS_COM_RUIDO),
        {"materiais": [{"forma_fisica": "vegetal"}],
         "exames_realizados": [{"nome_teste": "CCD", "item_material": "1",
                                "resultado": "positivo", "substancia": "THC"}]},
        {},
    )
    sem_padrao = [q.numero for q in montados if not q.padrao_conhecido]
    print("\nquesitos com ruído de OCR sem padrão:", sem_padrao or "(nenhum)")
    checa(not sem_padrao, "ruído de OCR não podia quebrar o casamento dos quesitos")

    # 5. A requisição lista os quesitos como "a)", "b)". O enumerador não pode ir
    #    junto do texto: o laudo renumera como 01, 02, e o prefixo quebrava o
    #    casamento com o padrão de resposta transcrito.
    # Traço em todas as formas: hífen do ofício nativo, meia-risca e travessão
    # da requisição digitalizada. O travessão escapou uma vez e deixou "4 —"
    # colado na pergunta.
    com_letra = [
        "a) Qual a natureza do material apresentado a exame?",
        "b. Quais suas características e peso exato?",
        "1 - São substâncias venenosas?",
        "2 – Há outros dados julgados úteis?",
        "4 — Qual a natureza do material apresentado a exame?",
    ]
    limpos = camada1_quesitos.numerar(com_letra)
    print("\nquesitos sem enumerador:", [q.pergunta for q in limpos])
    checa(
        all(q.pergunta[0].isupper() for q in limpos),
        "o enumerador da requisição não podia ficar no texto do quesito",
    )
    checa(
        all(camada1_quesitos.padrao_de_resposta(p) for p in com_letra),
        "o enumerador não podia impedir o casamento com o padrão de resposta",
    )

    # 6. O caminho de leitura precisa preferir OCR ao modelo de visão.
    print("tesseract disponível nesta máquina:", ocr.disponivel())

    print("\n" + "=" * 60)
    if falhas:
        print(f"{len(falhas)} FALHA(S):")
        for f in falhas:
            print(" -", f)
        return 1
    print("REQUISIÇÃO OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
