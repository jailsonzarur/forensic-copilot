"""Escreve a seção do E3 no relatório técnico, a partir do dado medido."""

from __future__ import annotations

import difflib
import json
import re
import unicodedata
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
BRUTO = RAIZ / "e3" / "resultados" / "e3_reproducao.json"
PARES = RAIZ / "e3" / "pares.json"
DESTINO = RAIZ / "E3-reproducao-de-laudos-reais.md"

#: Parágrafos técnicos conferidos trecho a trecho, por tipo de exame. São a
#: medida que interessa: a similaridade do documento inteiro é dominada por
#: artefato de extração de PDF (apêndice, rodapé, texto fora de ordem).
ANCORAS = {
    "identificacao_veicular": (
        ("NIV", "observando se o local de gravacao", 430),
        ("Motor", "examinando se a numeracao do motor", 430),
    ),
    "identificacao_substancia": (
        ("Descrição do material", "trata se de", 300),
    ),
    "verificacao_danos": (
        ("Do Local", "o local objeto de exame", 260),
    ),
}


def norm(t: str) -> str:
    t = unicodedata.normalize("NFKD", t)
    t = "".join(c for c in t if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^\w\s]", " ", t.lower()).split())


def paragrafos(apelido: str, exame: str) -> list[tuple[str, float | None]]:
    ofi_p = RAIZ / "e3" / "oficiais" / f"{apelido}.txt"
    ger_p = RAIZ / "e3" / "resultados" / f"{apelido}-gerado.txt"
    if not (ofi_p.exists() and ger_p.exists()):
        return []
    ofi, ger = norm(ofi_p.read_text(encoding="utf-8")), norm(ger_p.read_text(encoding="utf-8"))
    saida = []
    for rotulo, chave, n in ANCORAS.get(exame, ()):
        i, j = ofi.find(chave), ger.find(chave)
        if i < 0 or j < 0:
            saida.append((rotulo, None))
            continue
        saida.append((rotulo, difflib.SequenceMatcher(None, ofi[i:i+n], ger[j:j+n]).ratio()))
    return saida


