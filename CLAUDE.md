# Gerador de Laudos Periciais com IA (forensic-copilot)

Iniciação científica para a Secretaria de Segurança Pública do Piauí (SSP-PI).
Ferramenta que ajuda **peritos criminais** a gerar **minutas de laudos periciais**
a partir de uma conversa guiada com um agente. O perito trabalha (inclusive em
campo), conversa com a ferramenta, e ao final recebe uma minuta no padrão dos
laudos oficiais para revisar, editar e assinar.

Este arquivo é a fonte de verdade do projeto. Leia antes de escrever código.

---

## Princípios inegociáveis (governam TODA decisão técnica)

- **Fidelidade.** A IA só reformata e estrutura o que o perito informou. Ela
  NUNCA inventa achados, pesos, medidas, número de invólucros, tipos de exame ou
  resultados. Dado faltante vira **PENDÊNCIA** (pergunta dirigida ao perito),
  nunca invenção. Se você se pegar preenchendo uma lacuna com um valor
  plausível, pare — é exatamente o erro que este projeto existe para evitar.
- **Transparência na recusa.** Toda vez que a ferramenta deixar de registrar
  algo, ela diz POR QUÊ, em termos do que o perito escreveu — citando o trecho
  que causou a recusa. Nada de resposta genérica do tipo "não identifiquei
  nenhum dado": sem o motivo, o perito repete a mesma frase e a pergunta volta
  igual, sem fim. A única mensagem padronizada permitida é a de falha de
  código (erro de rede, de autenticação, JSON inválido) — aí o problema não
  partiu da fala do perito e não há motivo do modelo para explicar.
- **Leitura de documento ≠ interpretação de prova.** Transcrever um ofício com
  visão do modelo é leitura de papel, e é permitido. Ler a FOTO DO MATERIAL para
  descrever, pesar ou contar é inferência sobre prova física, e continua
  proibido. A distinção é o tipo de objeto, não a tecnologia.
- **Transcrição de digitalização é rascunho, nunca fato.** Requisição chega
  digitalizada: OCR é o caso normal, não a exceção. A leitura segue a ordem
  camada de texto do PDF → **OCR do Tesseract** → modelo de visão (só sem
  Tesseract na máquina).
  Medido nesta requisição real: o modelo de visão reescreveu um quesito de três
  maneiras diferentes em três leituras, inventou endereço, e-mail e matrícula, e
  apagou a data da apreensão. O Tesseract, com a página endireitada, transcreveu
  os seis quesitos palavra por palavra e acertou a matrícula. **Os dois erram —
  mas o OCR erra produzindo ruído visível ("1P" por "IP") e o modelo erra
  produzindo prosa plausível que ninguém confere.** Por isso o OCR vem primeiro,
  e a transcrição fica à vista para o perito conferir contra o papel.
- **Humano no controle.** A saída é uma MINUTA. Sempre há tela de confirmação
  antes de gerar o documento, onde o perito revisa e edita. A responsabilidade
  legal é do perito. A ferramenta é assistente de redação, não perito
  automático.

Corolário para o código: nenhum default "esperto", nenhum valor de exemplo que
possa vazar para o laudo, nenhum campo boilerplate escrito de cabeça — texto
institucional só entra transcrito de laudo real.

Corolário da transparência: a explicação nunca pode depender de o modelo
lembrar de explicar, nem ser aceita sem conferência. Os motivos são um conjunto
fechado (`core.extracao.MOTIVOS`) com texto montado por template, e cada recusa
passa por três checagens antes de chegar ao perito:

1. motivo fora do conjunto é **descartado**, nunca renomeado para um parecido —
   renomear transforma erro do extrator em explicação confiante e falsa;
2. `aproximado` exige que a fala contenha palavra de estimativa ("em torno de",
   "cerca de", "uns"). Sem isso a recusa é erro do extrator e não aparece;
3. trecho citado tem que existir na mensagem do perito; citação inventada é
   removida.

Quando nada sobra — o extrator não gravou e não explicou, ou a explicação não
passou —, o código produz `sem_extracao`, que **assume a falha de leitura em vez
de culpar a mensagem do perito**. Dizer "sua mensagem não tinha dado" quando o
extrator é que falhou seria a mesma desonestidade das respostas genéricas.

Recusar também não pode ser o caminho fácil do modelo: unidade inesperada e
formato de número (vírgula, ponto, por extenso) nunca são motivo de recusa.

