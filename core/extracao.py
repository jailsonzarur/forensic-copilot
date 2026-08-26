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
{"<colecao>": [{"indice": <n>, "campos": {"<slot>": "<valor>"}}]}

- "indice" é o número do item na coleção, começando em 1. Use um índice existente para completar um item já iniciado; use o próximo índice livre para um item novo, e só quando o perito estiver claramente falando de outro item.
- Inclua em "campos" apenas os slots informados nesta mensagem.
- Se a mensagem não trouxer nenhum dado novo, responda {}.
- Não invente coleções nem slots fora dos listados abaixo."""


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


def _indice_valido(valor: object, quantidade: int) -> int | None:
    """Índice 1..quantidade+1. Um salto maior vira o próximo índice livre."""
    try:
        indice = int(str(valor).strip())
    except (TypeError, ValueError):
        return None
    if indice < 1:
        return None
    return min(indice, quantidade + 1)
