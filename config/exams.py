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

from config.schema import CampoAdmin, Colecao, Exame, GrupoAdmin, Secao, Slot

# --------------------------------------------------------------------------
# Identificação de Substância (Química Forense)
# --------------------------------------------------------------------------

_ADMIN_IDENTIFICACAO = (
    CampoAdmin(
        chave="numero_laudo",
        label="Número do laudo",
        ajuda="Como aparece no cabeçalho, ex.: SB 1252/2019.",
    ),
    CampoAdmin(
        chave="numero_demanda",
        da_requisicao=True,
        label="Número da demanda",
        ajuda="Ex.: 00024529-28.",
    ),
    CampoAdmin(
        chave="data_exame",
        da_requisicao=True,
        label="Data de recebimento da solicitação",
        tipo="data",
        ajuda=(
            "A data do carimbo de recebimento no Instituto — é ela que abre o "
            "preâmbulo do laudo, não a data em que o exame foi bancado."
        ),
    ),
    CampoAdmin(
        chave="orgao_solicitante",
        da_requisicao=True,
        label="Órgão solicitante",
        ajuda="Delegacia ou unidade que requisitou o exame.",
    ),
    CampoAdmin(
        chave="documento_solicitacao",
        da_requisicao=True,
        label="Documento de solicitação",
        ajuda="Ofício, requisição ou memorando que originou o exame.",
    ),
    CampoAdmin(
        chave="data_documento",
        da_requisicao=True,
        label="Data do documento de solicitação",
        tipo="data",
        ajuda="A data do ofício, que o laudo cita separada da data do exame.",
    ),
    CampoAdmin(
        chave="tipo_procedimento",
        da_requisicao=True,
        label="Tipo de procedimento",
        tipo="select",
        opcoes=("IP", "APF", "BO"),
    ),
    CampoAdmin(
        chave="numero_procedimento",
        da_requisicao=True,
        label="Número do procedimento",
    ),
    CampoAdmin(
        chave="envolvido",
        da_requisicao=True,
        label="Envolvido",
    ),
    CampoAdmin(
        chave="data_apreensao",
        da_requisicao=True,
        label="Data da apreensão",
        tipo="data",
        obrigatorio=False,
        ajuda=(
            "Consta da requisição. Faz parte da cadeia de custódia; o laudo de "
            "referência não a imprime."
        ),
    ),
    CampoAdmin(
        chave="local_apreensao",
        da_requisicao=True,
        label="Local da apreensão",
        obrigatorio=False,
        ajuda=(
            "Consta da requisição. Faz parte da cadeia de custódia; o laudo de "
            "referência não o imprime."
        ),
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
        chave="classe_perito",
        label="Classe do perito",
        obrigatorio=False,
        ajuda="Aparece sob a assinatura, ex.: Primeira Classe.",
    ),
    CampoAdmin(
        chave="protocolo_sbs",
        label="Protocolo no Laboratório de Análises",
        ajuda="Ex.: SBI0302/2019.",
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
            exige_valor_exato=True,
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
            chave="massa_bruta_valor",
            label="Massa bruta",
            obrigatorio=False,
            exige_valor_exato=True,
            pergunta="Qual a massa bruta, com a embalagem?",
            instrucao_extracao=(
                "Valor numérico da massa bruta (com embalagem) medida pelo perito. "
                "Não converter unidades nem arredondar."
            ),
        ),
        Slot(
            chave="massa_bruta_unidade",
            label="Unidade da massa bruta",
            obrigatorio=False,
            obrigatorio_se=("massa_bruta_valor", "*"),
            pergunta="Em que unidade está a massa bruta?",
            instrucao_extracao="Unidade da massa bruta, exatamente como dita.",
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
            exige_valor_exato=True,
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
    vinculada_a="materiais",
    pergunta_mais_um="Foi realizado mais algum exame neste material?",
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
            na_conversa=False,
            referencia_colecao="materiais",
            pergunta="Esse exame se aplica a qual material?",
            instrucao_extracao=(
                "Não extrair: a ferramenta preenche pelo material de que a "
                "conversa está tratando."
            ),
        ),
        Slot(
            chave="resultado",
            label="Resultado",
            pergunta="O resultado foi positivo, negativo ou inconclusivo?",
            instrucao_extracao=(
                "Resultado declarado pelo perito: 'positivo', 'negativo' ou "
                "'inconclusivo'."
            ),
            opcoes=("positivo", "negativo", "inconclusivo"),
            opcoes_fechadas=True,
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
        Slot(
            chave="procedimento",
            label="Como o ensaio foi conduzido",
            obrigatorio=False,
            exigido_sem_redacao=True,
            pergunta=(
                "Não tenho a redação institucional deste ensaio. Conte como você "
                "o conduziu — reagente ou padrão usado, o que foi observado — que "
                "eu redijo o parágrafo com as suas palavras."
            ),
            instrucao_extracao=(
                "Descrição, com as palavras do perito, de como o ensaio foi "
                "conduzido: reagentes, padrões, equipamento, o que foi observado. "
                "Transcrever sem acrescentar etapa que ele não mencionou."
            ),
        ),
    ),
)

