"""OCR de documento digitalizado, com Tesseract.

Por que Tesseract e não o modelo de visão: **os dois erram, mas de formas
diferentes**. O Tesseract erra produzindo ruído legível como ruído — "1P" por
"IP", "€" por "e". O modelo de visão erra produzindo prosa fluente e plausível
que ninguém confere. Medido nesta requisição real: o modelo reescreveu um
quesito de três maneiras diferentes e inventou endereço, e-mail e matrícula; o
Tesseract transcreveu os seis quesitos palavra por palavra e acertou a
matrícula.

Documento digitalizado costuma chegar deitado, e texto de lado derruba
qualquer OCR — por isso a orientação é detectada e corrigida antes de ler.
"""

from __future__ import annotations

import io
import re
import shutil

IDIOMA = "por"

#: Abaixo disso a leitura foi ruim demais para ser aproveitada.
MINIMO_APROVEITAVEL = 200


class OCRIndisponivel(Exception):
    """Tesseract não está instalado nesta máquina."""


def disponivel() -> bool:
    return shutil.which("tesseract") is not None


def _exige_tesseract() -> None:
    if not disponivel():
        raise OCRIndisponivel(
            "Tesseract não encontrado. Instale com: brew install tesseract "
            "tesseract-lang (macOS) ou apt-get install tesseract-ocr "
            "tesseract-ocr-por (Linux)."
        )


def _abre(dados: bytes):
    from PIL import Image

    imagem = Image.open(io.BytesIO(dados))
    return imagem.convert("L") if imagem.mode not in ("L", "RGB") else imagem


def _confianca(imagem) -> float:
    """Confiança média que o Tesseract atribui às palavras que leu."""
    import pytesseract

    dados = pytesseract.image_to_data(
        imagem, lang=IDIOMA, output_type=pytesseract.Output.DICT
    )
    valores = [float(c) for c in dados.get("conf", []) if str(c).lstrip("-").isdigit() and float(c) >= 0]
    return sum(valores) / len(valores) if valores else 0.0


def endireita(imagem):
    """Corrige a orientação da página. Devolve (imagem, graus aplicados).

    Tenta o detector de orientação do Tesseract; se ele vier inseguro, testa as
    quatro rotações e fica com a de maior confiança de leitura.
    """
    import pytesseract

    try:
        osd = pytesseract.image_to_osd(imagem)
        graus = int(re.search(r"Rotate: (\d+)", osd).group(1))
        confianca = float(re.search(r"Orientation confidence: ([\d.]+)", osd).group(1))
        if graus and confianca >= 2.0:
            return imagem.rotate(-graus, expand=True), graus
        if graus == 0 and confianca >= 2.0:
            return imagem, 0
    except Exception:
        pass

    melhor, melhor_graus, melhor_conf = imagem, 0, _confianca(imagem)
    for graus in (90, 180, 270):
        candidata = imagem.rotate(-graus, expand=True)
        conf = _confianca(candidata)
        if conf > melhor_conf:
            melhor, melhor_graus, melhor_conf = candidata, graus, conf
    return melhor, melhor_graus


def ler_imagem(dados: bytes) -> tuple[str, int]:
    """(texto lido, graus de rotação aplicados)."""
    _exige_tesseract()
    import pytesseract

    imagem, graus = endireita(_abre(dados))
    return pytesseract.image_to_string(imagem, lang=IDIOMA).strip(), graus


def ler_paginas(paginas: list[bytes]) -> tuple[str, list[int]]:
    """OCR de várias páginas, na ordem."""
    textos: list[str] = []
    rotacoes: list[int] = []
    for pagina in paginas:
        texto, graus = ler_imagem(pagina)
        textos.append(texto)
        rotacoes.append(graus)
    return "\n\n".join(t for t in textos if t).strip(), rotacoes
