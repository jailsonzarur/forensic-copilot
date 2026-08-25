"""Registro de exames — fonte única da UI.

Adicionar um laudo novo = adicionar uma entrada em ``EXAMES``. O select da tela
de seleção, os campos do formulário administrativo e os slots da conversa saem
todos daqui.

ATENÇÃO — os slots de ``identificacao_substancia`` são uma PROPOSTA a ser
validada contra os 4 laudos reais do Instituto de Criminalística da PC-PI antes
de virar UI de conversa (CHECKPOINT do Milestone 2). Nenhum valor de exemplo
entra em ``instrucao_extracao``: as instruções descrevem o formato do dado, não
sugerem conteúdo.
"""

from __future__ import annotations

from config.schema import CampoAdmin, Colecao, Exame, Slot

# --------------------------------------------------------------------------
# Identificação de Substância (Química Forense)
# --------------------------------------------------------------------------

_ADMIN_IDENTIFICACAO = (
    CampoAdmin(
        chave="data_exame",
        label="Data do exame",
        tipo="data",
    ),
    CampoAdmin(
        chave="orgao_solicitante",
        label="Órgão solicitante",
        ajuda="Delegacia ou unidade que requisitou o exame.",
    ),
    CampoAdmin(
        chave="documento_solicitacao",
        label="Documento de solicitação",
        ajuda="Ofício, requisição ou memorando que originou o exame.",
    ),
    CampoAdmin(
        chave="tipo_procedimento",
        label="Tipo de procedimento",
        tipo="select",
        opcoes=("IP", "APF", "BO"),
    ),
    CampoAdmin(
        chave="numero_procedimento",
        label="Número do procedimento",
    ),
    CampoAdmin(
        chave="envolvido",
        label="Envolvido",
    ),
    CampoAdmin(
        chave="perito_designado",
        label="Perito designado",
    ),
    CampoAdmin(
        chave="matricula",
        label="Matrícula",
    ),
    CampoAdmin(
        chave="numero_demanda",
        label="Número da demanda",
        obrigatorio=False,
    ),
    CampoAdmin(
        chave="protocolo_sbs",
        label="Protocolo (SBS)",
        obrigatorio=False,
    ),
)

_MATERIAL = Colecao(
    chave="materiais",
    label_singular="Material",
    label_plural="Materiais",
    minimo=1,
    aceita_imagens=True,
    pergunta_mais_um="Há mais algum material a ser descrito?",
    slots=(
        Slot(
            chave="massa_liquida_valor",
            label="Massa líquida",
            pergunta="Qual a massa líquida do material?",
            instrucao_extracao=(
                "Valor numérico da massa líquida medida pelo perito, como "
                "número decimal. Não converter unidades nem arredondar."
            ),
        ),
        Slot(
            chave="massa_liquida_unidade",
            label="Unidade da massa",
            pergunta="Em que unidade está essa massa (g, kg)?",
            instrucao_extracao=(
                "Unidade em que o perito declarou a massa, exatamente como dita."
            ),
        ),
        Slot(
            chave="forma_fisica",
            label="Forma / tipo físico",
            pergunta="Qual a forma física do material?",
            instrucao_extracao=(
                "Descrição da forma física do material feita pelo perito, "
                "transcrita sem acrescentar características não ditas."
            ),
        ),
        Slot(
            chave="coloracao",
            label="Coloração",
            pergunta="Qual a coloração do material?",
            instrucao_extracao="Cor do material conforme descrita pelo perito.",
        ),
        Slot(
            chave="acondicionamento_quantidade",
            label="Quantidade de invólucros",
            pergunta="Em quantos invólucros o material estava acondicionado?",
            instrucao_extracao=(
                "Número inteiro de invólucros contado pelo perito. Se ele não "
                "disser um número, deixar vazio — nunca estimar."
            ),
        ),
        Slot(
            chave="acondicionamento_tipo",
            label="Tipo de acondicionamento",
            pergunta="Qual o tipo de acondicionamento desses invólucros?",
            instrucao_extracao=(
                "Tipo de embalagem/invólucro conforme descrito pelo perito."
            ),
        ),
        Slot(
            chave="observacoes",
            label="Observações",
            obrigatorio=False,
            pergunta="Alguma observação adicional sobre este material?",
            instrucao_extracao=(
                "Observações adicionais ditas pelo perito sobre este material, "
                "como recipientes que o acompanham."
            ),
        ),
    ),
)

_EXAMES_REALIZADOS = Colecao(
    chave="exames_realizados",
    label_singular="Exame realizado",
    label_plural="Exames realizados",
    minimo=1,
    pergunta_mais_um="Foi realizado mais algum exame?",
    slots=(
        Slot(
            chave="nome_teste",
            label="Nome do teste",
            pergunta="Qual exame foi realizado?",
            instrucao_extracao=(
                "Nome do ensaio realizado pelo perito, conforme dito por ele."
            ),
            # Vocabulário conhecido dos laudos reais — sugestão de UI, não um
            # conjunto fechado: o perito pode nomear outro ensaio.
            opcoes=(
                "Ensaio de Scott Modificado",
                "Ensaio de Fast Blue B",
                "Espectrometria no Infravermelho (FTIR)",
                "Cromatografia em Camada Delgada (CCD)",
                "Análise botânica",
            ),
        ),
        Slot(
            chave="item_material",
            label="Material examinado",
            pergunta="Esse exame se aplica a qual material?",
            instrucao_extracao=(
                "Identificação do item de material ao qual o exame se aplica, "
                "referenciando os materiais já descritos pelo perito."
            ),
        ),
        Slot(
            chave="resultado",
            label="Resultado",
            pergunta="O resultado foi positivo ou negativo?",
            instrucao_extracao=(
                "Resultado declarado pelo perito: 'positivo' ou 'negativo'."
            ),
            opcoes=("positivo", "negativo"),
        ),
        Slot(
            chave="substancia",
            label="Substância identificada",
            obrigatorio=False,
            obrigatorio_se=("resultado", "positivo"),
            pergunta="Positivo para qual substância?",
            instrucao_extracao=(
                "Substância para a qual o resultado foi positivo, conforme dita "
                "pelo perito. Vazio quando o resultado for negativo."
            ),
        ),
    ),
)

IDENTIFICACAO_SUBSTANCIA = Exame(
    id="identificacao_substancia",
    label="Identificação de Substância (Química Forense)",
    descricao=(
        "Exame de identificação de substância entorpecente: descrição do "
        "material apreendido, ensaios realizados e conclusão."
    ),
    campos_admin=_ADMIN_IDENTIFICACAO,
    colecoes=(_MATERIAL, _EXAMES_REALIZADOS),
)

# --------------------------------------------------------------------------
# Registro
# --------------------------------------------------------------------------

EXAMES: dict[str, Exame] = {
    IDENTIFICACAO_SUBSTANCIA.id: IDENTIFICACAO_SUBSTANCIA,
}


def listar_exames() -> list[Exame]:
    return list(EXAMES.values())


def obter_exame(exame_id: str) -> Exame:
    return EXAMES[exame_id]