#: Ordem das seções do laudo de identificação de substância, como no laudo real
#: SB 1252/2019. Cada tipo de exame declara a sua: identificação veicular, por
#: exemplo, não tem histórico nem referências.
_SECOES_IDENTIFICACAO = (
    Secao("cabecalho"),
    Secao("preambulo"),
    Secao("texto", "1. HISTÓRICO", "HISTORICO,HISTORICO_FECHO"),
    Secao("objetos", "2. IDENTIFICAÇÃO E DESCRIÇÃO DO MATERIAL", "materiais"),
    Secao("exames", "3. EXAMES REALIZADOS"),
    Secao("resultados", "4. RESULTADOS OBTIDOS"),
    Secao("conclusao", "5. CONCLUSÃO"),
    Secao("quesitos"),
    Secao("referencias", "6. REFERÊNCIAS"),
    Secao("fecho"),
    Secao("assinatura"),
)

IDENTIFICACAO_SUBSTANCIA = Exame(
    id="identificacao_substancia",
    template="identificacao_substancia",
    secoes=_SECOES_IDENTIFICACAO,
    label="Identificação de Substância (Química Forense)",
    descricao=(
        "Exame de identificação de substância entorpecente: descrição do "
        "material apreendido, ensaios realizados e conclusão."
    ),
    campos_admin=_ADMIN_IDENTIFICACAO,
    colecoes=(_MATERIAL, _EXAMES_REALIZADOS),
)

# --------------------------------------------------------------------------
# Identificação Veicular
# --------------------------------------------------------------------------

_ADMIN_VEICULAR = (
    CampoAdmin(
        chave="numero_demanda",
        da_requisicao=True,
        label="Número da demanda",
        ajuda="Ex.: 00078413-75.",
    ),
    CampoAdmin(
        chave="data_exame",
        da_requisicao=True,
        label="Data de recebimento da solicitação",
        tipo="data",
        ajuda="Abre o preâmbulo do laudo.",
    ),
    CampoAdmin(
        chave="orgao_solicitante",
        da_requisicao=True,
        label="Órgão solicitante",
    ),
    CampoAdmin(
        chave="documento_solicitacao",
        da_requisicao=True,
        label="Documento de solicitação",
        ajuda="Ex.: do Ofício 14744/2024, ou da Requisição S/N.",
    ),
    CampoAdmin(
        chave="tipo_procedimento",
        da_requisicao=True,
        label="Tipo de procedimento",
        tipo="select",
        opcoes=("BO", "IP", "APF"),
    ),
    CampoAdmin(
        chave="numero_procedimento",
        da_requisicao=True,
        label="Número do procedimento",
    ),
    CampoAdmin(
        chave="data_realizacao",
        label="Data de realização do exame",
        tipo="data",
        ajuda="Pode ser bem depois do recebimento; é a data que vai na seção 1.",
    ),
    CampoAdmin(
        chave="local_exame",
        label="Local do exame",
        ajuda="Ex.: pátio da Central de Flagrantes, Teresina-PI.",
    ),
    CampoAdmin(
        chave="data_encerramento",
        label="Data de encerramento do laudo",
        tipo="data",
        ajuda="Vai no fecho: 'deu-se por findo, em ...'.",
    ),
)

#: Peritos signatários: os laudos reais trazem um ou dois, com matrícula própria.
_PERITOS = GrupoAdmin(
    chave="peritos",
    label_singular="Perito signatário",
    minimo=1,
    campos=(
        CampoAdmin(chave="perito_designado", label="Nome do perito"),
        CampoAdmin(chave="matricula", label="Matrícula"),
    ),
)

_VEICULOS = Colecao(
    chave="veiculos",
    label_singular="Veículo",
    label_plural="Veículos",
    minimo=1,
    aceita_imagens=True,
    pergunta_mais_um="Há mais algum veículo examinado?",
    slots=(
        Slot(
            chave="tipo_veiculo",
            label="Tipo do veículo",
            pergunta="Que tipo de veículo é? (motocicleta, motoneta, automóvel…)",
            instrucao_extracao="Tipo do veículo conforme dito pelo perito.",
        ),
        Slot(
            chave="marca_modelo",
            label="Marca e modelo",
            pergunta="Qual a marca e o modelo?",
            instrucao_extracao="Marca e modelo como o perito disse, ex.: HONDA/BIZ 110I.",
        ),
        Slot(
            chave="cor",
            label="Cor",
            pergunta="Qual a cor do veículo?",
            instrucao_extracao="Cor do veículo conforme descrita pelo perito.",
        ),
        Slot(
            chave="placa",
            label="Placa",
            obrigatorio=False,
            pergunta="O veículo exibe placa? Se sim, qual?",
            instrucao_extracao=(
                "Placa exibida pelo veículo. Se o perito disser que não há placa, "
                "deixar vazio."
            ),
        ),
        Slot(
            chave="lacres",
            label="Lacres",
            obrigatorio=False,
            pergunta="Quais lacres acompanham o veículo?",
            instrucao_extracao="Lacres citados pelo perito, com os números.",
        ),
        Slot(
            chave="abertura",
            label="Abertura da descrição",
            obrigatorio=False,
            na_conversa=False,
            opcoes=("Trata-se da", "Foi apresentada a", "Foi apresentado o"),
        ),
    ),
)

