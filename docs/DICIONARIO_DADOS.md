# Dicionário de dados

Este documento reúne os contratos dos arquivos usados nas fases de busca, triagem,
mineração, análise e revisão do protocolo 2.1.0. Os resultados de cada rodada estão
no [registro dos casos](INSPECAO_MANUAL_AMOSTRA.md); a existência de um esquema não
indica que uma coleta ou revisão tenha sido concluída.

Datas são ISO 8601 em UTC, commits usam SHA integral de 40 caracteres e caminhos
usam `/`. Repositórios são identificados por `owner/name`. Proporções são armazenadas
entre zero e um. CSVs usam UTF-8, booleanos `true`/`false` e campos vazios para valores
ausentes; JSON usa tipos nativos. `decision_reasons` separa motivos por ` | `.
Os estados que explicam a ausência de valores seguem o [mapa GQM](GQM_MAPA_METRICAS.md).

## Configuração executável

Fonte: `config/config.yaml`. O carregador rejeita campos desconhecidos ou ausentes.

| Grupo/campo | Tipo | Significado |
|---|---|---|
| `protocol.id` | string | Identificador estável do protocolo. |
| `protocol.version` | string | Versão do contrato metodológico. |
| `execution.screening_workers` | inteiro 1–16 | Workers simultâneos da triagem. |
| `execution.progress_interval_seconds` | inteiro >= 1 | Intervalo entre atualizações de progresso. |
| `execution.progress_stall_threshold_seconds` | inteiro >= 1 | Tempo sem avanço para marcar espera e suspender a ETA. |
| `execution.mlflow_manifest_scan_limit` | inteiro 1–500 | Máximo de manifestos de dependência inspecionados por repositório. |
| `paths.*` | path | Diretórios de entrada, derivados, manifestos e relatórios. |
| `github.token_environment_variable` | string | Nome da variável que contém o token; nunca o token. |
| `github.per_page` | inteiro > 0 | Tamanho da página usado na busca paginada. |
| `github.max_results_per_query` | inteiro > 0 | Limite coletável por consulta antes de truncar. |
| `github.request_timeout_seconds` | inteiro > 0 | Timeout de requisição do adaptador GitHub. |
| `github.rate_limit.code_search_reserve` | inteiro >= 0 | Reserva mínima antes de pausar chamadas de Code Search. |
| `github.rate_limit.core_reserve` | inteiro >= 0 | Reserva mínima para chamadas da API core. |
| `github.rate_limit.reset_buffer_seconds` | inteiro >= 0 | Folga aplicada após o reset declarado pela API. |
| `github.rate_limit.request_interval_seconds` | número 0–10 | Espaçamento entre inícios de requisições. |
| `github.rate_limit.secondary_cooldown_seconds` | inteiro 1–3600 | Espera compartilhada após limite secundário. |
| `github.rate_limit.secondary_max_retries` | inteiro 0–10 | Retries permitidos antes de abrir o circuito. |
| `github.rate_limit.max_rate_limit_wait_seconds` | inteiro 1–3600 | Limite de espera exigida pelo rate limit. |
| `github.queries[].id` | string | Identificador estável de cada consulta. |
| `github.queries[].expression` | string | Expressão Code Search executada. |
| `selection.min_candidates` | inteiro > 0 | Quantidade mínima de candidatos brutos. |
| `selection.min_commits` | inteiro > 0 | Mínimo de commits para elegibilidade. |
| `selection.min_contributors` | inteiro > 0 | Mínimo de contribuidores para elegibilidade. |
| `selection.min_stars` | inteiro >= 0 | Mínimo de estrelas para elegibilidade. |
| `selection.active_after` | datetime UTC | Corte de atividade para commit humano. |
| `selection.min_shortlist` | inteiro > 0 | Quantidade mínima antes da inspeção manual. |
| `selection.max_shortlist` | inteiro > 0 | Quantidade máxima antes da inspeção manual. |
| `selection.final_sample_min/max` | inteiro > 0 | Intervalo permitido para a amostra final. |
| `selection.exclude_forks` | booleano | Exclui forks na triagem. |
| `selection.exclude_archived` | booleano | Exclui repositórios arquivados na triagem. |
| `selection.forbidden_terms` | lista de strings | Termos usados para excluir material didático ou de demonstração. |
| `strata.required` | lista enumerada | Estratos que a amostra final deve cobrir. |
| `commit_filter.exclude_merges` | booleano | Exclui merges das métricas quando verdadeiro. |
| `commit_filter.exclude_bots` | booleano | Exclui bots das métricas quando verdadeiro. |
| `commit_filter.large_commit_max_files` | inteiro > 0 | Maior quantidade de arquivos aceita na mineração semântica. |
| `commit_filter.large_commit_action` | enum | `flag_only` ou `flag_and_skip`. |
| `commit_filter.bot_patterns` | lista de strings | Padrões textuais usados na identificação de automações. |
| `taxonomy_validation.samples_per_category` | inteiro > 0 | Exemplos exigidos por categoria na validação manual. |
| `taxonomy_validation.minimum_agreement` | número [0, 1] | Concordância mínima aceita. |
| `taxonomy_validation.calibration_units` | lista de strings | Unidades `repositório:caminho` usadas na calibração, separadas da avaliação quando possível. |
| `analysis.plan_version`, `analysis.planned_at_utc` | string / datetime | Versão e data de definição do plano analítico. |
| `analysis.events_per_group`, `analysis.group_order`, `analysis.fill_deficits` | inteiro / lista / booleano | Cotas, precedência dos grupos e preenchimento dos eventos restantes. |
| `analysis.quantile_method`, `analysis.concentration_top_fraction` | string / número | Interpolação de quantis e fração superior usada na concentração. |
| `analysis.figure_dpi` | inteiro | Resolução das figuras exportadas. |
| `analysis.dataset_path_pattern`, `analysis.class_map_key` | strings | Regras sintáticas das variantes de sensibilidade. |
| `reproducibility.require_clean_worktree` | booleano | Exige estado Git limpo em execução oficial. |
| `reproducibility.save_manifests` | booleano | Determina a persistência de manifestos. |
| `reproducibility.hash_algorithm` | enum | Algoritmo dos artefatos; atualmente apenas `sha256`. |

