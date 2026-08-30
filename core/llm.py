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


#: Contabilidade das chamadas, para a bancada medir custo e latência por laudo.
#: Fica desligada por padrão: a ferramenta do perito não precisa contar nada.
_CONTAS: dict = {"chamadas": 0, "entrada": 0, "saida": 0, "segundos": 0.0, "esperas_por_cota": 0}


def zerar_contas() -> None:
    _CONTAS.update({"chamadas": 0, "entrada": 0, "saida": 0, "segundos": 0.0, "esperas_por_cota": 0})


def contas() -> dict:
    """(chamadas, tokens de entrada, tokens de saída, segundos) acumulados."""
    return dict(_CONTAS)


#: Provedor em uso, quando a bancada de experimentos força um. Fora dela fica
#: vazio e tudo vem do ``.env``, como sempre — a ferramenta que o perito usa não
#: muda de modelo sozinha.
_FORCADO: dict = {}


def usar_provedor(modelo: str, chave: str, base_url: str = "") -> None:
    """Fixa modelo e credencial para as próximas chamadas.

    Existe para a bancada de experimentos comparar famílias de modelo sem
    mexer no ``.env`` de quem está usando a ferramenta. ``base_url`` aponta
    para provedores compatíveis com a API da OpenAI — que hoje é quase todos.
    """
    _FORCADO.update({"modelo": modelo, "chave": chave, "base_url": base_url})


def soltar_provedor() -> None:
    """Volta ao que está configurado no ``.env``."""
    _FORCADO.clear()


def modelo() -> str:
    return _FORCADO.get("modelo") or os.getenv("OPENAI_MODEL", "gpt-4o")


def cliente() -> OpenAI:
    chave = _FORCADO.get("chave") or os.getenv("OPENAI_API_KEY")
    if not chave:
        raise ErroLLM(
            "A ferramenta não está configurada para conversar. Quem a instalou "
            "precisa cadastrar a chave de acesso (OPENAI_API_KEY no arquivo .env)."
        )
    base = _FORCADO.get("base_url") or os.getenv("OPENAI_BASE_URL", "")
    return OpenAI(api_key=chave, base_url=base) if base else OpenAI(api_key=chave)


def chave_configurada() -> bool:
    return bool(_FORCADO.get("chave") or os.getenv("OPENAI_API_KEY"))


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


#: Quantas vezes insistir quando o serviço responde 429 (cota estourada), e a
#: espera inicial em segundos — dobrada a cada tentativa. Existe porque contas
#: sem faturamento (o free tier do Gemini) limitam requisições por minuto: sem
#: isto, uma rajada de perguntas derruba a conversa por um limite de cota, e o
#: perito lê "a ferramenta falhou" no meio do laudo.
_TENTATIVAS_COTA = 4
_ESPERA_COTA = 8.0


def _e_cota(erro: Exception) -> bool:
    texto = str(erro).lower()
    return "429" in texto or "quota" in texto or "rate limit" in texto


def _cronometrar(argumentos: dict):
    """Chama o serviço medindo tempo e tokens, sem alterar o resultado.

    Estouro de cota não é erro de quem está usando: espera e tenta de novo,
    com a espera dobrando a cada vez.
    """
    import time

    espera = _ESPERA_COTA
    for tentativa in range(_TENTATIVAS_COTA):
        inicio = time.monotonic()
        try:
            resposta = cliente().chat.completions.create(**argumentos)
        except Exception as erro:
            _CONTAS["segundos"] += time.monotonic() - inicio
            if _e_cota(erro) and tentativa < _TENTATIVAS_COTA - 1:
                _CONTAS["esperas_por_cota"] = _CONTAS.get("esperas_por_cota", 0) + 1
                time.sleep(espera)
                espera *= 2
                continue
            raise
        _CONTAS["segundos"] += time.monotonic() - inicio
        _CONTAS["chamadas"] += 1
        uso = getattr(resposta, "usage", None)
        if uso is not None:
            _CONTAS["entrada"] += getattr(uso, "prompt_tokens", 0) or 0
            _CONTAS["saida"] += getattr(uso, "completion_tokens", 0) or 0
        return resposta
    raise ErroLLM("Cota do serviço esgotada após várias tentativas.")


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
        return _cronometrar(argumentos)
    except ErroLLM:
        raise
    except Exception as erro:
        if temperatura is not None and _sem_temperatura(erro):
            # Modelo novo: só aceita a temperatura padrão. Repete sem ela em vez
            # de obrigar quem instalou a saber disso.
            argumentos.pop("temperature")
            try:
                return _cronometrar(argumentos)
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
