"""Agente único da fase de conversa da CAMADA 1.

Uma chamada de LLM por turno, alinhando extração + intenção + recusas + mensagem
ao perito. O modelo dirige a conversa; as paredes de fidelidade validam a saída.

Paredes que não cedem:

- ``aplicar`` — schema, opções fechadas, valor exato, valor de enfeite descartado.
- ``ler_recusas`` — motivo em conjunto fechado, ``aproximado`` exige palavra de
  estimativa na fala, trecho conferido contra a mensagem do perito.
- ``valida_resumo`` — a mensagem ao perito só pode afirmar ter registrado o que
  saiu ``aplicar``: cada afirmação vai também em ``resumo_do_registrado``, que é
  comparado ao conjunto real de alterações. Se não bater, cai no fallback.
- ``pendencias.completo`` (fora deste módulo) — o botão "Avançar" só libera com
  as pendências determinísticas zeradas. O LLM pode dizer "pronto"; a regra
  checa.
"""

from __future__ import annotations

import json
import unicodedata
from dataclasses import dataclass

from config.schema import Colecao, Exame, Slot
from core import quesitos as camada1_quesitos
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
                f"Você disse {self._citacao()}, mas {campo} vai ao laudo como "
                "medição sua — estimativa aqui viraria número medido. Me diga "
                "o valor exato que você aferiu."
            )
        if self.motivo == "ambiguo":
            return (
                f"Você tocou em {campo}, só que {self._citacao()} não me deixa "
                "seguro de qual é o valor — e eu não vou chutar. Pode repetir "
                "de outro jeito?"
            )
        if self.motivo == "fora_do_escopo":
            return (
                f"{self._citacao().capitalize()} não é campo desse laudo, "
                "então deixei passar."
            )
        if self.motivo == "sem_extracao":
            return (
                "Aqui a culpa foi minha — não peguei nada dessa mensagem. Se "
                "tem dado aí, tenta dizer de outro jeito que eu registro."
            )
        if self.motivo == "pergunta":
            return (
                "Entendi isso como pergunta pra mim, não como dado do exame, "
                "então não anotei nada."
            )
        return (
            "Não vi dado do laudo nessa mensagem, então não anotei nada."
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
            # Regras condicionais — sem isso o agente não sabe que gravar
            # identificador=NIV torna numeracao_observada obrigatória, e pula
            # a etapa antes da hora.
            if slot.obrigatorio_se is not None:
                chave_gatilho, valor_gatilho = slot.obrigatorio_se
                if valor_gatilho == "*":
                    partes.append(
                        f'OBRIGATÓRIO sempre que o campo "{chave_gatilho}" '
                        "estiver preenchido nesse item."
                    )
                else:
                    partes.append(
                        f'OBRIGATÓRIO quando "{chave_gatilho}" = "{valor_gatilho}". '
                        "Se este item já tem esse valor, a etapa NÃO está completa "
                        "enquanto este campo não for informado."
                    )
            elif slot.obrigatorio:
                partes.append("Campo OBRIGATÓRIO deste item.")
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


# ==========================================================================
# Agente único da fase de conversa
# ==========================================================================


SISTEMA_AGENTE = """Você é o assistente conversacional de um perito criminal enquanto ele preenche a CAMADA 1 (dados coletados na fala do perito) de um laudo pericial.

UMA chamada por turno. Você lê o SCHEMA (coleções, slots, regras), o ESTADO atual, as PENDÊNCIAS (campos obrigatórios ainda vazios — a ferramenta calcula isso, é o ground truth), o HISTÓRICO recente e a MENSAGEM nova do perito. Produz UM JSON com extração + intenção + recusas + encerramentos + resposta a quesito + mensagem ao perito.

REGRAS ABSOLUTAS DE EXTRAÇÃO
1. Registre SOMENTE o que o perito disse EXPLICITAMENTE. Não infira, estime, arredonde, converta, complete campo faltante. Se ele não informou, OMITA a chave.
2. Não use conhecimento próprio (drogas costumam ser assim, veículos costumam ser assado, etc.). Saber que cocaína é branca NÃO autoriza escrever "branca".
3. Transcreva com as palavras do perito. Não reescreva pra ficar bonito.
4. Não deduza um campo a partir de outro. Massa não implica invólucros; ensaio não implica resultado.
5. Fração e extenso são valores EXATOS. "N gramas e meio" vira "N,5"; "meio quilo" vira "0,5" com unidade "quilo"; "N vírgula M" vira "N,M". Notação, não conversão — a unidade continua a que ele disse.
6. Em campo de valor exato vai SÓ o número, sem unidade — a unidade tem campo próprio.

REGRAS DE VÍNCULO ENTRE COLEÇÕES
Coleções vinculadas (exames pertencem a um material, sinais examinados pertencem a um veículo) precisam do índice da mãe no campo de referência (``item_material``, etc.). Se o histórico deixa claro qual mãe (o perito estava descrevendo o Material 1 e continua com os exames dele), preencha. Se AMBÍGUO, deixe vazio e PERGUNTE — não invente vínculo.

OBRIGATORIEDADE CONDICIONAL
Cada slot no SCHEMA pode ter uma linha "OBRIGATÓRIO quando X = Y" ou "OBRIGATÓRIO sempre que X estiver preenchido". Leia com atenção antes de decidir a próxima pergunta: quando VOCÊ grava um valor que ativa outra obrigatoriedade condicional (por exemplo, gravar identificador="NIV" torna numeracao_observada obrigatória neste item), a etapa NÃO está completa — a lista de PENDÊNCIAS que a ferramenta te mostra é PRÉ-extração dessa mensagem, então SUA extração pode gerar novas pendências que ela ainda não reflete. Só considere a etapa completa depois de olhar todos os obrigatórios (fixos e condicionais) do estado que ficará DEPOIS da sua extração.

RECUSAS — SOMENTE os motivos:
- "aproximado": estimativa em campo de valor exato. Só vale quando a fala TEM palavra de estimativa ("em torno de", "cerca de", "aproximadamente", "uns", "mais ou menos", "por volta de"). Sem isso, não recuse.
- "ambiguo": falou do campo mas o valor não dá pra ler.
- "fora_do_escopo": falou de algo que não é campo deste laudo.
- "pergunta": a mensagem é uma pergunta pra você, não dado.
- "sem_dado": saudação, agradecimento, desabafo, nada aproveitável.

Unidade diferente NÃO é recusa: grave como o perito disse. Forma de número (vírgula, ponto, extenso) NÃO é recusa. Cada recusa tem TRECHO — a citação literal e curta da fala que motivou; se não der pra citar, omita.

INTENÇÃO — SOMENTE uma de:
"conteudo", "encerrar", "mais_um", "confirmar", "responder_quesito", "pergunta", "fora_do_escopo", "sem_dado".

FLUXO DA CONVERSA
1. As ETAPAS estão declaradas no bloco ETAPAS DEFINIDAS. É o roteiro que a ferramenta impõe. Cada turno, fale do que a etapa ATUAL pede.
2. A etapa AVANÇA POR DADOS — a ferramenta calcula a etapa atual a partir do estado: quando os campos obrigatórios de uma etapa já estão preenchidos, ela é considerada completa mesmo sem o perito dizer "não há mais". Se o perito, na etapa 1, trouxer sem querer dados da etapa 2, ANOTE tudo, e no próximo turno o "ETAPA ATUAL" já vai refletir isso — você trata a etapa 2 sem restart. NÃO force o perito a passar por perguntas cujas respostas ele já deu.
3. Encerramento explícito ("não há mais", "só isso", "acabou") é um SINAL útil que você pode registrar em "encerramentos_de_colecao" pra ninguém perguntar "algo mais?" depois — mas NÃO é obrigatório pra avançar. Se você não teve confirmação explícita mas todos os obrigatórios já estão lá, avance sem forçar a pergunta.
4. Na etapa de quesitos, ofereça o padrão do Instituto quando existir (vem no bloco QUESITOS já resolvido com os dados do caso). Se o perito disser "confirmo", grave em "confirmou_padrao_quesito". Se ele digitar sua resposta, grave em "resposta_quesito".
5. Só marque "propoe_completo": true quando NADA houver pendente e todos os quesitos tiverem resposta.

MENSAGEM AO PERITO
1. Tom de colega ao lado. Direto, sem "por gentileza", sem "poderia me informar", sem saudação genérica, sem emoji.
2. Reconheça o que anotou — se não anotou nada, NÃO diga que anotou. Se houve recusa, explique com o motivo e cite o trecho.
3. Se o perito perguntou algo (intencao="pergunta"), EXPLIQUE o campo pendente com base no schema (label, opções, hints). NÃO invente fato fora do schema. Depois de explicar, repita a pergunta.
4. Pergunte o(s) próximo(s) campo(s) pendente(s). Pode juntar até 3. Se o slot tem OPÇÕES FECHADAS, liste TODAS na pergunta. Se tem HINTS (exemplos), cite-os deixando claro que são exemplos.
5. NUNCA sugira uma resposta como se fosse a do perito. "Seria branca?" não. Você só pergunta.
6. Uma a três frases. Sem paredão.

CONSISTÊNCIA ENTRE MENSAGEM E DADOS (crítico)
"resumo_do_registrado" tem que listar EXATAMENTE o que sua mensagem afirma ter anotado — cada entrada aqui está também em "extracao". Se sua mensagem disser "Anotei X" mas X não está em "resumo_do_registrado" (ou em "extracao"), a ferramenta detecta a alucinação e cai num fallback determinístico, e sua mensagem some.

FORMATO DA SAÍDA
Responda APENAS com um objeto JSON:
{
  "extracao": {"<colecao>": [{"indice": <n>, "campos": {"<slot>": "<valor>"}}]},
  "encerramentos_de_colecao": ["<colecao>" ou "<colecao>:<indice_da_mae>"],
  "resposta_quesito": {"numero": "<XX>", "texto": "<resposta livre>"} ou null,
  "confirmou_padrao_quesito": "<XX>" ou null,
  "recusas": [{"motivo": "<motivo>", "colecao": "<colecao>", "slot": "<slot>", "trecho": "<citação>"}],
  "intencao": "<intenção>",
  "propoe_completo": <bool>,
  "resumo_do_registrado": [{"colecao": "<colecao>", "indice": <n>, "slot": "<slot>", "valor": "<valor>"}],
  "mensagem_do_assistente": "<texto pro perito>"
}"""


def _descreve_fechadas(fechadas: list[str]) -> str:
    if not fechadas:
        return "Coleções encerradas: (nenhuma)"
    return "Coleções encerradas: " + ", ".join(fechadas)


def _descreve_pendencias(pendencias_lista: list) -> str:
    if not pendencias_lista:
        return "Pendências (ground truth do que falta): (nenhuma)"
    linhas = ["Pendências (ground truth do que falta):"]
    for p in pendencias_lista:
        linhas.append(f'  - {p.colecao.chave}[{p.indice}].{p.slot.chave} — {p.slot.label}')
    return "\n".join(linhas)


def _descreve_quesitos(
    quesitos: list[str],
    respostas: dict[str, str],
    colecoes: dict[str, list[dict]],
    exame: Exame,
) -> str:
    if not quesitos:
        return "Quesitos da requisição: (nenhum transcrito)"
    linhas = ["Quesitos da requisição:"]
    for q in camada1_quesitos.numerar(quesitos):
        resposta = respostas.get(q.numero, "")
        if resposta == camada1_quesitos.PADRAO_ACEITO:
            status = "RESPONDIDO (padrão do Instituto aceito)"
        elif resposta:
            status = f"RESPONDIDO: «{resposta}»"
        else:
            padrao_resolvido, tem_padrao = camada1_quesitos.responder(
                q.pergunta, colecoes, {}, exame
            )
            if tem_padrao and padrao_resolvido.strip():
                status = f"pendente — padrão do Instituto: «{padrao_resolvido}»"
            else:
                status = "pendente — sem padrão transcrito (o perito escreve)"
        linhas.append(f"  {q.numero}. {q.pergunta}  [{status}]")
    return "\n".join(linhas)


def _descreve_historico(historico: list[dict]) -> str:
    if not historico:
        return "Histórico da conversa: (esta é a primeira mensagem)"
    linhas = ["Histórico da conversa (mais recente por último):"]
    # Últimas 10 mensagens no máximo — suficiente pra contexto sem estufar prompt.
    for m in historico[-10:]:
        papel = m.get("role", "?")
        conteudo = m.get("content", "").strip()
        if conteudo:
            linhas.append(f"[{papel}]: {conteudo}")
    return "\n".join(linhas)


def _descreve_etapas(exame: Exame, etapa_corrente) -> str:
    """Etapas declaradas do laudo + qual é a atual.

    A ferramenta domina o roteiro; o agente executa cada etapa em conversa
    livre. Não pular pra frente enquanto a etapa atual não estiver completa é
    parte do contrato — o prompt reforça essa regra e o controlador calcula a
    etapa determinísticamente a partir do estado.
    """
    if not exame.etapas:
        return "ETAPAS: (não declaradas — siga a ordem das coleções do schema)"
    linhas = ["ETAPAS DEFINIDAS (o roteiro é nosso; você executa em conversa livre):"]
    for i, etapa in enumerate(exame.etapas, start=1):
        marcador = "→ ATUAL" if etapa_corrente is not None and etapa is etapa_corrente else ""
        linhas.append(f"  {i}. {etapa.titulo}: {etapa.objetivo} {marcador}".rstrip())
    linhas.append(
        "REGRA DE ETAPAS: fale do que a etapa ATUAL pede. A etapa avança POR DADOS "
        "— a ferramenta calcula automaticamente qual é a atual a partir do estado, "
        "e nunca te devolve uma etapa cujos campos obrigatórios já estão todos "
        "preenchidos. Se o perito trouxer sem querer dados de outra etapa, ANOTE "
        "tudo; no próximo turno a etapa atual já vai refletir isso. Não force o "
        "perito a passar por perguntas cujas respostas ele já deu."
    )
    return "\n".join(linhas)


def montar_prompt_agente(
    exame: Exame,
    colecoes: dict[str, list[dict]],
    fechadas: list[str],
    respostas_quesitos: dict[str, str],
    quesitos_da_requisicao: list[str],
    historico: list[dict],
    pendencias_lista: list,
    mensagem: str,
    etapa_corrente=None,
) -> str:
    """Prompt completo do turno: schema + estado + histórico + mensagem nova."""
    blocos = [
        f"TIPO DE LAUDO: {exame.label}",
        "",
        _descreve_etapas(exame, etapa_corrente),
        "",
        "SCHEMA — COLEÇÕES E SLOTS:",
        descreve_schema(exame),
        "",
        "ESTADO ATUAL:",
        descreve_estado(exame, colecoes),
        "",
        _descreve_fechadas(fechadas),
        "",
        _descreve_pendencias(pendencias_lista),
        "",
        _descreve_quesitos(quesitos_da_requisicao, respostas_quesitos, colecoes, exame),
        "",
        _descreve_historico(historico),
        "",
        "MENSAGEM NOVA DO PERITO:",
        mensagem.strip(),
    ]
    return "\n".join(blocos)


def orquestrar(
    exame: Exame,
    colecoes: dict[str, list[dict]],
    fechadas: list[str],
    respostas_quesitos: dict[str, str],
    quesitos_da_requisicao: list[str],
    historico: list[dict],
    pendencias_lista: list,
    mensagem: str,
    etapa_corrente=None,
) -> tuple[dict, str]:
    """Chama o agente único. Devolve (JSON parseado, bruto)."""
    return chamar_json(
        SISTEMA_AGENTE,
        montar_prompt_agente(
            exame, colecoes, fechadas, respostas_quesitos,
            quesitos_da_requisicao, historico, pendencias_lista, mensagem,
            etapa_corrente=etapa_corrente,
        ),
    )


def valida_resumo(
    resumo: object, alteracoes: list[Alteracao]
) -> bool:
    """A mensagem do agente só afirma ter registrado o que ``aplicar`` gravou?

    ``resumo`` é o que o LLM declarou ter afirmado na mensagem. Se ele afirma
    ter gravado algo que ``aplicar`` rejeitou — ou omite uma alteração que
    ``aplicar`` de fato gravou — a mensagem está incoerente com o estado e não
    pode ir ao perito.

    A comparação é por (coleção, índice, slot, valor). Empate exato passa;
    qualquer divergência devolve False e o chamador cai no fallback.
    """
    if not isinstance(resumo, list):
        return False
    esperado = {
        (a.colecao.chave, a.indice, a.slot.chave, a.valor) for a in alteracoes
    }
    afirmado: set = set()
    for entrada in resumo:
        if not isinstance(entrada, dict):
            return False
        try:
            afirmado.add((
                str(entrada.get("colecao", "")),
                int(entrada.get("indice", 0)),
                str(entrada.get("slot", "")),
                str(entrada.get("valor", "")),
            ))
        except (TypeError, ValueError):
            return False
    return afirmado == esperado
