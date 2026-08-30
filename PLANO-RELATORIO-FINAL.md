# Plano do Relatório Final — Iniciação Científica

**Título do plano de trabalho:** Criação Automática de Relatórios de Inquéritos
Periciais Usando Técnicas de IA Generativa
**Programa:** SSP-PI / UFPI · **Tipo:** Relatório Final

---

## Formato obrigatório (CPESI/PROPESQI/UFPI)

Extraído do próprio modelo. Não é sugestão — é exigência, e o `.docx` será
gerado já assim.

| Item | Regra |
|---|---|
| Partes | I – Identificação · II – Relato técnico-científico · III – Demais atividades |
| Seções da Parte II | exatamente 6, numeradas: Introdução · Revisão de Literatura · Metodologia · Resultados e discussão · Conclusão · Referências |
| Fonte | Arial 10, todo o documento |
| Alinhamento | justificado |
| Margens | 2 cm em todas |
| Recuo | primeira linha 1,25 cm |
| Entrelinhas | simples, 0 pt antes e depois |
| Paginação | arábica, rodapé à direita |
| Ilustrações/Tabelas | numeração arábica, título à esquerda sem negrito, separado por dois-pontos, **com indicação de fonte** |
| Referências | ABNT NBR 10520 e NBR 6023 |
| Entrega | `.doc` ou `.docx` |

---

## Mapa: o que já existe × o que falta escrever

| Seção | Situação | Origem do conteúdo |
|---|---|---|
| PARTE I | trivial | dados de identificação |
| 1. Introdução | **rascunho pronto** | `RELATORIO-TECNICO.md` §1 + plano de trabalho §1 |
| 2. Revisão de Literatura | **FALTA — maior lacuna** | precisa ser escrita do zero |
| 3. Metodologia | **80% pronto** | `RELATORIO-TECNICO.md` §2, §3, §8 + `CLAUDE.md` |
| 4. Resultados e discussão | **pronto** | `RELATORIO-TECNICO.md` §5–§8 + `E3-*.md` |
| 5. Conclusão | **pronto** | `RELATORIO-TECNICO.md` §9, §11 |
| 6. Referências | parcial | plano de trabalho [1]–[5] + as que a revisão trouxer |
| PARTE III | falta | seminários, apresentações, publicações — só você sabe |

---

## Estrutura proposta da PARTE II

### 1. Introdução  *(~1 página)*

Encadeamento sugerido:

1. Contexto — segurança pública, SSP-PI, o projeto guarda-chuva de PLN/LLM.
2. O problema concreto — o laudo pericial é documento **assinado por uma
   pessoa** e com efeito jurídico. Um modelo que inventa massa, contagem de
   invólucros ou resultado de ensaio insere erro num documento oficial sob
   assinatura de quem não o escreveu.
3. A inversão da pergunta de pesquisa — não é *"o LLM consegue redigir um
   laudo?"* (consegue, e é aí que mora o risco), e sim: **é possível usar LLM
   na produção de documento oficial de modo que a fidelidade seja garantida
   pelo código, e não pela boa vontade do modelo?**
4. Objetivos geral e específicos, transcritos do plano de trabalho.
5. Como o relatório se organiza.

> Fonte pronta: `experimentos/RELATORIO-TECNICO.md` §1.

### 2. Revisão de Literatura  *(~1,5 página — **a escrever**)*

É a única seção sem material pronto. Quatro blocos, com o que cada um precisa
sustentar:

**2.1 Modelos de linguagem e geração de texto**
Transformers, pré-treinamento, o salto para os LLMs. Base: WANG et al. [5],
CASELI & NUNES [4].

**2.2 Por que modelos *encoder-only* não servem a esta tarefa**
Achado a registrar: **o BERT, citado no plano de trabalho, não realiza esta
tarefa** — é encoder, não gerativo, e não produz JSON estruturado a partir de
fala livre. A tarefa exige geração condicionada a esquema. Não é falha da
execução; é imprecisão do plano, e vale como contribuição.

**2.3 Alucinação em LLMs e geração restrita**
O fenômeno, por que importa mais em documento oficial, e as abordagens de
mitigação (saída estruturada, validação de esquema, *grounding*). É a
literatura que dá nome ao que o protótipo faz.

**2.4 PLN aplicado a documentos jurídicos e periciais**
Trabalhos correlatos. Provável escassez em português para o domínio pericial —
e isso, dito explicitamente, justifica o trabalho.

> **Ação necessária:** buscar 8–12 referências. Posso levantar e redigir.

### 3. Metodologia  *(~2 páginas)*

Espelhando as cinco fases do plano de trabalho, como o modelo da UFPI espera:

- **3.1 Fase Teórica** — levantamento de modelos; critério de seleção do elenco
  por sondagem empírica (14 chamadas), não por catálogo.
