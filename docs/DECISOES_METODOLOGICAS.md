# Decisões metodológicas

Este documento registra o contrato metodológico da pesquisa. Os valores executáveis
correspondentes ficam em `config/config.yaml`; em caso de divergência, a documentação e
a configuração devem ser corrigidas no mesmo commit.

## DM-001 — Funil de seleção e tamanho da amostra

Exigir pelo menos 300 candidatos brutos, aplicar os critérios automáticos, obter uma
shortlist mínima de 10 repositórios e selecionar manualmente entre 3 e 5 casos. A
amostra final deve cobrir os três estratos definidos no protocolo: apenas DVC, apenas
MLflow e DVC com MLflow.

Justificativa: a shortlist de 10 resolve a divergência anterior entre 8 e 10 e preserva
margem para exclusões justificadas durante a inspeção manual. A amostra pequena é
intencional e favorece análise longitudinal aprofundada; ela não sustenta inferência
estatística para toda a população do GitHub.

## DM-002 — Definição de atividade

Um repositório é considerado ativo quando possui pelo menos um commit não automatizado
posterior a `2025-09-01T00:00:00Z`. A data será comparada em UTC. Commits de merge e de
bots não entram nas métricas, conforme DM-006.

## DM-003 — Unidade e ordem da classificação

Cada caminho modificado recebe exatamente uma categoria. A primeira expressão regular
compatível em `config/file_taxonomy.yaml` vence; portanto, a ordem das regras é parte
versionada do instrumento. `NOTEBOOK` permanece uma categoria própria para auditoria,
mas compõe a dimensão lógica de código (`CODE + NOTEBOOK`) nas métricas GQM de
acoplamento.

## DM-004 — Ausência não equivale a zero

A falta de dados públicos necessários recebe status `not_available`, nunca valor zero.
Uma métrica fora do escopo de um caso recebe `not_applicable`; denominador elegível igual
a zero recebe `undefined`. Falha de coleta ou processamento é `error` e não pode ser
publicada como resultado observado.

## DM-005 — Commits grandes

Commits com mais de 1.000 arquivos modificados serão sinalizados e excluídos da
mineração semântica. Eles permanecem contabilizados no funil de descarte, com o motivo
registrado, para evitar uma exclusão invisível.

## DM-006 — Merges e automações

Commits de merge e commits identificados como bots serão excluídos das métricas de
acoplamento. A identificação de bot usa os padrões versionados em `config/config.yaml`.
As contagens excluídas e seus motivos devem ser preservados para auditoria, pois padrões
textuais podem produzir falsos positivos ou falsos negativos.

## DM-007 — Critérios automáticos de elegibilidade

Antes da inspeção manual, o repositório deve ter ao menos 300 commits, 5 contribuidores
e 100 estrelas, além de satisfazer a definição de atividade. Termos de exclusão como
`tutorial`, `course`, `classroom`, `homework`, `awesome-list` e `toy-project` reduzem a
presença de material didático e projetos de demonstração. Todo descarte deve indicar o
critério aplicado.

As consultas à API são mecanismos de descoberta, não evidência suficiente de uso das
ferramentas. A presença efetiva de DVC e/ou MLflow deve ser confirmada por artefatos
versionados e registrada antes da estratificação.

A busca inicial é intencionalmente amostral e preserva a evidência bruta. Consultas
que ultrapassam o limite coletável da API são marcadas como truncadas, e buscas
incompletas não devem ser reinterpretadas como cobertura total da população.

## DM-008 — Unidades de análise

O repositório é a unidade de seleção e comparação entre casos. O commit elegível é a
unidade temporal das métricas baseadas em coalteração. Arquivos são classificados para
formar as dimensões do commit. Runs e versões de modelos só serão unidades observáveis
quando houver evidência pública e vinculável ao repositório.

## DM-009 — Proveniência das execuções

Cada execução oficial deve ocorrer com worktree limpo e registrar um manifesto com o
SHA do código, versão do protocolo, hashes da configuração, taxonomia e dependências,
versão do Python, sistema operacional, intervalo temporal e estado da execução. Horários
devem ser gravados em UTC.

## DM-010 — Validação da taxonomia

A taxonomia deve ser avaliada com 20 exemplos por categoria e concordância mínima de
0,95. A amostra de validação, os rótulos esperados, o resultado e qualquer mudança nas
regras devem ser versionados. Enquanto essa avaliação manual não for realizada, a
taxonomia é considerada tecnicamente testada, mas não empiricamente validada.

## DM-011 — Congelamento da amostra final

`config/amostra_final.yaml` permanece com status `pending` até a conclusão documentada
do funil. Ao ser finalizado, deve registrar repositórios, estratos, justificativas,
data UTC, commit da seleção e hash da configuração usada. Nenhum repositório será
incluído apenas para preencher os estratos sem satisfazer os critérios de elegibilidade.

## DM-012 — Descoberta bruta por GitHub Search

A Fase 1 usa consultas configuradas com paginação serial no GitHub Code Search para
gerar `candidatos_brutos.csv`, `evidencias_busca.csv` e `resumo_busca.csv`. A
deduplicação da saída bruta usa o ID numérico do repositório, e a ordenação final dos
artefatos é determinística para facilitar auditoria. O viés de ordenação inerente à
API, bem como truncamentos por limite coletável, devem permanecer explícitos na
documentação e no manifesto.
