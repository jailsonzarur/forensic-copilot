"""Seções fixas do relatório técnico — separadas para o gerador ficar legível."""

CABECALHO = """# Relatório técnico — Geração assistida de laudos periciais com LLM

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

E mesmo na linha Flash a cota é apertada. A documentação oficial não publica
mais os números — remete ao painel do AI Studio —, mas o próprio erro os
informa quando estoura:

> `Quota exceeded for metric:
> generativelanguage.googleapis.com/generate_content_free_tier_requests,
> limit: 20, model: gemini-3.5-flash`

**Vinte requisições por dia, por modelo.** Um conjunto de 21 casos não cabe
numa conta sem faturamento: o experimento com `gemini-3.5-flash` foi
interrompido por cota no 18º caso. Isso não é falha do modelo, e o relatório
distingue as duas coisas na tabela — confundi-las faria a tabela afirmar que
um modelo inventou dado quando ele sequer foi alcançado.

Consequência metodológica: **medir modelos Gemini com rigor exige conta com
faturamento**, mesmo que o custo real seja de centavos. O free tier serve para
sondar, não para experimentar.

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

### 4.5. O recuo por cota precisou existir no código do produto

Estourar cota não é erro de quem está usando a ferramenta. O cliente ganhou
recuo exponencial em 429 — quatro tentativas, dobrando a espera a partir de
8 segundos — porque sem isso o perito leria *"a ferramenta falhou"* no meio do
laudo por um limite administrativo do provedor.

Durante o E1 esse recuo foi acionado **13 vezes** só com `gemini-3.5-flash`, e
salvou 13 casos que teriam sido perdidos. Os quatro que ainda assim falharam
esgotaram as tentativas.

### 4.6. Todos aceitaram modo JSON com temperatura fixa

Os oito modelos do elenco aceitaram `response_format={"type":"json_object"}`
junto de `temperature=0.0` na primeira tentativa. O código já tinha um caminho
de repetição para modelos que recusam `temperature` — herdado de uma geração
anterior da OpenAI — e ele não precisou ser acionado por nenhum dos modelos
testados.

"""

COBERTURA = """
## 8. Como a cobertura do E3 é calculada

A porcentagem de cobertura é a medida central do E3, e ela só significa alguma
coisa se estiver claro o que entra e o que fica de fora da conta. O cálculo
vive em `experimentos/e3_cobertura.py`; o que segue descreve as decisões, e
cada uma delas está no código, não numa planilha.

### 8.1. O que é comparado

Compara-se **frase a frase**, do laudo OFICIAL para o GERADO — nunca o
contrário. A pergunta é *"o que o perito escreveu apareceu na minuta?"*, não
*"a minuta escreveu algo a mais?"*. Texto extra na minuta não conta como acerto
nem como erro nesta medida.

### 8.2. Normalização

Antes de comparar, o texto perde acento e pontuação e tem os espaços
colapsados. A extração de PDF quebra linha no meio de palavra e espalha
espaços; sem normalizar, a medida seria a do extrator de PDF, e não a da
ferramenta.

### 8.3. O que é excluído da conta, e por quê

| Excluído | Motivo |
|---|---|
| Frases com menos de 40 caracteres | não são conteúdo: são fragmento de quebra de linha do PDF |
| Rodapé de paginação (`"Página 2 de 3"`) | artefato de quem imprimiu o PDF, não conteúdo do laudo |
| **Legenda e remissão de imagem** (`"Imagem 02: ..."`, `"vide foto 03"`) | **a geração de legenda e de referência a imagem é frente própria, ainda não implementada. Mantê-la na conta mediria duas coisas ao mesmo tempo e escondia o desempenho do texto** |

A exclusão das imagens **muda o resultado de forma relevante** e por isso está
declarada aqui: no laudo veicular inédito, a cobertura sobe de 32,3% para
50,0% quando as frases de imagem saem da conta. Quem citar o número precisa
citar junto o que ele exclui.

### 8.4. Como cada frase é classificada

Para cada frase do oficial, procura-se primeiro a frase inteira no texto
gerado — a ferramenta pode quebrar parágrafos diferente do PDF, e isso não é
ausência. Não achando, mede-se a maior similaridade contra as frases do
gerado:

| Faixa | Classificação | Leitura |
|---|---|---|
| ≥ 85% | **coberta** | a frase saiu, com a redação do laudo |
| 50% a 85% | **parcial** | o conteúdo aparece, a redação não bate |
| < 50% | **ausente** | não saiu |

### 8.5. Erros de medição cometidos antes de chegar a estes números

Registrados porque a medição também erra, e esconder isso seria a mesma falha
que a ferramenta existe para impedir:

1. **Similaridade do documento inteiro** foi reportada primeiro (8% a 41%) e
   descartada como "artefato de extração de PDF" **sem verificação**. Ao medir,
   boa parte era ausência real. A métrica de documento inteiro não é
   informativa e não consta mais do relatório.
2. **O separador de frases quebrava em dois-pontos**, partindo
   `"Imagem 2: Mostra o material..."` em duas. A segunda metade escapava do
   filtro de imagens e era contada como conteúdo ausente. Corrigido para
   quebrar só em ponto e ponto-e-vírgula.

"""

FUTUROS = """
## 9. Trabalhos futuros

O que segue não é lista de ideias: cada item apareceu como ausência medida no
E3, com o caso e o número correspondentes.

Três frentes foram avaliadas como **relevantes** — são as que respondem pela
maior parte do conteúdo ausente e mudam o que a ferramenta entrega:

### 9.1. Consulta ao SINESP

Aparece na seção 2 e na conclusão de **todos** os laudos veiculares do corpus,
e é o que sustenta a afirmação de que uma placa é clonada ou falsa. Hoje o
perito escreve à mão. Já constava como pendência do projeto antes do E3; o
experimento quantificou o peso.

### 9.2. Narrativa do HISTÓRICO

Hoje é moldura fixa com campos do caso. Nos laudos reais é narrativa: conta o
trajeto da demanda — *"a demanda pericial fora recebida no setor de Química
Forense com requisição de exame pericial…"*, *"o documento pericial será
encaminhado para a DELEGACIA DE POLÍCIA CIVIL DE CURIMATÁ, conforme solicitado
na requisição"*. Apareceu ausente nos laudos de substância e de danos.

### 9.3. Mais de uma substância por ensaio

A Cromatografia Gasosa acoplada à Espectrometria de Massas identificou
**cocaína, cafeína e lidocaína** no laudo 00086731-52. O schema tem UM slot de
substância por exame, e a frase inteira entrou nele — o que derrubou em cascata
a referência bibliográfica, o texto de proscrição e a resposta do quesito 01.
É a lacuna com maior efeito colateral de todas as medidas.

### 9.4. Frentes avaliadas e consideradas menores

Registradas para que a decisão fique explícita, e não pareça esquecimento:
frases conclusivas derivadas (*"Dessa forma, a placa constitui placa falsa"*),
cabeçalho variável por unidade emissora, casamento flexível de enunciado de
quesito, e geração de legenda e referência de imagem. São ajustes pontuais de
template ou de vocabulário, sem efeito sobre a arquitetura nem sobre a
fidelidade.

"""

RODAPE_ANALISE = """
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

"""