def main() -> int:
    dados = json.loads(BRUTO.read_text(encoding="utf-8"))
    pares = json.loads(PARES.read_text(encoding="utf-8"))
    casos = dados["casos"]

    linhas = [
        "# E3 — Reprodução de laudos reais",
        "",
        f"*Modelo: `{dados['modelo']}` — o único 21/21 no E1. "
        f"Medido em {dados['medido_em'][:10]}.*",
        "",
        "## Método",
        "",
        "Para cada par requisição↔laudo oficial: a REQUISIÇÃO é lida pelo",
        "pipeline real; falas COLOQUIAIS do perito, escritas a partir dos fatos",
        "do laudo mas nunca copiadas dele, passam pelo agente de conversa; o",
        "`.docx` é montado pelo montador real; o texto gerado é comparado ao",
        "oficial.",
        "",
        "Os fatos da camada 1 só existem no laudo oficial — são o que o perito",
        "mediu, e não constam da requisição. Daí a autorreferência parcial que a",
        "seção de ameaças registra. A redação coloquial é o que impede o teste",
        "de virar cópia: a ferramenta precisa PRODUZIR o texto oficial a partir",
        "de fala solta.",
        "",
        "**Laudos inéditos × laudos-fonte.** Os marcados como inéditos não",
        "serviram de base para nenhum template. Só eles medem generalização; os",
        "demais medem consistência.",
        "",
        "## Resultado",
        "",
        "| Caso | Tipo | Inédito | Fatos presentes | Parágrafos técnicos |",
        "|---|---|---|---|---|",
    ]

    for apelido, caso in casos.items():
        c = caso["comparacao"]
        total = len(c["fatos_presentes"]) + len(c["fatos_ausentes"])
        inedito = "**sim**" if pares.get(apelido, {}).get("inedito") else "não"
        pars = paragrafos(apelido, caso["exame"])
        txt = " · ".join(
            f"{r}: {v:.1%}" if v is not None else f"{r}: não localizado" for r, v in pars
        ) or "—"
        linhas.append(
            f"| `{apelido}` | {caso['exame'].replace('identificacao_','').replace('verificacao_','')} "
            f"| {inedito} | {len(c['fatos_presentes'])}/{total} | {txt} |"
        )

    linhas += [
        "",
        "A similaridade do documento inteiro **não** é reportada como métrica:",
        "ela fica entre 8% e 41% em todos os casos, dominada por artefato de",
        "extração de PDF — apêndice fotográfico, rodapé de página e texto que o",
        "extrator devolve fora de ordem. O parágrafo técnico é a medida honesta.",
        "",
        "## O que os laudos inéditos revelaram",
        "",
        "Esta é a parte que só apareceu com laudos de fora do conjunto-fonte.",
        "Nenhum item abaixo é falha de fidelidade — são **lacunas de cobertura**:",
        "a ferramenta não inventou nada, ela deixou de saber dizer.",
        "",
    ]

    lacunas = [
        ("veicular-00100350-44", "estrutura da seção 2",
         "o laudo inédito não usa subseções numeradas (2.1/2.2/2.3) e intercala "
         "as imagens no corpo; o template numera e manda ao apêndice"),
        ("veicular-00100350-44", "ano de fabricação",
         "o oficial grava o ano junto do NIV — *«NIV: 9C2JC4110AR094988 e da "
         "gravação do ano de fabricação: 2010»* — e não há slot para isso"),
        ("veicular-00100350-44", "órgão emissor",
         "`DEPARTAMENTO DE PERÍCIAS DO INTERIOR`, não `INSTITUTO DE "
         "CRIMINALÍSTICA`: o cabeçalho está fixo no template"),
        ("veicular-00100350-44", "conjunto de quesitos",
         "4 quesitos, não 6, com enunciados diferentes — *«quais os caracteres "
         "adulterados»* contra *«quais os números e ou letras adulteradas»*"),
        ("substancia-00086731-52", "mais de uma substância por ensaio",
         "a CG/EM identificou cocaína, cafeína e lidocaína; o schema tem UM slot "
         "de substância por exame, e a frase inteira entrou nele"),
        ("substancia-00086731-52", "convenção do extenso",
         "o oficial escreve *«cento e três gramas e quatro decigramas»*; nossa "
         "convenção, transcrita de outro laudo, produz *«quatrocentos "
         "miligramas»*. Dois peritos, duas convenções"),
        ("substancia-00086731-52", "ensaio não catalogado",
         "Cromatografia Gasosa acoplada a Espectrometria de Massas não está no "
         "vocabulário nem tem redação transcrita"),
        ("danos-00074314-60", "seções DISCUSSÃO e REFERÊNCIAS",
         "o laudo inédito tem as duas; o template de danos não prevê nenhuma"),
        ("danos-00074314-60", "conjunto de quesitos",
         "16 quesitos vindos de Delegacia da Mulher, nenhum casando com o "
         "conjunto transcrito"),
        ("danos-00074314-60", "legenda das imagens",
         "o oficial usa *«FOTO 01 –»*; o template usa *«IMAGEM 01:»*"),
    ]
    linhas += ["| Caso | Lacuna | O que aconteceu |", "|---|---|---|"]
    linhas += [f"| `{a}` | {b} | {c} |" for a, b, c in lacunas]

    linhas += [
        "",
        "## Bugs encontrados e corrigidos",
        "",
        "Quatro defeitos reais, **todos silenciosos**, nenhum visível para a",
        "suíte de verificação — porque todos os roteiros alimentavam o estado",
        "direto, sem passar pela conversa.",
        "",
        "1. **A frase do tratamento sumia inteira.** O perito diz *«reagente DE",
        "   liga metálica»*, o template tem *«reagentes EM liga metálica»*: uma",
        "   preposição de diferença, e o parágrafo saía *«…de fábrica. obteve-se",
        "   resultado NEGATIVO»*. **O laudo afirmaria um resultado sem dizer como",
        "   foi obtido.**",
        "2. **A rede de segurança dos quesitos sequestrava fala do exame.** Como",
        "   a etapa avança por dados e o mínimo é 1, depois do primeiro sinal",
        "   identificador a ferramenta já se julgava na etapa de quesitos e",
        "   gravava a descrição do motor como resposta ao Quesito 01.",
        "3. **Português quebrado.** `caracteres_divergentes` guardava a oração",
        "   inteira e o template completa com *«apresentavam formato…»*,",
        "   produzindo *«todos os caracteres também divergentes apresentavam»*.",
        "4. **Maiúscula no meio da frase**: *«verificou-se que Todos os",
        "   caracteres»*.",
        "",
        "## Ameaças à validade",
        "",
        "- **Autorreferência parcial.** Os fatos da camada 1 vêm do laudo",
        "  oficial, porque só existem lá. O teste mede se a ferramenta remonta o",
        "  documento a partir deles, não se a conversa os extrai de um perito",
        "  real.",
        "- **As falas foram escritas por quem desenvolve a ferramenta.** Um",
        "  perito falaria diferente, e provavelmente pior para a extração.",
        "- **Um caso por tipo entre os inéditos.** Três laudos não sustentam",
        "  afirmação sobre a variedade do corpus inteiro.",
        "- **O laudo de danos inédito não teve os quesitos respondidos**, então",
        "  seu documento sai cheio de pendências e sua similaridade não é",
        "  comparável à dos demais.",
    ]

    DESTINO.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    print(f"escrito em {DESTINO}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
