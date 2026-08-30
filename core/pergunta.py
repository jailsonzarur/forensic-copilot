"""Formulação da pergunta que o assistente faz ao perito.

O QUE falta é decidido por regra — a varredura de pendências, que não depende
de modelo nenhum. Só a FORMA da pergunta passa por aqui, para que a conversa
soe como conversa e possa cobrir mais de um campo de uma vez.

A separação importa: o modelo escolhe palavras, nunca o que está faltando. E
não pode sugerir resposta — "a coloração é branca?" plantaria no laudo um dado
que o perito não disse. Também não pode engolir orientação: opção fechada
listada no padrão, ou exemplos entre parênteses, precisam sobreviver à
reformulação — sem eles o perito responde algo que a ferramenta descarta em
silêncio, ou fica sem saber o que a pergunta espera.
"""

from __future__ import annotations

import re

from core.llm import chamar_json

SISTEMA = """Você conversa com um perito criminal enquanto ele preenche um laudo. Sua tarefa é FORMULAR a próxima pergunta como um colega faria — não como um formulário.

REGRAS
1. Pergunte SOMENTE pelos campos listados. Não invente campo, nem pergunte por
   dado que não está na lista.
2. NUNCA sugira, exemplifique ou insinue uma resposta que não venha das listas
   abaixo. Nada de "a coloração é branca?", "seria em torno de 10 g?",
   "geralmente é plástico". O perito mediu; você só pergunta.
3. Pode juntar os campos numa frase só quando forem próximos, para não parecer
   interrogatório. No máximo três por vez.
4. Tom de colega ao lado: direto, à vontade, sem "por gentileza", "poderia me
   informar", saudação genérica ou emoji. Uma frase, no máximo duas.
5. Se houver contexto de item ("Material 2"), deixe claro de qual item se trata.
6. Não repita nem comente o que já foi anotado — o resto do texto do assistente
   cuida disso.
7. Quando um campo listar VALORES ACEITOS, TODOS têm que aparecer na pergunta,
   com os mesmos nomes. Sem isso o perito responde algo que a ferramenta descarta
   em silêncio.
8. Quando um campo listar EXEMPLOS, mencione TODOS na pergunta, deixando claro
   que são exemplos e que ele pode informar outro. Sem isso o perito fica sem
   saber que tipo de resposta a pergunta espera.

FORMATO DA SAÍDA
Responda APENAS com um objeto JSON: {"pergunta": "<a pergunta>"}"""


def _preserva_opcoes(pergunta: str, opcoes_por_campo: list[tuple[str, ...]]) -> bool:
    """Toda opção fechada aparece na pergunta reformulada?

    Se alguma sumir, o perito não sabe o que responder — melhor cair no padrão,
    que sempre lista tudo, do que servir a reformulação incompleta.
    """
    normalizada = pergunta.lower()
    for opcoes in opcoes_por_campo:
        for opcao in opcoes:
            if opcao.lower() not in normalizada:
                return False
    return True


_PARENTHETICAL = re.compile(r"\(([^)]+)\)")


def _hints_do_padrao(padrao: str) -> tuple[str, ...]:
    """Palavras entre parênteses no padrão: exemplos ou opções ditadas por ele.

    O laudo real convencionou colocar orientação assim — "Que tipo? (motocicleta,
    motoneta, automóvel…)". Se o formulador remove os parênteses, ele mata a
    orientação junto. Aqui a lista é extraída para a validação exigir que cada
    item apareça na pergunta reformulada.
    """
    match = _PARENTHETICAL.search(padrao)
    if not match:
        return ()
    conteudo = match.group(1)
    for lixo in ("…", "...", "etc.", "etc"):
        conteudo = conteudo.replace(lixo, "")
    partes = re.split(r"[,;]|\bou\b", conteudo)
    return tuple(p.strip() for p in partes if p.strip())


def formular(
    rotulo_item: str,
    campos: list[str],
    padrao: str,
    opcoes_por_campo: list[tuple[str, ...]] | None = None,
) -> str:
    """Pergunta natural pelos ``campos``; devolve ``padrao`` se algo falhar.

    ``padrao`` é a pergunta determinística. Ela é o contrato: sem chave, sem
    crédito, ou com falha de conteúdo (opção fechada engolida, exemplo do
    padrão perdido), a conversa segue com ela.
    """
    if not campos:
        return padrao

    opcoes_por_campo = list(opcoes_por_campo) if opcoes_por_campo else [() for _ in campos]
    # Exemplos entre parênteses no padrão vão como HINTS separados: são
    # orientação, não conjunto fechado. Só o primeiro campo recebe hints porque
    # o padrão vem da pergunta do primeiro slot.
    hints_por_campo: list[tuple[str, ...]] = [() for _ in campos]
    hints_por_campo[0] = _hints_do_padrao(padrao)

    linhas_campos: list[str] = []
    for label, opcoes, hints in zip(campos, opcoes_por_campo, hints_por_campo):
        partes = [f"  - {label}"]
        if opcoes:
            partes.append(f"[VALORES ACEITOS: {', '.join(opcoes)}]")
        if hints:
            partes.append(f"[EXEMPLOS: {', '.join(hints)}]")
        linhas_campos.append(" ".join(partes))

    instrucao = "\n".join(
        [
            f"ITEM: {rotulo_item}" if rotulo_item else "ITEM: (único)",
            "CAMPOS QUE FALTAM:",
            *linhas_campos,
        ]
    )
    try:
        dados, _ = chamar_json(SISTEMA, instrucao, temperatura=0.3)
    except Exception:
        return padrao

    pergunta = str(dados.get("pergunta", "")).strip()
    if not pergunta:
        return padrao
    # Opções fechadas E exemplos precisam sobreviver — a mesma validação cobre
    # os dois: item que sumiu é orientação perdida.
    if not _preserva_opcoes(pergunta, opcoes_por_campo):
        return padrao
    if not _preserva_opcoes(pergunta, hints_por_campo):
        return padrao
    return pergunta
