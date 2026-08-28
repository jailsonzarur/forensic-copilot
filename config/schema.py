"""Tipos que descrevem um exame no registro.

Um laudo novo = uma entrada nova em ``config.exams.EXAMES``. As telas leem
estes objetos; nada de UI hardcoded por tipo de exame.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

TipoCampo = Literal["texto", "texto_longo", "data", "select"]


@dataclass(frozen=True)
class CampoAdmin:
    """Campo do formulário administrativo — transcrição pura, sem LLM."""

    chave: str
    label: str
    tipo: TipoCampo = "texto"
    obrigatorio: bool = True
    ajuda: str = ""
    placeholder: str = ""
    opcoes: tuple[str, ...] = ()
    #: True quando o campo costuma constar da requisição e pode ser transcrito
    #: dela. Campo que só o Instituto atribui (número do laudo, perito
    #: designado) fica False: procurá-lo na requisição só produziria invenção.
    da_requisicao: bool = False


@dataclass(frozen=True)
class Slot:
    """Campo da CAMADA 1 — coletado na conversa com o perito.

    ``pergunta`` é a pergunta dirigida usada quando o slot vira pendência.
    ``instrucao_extracao`` orienta o extrator JSON sobre o que capturar; ela
    descreve o formato do dado, nunca sugere um valor.
    ``obrigatorio_se`` torna o slot exigível apenas quando outro slot da mesma
    coleção tem determinado valor — ex.: a substância só é exigida quando o
    resultado do exame é positivo.
    """

    chave: str
    label: str
    obrigatorio: bool = True
    pergunta: str = ""
    instrucao_extracao: str = ""
    obrigatorio_se: tuple[str, str] | None = None
    opcoes: tuple[str, ...] = ()
    #: Quando True, ``opcoes`` é o conjunto fechado de valores aceitos e a
    #: extração descarta qualquer outro valor (o slot volta como pendência).
    #: Quando False, ``opcoes`` é apenas vocabulário sugerido — o perito pode
    #: informar algo fora da lista e o valor dele prevalece.
    opcoes_fechadas: bool = False
    #: Campo que vai ao laudo como medição ou contagem do perito. Aproximação
    #: ("em torno de 15") não é gravada: o extrator recusa e diz o motivo, para
    #: o perito informar o valor exato em vez de ficar repetindo a pergunta.
    exige_valor_exato: bool = False
    #: False quando o slot não é coletado na conversa, e sim confirmado pelo
    #: perito na tela de confirmação — caso de referência entre coleções, que o
    #: extrator só preencheria por dedução.
    na_conversa: bool = True
    #: True quando o slot só é exigido enquanto não houver redação institucional
    #: transcrita para aquele ensaio: sem texto pronto, o perito precisa contar
    #: como conduziu o exame para que o parágrafo possa ser redigido.
    exigido_sem_redacao: bool = False
    #: Chave de outra coleção quando este slot referencia um item dela (ex.: o
    #: exame aponta para qual material foi examinado). A pergunta dirigida passa
    #: a listar os itens já registrados, para o perito responder pelo número.
    referencia_colecao: str = ""

    def exigido_em(self, item: dict) -> bool:
        """O slot é exigível para este item da coleção?"""
        if self.obrigatorio_se is not None:
            chave, valor = self.obrigatorio_se
            outro = str(item.get(chave, "")).strip()
            # "*" = exigido sempre que o outro campo estiver preenchido.
            if valor == "*":
                return bool(outro)
            return outro.lower() == valor.lower()
        return self.obrigatorio


@dataclass(frozen=True)
class Colecao:
    """Grupo repetível (1..N) de slots — ex.: itens de material, exames."""

    chave: str
    label_singular: str
    label_plural: str
    slots: tuple[Slot, ...]
    minimo: int = 1
    aceita_imagens: bool = False
    pergunta_mais_um: str = ""
    #: Chave da coleção à qual cada item desta pertence. A conversa percorre
    #: item por item da coleção-mãe e, dentro de cada um, os filhos — assim a
    #: referência entre eles é consequência de onde a conversa está, e não algo
    #: perguntado de novo nem deduzido pelo extrator.
    vinculada_a: str = ""

    def slot(self, chave: str) -> Slot | None:
        return next((s for s in self.slots if s.chave == chave), None)


@dataclass(frozen=True)
class Exame:
    """Uma entrada do registro: um tipo de laudo."""

    id: str
    label: str
    descricao: str
    campos_admin: tuple[CampoAdmin, ...]
    colecoes: tuple[Colecao, ...] = ()
    disponivel: bool = True
    observacao_indisponivel: str = ""

    def colecao(self, chave: str) -> Colecao | None:
        return next((c for c in self.colecoes if c.chave == chave), None)