---

## Arquitetura (v1)

- **Streamlit puro.** Sem LangGraph no v1 (arquitetura de escala futura, quando
  entrarem os outros tipos de exame). Controle de fluxo via `st.session_state` +
  roteador de telas simples.
- **OpenAI (GPT)** como LLM, com dois papéis distintos e separados:
  1. **extração estruturada** do que o perito disse (saída JSON estrita);
  2. **geração do texto narrativo final** a partir dos dados já confirmados.
- **A conversa alterna material e exames DELE.** A ordem é `Material 1 →
  exames do Material 1 → Material 2 → exames do Material 2 → quesitos`, e não
  todos os materiais seguidos de todos os exames. Isso não é só ergonomia: com
  os exames vindo logo depois do material de que tratam, a pergunta "de qual
  material?" some — a referência é consequência de ONDE a conversa está, não
  algo perguntado de novo nem deduzido pelo extrator. `Colecao.vinculada_a`
  declara esse aninhamento no registro, e o encerramento passa a ser por item
  da coleção-mãe (`exames_realizados:1`).
- **A conversa termina nos quesitos.** Depois das coleções, o assistente
  pergunta, um a um, os quesitos transcritos da requisição. Onde existe padrão
  transcrito de laudo real, ele é OFERECIDO para o perito confirmar ("confirmo")
  — oferecer não é preencher, e a confirmação fica gravada como marca, não como
  texto, para a resposta continuar acompanhando os dados se ele corrigir uma
  substância depois. Quesito sem resposta trava o avanço: o laudo responde ao
  que a autoridade perguntou, e quem responde é o perito.
- **A pergunta é formulada, o que falta é calculado.** `core/pendencias.py`
  decide QUAIS campos faltam, sem modelo nenhum; `core/pergunta.py` só escolhe
  as palavras, podendo cobrir até três campos de uma vez. O modelo é proibido de
  sugerir resposta — "a coloração é branca?" plantaria no laudo um dado que o
  perito não disse. Se a formulação falhar, a pergunta determinística é usada.
- **Fluxo de telas:**
  `seleção do tipo de exame` → `requisição (anexo + leitura)` →
  `formulário admin (transcrição)` →
  `conversa (slot-filling)` → `verificação de pendências` →
  `confirmação (humano no controle)` → `geração + export .docx`
- **Registro de exames:** os tipos de exame vivem em `config/exams.py`. O select
  da UI, os campos do formulário admin e os slots da conversa saem TODOS desse
  registro. Adicionar um laudo novo no futuro = adicionar uma entrada. Manter
  esse padrão religiosamente: nada de UI hardcoded por tipo de exame.
- O **tipo de exame escolhido no select governa o fluxo** da conversa (cada
  laudo tem seu conjunto de slots e suas perguntas).

### Estrutura de diretórios

```
app.py                     # entrypoint + roteador de telas
config/
  schema.py                # dataclasses que descrevem um exame
  exams.py                 # REGISTRO de exames (fonte da UI)
core/
  state.py                 # session_state: init, navegação, helpers
  ocr.py                   # Tesseract: endireita a página e transcreve
  requisicao.py            # leitura do ofício: texto do PDF > OCR > visão
  quesitos.py              # perguntas da autoridade + padrão de resposta
  redacao.py               # formaliza o relato de procedimento do perito
  biblioteca.py            # redação institucional escrita por perito
  referencias.py           # base bibliográfica da seção 6
  conferencia.py           # requisitado × examinado (cadeia de custódia)
  numeros.py               # extenso de números, massas e datas
  derivados.py             # camada 3: descrições, conclusão, quesitos
  documento.py             # montagem do .docx
  llm.py                   # cliente OpenAI + parsing JSON defensivo
  extracao.py              # prompt de extração + merge validado no estado
  pendencias.py            # varredura de campos obrigatórios
  conversa.py              # controlador do slot-filling (sem Streamlit)
screens/
  selecao.py               # tela 1 — seleção do tipo de exame
  requisicao.py            # tela 2 — anexo e leitura da requisição
  admin.py                 # tela 2 — formulário administrativo
  conversa.py              # tela 3 — slot-filling (chat + painel de estado)
  confirmacao.py           # tela 4 — revisão editável + imagens + derivados
  documento.py             # tela 5 — minuta e download
templates/
  identificacao_substancia/boilerplate.py   # CAMADA 2 (texto fixo)
  identificacao_veicular/boilerplate.py     # CAMADA 2 (texto fixo)
  identificacao_danos/boilerplate.py        # CAMADA 2 (texto fixo)
referencia/                # laudos reais; fora do git (dados pessoais)
verificacao/
  fluxo.py                 # controlador, com extrator falso (sem API)
  referencias.py           # base da seção 6 e sua seleção (sem API)
  veicular.py              # laudo veicular contra os reais (sem API)
  danos.py                 # laudo de danos contra os reais (sem API)
  danos_ponta_a_ponta.py   # o laudo de danos pelas TELAS reais (sem API)
  biblioteca.py            # redação aprendida e pendências (sem API)
  tela_requisicao.py       # a tela do anexo pela UI real (sem API)
  requisicao.py            # consenso e descarte de leitura (sem API)
  confirmacao.py           # tela de revisão pela UI real (sem API)
  documento.py             # .docx conferido contra o laudo real (sem API)
  fidelidade.py            # tenta induzir invenção, com API real
```