_EXAMES_VEICULO = Colecao(
    chave="exames_veiculo",
    label_singular="Sinal identificador",
    label_plural="Sinais identificadores examinados",
    minimo=1,
    vinculada_a="veiculos",
    pergunta_mais_um="Examinou mais algum sinal identificador neste veículo?",
    slots=(
        Slot(
            chave="identificador",
            label="Sinal identificador",
            opcoes=("NIV", "Motor", "Placa"),
            opcoes_fechadas=True,
            pergunta="Qual sinal identificador foi examinado: NIV, Motor ou Placa?",
            instrucao_extracao="Um destes: NIV, Motor ou Placa.",
        ),
        Slot(
            chave="item_material",
            label="Veículo examinado",
            na_conversa=False,
            referencia_colecao="veiculos",
            instrucao_extracao="Não extrair: a ferramenta preenche pelo veículo em foco.",
        ),
        Slot(
            chave="numeracao_observada",
            label="Numeração observada",
            obrigatorio_se=("identificador", "NIV"),
            obrigatorio=False,
            pergunta="Qual a numeração gravada que você observou?",
            instrucao_extracao="Numeração lida no veículo, exatamente como está gravada.",
        ),
        Slot(
            chave="local_gravacao",
            label="Local da gravação",
            obrigatorio=False,
            pergunta="Onde fica essa gravação no veículo?",
            instrucao_extracao="Local da gravação conforme descrito pelo perito.",
        ),
        Slot(
            chave="caracteres_divergentes",
            label="Caracteres divergentes",
            obrigatorio=False,
            pergunta="Quais caracteres divergiam do padrão de fábrica?",
            instrucao_extracao=(
                "Quais caracteres divergiam, como o perito disse — ex.: 'todos os "
                "caracteres' ou 'o 17º caractere'."
            ),
        ),
        Slot(
            chave="tratamento",
            label="Tratamento aplicado",
            obrigatorio=False,
            opcoes=(
                "reagentes em liga metálica",
                "reagentes em ferro e aço",
                "somente observação óptica",
            ),
            pergunta="Que tratamento você aplicou para tentar revelar a gravação?",
            instrucao_extracao="Tratamento aplicado, entre os que o perito citar.",
        ),
        Slot(
            chave="resultado_revelacao",
            label="Resultado da revelação",
            obrigatorio=False,
            opcoes=("positivo", "negativo"),
            opcoes_fechadas=True,
            pergunta="A revelação da numeração original foi positiva ou negativa?",
            instrucao_extracao="Resultado da revelação: 'positivo' ou 'negativo'.",
        ),
        Slot(
            chave="numeracao_revelada",
            label="Numeração revelada",
            obrigatorio=False,
            obrigatorio_se=("resultado_revelacao", "positivo"),
            pergunta="Qual numeração original foi revelada?",
            instrucao_extracao="Numeração original revelada pelos exames.",
        ),
        Slot(
            chave="descricao_placa",
            label="Descrição do exame da placa",
            obrigatorio=False,
            obrigatorio_se=("identificador", "Placa"),
            pergunta="Descreva o que você constatou na placa.",
            instrucao_extracao=(
                "Descrição do exame da placa com as palavras do perito: lacre, "
                "estado, consulta a sistema e conclusão sobre autenticidade."
            ),
        ),
    ),
)

_SECOES_VEICULAR = (
    Secao("cabecalho"),
    Secao("preambulo"),
    Secao("objetos", "1. DO VEÍCULO", "veiculos"),
    Secao("resultados", "2. EXAMES", "exames_veiculo"),
    Secao("conclusao", "3. CONCLUSÃO"),
    Secao("quesitos"),
    Secao("fecho"),
    Secao("assinatura"),
    Secao("apendice"),
)

IDENTIFICACAO_VEICULAR = Exame(
    id="identificacao_veicular",
    template="identificacao_veicular",
    label="Identificação Veicular",
    descricao=(
        "Exame dos sinais identificadores de veículo — NIV, número do motor e "
        "placa — para constatar adulteração e revelar a numeração original."
    ),
    campos_admin=_ADMIN_VEICULAR,
    grupos_admin=(_PERITOS,),
    colecoes=(_VEICULOS, _EXAMES_VEICULO),
    secoes=_SECOES_VEICULAR,
    imagens_em_apendice=True,
)

# --------------------------------------------------------------------------
# Registro
# --------------------------------------------------------------------------

EXAMES: dict[str, Exame] = {
    IDENTIFICACAO_SUBSTANCIA.id: IDENTIFICACAO_SUBSTANCIA,
    IDENTIFICACAO_VEICULAR.id: IDENTIFICACAO_VEICULAR,
}


def listar_exames() -> list[Exame]:
    return list(EXAMES.values())


def obter_exame(exame_id: str) -> Exame:
    return EXAMES[exame_id]
