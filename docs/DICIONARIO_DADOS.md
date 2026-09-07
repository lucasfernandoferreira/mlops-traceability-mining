# Dicionário de dados

## Escopo e convenções

Este dicionário descreve a configuração, a taxonomia, os manifestos e as saídas
implementadas das Fases 1 a 5. Mineração e métricas foram executadas no piloto
preliminar Ultralytics. Execuções locais são identificadas pelos ponteiros em
`data/interim/latest/`; a presença do código ou a aprovação do CI não comprovam,
por si sós, uma coleta empírica.

Convenções globais:

- datas e horários: ISO 8601 em UTC;
- repositório: `owner/name`, preservando a grafia retornada pela origem;
- commit: SHA Git integral de 40 caracteres;
- caminho: relativo à raiz do repositório, normalizado com `/`;
- proporção: número entre 0 e 1, sem conversão implícita para percentual;
- campo anulável: `null` somente quando acompanhado de um estado ou motivo explícito.

Nos CSVs, valores ausentes são campos vazios; booleanos são `true`/`false`, e
`decision_reasons` usa o separador literal ` | `. No JSON, são usados `null`,
booleanos e listas nativos. Cada execução grava saídas em
`data/interim/runs/<run_id>/`, preservando as execuções anteriores.

## Configuração executável — implementada

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
| `reproducibility.require_clean_worktree` | booleano | Exige estado Git limpo em execução oficial. |
| `reproducibility.save_manifests` | booleano | Determina a persistência de manifestos. |
| `reproducibility.hash_algorithm` | enum | Algoritmo dos artefatos; atualmente apenas `sha256`. |

## Classificação de arquivos — implementada

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

## Manifesto de execução — implementado

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

## Busca da Fase 1 — implementada

Fonte: `scripts/01_search_candidates.py` e `src/mlops_traceability/github_search.py`.

### `resumo_execucao_fase1.json`

Relatório pequeno de execução gerado ao final da Fase 1.

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

## Triagem da Fase 2 — implementada

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
| `status` | enum | `SUCCESS` somente se todos os gates passarem; caso contrário `FAILED`. |
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

Os gates são `worktree_clean`, `input_run_ids_match`, `errors_absent`,
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

## Commits e mudanças — implementado no piloto

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

Não serão persistidos nome nem e-mail do autor nas tabelas publicáveis.

## Resultado de métrica — implementado no piloto

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

## Amostra final — estado versionado

Fonte: `config/amostra_final.yaml`.

| Campo | Tipo | Anulável | Significado |
|---|---|---:|---|
| `schema_version` | string | não | Versão deste contrato. |
| `protocol_id` | string | não | Protocolo que governa a seleção. |
| `protocol_version` | string | não | Versão do protocolo. |
| `status` | enum | não | `pending`, `pilot` ou `final`. |
| `selected_at_utc` | datetime | sim | Data da decisão final. |
| `selection_commit_sha` | string | sim | Commit que congelou a seleção. |
| `selection_config_sha256` | string | sim | Hash da configuração aplicada. |
| `repositories` | lista de objetos | não | Casos selecionados; preenchida para `pilot`/`final`. |
| `pending_reason` | string | sim | Motivo enquanto a amostra não estiver finalizada. |

Quando `status=final`, cada item de `repositories` deverá conter ao menos
`repository_id`, `repository_url`, `head_commit_sha`, `stratum` e
`selection_rationale`.


## Extensões das Fases 3–5 (2.0.0)

- `amostra_congelada.csv`: um caso por run, com URL, SHA, clone_path, estrato,
  reachable_commits, shallow=false, clone_bytes e run_id. Clone bare completo.
- `commits.parquet`: todas as revisões, incluídas/excluídas; acrescenta parent_sha,
  large_commit, C/D/P, config_changed_keys e config_semantic_status. D é apenas o
  indicador técnico DATA_META, não a dimensão científica D validada.
