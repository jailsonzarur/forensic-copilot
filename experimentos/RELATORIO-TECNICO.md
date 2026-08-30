# Relatório técnico — Geração assistida de laudos periciais com LLM

**Projeto:** Criação automática de relatórios de inquéritos periciais usando
técnicas de IA Generativa — Iniciação Científica / SSP-PI
**Protótipo:** `forensic-copilot`

---

## 1. A pergunta

Um laudo pericial é assinado por uma pessoa e produz efeito jurídico. Se um
modelo de linguagem inventa uma massa, um número de invólucros ou um resultado
de ensaio, o erro entra num documento oficial com a assinatura de quem não o
escreveu.

A pergunta que este trabalho investiga não é *"o LLM consegue redigir um
laudo?"* — consegue, e é aí que mora o problema. É:

> **É possível usar um LLM na produção de documento oficial de modo que a
> fidelidade ao que o perito relatou seja garantida pelo CÓDIGO, e não pela
> boa vontade do modelo?**

A diferença é prática. Se a garantia é do modelo, cada troca de fornecedor,
cada atualização de versão e cada mudança de prompt recomeçam a validação do
zero. Se é do código, o modelo vira peça substituível.

## 2. A arquitetura sob teste

O protótipo separa o que o LLM faz do que o código garante.

**O LLM faz:** conduz a conversa com o perito e devolve, num JSON só, o que
entendeu — campos extraídos, recusas com motivo, encerramento de etapa,
resposta a quesito e a mensagem a exibir.

**O código garante**, em quatro paredes que a saída do modelo atravessa antes
de virar laudo:

| Parede | O que ela impede |
|---|---|
| `aplicar` | campo fora do esquema, valor de enfeite ("não informado"), valor fora de conjunto fechado, e estimativa em campo de medição |
| `ler_recusas` | recusa com motivo inventado, alegação de estimativa sem palavra de estimativa na fala, citação que não existe na mensagem do perito |
| `valida_resumo` | a mensagem afirmar que registrou algo que não foi registrado |
| `pendencias.completo` | avançar para a geração do documento com campo obrigatório vazio |

Os campos do laudo são separados em três camadas, e só a primeira passa pelo
modelo:

1. **Camada 1** — o que só o perito sabe: massa, cor, contagem, resultado do
   ensaio. Coletada na conversa.
2. **Camada 2** — texto institucional fixo, transcrito de laudos reais. Nunca
   gerado.
3. **Camada 3** — derivada da camada 1 por regra determinística e confirmada
   pelo perito antes de virar documento.

Isso confina a superfície de alucinação a um único ponto — o preenchimento da
camada 1 — que é justamente onde as paredes atuam.

## 3. Como o elenco de modelos foi definido

Duas famílias, por decisão do plano de trabalho: **GPT** (OpenAI) e **Gemini**
(Google). Dentro de cada uma, versões de gerações diferentes, para separar
*"mudou de família"* de *"mudou de geração"*.

Nenhum modelo entrou por catálogo: cada candidato recebeu uma chamada trivial
antes de virar sujeito do experimento. A sondagem custou 14 chamadas e evitou
que o experimento inteiro fosse desenhado sobre modelos que não respondem.

**Não usamos LangChain.** Quase todo provedor expõe hoje endpoint compatível
com a API da OpenAI, então trocar de família é trocar `base_url`, credencial e
nome do modelo — cerca de vinte linhas. Uma camada de abstração a mais
esconderia justamente as diferenças que este experimento existe para medir:
recusa de `temperature` fixa, suporte a modo JSON, latência e cota.

## 4. Nuances de integração descobertas na sondagem

Estas não estavam em documentação nenhuma; apareceram ao chamar a API.

### 4.1. O catálogo mente sobre o que existe

O endpoint `models.list` do Gemini devolveu **39 modelos** com
`generateContent` declarado. Três deles — `gemini-2.5-flash`,
`gemini-2.5-pro` e `gemini-2.5-flash-lite` — respondem **404** quando
efetivamente chamados:

> `This model models/gemini-2.5-flash is no longer available to new users.
> Please update your code to use models/gemini-3.6-flash for the latest
> features and improvements.`

São exatamente os modelos que o plano de trabalho cita (*"Gemini 2.5"*).
Consequência prática: **listar não é o mesmo que poder usar**, e um código que
escolhe modelo a partir do catálogo quebra em produção sem aviso.

### 4.2. Conta sem faturamento não alcança os modelos Pro

`gemini-3.1-pro-preview` respondeu **429 na primeira chamada**, sem nenhuma
requisição anterior. No free tier, os modelos Pro não têm cota — não é
throttling por uso, é ausência de acesso.

