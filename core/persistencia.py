"""Rascunhos em disco — o laudo sobrevive a fechar a aba.

Todo o estado vive no ``st.session_state``, que o Streamlit perde quando a aba
fecha, a página recarrega ou o servidor reinicia. Para quem trabalha em campo,
com rede instável, isso significava recomeçar o laudo do zero — e recomeçar um
laudo é a chance de o perito digitar diferente da segunda vez.

O que este módulo faz e o que ele NÃO faz:

- salva **exatamente** o que o perito ditou e revisou, sem tocar em nada;
- grava por escrita atômica (arquivo temporário e renomeação), para que uma
  queda no meio da gravação não deixe um rascunho pela metade — o anterior
  continua íntegro;
- não sincroniza, não sobe para lugar nenhum, não sai desta máquina.

**O rascunho contém dado pessoal** — envolvido, número de procedimento,
endereço, fotografias. Por isso ``rascunhos/`` está no ``.gitignore``, ao lado
de ``referencia/``, e o perito pode descartar um rascunho a qualquer momento
pela tela de seleção.
"""

from __future__ import annotations

import json
import os
import shutil
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

#: Onde os rascunhos ficam. A variável de ambiente existe para que os roteiros
#: de verificação rodem sem encostar nos laudos reais de quem executa a suíte —
#: um teste que apaga rascunho de perito seria pior que teste nenhum.
_PADRAO = Path(__file__).resolve().parent.parent / "rascunhos"


def pasta_base() -> Path:
    configurada = os.environ.get("FORENSIC_RASCUNHOS", "").strip()
    return Path(configurada) if configurada else _PADRAO

#: Chaves do ``session_state`` que compõem o laudo. É uma lista fechada de
#: propósito: o ``session_state`` também guarda o estado interno de cada widget
#: do Streamlit ("conf_admin_numero_laudo"), e restaurar isso brigaria com os
#: próprios widgets ao remontar a tela.
CHAVES = (
    "tela",
    "exame_id",
    "admin",
    "requisicao",
    "quesitos",
    "respostas_quesitos",
    "colecoes",
    "colecoes_fechadas",
    "mensagens",
    "derivados",
    "derivados_origem",
)

#: As imagens não cabem no JSON: vão em arquivo próprio, nomeado pela assinatura
#: que a tela de confirmação já calcula (sha256 do conteúdo).
_IMAGENS = "imagens"


@dataclass(frozen=True)
class Rascunho:
    """Um laudo em andamento, como aparece na lista para retomar."""

    id: str
    exame_id: str
    rotulo: str
    atualizado_em: str
    campos_preenchidos: int

    def quando(self) -> str:
        """Data e hora em português, para a lista da tela de seleção."""
        try:
            momento = datetime.fromisoformat(self.atualizado_em)
        except ValueError:
            return self.atualizado_em
        return momento.strftime("%d/%m/%Y às %Hh%M")


def novo_id() -> str:
    return uuid.uuid4().hex[:12]


def _pasta(laudo_id: str) -> Path:
    return pasta_base() / laudo_id


def _conta_preenchidos(estado: dict) -> int:
    """Quantos campos o perito já ditou — só para dar tamanho ao rascunho."""
    total = len(
        [v for v in (estado.get("admin") or {}).values() if str(v).strip()]
    )
    for itens in (estado.get("colecoes") or {}).values():
        for item in itens:
            total += len([v for v in item.values() if str(v).strip()])
    total += len(
        [v for v in (estado.get("respostas_quesitos") or {}).values() if str(v).strip()]
    )
    return total


def _rotulo(estado: dict) -> str:
    """Como o perito reconhece este laudo na lista."""
    admin = estado.get("admin") or {}
    for chave in ("numero_laudo", "numero_demanda", "numero_procedimento", "envolvido"):
        valor = str(admin.get(chave, "")).strip()
        if valor:
            return valor
    return "sem número ainda"


