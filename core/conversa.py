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

from config.schema import Colecao, Exame
from core import pendencias
from core import quesitos as camada1_quesitos
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
QUESITO = "quesito"
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


_CONFIRMACOES = {
    "confirmo", "confirmado", "confirma", "ok", "certo", "isso", "esse mesmo",
    "pode usar", "usa esse", "de acordo", "concordo", "sim", "padrao", "o padrao",
}


def _confirma(texto: str) -> bool:
    """O perito aceitou a resposta padrão em vez de escrever a dele."""
    return _chave(texto) in _CONFIRMACOES


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
    quesito_numero: str = ""
    quesito_pergunta: str = ""
    #: Rótulo do item e campos que ainda faltam nele. Servem para o assistente
    #: formular uma pergunta que cubra mais de um campo de uma vez.
    rotulo_item: str = ""
    campos_faltando: tuple[str, ...] = ()
    #: Material de que a conversa está tratando. É ele que vincula o exame ao
    #: material, sem perguntar de novo e sem o extrator deduzir.
    material_contexto: int = 0
    #: Marca a gravar em ``fechadas`` quando o perito disser que não há mais.
    token_fechamento: str = ""

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
    quesito_respondido: str = ""


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


def _fala_de_quesito(perguntas: list[str], respostas: dict[str, str]) -> Fala | None:
    """Próximo quesito da requisição a ser perguntado ao perito.

    O laudo responde ao que a autoridade perguntou, e quem responde é o perito.
    Quando existe padrão transcrito de laudo real, ele é oferecido para o perito
    confirmar — oferecer não é preencher.
    """
    faltando = camada1_quesitos.pendentes(perguntas, respostas)
    if not faltando:
        return None

    quesito = faltando[0]
    modelo = camada1_quesitos.padrao_de_resposta(quesito.pergunta)
    texto = f"Quesito {quesito.numero} da requisição — {quesito.pergunta}"

    if modelo and "{" not in modelo:
        texto += (
            f"\n\nA resposta padrão do Instituto para este quesito é: «{modelo}». "
            "Responda «confirmo» para usá-la, ou escreva a sua."
        )
    elif modelo:
        texto += (
            "\n\nEste quesito tem resposta padrão, montada a partir do que você já "
            "registrou. Responda «confirmo» para usá-la, ou escreva a sua."
        )
    return Fala(QUESITO, texto, quesito_numero=quesito.numero, quesito_pergunta=quesito.pergunta)


def _chave_fechada(colecao: Colecao, indice_mae: int = 0) -> str:
    """Marca de coleção encerrada. Coleção vinculada encerra por item da mãe."""
    return f"{colecao.chave}:{indice_mae}" if colecao.vinculada_a else colecao.chave


def _filhos(colecao: Colecao, colecoes: dict, indice_mae: int) -> list[tuple[int, dict]]:
    """(índice global, item) dos filhos que pertencem ao item ``indice_mae``."""
    referencia = str(indice_mae)
    return [
        (posicao, item)
        for posicao, item in enumerate(colecoes.get(colecao.chave, []), start=1)
        if str(item.get("item_material", "")).strip() == referencia
    ]


def _pergunta_do_item(
    exame: Exame,
    colecao: Colecao,
    colecoes: dict,
    indice: int,
    item: dict,
    total: int,
    material_contexto: int = 0,
) -> Fala | None:
    """Fala pedindo o que falta NESTE item, ou None se ele já está completo."""
    faltando = [
        slot
        for slot in colecao.slots
        if pendencias._exigido(slot, item, so_conversa=True)
        and not str(item.get(slot.chave, "")).strip()
    ]
    if not faltando:
        return None

    primeiro = faltando[0]
    base = primeiro.pergunta or f"Qual o valor de {primeiro.label}?"
    rotulo = f"{colecao.label_singular} {indice}" if total > 1 or indice > 1 else ""
    texto = f"{rotulo} — {base}" if rotulo else base
    texto += _itens_referenciaveis(exame, colecoes, primeiro)
    return Fala(
        PERGUNTA,
        texto,
        colecao.chave,
        primeiro.chave,
        indice,
        rotulo_item=rotulo or colecao.label_singular,
        campos_faltando=tuple(s.label for s in faltando),
        material_contexto=material_contexto,
    )


def proxima_fala(
    exame: Exame,
    colecoes: dict[str, list[dict]],
    fechadas: list[str],
    quesitos: list[str] | None = None,
    respostas: dict[str, str] | None = None,
) -> Fala:
    """Percorre material por material e, dentro de cada um, os seus exames.

    A ordem é Material 1 → exames do Material 1 → Material 2 → exames do
    Material 2 → quesitos. Assim o exame nunca precisa perguntar "de qual
    material?": ele é do material de que a conversa acabou de tratar.
    """
    principais = [c for c in exame.colecoes if not c.vinculada_a]
    for principal in principais:
        vinculadas = [c for c in exame.colecoes if c.vinculada_a == principal.chave]
        itens = colecoes.get(principal.chave, [])
        total = max(len(itens), principal.minimo)

        for indice in range(1, total + 1):
            item = itens[indice - 1] if indice <= len(itens) else {}

            fala = _pergunta_do_item(
                exame, principal, colecoes, indice, item, total, material_contexto=indice
            )
            if fala is not None:
                return fala

            for filha in vinculadas:
                filhos = _filhos(filha, colecoes, indice)
                if len(filhos) < filha.minimo:
                    fala = _pergunta_do_item(
                        exame, filha, colecoes,
                        len(colecoes.get(filha.chave, [])) + 1, {}, 1,
                        material_contexto=indice,
                    )
                    if fala is not None:
                        return fala

                for posicao, filho in filhos:
                    fala = _pergunta_do_item(
                        exame, filha, colecoes, posicao, filho,
                        len(colecoes.get(filha.chave, [])), material_contexto=indice,
                    )
                    if fala is not None:
                        return fala

                if _chave_fechada(filha, indice) not in fechadas:
                    pergunta = filha.pergunta_mais_um or (
                        f"Há mais algum {filha.label_singular.lower()}?"
                    )
                    if total > 1:
                        pergunta = f"{principal.label_singular} {indice} — {pergunta}"
                    return Fala(
                        CONFIRMAR_MAIS,
                        pergunta,
                        filha.chave,
                        material_contexto=indice,
                        token_fechamento=_chave_fechada(filha, indice),
                    )

        if _chave_fechada(principal) not in fechadas:
            pergunta = principal.pergunta_mais_um or (
                f"Há mais algum {principal.label_singular.lower()}?"
            )
            return Fala(
                CONFIRMAR_MAIS,
                pergunta,
                principal.chave,
                token_fechamento=_chave_fechada(principal),
            )

    fala = _fala_de_quesito(quesitos or [], respostas if respostas is not None else {})
    if fala is not None:
        return fala

    return Fala(
        COMPLETO,
        "Tudo registrado, inclusive os quesitos da requisição. Revise o painel ao "
        "lado e avance para a confirmação.",
    )


