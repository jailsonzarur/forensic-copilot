"""Verifica o laudo de identificação veicular contra os laudos reais.

Alimenta o montador com os dados das demandas 00078413-75 e 00082450-35 e
confere se sai o mesmo texto — inclusive as diferenças de estrutura que
justificaram o refactor: sem histórico, sem referências, imagens em apêndice e
mais de um perito signatário.

    .venv/bin/python -m verificacao.veicular
"""

from __future__ import annotations

import base64

from config.exams import obter_exame
from core import documento as montador
from templates.identificacao_veicular import boilerplate as texto

PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAE"
    "hQGAhKmMIQAAAABJRU5ErkJggg=="
)

#: Parágrafos como estão nos laudos reais. Se a montagem divergir de um
#: caractere, o teste aponta.
PARAGRAFOS_REAIS = {
    "niv-positivo-um-caractere": (
        {
            "identificador": "NIV",
            "numeracao_observada": "9C2JC7000NR023501",
            "local_gravacao": "gravados no setor posterior do chassi, sob o banco",
            "caracteres_divergentes": "o 17º (décimo sétimo) caractere",
            "tratamento": "somente observação óptica",
            "resultado_revelacao": "positivo",
            "numeracao_revelada": "9C2JC7000NR023508",
        },
        "Observando-se o local de gravação dos sinais identificadores da Numeração de "
        "Identificação Veicular – NIV: 9C2JC7000NR023501 (gravados no setor posterior "
        "do chassi, sob o banco), verificou-se que o 17º (décimo sétimo) caractere "
        "apresentava formato, profundidade e tamanho divergente dos padrões originais "
        "de fábrica. Realizando-se a observação com o auxílio de instrumentos ópticos "
        "apropriados, obteve-se resultado POSITIVO quanto à revelação do caractere "
        "latente original do NIV: 9C2JC7000NR023508.",
    ),
    "motor-positivo-todos": (
        {
            "identificador": "Motor",
            "numeracao_observada": "JC70E0N023626",
            "local_gravacao": "gravada no bloco",
            "caracteres_divergentes": "todos os caracteres",
            "tratamento": "reagentes em liga metálica",
            "resultado_revelacao": "positivo",
            "numeracao_revelada": "JC70E0N023554",
        },
        "Examinando-se a numeração do motor: JC70E0N023626 (gravada no bloco), "
        "verificou-se que todos os caracteres apresentavam formato, profundidade e "
        "tamanho divergente dos padrões originais de fábrica. Realizando-se a "
        "aplicação dos reagentes químicos específicos para revelação de gravação "
        "latente em liga metálica, e observação com o auxílio de instrumentos ópticos "
        "apropriados, obteve-se resultado POSITIVO quanto à revelação dos caracteres "
        "latentes originais do número de motor: JC70E0N023554.",
    ),
    "niv-negativo": (
        {
            "identificador": "NIV",
            "numeracao_observada": "9C2KC1670DR452854",
            "local_gravacao": "gravados na base do guidão, lado direito",
            "caracteres_divergentes": "todos os caracteres",
            "tratamento": "reagentes em ferro e aço",
            "resultado_revelacao": "negativo",
        },
        "Observando-se o local de gravação dos sinais identificadores da Numeração de "
        "Identificação Veicular – NIV: 9C2KC1670DR452854 (gravados na base do guidão, "
        "lado direito), verificou-se que todos os caracteres apresentavam formato, "
        "profundidade e tamanho divergente dos padrões originais de fábrica. "
        "Realizando-se a aplicação dos reagentes químicos específicos para revelação "
        "de gravação latente em ferro e aço, e observação com o auxílio de instrumentos "
        "ópticos apropriados, obteve-se resultado NEGATIVO quanto à revelação dos "
        "caracteres latentes originais do NIV.",
    ),
}

ADMIN = {
    "numero_demanda": "00078413-75",
    "data_exame": "2024-05-09",
    "orgao_solicitante": "POLÍCIA CIVIL DO PIAUÍ - DEPARTAMENTO DE ROUBO E FURTO DE VEÍCULOS",
    "documento_solicitacao": "da Requisição S/N",
    "tipo_procedimento": "BO",
    "numero_procedimento": "83111/2024",
    "data_realizacao": "2024-08-08",
    "local_exame": "pátio da Central de Flagrantes, Teresina-PI",
    "data_encerramento": "2024-08-08",
    "peritos": [{"perito_designado": "ALEXANDRE CITÓ LOPES", "matricula": "271.271-7"}],
}

