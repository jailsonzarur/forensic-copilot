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
- Motivos válidos, e só estes:
  - "aproximado": estimativa ("em torno de 15", "cerca de 10 g", "uns 3") num
    campo que exige valor exato.
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
                "de qual é o valor, e eu não vou adivinhar. Pode dizer de outro jeito?"
            )
        if self.motivo == "fora_do_escopo":
            return (
                f"{self._citacao().capitalize()} não corresponde a nenhum campo "
                "deste laudo, então não registrei nada."
            )
        if self.motivo == "pergunta":
            return (
                "Li isso como uma pergunta, não como um dado do exame, então não "
                "registrei nada."
            )
        return (
            "Essa mensagem não trouxe informação sobre nenhum campo do laudo, "
            "então não registrei nada."
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
            partes = [f'  - "{slot.chave}" ({slot.label})']
            if slot.instrucao_extracao:
                partes.append(slot.instrucao_extracao)
            if slot.exige_valor_exato:
                partes.append(
                    "Exige valor exato (é medição ou contagem do perito). Se a "
                    "fala trouxer aproximação, NÃO registre: informe em "
                    '"nao_registrado" com motivo "aproximado".'
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
                "Se a resposta do perito trouxer um valor solto (só um número, só "
                "uma palavra), esse valor é a resposta dessa pergunta e vai nesse "
                "slot. Isso NÃO autoriza preencher nenhum outro campo: todo slot "
                "que a fala não mencionar continua omitido."
            )
        else:
            contexto.append(
                "A mensagem pode responder a essa pergunta e trazer outros campos. "
                "Se a fala não contiver o dado, omita a chave."
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
) -> list[Alteracao]:
    """Grava no estado o que sobreviveu à validação. Nunca apaga dado."""
    alteracoes: list[Alteracao] = []

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
                if slot is None:
                    continue
                texto = _valor_limpo(valor)
                if not texto:
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


MOTIVOS = ("aproximado", "ambiguo", "fora_do_escopo", "pergunta", "sem_dado")


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
            motivo = "ambiguo" if slot else "sem_dado"

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
