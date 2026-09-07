# Caso pymc-labs/pymc-marketing — ficha técnica 2.1.0

SHA: `fabba92c96aa6a4ec6d42fb3241a8ed725995d0a`. Estado: **pilot**. Preparação por Codex em 07/09/2026; decisão humana pendente.

Domínio: Modelagem probabilística de marketing. Limite: repositório canônico e histórico alcançável no SHA.

Perguntas: C/P, magnitude CONFIG e contexto do modelo/dados na instrumentação. Contraste proposto: Autologging de modelos, configuração, dados e inferência.

| Campo | Evidência |
|---|---|
| reachable_commit_count | 1506 |
| active_after | 2025-09-01T00:00:00+00:00 |
| active_identity_count | 40 |
| stars_at_collection | 1250 |
| collection_timestamp | 2026-08-31T03:07:44.308341Z |
| integration_entrypoint | pymc_marketing/model_builder.py |
| integration_component | pymc_marketing/mlflow.py |
| operation | log_params; log_input; log_inference_data |
| enablement | autolog envolve pm.sample; log_mmm habilita wrapper de MMM.fit, registrando configuração antes e inferência depois. |
| integration_evidence_status | functional_integration_observed |
| evidence_type | structural |
| evidence_scope | Wrappers conectados às operações de amostragem/fit. Testes documentam chamadas; exemplos não foram executados nesta coleta. |

[Componente no SHA](https://github.com/pymc-labs/pymc-marketing/blob/fabba92c96aa6a4ec6d42fb3241a8ed725995d0a/pymc_marketing/mlflow.py).
[Entrada no SHA](https://github.com/pymc-labs/pymc-marketing/blob/fabba92c96aa6a4ec6d42fb3241a8ed725995d0a/pymc_marketing/model_builder.py).
[Teste associado](https://github.com/pymc-labs/pymc-marketing/blob/fabba92c96aa6a4ec6d42fb3241a8ed725995d0a/tests/test_mlflow.py).

A leitura Git nos SHAs fixados confirmou os arquivos e as ligações descritas.
Testes são evidência de implementação; não foram executados. Nenhum registro de
execução pública ou promoção foi coletado (`availability_reason=not_collected` para runtime).
A classificação estrutural é preparação técnica, não rótulo humano nem seleção final.

Identidades ativas usam email normalizado/nome fallback, sem publicar identidades.
Aliases não foram resolvidos em pessoas únicas; checagem humana pode alterar a decisão.

Ficha tabular imutável: `data/interim/runs/20260907T221633592494Z_11e480b5_study_index/case_review_template.json`.
Campos decision, decision_reason, reviewer e reviewed_at_utc permanecem vazios.

| Etapa | Run ID |
|---|---|
| freeze | `20260907T220836936866Z_11e480b5_phase3_clone_repos` |
| mine | `20260907T220849191554Z_11e480b5_phase4_mine_commits` |
| metrics | `20260907T221243225142Z_11e480b5_phase5_compute_metrics` |

Decisão de seleção: pendente. Fonte de aprovação específica MLflow/métricas: pendente.
Critérios e reservas: DEFINICAO_DOS_CASOS.md e INSPECAO_MANUAL_AMOSTRA.md.
