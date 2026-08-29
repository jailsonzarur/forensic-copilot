"""CAMADA 2 — texto fixo do laudo de Identificação Veicular.

Transcrito dos laudos reais das demandas 00078413-75 e 00082450-35, Instituto
de Criminalística / Departamento de Polícia Científica da PC-PI. Nada aqui foi
redigido: é cópia, com os pontos que variam trocados por marcadores.

Diferenças de estrutura em relação ao laudo de substância, todas observadas nos
originais: não há seção de histórico nem de referências; as imagens vão num
APÊNDICE FOTOGRÁFICO ao fim, e o corpo as referencia por número; e o laudo pode
ser assinado por mais de um perito.
"""

from __future__ import annotations

import unicodedata

CABECALHO = (
    "GOVERNO DO ESTADO DO PIAUÍ",
    "SECRETARIA DE SEGURANÇA PÚBLICA",
    "POLÍCIA CIVIL DO ESTADO DO PIAUÍ",
    "INSTITUTO DE CRIMINALÍSTICA",
    "DEPARTAMENTO DE POLÍCIA CIENTÍFICA",
)

TITULO = "LAUDO DE EXAME PERICIAL"
SUBTITULO = "(IDENTIFICAÇÃO VEICULAR)"

PREAMBULO = (
    "Em {data_exame_extenso}, no INSTITUTO DE CRIMINALÍSTICA do DEPARTAMENTO DE "
    "POLÍCIA CIENTÍFICA da POLÍCIA CIVIL DO ESTADO DO PIAUÍ, fora recebida "
    "solicitação do(a) {orgao_solicitante}, formalizada por meio {documento_solicitacao}, "
    "recebida em {data_exame_extenso}, para proceder EXAME PERICIAL PARA "
    "IDENTIFICAÇÃO VEICULAR, referente ao {tipo_procedimento} {numero_procedimento}. "
    "Em conformidade com a legislação e os dispositivos regulamentares vigentes a "
    "referida demanda foi encaminhada para o setor de IDENTIFICAÇÃO VEICULAR, sendo "
    "designado(a) pela direção do órgão pericial {perito_ou_peritos} "
    "{peritos_designados} para seu atendimento, que passa a relatar e descrever com "
    "verdade e com todas as circunstâncias tudo quanto possa interessar."
)

CONCLUSAO = (
    "Face ao exposto, o(s) perito(s) que subscreve(m) o presente laudo o conclui "
    "afirmando que o veículo submetido a exame, acima identificado, {resultados}"
)

ABERTURA_QUESITOS = (
    "Assim, passa o perito a transcrever e a responder os quesitos formulados, da "
    "maneira como segue:"
)

FECHO = (
    "Nada mais havendo a acrescentar, deu-se por findo, em {data_encerramento_extenso}, "
    "o presente laudo de exame pericial que, redigido em {paginas_extenso} página(s) "
    "e um apêndice com {paginas_apendice} página(s), segue assinado pelo seu(s) "
    "relator(es)."
)

ASSINATURA = "DOCUMENTO ASSINADO DIGITALMENTE"
CARGO = "PERITO(A) CRIMINAL"
TITULO_APENDICE = "APÊNDICE FOTOGRÁFICO"

#: Padrão de resposta já transcrito dos laudos reais, por pergunta normalizada.
#: Só o quesito 2 tem resposta invariável; os demais dependem do que foi
#: encontrado, e por isso o perito os responde na conversa.
RESPOSTAS_CONHECIDAS: dict[str, str] = {
    "caso positivo, quais os numeros e ou letras adulteradas?": "Vide item 2. EXAMES.",
}

#: Conjunto que apareceu nas requisições do DRFV nos dois laudos de referência.
QUESITOS_DA_REQUISICAO_MODELO = (
    "Houve adulteração na numeração do chassi, motor, câmbio, placas ou plaquetas?",
    "Caso positivo, quais os números e ou letras adulteradas?",
    "Qual o processo empregado para adulteração?",
    "Qual o tipo de adulteração?",
    "É possível revelar a numeração original?",
    "Outros dados julgados úteis.",
)

# --------------------------------------------------------------------------
# Seção 2 — um parágrafo por sinal identificador examinado
# --------------------------------------------------------------------------

#: Título da subseção, por identificador. Grafia dos laudos reais.
TITULOS_POR_IDENTIFICADOR = {
    "niv": "Do Numeração de Identificação Veicular",
    "motor": "Do Numeração de Identificação do Motor",
    "placa": "Da Placa",
}

