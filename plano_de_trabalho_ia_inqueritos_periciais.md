# Criação Automática de Relatórios de Inquéritos Periciais Usando Técnicas de IA Generativa

## 1. Introdução e Justificativa

Este plano de trabalho está diretamente ligado ao projeto **“Aplicação de Inteligência Artificial (IA), na modalidade de Processamento de Linguagem Natural (PLN), incluindo o uso de Grandes Modelos de Linguagem (Large Language Model – LLM) para auxiliar nas demandas da Secretaria de Segurança Pública do Estado do Piauí (SSP-PI)”**, que visa investigar soluções com a aplicação de Inteligência Artificial, na modalidade de PLN, incluindo o uso de Grandes Modelos de Linguagens (Large Language Model – LLM) para auxiliar nas demandas da SSP-PI.

A segurança pública é um pilar fundamental para a construção de uma sociedade justa e próspera, garantindo a ordem social, a proteção dos direitos e liberdades individuais e o bem-estar coletivo. No Brasil, as Secretarias de Segurança Pública desempenham um papel crucial na manutenção da ordem, atuando por meio de diferentes órgãos, como a Polícia Militar, a Polícia Civil e o Corpo de Bombeiros. Essas instituições trabalham em conjunto para prevenir e reprimir crimes, garantir a segurança da população e promover a reparação em caso de violações da ordem.

O *Anuário Brasileiro de Segurança Pública de 2024* ressalta a importância do uso de tecnologias avançadas para enfrentar os desafios da segurança pública. Ferramentas como a inteligência artificial, *big data* e sistemas de monitoramento digital permitem maior eficiência no combate ao crime, oferecendo *insights* em tempo real e aumentando a precisão na identificação de suspeitos. Além disso, a tecnologia contribui para a análise preditiva, o que auxilia na alocação de recursos e na prevenção de incidentes. A integração dessas tecnologias fortalece as ações das forças de segurança, tornando-as mais ágeis e capazes de responder com eficácia aos desafios contemporâneos [1].

Para embasar as suas ações e estratégias, as Secretarias de Segurança Pública se apoiam na coleta e análise de dados sobre registros criminais, incluindo informações provenientes dos órgãos de segurança, da população, por meio de canais como a delegacia virtual e de outras fontes relevantes. Esses dados são organizados em diferentes formatos, como tabelas, bases de dados e relatórios estatísticos, e são utilizados para identificar tendências, avaliar o desempenho das forças policiais e orientar a formulação de políticas públicas voltadas para a redução da criminalidade.

Um dos desafios do projeto de pesquisa é analisar os dados relativos aos laudos periciais do **Departamento de Polícia Científica (DEPOC)** e do **Instituto de Criminalística**, visando a criação automática de relatórios de inquéritos periciais, usando técnicas de Inteligência Artificial.

