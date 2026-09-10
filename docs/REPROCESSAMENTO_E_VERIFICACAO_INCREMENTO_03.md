# Reprocessamento e verificação — incremento 3

A etapa seguinte está concluída no
[incremento 4](VERIFICACAO_QUALITATIVA_INCREMENTO_04.md): G10 foi implementado e
aprovado na conferência empírica. Este documento preserva o reprocessamento e o
estado dos critérios no incremento 3.

A rodada foi executada em 09/09/2026 na branch
`feat/reprocessamento-pymc-e-evidencias`, após o merge `af5a00489166bf262e0cc8c8f3c2ad5bc6842e19`.
Mineração, métricas, índice, seleção, relatório e verificador registraram worktree
limpo. Protocolo 2.1.0, taxonomia 1.1.0, política de verificação 1.1.0 e locks foram
preservados. Não houve mudança adicional no código produtivo neste incremento.

## Resultado

A divergência encontrada no [incremento 2](VERIFICACAO_EMPIRICA_INCREMENTO_02.md)
foi resolvida nos novos dados. O oráculo independente não encontrou diferenças de
histórico, maturidade, métricas, inventário ou estatísticas nos três casos.
**G05, G08 e G09 passaram de FAIL para PASS.**

O agregado continua **FAIL, saída 1, sem erros de processamento**. Os registros
humanos locais ainda têm 0/180 rótulos de taxonomia, 0/45 interpretações e 0/3
decisões de caso preenchidos. Isso descreve os arquivos encontrados; não contradiz
a revisão concluída informada pelo pesquisador. A atualização técnica das fontes
não atribui aprovação, autoria de revisão ou datas por inferência.

O [resumo da verificação](evidencias/verificacao_empirica_incremento_03.json)
vincula o recibo integral, provas, fontes, manifestos, revisões e resultado anterior.
O [recibo do reprocessamento](evidencias/reprocessamento_incremento_03.json)
registra comparações de todas as linhas e as transformações de metadados.

## Mudança confirmada

Foram comparadas as 1.506 linhas de commits e as 8.506 linhas de alterações do PyMC
Marketing. Excluindo somente o novo `run_id`, houve uma diferença:

- Commit: `003b1a2916e57e6baafac826eab849433e1fa7ad`.
- Caminho: `.cursor/skills/mmm-modeling`.
- Campo: `before_blob_sha`.
- Valor antigo: `227a6606a6a04d47b8ebbe0f0c1a82a19d5c0159` (objeto tree).
- Valor novo: `null`, pois a operação adiciona um blob de link simbólico.

As métricas e seus membros, 6.981 eventos candidatos, 45 eventos selecionados,
amostra, inventário e tabelas descritivas permaneceram iguais, descontando os
identificadores novos de execução. As três figuras são idênticas byte a byte.
A conferência das fontes abrangeu 7.614 commits, 7.631 caminhos e 180 blobs da
amostra. Os 495 arquivos históricos registrados antes da rodada mantêm seus hashes.

## Cadeia de fontes atual

| Etapa | Run ID |
|---|---|
| mine_run_id | `20260909T144237582697Z_af5a0048_phase4_mine_commits` |
| metrics_run_id | `20260909T144621249616Z_af5a0048_phase5_compute_metrics` |
| qualitative_run_id | `20260909T144655212671Z_af5a0048_phase7_select_qualitative` |
| report_run_id | `20260909T144717557913Z_af5a0048_phase8_report` |
| study_index_run_id | `20260909T144632500174Z_af5a0048_study_index` |

Índice atual: `data/interim/runs/20260909T144632500174Z_af5a0048_study_index/study_index.json`.

O freeze do PyMC Marketing continua sendo
`20260908T003854721749Z_43a2dae0_phase3_clone_repos`, no mesmo SHA
`fabba92c96aa6a4ec6d42fb3241a8ed725995d0a`. As execuções de Ultralytics e Anomalib
foram reutilizadas com seus hashes originais. Não houve nova busca, triagem ou
consulta histórica ao GitHub.

O mapa de PRs foi reutilizado após conferir sua identidade, o template de todos os
commits elegíveis e os hashes de **146 respostas preservadas**. O recibo histórico
da coleta mantém o vínculo com o índice antigo; o recibo deste incremento documenta
a compatibilidade com o índice novo. A seleção idêntica comprova ausência de impacto
da correção nessa etapa, mas não substitui o oráculo independente exigido por G10.

