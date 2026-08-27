"""Acesso ao LLM: cliente, chamada em modo JSON e parsing defensivo.

Este módulo não sabe nada sobre laudos. Ele só garante que o que volta do
modelo é um dicionário — quem decide o que fazer com as chaves é
``core.extracao``.
"""

from __future__ import annotations

import base64
import json
import os
import re

from openai import OpenAI

_CERCA_INICIAL = re.compile(r"^\s*```(?:json)?\s*", re.IGNORECASE)
_CERCA_FINAL = re.compile(r"\s*```\s*$")


class ErroLLM(Exception):
    """Falha ao falar com o modelo ou ao entender a resposta."""


def modelo() -> str:
    return os.getenv("OPENAI_MODEL", "gpt-4o")


def cliente() -> OpenAI:
    chave = os.getenv("OPENAI_API_KEY")
    if not chave:
        raise ErroLLM(
            "OPENAI_API_KEY não encontrada. Copie o .env.example para .env e "
            "preencha a chave antes de usar a conversa."
        )
    return OpenAI(api_key=chave)


def chave_configurada() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))


def parse_json_seguro(texto: str) -> dict:
    """Converte a resposta do modelo em dicionário.

    Tolera cercas ```json e texto solto em volta do objeto; não tolera
    resultado que não seja um objeto JSON — nesse caso levanta ``ErroLLM``,
    porque preencher o laudo com um palpite seria pior do que falhar.
    """
    if not texto or not texto.strip():
        raise ErroLLM("O modelo devolveu uma resposta vazia.")

    limpo = _CERCA_FINAL.sub("", _CERCA_INICIAL.sub("", texto.strip()))
    try:
        dados = json.loads(limpo)
    except json.JSONDecodeError:
        inicio, fim = limpo.find("{"), limpo.rfind("}")
        if inicio == -1 or fim <= inicio:
            raise ErroLLM("O modelo não devolveu um objeto JSON.") from None
        try:
            dados = json.loads(limpo[inicio : fim + 1])
        except json.JSONDecodeError as erro:
            raise ErroLLM(f"JSON inválido na resposta do modelo: {erro}") from erro

    if not isinstance(dados, dict):
        raise ErroLLM("O modelo devolveu JSON que não é um objeto.")
    return dados


def chamar_visao(sistema: str, instrucao: str, imagens: list[bytes]) -> str:
    """Lê imagens de DOCUMENTO e devolve a transcrição em texto.

    Isto é leitura de papel, não interpretação de prova física. A foto do
    material periciado continua sendo anexo documental e nunca passa por aqui:
    peso, contagem e cor são medição do perito.
    """
    if not imagens:
        raise ErroLLM("Nenhuma imagem para transcrever.")

    conteudo: list[dict] = [{"type": "text", "text": instrucao}]
    for dados in imagens:
        codificada = base64.b64encode(dados).decode("ascii")
        conteudo.append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{codificada}"},
            }
        )

    try:
        resposta = cliente().chat.completions.create(
            model=modelo(),
            temperature=0.0,
            messages=[
                {"role": "system", "content": sistema},
                {"role": "user", "content": conteudo},
            ],
        )
    except ErroLLM:
        raise
    except Exception as erro:
        raise ErroLLM(f"Falha ao ler o documento: {erro}") from erro

    return resposta.choices[0].message.content or ""


def chamar_json(sistema: str, usuario: str, temperatura: float = 0.0) -> tuple[dict, str]:
    """Chama o modelo em modo JSON. Devolve (dados, resposta bruta)."""
    try:
        resposta = cliente().chat.completions.create(
            model=modelo(),
            temperature=temperatura,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": sistema},
                {"role": "user", "content": usuario},
            ],
        )
    except ErroLLM:
        raise
    except Exception as erro:  # falha de rede, autenticação, cota
        raise ErroLLM(f"Falha ao chamar o modelo: {erro}") from erro

    bruto = resposta.choices[0].message.content or ""
    return parse_json_seguro(bruto), bruto
