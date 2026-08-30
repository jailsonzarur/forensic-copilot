"""Verifica que o laudo sobrevive a fechar a aba, pela UI real.

O cenário que este roteiro reproduz é o da rede caindo em campo: o perito
ditou material e exames, a aba morre, ele reabre a ferramenta e precisa
encontrar o laudo como deixou — inclusive as fotos e as respostas dos quesitos.

Também exerce o que não pode acontecer: rascunho salvo antes de escolher o tipo
de exame, arquivo corrompido derrubando a tela, e "Novo laudo" apagando o que
estava salvo.

    .venv/bin/python -m verificacao.persistencia
"""

from __future__ import annotations

import base64
import os
import shutil
import tempfile
from pathlib import Path

# Antes de importar qualquer coisa que leia a pasta: os rascunhos deste roteiro
# vão para um diretório temporário, nunca para os laudos reais de quem roda.
_TEMPORARIA = Path(tempfile.mkdtemp(prefix="forensic-rascunhos-"))
os.environ["FORENSIC_RASCUNHOS"] = str(_TEMPORARIA)

from streamlit.testing.v1 import AppTest  # noqa: E402

from core import persistencia  # noqa: E402

APP = str(Path(__file__).resolve().parent.parent / "app.py")

PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAE"
    "hQGAhKmMIQAAAABJRU5ErkJggg=="
)

ADMIN = {
    "numero_laudo": "SB 0001/2026",
    "numero_demanda": "00099999-99",
    "orgao_solicitante": "1º DP de Teresina/PI",
    "envolvido": "FULANO DE TAL",
    "perito_designado": "PERITO DE TESTE",
    "matricula": "123456-7",
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
        }
    ],
    "exames_realizados": [
        {
            "nome_teste": "Análise botânica",
            "resultado": "positivo",
            "substancia": "Cannabis sativa L.",
            "item_material": "1",
        }
    ],
}


