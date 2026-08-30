# Dicionário de dados

## Escopo e convenções

Este dicionário separa artefatos já implementados de contratos planejados para as fases
de coleta e mineração. Na Fase 0, apenas a configuração, a taxonomia e o manifesto têm
modelos executáveis. As tabelas analíticas abaixo definem a interface esperada e não
atestam que dados reais já tenham sido coletados.

Convenções globais:

- datas e horários: ISO 8601 em UTC;
- repositório: `owner/name`, preservando a grafia retornada pela origem;
- commit: SHA Git integral de 40 caracteres;
- caminho: relativo à raiz do repositório, normalizado com `/`;
- proporção: número entre 0 e 1, sem conversão implícita para percentual;
- campo anulável: `null` somente quando acompanhado de um estado ou motivo explícito.

## Configuração executável — implementada

Fonte: `config/config.yaml`. O carregador rejeita campos desconhecidos ou ausentes.

| Grupo/campo | Tipo | Significado |
|---|---|---|
| `protocol.id` | string | Identificador estável do protocolo. |
| `protocol.version` | string | Versão do contrato metodológico. |
| `paths.*` | path | Diretórios de entrada, derivados, manifestos e relatórios. |
| `github.token_environment_variable` | string | Nome da variável que contém o token; nunca o token. |
| `github.per_page` | inteiro > 0 | Tamanho da página usado na busca paginada. |
| `github.max_results_per_query` | inteiro > 0 | Limite coletável por consulta antes de truncar. |
| `github.request_timeout_seconds` | inteiro > 0 | Timeout de requisição do adaptador GitHub. |
| `github.rate_limit.code_search_reserve` | inteiro >= 0 | Reserva mínima antes de pausar chamadas de Code Search. |
| `github.rate_limit.reset_buffer_seconds` | inteiro >= 0 | Folga aplicada após o reset declarado pela API. |
| `github.queries[].id` | string | Identificador estável de cada consulta. |
| `github.queries[].expression` | string | Expressão Code Search executada. |
| `selection.min_candidates` | inteiro > 0 | Quantidade mínima de candidatos brutos. |
| `selection.min_commits` | inteiro > 0 | Mínimo de commits para elegibilidade. |
| `selection.min_contributors` | inteiro > 0 | Mínimo de contribuidores para elegibilidade. |
| `selection.min_stars` | inteiro >= 0 | Mínimo de estrelas para elegibilidade. |
| `selection.active_after` | datetime UTC | Corte de atividade para commit humano. |
| `selection.min_shortlist` | inteiro > 0 | Quantidade mínima antes da inspeção manual. |
| `selection.final_sample_min/max` | inteiro > 0 | Intervalo permitido para a amostra final. |
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

## Candidatos e funil — contrato planejado

Uma linha por repositório avaliado em cada execução de seleção.

| Campo | Tipo | Anulável | Significado |
|---|---|---:|---|
| `repository_id` | string | não | Identificador público `owner/name`. |
| `repository_url` | string | não | URL canônica observada. |
| `observed_at_utc` | datetime | não | Instante da consulta. |
| `query_ids` | lista de strings | não | Consultas que encontraram o candidato. |
| `default_branch` | string | sim | Branch padrão informada pela origem. |
| `head_commit_sha` | string | sim | Revisão observada durante a seleção. |
| `stars_count` | inteiro >= 0 | sim | Estrelas na data de observação. |
| `commit_count` | inteiro >= 0 | sim | Commits segundo o método registrado. |
| `contributor_count` | inteiro >= 0 | sim | Contagem agregada de contribuidores. |
| `last_human_commit_at_utc` | datetime | sim | Última atividade não automatizada. |
| `detected_tools` | lista de enum | não | Evidência confirmada de `dvc` e/ou `mlflow`. |
| `stratum` | enum | sim | `apenas_dvc`, `apenas_mlflow` ou `dvc_e_mlflow`. |
| `decision` | enum | não | `eligible`, `rejected`, `shortlisted` ou `selected`. |
| `decision_reasons` | lista de strings | não | Critérios aplicados, inclusive rejeições. |
| `run_id` | string | não | Manifesto da execução que produziu a linha. |

Valores não observados por falha ou limite da API devem permanecer `null` com motivo;
não tornam o candidato inelegível silenciosamente.

## Commits e mudanças — contrato planejado

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
| `change_type` | enum | não | `added`, `modified`, `deleted` ou `renamed`. |
| `category` | enum | não | Categoria atribuída pela taxonomia vigente. |
| `run_id` | string | não | Manifesto da mineração. |

Não serão persistidos nome nem e-mail do autor nas tabelas publicáveis.

## Resultado de métrica — contrato planejado

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
| `status` | enum | não | `pending` ou `final`. |
| `selected_at_utc` | datetime | sim | Data da decisão final. |
| `selection_commit_sha` | string | sim | Commit que congelou a seleção. |
| `selection_config_sha256` | string | sim | Hash da configuração aplicada. |
| `repositories` | lista de objetos | não | Casos selecionados; vazia enquanto `pending`. |
| `pending_reason` | string | sim | Motivo enquanto a amostra não estiver finalizada. |

Quando `status=final`, cada item de `repositories` deverá conter ao menos
`repository_id`, `repository_url`, `head_commit_sha`, `stratum` e
`selection_rationale`.