def salvar(laudo_id: str, estado: dict) -> None:
    """Grava o rascunho. ``estado`` é o ``session_state`` (ou um dict igual).

    Escrita atômica: o JSON vai para um arquivo temporário e só então substitui
    o anterior. Uma falha no meio do caminho não corrompe o que já estava salvo.
    """
    pasta = _pasta(laudo_id)
    pasta.mkdir(parents=True, exist_ok=True)

    conteudo = {chave: estado.get(chave) for chave in CHAVES}

    # As imagens saem do JSON: cada uma vira um arquivo, e o JSON guarda só a
    # referência. Arquivo já gravado não é reescrito — a assinatura é do
    # conteúdo, então conteúdo igual é arquivo igual.
    pasta_imagens = pasta / "imagens"
    referencias = []
    for imagem in estado.get(_IMAGENS) or []:
        assinatura = str(imagem.get("assinatura", "")).strip()
        dados = imagem.get("dados")
        if not assinatura or not dados:
            continue
        pasta_imagens.mkdir(parents=True, exist_ok=True)
        arquivo = pasta_imagens / f"{assinatura}.bin"
        if not arquivo.exists():
            arquivo.write_bytes(dados)
        referencias.append(
            {
                "assinatura": assinatura,
                "nome": imagem.get("nome", ""),
                "material": imagem.get("material", 1),
                "legenda": imagem.get("legenda", ""),
            }
        )
    conteudo[_IMAGENS] = referencias
    conteudo["_meta"] = {
        "id": laudo_id,
        "atualizado_em": datetime.now().isoformat(timespec="seconds"),
        "rotulo": _rotulo(estado),
        "campos_preenchidos": _conta_preenchidos(estado),
    }

    destino = pasta / "laudo.json"
    temporario = pasta / "laudo.json.parcial"
    temporario.write_text(
        json.dumps(conteudo, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    os.replace(temporario, destino)


def carregar(laudo_id: str) -> dict | None:
    """Estado gravado, pronto para voltar ao ``session_state``. None se não há."""
    arquivo = _pasta(laudo_id) / "laudo.json"
    if not arquivo.exists():
        return None
    try:
        conteudo = json.loads(arquivo.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None

    estado = {chave: conteudo.get(chave) for chave in CHAVES}

    pasta_imagens = _pasta(laudo_id) / "imagens"
    imagens = []
    for referencia in conteudo.get(_IMAGENS) or []:
        arquivo_imagem = pasta_imagens / f"{referencia.get('assinatura', '')}.bin"
        if not arquivo_imagem.exists():
            # A foto sumiu do disco: melhor o laudo voltar sem ela, e o perito
            # ver que falta, do que não voltar.
            continue
        imagens.append({**referencia, "dados": arquivo_imagem.read_bytes()})
    estado[_IMAGENS] = imagens
    return estado


def listar() -> list[Rascunho]:
    """Rascunhos salvos, do mais recente para o mais antigo."""
    base = pasta_base()
    if not base.exists():
        return []
    encontrados: list[Rascunho] = []
    for pasta in base.iterdir():
        arquivo = pasta / "laudo.json"
        if not arquivo.exists():
            continue
        try:
            conteudo = json.loads(arquivo.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        meta = conteudo.get("_meta") or {}
        encontrados.append(
            Rascunho(
                id=meta.get("id", pasta.name),
                exame_id=conteudo.get("exame_id") or "",
                rotulo=meta.get("rotulo", "sem número ainda"),
                atualizado_em=meta.get("atualizado_em", ""),
                campos_preenchidos=int(meta.get("campos_preenchidos", 0) or 0),
            )
        )
    return sorted(encontrados, key=lambda r: r.atualizado_em, reverse=True)


def descartar(laudo_id: str) -> None:
    """Apaga o rascunho e as fotos dele. Ação do perito, nunca automática."""
    shutil.rmtree(_pasta(laudo_id), ignore_errors=True)


def assinatura_do_estado(estado: dict) -> str:
    """Impressão do que está salvo, para gravar só quando algo mudou.

    O Streamlit re-executa o script inteiro a cada clique; gravar em todas as
    execuções escreveria o mesmo arquivo dezenas de vezes por laudo.
    """
    resumo = {chave: estado.get(chave) for chave in CHAVES}
    resumo[_IMAGENS] = [
        (i.get("assinatura"), i.get("legenda"), i.get("material"))
        for i in (estado.get(_IMAGENS) or [])
    ]
    try:
        return json.dumps(resumo, ensure_ascii=False, sort_keys=True, default=str)
    except (TypeError, ValueError):
        return ""
