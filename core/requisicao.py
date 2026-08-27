"""Leitura da requisição — o documento que autoriza e guia o laudo.

O laudo pericial não nasce do nada: nasce de uma requisição da autoridade
policial, que descreve o material apreendido e **formula os quesitos**. Este
módulo transcreve esse documento e propõe o preenchimento do formulário.

Duas regras governam tudo aqui:

1. **Não inventa.** Campo que não estiver na requisição fica vazio, para o
   perito preencher. Todo valor extraído é conferido contra a transcrição:
   valor que não aparece no documento é descartado.
2. **A transcrição vem de OCR, não de modelo de visão.** Medido nesta
   requisição real: o modelo de visão reescreveu um quesito de três maneiras
   diferentes em três leituras, inventou endereço, e-mail e matrícula, e apagou
   a data da apreensão. O Tesseract, com a página endireitada, transcreveu os
   seis quesitos palavra por palavra e acertou a matrícula. Os dois erram — mas
   o OCR erra produzindo ruído visível ("1P" por "IP") e o modelo erra
   produzindo prosa plausível que ninguém confere. O modelo de visão só entra
   quando não há Tesseract na máquina, e aí a leitura é cruzada entre passes e
   marcada como frágil.
3. **A descrição do material da requisição NÃO entra no laudo.** O delegado
   escreve "aparentemente maconha", "semelhantes à pasta base de cocaína" —
   isso é a suspeita dele, não achado pericial. A camada 1 continua vindo
   exclusivamente do que o perito mediu e ditou na conversa.
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field

from config.schema import Exame
from core import ocr
from core.llm import chamar_json, chamar_visao
from templates.identificacao_substancia import boilerplate

#: Abaixo disso, a camada de texto do PDF é considerada inexistente.
_MINIMO_DE_TEXTO = 120

SISTEMA_TRANSCRICAO = """Você transcreve documentos oficiais digitalizados para texto.

REGRAS
- Transcreva EXATAMENTE o que está escrito, incluindo números, datas, nomes e
  numeração de ofício. Não corrija, não resuma, não reordene.
- Preserve a estrutura: cabeçalho, corpo, lista de quesitos, assinatura, carimbos.
- Trecho ilegível: escreva [ilegível]. Nunca chute o que pode estar escrito.
- Não comente nem interprete o documento. Só transcreva."""

SISTEMA_EXTRACAO = """Você preenche o formulário de um laudo pericial a partir do texto de uma requisição de exame.

REGRAS ABSOLUTAS
1. Só extraia o que está ESCRITO no texto da requisição.
2. Campo que não constar do texto: OMITA a chave. Campo omitido é preenchido
   pelo perito depois; campo inventado corrompe um documento oficial.
3. Não deduza um campo a partir de outro, nem use conhecimento próprio sobre
   como delegacias costumam numerar ofícios ou procedimentos.
4. A descrição do material vai APENAS em "itens_declarados", e serve só para
   conferir contagem contra o que o perito recebeu. Ela NUNCA preenche campo do
   laudo: a requisição traz a suspeita da autoridade ("aparentemente maconha",
   "semelhante a pasta base"), e suspeita não é achado pericial. Copie o texto
   como está, sem completar e sem concluir nada dele.
5. Os quesitos devem ser copiados PALAVRA POR PALAVRA, na ordem em que aparecem,
   sem renumerar, sem reescrever e sem completar com quesitos que você conheça
   de outros laudos.

FORMATO DA SAÍDA
Responda APENAS com um objeto JSON:
{"admin": {"<campo>": {"valor": "<valor>", "trecho": "<citação exata do documento>"}},
 "quesitos": ["<pergunta copiada>", "..."],
 "itens_declarados": [{"quantidade": "<número, só dígitos>", "texto": "<descrição copiada>"}]}

- "trecho" é a citação literal do documento de onde o valor saiu, copiada sem
  alterar uma letra. Valor cujo trecho não existir no documento é descartado.
- Datas no campo "valor" vão no formato AAAA-MM-DD; o "trecho" mantém a forma
  original escrita no documento.
