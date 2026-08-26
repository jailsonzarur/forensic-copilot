"""Verifica a montagem do .docx contra o laudo real SB 1252/2019.

Alimenta o montador com os dados desse laudo e confere se o documento sai com
o mesmo texto. Também checa o que acontece quando falta redação transcrita:
o trecho tem que virar PENDENTE visível, nunca ser preenchido por semelhança.

    .venv/bin/python -m verificacao.documento
"""

from __future__ import annotations

import base64

from config.exams import obter_exame
from core import documento as montador
from core.derivados import montar as derivar

PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAE"
    "hQGAhKmMIQAAAABJRU5ErkJggg=="
)

ADMIN = {
    "numero_laudo": "SB 1252/2019",
    "numero_demanda": "00024529-28",
    "data_exame": "2019-04-26",
    "orgao_solicitante": "10ª DELEGACIA REGIONAL DE POLÍCIA CIVIL – OEIRAS-PI",
    "documento_solicitacao": "Ofício n° 152/2019-DRO",
    "data_documento": "2019-04-23",
    "tipo_procedimento": "IP",
    "numero_procedimento": "030/2019-DRO9",
    "envolvido": "VALTERLY SILVA DOS SANTOS",
    "perito_designado": "Cristiano Ribeiro Gonçalves Affonso",
    "matricula": "218909-7",
    "classe_perito": "Primeira Classe",
    "protocolo_sbs": "SBI0302/2019",
}

COLECOES = {
    "materiais": [
        {
            "massa_liquida_valor": "3,0",
            "massa_liquida_unidade": "g",
            "forma_fisica": "vegetal, desidratada, composta de fragmentos de folhas, caules e frutos",
            "coloracao": "",
            "acondicionamento_quantidade": "2",
            "acondicionamento_tipo": "invólucros plásticos de coloração preta envoltos em fita adesiva verde",
        },
        {
            "massa_liquida_valor": "1,98",
            "massa_liquida_unidade": "kg",
            "forma_fisica": "sólida",
            "coloracao": "branca",
            "acondicionamento_quantidade": "2",
            "acondicionamento_tipo": "volumes retangulares envoltos em plástico transparente",
        },
    ],
    "exames_realizados": [
        {"nome_teste": "Análise botânica", "item_material": "1", "resultado": "positivo", "substancia": "Cannabis sativa L."},
        {"nome_teste": "Cromatografia em Camada Delgada (CCD)", "item_material": "1", "resultado": "positivo", "substancia": "THC"},
        {"nome_teste": "Cromatografia em Camada Delgada (CCD)", "item_material": "2", "resultado": "positivo", "substancia": "cocaína"},
    ],
}

#: Trechos que têm que sair iguais ao laudo real.
ESPERADOS = (
    "GOVERNO DO ESTADO DO PIAUÍ",
    "LAUDO DE EXAME PERICIAL",
    "Em 26 de abril de 2019, no INSTITUTO DE CRIMINALÍSTICA vinculado ao",
    "formalizada por meio do Ofício n° 152/2019-DRO, datada de 23/04/19",
    "Fora protocolado no Laboratório de Análises sob o n° SBI0302/2019",
    "referente ao IP Nº 030/2019-DRO9, envolvendo VALTERLY SILVA DOS SANTOS",
    "a) 3,0 g (três gramas) de substância vegetal, desidratada, composta de "
    "fragmentos de folhas, caules e frutos, distribuídos em 02 (dois) invólucros "
    "plásticos de coloração preta envoltos em fita adesiva verde.",
    "b) 1,98 kg (um quilograma e novecentos e oitenta gramas) de substância "
    "sólida, de coloração branca, distribuídos em 02 (dois) volumes retangulares",
    "Realizaram-se os seguintes exames nas amostras de substância vegetal para "
    "avaliar a ocorrência de Cannabis sativa L.",
    "O material vegetal foi submetido à avaliação visual para caracterizar o seu "
    "perfil botânico, ao final do ensaio constatou-se tratar-se de Cannabis sativa L..",
    "constatou-se a presença do alcalóide cocaína.",
    "POSITIVO para Cannabis sativa L. e POSITIVO para cocaína",
    "A substância vegetal trata-se de Cannabis sativa Lineu.",
    "Vide tópico IDENTIFICAÇÃO E DESCRIÇÃO DO MATERIAL.",
    "Portaria 344 SVS/MS de 12 de fevereiro de 1998",
    "Lista F1, trata-se de um entorpecente de uso proscrito no Brasil.",
    "Não se aplica.",
    "Sem elementos.",
    "MOFFAT, A. C. (Ed). Clarke's isolation and identification of drugs.",
    "DOCUMENTO ASSINADO DIGITALMENTE",
    "CRISTIANO RIBEIRO GONÇALVES AFFONSO",
    "Primeira Classe – Matrícula: 218909-7",
)


