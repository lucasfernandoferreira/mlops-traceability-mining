# Caso mosaicml/composer — ficha técnica 2.1.0

SHA: `6405188805a0054b4551ec49e4919c54c971d0e8`. Estado: **pilot**. Preparação por Codex em 07/09/2026; decisão humana pendente.

Domínio: Infraestrutura de treinamento. Limite: repositório canônico e histórico alcançável no SHA.

Perguntas: C/P, magnitude CONFIG e vínculos estruturados pelo logger. Contraste proposto: LoggerDestination e operações de modelos.

| Campo | Evidência |
|---|---|
| reachable_commit_count | 2701 |
| active_after | 2025-09-01T00:00:00+00:00 |
| active_identity_count | 2 |
| stars_at_collection | 5495 |
| collection_timestamp | 2026-08-31T03:07:44.308341Z |
| integration_entrypoint | composer/trainer/trainer.py |
| integration_component | composer/loggers/mlflow_logger.py |
| operation | log_params; log_metrics; register_model |
| enablement | Trainer instancia Logger com destinations=loggers; destino MLFlowLogger é condicionado por _enabled/rank e configuração. |
| integration_evidence_status | functional_integration_observed |
| evidence_type | structural |
| evidence_scope | Logger delega parâmetros/métricas; MLFlowLogger oferece registro de modelos. Disponibilidade da API não comprova promoção executada. |

[Componente no SHA](https://github.com/mosaicml/composer/blob/6405188805a0054b4551ec49e4919c54c971d0e8/composer/loggers/mlflow_logger.py).
[Entrada no SHA](https://github.com/mosaicml/composer/blob/6405188805a0054b4551ec49e4919c54c971d0e8/composer/trainer/trainer.py).
[Teste associado](https://github.com/mosaicml/composer/blob/6405188805a0054b4551ec49e4919c54c971d0e8/tests/loggers/test_mlflow_logger.py).

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
| freeze | `20260907T220840175940Z_11e480b5_phase3_clone_repos` |
| mine | `20260907T220852577444Z_11e480b5_phase4_mine_commits` |
| metrics | `20260907T221256960360Z_11e480b5_phase5_compute_metrics` |

Decisão de seleção: pendente. Fonte de aprovação específica MLflow/métricas: pendente.
Critérios e reservas: DEFINICAO_DOS_CASOS.md e INSPECAO_MANUAL_AMOSTRA.md.

## Pendência de elegibilidade observada em 07/09/2026

`active_contributors_gate=false`: 2 identidades ativas, mínimo 5. Sob as regras
vigentes, o caso não satisfaz a maturidade exigida. Sucesso dos parsers não supera
esse bloqueio; o caso permanece como proposta histórica/piloto, sem aceite final.

A primeira reserva previamente ordenada é `open-edge-platform/anomalib`, SHA
`0b7fdb9dde453f6474ac93f77188f4224d442999`. Sua avaliação e eventual substituição
precisam preservar esse SHA, registrar o motivo de elegibilidade e gerar novos
runs, inventário, revisão e índice. Não se reutiliza o recibo do universo contendo
Composer para certificar o universo substituto. A decisão humana permanece vazia.
