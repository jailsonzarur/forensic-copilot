"""CAMADA 3 — campos derivados da camada 1.

Derivar é recombinar o que o perito disse, com as palavras dele. Nada aqui
passa pelo LLM: conclusão e legenda são montadas por regra, exibidas como
rascunho e **confirmadas ou reescritas pelo perito** antes de virar documento.

A redação definitiva (como o laudo real escreve "POSITIVO para Cannabis sativa
L." em vez de "POSITIVO para maconha") é vocabulário institucional — camada 2,
que só entra transcrita dos laudos reais. Traduzir o termo do perito para o
termo técnico aqui seria inventar.
"""

from __future__ import annotations

from dataclasses import dataclass

from config.schema import Exame
from core import biblioteca
from core import numeros
from templates.identificacao_substancia import boilerplate

CHAVE_CONCLUSAO = "conclusao"
CHAVE_EXAMES = "exames_realizados_texto"
CHAVE_NATUREZA = "natureza"
CHAVE_PROSCRICAO = "proscricao"
CHAVE_PAGINAS = "paginas"
PREFIXO_REDACAO = "redacao_ensaio_"


def chave_redacao(nome_teste: str, substancia: str) -> str:
    """Onde fica a redação da seção 4 deste laudo, por ensaio e substância."""
    return PREFIXO_REDACAO + biblioteca.chave(nome_teste, substancia)
PREFIXO_MATERIAL = "descricao_material_"

#: Marcador que aparece no texto quando falta redação transcrita de laudo real.
#: Some do documento só depois que o perito escreve por cima.
PENDENTE = "[PENDENTE: {o_que}]"


@dataclass(frozen=True)
class Derivado:
    """Um campo da camada 3, com a origem à vista para o perito conferir."""

    chave: str
    label: str
    valor: str
    origem: str
    ajuda: str = ""


def _positivos(colecoes: dict[str, list[dict]]) -> list[str]:
    """Substâncias com resultado positivo, na ordem em que apareceram.

    Dois ensaios podem apontar a mesma substância com nomes diferentes — o laudo
    real conclui "Cannabis sativa L." a partir de um CCD que encontrou THC. A
    deduplicação usa a chave canônica do boilerplate, mas o texto que aparece é
    a palavra do perito: quem traduz para o termo técnico é ele, na confirmação.
    """
    encontradas: list[str] = []
    vistas: set[str] = set()
    for item in colecoes.get("exames_realizados", []):
        if str(item.get("resultado", "")).strip().lower() != "positivo":
            continue
        substancia = str(item.get("substancia", "")).strip()
        if not substancia:
            continue
        chave = boilerplate.chave_substancia(substancia) or boilerplate.normaliza(substancia)
        if chave in vistas:
            continue
        vistas.add(chave)
        encontradas.append(substancia)
    return encontradas


def _testes(colecoes: dict[str, list[dict]]) -> list[str]:
    nomes: list[str] = []
    for item in colecoes.get("exames_realizados", []):
        nome = str(item.get("nome_teste", "")).strip()
        if nome and nome not in nomes:
            nomes.append(nome)
    return nomes


def _lista(itens: list[str]) -> str:
    if len(itens) <= 1:
        return "".join(itens)
    return ", ".join(itens[:-1]) + " e " + itens[-1]


def conclusao(colecoes: dict[str, list[dict]]) -> tuple[str, str]:
    """(texto da conclusão, de onde ele saiu)."""
    positivas = _positivos(colecoes)
    if positivas:
        # O laudo real escreve "POSITIVO para X e POSITIVO para Y", repetindo a
        # palavra em cada substância.
        return (
            " e ".join(f"POSITIVO para {s}" for s in positivas),
            "substâncias dos exames com resultado positivo",
        )

    testes = _testes(colecoes)
    if testes:
        return (
            f"NEGATIVO nos ensaios realizados: {_lista(testes)}.",
            "nenhum exame com resultado positivo",
        )
    return "", "nenhum exame registrado"


