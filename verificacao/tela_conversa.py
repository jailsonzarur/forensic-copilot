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

#: Exatamente o estado ao fim de uma conversa completa: a referência de material
#: NÃO está preenchida, porque quem a escolhe é o perito na confirmação.
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
            "resultado": "positivo",
            "substancia": "crack",
            "procedimento": "apliquei o reagente de Scott e observei coloração azul",
        }
    ],
}


def _abre(colecoes: dict, fechadas: list[str]) -> AppTest:
    at = AppTest.from_file(APP, default_timeout=90)
    at.session_state["tela"] = "conversa"
    at.session_state["exame_id"] = "identificacao_substancia"
    at.session_state["admin"] = {"perito_designado": "PERITO DE TESTE"}
    at.session_state["colecoes"] = {c: [dict(i) for i in itens] for c, itens in colecoes.items()}
    at.session_state["colecoes_fechadas"] = list(fechadas)
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
    at = _abre(COLECOES, ["materiais", "exames_realizados"])
    checa(not at.exception, "a tela não pode levantar exceção")
    ultima = at.session_state["mensagens"][-1]["content"]
    print("assistente:", ultima)
    checa(
        "Todos os campos obrigatórios foram informados" in ultima,
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
    checa(
        any("10 de 10" in c.value for c in at.caption if "obrigatórios" in c.value),
        "o contador devia considerar só o que a conversa coleta",
    )

    # 3. Coleção ainda aberta mantém o avanço travado.
    at = _abre(COLECOES, ["materiais"])
    botao = avancar(at)
    checa(
        botao is not None and botao.disabled,
        "com exame ainda em aberto, o avanço deve continuar travado",
    )

    # 4. Clicar avança para a confirmação.
    at = _abre(COLECOES, ["materiais", "exames_realizados"])
    botao = avancar(at)
    if botao is not None and not botao.disabled:
        botao.click().run()
        print("tela final:", at.session_state["tela"])
        checa(at.session_state["tela"] == "confirmacao", "devia seguir para a confirmação")

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
