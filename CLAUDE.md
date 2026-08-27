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
- **Transcrição de digitalização é rascunho, nunca fato.** Medido neste projeto:
  três leituras da mesma requisição real devolveram três redações diferentes
  para o mesmo quesito, e nenhuma batia com o papel. O caminho da imagem roda
  várias vezes e só propõe o que saiu igual em todas; o resto vira leitura
  incerta. Mesmo o que passa no consenso é PROPOSTA — alucinação estável existe,
  e foi observada. Quem confirma é o perito, com o documento na mão.
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
  requisicao.py            # leitura do ofício: PDF, OCR por visão, consenso
  quesitos.py              # perguntas da autoridade + padrão de resposta
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
referencia/                # laudos reais; fora do git (dados pessoais)
verificacao/
  fluxo.py                 # controlador, com extrator falso (sem API)
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
  camada 1. O que vai ao laudo é o que o perito mediu. A extração da requisição
  é instruída a ignorar essa parte do documento.

## Primeiro (e único, no v1) exame: Identificação de Substância

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
- Dependências: `streamlit`, `openai`, `python-dotenv`, `python-docx` e `pypdf`
  (leitura da requisição em PDF). Não adicionar outras sem necessidade real.
- Python 3.12 (venv em `.venv`).

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
  vermelho no documento, para o perito redigir. Preencher por semelhança seria
  inventar procedimento pericial.
- **Milestone 4 — geração do .docx:** camadas 1+2+3 no layout do laudo real,
  com as imagens embutidas. Nenhum texto nasce na montagem, e o LLM não
  participa: tudo que varia já foi ditado pelo perito ou derivado por regra e
  confirmado por ele na tela anterior.
  - Números por extenso seguem o laudo: `1,98 kg (um quilograma e novecentos e
    oitenta gramas)`, `02 (dois) invólucros`. Grama com decimal ainda não tem
    forma transcrita — vira pendência em vez de palpite.
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
.venv/bin/python -m verificacao.fidelidade   # com API real, custa chamadas
```

`fidelidade.py` é a rede de segurança do princípio central: cada caso é uma
fala incompleta cujo preenchimento "óbvio" viria do conhecimento de mundo do
modelo. Rodar sempre que mexer no prompt de extração ou trocar de modelo.

### Pontos em aberto do schema

Levantados no checkpoint e ainda sem resposta dos laudos reais: massa bruta
além da líquida; terceira categoria de resultado além de positivo/negativo;
como os laudos nomeiam os itens de material; embalagem dentro de embalagem;
mais de um envolvido; imagem por laudo ou por material. Ver também o
comportamento de `item_material` descrito abaixo.

**`item_material` é preenchido pelo extrator por resolução de referência.**
Quando há um único material registrado, o modelo às vezes responde "1" mesmo
sem o perito ter dito o número. É um ponteiro, não um achado pericial, e o
perito confirma na tela do M3 — mas se isso incomodar, o campo deve virar
derivado (camada 3) em vez de slot de conversa.

## Plano de milestones

- **M3** — tela de confirmação: campos derivados (camada 3) + schema completo
  editável. CHECKPOINT.
- **M4** — geração e export `.docx`: camadas 1+2+3 no template, imagens
  embutidas, legendas e referências no lugar. Texto narrativo gerado pelo GPT
  SOMENTE a partir do que foi coletado e confirmado. CHECKPOINT: comparar com
  laudo real.

Parar em cada CHECKPOINT e pedir validação antes de avançar.

## Convenções

- Commits: conventional commits com escopo, em inglês, terminando em ponto
  final. Sem trailer `Co-Authored-By`. Confirmar antes de commitar.
- Quando algo do domínio pericial estiver ambíguo: PERGUNTAR ou derivar dos
  laudos reais — nunca preencher por conta própria.
