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

SISTEMA = """Você é o assistente de um perito criminal preenchendo um laudo. Sua tarefa é FORMULAR a próxima pergunta.

REGRAS
1. Pergunte SOMENTE pelos campos listados. Não invente campo, não pergunte por
   dado que não está na lista.
2. NUNCA sugira, exemplifique ou insinue uma resposta. Nada de "a coloração é
   branca?", "seria em torno de 10 g?", "geralmente é plástico". O perito mediu;
   você só pergunta.
3. Pode juntar os campos numa pergunta só quando forem próximos, para não
   interrogar campo a campo. No máximo três por vez.
4. Português direto e profissional, sem gentileza excessiva, sem emoji, sem
   repetir o que já foi registrado. Uma ou duas frases.
5. Se houver contexto de item ("Material 2"), deixe claro de qual item se trata.

FORMATO DA SAÍDA
Responda APENAS com um objeto JSON: {"pergunta": "<a pergunta>"}"""


def formular(rotulo_item: str, campos: list[str], padrao: str) -> str:
    """Pergunta natural pelos ``campos``; devolve ``padrao`` se algo falhar.

    ``padrao`` é a pergunta determinística. Ela é o contrato: se o modelo não
    responder, ou responder algo vazio, a conversa segue com ela.
    """
    if not campos:
        return padrao

    instrucao = "\n".join(
        [
            f"ITEM: {rotulo_item}" if rotulo_item else "ITEM: (único)",
            "CAMPOS QUE FALTAM:",
            *(f"  - {c}" for c in campos),
        ]
    )
    try:
        dados, _ = chamar_json(SISTEMA, instrucao, temperatura=0.3)
    except Exception:
        return padrao

    pergunta = str(dados.get("pergunta", "")).strip()
    return pergunta or padrao
