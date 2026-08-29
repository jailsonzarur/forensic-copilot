"""Verifica a TELA da conversa pela UI real, sem API.

Regressão que motivou este arquivo: quando a referência entre coleções saiu da
conversa, a tela continuou exigindo esse campo para liberar o avanço — e o
botão nunca habilitava, mesmo com o assistente dizendo que estava tudo pronto.

    .venv/bin/python -m verificacao.tela_conversa
"""

from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parent.parent / "app.py")

#: Estado ao fim de uma conversa completa. Nenhum campo obrigatório pode faltar:
#: o avanço só libera quando a conversa capturou tudo o que ela coleta.
COLECOES = {
    "materiais": [
        {
            "massa_liquida_valor": "16,5",
            "massa_liquida_unidade": "gramas",
            "forma_fisica": "sólido",
            "coloracao": "branca",
            "acondicionamento_quantidade": "16",
            "acondicionamento_tipo": "saco plástico verde",
        }
    ],
    "exames_realizados": [
        {
            "nome_teste": "Scott",
            "item_material": "1",
            "resultado": "positivo",
            "substancia": "crack",
            "procedimento": "apliquei o reagente de Scott e observei coloração azul",
        }
    ],
}


#: Fechamento dos exames é por material: "exames_realizados:1" encerra os do
#: Material 1. Assim a conversa nunca pergunta "de qual material?".
FECHADAS_COMPLETAS = ["exames_realizados:1", "materiais"]


def _abre_veicular() -> AppTest:
    """Tela da conversa no exame veicular, com dois peritos no formulário.

    Regressão: o painel de dados administrativos indexava rótulos por chave e
    quebrava com KeyError ao topar com o grupo repetível de peritos, que não é
    um campo simples.
    """
    at = AppTest.from_file(APP, default_timeout=90)
    at.session_state["tela"] = "conversa"
    at.session_state["exame_id"] = "identificacao_veicular"
    at.session_state["admin"] = {
        "numero_demanda": "00078413-75",
        "tipo_procedimento": "BO",
        "peritos": [
            {"perito_designado": "FLÁVIO FELINTO MOURA", "matricula": "402.340-4"},
            {"perito_designado": "HAMILTON CARVALHO FORTES JÚNIOR", "matricula": "357.724-4"},
        ],
    }
    at.run()
    return at


def _abre(colecoes: dict, fechadas: list[str], quesitos: list[str] | None = None) -> AppTest:
    at = AppTest.from_file(APP, default_timeout=90)
    at.session_state["tela"] = "conversa"
    at.session_state["exame_id"] = "identificacao_substancia"
    at.session_state["admin"] = {"perito_designado": "PERITO DE TESTE"}
    at.session_state["colecoes"] = {c: [dict(i) for i in itens] for c, itens in colecoes.items()}
    at.session_state["colecoes_fechadas"] = list(fechadas)
    at.session_state["quesitos"] = list(quesitos or [])
    at.run()
    return at


def main() -> int:
    falhas: list[str] = []

    def checa(condicao: bool, descricao: str) -> None:
        if not condicao:
            falhas.append(descricao)
            print(f"    ❌ {descricao}")

    def avancar(at: AppTest):
        return next((b for b in at.button if "Avançar" in b.label), None)

    # 1. Conversa completa: o avanço tem que liberar.
    at = _abre(COLECOES, FECHADAS_COMPLETAS)
    checa(not at.exception, "a tela não pode levantar exceção")
    ultima = at.session_state["mensagens"][-1]["content"]
    print("assistente:", ultima)
    checa(
        "Tudo registrado" in ultima,
        "com tudo preenchido, o assistente devia declarar concluído",
    )
    botao = avancar(at)
    checa(botao is not None, "o botão de avanço devia existir")
    checa(
        botao is not None and not botao.disabled,
        "o assistente disse que terminou: o avanço não pode ficar travado",
    )

    # 2. O contador não conta o que a conversa não coleta.
    textos = " ".join(m.value for m in at.caption) if hasattr(at, "caption") else ""
    print("progresso:", [c.value for c in at.caption if "obrigatórios" in c.value])
    contador = [c.value for c in at.caption if "obrigatórios" in c.value]
    checa(
        bool(contador) and contador[0].split(" de ")[0] == contador[0].split(" de ")[1].split()[0],
        "com tudo preenchido, o contador devia bater",
    )

    # 3. Quesito da requisição sem resposta trava o avanço: o laudo responde ao
    #    que a autoridade perguntou, e quem responde é o perito.
    at = _abre(COLECOES, FECHADAS_COMPLETAS, quesitos=["São substâncias venenosas?"])
    ultima = at.session_state["mensagens"][-1]["content"]
    print("com quesito pendente:", ultima[:90])
    checa("Quesito 01" in ultima, "devia perguntar o quesito da requisição")
    botao = avancar(at)
    checa(
        botao is not None and botao.disabled,
        "quesito sem resposta devia travar o avanço",
    )

    # 4. Coleção ainda aberta mantém o avanço travado.
    at = _abre(COLECOES, ["exames_realizados:1"])
    botao = avancar(at)
    checa(
        botao is not None and botao.disabled,
        "com a coleção de materiais ainda aberta, o avanço deve continuar travado",
    )

    # 5. Clicar avança para a confirmação.
    at = _abre(COLECOES, FECHADAS_COMPLETAS)
    botao = avancar(at)
    if botao is not None and not botao.disabled:
        botao.click().run()
        print("tela final:", at.session_state["tela"])
        checa(at.session_state["tela"] == "confirmacao", "devia seguir para a confirmação")

    # 6. Outro tipo de exame, com grupo repetível no formulário.
    at = _abre_veicular()
    print("\nveicular — exceção:", [e.value for e in at.exception] or "(nenhuma)")
    checa(
        not at.exception,
        "o painel não pode quebrar com grupo repetível no formulário",
    )
    ultima = at.session_state["mensagens"][-1]["content"]
    checa("veículo" in ultima.lower(), "a conversa devia começar pelo veículo")

    print("\n" + "=" * 60)
    if falhas:
        print(f"{len(falhas)} FALHA(S):")
        for f in falhas:
            print(" -", f)
        return 1
    print("TELA DA CONVERSA OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