def descricao_material(material: dict) -> str:
    """Frase do tópico IDENTIFICAÇÃO E DESCRIÇÃO DO MATERIAL.

    Segue o laudo real: massa com o extenso entre parênteses, forma, coloração e
    o acondicionamento com a contagem grafada em duas casas e por extenso.
    """
    valor = str(material.get("massa_liquida_valor", "")).strip()
    unidade = str(material.get("massa_liquida_unidade", "")).strip()
    extenso = numeros.massa_por_extenso(valor, unidade)

    if not extenso:
        extenso = PENDENTE.format(
            o_que=f"massa por extenso de {valor} {unidade}".strip()
        )
    massa = f"{valor} {unidade} ({extenso})".strip()

    partes = [f"{massa} de substância"] if massa else ["substância"]
    forma = str(material.get("forma_fisica", "")).strip()
    if forma:
        partes[-1] = f"{partes[-1]} {forma}"
    cor = str(material.get("coloracao", "")).strip()
    if cor:
        partes.append(f"de coloração {cor}")

    quantidade = str(material.get("acondicionamento_quantidade", "")).strip()
    tipo = str(material.get("acondicionamento_tipo", "")).strip()
    if quantidade and tipo:
        contagem = numeros.quantidade_por_extenso(quantidade)
        grafada = numeros.com_zero(quantidade)
        rotulo = f"{grafada} ({contagem}) {tipo}" if contagem else f"{grafada} {tipo}"
        partes.append(f"distribuídos em {rotulo}")
    elif tipo:
        partes.append(f"acondicionados em {tipo}")

    observacoes = str(material.get("observacoes", "")).strip()
    frase = ", ".join(partes) + "."
    return f"{frase} {observacoes}" if observacoes else frase


def natureza(colecoes: dict[str, list[dict]]) -> str:
    """Resposta do quesito 01, nomeando o material como o laudo real nomeia."""
    frases: list[str] = []
    vistas: set[str] = set()

    for item in colecoes.get("exames_realizados", []):
        if str(item.get("resultado", "")).strip().lower() != "positivo":
            continue
        substancia = str(item.get("substancia", "")).strip()
        if not substancia:
            continue
        chave = boilerplate.chave_substancia(substancia) or boilerplate.normaliza(substancia)
        if chave in vistas:
            continue
        vistas.add(chave)

        construcao = boilerplate.NATUREZA_POR_SUBSTANCIA.get(chave, "")
        if not construcao:
            aprendido = biblioteca.buscar("natureza", biblioteca.chave(substancia))
            construcao = aprendido["texto"] if aprendido else ""
        forma = _forma_curta(_material_de(colecoes, item.get("item_material", "")))
        if not construcao:
            # A redação da resposta é específica de cada substância; escolher a
            # de outra por semelhança seria inventar a conclusão do laudo.
            frases.append(
                PENDENTE.format(o_que=f"resposta do quesito 01 para {substancia}")
            )
            continue
        frases.append(construcao.format(forma=forma or "periciada"))

    if not frases:
        return PENDENTE.format(o_que="natureza do material")
    return " ".join(frases)


def proscricao(colecoes: dict[str, list[dict]]) -> str:
    """Resposta do quesito 03: texto legal de cada substância encontrada."""
    trechos: list[str] = []
    faltando: list[str] = []
    for substancia in _positivos(colecoes):
        chave = boilerplate.chave_substancia(substancia)
        texto = boilerplate.PROSCRICAO_POR_SUBSTANCIA.get(chave, "")
        if not texto:
            aprendido = biblioteca.buscar("proscricao", biblioteca.chave(substancia))
            texto = aprendido["texto"] if aprendido else ""
        if texto:
            if texto not in trechos:
                trechos.append(texto)
        else:
            faltando.append(substancia)
    for substancia in faltando:
        trechos.append(PENDENTE.format(o_que=f"texto de proscrição de {substancia}"))
    if not trechos:
        return PENDENTE.format(o_que="texto de proscrição")
    return " ".join(trechos)


