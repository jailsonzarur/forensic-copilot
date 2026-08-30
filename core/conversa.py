"""Controle fino da conversa — chamada única ao agente, com paredes de validação.

O agente vive em ``core/extracao.py`` e é quem dirige a conversa: extrai,
recusa, encerra coleção, responde quesito e escreve a mensagem ao perito. Este
módulo é a costura fina em cima disso:

- roda o agente (via callable, para poder ser substituído em teste),
- passa a extração pela parede ``aplicar``,
- passa as recusas pela parede ``ler_recusas``,
- aplica os encerramentos de coleção e a resposta a quesito,
- valida que a mensagem do agente afirma só o que ``aplicar`` gravou,
- devolve um Resultado com a mensagem final a exibir.

Se a validação falhar (agente alucinou ter gravado algo), a mensagem cai num
fallback determinístico composto a partir das ``alteracoes`` reais — nunca
chega ao perito uma frase que afirme registro que não aconteceu.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from config.schema import Exame
from core import quesitos as camada1_quesitos
from core.extracao import (
    Alteracao,
    Recusa,
    aplicar,
    consolida_recusas,
    ler_recusas,
    orquestrar,
    valida_resumo,
)
from core.llm import ErroLLM


@dataclass
class Resultado:
    """Efeito de uma mensagem do perito."""

    mensagem: str = ""
    alteracoes: list[Alteracao] = field(default_factory=list)
    recusas: list[Recusa] = field(default_factory=list)
    erro: str = ""
    bruto: str = ""
    chamou_modelo: bool = False
    quesito_respondido: str = ""
    #: True quando o agente sinalizou que a camada 1 está pronta. A regra
    #: ``pendencias.completo`` continua sendo o gate real do botão "Avançar".
    propoe_completo: bool = False


def _texto_alteracoes(alteracoes: list[Alteracao]) -> str:
    """Confirmação segura por construção — o texto sai da lista de alterações.

    Só é usada quando o agente falha na validação de consistência: um fallback
    seco pra o perito ver o que de fato foi gravado, sem risco de invenção.
    """
    if not alteracoes:
        return ""
    grupos: dict[tuple[str, int], list[Alteracao]] = {}
    ordem: list[tuple[str, int]] = []
    for alt in alteracoes:
        chave = (alt.colecao.chave, alt.indice)
        if chave not in grupos:
            ordem.append(chave)
            grupos[chave] = []
        grupos[chave].append(alt)

    partes: list[str] = []
    for chave in ordem:
        do_item = grupos[chave]
        rotulo = f"{do_item[0].colecao.label_singular} {do_item[0].indice}"
        pares = "; ".join(f"{a.slot.label.lower()}: {a.valor}" for a in do_item)
        partes.append(f"{rotulo} — {pares}")
    texto = "Anotei: " + ". ".join(partes)
    return texto if texto.endswith(".") else texto + "."


def _mensagem_fallback(
    alteracoes: list[Alteracao], recusas: list[Recusa]
) -> str:
    """Mensagem determinística quando a do agente não passou na validação."""
    partes: list[str] = []
    if alteracoes:
        partes.append(_texto_alteracoes(alteracoes))
    for recusa in recusas:
        partes.append(recusa.explicacao())
    if not partes:
        partes.append("Registrado. Continue.")
    return "\n\n".join(partes)


def _mensagem_pos_forca(
    exame: Exame,
    colecoes: dict[str, list[dict]],
    quesitos: list[str],
    respostas: dict[str, str],
    quesito_respondido: str,
) -> str:
    """Mensagem depois de forçar uma resposta de quesito que o LLM não gravou.

    O texto do LLM provavelmente afirmava "não registrei" — mentira, agora. Aqui
    a gente compõe deterministicamente: confirmação + próximo quesito com padrão
    resolvido, se houver.
    """
    partes = [f"Quesito {quesito_respondido} respondido."]
    pendentes = camada1_quesitos.pendentes(quesitos, respostas)
    if not pendentes:
        partes.append(
            "Todos os quesitos respondidos. Revise o painel ao lado e siga pra "
            "confirmação."
        )
        return "\n\n".join(partes)
    prox = pendentes[0]
    texto = f"Quesito {prox.numero}: {prox.pergunta}"
    modelo_resolvido, tem_padrao = camada1_quesitos.responder(
        prox.pergunta, colecoes, {}, exame
    )
    if tem_padrao and modelo_resolvido.strip():
        texto += (
            f"\n\nO Instituto costuma responder assim: «{modelo_resolvido}». "
            "Se serve pro caso, escreva «confirmo». Se não, escreva a sua."
        )
    partes.append(texto)
    return "\n\n".join(partes)


def processar(
    exame: Exame,
    colecoes: dict[str, list[dict]],
    fechadas: list[str],
    mensagem: str,
    orquestrador: Callable = orquestrar,
    historico: list[dict] | None = None,
    quesitos: list[str] | None = None,
    respostas: dict[str, str] | None = None,
) -> Resultado:
    """Aplica uma mensagem do perito ao estado e devolve a mensagem ao perito.

    ``colecoes``, ``fechadas`` e ``respostas`` são alterados no lugar.

    O ``orquestrador`` é a chamada única de LLM — extração + intenção + recusas
    + encerramentos + resposta a quesito + mensagem, tudo num JSON só. Ele
    recebe o schema, o estado, o histórico e a mensagem do perito, e devolve o
    JSON parseado. Nos testes, injeta-se um stub que devolve JSON canned.
    """
    from core import pendencias  # importado aqui para evitar ciclo

    quesitos = quesitos or []
    if respostas is None:
        respostas = {}
    historico = historico or []

    pendencias_lista = pendencias.todas(exame, colecoes, so_conversa=True)
    etapa_corrente = pendencias.etapa_atual(
        exame, colecoes, fechadas, quesitos, respostas
    )

    try:
        saida, bruto = orquestrador(
            exame,
            colecoes,
            fechadas,
            respostas,
            quesitos,
            historico,
            pendencias_lista,
            mensagem,
            etapa_corrente=etapa_corrente,
        )
    except ErroLLM as erro:
        return Resultado(
            mensagem=(
                "A ferramenta falhou ao processar sua mensagem — o problema é "
                "dela, não do que você escreveu. Nada foi anotado. Pode repetir? "
                f"Se continuar falhando, mostre isto a quem instalou: {erro}"
            ),
            erro=str(erro),
            chamou_modelo=True,
        )

    if not isinstance(saida, dict):
        saida = {}

    # PAREDE 1: aplicar valida a extração contra o schema.
    recusas_da_validacao: list[Recusa] = []
    alteracoes = aplicar(
        exame, colecoes, saida.get("extracao", {}) or {}, recusas_da_validacao
    )

    # PAREDE 2: ler_recusas valida cada recusa contra o conjunto fechado e a
    # fala do perito (motivo em MOTIVOS, "aproximado" exige palavra de
    # estimativa, trecho conferido).
    recusas_do_agente = saida.get("recusas", []) or []
    recusas = consolida_recusas(
        ler_recusas(exame, {"nao_registrado": recusas_do_agente}, mensagem)
        + recusas_da_validacao,
        houve_registro=bool(alteracoes),
    )

    # Encerramentos de coleção — token é o nome da coleção, ou "colecao:indice"
    # pra vinculada. LLM decide; a estrutura é a mesma de antes.
    for token in saida.get("encerramentos_de_colecao", []) or []:
        if isinstance(token, str) and token.strip() and token not in fechadas:
            fechadas.append(token.strip())

    # Resposta a quesito — confirmação de padrão OU texto livre do perito.
    quesito_respondido = ""
    confirmado = saida.get("confirmou_padrao_quesito")
    if isinstance(confirmado, str) and confirmado.strip():
        respostas[confirmado.strip()] = camada1_quesitos.PADRAO_ACEITO
        quesito_respondido = confirmado.strip()
    else:
        rq = saida.get("resposta_quesito")
        if isinstance(rq, dict):
            numero = str(rq.get("numero", "")).strip()
            texto = str(rq.get("texto", "")).strip()
            if numero and texto:
                respostas[numero] = texto
                quesito_respondido = numero

    # REDE DE SEGURANÇA: se estamos na etapa de quesitos, existe quesito
    # pendente, o LLM não gravou resposta E não interpretou como pergunta ao
    # assistente, a fala do perito é resposta ao primeiro quesito pendente. Sem
    # isso, "Nada a acrescentar." vira "sem_dado" e o perito repete a pergunta
    # infinito.
    forcado_forcada = False
    if (
        not quesito_respondido
        and etapa_corrente is not None
        and getattr(etapa_corrente, "quesitos", False)
        and str(saida.get("intencao", "")).strip().lower() != "pergunta"
        and mensagem.strip()
    ):
        pendentes_agora = camada1_quesitos.pendentes(quesitos, respostas)
        if pendentes_agora:
            numero = pendentes_agora[0].numero
            respostas[numero] = mensagem.strip()
            quesito_respondido = numero
            forcado_forcada = True
            # Suprime recusas que ficaram órfãs — o LLM disse "sem_dado" mas na
            # verdade era resposta.
            recusas = [
                r for r in recusas
                if r.motivo not in ("sem_dado", "fora_do_escopo", "sem_extracao")
            ]

    # PAREDE 3: valida_resumo — a mensagem do agente só afirma ter registrado o
    # que ``aplicar`` de fato gravou. Se não bater, cai no fallback determinístico.
    # Também caímos no fallback se a rede de segurança forçou uma resposta de
    # quesito — a mensagem do LLM provavelmente disse "não registrei" e virou
    # mentira.
    resumo = saida.get("resumo_do_registrado", [])
    mensagem_llm = str(saida.get("mensagem_do_assistente", "")).strip()
    if forcado_forcada:
        mensagem_final = _mensagem_pos_forca(
            exame, colecoes, quesitos, respostas, quesito_respondido
        )
    elif mensagem_llm and valida_resumo(resumo, alteracoes):
        mensagem_final = mensagem_llm
    else:
        mensagem_final = _mensagem_fallback(alteracoes, recusas)

    return Resultado(
        mensagem=mensagem_final,
        alteracoes=alteracoes,
        recusas=recusas,
        bruto=bruto,
        chamou_modelo=True,
        quesito_respondido=quesito_respondido,
        propoe_completo=bool(saida.get("propoe_completo")),
    )


def abertura(exame: Exame) -> str:
    """Mensagem inicial da conversa — dinâmica, ancorada na etapa 1 do laudo.

    A promessa de fidelidade fica no topo. Em seguida, a etapa 1 é anunciada
    com título e objetivo, para o perito saber exatamente sobre o que vamos
    falar primeiro. Sem etapas declaradas, cai numa saudação genérica.
    """
    partes = [
        "Vamos anotar esse exame. Fala como preferir — vou registrando o que "
        "você disser e pergunto o que faltar. Nada entra no laudo por mim."
    ]
    if exame.etapas:
        primeira = exame.etapas[0]
        partes.append(
            f"Vamos começar pela **etapa 1 — {primeira.titulo}**: "
            f"{primeira.objetivo}"
        )
    return "\n\n".join(partes)
