"""Controle da conversa de slot-filling.

Separado do Streamlit de propósito: aqui está a decisão de qual é a próxima
pergunta e o que fazer com a resposta, sem nenhuma chamada de UI.

O texto que o assistente fala é montado por template a partir do que foi
efetivamente gravado — o LLM não redige nenhuma fala. Assim o assistente não
tem como afirmar que registrou algo que não registrou.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field
from typing import Callable

from config.schema import Exame
from core import pendencias
from core.extracao import (
    Alteracao,
    Recusa,
    SEM_EXTRACAO,
    aplicar,
    consolida_recusas,
    extrair,
    ler_recusas,
)
from core.llm import ErroLLM

PERGUNTA = "pergunta"
CONFIRMAR_MAIS = "confirmar_mais"
COMPLETO = "completo"

#: Frases inteiras que encerram uma coleção ("não tem mais material").
_NEGATIVAS = {
    "nao", "n", "nao tem", "nao ha", "nao tem mais", "nao ha mais", "mais nenhum",
    "nenhum", "nenhuma", "so isso", "somente isso", "apenas isso", "e so",
    "e so isso", "e isso", "e isso mesmo", "isso", "negativo", "acabou",
    "finalizado", "sem mais", "pode seguir", "nao tem outro", "nao tem outra",
}
#: Frases inteiras que abrem um item novo sem descrevê-lo ainda.
_AFIRMATIVAS = {
    "sim", "s", "tem", "tem mais", "tem sim", "sim tem", "ha mais", "tem outro",
    "tem outra", "positivo", "mais um", "mais uma", "continua",
}
#: Palavras que sozinhas indicam intenção de encerrar.
_TOKENS_NEGATIVOS = {"nao", "n", "nenhum", "nenhuma", "negativo", "sem"}
#: Palavras que indicam que há mais um item.
_TOKENS_AFIRMATIVOS = {"sim", "tem", "outro", "outra", "positivo"}
#: Palavras que denunciam incerteza — nunca fecham nem abrem coleção.
_TOKENS_DUVIDA = {"sei", "lembro", "certeza", "talvez", "acho", "verificar", "conferir", "confirmar"}
#: Acima disso a mensagem é descrição, não um sim/não.
_MAX_PALAVRAS = 6


def _chave(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto)
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    limpo = sem_acento.lower()
    for pontuacao in ",.;!?":
        limpo = limpo.replace(pontuacao, " ")
    return " ".join(limpo.split())


def _sim_ou_nao(texto: str) -> tuple[list[str], bool]:
    """(tokens, é curto o bastante para ser um sim/não sem dado dentro)."""
    chave = _chave(texto)
    tokens = chave.split()
    curto = bool(tokens) and len(tokens) <= _MAX_PALAVRAS
    sem_numero = not any(c.isdigit() for c in chave)
    sem_duvida = not any(t in _TOKENS_DUVIDA for t in tokens)
    return tokens, curto and sem_numero and sem_duvida


def eh_negativa(texto: str) -> bool:
    """O perito disse que não há mais itens nesta coleção."""
    if _chave(texto) in _NEGATIVAS:
        return True
    tokens, avaliavel = _sim_ou_nao(texto)
    if not avaliavel:
        return False
    if any(t in _TOKENS_AFIRMATIVOS for t in tokens):
        return False  # "não, tem mais um" não encerra nada
    return tokens[0] in _TOKENS_NEGATIVOS


def eh_afirmativa(texto: str) -> bool:
    """O perito disse que há mais um item, sem descrevê-lo ainda."""
    if _chave(texto) in _AFIRMATIVAS:
        return True
    tokens, avaliavel = _sim_ou_nao(texto)
    if not avaliavel:
        return False
    if any(t in _TOKENS_NEGATIVOS for t in tokens):
        return False
    return any(t in _TOKENS_AFIRMATIVOS for t in tokens)


@dataclass(frozen=True)
class Fala:
    """O que o assistente deve dizer agora."""

    tipo: str
    texto: str
    colecao_chave: str = ""
    slot_chave: str = ""
    indice: int = 0

    def alvo(self) -> str:
        """Endereço do slot perguntado, para o extrator saber onde cai a resposta."""
        if self.tipo != PERGUNTA or not self.slot_chave:
            return ""
        return f'coleção "{self.colecao_chave}", índice {self.indice}, slot "{self.slot_chave}"' 


@dataclass
class Resultado:
    """Efeito de uma mensagem do perito."""

    fala: Fala
    alteracoes: list[Alteracao] = field(default_factory=list)
    recusas: list[Recusa] = field(default_factory=list)
    erro: str = ""
    bruto: str = ""
    chamou_modelo: bool = False
    abriu_item: bool = False


def _itens_referenciaveis(
    exame: Exame, colecoes: dict[str, list[dict]], slot
) -> str:
    """Lista os itens que um slot de referência pode apontar.

    Só enumera o que já está registrado — não sugere qual é o certo.
    """
    if not slot.referencia_colecao:
        return ""
    alvo = exame.colecao(slot.referencia_colecao)
    itens = colecoes.get(slot.referencia_colecao, [])
    if alvo is None or not itens:
        return ""
    rotulos = [f"{alvo.label_singular} {i}" for i in range(1, len(itens) + 1)]
    return "\n\nJá registrados: " + "; ".join(rotulos) + "."


def proxima_fala(exame: Exame, colecoes: dict[str, list[dict]], fechadas: list[str]) -> Fala:
    """Uma coleção por vez, na ordem do registro.

    Só depois de a coleção estar completa E o perito dizer que não há mais itens
    é que a conversa passa para a coleção seguinte — perguntar sobre exames no
    meio da descrição do material confundiria a transcrição.
    """
    for colecao in exame.colecoes:
        itens = colecoes.get(colecao.chave, [])

        encontradas = pendencias.pendencias_da_colecao(colecao, itens, so_conversa=True)
        if encontradas:
            pendente = encontradas[0]
            total = max(len(itens), colecao.minimo)
            texto = pendente.pergunta(total) + _itens_referenciaveis(
                exame, colecoes, pendente.slot
            )
            return Fala(
                PERGUNTA,
                texto,
                colecao.chave,
                pendente.slot.chave,
                pendente.indice,
            )

        if colecao.chave not in fechadas:
            pergunta = colecao.pergunta_mais_um or f"Há mais algum {colecao.label_singular.lower()}?"
            return Fala(CONFIRMAR_MAIS, pergunta, colecao.chave)

    return Fala(
        COMPLETO,
        "Todos os campos obrigatórios foram informados. Revise o painel ao lado e "
        "avance para a confirmação.",
    )


def saudacao(exame: Exame, colecoes: dict[str, list[dict]], fechadas: list[str]) -> str:
    fala = proxima_fala(exame, colecoes, fechadas)
    return (
        "Vamos registrar o que você examinou. Pode falar como você fala — eu só "
        "anoto o que você disser, e pergunto o que faltar.\n\n" + fala.texto
    )


def _texto_alteracoes(alteracoes: list[Alteracao]) -> str:
    linhas = "\n".join(f"- {a.descricao()}" for a in alteracoes)
    return f"Registrei:\n{linhas}"


def processar(
    exame: Exame,
    colecoes: dict[str, list[dict]],
    fechadas: list[str],
    mensagem: str,
    fala_anterior: Fala | None = None,
    extrator: Callable = extrair,
) -> Resultado:
    """Aplica uma mensagem do perito ao estado e decide a próxima fala.

    ``colecoes`` e ``fechadas`` são alterados no lugar.
    """
    aguardando = fala_anterior.colecao_chave if (
        fala_anterior is not None and fala_anterior.tipo == CONFIRMAR_MAIS
    ) else ""

    # "Não, é só isso" fecha a coleção sem gastar chamada de modelo.
    if aguardando and eh_negativa(mensagem):
        if aguardando not in fechadas:
            fechadas.append(aguardando)
        fala = proxima_fala(exame, colecoes, fechadas)
        return Resultado(fala=fala)

    pergunta_pendente = fala_anterior.texto if fala_anterior else ""
    alvo = fala_anterior.alvo() if fala_anterior else ""
    try:
        operacoes, bruto = extrator(exame, colecoes, mensagem, pergunta_pendente, alvo)
    except ErroLLM as erro:
        fala = fala_anterior or proxima_fala(exame, colecoes, fechadas)
        return Resultado(fala=fala, erro=str(erro), chamou_modelo=True)

    recusas_da_validacao: list[Recusa] = []
    alteracoes = aplicar(exame, colecoes, operacoes, recusas_da_validacao)
    recusas = consolida_recusas(
        ler_recusas(exame, operacoes, mensagem) + recusas_da_validacao,
        houve_registro=bool(alteracoes),
    )

    # "Sim" sem descrever nada: abre o próximo item para receber as perguntas.
    abriu_item = bool(aguardando) and not alteracoes and eh_afirmativa(mensagem)
    if abriu_item:
        colecoes.setdefault(aguardando, []).append({})

    # O modelo às vezes devolve {} sem dizer por quê, ou com um motivo que não
    # resistiu à conferência. Nada volta ao perito sem explicação — e a explicação
    # aqui assume a falha em vez de culpar a mensagem dele.
    if not alteracoes and not recusas and not abriu_item:
        # Com tudo preenchido, um "certo" do perito é assentimento, não dado
        # que faltou entender: não há por que devolver recusa.
        if proxima_fala(exame, colecoes, fechadas).tipo != COMPLETO:
            recusas = [Recusa(SEM_EXTRACAO)]

    fala = proxima_fala(exame, colecoes, fechadas)
    return Resultado(
        fala=fala,
        alteracoes=alteracoes,
        recusas=recusas,
        bruto=bruto,
        chamou_modelo=True,
        abriu_item=abriu_item,
    )


def resposta_do_assistente(resultado: Resultado) -> str:
    """Fala do assistente: o que foi gravado (se algo foi) e a próxima pergunta."""
    partes: list[str] = []

    if resultado.erro:
        # Única mensagem padronizada do sistema: a falha é da ferramenta, não da
        # fala do perito, e não há motivo do modelo para explicar.
        partes.append(
            "A ferramenta falhou ao processar sua mensagem — o problema é dela, não "
            "do que você escreveu. Nada foi anotado."
        )
        partes.append(
            "Pode repetir? Se continuar falhando, mostre isto a quem instalou a "
            f"ferramenta: {resultado.erro}"
        )
        return "\n\n".join(partes)

    if resultado.alteracoes:
        partes.append(_texto_alteracoes(resultado.alteracoes))

    # Toda recusa se explica e cita o trecho que a causou. Sem o motivo, o perito
    # repete a mesma frase e a pergunta volta igual, sem fim.
    for recusa in resultado.recusas:
        partes.append(recusa.explicacao())

    partes.append(resultado.fala.texto)
    return "\n\n".join(partes)
