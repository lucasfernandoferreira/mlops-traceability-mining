# DM-026 A e fechamento da taxonomia

A variante A foi escolhida expressamente pelo pesquisador em 11/09/2026 na
conversa de implementação. A decisão é posterior à inspeção do Anomalib, fica
registrada como clarificação retrospectiva e vale também para futuras avaliações
das reservas. Não constitui aprovação acadêmica nem preenchimento das revisões.
Protocolo de execução 2.1.0, taxonomia 1.1.0, filtros, fórmulas, locks e plano de
análise 1.0.0 permanecem iguais.

## Fontes e correção da ficha

O [registro das fontes](evidencias/dm026_fontes.json) reúne revisão, URLs, instantes
de consulta, hashes, linhas e **14 testemunhos resolvidos**. Nove arquivos externos,
incluindo a licença, estão em
`data/interim/documentation/dm026_lightning_2.6.5_be98784a/`.
A tag 2.6.5 foi resolvida para o commit
`be98784a1a03581b7051a355ae1084fd352d7cea`; os downloads usam esse SHA completo.
O lockfile do Anomalib identifica Lightning 2.6.5 e MLflow 3.15.1.

A cadeia principal liga Engine, Trainer, modelos LightningModule e logger MLflow.
O Engine repassa o logger ao Trainer; o AnomalibModule salva hiperparâmetros;
Cflow fornece um exemplo de `self.log` com `logger=True`. O framework encaminha
os valores ao logger, que usa o cliente MLflow. A conclusão é estrutural e
condicionada à configuração do logger, ao modelo e ao fluxo do Trainer. O envio
inicial dos hiperparâmetros também depende de `enable_autolog_hparams`.