## Classificação de arquivos

Fonte: `config/file_taxonomy.yaml`. A primeira regra compatível vence.

| Campo | Tipo | Significado |
|---|---|---|
| `taxonomy_version` | string | Versão das regras que produziram a classe. |
| `file_path` | string | Caminho normalizado do artefato. |
| `category` | enum | Categoria mutuamente exclusiva atribuída ao caminho. |

Categorias permitidas:

| Categoria | Interpretação |
|---|---|
| `TEST` | Testes automatizados e fixtures. |
| `CI` | Integração e entrega contínuas. |
| `ENV` | Dependências, ambiente e contêineres. |
| `DATA_META` | Metadados de dados e pipelines DVC. |
| `CONFIG` | Parâmetros e configurações do pipeline. |
| `NOTEBOOK` | Notebooks versionados. |
| `CODE` | Código-fonte executável. |
| `DOC` | Documentação textual. |
| `DATA_RAW` | Dados ou mídia potencialmente pesados. |
| `OUTRO` | Caminho sem correspondência anterior. |

## Manifesto de execução

Fonte: JSON produzido por `mlops_traceability.manifest.write_manifest`.

| Campo | Tipo | Anulável | Significado |
|---|---|---:|---|
| `schema_version` | string | não | Versão do esquema do manifesto. |
| `run_id` | string | não | Identificador composto por horário UTC com microssegundos, SHA abreviado e etapa. |
| `protocol_id` | string | não | Identificador do protocolo usado. |
| `protocol_version` | string | não | Versão do protocolo usado. |
| `stage` | string | não | Etapa executada. |
| `status` | enum | não | `SUCCESS` ou `FAILED`. |
| `started_at_utc` | datetime | não | Início da execução em UTC. |
| `finished_at_utc` | datetime | não | Término da execução em UTC. |
| `code_commit_sha` | string | não | Revisão do código executor. |
| `dirty_worktree` | booleano | não | Indica alterações não registradas no Git. |
| `config_sha256` | string | não | Hash SHA-256 da configuração. |
| `taxonomy_sha256` | string | não | Hash SHA-256 da taxonomia. |
| `requirements_sha256` | string | não | Hash SHA-256 das dependências travadas. |
| `python_version` | string | não | Versão completa do interpretador. |
| `operating_system` | string | não | Identificação da plataforma. |
| `artifacts` | lista de objetos | não | Artefatos gerados com caminho, SHA-256 e contagem de linhas. |
| `error` | string | sim | Diagnóstico quando a etapa falha. |