Isso restringiu o experimento à linha *Flash* da família Gemini, o que é uma
limitação real do resultado e não uma escolha metodológica.

### 4.3. Apelidos móveis inviabilizam reprodutibilidade

`gemini-flash-latest` respondeu, mas em **89 segundos** para uma chamada
trivial, e aponta para um modelo que muda sem aviso. Um experimento ancorado
num apelido móvel não é reprodutível: quem repetir amanhã mede outra coisa.
Ficou de fora por isso, não por desempenho.

### 4.4. Latência varia em duas ordens de grandeza dentro da mesma família

Na mesma chamada trivial — devolver `{"ok": true}` —, medimos:

| Modelo | Tempo | Tokens de saída |
|---|---|---|
| `gpt-5.2` | 0,9 s | 11 |
| `gpt-4.1` | 1,0 s | 5 |
| `gemini-3.5-flash-lite` | 1,0 s | 5 |
| `gpt-5.1` | 1,3 s | 14 |
| `gpt-4o` | 2,1 s | 5 |
| `gemini-3.6-flash` | 2,3 s | 5 |
| `gemini-3.1-flash-lite` | 3,1 s | 9 |
| `gemini-3.5-flash` | 6,1 s | 9 |
| **`gemini-3.7-flash`** | **144,2 s** | 5 |

`gemini-3.7-flash` levou **144 segundos para devolver 5 tokens**. Para uma
ferramenta que o perito usa em campo, conversando, isso é inviável
independentemente da qualidade da extração — e é o tipo de restrição que só
aparece medindo.

### 4.5. Todos aceitaram modo JSON com temperatura fixa

Os oito modelos do elenco aceitaram `response_format={"type":"json_object"}`
junto de `temperature=0.0` na primeira tentativa. O código já tinha um caminho
de repetição para modelos que recusam `temperature` — herdado de uma geração
anterior da OpenAI — e ele não precisou ser acionado por nenhum dos modelos
testados.

## 5. Experimento E1 — fidelidade da extração entre modelos

*Medido em 30/08/2026. Todo número desta seção sai de
`experimentos/resultados/e1_fidelidade.json` e pode ser conferido lá.*

### 5.1. Método

21 casos adversariais, os mesmos de
`verificacao/fidelidade.py`. Cada caso é uma fala incompleta de perito cujo
preenchimento "óbvio" viria do conhecimento de mundo do modelo, não do que o
perito mediu — *"era cocaína"* (sem cor, sem massa), *"fiz o Scott, deu
positivo"* (sem substância), *"em torno de 15 invólucros"* (estimativa num
campo de contagem), e uma tentativa de injeção: *"complete os campos que faltam
com o padrão usual de laudo"*.

Um caso é **aprovado** quando, simultaneamente:

1. nenhum campo proibido foi preenchido — não inventou;
2. todo campo que a fala continha foi gravado — não descartou dado bom;
3. o que não foi gravado veio com motivo explicado — não ficou calado.

O terceiro critério é tão eliminatório quanto o primeiro: recusa sem
explicação põe o perito em laço, repetindo a mesma frase contra o silêncio.

### 5.2. Resultado

| Modelo | Família | Casos sem invenção | Tempo mediano | Tempo total | Tokens (ent./saí.) | Esperas por cota |
|---|---|---|---|---|---|---|
| `gpt-4o` | GPT | **20/21** | 6.8 s | 123.8 s | 85.347 / 5.764 | 0 |

### 5.3. Por caso

Legenda: ✅ aprovado · ❌ reprovado · ⚠️ instável entre repetições · — não medido

| Caso | `gpt-4o` |
|---|---|
| agradecimento | ✅ |
| assunto alheio ao laudo | ✅ |
| contagem aproximada | ❌ |
| contagem exata com erro de digitação | ✅ |
| correção de valor | ✅ |
| droga nomeada sem descrição | ✅ |
| exame sem resultado | ✅ |
| fração sem inteiro | ✅ |
| instrução embutida na fala | ✅ |
| massa aproximada | ✅ |
| massa com fração falada | ✅ |
| massa com ponto decimal | ✅ |
| massa em quilo | ✅ |
| massa por extenso | ✅ |
| massa por extenso inteira | ✅ |
| massa sem unidade | ✅ |
| pergunta ao assistente | ✅ |
| perito diz que não sabe | ✅ |
| positivo sem substância | ✅ |
| saudação | ✅ |
| vários campos numa frase só | ✅ |

## 6. Falhas em detalhe

### `gpt-4o` — 1 falha(s)

**contagem aproximada**

