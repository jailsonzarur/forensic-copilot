"""CAMADA 2 — texto fixo do laudo de Identificação de Substância.

Este módulo está deliberadamente VAZIO. Cada bloco abaixo é texto institucional
que só pode ser TRANSCRITO dos laudos reais do Instituto de Criminalística da
PC-PI. Escrevê-lo de memória — inclusive a redação da Portaria 344 SVS/MS, dos
parágrafos técnicos dos ensaios ou do texto de proscrição — seria inventar
conteúdo de laudo, o que o projeto existe para evitar.

Nada aqui passa pelo LLM como criação: é template, copiado e parametrizado.
"""

from __future__ import annotations

PENDENTE = ""  # marcador: bloco ainda não transcrito de laudo real

#: Preâmbulo institucional (Instituto de Criminalística / DPTC / PC-PI).
PREAMBULO = PENDENTE

#: Parágrafo técnico de descrição de cada ensaio, indexado pelo nome do teste
#: usado em ``config.exams`` (ex.: "Ensaio de Scott Modificado").
DESCRICAO_EXAMES: dict[str, str] = {}

#: Texto legal de proscrição (Portaria 344 SVS/MS, Lista F1, art. 170 do CPP).
TEXTO_PROSCRICAO = PENDENTE

#: Quesitos e o padrão de resposta de cada um.
QUESITOS: tuple[dict[str, str], ...] = ()

#: Referências bibliográficas.
REFERENCIAS: tuple[str, ...] = ()

#: Fecho do laudo.
FECHO = PENDENTE


def blocos_pendentes() -> list[str]:
    """Blocos de boilerplate ainda não transcritos dos laudos reais."""
    pendencias = []
    if not PREAMBULO:
        pendencias.append("preâmbulo institucional")
    if not DESCRICAO_EXAMES:
        pendencias.append("descrição técnica dos ensaios")
    if not TEXTO_PROSCRICAO:
        pendencias.append("texto legal de proscrição")
    if not QUESITOS:
        pendencias.append("quesitos e padrão de resposta")
    if not REFERENCIAS:
        pendencias.append("referências bibliográficas")
    if not FECHO:
        pendencias.append("fecho")
    return pendencias