## Busca da Fase 1

Fonte: `scripts/01_search_candidates.py` e `src/mlops_traceability/github_search.py`.

### `resumo_execucao_fase1.json`

Resumo da coleta, com volumes e referências aos arquivos produzidos.

| Campo | Tipo | Significado |
|---|---|---|
| `schema_version` | string | Versão do relatório de execução. |
| `run_id` | string | Execução que produziu o relatório. |
| `stage` | string | Etapa executada. |
| `started_at_utc` | datetime UTC | Início da execução. |
| `finished_at_utc` | datetime UTC | Fim da execução. |
| `candidate_count` | inteiro >= 0 | Quantidade de candidatos únicos produzidos. |
| `evidence_count` | inteiro >= 0 | Quantidade total de evidências coletadas. |
| `query_count` | inteiro >= 0 | Quantidade de consultas executadas. |
| `truncated_query_count` | inteiro >= 0 | Número de consultas truncadas. |
| `incomplete_query_count` | inteiro >= 0 | Número de consultas marcadas como incompletas. |
| `queries[]` | lista de objetos | Resumo por consulta, com totais e flags. |
| `artifacts[]` | lista de objetos | Saídas geradas pela Fase 1, com caminho, SHA-256 e linhas. |
| `status` | string | Estado final do relatório de execução. |

### `candidatos_brutos.csv`

Uma linha por repositório único descoberto na Fase 1.

| Campo | Tipo | Significado |
|---|---|---|
| `repository_numeric_id` | inteiro | ID numérico estável retornado pelo GitHub. |
| `repository_id` | string | Identificador público `owner/name`. |
| `repository_url` | string | URL canônica do repositório. |
| `owner_login` | string | Login do proprietário observado. |
| `is_fork` | booleano | Estado de fork observado, sem filtragem. |
| `description` | string | Descrição pública do repositório, quando disponível. |
| `discovery_query_count` | inteiro >= 0 | Quantidade de consultas distintas que localizaram o repositório. |
| `discovery_hit_count` | inteiro >= 0 | Quantidade total de evidências encontradas para o repositório. |
| `observed_at_utc` | datetime UTC | Instante da coleta. |
| `run_id` | string | Execução que produziu a linha. |

### `evidencias_busca.csv`

Uma linha por resultado retornado pela API.

| Campo | Tipo | Significado |
|---|---|---|
| `query_id` | string | Consulta responsável pela evidência. |
| `query_expression` | string | Expressão executada. |
| `page_number` | inteiro >= 1 | Página da API usada na coleta. |
| `result_rank` | inteiro >= 1 | Posição da evidência dentro da página. |
| `repository_numeric_id` | inteiro | ID numérico do repositório vinculado. |
| `repository_id` | string | Identificador `owner/name` observado. |
| `file_path` | string | Caminho do arquivo encontrado. |
| `file_sha` | string | SHA do arquivo retornado pela API. |
| `file_url` | string | URL navegável da evidência. |
| `run_id` | string | Execução que produziu a linha. |

### `resumo_busca.csv`

Uma linha por consulta executada.

| Campo | Tipo | Significado |
|---|---|---|
| `query_id` | string | Identificador da consulta. |
| `query_expression` | string | Expressão executada. |
| `reported_total_count` | inteiro >= 0 | Total informado pela API. |
| `retrieved_hit_count` | inteiro >= 0 | Total efetivamente coletado. |
| `unique_repository_count` | inteiro >= 0 | Repositórios distintos observados. |
| `incomplete_results` | booleano | Sinal da própria API para busca incompleta. |
| `truncated` | booleano | Marca quando o limite coletável foi atingido. |
| `started_at_utc` | datetime UTC | Início da consulta. |
| `finished_at_utc` | datetime UTC | Fim da consulta. |
| `run_id` | string | Execução que produziu a linha. |

