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
class Secao:
    """Uma seção do documento, na ordem em que é impressa.

    A sequência de seções é do TIPO DE EXAME, não do montador: identificação de
    substância tem histórico e referências, identificação veicular não tem
    nenhum dos dois. Declarar aqui evita que o `documento.py` conheça os tipos.
    """

    #: "cabecalho", "preambulo", "texto", "objetos", "exames", "resultados",
    #: "conclusao", "quesitos", "referencias", "fecho", "assinatura", "apendice".
    tipo: str
    #: Título impresso, já com a numeração do laudo ("1. DO VEÍCULO").
    titulo: str = ""
    #: Para "texto", o nome da constante no template; para "objetos" e "exames",
    #: a chave da coleção.
    chave: str = ""


@dataclass(frozen=True)
class GrupoAdmin:
    """Campos administrativos repetíveis — ex.: dois peritos signatários.

    Existe porque a quantidade varia por tipo de exame e por caso: um laudo de
    identificação veicular pode sair assinado por dois peritos, e o formulário
    precisa acompanhar isso sem campo morto nos outros tipos.
    """

    chave: str
    label_singular: str
    campos: tuple[CampoAdmin, ...]
    minimo: int = 1
    maximo: int = 0  # 0 = sem limite


@dataclass(frozen=True)
class Etapa:
    """Uma etapa da fase de conversa — declarada pelo tipo de laudo.

    O agente é 100% conversacional, mas o roteiro é nosso: a ordem e o
    objetivo de cada etapa vêm daqui. O controlador calcula a etapa atual a
    partir das pendências determinísticas e informa ao agente, que não pode
    pular pra frente enquanto a atual não estiver completa.
    """

    titulo: str
    objetivo: str
    #: Chave da coleção associada — a etapa está completa quando esta coleção
    #: não tem pendência E está fechada (ou é a única obrigatória). Vazio = a
    #: etapa não é de coleção (etapa de quesitos, por exemplo).
    colecao: str = ""
    #: True para a etapa dos quesitos da requisição.
    quesitos: bool = False


@dataclass(frozen=True)
class Exame:
    """Uma entrada do registro: um tipo de laudo."""

    id: str
    label: str
    descricao: str
    campos_admin: tuple[CampoAdmin, ...]
    colecoes: tuple[Colecao, ...] = ()
    #: Grupos de campos administrativos que se repetem (peritos signatários).
    grupos_admin: tuple[GrupoAdmin, ...] = ()
    #: Etapas da fase de conversa, em ordem. O roteiro que o agente segue.
    etapas: tuple[Etapa, ...] = ()
    #: Ordem das seções do documento. Vazio = usa a ordem clássica do laudo de
    #: substância, para não quebrar o que já existe.
    secoes: tuple[Secao, ...] = ()
    #: Pacote em ``templates/`` de onde sai o texto fixo deste exame.
    template: str = ""
    #: Imagens em apêndice fotográfico ao fim, em vez de embutidas no corpo.
    imagens_em_apendice: bool = False
    disponivel: bool = True
    observacao_indisponivel: str = ""

    def colecao(self, chave: str) -> Colecao | None:
        return next((c for c in self.colecoes if c.chave == chave), None)

    def colecao_objeto(self) -> Colecao | None:
        """A coleção do que foi submetido a exame.

        É a primeira coleção que não pende de outra: o material no laudo de
        substância, o veículo no de identificação veicular, o local no de
        danos. Serve para que o montador e os derivados parem de presumir
        "materiais" — presumir era o que impedia um terceiro tipo de laudo.
        """
        return next((c for c in self.colecoes if not c.vinculada_a), None)

    def grupo(self, chave: str) -> GrupoAdmin | None:
        return next((g for g in self.grupos_admin if g.chave == chave), None)

    def todos_campos_admin(self) -> tuple[CampoAdmin, ...]:
        """Campos simples mais os dos grupos repetíveis, para rótulos e busca."""
        dos_grupos = tuple(c for g in self.grupos_admin for c in g.campos)
        return (*self.campos_admin, *dos_grupos)
