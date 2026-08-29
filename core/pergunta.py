"""Formulação da pergunta que o assistente faz ao perito.

O QUE falta é decidido por regra — a varredura de pendências, que não depende
de modelo nenhum. Só a FORMA da pergunta passa por aqui, para que a conversa
soe como conversa e possa cobrir mais de um campo de uma vez.

A separação importa: o modelo escolhe palavras, nunca o que está faltando. E
não pode sugerir resposta — "a coloração é branca?" plantaria no laudo um dado
que o perito não disse.
"""

from __future__ import annotations

from core.llm import chamar_json

SISTEMA = """Você conversa com um perito criminal enquanto ele preenche um laudo. Sua tarefa é FORMULAR a próxima pergunta como um colega faria — não como um formulário.

REGRAS
1. Pergunte SOMENTE pelos campos listados. Não invente campo, nem pergunte por
   dado que não está na lista.
2. NUNCA sugira, exemplifique ou insinue uma resposta. Nada de "a coloração é
   branca?", "seria em torno de 10 g?", "geralmente é plástico". O perito mediu;
   você só pergunta.
3. Pode juntar os campos numa frase só quando forem próximos, para não parecer
   interrogatório. No máximo três por vez.
4. Tom de colega ao lado: direto, à vontade, sem "por gentileza", "poderia me
   informar", saudação genérica ou emoji. Uma frase, no máximo duas.
5. Se houver contexto de item ("Material 2"), deixe claro de qual item se trata.
6. Não repita nem comente o que já foi anotado — o resto do texto do assistente
   cuida disso.
7. Quando um campo trouxer OPÇÕES entre parênteses, TODAS elas têm que aparecer
   na pergunta, com os mesmos nomes. É a única forma de o perito saber que só
   esses valores contam. Omitir qualquer uma faz a resposta dele cair fora do
   conjunto e ser descartada em silêncio.

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


def formular(
    rotulo_item: str,
    campos: list[str],
    padrao: str,
    opcoes_por_campo: list[tuple[str, ...]] | None = None,
) -> str:
    """Pergunta natural pelos ``campos``; devolve ``padrao`` se algo falhar.

    ``padrao`` é a pergunta determinística. Ela é o contrato: sem chave, sem
    crédito, ou com falha de conteúdo (opção fechada engolida), a conversa
    segue com ela.
    """
    if not campos:
        return padrao

    opcoes_por_campo = opcoes_por_campo or [() for _ in campos]

    linhas_campos: list[str] = []
    for label, opcoes in zip(campos, opcoes_por_campo):
        if opcoes:
            aceitas = ", ".join(opcoes)
            linhas_campos.append(f"  - {label} (só um destes: {aceitas})")
        else:
            linhas_campos.append(f"  - {label}")

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
    if not _preserva_opcoes(pergunta, opcoes_por_campo):
        return padrao
    return pergunta
