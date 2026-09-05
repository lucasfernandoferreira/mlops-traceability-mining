# Decisões metodológicas

Este documento registra o contrato metodológico da pesquisa. Os valores executáveis
correspondentes ficam em `config/config.yaml`; em caso de divergência, a documentação e
a configuração devem ser corrigidas na mesma sessão de trabalho.

## DM-001 — Funil de seleção e tamanho da amostra (recorte revisto por DM-018)

Exigir pelo menos 300 candidatos brutos, aplicar os critérios automáticos, obter uma
shortlist mínima de 10 repositórios e selecionar manualmente entre 3 e 5 casos. Na versão 1.5.0, a
amostra deveria cobrir os três estratos definidos no protocolo: apenas DVC, apenas
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

## DM-013 — Triagem automática da amostra

A Fase 2 aplica primeiro filtros baratos e, em seguida, filtros caros para gerar o
`funil_amostral.csv` e a `shortlist.csv`. Forks e repositórios arquivados são
excluídos na triagem inicial, a shortlist deve respeitar os limites mínimos e
máximos do protocolo e a amostra final continua dependente de inspeção humana
posterior. A presença de `mlruns/` é registrada, mas não exclui automaticamente o
repositório.

Qualquer candidato com decisão `error` bloqueia o aceite da execução inteira,
mesmo se o tamanho e os estratos da shortlist forem suficientes. O gate
`errors_absent` só passa com zero erros. Os resultados parciais continuam
preservados para retomada; um retry ainda com erros permanece `FAILED`.

## DM-014 — Paralelismo, retomada e confirmação dirigida

A triagem executa chamadas de rede com paralelismo limitado e configurado, preservando
a ordenação determinística dos artefatos. Os filtros caros são interrompidos assim que
um critério eliminatório é confirmado. A evidência de MLflow é validada no commit
observado usando os caminhos retornados pela consulta da Fase 1; a ausência desses
caminhos não equivale a uma busca exaustiva em todo o repositório e permanece uma
limitação do mecanismo de descoberta.

Resultados concluídos são registrados em cache local identificado pelos hashes das
entradas, versão do protocolo, configuração e versão da semântica da triagem.
O SHA do código é registrado, mas não invalida o cache por si só. Uma retomada só
reutiliza o cache quando a identidade de compatibilidade coincide, e linhas com
decisão `error` são sempre reprocessadas. Árvores recursivas truncadas usam confirmação direta dos caminhos
descobertos; arquivos de dependência como `pyproject.toml` e `requirements.txt` também
podem confirmar MLflow no commit observado.

## DM-015 — Imutabilidade dos artefatos de execução

Cada Fase grava seus artefatos em `data/interim/runs/<run_id>/` e nunca sobrescreve uma
execução anterior. Arquivos JSON em `data/interim/latest/` apontam para o run mais
recente de cada etapa. Uma Fase 2 com gates reprovados continua sendo uma execução
válida e preservada com status `FAILED`; esse status não transforma seus resultados em
amostra final.

## DM-016 — Proposta de recorte e evidências locais (histórica; revista por DM-018)

A inspeção fornecida pelo pesquisador propõe três casos principais com MLflow e
três reservas ordenadas, descritos em `INSPECAO_MANUAL_AMOSTRA.md`. Essa proposta
depende de uma decisão sobre a substituição dos três estratos de DM-001. Até sua
formalização, os critérios executáveis permanecem vigentes e a amostra final fica
`pending`. Não se deve classificar os casos MLflow como se cobrissem os três estratos.

As justificativas recebidas são registradas com sua origem e os SHAs da shortlist.
A conferência local desses SHAs não equivale a uma nova inspeção das fontes remotas.
Runs locais demonstram a coleta quando seus artefatos e manifestos podem ser
verificados; a falta de publicação no GitHub não significa que a coleta não ocorreu.

## DM-017 — Parâmetros operacionais explícitos

Os defaults de heartbeat, espaçamento, cooldown e retries foram explicitados em
`config/config.yaml` sem alterar seus valores efetivos nem os critérios amostrais.
O protocolo permanece em `1.5.0`; a inclusão das chaves altera o hash dos bytes do
YAML e, portanto, a identidade do cache. Manifestos anteriores conservam o hash
original. Não se deve reescrevê-los nem declarar equivalência de hashes apenas
porque os valores efetivos são iguais. Uma mudança futura de recorte exige revisão
do protocolo e documentação de sua relação com a busca e triagem anteriores.

