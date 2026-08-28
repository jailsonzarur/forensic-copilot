"""Verifica a base de referências da seção 6 (sem API).

O ponto: a seção 6 cita o que embasa ESTE exame, e nada entra sem confirmação.
Citação é onde um modelo de linguagem mais erra, e citação falsa num laudo
assinado é pior que referência faltando.

    .venv/bin/python -m verificacao.referencias
"""

from __future__ import annotations

from core import derivados, referencias

CANNABIS_E_COCAINA = {
    "exames_realizados": [
        {"resultado": "positivo", "substancia": "Cannabis sativa L.", "nome_teste": "Análise botânica"},
        {"resultado": "positivo", "substancia": "cocaína", "nome_teste": "CCD"},
    ]
}
SO_COCAINA = {
    "exames_realizados": [
        {"resultado": "positivo", "substancia": "cocaína", "nome_teste": "CCD"},
    ]
}
SUBSTANCIA_NOVA = {
    "exames_realizados": [
        {"resultado": "positivo", "substancia": "crack", "nome_teste": "Scott"},
    ]
}


def main() -> int:
    falhas: list[str] = []

    def checa(condicao: bool, descricao: str) -> None:
        if not condicao:
            falhas.append(descricao)
            print(f"    ❌ {descricao}")

    base = referencias.carregar()
    print("entradas na base:", len(base))
    checa(bool(base), "a base não pode estar vazia")

    # 1. Nada sem confirmação chega ao laudo.
    citacoes_no_laudo = set()
    for colecoes in (CANNABIS_E_COCAINA, SO_COCAINA, SUBSTANCIA_NOVA):
        citacoes_no_laudo |= set(derivados.referencias(colecoes))
    nao_confirmadas = {r.titulo for r in base if not r.confirmada and r.titulo}
    checa(
        not any(t and t in c for t in nao_confirmadas for c in citacoes_no_laudo),
        "referência não confirmada não pode aparecer no laudo",
    )
    checa(
        all(r.citacao for r in base if r.confirmada),
        "toda referência confirmada precisa de citação escrita",
    )
    checa(
        all(r.fonte for r in base),
        "toda entrada precisa registrar de onde veio",
    )

    # 2. A seleção segue as substâncias do caso.
    com_ambas = derivados.referencias(CANNABIS_E_COCAINA)
    so_coca = derivados.referencias(SO_COCAINA)
    print("\ncannabis + cocaína:", len(com_ambas), "referências")
    print("só cocaína:        ", len(so_coca), "referências")
    checa(
        any("cannabis" in r.lower() for r in com_ambas),
        "o manual de cannabis devia ser citado quando há cannabis",
    )
    checa(
        not any("cannabis" in r.lower() for r in so_coca),
        "não pode citar o manual de cannabis num laudo sem cannabis",
    )
    checa(
        any("cocaine" in r.lower() for r in so_coca),
        "o manual de cocaína devia ser citado quando há cocaína",
    )
    checa(
        all(any("Clarke's" in r for r in lista) for lista in (com_ambas, so_coca)),
        "a referência geral vale para qualquer laudo",
    )

    # 3. Substância sem referência confirmada vira pendência visível.
    nova = derivados.referencias(SUBSTANCIA_NOVA)
    print("substância nova:   ", nova[-1][:60])
    checa(
        any("[PENDENTE:" in r for r in nova),
        "substância sem referência confirmada devia virar pendência",
    )
    checa(
        bool(referencias.substancias_sem_referencia(SUBSTANCIA_NOVA)),
        "a substância descoberta devia ser apontada",
    )
    checa(
        not referencias.substancias_sem_referencia(CANNABIS_E_COCAINA),
        "com as duas cobertas, não devia sobrar pendência",
    )

    # 4. Candidata aparece para conferência, não no documento.
    pendentes = referencias.candidatas(SO_COCAINA)
    print("candidatas para conferir:", [r.id for r in pendentes])
    checa(bool(pendentes), "devia oferecer obras a conferir para a substância do caso")
    checa(
        all(not r.confirmada for r in pendentes),
        "candidata é, por definição, não confirmada",
    )

    print("\n" + "=" * 60)
    if falhas:
        print(f"{len(falhas)} FALHA(S):")
        for f in falhas:
            print(" -", f)
        return 1
    print("REFERÊNCIAS OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