COLECOES = {
    "veiculos": [
        {
            "abertura": "Foi apresentada a",
            "tipo_veiculo": "motoneta",
            "marca_modelo": "HONDA/BIZ 110I",
            "cor": "vermelha",
            "placa": "",
            "lacres": "Lacre DPTC 1829131, Lacre Laranja 0003485",
        }
    ],
    "exames_veiculo": [
        {**PARAGRAFOS_REAIS["niv-positivo-um-caractere"][0], "item_material": "1"},
        {**PARAGRAFOS_REAIS["motor-positivo-todos"][0], "item_material": "1"},
        {"identificador": "Placa", "item_material": "1",
         "descricao_placa": "O veículo não exibe placa."},
    ],
}

QUESITOS = list(texto.QUESITOS_DA_REQUISICAO_MODELO)


def main() -> int:
    falhas: list[str] = []

    def checa(condicao: bool, descricao: str) -> None:
        if not condicao:
            falhas.append(descricao)
            print(f"    ❌ {descricao}")

    # 1. Cada parágrafo de exame tem que sair igual ao laudo real.
    for nome, (item, esperado) in PARAGRAFOS_REAIS.items():
        _, gerado = texto.paragrafo_do_exame(item)
        igual = gerado == esperado
        print(f"{nome:32} {'idêntico ao laudo real' if igual else 'DIVERGE'}")
        checa(igual, f"{nome}: o parágrafo divergiu do laudo real")

    # 2. Combinação sem redação transcrita vira pendência, nunca preenchida
    #    por semelhança com outro identificador.
    _, pendente = texto.paragrafo_do_exame(
        {"identificador": "Câmbio", "resultado_revelacao": "positivo"}
    )
    checa("[PENDENTE:" in pendente, "identificador sem redação devia virar pendência")

    exame = obter_exame("identificacao_veicular")
    derivados = {"conclusao": "apresenta adulteração intencional no NIV."}
    respostas = {q: "resposta do perito" for q in ("01", "03", "04", "05", "06")}
    respostas["02"] = "__padrão__"
    imagens = [
        {"assinatura": f"i{n}", "nome": f"{n}.png", "dados": PNG, "material": 1,
         "legenda": f"Imagem {n:02d} - Teste."}
        for n in range(1, 5)
    ]
    documento = montador.montar(
        ADMIN, COLECOES, derivados, imagens, QUESITOS, respostas, exame=exame
    )
    corpo = "\n".join(p.text for p in documento.paragraphs)

    # 3. Estrutura própria: sem histórico, sem referências, com apêndice.
    checa("1. DO VEÍCULO" in corpo, "a seção do veículo devia existir")
    checa("2.1. Do Numeração de Identificação Veicular" in corpo, "faltou a subseção do NIV")
    checa("2.3. Da Placa" in corpo, "faltou a subseção da placa")
    checa("HISTÓRICO" not in corpo, "o laudo veicular não tem histórico")
    checa("REFERÊNCIAS" not in corpo, "o laudo veicular não tem referências")
    checa("APÊNDICE FOTOGRÁFICO" in corpo, "as imagens vão em apêndice")
    checa(len(documento.inline_shapes) == 4, "as quatro imagens deviam estar embutidas")
    checa(
        "e um apêndice com 1 página(s)" in corpo,
        "o fecho devia contar o apêndice à parte",
    )
    checa(
        "Vide item 2. EXAMES." in corpo,
        "o padrão de resposta do quesito 2 é do laudo veicular",
    )
    checa(
        not montador.pendencias_do_texto(ADMIN, COLECOES, derivados, QUESITOS, respostas, exame),
        "o laudo de referência não devia ter pendência",
    )

    # 4. Dois peritos: preâmbulo no plural e duas assinaturas.
    admin_dois = {
        **ADMIN,
        "peritos": [
            {"perito_designado": "FLÁVIO FELINTO MOURA", "matricula": "402.340-4"},
            {"perito_designado": "HAMILTON CARVALHO FORTES JÚNIOR", "matricula": "357.724-4"},
        ],
    }
    corpo_dois = "\n".join(
        p.text
        for p in montador.montar(
            admin_dois, COLECOES, derivados, imagens, QUESITOS, respostas, exame=exame
        ).paragraphs
    )
    print("\npreâmbulo com dois peritos:", "os PERITOS CRIMINAIS" in corpo_dois)
    checa(
        "os PERITOS CRIMINAIS FLÁVIO FELINTO MOURA e HAMILTON CARVALHO FORTES JÚNIOR"
        in corpo_dois,
        "com dois signatários o preâmbulo devia ir no plural",
    )
    checa(corpo_dois.count("Matrícula:") == 2, "deviam sair duas assinaturas")

    print("\n" + "=" * 60)
    if falhas:
        print(f"{len(falhas)} FALHA(S):")
        for f in falhas:
            print(" -", f)
        return 1
    print("IDENTIFICAÇÃO VEICULAR OK — bate com os laudos de referência")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
