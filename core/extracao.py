"""Extração dos slots da CAMADA 1 a partir da fala do perito.

O modelo aqui tem UM trabalho: transcrever para JSON o que o perito disse.
Ele não redige, não interpreta e não completa. Tudo que ele devolver passa
por ``aplicar``, que descarta chave desconhecida, valor vazio, valor de
enfeite ("não informado") e valor fora do conjunto fechado de um slot.
"""

from __future__ import annotations

import json
import unicodedata
from dataclasses import dataclass

from config.schema import Colecao, Exame, Slot
from core.llm import chamar_json

#: Respostas que o modelo às vezes inventa para "não sei" — nunca viram dado.
_NAO_VALORES = {
    "",
    "-",
    "--",
    "n/a",
    "na",
    "null",
    "none",
    "nulo",
    "nao informado",
    "nao informada",
    "nao declarado",
    "nao especificado",
    "desconhecido",
    "desconhecida",
    "indeterminado",
    "a definir",
    "pendente",
    "?",
}

SISTEMA = """Você extrai dados estruturados da fala de um perito criminal para uma minuta de laudo pericial.

REGRAS ABSOLUTAS
1. Registre SOMENTE o que o perito disse explicitamente. A fala dele é a única fonte.
2. Nunca infira, estime, arredonde, converta unidade nem complete campo faltante.
3. Se o perito não informou um campo, OMITA a chave. Campo omitido vira pergunta ao perito; campo inventado corrompe um documento oficial.
4. Não use conhecimento próprio sobre drogas, embalagens, cores ou exames para preencher nada. Saber que cocaína costuma ser branca não autoriza escrever "branca".
5. Transcreva o valor com as palavras do perito, sem reescrever nem melhorar a redação.
6. Não deduza um campo a partir de outro. Massa não implica quantidade de invólucros; nome do exame não implica resultado.
7. O perito fala como se fala, não como se digita. Número dito por extenso ou em
   fração é valor EXATO, não estimativa: escreva-o em algarismos. "N gramas e
   meio" vira o valor "N,5"; "meio quilo" vira o valor "0,5" com a unidade
   "quilo"; "N vírgula M" vira "N,M". Isso é notação, não conversão: a unidade
   continua sendo exatamente a que ele disse.
8. Em campo de valor exato entra SÓ o número, sem a unidade junto — a unidade
   tem campo próprio.

FORMATO DA SAÍDA
Responda APENAS com um objeto JSON no formato:
{"<colecao>": [{"indice": <n>, "campos": {"<slot>": "<valor>"}}],
 "nao_registrado": [{"colecao": "<colecao>", "slot": "<slot>", "motivo": "<motivo>"}]}

- "indice" é o número do item na coleção, começando em 1. Use um índice existente para completar um item já iniciado; use o próximo índice livre para um item novo, e só quando o perito estiver claramente falando de outro item.
- Inclua em "campos" apenas os slots informados nesta mensagem.
- Se a mensagem não trouxer nenhum dado novo, responda {}.
- Não invente coleções nem slots fora dos listados abaixo.
- "nao_registrado" explica TUDO que o perito falou e não foi gravado. Se você não
  gravar nenhum campo, "nao_registrado" é OBRIGATÓRIO: o perito precisa saber por
  que a pergunta voltou. Isso vale para qualquer mensagem — saudação, agradecimento,
  desabafo, pergunta, assunto alheio ao laudo. Responder {} sem explicação é erro:
  o perito fica sem saber o que aconteceu e repete a mesma frase.
- Cada entrada tem "motivo" e, quando houver, "trecho": a citação EXATA e curta
  das palavras do perito que causaram a recusa, copiada da mensagem sem alterar
  uma letra. Se não der para citar, omita "trecho".
- "colecao" e "slot" identificam o campo afetado; omita ambos quando a recusa não
  for sobre um campo específico.
- "nao_registrado" NÃO é a lista dos campos que ainda faltam. Só entra campo sobre
  o qual o perito falou NESTA mensagem e cujo valor não pôde ser gravado. Campo que
  ele não mencionou simplesmente não aparece — a próxima pergunta já cobre isso.
- Se você gravou algum campo, "sem_dado" está errado: a mensagem trouxe dado.
- Uma entrada por problema, sem repetir o mesmo motivo para o mesmo campo.
- ANTES de recusar, verifique se a fala contém o valor. Se contém, GRAVE. Recusar
  é exceção, não o caminho fácil. Em particular:
  - unidade diferente da que você esperava não é motivo de recusa: grave o valor e
    a unidade exatamente como o perito disse, sem converter;
  - forma de escrever o número (vírgula, ponto, por extenso) não é motivo de recusa.
- Não invente motivo: use um dos listados. Motivo fora da lista é descartado e o
  perito fica sem explicação nenhuma.
- Motivos válidos, e só estes:
  - "aproximado": o perito usou palavra de estimativa — "em torno de", "cerca de",
    "aproximadamente", "uns", "mais ou menos", "por volta de" — num campo que exige
    valor exato. Sem uma dessas palavras NÃO é aproximado: "1,2 kg" e "1,2 quilos"
    são valores exatos.
  - "ambiguo": o perito falou do campo mas não dá para saber qual é o valor.
  - "fora_do_escopo": o perito falou de algo que não é campo deste laudo.
  - "pergunta": a mensagem é uma pergunta ao assistente, não um dado.
  - "sem_dado": a mensagem não traz informação sobre nenhum campo.
- Omitir a chave e listar em "nao_registrado" são coisas diferentes: omita quando
  o perito não falou do campo; liste quando falou e o valor não serve."""


