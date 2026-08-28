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
            "A ferramenta não está configurada para conversar. Quem a instalou "
            "precisa cadastrar a chave de acesso (OPENAI_API_KEY no arquivo .env)."
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
        raise ErroLLM("A leitura automática não devolveu nada.")

    limpo = _CERCA_FINAL.sub("", _CERCA_INICIAL.sub("", texto.strip()))
    try:
        dados = json.loads(limpo)
    except json.JSONDecodeError:
        inicio, fim = limpo.find("{"), limpo.rfind("}")
        if inicio == -1 or fim <= inicio:
            raise ErroLLM("A leitura automática devolveu uma resposta ilegível.") from None
        try:
            dados = json.loads(limpo[inicio : fim + 1])
        except json.JSONDecodeError as erro:
            raise ErroLLM(f"Resposta ilegível da leitura automática: {erro}") from erro

    if not isinstance(dados, dict):
        raise ErroLLM("A leitura automática devolveu uma resposta no formato errado.")
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

    resposta = _completar(
        [
            {"role": "system", "content": sistema},
            {"role": "user", "content": conteudo},
        ],
        temperatura=0.0,
        json=False,
    )
    return resposta.choices[0].message.content or ""


def _sem_temperatura(erro: Exception) -> bool:
    """O modelo recusou a temperatura fixa? Os mais novos só aceitam a padrão."""
    return "temperature" in str(erro) and "does not support" in str(erro)


def _completar(mensagens: list[dict], temperatura: float | None, json: bool = True):
    """Chama o serviço, reagindo ao que cada geração de modelo aceita."""
    argumentos: dict = {"model": modelo(), "messages": mensagens}
    if json:
        argumentos["response_format"] = {"type": "json_object"}
    if temperatura is not None:
        argumentos["temperature"] = temperatura

    try:
        return cliente().chat.completions.create(**argumentos)
    except ErroLLM:
        raise
    except Exception as erro:
        if temperatura is not None and _sem_temperatura(erro):
            # Modelo novo: só aceita a temperatura padrão. Repete sem ela em vez
            # de obrigar quem instalou a saber disso.
            argumentos.pop("temperature")
            try:
                return cliente().chat.completions.create(**argumentos)
            except Exception as segundo:
                raise ErroLLM(
                    f"Não consegui falar com o serviço de leitura: {segundo}"
                ) from segundo
        raise ErroLLM(f"Não consegui falar com o serviço de leitura: {erro}") from erro


def chamar_json(sistema: str, usuario: str, temperatura: float = 0.0) -> tuple[dict, str]:
    """Chama o modelo em modo JSON. Devolve (dados, resposta bruta)."""
    resposta = _completar(
        [
            {"role": "system", "content": sistema},
            {"role": "user", "content": usuario},
        ],
        temperatura,
    )

    bruto = resposta.choices[0].message.content or ""
    return parse_json_seguro(bruto), bruto
