"""Verifica o laudo de Verificação de Danos contra os laudos reais.

Alimenta o montador com os dados das demandas 00016037-31 (cela de presídio
arrombada) e 00016160-22 (ponte ferroviária pichada) e confere se sai o mesmo
texto — inclusive as diferenças de estrutura que este tipo trouxe: a seção
``2. DO OBJETIVO DA PERÍCIA``, as duas subseções fixas de ``3. DOS EXAMES``,
as imagens no corpo e o rodapé de assinatura abreviado.

    .venv/bin/python -m verificacao.danos
"""

from __future__ import annotations

import base64

from config.exams import obter_exame
from core import documento as montador
from templates.identificacao_danos import boilerplate as texto

PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAE"
    "hQGAhKmMIQAAAABJRU5ErkJggg=="
)

# --------------------------------------------------------------------------
# Demanda 00016037-31 — cela de presídio
# --------------------------------------------------------------------------

CELA_LOCAL = {
    "endereco_local": (
        "verificada no Presídio Militar da PMPI, situado à Rua Jarbas Martins, "
        "s/nº, (no Complexo CEP PM-PI, antigo CFAP), Ilhotas, zona sul desta capital"
    ),
    "hora_comunicacao": "17h50min",
    "hora_chegada": "18h10min",
    "recepcao": "",
    "natureza": "interna",
    "idoneidade": "inidônea",
    "motivo_inidoneidade": (
        "o ambiente a ser examinado não fora devidamente preservado para os "
        "procedimentos periciais, tendo ocorrido ALTERAÇÕES antes da estada da "
        "perícia ao local com prejuízos para efeito de exames periciais"
    ),
    "descricao_local": (
        "Trata-se de um estabelecimento prisional, situado em zona urbana, "
        "conforme endereço epigrafado, cravado dentro do Complexo CEP PM-PI, "
        "antigo CFAP, constituído de duas edificações: uma administrativa, "
        "voltada para a via pública e outra no setor posterior a esta onde ficam "
        "as celas, intercaladas por um pátio à céu aberto."
    ),
    "meio_instrumento": (
        "meio de força física direta, além do auxílio de instrumento contundente "
        "com características recente"
    ),
}

CELA_DANOS = [
    "Arrombamento do portão em estrutura de gradis de ferro da cela nº 04, de "
    "modo a destruir parcialmente a parede no entorno onde era afixado o ferrolho "
    "superior (de dois) do sistema de tranca do referido portão (vide ilustrações "
    "fotográficas 01 e ampliação, 02, 03 e 04 abaixo)",
    "Visivelmente destruição de uma lâmpada existente no teto da cela (vide "
    "ilustração 05 abaixo)",
    "Destruição de uma tomada elétrica existente na parede interna próxima ao "
    "portão de acesso à cela (vide imagem fotográfica 04 e 06 abaixo)",
]

CELA_LOCAL_ESPERADO = (
    "O local objeto de exame (“Corpo de Delito”) constitui-se de uma área de "
    "natureza interna e inidônea para efeito de perícia, uma vez que o ambiente "
    "a ser examinado não fora devidamente preservado para os procedimentos "
    "periciais, tendo ocorrido ALTERAÇÕES antes da estada da perícia ao local "
    "com prejuízos para efeito de exames periciais."
)

CELA_ADMIN = {
    "numero_demanda": "00016037-31",
    "data_exame": "2018-05-24",
    "hora_recebimento": "17h50min",
    "orgao_solicitante": "CORREGEDORIA DA POLÍCIA MILITAR DO ESTADO DO PIAUÍ",
    "documento_solicitacao": "do ofício n.º 001/CORREG - APFD",
    "data_documento": "2018-05-24",
    "subscritor": "CAP PM Ferdinand Lira (Presidente do Inquérito)",
    "finalidade": "Exame Pericial para Verificação de Danos",
    "perito_designado": "JEFFERSON RIBEIRO AVELINO",
    "matricula": "009310-6",
    "classe_perito": "Especial",
}

# --------------------------------------------------------------------------
# Demanda 00016160-22 — ponte ferroviária
# --------------------------------------------------------------------------

PONTE_LOCAL = {
    "endereco_local": (
        "situado na Ponte Ferroviária sobre a Av. Pe. Huberto Pietro Grande"
    ),
    "hora_comunicacao": "15h10min",
    "hora_chegada": "15h30min",
    "recepcao": (
        "um Servidor da Prefeitura Municipal desta capital, que prestou ao "
        "perito todas as informações necessárias pertinentes ao fato em questão"
    ),
    "natureza": "externa",
    "idoneidade": "idônea",
    "descricao_local": (
        "Trata-se da ponte ferroviária sobre a Av. Padre Humberto Pietro Grande, "
        "situada à margem sul da Av. Dos Ipês, prolongamento da Av. Cajuína, "
        "bairro São João, com uma extensão aproximada de 40m, de estrutura "
        "metálica em aço sustentadas por bases laterais em concreto (vide imagens "
        "01 e 03 abaixo)."
    ),
    "meio_instrumento": "",
}