## Revisões e proveniência

Pasta preparada para o índice novo:
`data/interim/reviews/reprocessamento_20260909T144632500174Z_af5a0048_study_index`.

Os arquivos originais foram copiados para `originais_preservados/`. Taxonomia,
codificação e alinhamento foram copiados byte a byte. Em `casos_revisados.json`,
apenas `source_run_ids` do PyMC Marketing foi atualizado; `origens.json` registra
os valores anteriores e novos, hashes das cópias, índice e derivados correspondentes.
A atribuição antiga da preparação foi preservada nas revisões.

A primeira conferência operacional recusou a diferença no texto de
`preparation_by` dos templates novos. A diferença foi examinada e documentada como
metadado de preparação; todos os demais fatos de caso coincidiram. Uma tentativa
de retomada também recusou regravar a especificação de runs já existente. Ela foi
conferida por igualdade e reutilizada. Os scripts e logs dessas recusas permanecem
em `data/interim/verification/incremento_03/`, sem repetir as etapas concluídas.
Nenhuma dessas recusas representa divergência numérica ou erro do verificador empírico.

Os [comandos operacionais preservados](evidencias/comandos_reprocessamento_incremento_03.txt)
são um registro da retomada sobre os artefatos desta rodada; não são um comando
idempotente para iniciar outra coleta. Os comandos de cada etapa e seus logs estão
no recibo do reprocessamento. Os run IDs emitidos sempre foram usados explicitamente.

## Critérios e validação

| Critério | Incremento 2 | Incremento 3 |
|---|---|---|
| G00 | NOT_RUN | NOT_RUN |
| G01 | FAIL | FAIL |
| G02 | NOT_RUN | NOT_RUN |
| G03 | PASS | PASS |
| G04 | NOT_RUN | NOT_RUN |
| G05 | FAIL | PASS |
| G06 | PASS | PASS |
| G07 | FAIL | FAIL |
| G08 | FAIL | PASS |
| G09 | FAIL | PASS |
| G10 | NOT_RUN | NOT_RUN |
| G11 | NOT_RUN | NOT_RUN |
| G12 | NOT_RUN | NOT_RUN |
| G13 | FAIL | FAIL |

`scientific_eligible=true` nas etapas confirma a elegibilidade técnica da execução;
não equivale a `scientific_result_accepted=true`. Este último permanece falso.
G13 ainda requer integração ao finalizador. G14–G15 não pertencem ao escopo deste
recibo. Os contadores estáticos de chamadas MLflow não foram reimplementados no oráculo.

O [make check](evidencias/validacao_reprocessamento_incremento_03.txt) passou com
**203 testes, cobertura de 94,17%, lint, formatação, mypy e smoke com worktree limpo**.
Após a execução, foram reconferidos 20 arquivos de prova,
91 entradas vinculadas e os vínculos do importador de revisões.
As alterações versionáveis desta entrega são documentação e evidências da execução.
Os dados completos continuam nos diretórios locais de runs e verificação; devem
integrar o pacote de reprodução futuro, não apenas este resumo versionado.

Para repetir a conferência atual, criando outro diretório imutável automaticamente:

```sh
make verify-study \
  STUDY_INDEX=data/interim/runs/20260909T144632500174Z_af5a0048_study_index/study_index.json \
  REVIEW_DIR=data/interim/reviews/reprocessamento_20260909T144632500174Z_af5a0048_study_index
```

A recusa agregada é esperada enquanto os critérios obrigatórios permanecerem
pendentes. O Make representa a saída 1 da CLI como falha da receita.

## Próximos passos

1. Incorporar os arquivos humanos concluídos quando sua localização for fornecida,
   preservando as origens e conferindo a compatibilidade com este índice.
2. Implementar G10, reconstruindo de forma independente o agrupamento por PR e a
   seleção; completar as contraprovas obrigatórias de G04 e a resolução de evidências.
3. Integrar o recibo ao finalizador sem retirar os controles anteriores; resolver
   catálogo de afirmações, alinhamento e critérios ainda não executados.
4. Consolidar manuscrito, gerar pacote candidato e demonstrar restauração isolada
   antes do aceite final G00–G15.

A mineração corrigida já foi realizada; não é necessário repeti-la apenas para
versionar esta documentação ou incorporar revisões compatíveis.