- `changes.parquet`: somente arquivos de commits incluídos; acrescenta parent_sha,
  change_type, semantic_status/detail, changed_keys (lista) e changed_key_count.
  Chaves são caminhos JSON com tipos, contadas por arquivo/commit. Semântica de
  arquivos fora de CONFIG é not_applicable, com contagem nula.
- `mining_summary.json`: funil exclusivo, intervalo do universo, contagem de
  contribuidores ativos sem identidades, gate suplementar e erros semânticos.
- `tree_inspection.json`: arquivos e blobs do SHA, chamadas AST com linhas, URLs,
  SHA-256 do conteúdo, categoria, erros de parser e caminhos mlruns aninhados.
- `amostra_validacao_taxonomia.csv`: até 20 caminhos por categoria no SHA, ordenados
  por SHA-256 de caminho:blob; expected_category, reviewer e reviewed_at_utc vazios.
- `metric_membership.csv`: uma linha por membro de denominador longitudinal,
  metric_id, commit_sha, in_numerator e numerator_contribution. A soma reproduz o
  numerador; quantidade de linhas reproduz o denominador.
- `metrics.csv`: contrato GQM, mais head_commit_sha, unit e validation_status.
- `execution.json`: run, upstream, status técnico, erro e indicador preliminar.
- `source_snapshot.tar.gz`: bytes do instrumento executado; não contém credenciais
  nem clones de terceiros. Hash e byte_count registrados no manifesto.

Manifesto 1.2.0 mantém compatibilidade com versões antigas: `line_count` é anulável
para binários e `byte_count` registra tamanho. Nenhum manifesto anterior é reescrito.
Ponteiros admitem `phase3_clone_repos`, `phase4_mine_commits`, `phase5_compute_metrics`.
Resultados unavailable têm células vazias para valor/numerador/denominador.
Amostra pilot registra source_runs, source_shortlist_sha256, responsabilidades,
status de alinhamento acadêmico e de validação humana, além das evidências por caso.
`selection_commit_sha` é o commit-base no instante da decisão; em desenvolvimento os
bytes completos da seleção estão no snapshot. Não significa que o YAML já foi commitado.

## Contratos adicionais — 2.1.0

`evidence_type`: direct = registro público da prática; structural = vínculo nos
artefatos; proxy = sinal indireto/candidato sintático. Não somar tipos em escore.
`availability_reason`: not_found_in_inspected_scope, source_inaccessible,
not_collected, parser_not_implemented, dimension_not_validated; vazio quando não
aplicável. Status numéricos preservados. Falta de coleta/parser não é busca negativa.
Escopo registra SHA, universo, método e limites. Não foi encontrada evidência pública
suficiente nas fontes inspecionadas é formulação válida somente para busca realizada.

Inventário: unit_id, repository_id, head_commit_sha, file_path normalizado, commit_sha,
blob_revision, blob_sha, category, taxonomy_version, calibration_used. Unidade única
por repositório/caminho; deletion recupera revisão pai. Amostras acrescentam
expected_category, reviewer, reviewed_at_utc, justification e source_unit_id.
Recibo: hashes origem/revisão/inventário, cobertura, concordância/matriz e aceite.

Índice do estudo referencia manifesto e SHA-256 de cada run e caso; caminhos novos
relativos à raiz do projeto. Leitura legada remapeia somente sufixo /data/ para a
raiz local, ou configurações conhecidas; rejeita escape. Fontes explícitas inválidas
não caem para latest. Compatibilidade requer protocolo, configuração, taxonomia e
contrato de mineração iguais; SHA de código e snapshot preservados por etapa.

Saídas descritivas: métricas por caso e status; série mensal UTC com numerador e
denominador; distribuição CONFIG com quantis lineares; variantes de magnitude com
unidade idêntica ao principal. Seleção: universo completo, PR/fonte/status, grupos
possíveis, posição, motivo, cotas/déficits e revisão humana vazia.
