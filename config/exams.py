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

from config.schema import CampoAdmin, Colecao, Etapa, Exame, GrupoAdmin, Secao, Slot

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
            referencia_colecao="materiais",
            pergunta="Esse exame se aplica a qual material?",
            instrucao_extracao=(
                "Índice do material a que este exame se refere, começando em 1. "
                "Se o histórico deixa claro qual material está sendo descrito, "
                "use esse índice. Se AMBÍGUO ou não houver material registrado "
                "ainda, deixe vazio — a ferramenta pedirá pra clarificar. NUNCA "
                "invente vínculo."
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

_ETAPAS_SUBSTANCIA = (
    Etapa(
        titulo="Identificação do material",
        objetivo=(
            "capturar, para cada porção de material examinado, a massa líquida "
            "com unidade, a forma física, a coloração e o acondicionamento "
            "(quantidade e tipo de invólucros)."
        ),
        colecao="materiais",
    ),
    Etapa(
        titulo="Exames realizados",
        objetivo=(
            "para cada material, registrar os ensaios feitos, com o nome do "
            "teste, o resultado (positivo, negativo ou inconclusivo) e — quando "
            "positivo — a substância identificada."
        ),
        colecao="exames_realizados",
    ),
    Etapa(
        titulo="Quesitos da requisição",
        objetivo=(
            "responder, um por um, os quesitos formulados pela autoridade. "
            "Quando houver padrão do Instituto, oferecer para confirmação; "
            "quando não houver, o perito escreve a resposta."
        ),
        quesitos=True,
    ),
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
    etapas=_ETAPAS_SUBSTANCIA,
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
            referencia_colecao="veiculos",
            instrucao_extracao=(
                "Índice do veículo a que este sinal se refere, começando em 1. "
                "Se o histórico deixa claro qual veículo está sendo examinado, "
                "use esse índice. Se AMBÍGUO, deixe vazio — a ferramenta pedirá "
                "pra clarificar. NUNCA invente vínculo."
            ),
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
            instrucao_extracao=(
                "Local da gravação como o perito descreveu, COM o particípio "
                "que o laudo imprime entre parênteses: 'gravados no setor "
                "posterior do chassi', 'gravada no bloco', 'gravados na base do "
                "guidão, lado direito'. Sem o particípio o parêntese do laudo "
                "sai truncado."
            ),
        ),
        Slot(
            chave="caracteres_divergentes",
            label="Caracteres divergentes",
            obrigatorio=False,
            pergunta="Quais caracteres divergiam do padrão de fábrica?",
            instrucao_extracao=(
                "APENAS o sujeito da frase, sem verbo: 'todos os caracteres', "
                "'o 17º caractere'. O laudo completa com 'apresentavam formato, "
                "profundidade e tamanho divergente...', então guardar a oração "
                "inteira ('todos os caracteres divergiam do padrão') duplica o "
                "verbo e quebra a frase do documento. Se o perito disser a "
                "oração completa, registre só o sujeito dela."
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

_ETAPAS_VEICULAR = (
    Etapa(
        titulo="Identificação do veículo",
        objetivo=(
            "capturar os dados de identificação do veículo apresentado: tipo, "
            "marca e modelo, cor, placa (se exibida) e os lacres que o "
            "acompanham."
        ),
        colecao="veiculos",
    ),
    Etapa(
        titulo="Exame dos sinais identificadores",
        objetivo=(
            "para cada sinal identificador examinado (NIV, Motor ou Placa), "
            "registrar a numeração observada, o local da gravação, os "
            "caracteres divergentes, o tratamento aplicado e o resultado da "
            "revelação."
        ),
        colecao="exames_veiculo",
    ),
    Etapa(
        titulo="Quesitos da requisição",
        objetivo=(
            "responder, um por um, os quesitos formulados pela autoridade. "
            "Quando houver padrão do Instituto, oferecer para confirmação; "
            "quando não houver, o perito escreve a resposta."
        ),
        quesitos=True,
    ),
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
    etapas=_ETAPAS_VEICULAR,
    secoes=_SECOES_VEICULAR,
    imagens_em_apendice=True,
)

# --------------------------------------------------------------------------
# Verificação de Danos (Perícias Externas)
# --------------------------------------------------------------------------

_ADMIN_DANOS = (
    CampoAdmin(
        chave="numero_demanda",
        da_requisicao=True,
        label="Número da demanda",
        ajuda="Ex.: 00016037-31.",
    ),
    CampoAdmin(
        chave="data_exame",
        da_requisicao=True,
        label="Data de recebimento da solicitação",
        tipo="data",
        ajuda="Abre o preâmbulo do laudo.",
    ),
    CampoAdmin(
        chave="hora_recebimento",
        da_requisicao=True,
        label="Hora de recebimento",
        ajuda="Como está no carimbo, ex.: 17h50min.",
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
        ajuda=(
            "Com o artigo, como entra na frase: do ofício n.º 001/CORREG - APFD, "
            "ou da requisição n.º 002571/18. O artigo comanda a concordância do "
            "preâmbulo."
        ),
    ),
    CampoAdmin(
        chave="data_documento",
        da_requisicao=True,
        label="Data do documento de solicitação",
        tipo="data",
    ),
    CampoAdmin(
        chave="subscritor",
        da_requisicao=True,
        label="Quem subscreveu a solicitação",
        ajuda="Como consta no documento, ex.: CAP PM Ferdinand Lira (Presidente do Inquérito).",
    ),
    CampoAdmin(
        chave="finalidade",
        label="Finalidade do exame",
        tipo="select",
        opcoes=(
            "Exame Pericial para Verificação de Danos",
            "Exame Pericial em Local para Verificação de Danos",
        ),
        ajuda="As duas formas transcritas dos laudos reais.",
    ),
    CampoAdmin(chave="perito_designado", label="Perito designado"),
    CampoAdmin(chave="matricula", label="Matrícula"),
    CampoAdmin(
        chave="classe_perito",
        label="Classe do perito",
        obrigatorio=False,
        ajuda="Como sai no rodapé da assinatura, ex.: Especial.",
    ),
)

_LOCAIS = Colecao(
    chave="locais",
    label_singular="Local",
    label_plural="Locais examinados",
    minimo=1,
    aceita_imagens=True,
    pergunta_mais_um="Há mais algum local examinado?",
    slots=(
        Slot(
            chave="endereco_local",
            label="Endereço do local",
            pergunta="Onde fica o local que você examinou?",
            instrucao_extracao=(
                "Endereço do local da ocorrência como o perito o descreveu, "
                "transcrito sem completar com dados que ele não disse."
            ),
        ),
        Slot(
            chave="hora_comunicacao",
            label="Hora da comunicação",
            pergunta="A que horas você foi comunicado da ocorrência?",
            instrucao_extracao=(
                "Hora em que o perito foi comunicado, na grafia dos laudos: "
                "17h50min. Transcrever o que ele disse, sem arredondar."
            ),
        ),
        Slot(
            chave="hora_chegada",
            label="Hora de chegada ao local",
            pergunta="A que horas você chegou ao local?",
            instrucao_extracao=(
                "Hora de chegada ao local, na grafia dos laudos: 18h10min. "
                "Transcrever o que ele disse, sem arredondar."
            ),
        ),
        Slot(
            chave="recepcao",
            label="Quem recebeu o perito",
            obrigatorio=False,
            pergunta="Alguém recebeu você no local? Se sim, quem?",
            instrucao_extracao=(
                "Quem recebeu o perito no local, como ele descreveu — ex.: um "
                "Servidor da Prefeitura Municipal desta capital, que prestou ao "
                "perito todas as informações necessárias. Vazio se ninguém o "
                "recebeu."
            ),
        ),
        Slot(
            chave="natureza",
            label="Natureza da área",
            opcoes=("interna", "externa"),
            opcoes_fechadas=True,
            pergunta="A área examinada é interna ou externa?",
            instrucao_extracao="Um destes: interna ou externa.",
        ),
        Slot(
            chave="idoneidade",
            label="Idoneidade para perícia",
            opcoes=("idônea", "inidônea"),
            opcoes_fechadas=True,
            pergunta="O local estava idôneo ou inidôneo para efeito de perícia?",
            instrucao_extracao="Um destes: idônea ou inidônea.",
        ),
        Slot(
            chave="motivo_inidoneidade",
            label="Motivo da inidoneidade",
            obrigatorio=False,
            obrigatorio_se=("idoneidade", "inidônea"),
            pergunta="Por que o local estava inidôneo para perícia?",
            instrucao_extracao=(
                "Motivo da inidoneidade com as palavras do perito — o que foi "
                "alterado, o que não foi preservado. Não acrescentar causa que "
                "ele não citou."
            ),
        ),
        Slot(
            chave="descricao_local",
            label="Descrição do local",
            pergunta="Descreva o local: o que é, como é, o que interessa à perícia.",
            instrucao_extracao=(
                "Descrição do local com as palavras do perito, transcrita "
                "inteira, sem acrescentar característica que ele não descreveu."
            ),
        ),
        Slot(
            chave="meio_instrumento",
            label="Meio ou instrumento que produziu os danos",
            obrigatorio=False,
            pergunta=(
                "Com que meio ou instrumento os danos são compatíveis? "
                "(entra na abertura das constatações e responde o quesito do meio)"
            ),
            instrucao_extracao=(
                "Meio ou instrumento a que o perito atribuiu os danos, com as "
                "palavras dele — ex.: meio de força física direta, além do "
                "auxílio de instrumento contundente. NUNCA deduzir da descrição "
                "dos danos: só entra se ele disser."
            ),
        ),
    ),
)

_DANOS = Colecao(
    chave="danos",
    label_singular="Dano constatado",
    label_plural="Danos constatados",
    minimo=1,
    vinculada_a="locais",
    pergunta_mais_um="Constatou mais algum dano neste local?",
    slots=(
        Slot(
            chave="descricao",
            label="Descrição do dano",
            pergunta="Descreva o dano constatado.",
            instrucao_extracao=(
                "Um dano constatado, com as palavras do perito. Cada dano "
                "distinto é um item próprio. Transcrever sem acrescentar "
                "extensão, causa ou objeto que ele não citou."
            ),
        ),
        Slot(
            chave="item_material",
            label="Local examinado",
            referencia_colecao="locais",
            instrucao_extracao=(
                "Índice do local a que este dano se refere, começando em 1. Se "
                "o histórico deixa claro qual local está sendo examinado, use "
                "esse índice. Se AMBÍGUO, deixe vazio. NUNCA invente vínculo."
            ),
        ),
    ),
)

_ETAPAS_DANOS = (
    Etapa(
        titulo="Local examinado",
        objetivo=(
            "capturar onde foi a ocorrência, a que horas o perito foi "
            "comunicado e chegou, quem o recebeu, se a área é interna ou "
            "externa, se estava idônea para perícia, e a descrição do local."
        ),
        colecao="locais",
    ),
    Etapa(
        titulo="Danos constatados",
        objetivo=(
            "registrar, um a um, os danos que o perito constatou no local, com "
            "as palavras dele."
        ),
        colecao="danos",
    ),
    Etapa(
        titulo="Quesitos da requisição",
        objetivo=(
            "responder, um por um, os quesitos formulados pela autoridade. "
            "Quando houver padrão do Instituto, oferecer para confirmação; "
            "quando não houver, o perito escreve a resposta."
        ),
        quesitos=True,
    ),
)

#: Ordem das seções dos laudos reais 00016037-31 e 00016160-22. Sem tópico de
#: referências; as imagens saem no corpo, logo após as constatações.
_SECOES_DANOS = (
    Secao("cabecalho"),
    Secao("preambulo"),
    Secao("texto", "1. HISTÓRICO", "HISTORICO"),
    Secao("texto", "2. DO OBJETIVO DA PERÍCIA", "OBJETIVO"),
    Secao("resultados", "3. DOS EXAMES"),
    Secao("imagens"),
    Secao("conclusao", "4. CONCLUSÃO"),
    Secao("quesitos"),
    Secao("fecho"),
    Secao("assinatura"),
)

VERIFICACAO_DANOS = Exame(
    id="verificacao_danos",
    template="identificacao_danos",
    label="Verificação de Danos (Perícias Externas)",
    descricao=(
        "Exame pericial em local para verificação de danos materiais: "
        "descrição do local, constatação dos danos e resposta aos quesitos."
    ),
    campos_admin=_ADMIN_DANOS,
    colecoes=(_LOCAIS, _DANOS),
    etapas=_ETAPAS_DANOS,
    secoes=_SECOES_DANOS,
)

# --------------------------------------------------------------------------
# Registro
# --------------------------------------------------------------------------

EXAMES: dict[str, Exame] = {
    IDENTIFICACAO_SUBSTANCIA.id: IDENTIFICACAO_SUBSTANCIA,
    IDENTIFICACAO_VEICULAR.id: IDENTIFICACAO_VEICULAR,
    VERIFICACAO_DANOS.id: VERIFICACAO_DANOS,
}


def listar_exames() -> list[Exame]:
    return list(EXAMES.values())


def obter_exame(exame_id: str) -> Exame:
    return EXAMES[exame_id]
