# Índice temporal das evidências DM-027

O [estado final canônico](../ESTADO_FINAL_DM027.md) registra o aceite de 15/09/2026.
Este índice é uma camada documental posterior: não altera os bytes das evidências
de seleção, construção, julgamento ou fechamento.

## Entradas da entrega final

| Arquivo | Papel |
|---|---|
| [manifesto_final_dm027.json](manifesto_final_dm027.json) | Índice de casos, SHAs, runs, provas G00–G15 e hashes preexistentes. Caminhos relativos à raiz do repositório. |
| [recibo_final_dm027.json](recibo_final_dm027.json) | Cópia literal do recibo final local de 15/09, aceite verdadeiro e G15 PASS. SHA-256 `b188957b9acc84d933162594bd9ace260d3fe2eca6721b1892868cd0e4680d42`. |
| [confirmacao_pesquisador_dm027_extrato.json](confirmacao_pesquisador_dm027_extrato.json) | Extrato de campos da confirmação existente, com origem e hash do documento integral. Não é nova confirmação nem substitui a fonte. |
| [auditoria_estados_dm027.csv](auditoria_estados_dm027.csv) | Ocorrências da auditoria, com localização no baseline, classificação e tratamento. |
| [auditoria da consolidação](../AUDITORIA_CONSOLIDACAO_DM027.md) | Justificativas, arquivos alterados, verificações e pendências de entrega. |

O recibo original está em
`data/interim/fechamento_dm027/fechamento_confirmado_20260915T120020515444Z/recibo_final.json`.
O checksum acima já constava do `resumo_validacao.md` dessa execução e foi
conferido por leitura. Os hashes no manifesto foram transcritos das fontes
identificadas; não se atribuem hashes novos aos resultados científicos.

## Estados históricos e confirmação posterior

| Registro preservado | Temporalidade e interpretação após o fechamento |
|---|---|
| `config/amostra_final.yaml` | Snapshot da seleção de 05/09 e revisão técnica de 08/09. `pilot`, `pending` e `pending_reason` permanecem históricos; o arquivo é entrada vinculada por hash e não foi editado. |
| `rodada_atual.json`, `indice_entrega_parecer.json`, `validacao_atual.txt` | “Atual” e “entrega” referem-se à etapa registrada no arquivo; não são ponteiros para o aceite de 15/09. |
| `baseline_*`, `*_inicial.*`, `*_incremento_0*.*`, `dm026_*`, `runs_dm026.json` | Baselines, incrementos e rodada anterior. FAIL, NOT_RUN e aceite falso são resultados legítimos dessas etapas. |
| `dm027_impacto.json`, `runs_dm027.json`, `rodada_referencia_1_2_0.*` | Impacto/prévia e identidades das execuções. Identificar a cadeia técnica não equivale, isoladamente, ao aceite posterior. |
| `casos_dm027.json`, `alinhamento_academico_dm027.json`, `catalogo_afirmacoes_dm027.json`, `parecer_manuscrito_dm027.json` | Redações anteriores à confirmação, com `draft_pending_confirmation`. Cópias confirmadas posteriores estão no diretório indicado abaixo; não se promove o rascunho por edição. |
| `avaliacao_taxonomia_dm027.*`, `taxonomy_validation_dm027.json`, julgamentos e timestamps | Preservam avaliação, diagnóstico e proveniência. A fase 6 confirmada de 15/09, indexada no manifesto, registra o aceite de 173/180. Datas reconstruídas continuam identificadas como tal. |
| `log_fechamento_dm027.md` | Diário de construção. Passagens no futuro sobre confirmação descrevem o instante de redação; a confirmação efetiva ocorreu em 15/09. |
| `RELATORIO_FECHAMENTO_DM027.md` (raiz, local ignorado) | Relatório gerado em 14/09, antes da confirmação. Aceite falso e pacote de ensaio são históricos; não é o relatório corrente de aceite. |
| `study_acceptance.json` da fase 9 confirmada | Recibo intermediário que autoriza o candidato antes de G14/G15. Seu aceite falso não contradiz o recibo final posterior. |
| `verification_receipt.json` da execução confirmada | G00–G13 PASS; seu escopo não inclui sozinho o aceite final G00–G15. |

As cópias confirmadas estão em
`data/interim/fechamento_dm027/confirmadas_20260915T120008855301Z/`.
Elas conservam a autoria preliminar e registram `human_confirmed`, responsável e
instante real da confirmação. O catálogo confirmado tem SHA-256
`8093a959184b7b2d04541f474cda06f1c7f65c03c343a9ddf53d39f32417236a`,
vinculado a G15. O catálogo versionado de redação tem hash diferente,
`b5c489ab9de2ffab6e43e578811a6e29ed600156300cdc0fbbf6ba920c687112`;
não se apresenta esse rascunho como se fosse a cópia confirmada.

## Textos examinados e mantidos por integridade

O [manuscrito técnico](../MANUSCRITO_DM027.md), a
[síntese qualitativa](../SINTESE_QUALITATIVA_DM027.md), o
[parecer de alinhamento](../ALINHAMENTO_DM027.md) e o
[procedimento G14](../G14_RESTAURACAO_ISOLADA.md) foram revisados documentalmente
e mantidos byte a byte: seus hashes integram os vínculos do fechamento.
No manuscrito e no parecer, a identificação preliminar e o ato ainda futuro
correspondem à data de redação. O extrato e o recibo final registram o ato posterior.
O procedimento G14 continua sendo uma especificação; sua prova executada é o
relatório de restauração apontado no manifesto. Não é preciso repetir confirmação
ou restauração para atualizar a narrativa documental.

## Acesso para auditoria externa

`storage: git` identifica arquivos versionados nesta entrega; `local_ignored`
identifica arquivos existentes no acervo local, ausentes no checkout simples.
O extrato de confirmação permite ler autoria/data no Git, mas a conferência de
seu hash de origem requer o documento integral local.

A restauração requer o candidato e o acervo de `external_sources`/`source_hashes`
do relatório G14, incluindo o bundle do instrumento e os clones congelados.
O relatório contém caminhos absolutos do ambiente original; a recuperação usa
também os caminhos relativos inventariados. Não há depósito público integral
documentado. Organizar a entrega dessas fontes à orientadora é uma pendência de
distribuição, sem necessidade de nova observação do GitHub.
