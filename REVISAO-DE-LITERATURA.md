# Seção 2 — Revisão de Literatura

*Rascunho para o Relatório Final de IC. Todas as referências foram **verificadas
na fonte** em 30/08/2026: autoria, veículo, ano e páginas conferidos contra o
repositório do editor ou a ACL Anthology. Nenhuma foi escrita de memória — num
trabalho cuja tese é impedir fabricação, citação inventada seria a falha mais
grave possível.*

---

## 2.1 Modelos de linguagem pré-treinados

A arquitetura *Transformer* (VASWANI et al., 2017) substituiu recorrência por
mecanismos de atenção e viabilizou o treinamento em escala que define os
modelos de linguagem atuais. Sobre ela consolidou-se o paradigma de
**pré-treinamento seguido de ajuste fino**, que WANG et al. (2023) revisam de
forma sistemática, organizando os modelos pré-treinados em uma taxonomia e
descrevendo a mudança de patamar que representaram para o Processamento de
Linguagem Natural.

No contexto brasileiro, CASELI e NUNES (2024) reúnem a literatura de PLN
aplicada ao português, incluindo capítulo dedicado ao domínio jurídico —
referência direta para este trabalho, que opera sobre documentos oficiais
redigidos em português técnico-jurídico. BIRD, KLEIN e LOPER (2009) permanecem
como base introdutória das técnicas clássicas de processamento textual.

## 2.2 Por que modelos *encoder-only* não atendem a esta tarefa

O plano de trabalho menciona o BERT (DEVLIN et al., 2019) entre os modelos a
considerar. O levantamento realizado nesta pesquisa mostra, contudo, que
modelos dessa família **não realizam a tarefa aqui investigada**.

O BERT é um modelo *encoder-only*: foi projetado para produzir representações
contextuais bidirecionais destinadas a tarefas de classificação, rotulagem de
sequência e extração de entidades. Ele não gera texto autorregressivamente e,
por consequência, não produz saída estruturada — como um objeto JSON conforme a
um esquema — a partir de fala livre do perito.

A tarefa deste trabalho exige **geração condicionada a esquema**: dado um
enunciado em linguagem natural, produzir uma estrutura de dados válida e
somente com o que o enunciado contém. Isso demanda modelos generativos. O
registro desta constatação é, em si, um resultado do levantamento previsto no
primeiro objetivo específico: parte dos modelos citados no plano de trabalho é
inadequada à tarefa, e a justificativa é arquitetural, não de desempenho.

## 2.3 Alucinação e geração restrita

O obstáculo central ao uso de modelos generativos em documentos oficiais é a
**alucinação**. JI et al. (2023), em levantamento abrangente sobre o fenômeno
em geração de linguagem natural, distinguem a alucinação **intrínseca** — em
que a saída contradiz a fonte — da **extrínseca**, em que a saída afirma
conteúdo que a fonte não permite verificar. Num laudo pericial, ambas são
inaceitáveis: a primeira contradiz o que o perito mediu; a segunda insere no
documento afirmação que nenhuma medição sustenta.

Entre as estratégias de mitigação, interessa a este trabalho a **geração
restrita**. GENG et al. (2023) demonstram que restringir a decodificação a uma
gramática formal melhora substancialmente o desempenho em tarefas estruturadas
de PLN, sem necessidade de ajuste fino, ao garantir que a saída obedeça a uma
estrutura dada.

A abordagem adotada nesta pesquisa é aparentada, porém mais conservadora: em
vez de restringir a decodificação, **valida-se a saída do modelo contra o
esquema antes de qualquer gravação**, descartando o que não se sustenta na
fala do perito. A diferença é que a restrição gramatical garante a *forma* da
saída, enquanto a validação aqui empregada busca garantir a sua *procedência* —
que cada valor gravado tenha origem no que o perito efetivamente declarou.

## 2.4 LLMs aplicados ao domínio pericial

A aplicação de modelos de linguagem à perícia é área recente e concentrada na
computação forense. WICKRAMASEKARA, BREITINGER e SCANLON (2025) revisam o
estado da arte e concluem que a adoção de LLMs na perícia digital **com
restrições apropriadas** tem potencial para melhorar a eficiência das
investigações — ressalvando desafios de viés, explicabilidade e requisitos de
infraestrutura.

SHARMA et al. (2025) propõem o ForensicLLM, modelo local ajustado para o
domínio forense, e endereçam explicitamente o problema da alucinação por meio
de rastreabilidade: o modelo atribui corretamente a fonte em 86,6% das
respostas. O princípio subjacente — **toda afirmação deve poder ser remetida à
sua origem** — é o mesmo que orienta a arquitetura proposta neste trabalho,
ainda que por mecanismo distinto: aqui a origem não é a literatura, e sim a
fala do próprio perito.

Cabe registrar a lacuna que este trabalho procura ocupar. A literatura
localizada concentra-se em **perícia digital** e, majoritariamente, nas fases de
exame e análise; não foram encontrados trabalhos sobre **geração assistida de
laudos periciais em português**, tampouco sobre perícias de natureza física —
identificação de substância, identificação veicular, verificação de danos. A
escassez reforça a pertinência da investigação e, ao mesmo tempo, recomenda
cautela: não há linha de base consolidada contra a qual comparar os resultados
aqui obtidos.