- **3.2 Fase de Planejamento — análise do corpus** — os seis tipos previstos, o
  que foi encontrado de cada um, e **a justificativa de ter implementado três**
  (substância, veicular, danos). *Registrar aqui que Danos entrou por
  disponibilidade de laudos reais, e não está entre os seis do plano.*
- **3.3 Arquitetura** — o modelo em três camadas e as quatro paredes
  determinísticas (`aplicar`, `ler_recusas`, `valida_resumo`,
  `pendencias.completo`). **Figura 1: arquitetura em camadas.**
- **3.4 O protótipo** — Streamlit, agente conversacional único, etapas
  declaradas por tipo de exame, persistência em disco. **Figura 2: fluxo de
  telas.**
- **3.5 Protocolo experimental** — E1 (fidelidade entre modelos) e E3
  (reprodução de laudos reais), com os critérios de aprovação e a métrica de
  cobertura. **Quadro 1: critérios de classificação de frase.**

> Fonte pronta: `RELATORIO-TECNICO.md` §2, §3, §8; `CLAUDE.md`.

### 4. Resultados e discussão  *(~3 páginas — o núcleo)*

- **4.1 Elenco de modelos e nuances de integração**
  Modelos aposentados (`gemini-2.5-*` retornam 404), Pro inacessível no free
  tier, cota de 20 requisições/dia/modelo, latência variando duas ordens de
  grandeza. **Tabela 1: modelos sondados e desfecho.**

- **4.2 E1 — fidelidade da extração entre modelos**
  141 casos, 8 modelos, 2 famílias, 4 gerações. **136 aprovados, 5 reprovados,
  nenhuma invenção.** **Tabela 2: resultado por modelo.** Discutir que as
  falhas são de recusa excessiva, não de fabricação — o risco desloca-se para
  *campo faltando*, que é visível e corrigível.

- **4.3 E3 — reprodução de laudos reais**
  Metodologia da cobertura (o que entra e o que sai da conta, com a exclusão
  das imagens declarada). **Tabela 3: cobertura por laudo.** O número
  defensável: **44% a 50% em laudos inéditos**.

- **4.4 A comparação entre modelos como instrumento de verificação**
  O achado metodológico: a garantia de "nenhuma resposta sem explicação" havia
  migrado silenciosamente do código para o modelo, e a suíte passava porque o
  modelo em uso colaborava. Só apareceu ao rodar contra um segundo modelo.
  **É o resultado mais forte para publicação.**

- **4.5 Defeitos silenciosos revelados pelo E3**
  Quatro, com destaque para a frase de tratamento que sumia — o laudo
  afirmaria um resultado sem dizer como foi obtido.

- **4.6 Limitações**
  Uma repetição por caso; casos sintéticos escritos por quem desenvolve;
  autorreferência parcial do E3; três laudos inéditos apenas; free tier
  contaminando latência.

### 5. Conclusão  *(~1 página)*

1. Resposta à pergunta de pesquisa: **sim** — a fidelidade pode ser garantida
   por validação determinística fora do modelo, e isso foi demonstrado em 8
   modelos e 141 casos.
2. O que o protótipo entrega hoje: cerca de metade de um laudo inédito. Não é
   minuta pronta; é base sobre a qual o perito escreve o resto.
3. Trabalhos futuros — **as três frentes priorizadas**: consulta ao SINESP,
   narrativa do HISTÓRICO, múltiplas substâncias por ensaio.

### 6. Referências  *(ABNT)*

As cinco do plano de trabalho mais as que a Revisão de Literatura trouxer.

---

## Ilustrações previstas

| Nº | Tipo | Conteúdo | Fonte a indicar |
|---|---|---|---|
| Figura 1 | diagrama | arquitetura em três camadas e as quatro paredes | elaborada pelo autor |
| Figura 2 | diagrama | fluxo de telas do protótipo | elaborada pelo autor |
| Figura 3 | captura | tela da conversa com o perito | elaborada pelo autor |
| Tabela 1 | tabela | modelos sondados e desfecho | dados da pesquisa |
| Tabela 2 | tabela | E1 — fidelidade por modelo | dados da pesquisa |
| Tabela 3 | tabela | E3 — cobertura por laudo | dados da pesquisa |
| Quadro 1 | quadro | critérios de classificação de frase | elaborado pelo autor |

---

## Ordem de execução sugerida

1. **Revisão de Literatura** — é o caminho crítico; tudo o mais já tem material.
2. **Análise dos seis tipos de laudo** — fecha o objetivo específico 2 e entra
   em 3.2.
3. **Montagem do `.docx`** no formato da UFPI, com o conteúdo já existente.
4. **Figuras** — as duas de arquitetura e a captura de tela.
5. **PARTE III** — só você tem os dados.

## Pendências que dependem de você

- Dados da PARTE I (orientador, período, programa).
- PARTE III (seminários, apresentações, publicações).
- Confirmar se Danos entrou por disponibilidade de laudos — a justificativa
  precisa ser verdadeira.
