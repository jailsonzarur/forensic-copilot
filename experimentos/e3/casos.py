"""Falas simuladas do perito para o E3, uma por laudo de referência.

**Como estas falas foram escritas.** Os fatos vêm do laudo oficial — massa,
numeração, cor, o que foi constatado — porque é ali que eles existem: são o que
o perito mediu, e não constam da requisição. Mas a REDAÇÃO é deliberadamente
coloquial, como o perito fala, nunca copiada do laudo. Onde o documento
oficial escreve "acondicionada em 03 (três) invólucros plásticos", a fala diz
"tá em três invólucros de plástico".

Essa distinção é o que dá sentido ao experimento: se a fala fosse copiada, o
teste mediria a capacidade de repetir texto. Como ela é solta, a ferramenta
precisa PRODUZIR a redação oficial a partir de linguagem falada, que é a
tarefa real.

``admin_extra`` são os campos que a requisição não traz e o perito preenche no
formulário. ``derivados`` são as confirmações da camada 3 que ele faz na tela
de revisão. Ambos são contados no relatório: quanto maior, menos a ferramenta
automatiza.
"""

from __future__ import annotations

CASOS = {
    # ------------------------------------------------------------------
    "veicular-of14744": {
        "exame": "identificacao_veicular",
        "descricao": "motocicleta com NIV, motor e placa adulterados",
        "falas": [
            "É uma motocicleta Honda CG 150 Fan, cor vermelha, placa OEB9641. "
            "Veio com o lacre DPTC 1829159.",
            "Examinei o NIV primeiro. A numeração que tá lá é 9C2KC1670DR452854, "
            "gravada na base do guidão, lado direito. Todos os caracteres "
            "divergiam do padrão de fábrica. Apliquei os reagentes de ferro e "
            "aço e deu negativo, não revelou nada.",
            "Depois o motor. Numeração KC16E7D452854, gravada no bloco. Todos os "
            "caracteres também divergentes. Usei reagente de liga metálica e "
            "dessa vez deu positivo: revelou KC16E8E012818.",
            "Por último a placa. Ela exibe a OEB9641, com lacre do DETRAN-PI "
            "número 000064319-0, e o arame do lacre estava seccionado, o que "
            "mostra que a placa foi violada. Consultei o SINESP e não houve "
            "resultado para essa placa. Então é placa falsa.",
            "Não examinei mais nada nesse veículo.",
        ],
        "respostas_quesitos": {
            "01": "Sim, na numeração de identificação veicular, na numeração do "
                  "motor e na placa (vide Item 2. EXAMES).",
            "02": "__padrão__",
            "03": "Uso de instrumento abrasivo para suprimir os caracteres "
                  "originais do Número de Identificação Veicular e os do Número "
                  "do Motor, seguido de regravação de caracteres divergentes e "
                  "substituição da placa original por placa clonada (vide item "
                  "3. CONCLUSÃO).",
            "04": "Supressão e regravação dos caracteres identificadores do NIV "
                  "e do número de motor, e falsificação de placa.",
            "05": "Através de exames periciais revelaram-se os caracteres "
                  "latentes originais do número do motor: KC16E8E012818, mas não "
                  "foi possível revelar os caracteres latentes originais do NIV.",
            "06": "Em consulta ao Sistema Nacional de Informações de Segurança "
                  "Pública - SINESP, o número do motor: KC16E8E012818 (revelado "
                  "no veículo examinado) está cadastrado para a motocicleta com "
                  "ocorrência de ROUBO/FURTO.",
        },
        "admin_extra": {
            "numero_demanda": "00082450-35",
            "data_realizacao": "2024-07-18",
            "local_exame": "pátio da Central de Flagrantes, Teresina-PI",
            "data_encerramento": "2024-07-25",
            "peritos": [
                {"perito_designado": "FLÁVIO FELINTO MOURA", "matricula": "402.340-4"},
                {"perito_designado": "HAMILTON CARVALHO FORTES JÚNIOR", "matricula": "357.724-4"},
            ],
        },
        "colecoes_extra": {"veiculos": [{"abertura": "Trata-se da"}]},
        "derivados": {
            "conclusao": (
                "apresenta placa falsificada, adulteração intencional na sua "
                "numeração de identificação veicular – NIV – e no número de motor "
                "pela modalidade de SUPRESSÃO E REGRAVAÇÃO DE CARACTERES "
                "IDENTIFICADORES."
            ),
            "paginas": "2",
        },
        # Trechos que o laudo oficial traz e que serão procurados no gerado.
        "fatos_esperados": [
            "9C2KC1670DR452854",
            "KC16E7D452854",
            "KC16E8E012818",
            "OEB9641",
            "base do guidão",
            "ferro e aço",
            "liga metálica",
            "NEGATIVO",
            "POSITIVO",
            "HONDA/CG 150 FAN",
            "FLÁVIO FELINTO MOURA",
            "HAMILTON CARVALHO FORTES JÚNIOR",
        ],
    },

    # ------------------------------------------------------------------
    # INÉDITO — não foi fonte de nenhum template. É o teste de generalização.
    "veicular-00100350-44": {
        "exame": "identificacao_veicular",
        "descricao": "motocicleta com NIV, motor e placa adulterados (laudo inédito)",
        "inedito": True,
        "falas": [
            "É uma motocicleta Honda CG 125 ES, cor preta, placa NIH1905. "
            "Veio com o lacre DPTC 1839545.",
            "Comecei pelo NIV. A numeração é 9C2JC4110AR094988, e o ano de "
            "fabricação gravado é 2010, tudo na base do guidão, lado direito. "
            "Todos os caracteres divergiam do padrão de fábrica. Apliquei "
            "reagente de ferro e aço e deu positivo, mas só revelou um "
            "caractere: ?????????????2???",
            "Depois o motor. Numeração JC41E1A094988, gravada no bloco. Todos "
            "os caracteres divergentes também. Usei reagente de liga metálica, "
            "deu positivo e revelou JC41E1A032959.",
            "Por fim a placa. Ela exibe NIH1905, com QR Code de número de série "
            "200727017890173 indicando estampagem não encontrada. Consultei o "
            "SINESP e a placa está cadastrada para o NIV 9C2JC4110AR094988, que "
            "é justamente o NIV adulterado que eu observei. Então é clone de placa.",
            "Não examinei mais nada.",
        ],
        "respostas_quesitos": {
            "01": "Sim, na numeração de identificação veicular, na numeração do "
                  "motor e na placa (vide item 2. EXAMES).",
            "02": "Vide item 2. EXAMES.",
            "03": "Uso de instrumento abrasivo para suprimir os caracteres "
                  "originais do Número de Identificação Veicular e os do Número "
                  "do Motor, seguido de regravação de caracteres divergentes e "
                  "substituição da placa original por placa clonada (vide item "
                  "3. CONCLUSÃO).",
            "04": "Supressão e regravação de caracteres identificadores do NIV e "
                  "do Número do Motor e clone de placa (vide item 3. CONCLUSÃO).",
        },
        "admin_extra": {
            "numero_demanda": "00100350-44",
            "data_realizacao": "2025-02-01",
            "local_exame": "pátio da POLÍCIA CIVIL DO PIAUÍ - DELEGACIA SECCIONAL DE CAMPO MAIOR-DSPC",
            "data_encerramento": "2025-02-03",
            "peritos": [
                {"perito_designado": "HUNOS PAIXÃO MADUREIRA", "matricula": "354028-6"},
            ],
        },
        "colecoes_extra": {"veiculos": [{"abertura": "Trata-se da"}]},
        "derivados": {
            "conclusao": (
                "apresenta adulteração intencional na sua numeração de "
                "identificação veicular – NIV – e no número de motor pela "
                "modalidade de SUPRESSÃO E REGRAVAÇÃO DE CARACTERES "
                "IDENTIFICADORES."
            ),
            "paginas": "3",
        },
        "fatos_esperados": [
            "9C2JC4110AR094988", "JC41E1A094988", "JC41E1A032959", "NIH1905",
            "base do guidão", "ferro e aço", "liga metálica", "POSITIVO",
            "HONDA/CG 125 ES", "HUNOS PAIXÃO MADUREIRA", "1839545",
        ],
    },
}
