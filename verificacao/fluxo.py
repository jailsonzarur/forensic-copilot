"""Verifica as três paredes de fidelidade sobre o agente único, sem API real.

Um stub do orquestrador devolve JSON canned por turno. O controlador da
conversa passa cada saída pelas paredes:

- ``aplicar`` — schema, opções fechadas, valor exato, valor de enfeite.
- ``ler_recusas`` — motivo em conjunto fechado, "aproximado" exige palavra de
  estimativa, trecho conferido contra a fala.
- ``valida_resumo`` — mensagem do agente afirma só o que ``aplicar`` gravou.

Este script não testa o SISTEMA_AGENTE em si (isso a fidelidade real faz, com
API). Ele garante que, dada uma saída do agente, o pipeline determinístico
mantém as garantias mesmo quando o agente devolve algo inconsistente.

    .venv/bin/python -m verificacao.fluxo
"""

from __future__ import annotations

from config.exams import obter_exame
from core import conversa, pendencias

MATERIAL_1 = {
    "massa_liquida_valor": "15",
    "massa_liquida_unidade": "gramas",
    "forma_fisica": "erva prensada",
    "coloracao": "esverdeada",
    "acondicionamento_quantidade": "2",
    "acondicionamento_tipo": "invólucros plásticos",
}


def _saida(**kwargs) -> dict:
    """Molde da saída do agente com defaults sensatos."""
    base = {
        "extracao": {},
        "encerramentos_de_colecao": [],
        "resposta_quesito": None,
        "confirmou_padrao_quesito": None,
        "recusas": [],
        "intencao": "conteudo",
        "propoe_completo": False,
        "resumo_do_registrado": [],
        "mensagem_do_assistente": "",
    }
    base.update(kwargs)
    return base


def _stub(saida: dict):
    def orquestrador(exame, colecoes, fechadas, respostas, quesitos, historico, pend, mensagem):
        return saida, "<stub>"
    return orquestrador