def saudacao(
    exame: Exame,
    colecoes: dict[str, list[dict]],
    fechadas: list[str],
    quesitos: list[str] | None = None,
    respostas: dict[str, str] | None = None,
) -> str:
    fala = proxima_fala(exame, colecoes, fechadas, quesitos, respostas)
    return (
        "Vamos registrar o que você examinou. Pode falar como você fala — eu só "
        "anoto o que você disser, e pergunto o que faltar.\n\n" + fala.texto
    )


def _vincula(exame: Exame, colecoes: dict[str, list[dict]], material: int) -> None:
    """Prende ao material em foco os itens vinculados que ainda estão soltos."""
    if not material:
        return
    for colecao in exame.colecoes:
        if not colecao.vinculada_a:
            continue
        for item in colecoes.get(colecao.chave, []):
            if not str(item.get("item_material", "")).strip():
                item["item_material"] = str(material)


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
    quesitos: list[str] | None = None,
    respostas: dict[str, str] | None = None,
) -> Resultado:
    """Aplica uma mensagem do perito ao estado e decide a próxima fala.

    ``colecoes`` e ``fechadas`` são alterados no lugar.
    """
    quesitos = quesitos or []
    if respostas is None:
        respostas = {}

    # Resposta a quesito é a palavra do perito: entra como ele escreveu, sem
    # passar por leitura automática. "Confirmo" registra o padrão do Instituto.
    if fala_anterior is not None and fala_anterior.tipo == QUESITO:
        numero = fala_anterior.quesito_numero
        modelo = camada1_quesitos.padrao_de_resposta(fala_anterior.quesito_pergunta)
        if modelo and _confirma(mensagem):
            respostas[numero] = camada1_quesitos.PADRAO_ACEITO
        else:
            respostas[numero] = mensagem.strip()
        return Resultado(
            fala=proxima_fala(exame, colecoes, fechadas, quesitos, respostas),
            quesito_respondido=numero,
        )

    aguardando = (
        fala_anterior.token_fechamento
        if fala_anterior is not None and fala_anterior.tipo == CONFIRMAR_MAIS
        else ""
    )
    colecao_aguardada = fala_anterior.colecao_chave if aguardando else ""
    contexto = fala_anterior.material_contexto if fala_anterior else 0

    # "Não, é só isso" fecha a coleção sem gastar chamada de leitura.
    if aguardando and eh_negativa(mensagem):
        if aguardando not in fechadas:
            fechadas.append(aguardando)
        fala = proxima_fala(exame, colecoes, fechadas, quesitos, respostas)
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

    # Todo exame descrito enquanto se fala de um material pertence a ele: a
    # referência vem de onde a conversa está, não de dedução do extrator.
    _vincula(exame, colecoes, contexto)

    # "Sim" sem descrever nada: abre o próximo item para receber as perguntas.
    abriu_item = bool(aguardando) and not alteracoes and eh_afirmativa(mensagem)
    if abriu_item:
        novo_item: dict = {}
        colecao = exame.colecao(colecao_aguardada)
        if colecao is not None and colecao.vinculada_a and contexto:
            novo_item["item_material"] = str(contexto)
        colecoes.setdefault(colecao_aguardada, []).append(novo_item)

    # O modelo às vezes devolve {} sem dizer por quê, ou com um motivo que não
    # resistiu à conferência. Nada volta ao perito sem explicação — e a explicação
    # aqui assume a falha em vez de culpar a mensagem dele.
    if not alteracoes and not recusas and not abriu_item:
        # Com tudo preenchido, um "certo" do perito é assentimento, não dado
        # que faltou entender: não há por que devolver recusa.
        if proxima_fala(exame, colecoes, fechadas, quesitos, respostas).tipo != COMPLETO:
            recusas = [Recusa(SEM_EXTRACAO)]

    fala = proxima_fala(exame, colecoes, fechadas, quesitos, respostas)
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

    if resultado.quesito_respondido:
        partes.append(f"Quesito {resultado.quesito_respondido} respondido.")

    if resultado.alteracoes:
        partes.append(_texto_alteracoes(resultado.alteracoes))

    # Toda recusa se explica e cita o trecho que a causou. Sem o motivo, o perito
    # repete a mesma frase e a pergunta volta igual, sem fim.
    for recusa in resultado.recusas:
        partes.append(recusa.explicacao())

    partes.append(resultado.fala.texto)
    return "\n\n".join(partes)
