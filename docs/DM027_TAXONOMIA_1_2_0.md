# DM-027: validação da taxonomia 1.1.0 e versão 1.2.0

A revisão humana das 180 unidades da taxonomia 1.1.0 foi recebida em 11/09/2026.
Na mesma data, na conversa de implementação, o pesquisador solicitou a consolidação
da revisão e a versão 1.2.0. Este dossiê registra o que foi recebido, o resultado da
1.1.0, o diagnóstico das divergências, as regras novas e o impacto medido em prévia.
Nenhuma alteração foi commitada; a decisão não constitui aprovação acadêmica.
Protocolo 2.1.0, fórmulas, filtros, limiar de 95%, cotas e plano de análise 1.0.0
permanecem iguais.

## Revisão recebida e consolidação

As avaliações foram coladas no CSV da pasta de origem
`reprocessamento_20260909T144632500174Z_af5a0048_study_index/`, não na pasta de trabalho.
O arquivo foi salvo em 11/09/2026 às 13:45:27 (UTC−03:00), com SHA-256
`754151228167445d45e4b42568fd9c25a128fc85b46ad17bc00136919a476692`. Ele foi preservado
byte a byte em `fechamento_taxonomia_dm026_20260911/recebido/`, e a origem voltou ao
conteúdo em branco registrado em 11/09 (`ec4823b4…`).

A consolidação manteve os 12 campos de identidade, `expected_category`, `reviewer`
e o texto das justificativas. Foram corrigidos dois defeitos de formato: o cabeçalho
perdera o nome `role_change_review`, e 37 justificativas com vírgula estavam divididas
em várias colunas, 14 delas além da última. Os fragmentos foram unidos sem perda.
O resultado está em `fechamento_taxonomia_dm026_20260911/taxonomia_revisada.csv`.

`reviewed_at_utc` continha apenas datas (`20260909`) e 18 linhas vazias. O pesquisador
declarou que não salvou os horários e que as sessões ocorreram entre 12h e 13h e
entre 19h e 21h (UTC−03:00) em todos os dias. Os instantes foram reconstruídos nessas
janelas, distribuídos na ordem do arquivo, com precisão de minuto:

| Dia | Linhas | Janelas usadas | Base da data |
|---|---:|---|---|
| 09/09 | 81 | 12h–13h e 19h–21h | registrada |
| 10/09 | 80 | 12h–13h e 19h–21h | registrada |
| 11/09 | 19 | somente 12h–13h | 1 registrada, 18 inferidas |

Em 11/09, a janela noturna ainda não havia ocorrido quando o arquivo foi salvo.
As 18 datas ausentes sucedem, na ordem monotônica do arquivo, a última linha de 11/09.
Os valores indicam a sessão provável, não o instante de cada julgamento; a
[consolidação](evidencias/taxonomia_1_1_0_consolidacao.json) registra cada linha.

`role_change_review` está vazio nas 180 unidades, e todas têm mais de uma observação
histórica. Esse julgamento não foi preenchido nem inferido. Para apoiá-lo,
`historico_papeis.html` compara as versões de cada caminho com o blob avaliado.
Das 180 unidades, 61 têm um único blob, 116 têm similaridade mínima de linhas de 0,7
ou mais, e 26 ficam abaixo de 0,3. A similaridade não mede papel e não sugere resposta.

Das 180 justificativas, 162 repetem um de dez textos por categoria, como
"classificação CI é direta". Todas as concordâncias, exceto duas, usam esses textos;
todas as divergências têm texto específico. O validador aceita o formato, mas
justificativas ligadas ao conteúdo de cada arquivo reduzem a leitura de ancoragem
na predição automática.

## Resultado da taxonomia 1.1.0

O índice DM-026 foi registrado com worktree limpo no commit `f6fa825`. Inventário,
amostra e template de PRs ficaram idênticos aos de 09/09; seleção, candidatos e
codificação repetiram a prévia DM-026. A fase 6
(`20260911T193603470335Z_f6fa8256_phase6_validate_taxonomy`) confirmou a integridade
da amostra e recusou o aceite por revisão incompleta e concordância insuficiente.

Sobre as 180 classificações, a concordância foi de **164/180 (91,1%)**, abaixo de 95%.
O [diagnóstico](evidencias/taxonomia_1_1_0_diagnostico.json) traz matriz, casos e regras.

| Categoria | Concordância | | Caso | Concordância |
|---|---:|---|---|---:|
| CI, CONFIG, ENV, NOTEBOOK, TEST | 20/20 cada | | pymc-labs/pymc-marketing | 68/70 |
| CODE, DOC | 19/20 | | ultralytics/ultralytics | 45/51 |
| DATA_RAW | 17/20 | | open-edge-platform/anomalib | 51/59 |
| OUTRO | 9/20 | | | |