As fontes principais são o
[logger MLflow](https://github.com/Lightning-AI/pytorch-lightning/blob/be98784a1a03581b7051a355ae1084fd352d7cea/src/lightning/pytorch/loggers/mlflow.py),
o [envio de hiperparâmetros](https://github.com/Lightning-AI/pytorch-lightning/blob/be98784a1a03581b7051a355ae1084fd352d7cea/src/lightning/pytorch/loggers/utilities.py)
e o [conector de métricas](https://github.com/Lightning-AI/pytorch-lightning/blob/be98784a1a03581b7051a355ae1084fd352d7cea/src/lightning/pytorch/trainer/connectors/logger_connector/logger_connector.py).
Nenhum treinamento, servidor MLflow ou código dessas dependências foi executado.

O Engine removeu o registro de `_VisualizationCallback` na v2.0.0. Por isso,
`callbacks/visualizer.py` saiu dos caminhos de integração do Anomalib. `add_image`
permanece disponível para chamada explícita, mas não sustenta a ligação automática
antiga. A ficha descreve agora injeção de logger e operações herdadas. Casos e
SHAs foram mantidos; o ponteiro de maturidade do PyMC passou a usar o run corrigido.

**Esclarecimento V1:** o Trainer anexa callbacks do modelo e atribui dinamicamente
`lightning_module.log` e `log_dict` a esses callbacks. O Anomalib oferece o
Evaluator quando ele é um Callback configurado. Isso explica estruturalmente a
disponibilidade desses métodos; não certifica sua execução ou correção. A cadeia
principal registrada usa os modelos, independentemente desse esclarecimento.

## Impacto medido

A [prévia de impacto](evidencias/dm026_impacto.json) usou fontes conferidas e a
especificação [runs_dm026.json](evidencias/runs_dm026.json). Seus arquivos estão em
`data/interim/verification/incremento_06/`. É uma prévia com alterações locais,
não um run científico registrado ou um recibo de aceite.

- Inventário, amostra taxonômica de 180 unidades e template do mapa de PRs:
  **idênticos byte a byte** aos do índice corrigido de 09/09.
- Mineração e métricas: reutilizadas, sem reextração ou mudança de fórmula.
- Candidatos Q1 do Anomalib: **46 para 44 eventos**, após agrupamento por PR.
- As identidades dos **45 selecionados permanecem iguais**. Ultralytics e PyMC
  têm linhas idênticas. No Anomalib, `group_position` muda de 30 para 29 no PR
  #2498 e de 45 para 43 no PR #3560.

Novo índice, fichas, seleção e relatório devem ser registrados após commit, com
worktree limpo. Identidades iguais permitem avaliar reaproveitamento de codificação;
interpretações ligadas à ficha incorreta exigem revisão mesmo no mesmo evento.

## Pasta de trabalho da taxonomia

`data/interim/reviews/fechamento_taxonomia_dm026_20260911/`

| Arquivo | Uso |
|---|---|
| `taxonomia_revisada.csv` | Cópia para preencher as 180 avaliações. |
| `fontes_taxonomia.html` | Guia com prévia, blob integral e links históricos; não salva avaliações. |
| `origem_taxonomia.json` | Índice, hashes e identidade dos 180 blobs preservados. |
| `blobs/` | Conteúdos exatos obtidos dos clones congelados. |

O [diagnóstico da preparação](evidencias/taxonomia_dm026_preparacao.json) registra
**zero avaliações completas, concordância indefinida e aceite falso** no instante
da cópia. Foram conferidos identidade Git, tipo, conteúdo, revisão/caminho e
ancestralidade dos 180 blobs. Essa conferência não atribui classe esperada e não
substitui a fase 6. A origem permanece na pasta `reprocessamento_20260909T144632500174Z_af5a0048_study_index`.

Preencha `expected_category`, `reviewer`, `reviewed_at_utc` (data real com offset
UTC), `justification` e `role_change_review` quando houver múltiplas observações
históricas. Classes: TEST, CI, ENV, DATA_META, CONFIG, NOTEBOOK, CODE, DOC, DATA_RAW,
OUTRO. Os demais campos identificam as fontes e devem permanecer íntegros.
Se as avaliações já existem em outro arquivo, preservar seus julgamentos, autoria
e correspondência das unidades, sem repetir a revisão.

A prévia HTML mostra até 150 linhas; o blob integral é preservado. A classificação
automática aparece recolhida e não constitui julgamento humano. Avaliar conteúdo,
contexto e versões históricas relevantes. Os exemplos de ambiguidade recebidos
com auxílio de IA não constituem outro codificador ou rótulos independentes.

O limiar continua 95%. Uma reprovação exige diagnosticar as divergências. Eventual
alteração da taxonomia exige versionamento, recálculo e separação entre calibração
e avaliação. DATA_META ausente não recebe concordância artificial.

## Verificação da implementação

O [log da verificação](evidencias/validacao_dm026.txt) registra sucesso de
`make lint format-check typecheck test smoke-dev`: **258 testes passaram**, com
**94,28% de cobertura**. Também foram reconferidos os hashes das nove fontes
externas, sete fontes do Anomalib e 14 testemunhos. O smoke usou `--allow-dirty`;
esse resultado de desenvolvimento não constitui aceite científico.

## Comandos após commit

```sh
make check
make study-index RUNS_FILE=docs/evidencias/runs_dm026.json
```

O segundo comando imprime o diretório do índice. Substitua `NOVO_RUN_ID` abaixo
pelo identificador efetivamente gerado:

```sh
STUDY_INDEX=data/interim/runs/NOVO_RUN_ID/study_index.json
make qualitative STUDY_INDEX="$STUDY_INDEX" \
  PR_MAP=data/interim/pr_maps/trio_20260908T003438Z/mapa_prs.json
make report STUDY_INDEX="$STUDY_INDEX"
make validate-taxonomy STUDY_INDEX="$STUDY_INDEX" \
  INVENTORY="${STUDY_INDEX%/*}/taxonomy_inventory.json" \
  SAMPLE=data/interim/reviews/fechamento_taxonomia_dm026_20260911/taxonomia_revisada.csv
```

A fase 6 confere as identidades contra a amostra e o inventário fornecidos.
Campos incompletos ou concordância insuficiente produzem recusa registrada.
Reutilizar PRs depende da igualdade do universo e dos hashes do template/mapa.

A pasta de trabalho é específica da taxonomia, não um pacote completo para
`import-reviews`. Depois, preparar revisões a partir dos templates e runs novos,
incorporar as decisões de caso, alinhamento e codificação, e verificar novamente.
Os recibos anteriores não são aprovações transferíveis. Os critérios G02/G11/G12
e os demais controles obrigatórios permanecem separados desta preparação.