PONTE_DANOS = [
    "consistem na pichação de ambas as faces laterais externas da ponte em "
    "questão, ora mencionada, assim como, de igual modo, as bases de sustentação "
    "laterais em concreto."
]

PONTE_LOCAL_ESPERADO = (
    "O local objeto de exame (“Corpo de Delito”) constitui-se de uma área de "
    "natureza externa considerada idônea para efeito de perícia."
)

PONTE_ADMIN = {
    "numero_demanda": "00016160-22",
    "data_exame": "2018-06-01",
    "hora_recebimento": "15h30min",
    "orgao_solicitante": (
        "DELEGACIA ESPECIALIZADA DE PROTEÇÃO AO MEIO AMBIENTE – DPAMB, desta "
        "capital, via Central Única de Flagrantes"
    ),
    "documento_solicitacao": "da requisição n.º 002571/18",
    "data_documento": "2018-06-01",
    "subscritor": "Delegado Bel. Antônio Marques Filho",
    "finalidade": "Exame Pericial em Local para Verificação de Danos",
    "perito_designado": "JEFFERSON RIBEIRO AVELINO",
    "matricula": "009310-6",
    "classe_perito": "Especial",
}


def _colecoes(local: dict, danos: list[str]) -> dict:
    return {
        "locais": [dict(local)],
        "danos": [{"descricao": d, "item_material": "1"} for d in danos],
    }