@dataclass(frozen=True)
class Recusa:
    """Algo que o perito falou e não foi gravado, com o motivo.

    Nunca vira mensagem genérica: o texto sai de um motivo fechado, e o trecho
    citado é conferido contra a fala do perito antes de ser exibido.
    """

    motivo: str
    colecao: Colecao | None = None
    slot: Slot | None = None
    trecho: str = ""

    @property
    def chave(self) -> str:
        return self.slot.chave if self.slot else self.motivo

    def _citacao(self) -> str:
        return f"«{self.trecho}»" if self.trecho else "o que você escreveu"

    def explicacao(self) -> str:
        campo = self.slot.label.lower() if self.slot else "esse ponto"

        if self.motivo == "aproximado":
            return (
                f"Você disse {self._citacao()}. {campo.capitalize()} vai ao laudo "
                "como medição sua, então não registro estimativa — me diga o valor "
                "exato."
            )
        if self.motivo == "ambiguo":
            return (
                f"Você falou de {campo}, mas {self._citacao()} não me deixa seguro "
                "de qual é o valor, e eu não vou adivinhar. Pode repetir de outro jeito?"
            )
        if self.motivo == "fora_do_escopo":
            return (
                f"{self._citacao().capitalize()} não corresponde a nada que este "
                "laudo registre, então não anotei nada."
            )
        if self.motivo == "sem_extracao":
            return (
                "Não consegui aproveitar nada dessa mensagem. Se você informou algum "
                "dado aí, quem não entendeu fui eu, não você — tente dizer de outro "
                "jeito, com outras palavras."
            )
        if self.motivo == "pergunta":
            return (
                "Entendi isso como uma pergunta, não como um dado do exame, então "
                "não anotei nada."
            )
        return (
            "Não vi nessa mensagem nenhuma informação que entre no laudo, então "
            "não anotei nada."
        )


@dataclass(frozen=True)
class Alteracao:
    """Um campo que passou a existir (ou mudou) no estado da camada 1."""

    colecao: Colecao
    indice: int
    slot: Slot
    valor: str
    anterior: str | None = None

    def descricao(self) -> str:
        rotulo = f"{self.colecao.label_singular} {self.indice}"
        return f"{rotulo} — {self.slot.label}: {self.valor}"


def _normaliza(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto)
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    return sem_acento.strip().lower()


def _valor_limpo(valor: object) -> str:
    """Texto aproveitável, ou string vazia se o valor não for dado de verdade."""
    if valor is None or isinstance(valor, (dict, list, bool)):
        return ""
    texto = str(valor).strip()
    if _normaliza(texto).strip(".") in _NAO_VALORES:
        return ""
    return texto


def _numero(texto: str) -> float | None:
    """Valor numérico de um campo de medição, ou None se não for número.

    Aceita as duas notações que aparecem na prática — "1,2" e "1.2" — porque o
    valor gravado é o do perito e não se reescreve aqui. Quando os dois
    separadores aparecem, o último é o decimal ("1.234,5").
    """
    limpo = str(texto).strip().replace(" ", "")
    if not limpo:
        return None
    if "," in limpo and "." in limpo:
        if limpo.rfind(",") > limpo.rfind("."):
            limpo = limpo.replace(".", "").replace(",", ".")
        else:
            limpo = limpo.replace(",", "")
    else:
        limpo = limpo.replace(",", ".")
    try:
        return float(limpo)
    except ValueError:
        return None


def _canonico(texto: str, opcoes: tuple[str, ...]) -> str | None:
    alvo = _normaliza(texto).strip(".")
    for opcao in opcoes:
        if _normaliza(opcao) == alvo:
            return opcao
    return None