## Triagem da Fase 2

Fonte: `scripts/02_screen_sample.py`, lista `SCREENING_FIELDS` e função
`_candidate_to_output_row`. `funil_amostral.csv` contém uma linha por candidato
avaliado; `shortlist.csv` usa as mesmas colunas e contém apenas `decision=eligible`.
Elegibilidade automática não equivale a inclusão manual na amostra final.

| Campo | Tipo | Anulável | Significado |
|---|---|---:|---|
| `repository_numeric_id` | inteiro | não | Identificador numérico estável do GitHub. |
| `repository_id` | string | não | Identificador público `owner/name`. |
| `repository_url` | string | não | URL canônica observada. |
| `source_run_id` | string | não | Execução de busca que originou o candidato. |
| `screening_run_id` | string | não | Execução de triagem que publicou a linha, inclusive quando reutilizada. |
| `observed_at_utc` | datetime | não | Instante de observação herdado do candidato da Fase 1; não é o horário de cada chamada da triagem. |
| `head_commit_sha` | string | sim | Revisão observada durante a seleção. |
| `stars_count` | inteiro >= 0 | sim | Estrelas na data de observação. |
| `commit_count` | inteiro >= 0 | sim | Commits segundo o método registrado. |
| `contributor_count` | inteiro >= 0 | sim | Contagem agregada de contribuidores. |
| `last_human_commit_at_utc` | datetime | sim | Última atividade não automatizada. |
| `dvc_detected` | booleano | sim | Evidência de DVC pelo detector da triagem. |
| `mlflow_detected` | booleano | sim | Import ou dependência MLflow confirmada; não mede proveniência. |
| `mlruns_detected` | booleano | sim | Presença de `mlruns/` na raiz pelo procedimento atual. |
| `stratum` | enum | sim | `apenas_dvc`, `apenas_mlflow` ou `dvc_e_mlflow`. |
| `cheap_gate_status` | enum | não | `passed`, `failed` ou `error` nos filtros iniciais. |
| `expensive_gate_status` | enum | não | `passed`, `failed`, `error` ou `not_evaluated` nos filtros caros. |
| `decision` | enum | não | `eligible`, `rejected` ou `error`. |
| `exclusion_stage` | enum | sim | `snapshot`, `cheap` ou `expensive`; vazio para elegíveis. |
| `primary_reason` | string | sim | Primeiro motivo de decisão, usado na contagem exclusiva do funil. |
| `decision_reasons` | string delimitada | não | Motivos separados por ` | `; pode haver vários por candidato. |
| `error_detail` | string | sim | Diagnóstico de falha de coleta; vazio quando não houve erro. |

Campos podem ficar vazios quando um filtro anterior interrompe a avaliação.
Falha de API produz `decision=error`, nunca rejeição científica silenciosa. `false`
em `mlruns_detected` significa não detectado pelo procedimento atual; não exclui
pastas aninhadas, histórico anterior ou serviços de tracking externos.

### `resumo_execucao_fase2.json`

| Campo | Tipo | Significado |
|---|---|---|
| `schema_version` | string | Versão do esquema do resumo. |
| `stage` | string | `phase2_screen_sample`. |
| `status` | enum | `SUCCESS` somente se todos os critérios passarem; caso contrário `FAILED`. |
| `screening_run_id` | string | Execução que produziu o resumo. |
| `source_run_id` | string | Execução de busca usada como entrada. |
| `received_candidates` | inteiro >= 0 | Candidatos recebidos da Fase 1. |
| `screened_rows` | inteiro >= 0 | Linhas produzidas na triagem. |
| `eligible` / `rejected` / `errors` | inteiro >= 0 | Contagens por decisão. |
| `reused_rows` / `processed_rows` | inteiro >= 0 | Resultados reutilizados e processados nesta execução. |
| `discard_counts_by_primary_reason` | objeto de contagens | Cada candidato não elegível conta uma vez pelo primeiro motivo. |
| `discard_counts_by_reason` | objeto de contagens | Todos os motivos; a soma pode superar o total de candidatos descartados. |
| `strata_distribution` | objeto de contagens | Distribuição dos elegíveis por estrato. |
| `mlruns_detected_count` | inteiro >= 0 | Elegíveis com `mlruns_detected=true`. |
| `gates` | objeto de booleanos | Critérios de aceite listados abaixo. |
| `input_artifacts` / `output_artifacts` | lista de objetos | Caminhos e hashes SHA-256 dos CSVs de entrada e saída. |

