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
- **Humano no controle.** A saída é uma MINUTA. Sempre há tela de confirmação
  antes de gerar o documento, onde o perito revisa e edita. A responsabilidade
  legal é do perito. A ferramenta é assistente de redação, não perito
  automático.

Corolário para o código: nenhum default "esperto", nenhum valor de exemplo que
possa vazar para o laudo, nenhum campo boilerplate escrito de cabeça — texto
institucional só entra transcrito de laudo real.

---

## Arquitetura (v1)

- **Streamlit puro.** Sem LangGraph no v1 (arquitetura de escala futura, quando
  entrarem os outros tipos de exame). Controle de fluxo via `st.session_state` +
  roteador de telas simples.
- **OpenAI (GPT)** como LLM, com dois papéis distintos e separados:
  1. **extração estruturada** do que o perito disse (saída JSON estrita);
  2. **geração do texto narrativo final** a partir dos dados já confirmados.
- **Fluxo de telas:**
  `seleção do tipo de exame` → `formulário admin (transcrição)` →
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
  llm.py                   # cliente OpenAI + parsing JSON seguro   (M2)
  pendencias.py            # varredura de campos obrigatórios       (M2)
screens/
  selecao.py               # tela 1 — seleção do tipo de exame
  admin.py                 # tela 2 — formulário administrativo
  conversa.py              # tela 3 — slot-filling (placeholder no M1)
  # confirmacao.py (M3) e documento.py (M4) ainda não existem
templates/
  identificacao_substancia/boilerplate.py   # CAMADA 2 (texto fixo)
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
- Dependências limitadas a: `streamlit`, `openai`, `python-dotenv`,
  `python-docx`. Não adicionar outras sem necessidade real.
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
  tela de conversa (placeholder). Formulário renderizado a partir do registro.
- **Camada 2 (boilerplate) está VAZIA e marcada como pendente** em
  `templates/identificacao_substancia/boilerplate.py`. Só será preenchida com
  texto transcrito dos 4 laudos reais — escrever esse texto de cabeça violaria
  a regra de fidelidade.
- **Milestone 2 — próximo:** validar o schema de slots contra os laudos reais
  (CHECKPOINT), depois loop de chat + extração de slots + verificação de
  pendências.

## Plano de milestones

- **M2** — conversa + slot-filling + pendências. CHECKPOINTs: (a) aprovar o
  schema de slots antes da UI; (b) conversa preenchendo o schema corretamente.
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