---

## Modelo de campos em 3 camadas (o coração do design)

Nem todo campo do laudo é coletado na conversa. Separe SEMPRE em:

1. **Camada 1 — coletados na conversa.** Só o que depende do perito. Para
   identificação de substância: dados do material (massa, forma física, cor,
   acondicionamento) e os exames feitos com seus resultados.
2. **Camada 2 — boilerplate.** Texto fixo do template, que NÃO passa pelo LLM
   como criação: preâmbulo institucional (Instituto de Criminalística / DPTC /
   Polícia Civil do Piauí), parágrafos técnicos de descrição de cada exame
   (ensaio de Scott, Fast Blue B, FTIR com espectrômetro Bruker Alpha II, CCD),
   texto legal de proscrição (Portaria 344 SVS/MS, Lista F1, art. 170 do CPP),
   referências bibliográficas e fecho.
3. **Camada 3 — derivados.** Calculados da camada 1 e confirmados pelo perito na
   tela de confirmação: a conclusão (ex.: "POSITIVO para cocaína e THC"), a
   legenda da imagem e a referência "(vide imagem N)".

**Regra decorrente: a conversa só preenche a camada 1.** É isso que confina a
superfície de alucinação. O LLM não "escreve o laudo inteiro": ele preenche a
camada 1, deriva a camada 3 (para confirmação humana), e a camada 2 é template.

---

## O processo legal que a ferramenta tem que respeitar

Apreensão → **requisição da autoridade policial** → recebimento no Instituto →
exame → laudo que responde aos quesitos. Os dois primeiros elos são documento
de terceiro, não do perito:

- A requisição é o que **autoriza** o exame, e o laudo a cita no preâmbulo
  (órgão, número do ofício, data).
- **Os quesitos são da autoridade, não do Instituto.** Eles são CAMADA 1 —
  transcrição — e mudam a cada requisição. O que é boilerplate é o *padrão de
  resposta* de cada pergunta conhecida (`RESPOSTAS_CONHECIDAS`). Pergunta fora
  desse conjunto é respondida pelo perito, nunca por semelhança com outra.
- A data que abre o preâmbulo é a do **carimbo de recebimento**, não a data em
  que o exame foi bancado.
- **A descrição do material na requisição é suspeita da autoridade**
  ("aparentemente maconha", "semelhante a pasta base") e NÃO pode tocar a
  camada 1. O que vai ao laudo é o que o perito mediu. Ela é guardada à parte,
  em `itens_declarados`, com um único uso: **conferência de cadeia de custódia**
  (`core/conferencia.py`). A ferramenta compara quantidade de itens e contagem
  de porções, aponta divergência e exige reconhecimento explícito antes de
  gerar — mas não conclui nada: divergência pode ter explicação legítima, e
  quem interpreta é o perito.
- Data e local da apreensão são registrados (cadeia de custódia) mas **não são
  impressos**: o laudo de referência não os traz. Entram no documento quando
  algum laudo real mostrar onde.

## Tudo que é do TIPO DE EXAME sai do código

Um segundo laudo não podia existir enquanto o montador soubesse o que é
"substância". Hoje o tipo de exame declara, no registro:

- **as seções do documento** (`Exame.secoes`) — identificação de substância tem
  histórico e referências; identificação veicular não tem nenhum dos dois;
- **o seu pacote de texto fixo** (`Exame.template`), resolvido por
  `core/templates.py`;
