"""Números e datas por extenso, no formato que o laudo real usa.

O laudo escreve o valor e o extenso lado a lado: "3,0 g (três gramas)",
"02 (dois) invólucros", "1,98 kg (um quilograma e novecentos e oitenta gramas)".
Tudo aqui é aritmética determinística sobre o que o perito mediu — e o resultado
aparece editável na tela de confirmação antes de virar documento.
"""

from __future__ import annotations

from datetime import date

_ATE_19 = (
    "zero", "um", "dois", "três", "quatro", "cinco", "seis", "sete", "oito",
    "nove", "dez", "onze", "doze", "treze", "catorze", "quinze", "dezesseis",
    "dezessete", "dezoito", "dezenove",
)
_DEZENAS = (
    "", "", "vinte", "trinta", "quarenta", "cinquenta", "sessenta", "setenta",
    "oitenta", "noventa",
)
_CENTENAS = (
    "", "cento", "duzentos", "trezentos", "quatrocentos", "quinhentos",
    "seiscentos", "setecentos", "oitocentos", "novecentos",
)
_MESES = (
    "janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
    "agosto", "setembro", "outubro", "novembro", "dezembro",
)

#: Unidades de massa conhecidas: (singular, plural, fator em gramas).
UNIDADES_MASSA = {
    "g": ("grama", "gramas", 1),
    "grama": ("grama", "gramas", 1),
    "gramas": ("grama", "gramas", 1),
    "kg": ("quilograma", "quilogramas", 1000),
    "quilo": ("quilograma", "quilogramas", 1000),
    "quilos": ("quilograma", "quilogramas", 1000),
    "quilograma": ("quilograma", "quilogramas", 1000),
    "quilogramas": ("quilograma", "quilogramas", 1000),
    "mg": ("miligrama", "miligramas", 0.001),
}


def _ate_999(numero: int) -> str:
    if numero < 20:
        return _ATE_19[numero]
    if numero < 100:
        dezena, unidade = divmod(numero, 10)
        base = _DEZENAS[dezena]
        return f"{base} e {_ATE_19[unidade]}" if unidade else base
    if numero == 100:
        return "cem"
    centena, resto = divmod(numero, 100)
    base = _CENTENAS[centena]
    return f"{base} e {_ate_999(resto)}" if resto else base


#: Formas femininas: "duas páginas", não "dois páginas".
_FEMININO = {
    "um": "uma", "dois": "duas", "duzentos": "duzentas", "trezentos": "trezentas",
    "quatrocentos": "quatrocentas", "quinhentos": "quinhentas",
    "seiscentos": "seiscentas", "setecentos": "setecentas",
    "oitocentos": "oitocentas", "novecentos": "novecentas",
}


def _flexiona(texto: str) -> str:
    return " ".join(_FEMININO.get(palavra, palavra) for palavra in texto.split())


def por_extenso(numero: int, feminino: bool = False) -> str:
    """Inteiro por extenso, de 0 a 999.999."""
    if numero < 0 or numero > 999_999:
        raise ValueError(f"fora do intervalo suportado: {numero}")
    if numero < 1000:
        escrito = _ate_999(numero)
        return _flexiona(escrito) if feminino else escrito

    milhares, resto = divmod(numero, 1000)
    base = "mil" if milhares == 1 else f"{_ate_999(milhares)} mil"
    if not resto:
        return base
    ligacao = " e " if resto < 100 or resto % 100 == 0 else " "
    escrito = f"{base}{ligacao}{_ate_999(resto)}"
    return _flexiona(escrito) if feminino else escrito


def _decimal(texto: str) -> float | None:
    limpo = str(texto).strip().replace(" ", "").replace(",", ".")
    try:
        return float(limpo)
    except ValueError:
        return None


def massa_por_extenso(valor: str, unidade: str) -> str:
    """"1,98" + "kg" -> "um quilograma e novecentos e oitenta gramas".

    Devolve string vazia quando o valor ou a unidade não são reconhecidos —
    melhor não escrever nada do que escrever um número errado no laudo.
    """
    numero = _decimal(valor)
    if numero is None or numero < 0:
        return ""

    chave = str(unidade).strip().lower().rstrip(".")
    if chave not in UNIDADES_MASSA:
        return ""
    singular, plural, fator = UNIDADES_MASSA[chave]

    inteiro = int(numero)
    fracao = numero - inteiro

    partes: list[str] = []
    if inteiro or not fracao:
        rotulo = singular if inteiro == 1 else plural
        partes.append(f"{por_extenso(inteiro)} {rotulo}")

    if fracao > 0:
        if fator == 1000:  # quilograma: a fração vira gramas
            gramas = int(round(fracao * 1000))
            if gramas:
                partes.append(f"{por_extenso(gramas)} {'grama' if gramas == 1 else 'gramas'}")
        else:
            # Sem sub-unidade transcrita de laudo real para este caso.
            return ""

    return " e ".join(partes)


def paginas_por_extenso(valor: str) -> str:
    """"2" -> "duas". Vazio se não for um número de páginas plausível."""
    texto = str(valor).strip()
    if not texto.isdigit():
        return ""
    quantidade = int(texto)
    if not 1 <= quantidade <= 999:
        return ""
    return por_extenso(quantidade, feminino=True)


def quantidade_por_extenso(valor: str) -> str:
    """"02" -> "dois". Vazio se não for inteiro."""
    texto = str(valor).strip()
    if not texto.isdigit():
        return ""
    return por_extenso(int(texto))


def data_por_extenso(iso: str) -> str:
    """"2019-04-26" -> "26 de abril de 2019"."""
    try:
        dia = date.fromisoformat(str(iso).strip())
    except ValueError:
        return str(iso).strip()
    return f"{dia.day} de {_MESES[dia.month - 1]} de {dia.year}"


def data_curta(iso: str) -> str:
    """"2019-04-23" -> "23/04/19", como o laudo escreve a data do ofício."""
    try:
        dia = date.fromisoformat(str(iso).strip())
    except ValueError:
        return str(iso).strip()
    return dia.strftime("%d/%m/%y")


def com_zero(valor: str) -> str:
    """"2" -> "02", como o laudo grafa a contagem de invólucros."""
    texto = str(valor).strip()
    return texto.zfill(2) if texto.isdigit() and len(texto) < 2 else texto