Os critérios de aceite são `worktree_clean`, `input_run_ids_match`, `errors_absent`,
`shortlist_bounds`, `required_strata_present` e `mlruns_evaluated_on_eligible`.
`errors_absent` exige zero erros, mesmo que a shortlist já tenha tamanho e estratos
suficientes. Resumos anteriores à introdução desse gate não contêm essa chave;
seus arquivos e manifestos devem ser preservados sem alteração retroativa.

### Ponteiros e decisões manuais

`data/interim/latest/<stage>.json` contém `schema_version`, `stage`, `status`,
`run_id`, `source_run_id`, `run_directory`, `artifacts` e `manifest_path`.
Os caminhos de `artifacts` são relativos a `data/interim/`. O ponteiro aponta para
a última execução, inclusive quando `FAILED`; não significa última execução aprovada.

As justificativas fornecidas para a inspeção humana estão em
`docs/INSPECAO_MANUAL_AMOSTRA.md`, separadas dos CSVs automáticos. A proposta de
amostra não deve substituir a shortlist nem alterar suas decisões originais.

## Commits e mudanças

Uma linha de commit representa uma revisão elegível ou excluída. A tabela de mudanças
possui uma linha por caminho modificado no commit.

| Campo | Tipo | Anulável | Significado |
|---|---|---:|---|
| `repository_id` | string | não | Repositório analisado. |
| `commit_sha` | string | não | SHA integral da revisão. |
| `committed_at_utc` | datetime | não | Horário do commit normalizado para UTC. |
| `parent_count` | inteiro >= 0 | não | Quantidade de pais; permite identificar merges. |
| `is_bot` | booleano | não | Resultado do filtro de automação. |
| `files_changed_count` | inteiro >= 0 | não | Total de caminhos alterados. |
| `eligibility_status` | enum | não | `included`, `merge`, `bot`, `large_commit` ou `error`. |
| `file_path` | string | não | Caminho da mudança; existe apenas na tabela de mudanças. |
| `change_type` | enum | não | `A`, `M`, `D` ou `T`, códigos Git; renomeação conta como D+A. |
| `category` | enum | não | Categoria atribuída pela taxonomia vigente. |
| `run_id` | string | não | Manifesto da mineração. |

As tabelas analíticas não contêm nome ou email do autor.

## Resultado de métrica

| Campo | Tipo | Anulável | Significado |
|---|---|---:|---|
| `repository_id` | string | não | Caso analisado. |
| `metric_id` | enum | não | Métrica definida em `docs/GQM_MAPA_METRICAS.md`. |
| `period_start_utc` | datetime | não | Início inclusivo do período. |
| `period_end_utc` | datetime | não | Fim inclusivo do período. |
| `value` | número | sim | Valor somente quando `status=observed`. |
| `status` | enum | não | `observed`, `not_available`, `not_applicable`, `undefined` ou `error`. |
| `status_detail` | string | sim | Justificativa da ausência ou falha. |
| `numerator` | número | sim | Numerador auditável quando aplicável. |
| `denominator` | número | sim | Denominador auditável quando aplicável. |
| `excluded_commit_count` | inteiro >= 0 | não | Commits fora do cálculo. |
| `protocol_version` | string | não | Versão metodológica usada. |
| `taxonomy_version` | string | não | Versão da classificação usada. |
| `run_id` | string | não | Manifesto do cálculo. |

As fórmulas, escalas e regras de ausência estão em `docs/GQM_MAPA_METRICAS.md`.

## Seleção e contexto dos casos

`config/amostra_final.yaml` guarda a proposta de amostra e a relação com a coleta.
`config/casos.yaml` descreve domínio, contraste, caminhos de integração, operação,
habilitação e escopo das evidências. As fichas geradas pelo índice incorporam esses
campos e deixam a decisão do pesquisador em branco.