def main() -> int:
    falhas: list[str] = []
    criados: list[str] = []

    def checa(condicao: bool, descricao: str) -> None:
        if not condicao:
            falhas.append(descricao)
            print(f"    ❌ {descricao}")

    print("rascunhos deste teste em:", _TEMPORARIA)
    try:
        # 1. Antes de escolher o exame, nada é gravado.
        at = AppTest.from_file(APP, default_timeout=120)
        at.run()
        checa(not at.exception, f"tela inicial quebrou: {at.exception}")
        checa(
            not persistencia.listar(),
            "sem tipo de exame escolhido, não devia existir rascunho",
        )

        # 2. Sessão de trabalho: o perito dita, e o laudo é salvo sozinho.
        at = AppTest.from_file(APP, default_timeout=120)
        at.session_state["tela"] = "confirmacao"
        at.session_state["exame_id"] = "identificacao_substancia"
        at.session_state["admin"] = dict(ADMIN)
        at.session_state["colecoes"] = {
            chave: [dict(i) for i in itens] for chave, itens in COLECOES.items()
        }
        at.session_state["colecoes_fechadas"] = ["materiais", "exames_realizados"]
        at.session_state["quesitos"] = ["São substâncias venenosas?"]
        at.session_state["respostas_quesitos"] = {"01": "Sim, conforme item 5."}
        at.session_state["mensagens"] = [
            {"role": "assistant", "content": "Vamos anotar esse exame."},
            {"role": "user", "content": "15,3 g de erva prensada esverdeada"},
        ]
        at.session_state["imagens"] = [
            {
                "assinatura": "b" * 64,
                "nome": "material.png",
                "dados": PNG,
                "material": 1,
                "legenda": "Foto do material periciado",
            }
        ]
        at.run()
        checa(not at.exception, f"tela de confirmação quebrou: {at.exception}")

        laudo_id = at.session_state["laudo_id"]
        criados.append(laudo_id)
        salvos = persistencia.listar()
        print("rascunhos após a sessão:", [(r.rotulo, r.campos_preenchidos) for r in salvos])
        checa(len(salvos) == 1, "o laudo devia ter sido salvo sozinho, sem o perito pedir")
        if salvos:
            checa(
                salvos[0].rotulo == "SB 0001/2026",
                "o rascunho devia ser reconhecível pelo número do laudo",
            )
            checa(
                salvos[0].campos_preenchidos > 10,
                "a lista devia mostrar quanto do laudo já está preenchido",
            )

        # 3. A aba morre. Nova sessão: o laudo tem que voltar inteiro.
        nova = AppTest.from_file(APP, default_timeout=120)
        nova.run()
        checa(not nova.exception, f"tela de seleção quebrou: {nova.exception}")
        continuar = [b for b in nova.button if b.key == f"retomar_{laudo_id}"]
        checa(bool(continuar), "a tela de seleção devia oferecer o rascunho para continuar")
        if continuar:
            continuar[0].click().run()
            checa(not nova.exception, f"retomar quebrou: {nova.exception}")

            recuperado = nova.session_state
            print("retomado em:", recuperado["tela"])
            checa(
                recuperado["admin"].get("numero_laudo") == "SB 0001/2026",
                "os dados administrativos deviam voltar",
            )
            checa(
                recuperado["colecoes"]["materiais"][0].get("massa_liquida_valor") == "15,3",
                "a massa ditada pelo perito devia voltar exatamente como ele disse",
            )
            checa(
                recuperado["colecoes"]["exames_realizados"][0].get("substancia")
                == "Cannabis sativa L.",
                "o exame e a substância deviam voltar",
            )
            checa(
                recuperado["respostas_quesitos"].get("01") == "Sim, conforme item 5.",
                "a resposta do quesito devia voltar",
            )
            checa(
                len(recuperado["mensagens"]) == 2,
                "o histórico da conversa devia voltar, para o agente saber onde parou",
            )
            imagens = recuperado["imagens"] or []
            checa(len(imagens) == 1, "a foto anexada devia voltar")
            if imagens:
                checa(imagens[0]["dados"] == PNG, "os bytes da foto deviam voltar intactos")
                checa(
                    imagens[0]["legenda"] == "Foto do material periciado",
                    "a legenda escrita pelo perito devia voltar",
                )
            checa(
                recuperado["laudo_id"] == laudo_id,
                "continuar o rascunho não pode criar um laudo novo",
            )
            checa(
                len(persistencia.listar()) == 1,
                "retomar não podia duplicar o rascunho",
            )

        # 4. "Novo laudo" não apaga o que estava salvo.
        outro = AppTest.from_file(APP, default_timeout=120)
        outro.session_state["exame_id"] = "identificacao_substancia"
        outro.session_state["admin"] = {"numero_laudo": "SB 0002/2026"}
        outro.run()
        criados.append(outro.session_state["laudo_id"])
        novos = [b for b in outro.sidebar.button if "Novo laudo" in b.label]
        if novos:
            novos[0].click().run()
            checa(
                len(persistencia.listar()) >= 1,
                "abrir um laudo novo não pode apagar os rascunhos salvos",
            )

        # 5. Arquivo danificado não derruba a tela.
        quebrado = persistencia.pasta_base() / "danificado"
        quebrado.mkdir(parents=True, exist_ok=True)
        (quebrado / "laudo.json").write_text("{ isto não é json", encoding="utf-8")
        checa(
            persistencia.carregar("danificado") is None,
            "rascunho ilegível devia devolver None, não explodir",
        )
        at = AppTest.from_file(APP, default_timeout=120)
        at.run()
        checa(not at.exception, f"rascunho danificado derrubou a tela: {at.exception}")

        # 6. Descartar apaga o laudo e as fotos.
        if criados:
            persistencia.descartar(criados[0])
            checa(
                not (persistencia.pasta_base() / criados[0]).exists(),
                "descartar devia apagar a pasta do rascunho, com as fotos",
            )

        print("\n" + "=" * 60)
        if falhas:
            print(f"{len(falhas)} FALHA(S):")
            for f in falhas:
                print(" -", f)
            return 1
        print("PERSISTÊNCIA OK — o laudo sobrevive a fechar a aba")
        return 0
    finally:
        shutil.rmtree(_TEMPORARIA, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