def descreve_schema(exame: Exame) -> str:
    linhas: list[str] = []
    for colecao in exame.colecoes:
        linhas.append(f'Coleção "{colecao.chave}" ({colecao.label_plural}):')
        for slot in colecao.slots:
            if not slot.na_conversa:
                continue  # preenchido só na confirmação
            partes = [f'  - "{slot.chave}" ({slot.label})']
            if slot.instrucao_extracao:
                partes.append(slot.instrucao_extracao)
            if slot.exige_valor_exato:
                partes.append(
                    "Só o número, em algarismos, sem unidade e sem texto em volta. "
                    "É medição ou contagem do perito: se a fala trouxer estimativa "
                    '("em torno de", "cerca de"), NÃO registre — informe em '
                    '"nao_registrado" com motivo "aproximado". Número dito por '
                    "extenso não é estimativa: transcreva em algarismos."
                )
            if slot.opcoes_fechadas:
                aceitos = ", ".join(f'"{o}"' for o in slot.opcoes)
                partes.append(f"Somente um destes valores: {aceitos}.")
            elif slot.opcoes:
                sugestoes = ", ".join(slot.opcoes)
                partes.append(
                    "Nomes que costumam aparecer (o perito pode usar outro; "
                    f"vale o que ele disse): {sugestoes}."
                )
            linhas.append(" ".join(partes))
    return "\n".join(linhas)


def descreve_estado(exame: Exame, colecoes: dict[str, list[dict]]) -> str:
    linhas: list[str] = []
    for colecao in exame.colecoes:
        itens = colecoes.get(colecao.chave, [])
        linhas.append(f'Coleção "{colecao.chave}":')
        if not itens:
            linhas.append("  (nenhum item registrado)")
        for i, item in enumerate(itens, start=1):
            linhas.append(f"  índice {i}: {json.dumps(item, ensure_ascii=False)}")
        linhas.append(f"  próximo índice livre: {len(itens) + 1}")
    return "\n".join(linhas)


def montar_prompt(
    exame: Exame,
    colecoes: dict[str, list[dict]],
    mensagem: str,
    pergunta_pendente: str = "",
    alvo: str = "",
) -> str:
    blocos = [
        f"TIPO DE LAUDO: {exame.label}",
        "",
        "COLEÇÕES E SLOTS DISPONÍVEIS:",
        descreve_schema(exame),
        "",
        "ESTADO JÁ REGISTRADO:",
        descreve_estado(exame, colecoes),
    ]
    if pergunta_pendente:
        contexto = [
            "",
            "PERGUNTA QUE O ASSISTENTE ACABOU DE FAZER AO PERITO:",
            pergunta_pendente,
        ]
        if alvo:
            contexto.append(f"Essa pergunta se refere a: {alvo}.")
            contexto.append(
                "Se a resposta trouxer um valor solto (só um número, só uma "
                "palavra), ele pertence ao slot perguntado. Mas a fala quase nunca "
                "responde só isso: o perito descreve várias coisas de uma vez. "
                "GRAVE TODOS os campos que ele mencionar, não apenas o perguntado. "
                "O que ele não mencionar continua omitido."
            )
        else:
            contexto.append(
                "A mensagem pode responder a essa pergunta e trazer outros campos "
                "junto. Grave todos os que ela mencionar; o que não mencionar, omita."
            )
        blocos += contexto
    blocos += ["", "MENSAGEM DO PERITO:", mensagem.strip()]
    return "\n".join(blocos)


def extrair(
    exame: Exame,
    colecoes: dict[str, list[dict]],
    mensagem: str,
    pergunta_pendente: str = "",
    alvo: str = "",
) -> tuple[dict, str]:
    """Chama o modelo e devolve (operações cruas, resposta bruta)."""
    return chamar_json(
        SISTEMA, montar_prompt(exame, colecoes, mensagem, pergunta_pendente, alvo)
    )


def aplicar(
    exame: Exame,
    colecoes: dict[str, list[dict]],
    operacoes: dict,
    recusas_locais: list[Recusa] | None = None,
) -> list[Alteracao]:
    """Grava no estado o que sobreviveu à validação. Nunca apaga dado.

    ``recusas_locais`` recebe as recusas que a própria validação produziu, para
    que o perito saiba por que um valor não entrou.
    """
    alteracoes: list[Alteracao] = []
    if recusas_locais is None:
        recusas_locais = []

    for colecao in exame.colecoes:
        entradas = operacoes.get(colecao.chave)
        if not isinstance(entradas, list):
            continue

        itens = colecoes.setdefault(colecao.chave, [])
        for entrada in entradas:
            if not isinstance(entrada, dict):
                continue
            campos = entrada.get("campos")
            if not isinstance(campos, dict):
                continue

            indice = _indice_valido(entrada.get("indice"), len(itens))
            if indice is None:
                continue
            while len(itens) < indice:
                itens.append({})
            item = itens[indice - 1]

            for chave, valor in campos.items():
                slot = colecao.slot(str(chave))
                if slot is None or not slot.na_conversa:
                    # Slot fora da conversa só é preenchido pelo perito na
                    # confirmação. O extrator o deduziria, e dedução não é
                    # transcrição.
                    continue
                texto = _valor_limpo(valor)
                if not texto:
                    continue
                if slot.exige_valor_exato and _numero(texto) is None:
                    # "dezessete gramas e meio" inteiro dentro do campo numérico
                    # iria para o laudo como se fosse um número medido.
                    recusas_locais.append(Recusa("ambiguo", colecao, slot, texto))
                    continue
                if slot.opcoes_fechadas:
                    canonico = _canonico(texto, slot.opcoes)
                    if canonico is None:
                        continue
                    texto = canonico
                anterior = item.get(slot.chave)
                if anterior == texto:
                    continue
                item[slot.chave] = texto
                alteracoes.append(Alteracao(colecao, indice, slot, texto, anterior))

    return alteracoes