def _texto(documento) -> str:
    return "\n".join(p.text for p in documento.paragraphs)


def _monta(colecoes=None, imagens=None, derivados_extra=None):
    colecoes = colecoes or COLECOES
    exame = obter_exame("identificacao_substancia")
    derivados = {d.chave: d.valor for d in derivar(exame, colecoes)}
    derivados.update(derivados_extra or {})
    return montador.montar(ADMIN, colecoes, derivados, imagens or []), derivados, colecoes


def main() -> int:
    falhas: list[str] = []

    def checa(condicao: bool, descricao: str) -> None:
        if not condicao:
            falhas.append(descricao)
            print(f"    ❌ {descricao}")

    documento, derivados, _ = _monta()
    texto = _texto(documento)
    print("parágrafos gerados:", len([p for p in documento.paragraphs if p.text.strip()]))

    for trecho in ESPERADOS:
        checa(trecho in texto, f"faltou no documento: {trecho[:60]}...")

    checa(
        not montador.pendencias_do_texto(ADMIN, COLECOES, derivados),
        "o laudo de referência não devia ter pendência de redação",
    )
    checa("[PENDENTE: número de páginas" in texto, "contagem de páginas devia ficar pendente")

    # Ensaio sem texto transcrito: PENDENTE visível, nunca preenchido por semelhança.
    com_scott = {
        "materiais": COLECOES["materiais"],
        "exames_realizados": [
            *COLECOES["exames_realizados"],
            {"nome_teste": "Ensaio de Scott Modificado", "item_material": "2",
             "resultado": "positivo", "substancia": "cocaína"},
        ],
    }
    documento, derivados, _ = _monta(colecoes=com_scott)
    texto = _texto(documento)
    pendentes = montador.pendencias_do_texto(ADMIN, com_scott, derivados)
    print("pendências com ensaio não transcrito:", pendentes)
    checa(
        any("Scott" in p for p in pendentes),
        "ensaio sem texto transcrito devia aparecer como pendência",
    )
    checa(
        "[PENDENTE: descrição técnica do ensaio Ensaio de Scott Modificado" in texto,
        "o marcador do ensaio pendente devia estar no documento",
    )

    # Substância sem texto legal transcrito.
    com_crack = {
        "materiais": COLECOES["materiais"],
        "exames_realizados": [
            {"nome_teste": "Ensaio de Scott Modificado", "item_material": "2",
             "resultado": "positivo", "substancia": "crack"},
        ],
    }
    _, derivados, _ = _monta(colecoes=com_crack)
    pendentes = montador.pendencias_do_texto(ADMIN, com_crack, derivados)
    print("pendências com substância não transcrita:", pendentes)
    checa(
        any("proscrição" in p for p in pendentes),
        "substância sem texto legal devia virar pendência",
    )

    # Texto confirmado pelo perito manda sobre a regra.
    escrito = "POSITIVO para Cannabis sativa L. (substância vegetal)."
    documento, _, _ = _monta(derivados_extra={"conclusao": escrito})
    checa(escrito.rstrip(".") in _texto(documento), "conclusão confirmada devia ir ao documento")

    # Imagem embutida com a legenda.
    imagem = [{"assinatura": "x", "nome": "foto.png", "dados": PNG, "material": 1,
               "legenda": "Foto do material periciado"}]
    documento, _, _ = _monta(imagens=imagem)
    embutidas = len(documento.inline_shapes)
    print("imagens embutidas:", embutidas)
    checa(embutidas == 1, "a imagem devia estar embutida no .docx")
    checa("Foto do material periciado" in _texto(documento), "a legenda devia acompanhar a foto")

    checa(len(montador.em_bytes(documento)) > 5000, "o .docx devia ter conteúdo")

    print("\n" + "=" * 60)
    if falhas:
        print(f"{len(falhas)} FALHA(S):")
        for f in falhas:
            print(" -", f)
        return 1
    print("DOCUMENTO OK — bate com o laudo de referência")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
