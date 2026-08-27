"""Verifica a TELA da requisição pela UI real, sem OCR e sem API.

A leitura já é testada em `verificacao.requisicao`; aqui o que interessa é a
tela: o que ela propõe, o que ela deixa vazio, e o que ela grava na sessão
quando o perito confirma.

    .venv/bin/python -m verificacao.tela_requisicao
"""

from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest

from core import requisicao as leitor
from templates.identificacao_substancia.boilerplate import QUESITOS_DA_REQUISICAO_MODELO

APP = str(Path(__file__).resolve().parent.parent / "app.py")

QUESITOS_LIDOS = [
    "Qual a natureza do material apresentado a exame?",
    "",  # o OCR oscilou neste: a tela tem que deixar em branco para transcrever
    "São substâncias venenosas?",
]


def _leitura() -> leitor.Leitura:
    return leitor.Leitura(
        texto="Ofício n.º 152/2019-DRO ... quesitos ...",
        origem="OCR do documento digitalizado",
        nivel="ocr",
        rotacoes=[90],
        campos={"documento_solicitacao": "Ofício n.º 152/2019-DRO"},
        trechos={"documento_solicitacao": "Ofício n.º 152/2019-DRO"},
        quesitos=list(QUESITOS_LIDOS),
        incertos=["o quesito 02"],
        itens_declarados=[{"quantidade": "2", "texto": "trouxinhas de substância vegetal"}],
    )


def _abre(com_leitura: bool = True) -> AppTest:
    at = AppTest.from_file(APP, default_timeout=90)
    at.session_state["tela"] = "requisicao"
    at.session_state["exame_id"] = "identificacao_substancia"
    if com_leitura:
        at.session_state["leitura_requisicao"] = _leitura()
    at.run()
    return at


def main() -> int:
    falhas: list[str] = []

    def checa(condicao: bool, descricao: str) -> None:
        if not condicao:
            falhas.append(descricao)
            print(f"    ❌ {descricao}")

    def botao(at: AppTest, texto: str):
        return next((b for b in at.button if texto in b.label), None)

    # 1. Sem documento, dá para seguir na mão com os quesitos modelo.
    at = _abre(com_leitura=False)
    checa(not at.exception, "a tela sem leitura não pode levantar exceção")
    manual = botao(at, "Preencher na mão")
    checa(manual is not None, "devia oferecer o caminho sem anexo")
    if manual:
        manual.click().run()
        checa(at.session_state["tela"] == "admin", "devia seguir para o formulário")
        checa(
            at.session_state["quesitos"] == list(QUESITOS_DA_REQUISICAO_MODELO),
            "sem requisição, os quesitos entram como o conjunto modelo",
        )

    # 2. Com leitura por OCR: aviso de confiança, campos propostos, incertos à vista.
    at = _abre()
    checa(not at.exception, "a tela com leitura não pode levantar exceção")
    avisos = " ".join(w.value for w in at.warning)
    print("avisos:", avisos[:110])
    checa("OCR" in avisos, "devia avisar que a leitura veio de OCR")
    checa("90°" in avisos, "devia dizer que endireitou a página")
    checa(
        any("quesito 02" in w.value for w in at.warning),
        "o que oscilou entre leituras devia aparecer como incerto",
    )
    checa(not any(s.value for s in at.success), "OCR não pode ser anunciado como exato")

    campo = at.text_input(key="req_campo_documento_solicitacao")
    print("campo proposto:", repr(campo.value))
    checa(campo.value == "Ofício n.º 152/2019-DRO", "o campo lido devia vir preenchido")

    caixas = [t for t in at.text_area if t.key and t.key.startswith("req_quesito_")]
    print("quesitos na tela:", [t.value for t in caixas])
    checa(len(caixas) == 3, "devia render um campo por quesito lido")
    checa(caixas[1].value == "", "quesito instável devia ficar em branco para transcrever")

    # 3. Confirmar grava campos e quesitos na sessão, sem o vazio.
    seguir = botao(at, "Confirmar e seguir")
    checa(seguir is not None and not seguir.disabled, "com quesitos, devia liberar")
    if seguir:
        seguir.click().run()
        print("admin gravado:", at.session_state["admin"])
        print("quesitos gravados:", at.session_state["quesitos"])
        checa(
            at.session_state["admin"].get("documento_solicitacao") == "Ofício n.º 152/2019-DRO",
            "o campo confirmado devia ir para o formulário",
        )
        checa(
            at.session_state["quesitos"] == [QUESITOS_LIDOS[0], QUESITOS_LIDOS[2]],
            "quesito em branco não pode entrar na lista",
        )
        checa(
            at.session_state["requisicao"]["itens_declarados"],
            "o declarado pela autoridade devia ser guardado para a conferência",
        )
        checa(at.session_state["tela"] == "admin", "devia seguir para o formulário")

    # 4. Sem nenhum quesito transcrito, não dá para seguir.
    at = _abre()
    for indice in range(1, 4):
        at.text_area(key=f"req_quesito_{indice}").set_value("").run()
    seguir = botao(at, "Confirmar e seguir")
    checa(
        seguir is not None and seguir.disabled,
        "sem quesito nenhum, o avanço devia ficar bloqueado",
    )

    print("\n" + "=" * 60)
    if falhas:
        print(f"{len(falhas)} FALHA(S):")
        for f in falhas:
            print(" -", f)
        return 1
    print("TELA DA REQUISIÇÃO OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