def resultados_obtidos(
    colecoes: dict[str, list[dict]], derivados: dict | None = None
) -> list[dict[str, str]]:
    """Subseções de RESULTADOS OBTIDOS, uma por exame registrado.

    Ordem das fontes: texto transcrito de laudo real, redação já escrita por
    perito na biblioteca, redação feita para ESTE laudo a partir do relato do
    perito, e só então pendência.
    """
    guardadas = derivados or {}
    secoes: list[dict[str, str]] = []
    for item in colecoes.get("exames_realizados", []):
        nome = str(item.get("nome_teste", "")).strip()
        substancia = str(item.get("substancia", "")).strip()
        chave = (boilerplate.normaliza(nome), boilerplate.chave_substancia(substancia))
        transcrito = boilerplate.RESULTADOS_POR_ENSAIO.get(chave)
        if transcrito:
            secoes.append(dict(transcrito))
            continue
        aprendido = biblioteca.buscar("resultado", biblioteca.chave(nome, substancia))
        if aprendido:
            secoes.append({"titulo": aprendido["titulo"], "texto": aprendido["texto"]})
            continue

        deste_laudo = guardadas.get(chave_redacao(nome, substancia))
        if isinstance(deste_laudo, dict) and deste_laudo.get("texto"):
            secoes.append(
                {"titulo": deste_laudo.get("titulo") or nome, "texto": deste_laudo["texto"]}
            )
            continue

        alvo = f"{nome} para {substancia}" if substancia else nome
        secoes.append(
            {
                "titulo": nome or "Ensaio",
                "texto": PENDENTE.format(o_que=f"descrição técnica do ensaio {alvo}"),
            }
        )
    return secoes


def referencias(colecoes: dict[str, list[dict]]) -> list[str]:
    """Referências que este laudo deve citar.

    Saem da base (``core/referencias.py``), casadas com as substâncias e os
    métodos registrados. Substância que nenhuma referência confirmada cobre
    vira pendência — inclusive quando existe candidata, porque candidata não
    tem ano nem edição conferidos e citação falsa é pior que citação faltando.
    """
    from core import referencias as base

    lista = [r.citacao for r in base.para_o_laudo(colecoes) if r.citacao]
    for substancia in base.substancias_sem_referencia(colecoes):
        lista.append(PENDENTE.format(o_que=f"referência bibliográfica de {substancia}"))
    return lista


def legenda(
    material: dict,
    indice_material: int,
    numero_imagem: int,
    exame: Exame | None = None,
) -> str:
    """Legenda da foto, como o laudo real do TIPO de exame escreve.

    O laudo SB 1252/2019 usa uma legenda única e genérica — "Foto do material
    periciado" — mesmo com dois materiais. O briefing menciona um formato
    descritivo ("Imagem 01: Fotografia dos invólucros...") que deve vir de outro
    dos quatro laudos; enquanto ele não chega, vale o que está transcrito.

    Quando o template do exame sabe montar a sua, ele monta — é o caso do laudo
    de danos, cuja legenda numera a imagem e deixa a descrição para o perito.
    Em qualquer caso o texto é rascunho: o perito reescreve na confirmação.
    """
    from core import templates as texto_fixo

    proprio = getattr(texto_fixo.boilerplate(exame), "legenda", None)
    if proprio is not None:
        return proprio(material, indice_material, numero_imagem)
    return texto_fixo.texto(exame, "LEGENDA_FOTO", boilerplate.LEGENDA_FOTO)


def referencia_imagem(numero_imagem: int) -> str:
    return f"(vide imagem {numero_imagem:02d})"


def _forma_curta(material: dict) -> str:
    """Primeiro segmento da forma física: "vegetal, desidratada, ..." -> "vegetal".

    O laudo real chama de "substância vegetal" e "substância sólida" ao referir
    o material fora do tópico de descrição, onde a forma aparece por inteiro.
    """
    forma = str(material.get("forma_fisica", "")).strip()
    return forma.split(",")[0].strip()


def _material_de(colecoes: dict[str, list[dict]], referencia: str) -> dict:
    materiais = colecoes.get("materiais", [])
    texto = str(referencia).strip()
    if texto.isdigit() and 0 < int(texto) <= len(materiais):
        return materiais[int(texto) - 1]
    return {}


def texto_exames(colecoes: dict[str, list[dict]]) -> str:
    """Seção EXAMES REALIZADOS: quais ensaios, em qual material, para quê.

    Monta a partir do que o perito registrou. Detalhe de método que só ele sabe
    (o laudo real cita "dois eluentes diferentes") entra na edição dele.
    """
    por_material: dict[str, list[dict]] = {}
    for item in colecoes.get("exames_realizados", []):
        por_material.setdefault(str(item.get("item_material", "")).strip(), []).append(item)

    frases: list[str] = []
    for referencia, itens in por_material.items():
        ensaios = [str(i.get("nome_teste", "")).strip() for i in itens]
        ensaios = [e for e in dict.fromkeys(ensaios) if e]

        alvos: list[str] = []
        vistas: set[str] = set()
        for i in itens:
            substancia = str(i.get("substancia", "")).strip()
            if not substancia:
                continue
            chave = boilerplate.chave_substancia(substancia) or boilerplate.normaliza(substancia)
            if chave not in vistas:
                vistas.add(chave)
                alvos.append(substancia)

        forma = _forma_curta(_material_de(colecoes, referencia))
        amostra = f"substância {forma}" if forma else f"material {referencia or '?'}"

        frase = f"Realizaram-se os seguintes exames nas amostras de {amostra}"
        if alvos:
            frase += f" para avaliar a ocorrência de {_lista(alvos)}"
        frase += f": {_lista(ensaios)}." if ensaios else "."
        frases.append(frase)

    return " ".join(frases)