| Campo da amostra | Significado |
|---|---|
| `schema_version`, `protocol_id`, `protocol_version` | Identidade do contrato e do protocolo. |
| `status` | Estado da proposta: `pending`, `pilot` ou `final`; não certifica o aceite. |
| `selected_at_utc` | Data de preparação da seleção registrada, que pode ainda ser piloto. |
| `selection_commit_sha`, `selection_config_sha256` | Referências históricas do instrumento no início da seleção. |
| `source_runs`, `source_shortlist_sha256` | Busca, triagem e hash da shortlist original. |
| `repositories` | Casos atuais com ID, URL, SHA, estrato, justificativa e evidências. |
| `historical_repositories` | Casos substituídos, com motivo técnico e situação da decisão humana. |
| `technical_revision_at_utc`, `technical_revision_reason` | Data e motivo da atualização técnica da proposta. |
| `academic_alignment_status`, `human_taxonomy_validation_status` | Situação das revisões declaradas. |
| `pending_reason`, `decision_responsibility` | Pendência e responsabilidade pelo registro técnico. |

Os campos históricos da seleção não afirmam que a configuração atual existia no
commit inicial. Cada execução preserva os bytes usados em seu próprio snapshot.

## Congelamento e mineração

| Arquivo | Conteúdo |
|---|---|
| `amostra_congelada.csv` | Um caso por execução: URL, SHA, clone, estrato, commits alcançáveis, tamanho, `shallow=false` e `run_id`. |
| `source_audit.json` | Conferência dos artefatos e instrumentos originais de busca e triagem. |
| `commits.parquet` | Todas as revisões: pais, data, elegibilidade, C/D/P, magnitude e estado semântico. |
| `changes.parquet` | Caminhos dos commits incluídos: categoria, A/M/D/T, blobs anterior/posterior, chaves e estado semântico. |
| `mining_summary.json` | Funil exclusivo, período, contagem de identidades ativas, critério de atividade e erros semânticos. |
| `tree_inspection.json` | Arquivos da árvore congelada, blobs, candidatos AST, linhas, URLs, hashes, erros e caminhos `mlruns`. |
| `metric_membership.csv` | Membros dos denominadores, com `metric_id`, `commit_sha`, `in_numerator` e `numerator_contribution`. |
| `metrics.csv` | Medidas do mapa GQM, com SHA do caso, unidade e situação da validação. |
| `source_snapshot.tar.gz` | Instrumento executado: código, scripts, configuração e documentos; sem credenciais nem clones. |
| `execution.json` | Resultado técnico, erro, origem e condição de elegibilidade da cadeia. |

Em `commits.parquet`, `parent_sha` é vazio no commit inicial; `large_commit` informa
o limite de arquivos. `config_changed_keys` é nulo quando a semântica não foi
observada. D continua sendo o indicador técnico DATA_META. Em `changes.parquet`,
`before_blob_sha` e `after_blob_sha` permitem conferir adições e remoções;
`changed_keys` é uma lista de caminhos tipados. Arquivos fora de CONFIG têm
`semantic_status=not_applicable` e contagem nula.

A quantidade de linhas de `metric_membership.csv` por medida reproduz seu denominador;
a soma das contribuições reproduz o numerador. Renomeações contam como D+A na análise
principal. O tamanho dos binários é registrado em `byte_count` no manifesto;
`line_count` pode ser nulo. Manifestos anteriores mantêm seus esquemas originais.

## Inventário e revisão da taxonomia

O inventário usa uma unidade por repositório e caminho, incluindo mudanças históricas
e a árvore congelada. A amostra é derivada do inventário completo e das regras de
cota e calibração. Os campos de revisão ficam vazios na origem.