---

## Seção 6 — Referências (ABNT NBR 6023)

**Já constantes do plano de trabalho** (duas com correção necessária):

BIRD, Steven; KLEIN, Ewan; LOPER, Edward. **Natural Language Processing with
Python**: analyzing text with the Natural Language Toolkit. Sebastopol:
O'Reilly Media, 2009.

CASELI, Helena de Medeiros; NUNES, Maria das Graças Volpe (org.).
**Processamento de Linguagem Natural**: conceitos, técnicas e aplicações em
português. 3. ed. [S.l.]: BPLN, 2024. Disponível em:
https://brasileiraspln.com/livro-pln/3a-edicao. Acesso em: 30 ago. 2026.

FÓRUM BRASILEIRO DE SEGURANÇA PÚBLICA. **18º Anuário Brasileiro de Segurança
Pública**. São Paulo: Fórum Brasileiro de Segurança Pública, 2024. Disponível
em: https://publicacoes.forumseguranca.org.br/handle/123456789/253. Acesso em:
30 ago. 2026.

WANG, Haifeng; LI, Jiwei; WU, Hua; **HOVY**, Eduard; SUN, Yu. Pre-Trained
Language Models and Their Applications. **Engineering**, v. 25, p. 51-65, 2023.
DOI: 10.1016/j.eng.2022.04.024.
> ⚠️ **Correção:** o plano grafa "HAVY, E."; o sobrenome correto é **HOVY**.

KODRATOFF, Yves; MICHALSKI, Ryszard S. (ed.). **Machine Learning**: an
artificial intelligence approach, volume III. San Mateo: Morgan Kaufmann, 1990.
> ⚠️ **Correção:** o plano atribui esta obra a "MITCHELL, T." e ao ano 2014. O
> Volume III foi editado por **Kodratoff e Michalski** e publicado em **1990**;
> Mitchell foi coeditor apenas do Volume I (1983). **Se a intenção era citar a
> obra de Tom Mitchell, a referência correta é a seguinte** — e é a mais
> provável, por ser o livro-texto canônico:

MITCHELL, Tom M. **Machine Learning**. New York: McGraw-Hill, 1997.

**Acrescentadas por esta revisão:**

DEVLIN, Jacob; CHANG, Ming-Wei; LEE, Kenton; TOUTANOVA, Kristina. BERT:
pre-training of deep bidirectional transformers for language understanding.
In: CONFERENCE OF THE NORTH AMERICAN CHAPTER OF THE ASSOCIATION FOR
COMPUTATIONAL LINGUISTICS: HUMAN LANGUAGE TECHNOLOGIES, 2019, Minneapolis.
**Proceedings** [...]. Minneapolis: ACL, 2019. p. 4171-4186.

GENG, Saibo; JOSIFOSKI, Martin; PEYRARD, Maxime; WEST, Robert.
Grammar-constrained decoding for structured NLP tasks without finetuning.
In: CONFERENCE ON EMPIRICAL METHODS IN NATURAL LANGUAGE PROCESSING, 2023.
**Proceedings** [...]. [S.l.]: ACL, 2023. p. 10932-10952.

JI, Ziwei; LEE, Nayeon; FRIESKE, Rita; YU, Tiezheng; SU, Dan; XU, Yan; ISHII,
Etsuko; BANG, Yejin; MADOTTO, Andrea; FUNG, Pascale. Survey of hallucination in
natural language generation. **ACM Computing Surveys**, v. 55, n. 12, art. 248,
2023. DOI: 10.1145/3571730.

SHARMA, Binaya; GHAWALY, James; McCLEARY, Kyle; WEBB, Andrew; BAGGILI,
Ibrahim. ForensicLLM: a local large language model for digital forensics.
**Forensic Science International: Digital Investigation**, v. 52, art. 301872,
2025.

VASWANI, Ashish; SHAZEER, Noam; PARMAR, Niki; USZKOREIT, Jakob; JONES, Llion;
GOMEZ, Aidan N.; KAISER, Lukasz; POLOSUKHIN, Illia. Attention is all you need.
In: **Advances in Neural Information Processing Systems 30**. [S.l.]: Curran
Associates, 2017. p. 6000-6010.

WICKRAMASEKARA, Akila; BREITINGER, Frank; SCANLON, Mark. Exploring the
potential of large language models for improving digital forensic investigation
efficiency. **Forensic Science International: Digital Investigation**, v. 52,
art. 301859, 2025.

---

## Notas para você

**Duas correções que o plano de trabalho exige.** A referência [2] está
incorreta em autoria e ano, e a [5] tem erro de grafia no sobrenome. Ambas
precisam ser acertadas antes da entrega — citação errada num relatório final é
apontamento certo de avaliador.

**Uma frente que não persegui.** Não localizei trabalho sobre geração assistida
de laudo pericial em português. Se o seu orientador conhecer produção do grupo
ou da UFPI nessa linha, ela deve entrar — cita-se o que é próximo, e proximidade
institucional conta.

**Duas referências plausíveis que NÃO incluí**, por não ter conferido os dados
completos na fonte: BROWN et al. (2020), sobre aprendizado *few-shot*, e o
levantamento de LLMs em perícia digital publicado em 2025 na *Forensic Science
International: Digital Investigation*. Posso verificá-las e acrescentar.
