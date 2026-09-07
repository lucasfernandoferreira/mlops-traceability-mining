# Caso ultralytics/ultralytics — ficha técnica 2.1.0

SHA: `fa34184a5080c81fff453670394e13303ac781b2`. Estado: **pilot**. Preparação por Codex em 07/09/2026; decisão humana pendente.

Domínio: Visão computacional. Limite: repositório canônico e histórico alcançável no SHA.

Perguntas: C/P, magnitude CONFIG e instrumentação de parâmetros/métricas/artefatos. Contraste proposto: Integração por callbacks do treinamento.

| Campo | Evidência |
|---|---|
| reachable_commit_count | 4974 |
| active_after | 2025-09-01T00:00:00+00:00 |
| active_identity_count | 175 |
| stars_at_collection | 61103 |
| collection_timestamp | 2026-08-31T03:07:44.308341Z |
| integration_entrypoint | ultralytics/engine/trainer.py |
| integration_component | ultralytics/utils/callbacks/mlflow.py |
| operation | log_params; log_metrics; log_artifact |
| enablement | add_integration_callbacks registra callbacks; SETTINGS.mlflow verdadeiro, pacote disponível e guards de execução/teste. |
| integration_evidence_status | functional_integration_observed |
| evidence_type | structural |
| evidence_scope | BaseTrainer registra os callbacks e dispara eventos; callback envia trainer.args, métricas e pesos. Não comprova execução pública. |

[Componente no SHA](https://github.com/ultralytics/ultralytics/blob/fa34184a5080c81fff453670394e13303ac781b2/ultralytics/utils/callbacks/mlflow.py).
[Entrada no SHA](https://github.com/ultralytics/ultralytics/blob/fa34184a5080c81fff453670394e13303ac781b2/ultralytics/engine/trainer.py).
[Teste associado](https://github.com/ultralytics/ultralytics/blob/fa34184a5080c81fff453670394e13303ac781b2/tests/test_integrations.py).

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
| freeze | `20260907T220836923485Z_11e480b5_phase3_clone_repos` |
| mine | `20260907T220849687387Z_11e480b5_phase4_mine_commits` |
| metrics | `20260907T221449301437Z_11e480b5_phase5_compute_metrics` |

Decisão de seleção: pendente. Fonte de aprovação específica MLflow/métricas: pendente.
Critérios e reservas: DEFINICAO_DOS_CASOS.md e INSPECAO_MANUAL_AMOSTRA.md.