def main() -> int:
    exame = obter_exame("identificacao_substancia")
    colecoes: dict[str, list[dict]] = {}
    fechadas: list[str] = []
    quesitos = ["São substâncias venenosas?"]
    respostas: dict[str, str] = {}
    falhas: list[str] = []

    def passo(msg: str, saida: dict) -> conversa.Resultado:
        resultado = conversa.processar(
            exame, colecoes, fechadas, msg,
            orquestrador=_stub(_saida(**saida)),
            historico=[], quesitos=quesitos, respostas=respostas,
        )
        print(f"\n>>> {msg}")
        print(resultado.mensagem)
        return resultado

    def checa(condicao: bool, descricao: str):
        if not condicao:
            falhas.append(descricao)
            print(f"    ❌ {descricao}")

    # --- Parede 1: aplicar descarta o que não pertence ao schema.
    resultado = passo(
        "15 gramas de erva prensada esverdeada em 2 invólucros plásticos",
        {
            "extracao": {
                "materiais": [{"indice": 1, "campos": dict(MATERIAL_1, peso_bruto="30", observacoes="não informado")}],
                "inexistente": [{"indice": 1, "campos": {"x": "y"}}],
            },
            "resumo_do_registrado": [
                {"colecao": "materiais", "indice": 1, "slot": k, "valor": v}
                for k, v in MATERIAL_1.items()
            ],
            "mensagem_do_assistente": "Anotei os campos do Material 1.",
        },
    )
    item = colecoes["materiais"][0]
    checa("peso_bruto" not in item, "slot fora do schema não pode entrar")
    checa("inexistente" not in colecoes, "coleção fora do schema não pode entrar")
    checa(not item.get("observacoes"), "'não informado' não pode virar valor")
    checa(item.get("massa_liquida_valor") == "15", "valor válido devia estar gravado")
    checa(len(resultado.alteracoes) == len(MATERIAL_1), "alteracoes devia refletir só o gravado")
    checa(resultado.mensagem == "Anotei os campos do Material 1.", "mensagem do agente devia ter passado")

    # --- Parede 3: valida_resumo detecta afirmação de gravação inexistente.
    resultado = passo(
        "positivo pra maconha, análise botânica",
        {
            "extracao": {
                "exames_realizados": [{"indice": 1, "campos": {
                    "nome_teste": "Análise botânica",
                    "resultado": "positivo",
                    "substancia": "maconha",
                    "item_material": "1",
                }}],
            },
            # O agente MENTE aqui: afirma ter gravado massa=20, que nem está na extração.
            "resumo_do_registrado": [
                {"colecao": "materiais", "indice": 1, "slot": "massa_liquida_valor", "valor": "20"},
            ],
            "mensagem_do_assistente": "Anotei massa 20 g e análise botânica.",
        },
    )
    checa(
        "Anotei massa 20 g" not in resultado.mensagem,
        "mensagem alucinada não pode ir ao perito — deveria cair no fallback",
    )
    checa(
        resultado.mensagem.startswith("Anotei:"),
        "fallback determinístico deveria compor a mensagem a partir das alteracoes reais",
    )
    checa(
        colecoes["exames_realizados"][0].get("nome_teste") == "Análise botânica",
        "extração legítima ainda tem que ser gravada, mesmo com resumo inconsistente",
    )

    # --- Parede 1: opção fora do conjunto fechado é descartada.
    resultado = passo(
        "o resultado foi 'deu certo'",
        {
            "extracao": {"exames_realizados": [{"indice": 1, "campos": {"resultado": "deu certo"}}]},
            "resumo_do_registrado": [],
            "mensagem_do_assistente": "Não peguei o resultado. Foi positivo, negativo ou inconclusivo?",
        },
    )
    checa(
        colecoes["exames_realizados"][0].get("resultado") == "positivo",
        "resultado inválido não pode sobrescrever o positivo já gravado",
    )
    checa(len(resultado.alteracoes) == 0, "sem alteração — 'deu certo' não é do conjunto fechado")

    # --- Parede 2: recusa "aproximado" só passa se a fala trouxer estimativa.
    resultado = passo(
        "1,2 kg",  # NÃO é estimativa — número exato
        {
            "extracao": {},
            "recusas": [{
                "motivo": "aproximado",
                "colecao": "materiais",
                "slot": "massa_liquida_valor",
                "trecho": "1,2 kg",
            }],
            "resumo_do_registrado": [],
            "mensagem_do_assistente": "Não entendi a massa direito, me diz o valor exato.",
        },
    )
    checa(
        not any(r.motivo == "aproximado" for r in resultado.recusas),
        "recusa 'aproximado' sem palavra de estimativa na fala tem que ser descartada",
    )

    # --- Encerramento de coleção pelo token do agente.
    resultado = passo(
        "não, só isso",
        {
            "extracao": {},
            "encerramentos_de_colecao": ["exames_realizados:1", "materiais"],
            "intencao": "encerrar",
            "resumo_do_registrado": [],
            "mensagem_do_assistente": "Ok, encerrei os exames do Material 1 e os materiais.",
        },
    )
    checa("exames_realizados:1" in fechadas, "encerramento vinculado do agente devia entrar em fechadas")
    checa("materiais" in fechadas, "encerramento de materiais devia entrar em fechadas")

    # --- Confirmação de padrão de quesito.
    resultado = passo(
        "confirmo",
        {
            "extracao": {},
            "confirmou_padrao_quesito": "01",
            "intencao": "confirmar",
            "resumo_do_registrado": [],
            "mensagem_do_assistente": "Quesito 01 respondido.",
        },
    )
    from core.quesitos import PADRAO_ACEITO
    checa(respostas.get("01") == PADRAO_ACEITO, "confirmação do padrão devia ser gravada como marca")

    # --- propoe_completo é sinal, não gate: a regra é quem libera.
    resultado = passo(
        "acho que tá tudo",
        {
            "extracao": {},
            "propoe_completo": True,
            "intencao": "conteudo",
            "resumo_do_registrado": [],
            "mensagem_do_assistente": "Fechado então.",
        },
    )
    checa(resultado.propoe_completo, "sinal do agente devia ser propagado no Resultado")
    faltando = pendencias.todas(exame, colecoes, so_conversa=True)
    print(f"\nainda pendente (regra): {[p.rotulo() for p in faltando] or '(nada)'}")

    print("\n" + "=" * 60)
    if falhas:
        print(f"{len(falhas)} FALHA(S):")
        for f in falhas:
            print(" -", f)
        return 1
    print("FLUXO OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