- **grupos de campos repetíveis** (`Exame.grupos_admin`) — o laudo veicular
  pode ser assinado por dois peritos, com matrícula própria, e o preâmbulo vai
  ao plural;
- **onde ficam as imagens** (`Exame.imagens_em_apendice`) — no corpo, como no
  laudo de substância, ou em APÊNDICE FOTOGRÁFICO ao fim, como no veicular;
- **como descrever o objeto e cada exame**: se o template traz
  `descricao_objeto` e `paragrafo_do_exame`, o montador chama; senão vale a
  montagem do laudo de substância. Regra de veículo não entra no `core`.

Os padrões de resposta dos quesitos também são por exame: "Vide item 2. EXAMES"
existe no veicular e não no de substância.

## Terceiro exame: Verificação de Danos (Perícias Externas)

Transcrito dos laudos reais das demandas 00016037-31 (cela de presídio
arrombada) e 00016160-22 (ponte ferroviária pichada). Estrutura:
preâmbulo → 1. HISTÓRICO → 2. DO OBJETIVO DA PERÍCIA → 3. DOS EXAMES
(3.1 Do Local, 3.2 Das Constatações) → imagens no corpo → 4. CONCLUSÃO →
quesitos → fecho → assinatura.

Foi o primeiro tipo a entrar **sem tocar em `core/conversa.py` nem em
`core/extracao.py`** — o agente único e as etapas declaradas já bastavam. O que
o registro passou a declarar:

- **duas subseções fixas** em `3. DOS EXAMES` (`boiler.subsecoes`), contra uma
  por item examinado no veicular;
- **`campos_extras`**: marcadores que só um laudo usa. Aqui a concordância do
  preâmbulo sai do artigo que o perito escreveu — "do ofício … datado" contra
  "da requisição … datada". É gramática sobre o texto dele, não achado;
- **`Secao("imagens")`**: fotos no corpo onde o tipo mandar, em vez de presas à
  seção de descrição do objeto;
- **`RODAPE_MATRICULA`**: os laudos de danos abreviam "Mat.:".

E `Exame.colecao_objeto()` acabou com o `"materiais"` presumido em
`core/derivados.py`, `core/documento.py` e `screens/confirmacao.py`: a coleção
do objeto examinado é a primeira que não pende de outra — material, veículo ou
local.

**Os dois laudos são do mesmo perito**, como a camada 2 de substância nasceu de
um laudo só. Aceito pelo perito responsável em 2026-08-30.

**Padrão de resposta só onde é remissão.** "Vide tópico 3. DOS EXAMES, item
3.2", "Vide bojo do presente laudo" e "Prejudicada" entram em
`RESPOSTAS_CONHECIDAS`. `"Houve dano(s)?" → "sim"` e `"Houve emprego de
substância inflamável?" → "não"` **não entram**: são o achado do caso, e
oferecê-los prontos plantaria no laudo uma conclusão que o perito não relatou.

Três pontos em que a transcrição se afasta do papel, todos anotados no cabeçalho
do template: a grafia "PARÍCIA" foi corrigida; a concordância de "subscrit_",
que os dois originais invertem, passou a acompanhar o artigo do documento; e a
abertura das constatações ficou sem o "supostamente" que só um dos laudos traz.

**A legenda numera, o perito descreve.** Numa foto de danos a legenda É o
achado — "Mostrando a lâmpada do teto da cela, danificada" afirma que houve
dano. Descrevê-la a partir da imagem, por visão de modelo ou por regra, seria
inferência sobre prova física. Então a ferramenta preenche só o que é contagem
("IMAGEM 01: ") e o perito completa. Decidido com o perito responsável em
2026-08-30, depois de a visão computacional ter sido cogitada e descartada por
este motivo.

**Fechar o tipo custou menos código novo que desacoplamento.** O que impedia o
laudo de danos de rodar não era o montador — era a UI ainda presumir substância:
a tela de requisição propunha os quesitos de substância em QUALQUER laudo, o
seletor de referência dizia "Material 1" onde era "Local 1", a legenda saía com
marcador cru, e `derivados.montar` pedia "natureza do material" e "texto de
proscrição" num laudo que não tem substância nenhuma. Nada disso aparecia nos
roteiros existentes, porque nenhum deles abria as TELAS com um tipo que não
fosse o de substância — `verificacao/danos_ponta_a_ponta.py` existe para isso.