DATA_META não existe no universo inventariado e não recebe concordância.
A reprovação permanece como resultado da 1.1.0.

## Diagnóstico das divergências

As 16 divergências seguem seis mecanismos das regras:

| Mecanismo | Unidades | 1.1.0 → revisor |
|---|---|---|
| M1. Extensões de código ausentes | `yolo_show.hpp`, `custom_components.sh`, dois `.tsx` | OUTRO → CODE |
| M2. Variantes de nome | `Dockerfile-nvidia-cuda`; `cubes_config.yaml` | OUTRO → ENV; OUTRO → CONFIG |
| M3. Manifestos e empacotamento | `package-lock.json`; `setup.py` da raiz | OUTRO → ENV; CODE → ENV |
| M4. Imagens de interface | três PNG em `ui/` e `icons/` | DATA_RAW → OUTRO |
| M5. Dados sob `docs/` | `multidimensional_model.nc` | DOC → DATA_RAW |
| M6. Configurações fora de `cfg/` | três YAML de modelo e `xView.yaml` no layout antigo | OUTRO → CONFIG |

OUTRO é a maior categoria do universo (2.669 caminhos). Além de 2.017 catálogos `.po`,
confirmados como OUTRO, abrigava código TypeScript, Shell, C++ e Rust, e cerca de
100 YAMLs de modelo e dataset do Ultralytics. O efeito, portanto, alcança as medidas.

## Regras da taxonomia 1.2.0

As mudanças se limitam aos mecanismos observados. O universo de caminhos, sem rótulos
humanos, serviu apenas para conferir efeitos colaterais, e cada regra tem um caso
de proteção em `tests/test_taxonomy.py`.

| Categoria | Mudança | Mecanismo | Proteção |
|---|---|---|---|
| ENV | `Dockerfile*`, `*.dockerfile`, `docker-compose*`, `environment*`/`conda*` | M2 | — |
| ENV | `setup.py`/`setup.cfg` somente na raiz; `package(-lock).json`, `yarn.lock`, `pnpm-lock.yaml`, `Cargo.toml/lock` | M3 | `core/logging/setup.py` continua CODE |
| CONFIG | prefixo com `_`/`-` antes de `config`/`params` | M2 | `.pre-commit-config.yaml` e `tsconfig.json` continuam OUTRO |
| CONFIG | YAML sob `models/`, `model/`, `datasets/`, `dataset/` | M6 | `.github/ISSUE_TEMPLATE/*.yml` continua OUTRO |
| CODE | `hpp`, `hh`, `hxx`, `cc`, `cxx`, `cu`, `rs`, `ts`, `tsx`, `js`, `jsx`, `mjs`, `cjs`, `sh`, `bash` | M1 | `.scss` e `.po` continuam OUTRO |
| DOC | `docs/` não captura formatos de dados | M5 | imagens em `docs/` continuam DOC |
| DATA_RAW | `.nc`; imagens em `ui/` e `icons/` saem da regra | M4, M5 | `ultralytics/assets/bus.jpg` continua DATA_RAW |

Código-fonte de interface segue a definição de CODE aplicada pelo revisor e passa a
compor a dimensão C. Precedências e categorias foram mantidas. Não foram criadas
regras sem evidência nas divergências: ações compostas em `.github/actions/`,
`.dockerignore`, `.svg` e `.scss` continuam em OUTRO e serão testados pela nova amostra.

A 1.2.0 reproduz os 180 rótulos humanos. Isso é calibração, não avaliação. No
inventário de 7.631 caminhos, 440 mudam de categoria: 284 de OUTRO para CODE, 104 para
CONFIG e 29 para ENV; 8 de DOC para CODE; 9 passam a DATA_RAW; 3 de CODE para ENV;
e 3 de DATA_RAW para OUTRO.

## Calibração e nova amostra de avaliação

As 180 unidades estão em [taxonomia_calibracao_1_2_0.csv](evidencias/taxonomia_calibracao_1_2_0.csv)
e em `calibration_units`. Um teste confere que a taxonomia vigente reproduz esses
rótulos. Todas as categorias têm ao menos 20 unidades nunca revisadas (DATA_RAW 22,
ENV 34); por isso, a regra de amostragem não mudou.

A nova amostra tem 180 unidades, 20 por categoria, sem sobreposição com a calibração.
Todas exigem `role_change_review`. A pasta de trabalho é
`data/interim/reviews/avaliacao_taxonomia_1_2_0_20260911/`:

| Arquivo | Uso |
|---|---|
| `taxonomia_revisada.csv` | Cópia em branco para preencher as 180 avaliações. |
| `fontes_taxonomia.html` | Prévia, blob integral e links; não salva avaliações. |
| `historico_papeis.html` | Versões históricas por caminho, para `role_change_review`. |
| `origem_taxonomia.json` | Índice, hashes e identidade dos blobs preservados. |
| `blobs/` | 178 conteúdos exatos (algumas unidades têm conteúdo idêntico). |

A amostra vem de uma prévia com alterações locais. Após o commit, o índice registrado
precisa gerar a mesma amostra (`5ccdb6a6…`), como na DM-026.

## Impacto medido em prévia

`verified_run` vincula `config.yaml` e `file_taxonomy.yaml` a cada run de origem.
A tentativa de reaproveitar os congelamentos falhou por esse vínculo e ficou
preservada; a cadeia foi refeita a partir da fase 3, com `ALLOW_DIRTY=1`.
Commits, elegibilidade e linhas de mudança ficaram idênticos nos três casos;
só a classificação mudou. O [registro de impacto](evidencias/dm027_impacto.json)
e as [execuções](evidencias/dm027_execucoes.json) trazem runs e hashes.

| Caso | Mudanças reclassificadas | Coalteração 1.1.0 → 1.2.0 | Magnitude CONFIG 1.1.0 → 1.2.0 |
|---|---:|---|---|
| ultralytics/ultralytics | 990 | 224/3.220 (6,96%) → 249/3.272 (7,61%) | 8.136/276 (29,48) → 20.723/299 (69,31) |
| pymc-labs/pymc-marketing | 45 | 14/876 (1,60%) → 14/879 (1,59%) | 469/16 (29,31) → igual |
| open-edge-platform/anomalib | 541 | 108/668 (16,17%) → 115/668 (17,22%) | 10.883/119 (91,45) → 11.254/128 (87,92) |

No Ultralytics, os YAMLs de arquitetura e dataset têm muitas chaves e mais que dobram
a magnitude média. Não houve erro semântico. O template de PRs ficou idêntico, e o
mapa de PRs pode ser reaproveitado. A seleção qualitativa mantém 37 dos 45 eventos:
cinco mudam no Ultralytics, três no Anomalib e nenhum no PyMC. Os eventos novos exigem
codificação, e as fichas dos casos precisam refletir as métricas novas.

## Pendências e próximos passos

1. **Revisão humana da nova amostra.** Preencher as 180 linhas da pasta de avaliação,
   registrando `reviewed_at_utc` no momento de cada avaliação.
2. **Recibo formal da 1.1.0 (recomendado).** Preencher `role_change_review` na pasta
   de fechamento. Como o índice é conferido contra o instrumento vigente, a fase 6
   dessa revisão precisa rodar com o código de `f6fa825`, depois do commit da DM-027
   e com worktree limpo (`data/interim/` é ignorado e permanece disponível):

   ```sh
   git switch --detach f6fa825
   STUDY_INDEX=data/interim/runs/20260911T193457396587Z_f6fa8256_study_index/study_index.json
   make validate-taxonomy STUDY_INDEX="$STUDY_INDEX" \
     INVENTORY="${STUDY_INDEX%/*}/taxonomy_inventory.json" \
     SAMPLE=data/interim/reviews/fechamento_taxonomia_dm026_20260911/taxonomia_revisada.csv
   git switch -
   ```

3. **Alinhamento acadêmico da DM-027**, incluindo CODE para código de interface.
4. **Cadeia registrada após o commit.** O script
   `data/interim/verification/incremento_07/registrar_cadeia_1_2_0.sh` exige worktree
   limpo, executa `make check` e as fases 3 a 8. Ele confere se a amostra é idêntica à
   prévia e copia a especificação para `docs/evidencias/runs_dm027.json`.
5. **Fase 6 da 1.2.0** com a amostra preenchida; reprovação exige novo diagnóstico.
6. **Revisões do novo índice**: fichas, alinhamento e codificação dos oito eventos novos,
   seguidas de verificação e finalização. Os recibos anteriores não são transferíveis.

## Verificação

O [log da verificação](evidencias/validacao_dm027.txt) registra `make lint format-check
typecheck test smoke-dev` sobre as alterações locais. Os scripts de consolidação,
diagnóstico, prévia e preparação estão em `data/interim/verification/incremento_07/`,
com seus logs. O smoke usa `--allow-dirty`; esse resultado não constitui aceite.