- Se não houver quesitos no documento, devolva a lista vazia.
- "itens_declarados": um por item de material que a autoridade diz estar enviando.
  "quantidade" é só o número que ela declarou (de "02 (dois) tabletes", é "2").
  Se ela não declarar número, omita "quantidade"."""


@dataclass
class Leitura:
    """Resultado de ler uma requisição."""

    texto: str = ""
    origem: str = ""
    campos: dict[str, str] = field(default_factory=dict)
    trechos: dict[str, str] = field(default_factory=dict)
    quesitos: list[str] = field(default_factory=list)
    #: O que a AUTORIDADE diz ter enviado. Serve para conferência de contagem e
    #: nada mais — nunca preenche a camada 1, que é o que o perito mediu.
    itens_declarados: list[dict] = field(default_factory=list)
    descartados: list[str] = field(default_factory=list)
    #: Campos e quesitos que variaram entre as leituras — o perito lê do papel.
    incertos: list[str] = field(default_factory=list)
    passes: int = 1
    bruto: str = ""
    erro: str = ""

    #: "exata" (camada de texto), "ocr" (Tesseract) ou "modelo" (visão).
    nivel: str = "exata"
    #: Graus de rotação que o OCR precisou aplicar em cada página.
    rotacoes: list[int] = field(default_factory=list)

    @property
    def confiavel(self) -> bool:
        """Só a camada de texto de um PDF é leitura exata do documento."""
        return self.nivel == "exata"


def texto_de_pdf(dados: bytes) -> str:
    """Camada de texto do PDF, quando existe."""
    from pypdf import PdfReader

    leitor = PdfReader(io.BytesIO(dados))
    partes = [(pagina.extract_text() or "") for pagina in leitor.pages]
    return "\n".join(partes).strip()


def imagens_de_pdf(dados: bytes, limite: int = 4) -> list[bytes]:
    """Imagens embutidas de um PDF digitalizado, uma por página."""
    from pypdf import PdfReader

    leitor = PdfReader(io.BytesIO(dados))
    encontradas: list[bytes] = []
    for pagina in leitor.pages:
        for imagem in pagina.images:
            encontradas.append(imagem.data)
            break
        if len(encontradas) >= limite:
            break
    return encontradas


def transcrever(dados: bytes, nome: str) -> tuple[str, str]:
    """(texto do documento, como ele foi obtido)."""
    if nome.lower().endswith(".pdf"):
        texto = texto_de_pdf(dados)
        if len(texto) >= _MINIMO_DE_TEXTO:
            return texto, "camada de texto do PDF"
        imagens = imagens_de_pdf(dados)
        if not imagens:
            return "", "PDF sem texto e sem imagem legível"
        return (
            chamar_visao(
                SISTEMA_TRANSCRICAO,
                "Transcreva integralmente esta requisição de exame pericial.",
                imagens,
            ),
            "leitura da imagem digitalizada",
        )

    return (
        chamar_visao(
            SISTEMA_TRANSCRICAO,
            "Transcreva integralmente esta requisição de exame pericial.",
            [dados],
        ),
        "leitura da imagem enviada",
    )


def _campos_procurados(exame: Exame) -> str:
    linhas = []
    for campo in exame.campos_admin:
        if not campo.da_requisicao:
            continue
        descricao = f'  - "{campo.chave}" ({campo.label})'
        if campo.ajuda:
            descricao += f" — {campo.ajuda}"
        if campo.opcoes:
            descricao += " Valores possíveis: " + ", ".join(campo.opcoes) + "."
        linhas.append(descricao)
    return "\n".join(linhas)


def extrair(exame: Exame, texto: str) -> Leitura:
    """Preenche o formulário a partir do texto da requisição."""
    leitura = Leitura(texto=texto)
    if not texto.strip():
        leitura.erro = "Documento sem texto legível."
        return leitura

    instrucao = "\n".join(
        [
            "CAMPOS PROCURADOS:",
            _campos_procurados(exame),
            "",
            "TEXTO DA REQUISIÇÃO:",
            texto.strip(),
        ]
    )
    try:
        dados, bruto = chamar_json(SISTEMA_EXTRACAO, instrucao)
    except Exception as erro:
        leitura.erro = str(erro)
        return leitura

    leitura.bruto = bruto
    referencia = boilerplate.normaliza(texto)
    validos = {c.chave: c for c in exame.campos_admin if c.da_requisicao}

    entradas = dados.get("admin")
    if isinstance(entradas, dict):
        for chave, conteudo in entradas.items():
            campo = validos.get(str(chave))
            if campo is None:
                continue
            if isinstance(conteudo, dict):
                valor = str(conteudo.get("valor", "")).strip()
                trecho = str(conteudo.get("trecho", "")).strip()
            else:
                valor, trecho = str(conteudo).strip(), ""
            if not valor:
                continue
            # A citação é a prova de que o valor saiu do papel. Sem ela, cai fora.
            if not trecho or boilerplate.normaliza(trecho) not in referencia:
                leitura.descartados.append(campo.label)
                continue
            leitura.campos[campo.chave] = valor
            leitura.trechos[campo.chave] = trecho

    declarados = dados.get("itens_declarados")
    if isinstance(declarados, list):
        for item in declarados:
            if not isinstance(item, dict):
                continue
            texto_item = str(item.get("texto", "")).strip()
            if not texto_item or boilerplate.normaliza(texto_item) not in referencia:
                continue
            quantidade = str(item.get("quantidade", "")).strip()
            leitura.itens_declarados.append(
                {
                    "quantidade": quantidade if quantidade.isdigit() else "",
                    "texto": texto_item,
                }
            )

    perguntas = dados.get("quesitos")
    if isinstance(perguntas, list):
        for pergunta in perguntas:
            texto_pergunta = str(pergunta).strip()
            if not texto_pergunta:
                continue
            if boilerplate.normaliza(texto_pergunta) not in referencia:
                leitura.descartados.append(f"quesito: {texto_pergunta[:40]}...")
                continue
            leitura.quesitos.append(texto_pergunta)

    return leitura


def _consolidar(leituras: list[Leitura], exame: Exame) -> Leitura:
    """Mantém só o que saiu igual em todas as leituras.

    Divergência entre passes é prova de que o modelo não leu, adivinhou. O que
    diverge não entra como valor: entra como leitura incerta.
    """
    # Consolidar só acontece no caminho do modelo de visão: o nível já nasce
    # marcado como frágil, para que uma Leitura solta nunca pareça confiável.
    final = Leitura(
        texto=leituras[0].texto,
        bruto=leituras[0].bruto,
        passes=len(leituras),
        nivel="modelo",
    )
    rotulos = {c.chave: c.label for c in exame.campos_admin}

    chaves = {chave for leitura in leituras for chave in leitura.campos}
    for chave in sorted(chaves):
        valores = {boilerplate.normaliza(l.campos.get(chave, "")) for l in leituras}
        if len(valores) == 1 and "" not in valores:
            final.campos[chave] = leituras[0].campos[chave]
            final.trechos[chave] = leituras[0].trechos.get(chave, "")
        else:
            final.incertos.append(rotulos.get(chave, chave))

    contagens = {
        tuple(i.get("quantidade", "") for i in l.itens_declarados) for l in leituras
    }
    if len(contagens) == 1:
        final.itens_declarados = leituras[0].itens_declarados
    else:
        final.incertos.append("os itens declarados pela autoridade")

    tamanhos = {len(l.quesitos) for l in leituras}
    if len(tamanhos) != 1 or tamanhos == {0}:
        final.incertos.append("a lista de quesitos (número de perguntas variou)")
        return final

    for posicao in range(tamanhos.pop()):
        versoes = {boilerplate.normaliza(l.quesitos[posicao]) for l in leituras}
        if len(versoes) == 1:
            final.quesitos.append(leituras[0].quesitos[posicao])
        else:
            final.quesitos.append("")
            final.incertos.append(f"o quesito {posicao + 1:02d}")

    for leitura in leituras:
        for descartado in leitura.descartados:
            if descartado not in final.descartados:
                final.descartados.append(descartado)
    return final


def ler(exame: Exame, dados: bytes, nome: str, passes: int = 3) -> Leitura:
    """Lê a requisição pelo caminho mais fiel que estiver disponível.

    Ordem: camada de texto do PDF > OCR do Tesseract > modelo de visão. O
    último só entra sem Tesseract instalado, e roda várias vezes para que a
    divergência entre leituras apareça como incerteza em vez de virar valor.
    """
    try:
        if nome.lower().endswith(".pdf"):
            texto = texto_de_pdf(dados)
            if len(texto) >= _MINIMO_DE_TEXTO:
                leitura = extrair(exame, texto)
                leitura.origem = "camada de texto do PDF"
                leitura.nivel = "exata"
                return leitura
            paginas = imagens_de_pdf(dados)
            if not paginas:
                return Leitura(erro="PDF sem camada de texto e sem imagem legível.")
        else:
            paginas = [dados]

        if ocr.disponivel():
            texto, rotacoes = ocr.ler_paginas(paginas)
            if len(texto) >= ocr.MINIMO_APROVEITAVEL:
                leitura = extrair(exame, texto)
                leitura.origem = "OCR do documento digitalizado"
                leitura.nivel = "ocr"
                leitura.rotacoes = rotacoes
                return leitura

        textos = [
            chamar_visao(
                SISTEMA_TRANSCRICAO,
                "Transcreva integralmente esta requisição de exame pericial.",
                paginas,
            )
            for _ in range(max(passes, 1))
        ]
    except Exception as erro:
        return Leitura(erro=str(erro))

    leituras = [extrair(exame, texto) for texto in textos]
    if any(l.erro for l in leituras):
        return Leitura(erro=next(l.erro for l in leituras if l.erro))

    final = _consolidar(leituras, exame)
    final.origem = "leitura por modelo de visão (sem OCR nesta máquina)"
    final.nivel = "modelo"
    return final
