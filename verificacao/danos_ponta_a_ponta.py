"""Percorre um laudo de danos pela UI real: conversa, confirmação e minuta.

O que os outros roteiros não cobrem: as TELAS com um tipo de exame que não é o
de substância. É aqui que apareciam os acoplamentos — quesito de substância
carregado num laudo de danos, seletor dizendo "Material 1" onde é "Local 1",
legenda com marcador cru.

Não gasta chamada de API: o agente da conversa é substituído por um dublê que
devolve a extração já pronta.

    .venv/bin/python -m verificacao.danos_ponta_a_ponta
"""

from __future__ import annotations

import base64
from pathlib import Path

import os as _os
import tempfile as _tempfile

# Este roteiro abre o app de verdade, e o app salva rascunho sozinho. Sem isto,
# rodar a verificação encheria a lista de laudos do perito com dados de teste.
_os.environ.setdefault(
    "FORENSIC_RASCUNHOS", _tempfile.mkdtemp(prefix="forensic-rascunhos-")
)

from streamlit.testing.v1 import AppTest

from templates.identificacao_danos.boilerplate import QUESITOS_DA_REQUISICAO_MODELO
from verificacao.danos import CELA_ADMIN, CELA_DANOS, CELA_LOCAL

APP = str(Path(__file__).resolve().parent.parent / "app.py")

PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAE"
    "hQGAhKmMIQAAAABJRU5ErkJggg=="
)


def _abre(tela: str, com_imagem: bool = False) -> AppTest:
    at = AppTest.from_file(APP, default_timeout=120)
    at.session_state["tela"] = tela
    at.session_state["exame_id"] = "verificacao_danos"
    at.session_state["admin"] = dict(CELA_ADMIN)
    at.session_state["colecoes"] = {
        "locais": [dict(CELA_LOCAL)],
        "danos": [{"descricao": d, "item_material": "1"} for d in CELA_DANOS],
    }
    at.session_state["colecoes_fechadas"] = ["locais", "danos:1"]
    at.session_state["quesitos"] = list(QUESITOS_DA_REQUISICAO_MODELO)
    at.session_state["respostas_quesitos"] = {
        "01": "sim",
        "02": "compatíveis com aqueles produzidos por meio de força física direta",
        "03": "danos materiais",
        "04": "__padrão__",
        "05": "__padrão__",
        "06": "__padrão__",
    }
    at.session_state["requisicao"] = {"origem": "não anexada", "texto": ""}
    if com_imagem:
        at.session_state["imagens"] = [
            {
                "assinatura": "a" * 64,
                "nome": "cela.png",
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

    # 1. Seleção lista o novo tipo.
    at = AppTest.from_file(APP, default_timeout=120)
    at.run()
    rotulos = " ".join(str(o) for r in at.radio for o in r.options) if at.radio else ""
    rotulos += " ".join(str(o) for s in at.selectbox for o in s.options) if at.selectbox else ""
    checa(not at.exception, f"tela de seleção quebrou: {at.exception}")
    print("seleção:", "Verificação de Danos ofertada" if "Danos" in rotulos else rotulos[:80])

    # 2. Requisição sem anexo tem que propor os quesitos de DANOS.
    at = AppTest.from_file(APP, default_timeout=120)
    at.session_state["tela"] = "requisicao"
    at.session_state["exame_id"] = "verificacao_danos"
    at.run()
    checa(not at.exception, f"tela de requisição quebrou: {at.exception}")
    manual = [b for b in at.button if "mão" in b.label.lower()]
    if manual:
        manual[0].click().run()
        propostos = at.session_state["quesitos"]
        print("quesitos propostos:", propostos[:2], "...")
        checa(
            propostos and propostos[0] == "Houve dano(s)?",
            "sem anexo, os quesitos propostos deviam ser os de DANOS, não os de substância",
        )
        checa(
            not any("substância" in q.lower() or "material apresentado" in q.lower() for q in propostos),
            "quesito de substância vazou para um laudo de danos",
        )
    else:
        checa(False, "botão de preencher sem anexar não apareceu")

    # 3. Conversa abre na etapa 1 do laudo de danos.
    at = AppTest.from_file(APP, default_timeout=120)
    at.session_state["tela"] = "conversa"
    at.session_state["exame_id"] = "verificacao_danos"
    at.session_state["admin"] = dict(CELA_ADMIN)
    at.session_state["colecoes"] = {"locais": [], "danos": []}
    at.run()
    if at.exception:
        checa(False, f"tela de conversa quebrou: {at.exception}")
    else:
        abertura = " ".join(m["content"] for m in at.session_state["mensagens"])
        print("abertura:", abertura.split("\n")[-1][:90])
        checa(
            "Local examinado" in abertura,
            "a abertura devia anunciar a etapa 1 do laudo de danos",
        )

    # 4. Confirmação: rótulos e legenda do tipo certo.
    at = _abre("confirmacao", com_imagem=True)
    checa(not at.exception, f"tela de confirmação quebrou: {at.exception}")
    if not at.exception:
        legendas = [t for t in at.text_area if t.label == "Legenda"]
        if legendas:
            print("legenda sugerida:", repr(legendas[0].value))
            checa(
                legendas[0].value == "IMAGEM 01: ",
                "a legenda devia numerar a imagem e deixar a descrição ao perito",
            )
            checa(
                "{" not in legendas[0].value,
                "a legenda não pode sair com marcador cru do template",
            )
        else:
            checa(False, "campo de legenda não apareceu")

        seletores = [s for s in at.selectbox if "Local examinado" in s.label]
        if seletores:
            mostradas = [str(o) for o in seletores[0].options]
            print("seletor de referência:", mostradas)
            checa(
                not any("Material" in o for o in mostradas),
                "o seletor devia dizer 'Local N', não 'Material N'",
            )

        derivados = at.session_state["derivados"]
        rotulos_derivados = [d for d in derivados]
        print("derivados montados:", rotulos_derivados)

    # 5. Minuta gerada, com a prévia falando a língua do laudo de danos.
    at = _abre("documento", com_imagem=True)
    checa(not at.exception, f"tela do documento quebrou: {at.exception}")
    if not at.exception:
        # A prévia é um resumo do que foi para o .docx, não o documento inteiro.
        resumo = " ".join(str(m.value) for m in at.markdown)
        print("prévia menciona:", [t for t in ("Locais examinados", "Materiais") if t in resumo])
        checa(
            "Locais examinados" in resumo,
            "a prévia devia listar 'Locais examinados', não 'Materiais'",
        )
        checa(
            "Materiais" not in resumo,
            "rótulo de laudo de substância vazou para a prévia do laudo de danos",
        )
        downloads = at.get("download_button")
        print("botões de download:", len(downloads))
        checa(bool(downloads), "a minuta devia oferecer o download do .docx")

    # 6. Nenhum campo derivado de substância aparece num laudo de danos.
    at = _abre("confirmacao")
    if not at.exception:
        chaves = list(at.session_state["derivados"])
        print("derivados do laudo de danos:", chaves)
        for fantasma in ("natureza", "proscricao", "exames_realizados_texto"):
            checa(
                fantasma not in chaves,
                f"campo derivado '{fantasma}' é do laudo de substância e não cabe aqui",
            )

    print("\n" + "=" * 60)
    if falhas:
        print(f"{len(falhas)} FALHA(S):")
        for f in falhas:
            print(" -", f)
        return 1
    print("DANOS PONTA A PONTA OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
