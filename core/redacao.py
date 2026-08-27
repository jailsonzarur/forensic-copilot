"""Redação do parágrafo técnico da seção 4, a partir do relato do perito.

A regra do projeto não muda: a IA só reformata o que o perito informou. Aqui
ela reformata o **relato de procedimento** — "fiz o Scott, usei padrão de
cocaína, deu azul" vira o parágrafo no registro formal do laudo.

O que ela não pode fazer é acrescentar etapa, reagente, fase ou grandeza que o
perito não citou. Um parágrafo que inventa "na fase clorofórmica" descreve um
procedimento que talvez não tenha acontecido, num documento assinado.
"""

from __future__ import annotations

from core import biblioteca
from core.llm import chamar_json
from templates.identificacao_substancia import boilerplate

SISTEMA = """Você redige o parágrafo técnico de um laudo pericial a partir do relato do perito sobre como conduziu o ensaio.

REGRAS ABSOLUTAS
1. Use SOMENTE o que o perito relatou. Reagente, padrão de referência, fase,
   grandeza comparada, equipamento, cor observada: só entra o que ele disse.
2. NUNCA acrescente etapa, condição ou detalhe técnico que ele não citou, mesmo
   que seja o procedimento usual daquele ensaio. O laudo registra o que foi
   feito naquela bancada, não o que os laboratórios costumam fazer.
3. Não conclua além do que ele relatou. Se ele não disse que o resultado
   confirma a substância, não escreva que confirma.
4. Escreva em português formal, impessoal, no pretérito, no tom de laudo
   oficial. Uma frase ou duas. Sem adjetivos de ênfase.
5. O título é o nome da subseção, no padrão "Análise por <ensaio>".

FORMATO DA SAÍDA
Responda APENAS com um objeto JSON:
{"titulo": "<título da subseção>", "texto": "<parágrafo>"}"""


def tem_redacao(nome_teste: str, substancia: str) -> bool:
    """Já existe parágrafo transcrito ou escrito por perito para este ensaio?"""
    if not str(nome_teste).strip():
        return True  # sem ensaio nomeado não há o que redigir ainda
    chave_par = (
        boilerplate.normaliza(nome_teste),
        boilerplate.chave_substancia(substancia),
    )
    if boilerplate.RESULTADOS_POR_ENSAIO.get(chave_par):
        return True
    return biblioteca.buscar("resultado", biblioteca.chave(nome_teste, substancia)) is not None


def redigir(nome_teste: str, substancia: str, procedimento: str) -> tuple[dict, str]:
    """(dicionário com titulo e texto, resposta bruta do modelo)."""
    instrucao = "\n".join(
        [
            f"ENSAIO: {nome_teste}",
            f"SUBSTÂNCIA PESQUISADA: {substancia or '(não informada)'}",
            "",
            "RELATO DO PERITO SOBRE COMO CONDUZIU O ENSAIO:",
            procedimento.strip(),
        ]
    )
    dados, bruto = chamar_json(SISTEMA, instrucao, temperatura=0.2)
    return (
        {
            "titulo": str(dados.get("titulo", "")).strip()
            or f"Análise por {nome_teste.lower()}",
            "texto": str(dados.get("texto", "")).strip(),
        },
        bruto,
    )
