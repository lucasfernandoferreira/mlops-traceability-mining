# Verificação da seleção qualitativa — incremento 4

O incremento implementa G10 sobre a rodada corrigida no
[incremento 3](REPROCESSAMENTO_E_VERIFICACAO_INCREMENTO_03.md). A política de
verificação passa a **1.2.0**; configuração científica, taxonomia, plano de análise
1.0.0 e dependências permanecem iguais. O código produtivo de seleção e mineração
não foi alterado.

## Resultado empírico

**G10 passou**, com zero diferenças na reconstrução dos vínculos, candidatos,
selecionados, ordem, posições, grupos, cotas e cobertura. O mesmo índice corrigido
foi conferido novamente contra o Git. G03, G05, G06, G08 e G09 também passaram.

Foram lidas **146 respostas preservadas**, cobrindo **7.182 commits elegíveis**.
A reconstrução confirmou **6.955 commits com uma associação de PR** e **227 commits
com resposta completa sem PR associado**, no escopo da API e nas datas da coleta. Isso não
prova ausência de toda relação documental fora dessa consulta.

| Caso | Eventos candidatos | Selecionados | Déficit final |
|---|---:|---:|---:|
| ultralytics/ultralytics | 4913 | 15 | 0 |
| pymc-labs/pymc-marketing | 1091 | 15 | 0 |
| open-edge-platform/anomalib | 977 | 15 | 0 |

O total é **6.981 candidatos e 45 eventos selecionados**, após agrupar os commits
associados ao mesmo PR. Não houve repetição de busca, triagem, mineração, consulta
ao GitHub ou geração da seleção produtiva. A rodada usa os mesmos SHAs e derivados
registrados no índice `20260909T144632500174Z_af5a0048_study_index`.

O agregado permanece **FAIL, saída 1, sem erros de processamento**. Os arquivos
humanos disponíveis continuam incompletos e há critérios obrigatórios não
executados. Este resultado não constitui aceite científico final.

## Implementação e independência

| Módulo | Responsabilidade |
|---|---|
| `verification/pr_sources.py` | Lê a consulta preservada, liga cada alias ao SHA e interpreta a resposta sem importar o coletor ou `pr_mapping`. Confere hashes, timestamps, casos congelados, template, universo completo e mapa usado na seleção. |
| `verification/selection.py` | Parte das linhas obtidas pelo oráculo Git e dos vínculos reconstruídos. Agrupa por partições ordenadas e calcula posições com frações exatas, sem importar `qualitative_selection`. |
| `verification/qualitative.py` | Confere o manifesto e o índice da seleção; compara todos os candidatos, selecionados, cobertura e identidades da planilha de codificação, preservando as saídas independentes. |
| `verification/runner.py` | Executa G10, vincula as fontes e provas ao recibo e conserva os bloqueios dos demais critérios. |

O leitor aceita especificamente o formato GraphQL congelado do coletor do estudo;
consultas fora desse formato são recusadas. Resposta incompleta, associação múltipla,
objeto ausente, PR de outro repositório ou falha da API não viram `pr_not_found`.
Consultas duplicadas, evidência sem hash correspondente e universo incompatível
impedem a conferência. A atribuição automática da coleta é preservada como metadado,
sem tratá-la como autenticação de revisão humana.

O agrupamento ocorre antes de Q1/Q2/Q3. A magnitude soma CONFIG no PR; Q2 exige C e P
no mesmo commit. A primeira adição elegível do componente é reservada em Q1.
Q1/Q2 usam posições temporais; Q3 usa magnitude decrescente com desempate por UTC e
SHA. Eventos já escolhidos são retirados dos grupos seguintes. O preenchimento
FILL registra déficits sem inventar pertencimento aos grupos.

As implementações compartilham Git, Python, JSON, o plano declarado e os caminhos
de integração. Os manifestos e o transporte das tabelas usam componentes comuns.
A interpretação dos vínculos e a seleção têm implementação separada da produção;
a pertinência científica dos caminhos e a interpretação dos eventos continuam
sendo controles de G11/G12.

## Provas e execução

A execução `empirical_01/` preserva a versão anterior ao reforço do tratamento de
casos ausentes/duplicados no template. A suíte e o verificador foram repetidos após
esse ajuste. O recibo final deste incremento é o de `empirical_02/`.

O [resumo versionado](evidencias/verificacao_empirica_incremento_04.json) contém
os hashes das fontes e provas, o vínculo com a rodada anterior e as limitações.
O recibo integral está em:

`data/interim/verification/incremento_04/empirical_02/verification_receipt.json`.

Dentro dessa execução, `qualitative/` contém `associations.json`, `candidates.json`,
`selected.json` e `crosscheck.json`. Os hashes das consultas e respostas originais,
mapa, manifestos e arquivos de seleção estão vinculados ao recibo. Os insumos
completos permanecem locais para inclusão posterior no pacote de reprodução.

O recibo registra **worktree com alterações locais**, base `af5a00489166bf262e0cc8c8f3c2ad5bc6842e19`
e o hash de `verification_source.tar.gz`, que preserva o código novo. O SHA da base
sozinho não identifica esta implementação de G10. G13 permanece reprovado tanto
pela integração ainda ausente ao finalizador quanto pela condição local do código.
Após commit e merge, repetir a verificação com worktree limpo, sem refazer a mineração.

```sh
make verify-study \
  STUDY_INDEX=data/interim/runs/20260909T144632500174Z_af5a0048_study_index/study_index.json \
  REVIEW_DIR=data/interim/reviews/reprocessamento_20260909T144632500174Z_af5a0048_study_index
```

Sem `OUTPUT_DIR`, o destino recebe timestamp e não substitui recibos anteriores.
A CLI retorna 1 para divergências/pendências e 2 para entradas ausentes ou
incompatíveis que impedem a conferência. O Make representa a recusa como falha da receita.

## Validação e estado dos critérios

A [suíte completa](evidencias/validacao_selecao_incremento_04.txt) passou com
**245 testes e 94,28% de cobertura**, incluindo lint, formatação, mypy e smoke-dev.
As [38 contraprovas](evidencias/contraprovas_incremento_04.xml) passaram. Os cenários
novos cobrem agrupamento prévio, primeira introdução, cotas, sobreposição, déficits,
empates UTC/SHA, magnitude nula/zero, alteração de vínculos mesmo com hashes de mapa
atualizados, resposta incompleta, SHA trocado, consulta duplicada, evento repetido e caso ausente/duplicado no template.

Os testes não completam automaticamente todo G04 e não substituem a rodada real.
Após a execução foram reconferidos **24 arquivos de prova**,
**248 entradas vinculadas** e os vínculos do importador.

| Critério | Estado |
|---|---|
| G00 | NOT_RUN |
| G01 | FAIL |
| G02 | NOT_RUN |
| G03 | PASS |
| G04 | NOT_RUN |
| G05 | PASS |
| G06 | PASS |
| G07 | FAIL |
| G08 | PASS |
| G09 | PASS |
| G10 | PASS |
| G11 | NOT_RUN |
| G12 | NOT_RUN |
| G13 | FAIL |

## Próximos passos

1. Integrar o recibo empírico ao finalizador (G13), preservando os controles atuais
   de revisões, validação de taxonomia, seleção e relatório.
2. Resolver as evidências citadas e o catálogo de afirmações; incorporar as revisões
   concluídas quando sua origem for disponibilizada e completar G04/G11/G12.
3. Gerar candidato, preparar o manuscrito e demonstrar a restauração isolada antes
   do aceite agregado G00–G15.
