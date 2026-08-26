"""Verifica a tela de confirmação pela UI real, sem gastar chamadas de API.

O estado da camada 1 é injetado direto no ``session_state``, como se a conversa
já tivesse acontecido. O que interessa aqui é o comportamento da revisão: campo
obrigatório apagado bloqueia, derivado intocado acompanha os dados, texto escrito
pelo perito não é sobrescrito, e a imagem entra como anexo com legenda montada.

    .venv/bin/python -m verificacao.confirmacao
"""

from __future__ import annotations

import base64
import hashlib
from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parent.parent / "app.py")

#: PNG 1x1, só para exercitar o anexo.
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAE"
    "hQGAhKmMIQAAAABJRU5ErkJggg=="
)

ADMIN = {
    "data_exame": "2026-08-25",
    "orgao_solicitante": "1º DP de Teresina/PI",
    "documento_solicitacao": "Ofício 412/2026",
    "tipo_procedimento": "IP",
    "numero_procedimento": "087/2026",
    "envolvido": "FULANO DE TAL",
    "perito_designado": "PERITO DE TESTE",
    "matricula": "123456-7",
    "numero_demanda": "",
    "protocolo_sbs": "",
}

COLECOES = {
    "materiais": [
        {
            "massa_liquida_valor": "15,3",
            "massa_liquida_unidade": "g",
            "forma_fisica": "erva prensada",
            "coloracao": "esverdeada",
            "acondicionamento_quantidade": "3",
            "acondicionamento_tipo": "invólucros plásticos",
        },
        {
            "massa_liquida_valor": "1,2",
            "massa_liquida_unidade": "kg",
            "forma_fisica": "tablete",
            "coloracao": "branco",
            "acondicionamento_quantidade": "1",
            "acondicionamento_tipo": "papel alumínio",
        },
    ],
    "exames_realizados": [
        {"nome_teste": "Fast Blue B", "item_material": "1", "resultado": "positivo", "substancia": "THC"},
        {"nome_teste": "Scott", "item_material": "2", "resultado": "positivo", "substancia": "cocaína"},
    ],
}


def _abre(com_imagem: bool = False) -> AppTest:
    at = AppTest.from_file(APP, default_timeout=90)
    at.session_state["tela"] = "confirmacao"
    at.session_state["exame_id"] = "identificacao_substancia"
    at.session_state["admin"] = dict(ADMIN)
    at.session_state["colecoes"] = {
        chave: [dict(item) for item in itens] for chave, itens in COLECOES.items()
    }
    at.session_state["colecoes_fechadas"] = ["materiais", "exames_realizados"]
    if com_imagem:
        at.session_state["imagens"] = [
            {
                "assinatura": hashlib.sha256(PNG).hexdigest(),
                "nome": "foto.png",
                "dados": PNG,
                "material": 1,
                "legenda": "",
            }
        ]
    at.run()
    return at


def main() -> int:
    falhas: list[str] = []

    def checa(condicao: bool, descricao: str) -> None:
        if not condicao:
            falhas.append(descricao)
            print(f"    ❌ {descricao}")

    def confirmar(at: AppTest):
        return next((b for b in at.button if "Confirmar" in b.label), None)

    at = _abre()
    checa(not at.exception, "a tela não pode levantar exceção")
    print("conclusão derivada:", repr(at.session_state["derivados"].get("conclusao")))
    checa(
        at.session_state["derivados"].get("conclusao") == "POSITIVO para THC e cocaína.",
        "conclusão devia sair dos resultados positivos",
    )
    checa(not at.error, "schema completo não devia ter impedimento")
    checa(confirmar(at) is not None and not confirmar(at).disabled, "devia liberar o avanço")

    # Derivado intocado acompanha a camada 1.
    at.text_input(key="conf_exames_realizados_1_substancia").set_value("Cannabis sativa L.").run()
    print("após editar a substância:", repr(at.session_state["derivados"]["conclusao"]))
    checa(
        at.session_state["derivados"]["conclusao"] == "POSITIVO para Cannabis sativa L. e cocaína.",
        "derivado intocado devia acompanhar a camada 1",
    )

    # Obrigatório apagado bloqueia; restaurado libera.
    at.text_input(key="conf_materiais_1_coloracao").set_value("").run()
    checa(bool(at.error), "campo obrigatório vazio devia bloquear")
    checa(confirmar(at) is not None and confirmar(at).disabled, "botão devia ficar desabilitado")
    at.text_input(key="conf_materiais_1_coloracao").set_value("esverdeada").run()
    checa(not at.error and not confirmar(at).disabled, "restaurar o campo devia liberar")

    # Texto do perito manda sobre a regra.
    escrito = "POSITIVO para maconha e cocaína, conforme item 3."
    at.text_area(key="derivado_conclusao").set_value(escrito).run()
    at.text_input(key="conf_exames_realizados_2_substancia").set_value("cloridrato de cocaína").run()
    print("conclusão do perito:", repr(at.session_state["derivados"]["conclusao"]))
    checa(
        at.session_state["derivados"]["conclusao"] == escrito,
        "texto do perito não pode ser sobrescrito pela regra",
    )
    recalcular = [b for b in at.button if "Recalcular" in b.label]
    checa(bool(recalcular), "divergência devia oferecer o recálculo")
    if recalcular:
        recalcular[0].click().run()
        print("após recalcular:", repr(at.session_state["derivados"]["conclusao"]))
        checa(not at.exception, "recalcular não pode levantar exceção de session_state")
        checa(
            at.session_state["derivados"]["conclusao"]
            == "POSITIVO para Cannabis sativa L. e cloridrato de cocaína.",
            "recalcular devia usar os dados atuais",
        )

    botao = confirmar(at)
    if botao is not None:
        botao.click().run()
    print("tela final:", at.session_state["tela"])
    checa(at.session_state["tela"] == "documento", "confirmar devia avançar para o documento")

    # Imagem: anexo com legenda montada dos campos do perito.
    at = _abre(com_imagem=True)
    checa(not at.exception, "a tela com imagem não pode levantar exceção")
    legendas = [t for t in at.text_area if t.key and t.key.startswith("legenda_")]
    checa(len(legendas) == 1, "a imagem anexada devia ter uma legenda")
    if legendas:
        print("legenda sugerida:", repr(legendas[0].value))
        checa(
            legendas[0].value
            == "Imagem 01: Fotografia do material 1 — erva prensada, esverdeada, 3 invólucros plásticos.",
            "legenda devia sair dos campos informados pelo perito",
        )
    checa(
        any("Remover imagem" in b.label for b in at.button),
        "devia dar para remover a imagem anexada",
    )

    print("\n" + "=" * 60)
    if falhas:
        print(f"{len(falhas)} FALHA(S):")
        for f in falhas:
            print(" -", f)
        return 1
    print("CONFIRMAÇÃO OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