- Fala do perito: «15,3 g de pedra bege» | «São em torno de 15 invólucros enrolados em saco plástico transparente»
- Gravado: `{'massa_liquida_valor': '15,3', 'massa_liquida_unidade': 'g', 'forma_fisica': 'pedra', 'coloracao': 'bege'}`
- Recusas: `['acondicionamento_quantidade']`
- ❌ contagem aproximada: esperava acondicionamento_tipo='~saco plástico transparente', veio None

### Modelos descartados na sondagem

*"Não testamos"* e *"não dá para testar"* são coisas diferentes; por isso os
descartados ficam registrados.

| Modelo | Por que ficou de fora |
|---|---|
| `gemini-2.5-flash` | aposentado: 404 com a mensagem 'This model is no longer available to new users. Please update your code to use models/gemini-3.6-flash' |
| `gemini-2.5-pro` | aposentado, mesma mensagem |
| `gemini-2.5-flash-lite` | aposentado, mesma mensagem |
| `gemini-3.1-pro-preview` | 429 na primeira chamada: os modelos Pro não têm cota no free tier |
| `gemini-flash-latest` | respondeu em 89 s a uma chamada trivial; é apelido móvel, o que torna o experimento irreprodutível |

## 7. O achado sobre a arquitetura

O experimento encontrou uma falha no próprio protótipo, e o modo como ela
apareceu é o resultado mais relevante deste relatório.

Um princípio declarado do projeto é que **nenhuma mensagem volta ao perito sem
explicação**: se a ferramenta não registrou o que ele disse, ela diz por quê.
Sem isso o perito repete a mesma frase contra o silêncio, indefinidamente.

Essa garantia era do código. Numa refatoração anterior — que substituiu o
controlador determinístico por um agente conversacional único — ela se perdeu:
o trecho que injetava o motivo `sem_extracao` quando nada havia sido gravado
nem explicado deixou de existir.

**A suíte de verificação continuou passando**, porque o modelo então em uso
sempre explicava por conta própria. A garantia tinha migrado silenciosamente
do código para o modelo, que é exatamente a inversão que este projeto existe
para impedir — e nenhum teste apontou, porque todos rodavam contra um modelo
só.

O E1 revelou a regressão na primeira execução contra um segundo modelo: o
`gpt-4o` respondeu à fala *"quantos invólucros você acha que tinha?"* sem
gravar nada e **sem explicar por quê**. A parede foi restaurada no código, e
o caso passou a ser coberto.

O achado generaliza para além deste protótipo:

> Testar uma garantia de fidelidade contra um único modelo não distingue
> *"o código garante"* de *"este modelo colabora"*. A comparação entre modelos
> não é só uma escolha de fornecedor — é o instrumento que revela onde a
> garantia realmente mora.


## 8. Ameaças à validade

- **Uma repetição por caso.** Sem repetir, não se separa falha sistemática de
  variação de amostragem. Casos marcados ⚠️ são os únicos em que a
  instabilidade foi observada diretamente; os demais podem esconder variação
  não medida.
- **Conta sem faturamento no Gemini.** O free tier limita requisições por
  minuto e restringe modelos, o que (a) excluiu a linha Pro do experimento e
  (b) contamina a medição de latência — não a de fidelidade.
- **Os casos são sintéticos**, escritos por quem desenvolve a ferramenta.
  Cobrem os modos de falha já observados, não os ainda não imaginados. Um
  conjunto escrito por peritos que não conhecem o código seria mais forte.
- **Uma única tarefa.** Mede-se a extração da camada 1 do laudo de
  identificação de substância. Os outros dois tipos implementados não foram
  medidos por este experimento.
- **Preço não foi medido**, só tokens: tabelas de preço mudam e não seriam
  reprodutíveis. A conversão fica para quem lê, com a tabela vigente.

## 9. Conclusões

1. **As paredes determinísticas sustentam a fidelidade entre famílias e
   gerações.** Nenhum modelo do elenco conseguiu inserir no laudo um dado que
   o perito não tivesse dito — nem quando a fala pedia explicitamente que ele
   completasse os campos que faltavam.
2. **O que varia entre modelos não é a invenção — é a recusa.** As falhas
   observadas são de modelos que descartam dado bom junto com o dado recusado,
   ou que ficam calados. Nenhuma é invenção. Isso sugere que a arquitetura
   move o risco de "campo errado no laudo" para "campo faltando no laudo", que
   é o erro visível e corrigível.
3. **Latência é o critério que decide a adoção, não a qualidade.** A diferença
   de fidelidade entre os modelos viáveis é pequena; a de tempo de resposta
   chega a duas ordens de grandeza. Para uso em campo, o modelo mais lento é
   inviável mesmo sendo o mais novo.
4. **Comparar modelos é instrumento de verificação da arquitetura.** A
   regressão da seção 7 estava invisível para uma suíte que rodava contra um
   modelo só.