def montar(exame: Exame, colecoes: dict[str, list[dict]]) -> list[Derivado]:
    """Campos derivados que o perito revisa na tela de confirmação."""
    campos: list[Derivado] = []

    # A coleção do objeto examinado é declarada pelo tipo de laudo: material,
    # veículo ou local. Quem sabe descrevê-lo é o template do exame; sem isso
    # vale a descrição do laudo de substância.
    from core import templates as texto_fixo

    objeto = exame.colecao_objeto() if exame is not None else None
    chave_objeto = objeto.chave if objeto is not None else "materiais"
    rotulo_objeto = objeto.label_singular if objeto is not None else "Material"
    proprio = getattr(texto_fixo.boilerplate(exame), "descricao_objeto", None)
    de_substancia = bool(
        texto_fixo.texto(exame, "NATUREZA_POR_SUBSTANCIA", {})
        or texto_fixo.texto(exame, "PROSCRICAO_POR_SUBSTANCIA", {})
    )

    for indice, item in enumerate(colecoes.get(chave_objeto, []), start=1):
        valor = proprio(item, {}) if proprio is not None else descricao_material(item)
        campos.append(
            Derivado(
                chave=f"{PREFIXO_MATERIAL}{indice}",
                label=f"Descrição — {rotulo_objeto} {indice}",
                valor=valor,
                origem=f"campos do {rotulo_objeto} {indice}, no formato do laudo",
                ajuda="Entra no tópico de descrição do objeto examinado.",
            )
        )

    # A narrativa de ensaios só existe onde o laudo tem seção de exames sobre
    # uma coleção vinculada. Num laudo de danos ela sairia vazia e confundiria.
    if colecoes.get("exames_realizados"):
        campos.append(
            Derivado(
                chave=CHAVE_EXAMES,
                label="Exames realizados (texto)",
                valor=texto_exames(colecoes),
                origem="ensaios registrados e o material de cada um",
                ajuda="Detalhe de método que só você sabe deve ser acrescentado aqui.",
            )
        )

    texto, origem = conclusao(colecoes)
    campos.append(
        Derivado(
            chave=CHAVE_CONCLUSAO,
            label="Conclusão",
            valor=texto,
            origem=origem,
            ajuda=(
                "Montada a partir dos resultados que você registrou, com as suas "
                "palavras. A redação técnica do laudo (nome científico, fórmula "
                "consagrada) é sua — edite à vontade."
            ),
        )
    )
    # Natureza e proscrição são do laudo de substância: pedi-las num laudo de
    # danos ou veicular seria campo fantasma, e campo fantasma vazio acaba
    # virando pendência que ninguém sabe resolver.
    if de_substancia:
        campos.append(
            Derivado(
                chave=CHAVE_NATUREZA,
                label="Quesito 01 — natureza do material",
                valor=natureza(colecoes),
                origem="substâncias com resultado positivo",
            )
        )
    campos.append(
        Derivado(
            chave=CHAVE_PAGINAS,
            label="Número de páginas do laudo",
            valor="",
            origem="o editor de texto conta sozinho ao abrir o arquivo",
            ajuda=(
                "Deixe em branco: o fecho sai com um campo que o Word preenche "
                "sozinho, e o número fica sempre certo. Preencha aqui só se o "
                "Instituto exigir a contagem por extenso ('duas páginas')."
            ),
        )
    )
    if de_substancia:
        campos.append(
            Derivado(
                chave=CHAVE_PROSCRICAO,
                label="Quesito 03 — texto de proscrição",
                valor=proscricao(colecoes),
                origem="texto legal transcrito do laudo real, por substância",
                ajuda="Substância sem texto transcrito aparece como PENDENTE.",
            )
        )
    return campos
