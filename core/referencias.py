"""Base de referências da seção 6, escolhida pelo conteúdo do laudo.

A seção 6 não é bibliografia fixa: ela cita o que embasa ESTE exame. A base
guarda cada obra com a descrição do que ela cobre e as substâncias e métodos a
que se aplica; a seleção casa essas marcas com o que o perito registrou.

**Só entra no laudo o que está confirmado.** Citação é o ponto onde um modelo
de linguagem mais erra — inventa título, ano, edição, manual inteiro — e
citação falsa num laudo assinado é pior que referência faltando. Por isso cada
entrada carrega a origem:

- ``transcrita``  — copiada de laudo real;
- ``verificada``  — conferida na fonte oficial, com endereço e data;
- ``candidata``   — encontrada em busca, sem ano/edição conferidos. **Não vai
  ao documento** até o perito confirmar com a obra em mãos.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from templates.identificacao_substancia import boilerplate

ARQUIVO = (
    Path(__file__).resolve().parent.parent
    / "templates"
    / "identificacao_substancia"
    / "referencias.json"
)


@dataclass
class Referencia:
    id: str
    descricao: str = ""
    citacao: str = ""
    titulo: str = ""
    geral: bool = False
    substancias: list[str] = field(default_factory=list)
    metodos: list[str] = field(default_factory=list)
    origem: str = "candidata"
    fonte: str = ""
    confirmada: bool = False

    @property
    def rotulo(self) -> str:
        return self.citacao or self.titulo or self.id


def _carregar_bruto() -> dict:
    if not ARQUIVO.exists():
        return {"referencias": []}
    try:
        return json.loads(ARQUIVO.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"referencias": []}


def carregar() -> list[Referencia]:
    dados = _carregar_bruto()
    return [
        Referencia(**{k: v for k, v in item.items() if k in Referencia.__annotations__})
        for item in dados.get("referencias", [])
    ]


def _marcas(colecoes: dict[str, list[dict]]) -> tuple[set[str], set[str]]:
    """(substâncias, métodos) que este laudo registrou, normalizados."""
    substancias: set[str] = set()
    metodos: set[str] = set()
    for item in colecoes.get("exames_realizados", []):
        substancia = str(item.get("substancia", "")).strip()
        if substancia:
            substancias.add(boilerplate.normaliza(substancia))
            canonica = boilerplate.chave_substancia(substancia)
            if canonica:
                substancias.add(canonica)
        teste = str(item.get("nome_teste", "")).strip()
        if teste:
            metodos.add(boilerplate.normaliza(teste))
    return substancias, metodos


def _casa(referencia: Referencia, substancias: set[str], metodos: set[str]) -> bool:
    if referencia.geral:
        return True
    alvos = {boilerplate.normaliza(s) for s in referencia.substancias}
    if alvos & substancias:
        return True
    marcas = {boilerplate.normaliza(m) for m in referencia.metodos}
    return bool(marcas and marcas & metodos)


def para_o_laudo(colecoes: dict[str, list[dict]]) -> list[Referencia]:
    """Referências confirmadas que se aplicam a este laudo."""
    substancias, metodos = _marcas(colecoes)
    return [
        r for r in carregar() if r.confirmada and _casa(r, substancias, metodos)
    ]


def candidatas(colecoes: dict[str, list[dict]]) -> list[Referencia]:
    """Obras que se aplicam a este laudo mas ainda esperam confirmação."""
    substancias, metodos = _marcas(colecoes)
    return [
        r for r in carregar() if not r.confirmada and _casa(r, substancias, metodos)
    ]


def substancias_sem_referencia(colecoes: dict[str, list[dict]]) -> list[str]:
    """Substâncias do laudo que nenhuma referência confirmada cobre."""
    cobertas: set[str] = set()
    for referencia in para_o_laudo(colecoes):
        if referencia.geral:
            continue
        cobertas |= {boilerplate.normaliza(s) for s in referencia.substancias}

    faltando: list[str] = []
    for item in colecoes.get("exames_realizados", []):
        if str(item.get("resultado", "")).strip().lower() != "positivo":
            continue
        substancia = str(item.get("substancia", "")).strip()
        if not substancia:
            continue
        chaves = {boilerplate.normaliza(substancia)}
        canonica = boilerplate.chave_substancia(substancia)
        if canonica:
            chaves.add(canonica)
        if not (chaves & cobertas) and substancia not in faltando:
            faltando.append(substancia)
    return faltando


def gravar(referencias: list[Referencia]) -> None:
    dados = _carregar_bruto()
    dados["referencias"] = [
        {k: v for k, v in vars(r).items() if v not in ("", [], False) or k in ("geral", "confirmada")}
        for r in referencias
    ]
    ARQUIVO.write_text(
        json.dumps(dados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def confirmar(identificador: str, citacao: str, autor: str) -> None:
    """O perito completou a citação com a obra em mãos: passa a valer."""
    todas = carregar()
    for referencia in todas:
        if referencia.id == identificador:
            referencia.citacao = citacao.strip()
            referencia.confirmada = True
            referencia.origem = "perito"
            referencia.fonte = (
                f"{referencia.fonte} | confirmada por {autor.strip() or 'perito'} "
                f"em {date.today().isoformat()}"
            )
            break
    gravar(todas)


def adicionar(
    identificador: str,
    citacao: str,
    descricao: str,
    substancias: list[str],
    autor: str,
) -> None:
    """Referência que o perito trouxe por conta própria."""
    todas = carregar()
    todas.append(
        Referencia(
            id=identificador,
            citacao=citacao.strip(),
            descricao=descricao.strip(),
            substancias=[s for s in substancias if s],
            geral=not substancias,
            origem="perito",
            fonte=f"informada por {autor.strip() or 'perito'} em {date.today().isoformat()}",
            confirmada=True,
        )
    )
    gravar(todas)