#: Motivos que o extrator pode declarar.
MOTIVOS = ("aproximado", "ambiguo", "fora_do_escopo", "pergunta", "sem_dado")

#: Usado só pelo código, quando o extrator não gravou nada e não explicou (ou
#: explicou com um motivo que não resistiu à conferência). Não é oferecido ao
#: modelo: ele nunca deve alegar falha da própria ferramenta.
SEM_EXTRACAO = "sem_extracao"

#: Palavras que caracterizam estimativa. Sem uma delas, uma recusa "aproximado"
#: é erro do extrator e não chega ao perito.
_ESTIMATIVAS = (
    "em torno de", "cerca de", "aproximadamente", "aproximado", "mais ou menos",
    "por volta de", "uns ", "umas ", "estimad", "chute", "acho que",
)

#: Motivos que falam da mensagem inteira, não de um campo. No máximo um deles
#: aparece por vez, e sem slot associado.
MOTIVOS_DE_MENSAGEM = ("sem_dado", "pergunta", "fora_do_escopo", SEM_EXTRACAO)


def consolida_recusas(recusas: list[Recusa], houve_registro: bool) -> list[Recusa]:
    """Uma explicação por problema, e nenhuma que contradiga o que foi gravado.

    O extrator às vezes devolve uma entrada por slot vazio, o que viraria uma
    parede de mensagens idênticas. E "não registrei nada" logo depois de um
    "Registrei:" seria mentira — some.
    """
    vistos: set = set()
    por_campo: list[Recusa] = []
    da_mensagem: list[Recusa] = []

    for recusa in recusas:
        if recusa.motivo in MOTIVOS_DE_MENSAGEM:
            if recusa.motivo == "sem_dado" and houve_registro:
                continue
            if recusa.motivo in vistos:
                continue
            vistos.add(recusa.motivo)
            da_mensagem.append(Recusa(recusa.motivo, trecho=recusa.trecho))
            continue

        chave = (recusa.motivo, recusa.slot.chave if recusa.slot else "")
        if chave in vistos:
            continue
        vistos.add(chave)
        por_campo.append(recusa)

    return por_campo + da_mensagem[:1]


def ler_recusas(exame: Exame, operacoes: dict, mensagem: str = "") -> list[Recusa]:
    """Recusas declaradas pelo extrator, validadas contra o schema e a fala.

    Um trecho que não aparece na mensagem do perito é descartado: citação
    inventada seria pior do que citação nenhuma.
    """
    encontradas: list[Recusa] = []
    entradas = operacoes.get("nao_registrado")
    if not isinstance(entradas, list):
        return encontradas

    referencia = _normaliza(mensagem)
    for entrada in entradas:
        if not isinstance(entrada, dict):
            continue

        colecao = exame.colecao(str(entrada.get("colecao", "")))
        slot = colecao.slot(str(entrada.get("slot", ""))) if colecao else None
        if slot is None:
            colecao = None

        motivo = str(entrada.get("motivo", "")).strip().lower()
        if motivo not in MOTIVOS:
            # Renomear para um motivo plausível transformaria erro do extrator em
            # explicação confiante e falsa. Descarta.
            continue

        if motivo == "aproximado" and not any(p in referencia for p in _ESTIMATIVAS):
            # O extrator alegou estimativa sem que o perito tenha estimado.
            continue

        trecho = str(entrada.get("trecho", "")).strip().strip('"«»')
        if trecho and _normaliza(trecho) not in referencia:
            trecho = ""

        encontradas.append(Recusa(motivo, colecao, slot, trecho))
    return encontradas


def _indice_valido(valor: object, quantidade: int) -> int | None:
    """Índice 1..quantidade+1. Um salto maior vira o próximo índice livre."""
    try:
        indice = int(str(valor).strip())
    except (TypeError, ValueError):
        return None
    if indice < 1:
        return None
    return min(indice, quantidade + 1)
