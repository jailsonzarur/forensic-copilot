"""Verifica a biblioteca de redação institucional (sem API).

O ponto: texto que falta vira PENDENTE visível; texto escrito por perito é
reaproveitado; e nada entra sem autoria registrada.

    .venv/bin/python -m verificacao.biblioteca
"""

from __future__ import annotations

from core import biblioteca, derivados

COLECOES = {
    "materiais": [{"forma_fisica": "pedra"}],
    "exames_realizados": [
        {
            "nome_teste": "Ensaio de Scott Modificado",
            "item_material": "1",
            "resultado": "positivo",
            "substancia": "substância fictícia de teste",
        }
    ],
}
SUBSTANCIA = "substância fictícia de teste"
ENSAIO = "Ensaio de Scott Modificado"


def main() -> int:
    falhas: list[str] = []

    def checa(condicao: bool, descricao: str) -> None:
        if not condicao:
            falhas.append(descricao)
            print(f"    ❌ {descricao}")

    chaves = (
        ("resultado", biblioteca.chave(ENSAIO, SUBSTANCIA)),
        ("proscricao", biblioteca.chave(SUBSTANCIA)),
        ("natureza", biblioteca.chave(SUBSTANCIA)),
    )
    for tipo, identificador in chaves:
        biblioteca.remover(tipo, identificador)

    try:
        # 1. Sem redação, tudo vira pendência visível.
        checa(
            "[PENDENTE:" in derivados.resultados_obtidos(COLECOES)[0]["texto"],
            "ensaio sem redação devia virar pendência na seção 4",
        )
        checa("[PENDENTE:" in derivados.natureza(COLECOES), "quesito 01 devia ficar pendente")
        checa("[PENDENTE:" in derivados.proscricao(COLECOES), "quesito 03 devia ficar pendente")

        # 2. Escrita pelo perito, a redação passa a ser usada.
        biblioteca.salvar(
            "resultado",
            chaves[0][1],
            {"titulo": "Análise por ensaio de teste", "texto": "Parágrafo de teste."},
            autor="Perito de Teste",
        )
        biblioteca.salvar(
            "proscricao", chaves[1][1], {"texto": "Texto legal de teste."}, "Perito de Teste"
        )
        biblioteca.salvar(
            "natureza",
            chaves[2][1],
            {"texto": "A substância {forma} é de teste."},
            "Perito de Teste",
        )

        secao = derivados.resultados_obtidos(COLECOES)[0]
        print("seção 4:", secao["titulo"], "::", secao["texto"])
        print("quesito 01:", derivados.natureza(COLECOES))
        print("quesito 03:", derivados.proscricao(COLECOES))

        checa(secao["texto"] == "Parágrafo de teste.", "a redação salva devia ser usada")
        checa(secao["titulo"] == "Análise por ensaio de teste", "o título salvo devia ser usado")
        checa(
            derivados.natureza(COLECOES) == "A substância pedra é de teste.",
            "a construção salva devia receber a forma do material",
        )
        checa(
            derivados.proscricao(COLECOES) == "Texto legal de teste.",
            "o texto legal salvo devia ser usado",
        )

        # 3. Autoria é obrigatória no registro.
        entrada = biblioteca.buscar("resultado", chaves[0][1])
        print("autoria:", entrada.get("autor"), "|", entrada.get("em"))
        checa(bool(entrada.get("autor")), "toda entrada precisa de autor registrado")
        checa(bool(entrada.get("em")), "toda entrada precisa de data")

        # 4. A busca não depende de caixa nem de acento.
        checa(
            biblioteca.buscar("resultado", biblioteca.chave("ENSAIO DE SCOTT MODIFICADO", SUBSTANCIA.upper()))
            is not None,
            "a chave devia ser insensível a caixa e acento",
        )
    finally:
        for tipo, identificador in chaves:
            biblioteca.remover(tipo, identificador)

    checa(
        "[PENDENTE:" in derivados.resultados_obtidos(COLECOES)[0]["texto"],
        "removida a entrada, a pendência devia voltar",
    )

    print("\n" + "=" * 60)
    if falhas:
        print(f"{len(falhas)} FALHA(S):")
        for f in falhas:
            print(" -", f)
        return 1
    print("BIBLIOTECA OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