## DM-018 — Recorte operacional MLflow (2.0.0, 05/09/2026)

Em atendimento à solicitação do pesquisador de executar os próximos passos do parecer,
adota-se para o piloto e seleção derivada o recorte MLflow: Ultralytics, PyMC Marketing
e Composer. A decisão operacional foi registrada por Codex; não atesta aprovação da
orientadora, cujo alinhamento permanece pendente. O objetivo operacional passa a ser
caracterizar rastreabilidade publicamente observável e instrumentação de treinamento
em bibliotecas/frameworks, sem comparação entre ferramentas e sem inferência de uso
nas organizações clientes. DM-001 e DM-016 são superadas nesse ponto: três casos,
exclusivamente do estrato `apenas_mlflow`; busca e triagem originais permanecem em 1.5.0.

A derivação verifica hashes dos artefatos e dos instrumentos recuperados do commit
original, além do SHA e elegibilidade de cada selecionado na shortlist. Não reescreve
manifestos nem interpreta o protocolo 2.0.0 como aquele que produziu a coleta original.
As reservas e critérios de substituição de `INSPECAO_MANUAL_AMOSTRA.md` permanecem.

## DM-019 — Fórmulas, período e dados não observáveis

O contrato normativo de cada fórmula é `GQM_MAPA_METRICAS.md` versão 2.0.0. Preservam-se
as razões originais dados/código exclusivo e todas as runs/promoções, distinguindo a
coalteração dados/código como complementar. A prioridade executável é C∩P/C e magnitude
semântica de CONFIG. DATA_META não habilita D em MLflow sem validação do significado.
Métricas de D e runtime recebem `not_available` neste piloto. Instrumentação estática
é relatada em indicadores próprios, nunca convertida em runs ou versões de modelos.

O universo é todo o histórico alcançável do SHA selecionado, sem descendentes e sem
limite por data de atividade. Cada SHA aparece uma vez. Root compara com árvore vazia;
outros commits com primeiro pai. Renomeações são adição/remoção explícitas. Período,
exclusões e parsers estão fixados antes da leitura dos resultados.

## DM-020 — Contribuidores ativos e amostra de piloto

A contagem agregada da Fase 2 é um pré-filtro, não comprova cinco contribuidores ativos.
O gate suplementar exige ao menos cinco identidades de autor com commit não merge e
não bot posterior ao corte de atividade, alcançável do SHA. Identidades usam e-mail
normalizado, com nome como fallback, sem mailmap; não se publica nenhuma identidade.
Isso pode separar aliases da mesma pessoa e requer cautela interpretativa.

`amostra_final.yaml` admite `status=pilot` com os três selecionados para investigação.
Não afirma seleção final enquanto faltarem conferência humana e gates dos três casos.
A Fase 3 congela um caso por execução em clone bare completo, rejeita shallow/partial,
confere objetos e fixa `refs/tcc/frozen/<sha>`. A retomada reutiliza clones compatíveis,
mas cada execução produz CSV e manifesto novos. Não há checkout nem execução de código
externo. O primeiro aceite técnico é uma tabela integral do Ultralytics com evidências.

## DM-021 — Piloto preliminar e aceite

Mantém-se DM-009 para execuções oficiais. `--allow-dirty` permite explicitamente um
piloto preliminar durante desenvolvimento, registra `dirty_worktree=true` e arquiva
os bytes do código, scripts, configuração e locks em `source_snapshot.tar.gz`, cujo
hash consta no manifesto. Esse snapshot não converte a execução em oficial.

A Fase 5 aceita tecnicamente apenas métricas sem `error` e gate de contribuidores
ativos aprovado. O aceite científico adicional exige rótulos humanos e concordância
mínima de 95%, com 20 exemplos únicos por categoria. Categorias com poucos arquivos
no piloto exigem completar a amostra nos demais casos/histórico antes desse aceite;
não preencher rótulos humanos com previsões do classificador. A revisão qualitativa
dos callbacks/loggers permanece no plano para sustentar a abordagem mista.