| Campo | Significado |
|---|---|
| `unit_id`, `source_unit_id` | Identificador da unidade e vínculo da amostra com sua origem. |
| `repository_id`, `head_commit_sha`, `file_path` | Caso, limite do histórico e caminho normalizado. |
| `commit_sha`, `blob_revision`, `blob_sha` | Mudança representativa, revisão recuperável e identidade do conteúdo. |
| `category`, `taxonomy_version` | Predição do instrumento e versão usada. |
| `historical_observations` | Número de observações do caminho no universo inventariado. |
| `calibration_used` | Indica uso prévio da unidade na calibração. |
| `expected_category` | Categoria atribuída pelo pesquisador. |
| `reviewer`, `reviewed_at_utc` | Responsável pela revisão e instante UTC (ISO 8601 com `+00:00`). |
| `justification`, `role_change_review` | Justificativa e conferência de mudanças históricas de papel. |

`taxonomy_validation.json` registra hashes da amostra original, cópia revisada e
inventário, cobertura, concordância, matriz de confusão e aceite. O arquivo original
é conferido contra a amostra recalculada; campos imutáveis não podem ser editados.
A definição das cotas está no [método](DECISOES_METODOLOGICAS.md#validação-da-taxonomia).

`docs/evidencias/taxonomia_calibracao_1_2_0.csv` lista as 180 unidades revisadas na
validação da 1.1.0 que calibraram a 1.2.0: `unit_id`, `repository_id`, `file_path`,
`blob_sha`, `category_1_1_0` e `expected_category`. As mesmas identidades constam em
`calibration_units`, e um teste confere que a taxonomia vigente reproduz esses rótulos.

## Índice e arquivos de revisão

`study_index.json` relaciona exatamente os casos e SHAs da seleção às execuções de
congelamento, mineração e métricas. Cada referência contém o `run_id` e o hash do
manifesto. O índice também registra versão do plano, taxonomia e hashes do inventário
e da amostra. Uma origem incompatível interrompe a leitura, sem recorrer a `latest`.

`case_review_template.json` contém as medições e o contexto dos casos. A revisão
preenche `decision`, `decision_reason`, `reviewer` e `reviewed_at_utc`, mantendo
medidas e fontes conferíveis. `academic_review_template.json` registra `status`,
responsável, data, `evidence`, `operational_objective`, `unanswered_questions`,
`mlflow_scope_resolved` e `metric_mapping_resolved`.

`pr_map_template.json` contém todos os commits elegíveis, agrupados por repositório.
Cada linha tem `commit_sha`, `status`, `pr_url`, `source_url`, `reviewer` e
`checked_at_utc`. Os estados são `found`, `pr_not_found`, `not_collected` e `error`.
Uma coleta automática acrescenta método, arquivo de evidência e hash da resposta;
seu responsável é identificado como coleta técnica, sem atribuir revisão humana.

## Análise e finalização

O relatório produz `metricas_consolidadas.csv`, `serie_mensal.csv`,
`distribuicao_configuracao.csv`, `sensibilidade_configuracao.csv`,
`caracterizacao_casos.csv`, `funil_commits.csv` e `cobertura_evidencias.csv`.
As tabelas preservam caso, unidade, estado e denominadores pertinentes.

`eventos_candidatos.csv` guarda o universo documental e `eventos_selecionados.csv`
registra grupo, posição, motivo, SHAs, status e fonte PR. A cobertura informa cotas,
sobreposições, déficits e completude do mapa. A tabela de codificação acrescenta
`themes`, `evidence`, `interpretation`, `justification`, `ambiguity`, `metric_id`,
`quantitative_pattern`, `contrary_evidence`, `conclusion_limit`, `reviewer` e
`reviewed_at_utc`. Esses campos dependem de leitura e julgamento do pesquisador.

`study_acceptance.json` reúne `scientific_result_accepted`, `blocking_reasons` e os
estados de processamento, amostra, validação, alinhamento e análise qualitativa.
A finalização aceita gera nova tabela validada, integração dos resultados,
rascunho de redação e pacote de reprodução com hashes. A condição científica da
cadeia é distinta do sucesso de cada processamento.

Caminhos novos são relativos à raiz do projeto. Na leitura de artefatos legados,
somente caminhos absolutos com o sufixo `/data/` são remapeados; saídas fora da raiz
são rejeitadas. A auditoria da coleta recupera os instrumentos históricos no commit
original. Alterar protocolo, configuração, taxonomia ou contrato exige verificar a
compatibilidade antes de reutilizar uma fonte.