O bolsista a ser envolvido deve ter habilidades na linguagem de programação Python e nas seguintes bibliotecas:
- [NLTK](https://www.nltk.org/book/)
- [spaCy](https://spacy.io)
- [Scikit-Learn](https://scikit-learn.org/stable/)

Além disso, deve ter conhecimento em modelos de IA generativa, tais como:
- BERT (*Bidirectional Encoder Representations from Transformers*) e variações
- Llama 3 (Meta AI)
- Gemini 2.5 (Google)
- Qwen2.5-Max (Alibaba)
- V3 (DeepSeek AI)
- Sabiá 3 (Maritaca AI)
- GPT-4o (OpenAI), entre outros.

Os trabalhos [2, 3, 4, 5] serão utilizados como referências básicas para a definição do referencial teórico deste projeto. Além dessas referências, existem vários tutoriais e videoaulas disponíveis na Web sobre *Machine Learning*, *Deep Learning* e Grandes Modelos de Linguagens (LLMs).

---

## 2. Objetivos

### Objetivo Geral
Analisar os dados relativos aos laudos periciais do Departamento de Polícia Científica (DEPOC) e do Instituto de Criminalística, visando a criação automática de relatórios de inquéritos periciais, usando técnicas de IA generativas e LLMs.

### Objetivos Específicos
- **Levantamento de Modelos:** Fazer um levantamento dos principais modelos de IAs Generativas e LLMs usados para criação automática de relatório a partir de dados textuais, áudios, imagens e vídeos;
- **Análise e Criação de Templates:** Analisar os dados relativos aos laudos periciais gerados pelo Departamento de Polícia Científica (DEPOC) e do Instituto de Criminalística nos últimos anos, com a intenção de encontrar padrões para serem usados como modelos de *templates* dos seis principais tipos de laudos, a saber:
  1. Exame de lesão corporal;
  2. Exame de identificação de substância;
  3. Exame cadavérico;
  4. Exame pericial de balística forense;
  5. Exame pericial para identificação veicular;
  6. Exame preliminar de constatação de substância.
- **Implementação de Métodos:** Implementar métodos para auxiliar a criação de relatórios de inquéritos periciais dos principais tipos de exames;
- **Integração e Avaliação:** Integrar todas as funcionalidades em um protótipo, experimentar e discutir os resultados.

---

## 3. Metodologia

A metodologia utilizada para a execução deste plano de trabalho será sistematizada em cinco fases:

1. **Fase Teórica (FT):**
   - *Atividades:* Levantamento das bibliotecas da linguagem de programação Python e dos LLMs usados para a geração automática de relatórios a partir de dados textuais, áudios, imagens e vídeos.
   - *Resultado Esperado:* Relatório técnico contendo um resumo das principais bibliotecas, incluindo tutoriais de instalação e uso.

2. **Fase de Planejamento (FP):**
   - *Atividades:* Especificação das funcionalidades e requisitos do protótipo a ser desenvolvido.
   - *Resultado Esperado:* Relatório técnico com as funcionalidades e requisitos levantados, além de exemplos de relatórios de inquéritos periciais dos principais tipos de exames/laudos.

3. **Fase de Desenvolvimento (FD):**
   - *Atividades:* Desenvolvimento de métodos para auxiliar a criação de relatórios de inquéritos periciais dos principais tipos de exames. Verificação de pendências nos modelos gerados e solicitação de informações adicionais ao perito responsável para comprovação dos fatos, se necessário.
   - *Resultado Esperado:* Aplicação parcial com os métodos desenvolvidos e relatório técnico destacando os principais resultados e limitações da solução.

4. **Fase de Integração (FI):**
   - *Atividades:* Integração de todas as funcionalidades em um protótipo Web ou Mobile.
   - *Resultado Esperado:* Aplicativo funcional integrado.

5. **Fase Final (FF):**
   - *Atividades:* Experimentação, descrição, discussão e publicação dos principais resultados.
   - *Resultado Esperado:* Aplicativo funcional acompanhado de documentação, vídeos explicativos, relatórios técnicos e artigos científicos.

---

## 4. Referências

- **[1]** FÓRUM BRASILEIRO DE SEGURANÇA PÚBLICA. *18º Anuário Brasileiro de Segurança Pública*. São Paulo: Fórum Brasileiro de Segurança Pública, 2024. Disponível em: [https://publicacoes.forumseguranca.org.br/handle/123456789/253](https://publicacoes.forumseguranca.org.br/handle/123456789/253).
- **[2]** MITCHELL, T. *Machine Learning: An Artificial Intelligence Approach*, Volume III (English Edition). Editora: Morgan Kaufmann; 1ª edição, 2014.
- **[3]** BIRD, S.; KLEIN, E.; LOPER, E. *Natural Language Processing with Python: Analyzing Text with the Natural Language Toolkit*. Editora: O'Reilly Media; 1st Edition, 2009.
- **[4]** CASELI, H. M.; NUNES, M.G.V. (org.) *Processamento de Linguagem Natural: Conceitos, Técnicas e Aplicações em Português*. 3 ed. BPLN, 2024. Disponível em: [https://brasileiraspln.com/livro-pln/3a-edicao](https://brasileiraspln.com/livro-pln/3a-edicao).
- **[5]** WANG, H.; LI, J.; WU, H.; HAVY, E.; SUN, Y. *Pre-Trained Language Models and Their Applications*. Engineering, 2023.