**Pendente:** derivar a resposta do quesito do meio/instrumento a partir de
`meio_instrumento` (hoje o perito a escreve na conversa) — mesma pergunta em
aberto do laudo veicular.

## Segundo exame: Identificação Veicular

Transcrito dos laudos reais das demandas 00078413-75 e 00082450-35. Estrutura:
preâmbulo → 1. DO VEÍCULO → 2. EXAMES (2.1 NIV, 2.2 Motor, 2.3 Placa) →
3. CONCLUSÃO → quesitos → fecho → assinaturas → apêndice fotográfico.

Os parágrafos da seção 2 são altamente templatizados: variam a numeração, o
local da gravação, quais caracteres divergiam, o tratamento aplicado e o
resultado da revelação. `verificacao/veicular.py` confere os três casos reais
caractere por caractere, inclusive a concordância ("o 17º caractere
apresentava … do caractere latente original" contra "todos os caracteres
apresentavam … dos caracteres latentes originais").

**Pendente:** derivar as respostas dos quesitos 1 e 5 dos resultados
registrados (hoje o perito as escreve na conversa), e a consulta ao SINESP, que
aparece na conclusão e no quesito 6.

## Primeiro exame: Identificação de Substância

Química Forense, baseado em laudos reais do Instituto de Criminalística da
PC-PI. Os 4 laudos de exemplo são a **fonte de verdade** para tom, estrutura e
texto boilerplate. NÃO inventar estrutura — extrair dos laudos reais.

- **Admin (formulário, transcrição pura):** data do exame, órgão solicitante,
  documento de solicitação (ofício/requisição), tipo e número do procedimento
  (IP/APF/BO), envolvido, perito designado, matrícula, número da demanda,
  protocolo (SBS).
- **Material (conversa, 1..N itens):** por item → massa líquida (valor +
  unidade), forma/tipo físico, coloração, acondicionamento (nº de invólucros +
  tipo), observações opcionais, imagens (0..N).
- **Exames realizados (conversa, 1..N):** por exame → nome do teste (Scott
  Modificado, Fast Blue B, FTIR, CCD, análise botânica), a qual item de material
  se aplica, resultado (positivo/negativo) e para qual substância.
- **Conclusão:** DERIVADA dos resultados, confirmada pelo perito.
- **Quesitos:** em grande parte templatizados (respostas remetem ao Item 2 ou ao
  texto legal — camada 2), com a parte substantiva derivada da camada 1.

---

## Tratamento da imagem do material

- Campo **opcional-mas-recomendado**, **0..N por laudo** (um laudo real tem duas
  fotos, uma por substância).
- Capturada via `st.camera_input` (perito fotografa em campo) ou upload.
- **A imagem é ANEXO DOCUMENTAL, nunca fonte que a IA interpreta.** NÃO usar
  visão do GPT para descrever a substância, pesar, contar invólucros ou inferir
  qualquer dado a partir da foto. Peso e contagem são medição física do perito.
  A foto apenas corrobora o texto.
- O LLM gera a legenda no padrão dos laudos ("Imagem 01: Fotografia dos
  invólucros de substância de cor branca") e a referência "(vide imagem 01)" no
  ponto certo. A imagem é embutida na montagem do `.docx`.

---

## Guardrails técnicos

- `OPENAI_API_KEY` vem do `.env`, nunca hardcoded. `.env` está no `.gitignore`.
- Extração via GPT retorna **JSON estrito**: parsing seguro (try/except, remoção
  de cercas ```json), validação contra o schema antes de gravar no
  `session_state`.
- Streamlit re-executa o script a cada interação: gerenciar estado com cuidado
  via `session_state`, sem presumir execução linear.
- Dependências: `streamlit`, `openai`, `python-dotenv`, `python-docx`, `pypdf` e
  `pytesseract`. Não adicionar outras sem necessidade real.
- **Tesseract é binário de sistema**, não vem no `pip install`:
  `brew install tesseract tesseract-lang` (macOS) ou
  `apt-get install tesseract-ocr tesseract-ocr-por` (Linux). Sem ele a leitura
  cai para o modelo de visão, que é o caminho frágil.
- Documento digitalizado costuma chegar **deitado**, e texto de lado derruba o
  OCR. A orientação é detectada e corrigida antes de ler — na requisição de
  referência foram 90°.
- Python 3.12 (venv em `.venv`).
- **Modelo é configurável** (`OPENAI_MODEL` no `.env`) e a chamada se adapta ao
  que cada geração aceita: os modelos novos recusam `temperature` fixa, e a
  chamada repete sem ela em vez de obrigar quem instalou a saber disso. A suíte
  de fidelidade passa igual em `gpt-4o` e `gpt-5.6-terra` — trocar de modelo é
  decisão de custo e latência, não de fidelidade.
- **O estado inteiro vai em toda leitura.** `descreve_estado` manda todos os
  itens já registrados junto de cada mensagem: é context offloading em forma
  estruturada, melhor que um rascunho de conversa. O painel lateral é esse
  mesmo estado, visível ao perito.

---

## Como rodar

```bash
python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env   # preencher OPENAI_API_KEY
.venv/bin/streamlit run app.py
```

---

## Estado atual

- **Milestone 1 — esqueleto navegável:** seleção do exame → formulário admin →
  conversa. Formulário renderizado a partir do registro, sem valor
  pré-preenchido (a data começa vazia).
- **Milestone 2 — conversa de slot-filling:** chat que preenche a camada 1.
  O extrator devolve JSON estrito; `core.extracao.aplicar` descarta chave
  desconhecida, valor vazio, valor de enfeite ("não informado") e valor fora do
  conjunto fechado de um slot. As falas do assistente são montadas por template
  a partir do que foi gravado — o LLM não redige nenhuma fala, então não tem
  como afirmar que registrou algo que não registrou. Uma coleção por vez, na
  ordem do registro; a coleção só encerra quando o perito diz que não há mais
  itens, e o painel de estado tem botão para reabrir se ela encerrar cedo demais.
  O avanço só libera com a camada 1 completa.
- **Recusa explicada:** slots marcados `exige_valor_exato` (massa e contagem de
  invólucros) não aceitam estimativa — "em torno de 15" não vira 15. Nesse caso
  a ferramenta diz o motivo e cita o trecho: *"Você disse «em torno de 15».
  Quantidade de invólucros vai ao laudo como medição sua, então não registro
  estimativa — me diga o valor exato."* Trecho citado é conferido contra a fala
  do perito antes de aparecer; citação que não bate é descartada.
- **Camada 2 transcrita do laudo SB 1252/2019** (demanda 00024529-28) em
  `templates/identificacao_substancia/boilerplate.py`: cabeçalho, preâmbulo,
  histórico, conclusão, os 6 quesitos, referências, fecho e assinatura.
  **Um dos quatro laudos.** Por isso só existe descrição técnica para análise
  botânica e CCD, e texto de proscrição para Cannabis sativa L. e cocaína.
  Scott, Fast Blue B e FTIR seguem sem texto: viram `[PENDENTE: ...]` em
  vermelho no documento. Preencher por semelhança seria inventar procedimento
  pericial — o parágrafo da seção 4 **declara como o exame foi conduzido**
  (qual padrão de referência, qual grandeza comparada), e um modelo escrevendo
  isso afirma procedimento que ninguém relatou.
- **O relato do perito vira o parágrafo, sozinho.** A conversa promete "conte
  como conduziu que eu redijo" — e a promessa se cumpre ao entrar na
  confirmação: o parágrafo é escrito a partir do relato, entra na seção 4 deste
  laudo e fica editável. Salvar na biblioteca é opcional, e serve só para
  reaproveitar nos próximos laudos. Antes, quem não achasse o botão exportava
  com `[PENDENTE]` no lugar.
- **Sem redação transcrita, a conversa pergunta o procedimento.** O slot
  `procedimento` só é exigido quando não existe parágrafo para aquele
  (ensaio, substância): o perito conta como conduziu — reagente, padrão, o que
  observou — e `core/redacao.py` formaliza **o relato dele**. Isso não afrouxa a
  regra: continua sendo reformatar o que o perito informou. O que o modelo não
  pode é acrescentar etapa, fase ou grandeza que ele não citou, e o texto passa
  pela confirmação antes de valer.
- **A camada 2 cresce por escrita de perito, não por PDF.** A fonte sempre foi
  um perito redigindo; o laudo em PDF era só o transporte. Quando falta redação,
  a tela de confirmação abre um campo, o perito escreve UMA vez e
  `core/biblioteca.py` guarda em `templates/identificacao_substancia/
  aprendidos.json`, indexado por ensaio e substância, **com autor e data**. O
  próximo laudo já sai completo. Nenhuma entrada é gerada por modelo.
- **Milestone 4 — geração do .docx:** camadas 1+2+3 no layout do laudo real,
  com as imagens embutidas. Nenhum texto nasce na montagem, e o LLM não
  participa: tudo que varia já foi ditado pelo perito ou derivado por regra e
  confirmado por ele na tela anterior.
  - Números por extenso seguem o laudo: `1,98 kg (um quilograma e novecentos e
    oitenta gramas)`, `02 (dois) invólucros`, `redigido em duas páginas` (com
    flexão de gênero). Grama com decimal aplica a MESMA convenção do laudo — a
    fração vira a sub-unidade: `15,3 g (quinze gramas e trezentos miligramas)`.
  - **Paginação é do editor, não da montagem.** O fecho sai com um campo
    `NUMPAGES`, que o Word preenche ao abrir o arquivo — o número fica certo
    sozinho. O perito só informa a contagem se o Instituto exigir por extenso
    ("duas páginas"). Estimar aqui poria número inventado no fecho de um laudo.
  - **A resposta do quesito 01 muda por substância** e é transcrita: "trata-se
    de Cannabis sativa Lineu" para a vegetal, "apresentou resultado positivo
    para presença de cocaína" para a sólida. Não são construções
    intercambiáveis; substância sem construção transcrita vira pendência.
  - O laudo real é a referência do teste: `verificacao/documento.py` alimenta o
    montador com os dados dele e confere trecho a trecho.
- **Milestone 3 — confirmação:** tudo que vai ao documento passa por uma tela
  editável — dados administrativos, camada 1, imagens e camada 3. Campo
  obrigatório apagado na revisão volta a bloquear o avanço.
  - **Derivados (camada 3) são montados por regra, sem LLM.** Conclusão sai das
    substâncias com resultado positivo; legenda sai dos campos do material. A
    tradução para o termo técnico do laudo ("THC" → "Cannabis sativa L.") é
    vocabulário institucional, então é o perito quem escreve — a ferramenta não
    traduz por conta própria.
  - Enquanto o perito não editar, o derivado **acompanha** a camada 1: conclusão
    desatualizada num laudo é erro silencioso. Depois que ele escreve a versão
    dele, o texto dele manda e a divergência fica à vista com opção de recalcular.
  - **Imagens** entram por upload ou `st.camera_input`, presas a um material,
    com legenda montada dos campos que o perito informou. Continuam sendo anexo
    documental: nada é lido da foto.
- **Próximo:** os outros três laudos completam a camada 2 e respondem o que
  ainda está em aberto no schema.

### Verificação

```bash
.venv/bin/python -m verificacao.fluxo        # sem API, determinístico
.venv/bin/python -m verificacao.requisicao   # sem API, consenso e descarte
.venv/bin/python -m verificacao.confirmacao  # sem API, pela UI real
.venv/bin/python -m verificacao.documento    # sem API, contra o laudo real
.venv/bin/python -m verificacao.danos        # sem API, contra os laudos reais
.venv/bin/python -m verificacao.danos_ponta_a_ponta   # sem API, pelas telas
.venv/bin/python -m verificacao.fidelidade   # com API real, custa chamadas
```

`fidelidade.py` é a rede de segurança do princípio central: cada caso é uma
fala incompleta cujo preenchimento "óbvio" viria do conhecimento de mundo do
modelo. Rodar sempre que mexer no prompt de extração ou trocar de modelo.

### Pontos em aberto do schema

**Em aberto, dependendo do perito:** o bloco de assinatura
("DOCUMENTO ASSINADO DIGITALMENTE", "PERITO CRIMINAL") tem variação real?

Respondidos pelo perito em 2026-08-27: massa bruta é registrada (slots
opcionais); "inconclusivo" é resultado válido; embalagem dentro de embalagem
cabe numa frase só no tipo de acondicionamento; grama com decimal segue a
convenção do laudo (fração vira sub-unidade). Ainda em aberto: mais de um
envolvido (hoje campo único).

**Nenhum campo obrigatório escapa da conversa.** O avanço só libera quando a
varredura de pendências não encontra nada. A referência de material não é
exceção: ela é preenchida pela travessia, a partir do material em foco — nem
perguntada ("é óbvio, só existe um material"), nem deduzida pelo extrator, que
está proibido de tocá-la. A confirmação continua oferecendo o seletor, como
revisão.

## Plano de milestones

- **M3** — tela de confirmação: campos derivados (camada 3) + schema completo
  editável. CHECKPOINT.
- **M4** — geração e export `.docx`: camadas 1+2+3 no template, imagens
  embutidas, legendas e referências no lugar. Texto narrativo gerado pelo GPT
  SOMENTE a partir do que foi coletado e confirmado. CHECKPOINT: comparar com
  laudo real.

Parar em cada CHECKPOINT e pedir validação antes de avançar.

## Texto fixo que NÃO deveria ser fixo

Auditoria do que o `.docx` imprime sem olhar para o caso, feita em 2026-08-28:

| Bloco | Situação |
|---|---|
| Cabeçalho, título | institucional — correto ser fixo |
| Preâmbulo, histórico, fecho | moldura fixa com campos do caso — ok |
| Conclusão, quesitos | derivados/transcritos do caso — ok |
| **Referências (seção 6)** | **corrigido**: seguem as substâncias do caso |
| `SUBTITULO`, "Setor de Química Forense" no preâmbulo | presos ao TIPO de exame, não ao caso. Passam ao registro quando entrar um segundo tipo de laudo |
| `ASSINATURA` ("DOCUMENTO ASSINADO DIGITALMENTE"), `CARGO` | fixos; laudo assinado à caneta, ou outra carreira, diriam outra coisa |

**Referências (seção 6):** confirmado pelo perito em 2026-08-28 que **não é
bibliografia fixa** — cita o que embasa cada exame. Vive em
`templates/identificacao_substancia/referencias.json`, e `core/referencias.py`
casa cada obra com as substâncias e métodos que o laudo registrou.

Cada entrada carrega a ORIGEM, e só entra no documento o que está confirmado:

| origem | o que significa |
|---|---|
| `transcrita` | copiada de laudo real |
| `verificada` | conferida na fonte oficial, com endereço e data |
| `perito` | confirmada ou trazida pelo perito |
| `candidata` | achada em busca; **não vai ao documento** |

**Por que candidata não entra:** citação é onde um modelo de linguagem mais
erra — inventa título, ano, edição, manual inteiro. Citação falsa num laudo
assinado é pior que referência faltando. As candidatas trazem título, descrição
e o endereço onde foram achadas; o perito abre a obra, escreve a citação
completa e ela passa a valer. Na tentativa de verificar as da UNODC, o site
respondeu 404 a todo acesso automatizado e os catálogos da ONU responderam 403
— por isso elas ficaram como candidatas, e não como verificadas.

Substância sem referência confirmada vira pendência visível, mesmo havendo
candidata para ela.

## O que a ferramenta NÃO julga

Ela não avalia a coerência técnica do achado. Se o perito registra um ensaio e
uma substância que, no entender de alguém, não combinam, a ferramenta não
opina: julgar achado é trabalho do perito, e um modelo "corrigindo" resultado
de exame é exatamente o que este projeto existe para impedir.

O que ela faz é **apontar contagem que não bate** (cadeia de custódia), porque
ali a comparação é aritmética entre dois documentos, não juízo técnico. A
diferença é essa: comparar números declarados é objetivo; dizer que um ensaio
não poderia ter dado aquele resultado é perícia.

## Linguagem com o perito

Quem usa isto é perito criminal, não pessoa de tecnologia. Nenhum texto de tela
usa jargão: nada de "JSON", "extrator", "OCR", "modelo", "camada 1", "schema",
"slot", "API". Erro de configuração não é culpa de quem está usando — a
mensagem diz o que fazer e a quem avisar, e o detalhe técnico vai rotulado como
"mostre isto a quem instalou".

E o perito **fala**, não digita formulário. "17 gramas e meio" é 17,5; "meio
quilo" é 0,5 quilo. Número por extenso ou em fração é valor exato, não
estimativa — transcrever em algarismos é notação, não conversão. Uma frase pode
preencher vários campos de uma vez, e a pergunta pendente não pode fazer o
resto da fala ser ignorado.

Guarda determinística: campo marcado `exige_valor_exato` só aceita número. Sem
isso, "dezessete gramas e meio" entrava inteiro no campo de massa e iria assim
para o laudo — aconteceu, e virou caso de teste.

## Convenções

- Commits: conventional commits com escopo, em inglês, terminando em ponto
  final. Sem trailer `Co-Authored-By`. Confirmar antes de commitar.
- Quando algo do domínio pericial estiver ambíguo: PERGUNTAR ou derivar dos
  laudos reais — nunca preencher por conta própria.