def main() -> int:
    exame = obter_exame("verificacao_danos")
    falhas: list[str] = []

    def checa(condicao: bool, descricao: str) -> None:
        if not condicao:
            falhas.append(descricao)
            print(f"    ❌ {descricao}")

    # 1. Concordância do preâmbulo sai do artigo que o perito escreveu.
    masc = texto.campos_extras(CELA_ADMIN, _colecoes(CELA_LOCAL, CELA_DANOS), {})
    fem = texto.campos_extras(PONTE_ADMIN, _colecoes(PONTE_LOCAL, PONTE_DANOS), {})
    print(f"'do ofício'     -> {masc['datado']}, {masc['recebido']}, {masc['subscrito']}")
    print(f"'da requisição' -> {fem['datado']}, {fem['recebido']}, {fem['subscrito']}")
    checa(
        (masc["datado"], masc["recebido"]) == ("datado", "recebido"),
        "documento masculino devia levar 'datado'/'recebido'",
    )
    checa(
        (fem["datado"], fem["recebido"]) == ("datada", "recebida"),
        "documento feminino devia levar 'datada'/'recebida'",
    )

    # 2. Subseção 3.1 — Do Local, caractere por caractere.
    for nome, local, esperado in (
        ("cela (inidônea)", CELA_LOCAL, CELA_LOCAL_ESPERADO),
        ("ponte (idônea)", PONTE_LOCAL, PONTE_LOCAL_ESPERADO),
    ):
        gerado = texto.descricao_objeto(local, {}).split("\n")[0]
        igual = gerado == esperado
        print(f"3.1 {nome:18} {'idêntico ao laudo real' if igual else 'DIVERGE'}")
        if not igual:
            print(f"      gerado:   {gerado}")
            print(f"      esperado: {esperado}")
        checa(igual, f"3.1 {nome}: moldura divergiu do laudo real")

    # 3. Subseção 3.2 — vários danos saem numerados; um só sai corrido.
    varios = texto.texto_constatacoes(_colecoes(CELA_LOCAL, CELA_DANOS))
    checa("1. Arrombamento do portão" in varios, "com vários danos, devia numerar")
    checa("3. Destruição de uma tomada" in varios, "devia numerar até o último dano")
    checa(
        "compatíveis com aqueles produzidos por meio de força física direta" in varios,
        "o meio informado pelo perito devia entrar na abertura das constatações",
    )
    um_so = texto.texto_constatacoes(_colecoes(PONTE_LOCAL, PONTE_DANOS))
    checa("1. consistem" not in um_so, "com um dano só, não devia numerar")
    checa(
        "cujos danos, são compatíveis" not in um_so,
        "sem meio informado, a abertura não podia afirmar compatibilidade",
    )

    # 4. Dano sem descrição vira pendência visível, nunca texto inventado.
    vazio = texto.texto_constatacoes({"locais": [{}], "danos": []})
    checa("[PENDENTE:" in vazio, "sem dano descrito, devia sair pendência à vista")
    inidoneo_sem_motivo = texto.descricao_objeto(
        {"natureza": "interna", "idoneidade": "inidônea"}, {}
    )
    checa(
        "[PENDENTE:" in inidoneo_sem_motivo,
        "inidoneidade sem motivo devia sair pendência, nunca motivo presumido",
    )

    # 5. Padrões de resposta: só remissão, nunca achado.
    conhecidas = texto.RESPOSTAS_CONHECIDAS
    checa(
        conhecidas.get("podem os senhores peritos determinarem a extensao do(s) dano(s)?")
        == "Vide tópico 3. DOS EXAMES, item 3.2. Das Constatações (Danos).",
        "a remissão do quesito da extensão devia estar transcrita",
    )
    for achado in ("houve dano(s)?", "houve emprego de substancia inflamavel ou explosiva?"):
        checa(
            achado not in conhecidas,
            f"'{achado}' é achado do caso e não pode ter resposta pronta",
        )

    # 6. Montagem completa dos dois laudos.
    for nome, admin, local, danos, conclusao in (
        (
            "00016037-31",
            CELA_ADMIN,
            CELA_LOCAL,
            CELA_DANOS,
            "visíveis, de localização, modo e proporção como acima mencionados.",
        ),
        (
            "00016160-22",
            PONTE_ADMIN,
            PONTE_LOCAL,
            PONTE_DANOS,
            "por pichação de Patrimônio Público com modos e meios, localização e "
            "proporção como acima mencionado.",
        ),
    ):
        colecoes = _colecoes(local, danos)
        documento = montador.montar(
            admin=admin,
            colecoes=colecoes,
            derivados={"conclusao": conclusao, "paginas": "5"},
            imagens=[{"dados": PNG, "legenda": "IMAGEM 01: Mostrando o portão da cela 04 arrombado (DANIFICADO);", "material": 1}],
            quesitos=list(texto.QUESITOS_DA_REQUISICAO_MODELO),
            respostas_quesitos={},
            exame=exame,
        )
        corpo = "\n".join(p.text for p in documento.paragraphs)
        print(f"\ndemanda {nome}: {len(documento.paragraphs)} parágrafos")

        checa("DEPARTAMENTO DE POLÍCIA TÉCNICO-CIENTÍFICA" in corpo, f"{nome}: cabeçalho")
        checa("(PERÍCIAS EXTERNAS)" in corpo, f"{nome}: subtítulo")
        checa("1. HISTÓRICO" in corpo, f"{nome}: seção de histórico")
        checa("2. DO OBJETIVO DA PERÍCIA" in corpo, f"{nome}: seção de objetivo")
        checa("3. DOS EXAMES" in corpo, f"{nome}: seção de exames")
        checa("3.1. Do Local" in corpo, f"{nome}: subseção do local")
        checa("3.2. Das Constatações (Danos)" in corpo, f"{nome}: subseção das constatações")
        checa("4. CONCLUSÃO" in corpo, f"{nome}: seção de conclusão")
        checa(conclusao in corpo, f"{nome}: complemento da conclusão do perito")
        checa("DANOS MATERIAIS" in corpo, f"{nome}: a conclusão afirma danos materiais")
        checa(admin["subscritor"] in corpo, f"{nome}: quem subscreveu a solicitação")
        checa(local["hora_chegada"] in corpo, f"{nome}: hora de chegada no histórico")
        checa("Especial – Mat.: 009310-6" in corpo, f"{nome}: rodapé abreviado da assinatura")
        checa("PERITO CRIMINAL" in corpo, f"{nome}: cargo")
        checa("cinco (5) página(s)" in corpo, f"{nome}: contagem de páginas do fecho")
        checa("REFERÊNCIAS" not in corpo, f"{nome}: este laudo não tem referências")
        checa(
            len(documento.inline_shapes) == 1,
            f"{nome}: a imagem devia entrar no corpo, não em apêndice",
        )

    # 7. Nenhuma pendência fantasma de outro tipo de laudo.
    pendentes = montador.pendencias_do_texto(
        admin=CELA_ADMIN,
        colecoes=_colecoes(CELA_LOCAL, CELA_DANOS),
        derivados={"conclusao": "visíveis."},
        quesitos=list(texto.QUESITOS_DA_REQUISICAO_MODELO),
        respostas_quesitos={
            "01": "sim", "02": "compatíveis com força física direta",
            "03": "danos materiais", "04": "__padrão__",
            "05": "__padrão__", "06": "__padrão__",
        },
        exame=exame,
    )
    print("\npendências do texto:", pendentes or "(nenhuma)")
    checa(
        not any("proscri" in p or "referência bibliográfica" in p for p in pendentes),
        "laudo de danos não pode cobrar proscrição nem bibliografia de substância",
    )

    print("\n" + "=" * 60)
    if falhas:
        print(f"{len(falhas)} FALHA(S):")
        for f in falhas:
            print(" -", f)
        return 1
    print("DANOS OK — bate com os laudos de referência")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