#: Redação transcrita, por identificador e por resultado da revelação.
PARAGRAFOS = {
    ("niv", "positivo"): (
        "Observando-se o local de gravação dos sinais identificadores da Numeração "
        "de Identificação Veicular – NIV: {numeracao_observada} ({local_gravacao}), "
        "verificou-se que {caracteres_divergentes} {apresentava} formato, profundidade "
        "e tamanho divergente dos padrões originais de fábrica. {tratamento}"
        "obteve-se resultado POSITIVO quanto à revelação {do_caractere} "
        "do NIV: {numeracao_revelada}."
    ),
    ("niv", "negativo"): (
        "Observando-se o local de gravação dos sinais identificadores da Numeração "
        "de Identificação Veicular – NIV: {numeracao_observada} ({local_gravacao}), "
        "verificou-se que {caracteres_divergentes} {apresentava} formato, profundidade "
        "e tamanho divergente dos padrões originais de fábrica. {tratamento}"
        "obteve-se resultado NEGATIVO quanto à revelação dos caracteres latentes "
        "originais do NIV."
    ),
    ("motor", "positivo"): (
        "Examinando-se a numeração do motor: {numeracao_observada} "
        "({local_gravacao}), verificou-se que {caracteres_divergentes} {apresentava} "
        "formato, profundidade e tamanho divergente dos padrões originais de "
        "fábrica. {tratamento}obteve-se resultado POSITIVO quanto à revelação "
        "{do_caractere} do número de motor: {numeracao_revelada}."
    ),
    ("motor", "negativo"): (
        "Examinando-se a numeração do motor: {numeracao_observada} "
        "({local_gravacao}), verificou-se que {caracteres_divergentes} {apresentava} "
        "formato, profundidade e tamanho divergente dos padrões originais de "
        "fábrica. {tratamento}obteve-se resultado NEGATIVO quanto à revelação dos "
        "caracteres latentes originais do número do motor."
    ),
}

#: Frase do tratamento aplicado antes da observação óptica, transcrita.
TRATAMENTOS = {
    "reagentes em liga metálica": (
        "Realizando-se a aplicação dos reagentes químicos específicos para revelação "
        "de gravação latente em liga metálica, e observação com o auxílio de "
        "instrumentos ópticos apropriados, "
    ),
    "reagentes em ferro e aço": (
        "Realizando-se a aplicação dos reagentes químicos específicos para revelação "
        "de gravação latente em ferro e aço, e observação com o auxílio de "
        "instrumentos ópticos apropriados, "
    ),
    "somente observação óptica": (
        "Realizando-se a observação com o auxílio de instrumentos ópticos "
        "apropriados, "
    ),
}

PENDENTE = "[PENDENTE: {o_que}]"


def normaliza(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", str(texto))
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    return " ".join(sem_acento.lower().split())


def chave_substancia(substancia: str) -> str:
    """Este laudo não trata de substâncias; existe para a interface comum."""
    return ""


def paragrafo_do_exame(item: dict) -> tuple[str, str]:
    """(título da subseção, parágrafo) de um sinal identificador examinado.

    A redação é transcrita; o que varia são os valores que o perito informou.
    Combinação sem texto transcrito vira pendência visível, nunca preenchida
    por semelhança com outro identificador.
    """
    identificador = normaliza(item.get("identificador", ""))
    resultado = normaliza(item.get("resultado_revelacao", ""))
    titulo = TITULOS_POR_IDENTIFICADOR.get(identificador, item.get("identificador", ""))

    if identificador == "placa":
        descricao = str(item.get("descricao_placa", "")).strip()
        return titulo, descricao or PENDENTE.format(o_que="descrição do exame da placa")

    modelo = PARAGRAFOS.get((identificador, resultado))
    if modelo is None:
        return titulo, PENDENTE.format(
            o_que=f"redação do exame de {item.get('identificador', '?')} "
            f"com resultado {item.get('resultado_revelacao', '?')}"
        )

    tratamentos = {normaliza(k): v for k, v in TRATAMENTOS.items()}
    tratamento = tratamentos.get(normaliza(item.get("tratamento", "")), "")
    divergentes = str(item.get("caracteres_divergentes", "")).strip()
    unico = "caractere" in normaliza(divergentes) and "todos" not in normaliza(divergentes)
    # Concordância: "o 17º caractere apresentava ... do caractere latente
    # original" contra "todos os caracteres apresentavam ... dos caracteres
    # latentes originais". Os dois aparecem nos laudos de referência.
    return titulo, modelo.format(
        numeracao_observada=item.get("numeracao_observada", ""),
        local_gravacao=item.get("local_gravacao", ""),
        caracteres_divergentes=divergentes,
        apresentava="apresentava" if unico else "apresentavam",
        tratamento=tratamento,
        do_caractere=(
            "do caractere latente original" if unico else "dos caracteres latentes originais"
        ),
        numeracao_revelada=item.get("numeracao_revelada", ""),
    )


def blocos_pendentes() -> list[str]:
    return []


def descricao_objeto(item: dict, admin: dict) -> str:
    """Seção 1 — DO VEÍCULO, na redação dos laudos reais.

    Os dois laudos abrem diferente ("Foi apresentada a" / "Trata-se da"); o
    perito escolhe, e a escolha é dele porque é redação, não achado.
    """
    abertura = str(item.get("abertura", "")).strip() or "Trata-se da"
    partes = [
        p
        for p in (
            str(item.get("tipo_veiculo", "")).strip(),
            str(item.get("marca_modelo", "")).strip(),
        )
        if p
    ]
    frase = f"{abertura} {' '.join(partes)}" if partes else abertura

    cor = str(item.get("cor", "")).strip()
    if cor:
        frase += f", cor {cor}"

    placa = str(item.get("placa", "")).strip()
    frase += f", placa {placa}" if placa else ", sem placa"
    frase += "."

    lacres = str(item.get("lacres", "")).strip()
    if lacres:
        frase += f" {lacres}."

    data = str(admin.get("data_realizacao", "")).strip()
    local = str(admin.get("local_exame", "")).strip()
    if data or local:
        from core import numeros

        quando = numeros.data_dmy(data) if data else ""
        onde = f" no {local}" if local else ""
        frase += f" Exame realizado{f' em {quando}' if quando else ''}{onde}."

    return frase
