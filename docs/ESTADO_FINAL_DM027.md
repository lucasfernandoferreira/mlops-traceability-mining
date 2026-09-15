# Estado final do DM-027

**Fechado e tecnicamente aceito em 15/09/2026; congelado para redação do TCC.**
Esta é a página canônica de estado corrente. O
[manifesto de entrega](evidencias/manifesto_final_dm027.json) indexa as fontes,
seus hashes preexistentes e sua disponibilidade no Git ou no acervo local.

## 1. Identificação

| Campo | Registro |
|---|---|
| Protocolo | TCC-MLOPS-TRACE-2026, versão **2.1.0**; [configuração](../config/config.yaml) |
| Recorte | DM-027; plano de análise 1.0.0 |
| Taxonomia | **1.2.0**; [instrumento congelado](../config/file_taxonomy.yaml) |
| Fechamento | **15/09/2026**, recibo emitido em `2026-09-15T12:46:04Z` |
| Commit de referência em main | `7318222096720b0f2c74bb0c1859beaed89591da` |
| PR de fechamento | PR #17, `lucasfernandoferreira/mlops-traceability-mining` |
| Instrumento da confirmação e verificação | `16d24cc77c5df7baec6090144acb54bf7c40f588` |
| Política de verificação | 1.4.1; distinta do protocolo científico |
| Responsável | Lucas Fernando Alves Ferreira |
| Confirmação | `2026-09-15T12:00:08Z`; [extrato documental](evidencias/confirmacao_pesquisador_dm027_extrato.json) |
| Aceite final | [Recibo preservado](evidencias/recibo_final_dm027.json): `scientific_result_accepted: true`, sem bloqueios |

O commit de merge identifica a integração do fechamento. Cada run conserva seu
executor original no [índice de runs](evidencias/runs_dm027.json); esta consolidação
documental não muda o instrumento usado nas observações ou no aceite.

### Como ler os três estados

1. **Seleção e coleta históricas:** busca/triagem de 31/08/2026 e
   [amostra_final.yaml](../config/amostra_final.yaml), com seleção registrada em
   05/09 e revisão técnica em 08/09. `pilot`, `pending` e `pending_reason`
   descrevem esse snapshot. O arquivo também é entrada do instrumento, vinculado
   por SHA-256 à confirmação; nenhum campo ou metadado foi acrescentado.
2. **Construção:** incrementos, prévias, reprovação da taxonomia 1.1.0,
   rascunhos e recibos intermediários permanecem como foram registrados.
   Nomes como `rodada_atual.json` referem-se à etapa em que foram produzidos.
3. **Final aceito:** confirmação de 15/09, candidato restaurado e recibo final.
   A [leitura temporal das evidências](evidencias/README.md) resolve os vínculos
   entre rascunhos versionados e cópias confirmadas locais.

## 2. Casos congelados

| repository_id | SHA congelado | Justificativa e papel no contraste |
|---|---|---|
| `ultralytics/ultralytics` | `fa34184a5080c81fff453670394e13303ac781b2` | Visão computacional; callbacks concentram parâmetros, métricas e artefatos do treinamento. |
| `pymc-labs/pymc-marketing` | `fabba92c96aa6a4ec6d42fb3241a8ed725995d0a` | Domínio probabilístico/marketing; wrappers e contexto de inferência, com configurações Python classificadas como CODE. |
| `open-edge-platform/anomalib` | `0b7fdb9dde453f6474ac93f77188f4224d442999` | Detecção de anomalias; injeção de logger e operações herdadas do Lightning, condicionadas à habilitação. |

A seleção é intencional. Composer foi excluído por duas identidades ativas,
abaixo do mínimo de cinco; Anomalib era a primeira reserva previamente ordenada,
com 39 identidades, avaliada antes de observar suas métricas. Composer permanece
como caso histórico, sem integrar os três casos finais. Fontes, maturidade e
justificativas detalhadas estão no [registro de casos](INSPECAO_MANUAL_AMOSTRA.md)
e no [dossiê DM-026](DM026_E_FECHAMENTO_TAXONOMIA.md). Nenhum SHA foi atualizado.

## 3. Estado das avaliações

| Avaliação | Estado final e evidência |
|---|---|
| Taxonomia 1.2.0 | Aceita: **173/180 = 96,11%**, limiar global **95%**, sete divergências preservadas. Run `20260915T120009665828Z_16d24cc7_phase6_validate_taxonomy`, indexado no manifesto. |
| Análise qualitativa | **45 eventos, 15 por caso**, codificação confirmada; [síntese](SINTESE_QUALITATIVA_DM027.md) e artefato `confirmed_qualitative_coding` no manifesto. |
| Revisão de casos | Três casos aceitos na cópia confirmada `casos_revisados.json`; artefato `confirmed_case_reviews`. |
| Alinhamento acadêmico | Recorte operacional aceito pelo pesquisador, G12 PASS; `confirmed_academic_alignment`. Não comprova aprovação institucional ou da orientadora. |
| Confirmação do pesquisador | Registrada em 15/09/2026; autoria da redação preliminar e limites preservados no [extrato](evidencias/confirmacao_pesquisador_dm027_extrato.json). |

A avaliação mascarou predições individuais, mas conservou ordem estratificada e
conhecimento prévio do método. A confirmação assume julgamentos preparados;
não cria um segundo codificador independente. A calibração anterior é separada
da amostra de avaliação. O limiar é global: não assegura a mesma concordância
por caso/categoria. DATA_META está ausente no universo validado; sua concordância
não foi artificialmente preenchida. Consulte o [dossiê](DM027_TAXONOMIA_1_2_0.md)
e a [avaliação preservada](evidencias/avaliacao_taxonomia_dm027.md).

## 4. Gates de verificação

Os caminhos completos das provas por gate estão em `gates` no
[manifesto](evidencias/manifesto_final_dm027.json). Nesta tabela, **E** significa
o diretório `empirical/` da execução confirmada
`data/interim/fechamento_dm027/fechamento_confirmado_20260915T120020515444Z`.
As provas E e o relatório G14 são locais, inventariados; não acompanham um clone
Git simples. A coluna de evidência identifica arquivos efetivamente existentes.

| Gate | Critério | Status | Artefato de evidência | Observação |
|---|---|---|---|---|
| G00 | Preservação e origens | PASS | E/closure/G00.json | Inventários, hashes e bundle. |
| G01 | Registros de revisão | PASS | E/reviews/review_import.json | Cópias confirmadas, identidades e autoria. |
| G02 | Catálogo de afirmações | PASS | E/closure/G02.json | Estados, fontes e limites explícitos. |
| G03 | Oráculos independentes | PASS | E/independence.json | Implementações e confrontos documentados. |
| G04 | Fixtures e contraprovas | PASS | E/closure/G04.json; E/closure/fixtures.xml | Execução no verificador congelado. |
| G05 | Histórico e mudanças Git | PASS | E/{caso}/crosscheck.json | Três casos; objetos e tabelas confrontados. |
| G06 | Atividade e elegibilidade | PASS | E/original_collection_audit.json; E/{caso}/crosscheck.json | Contagens e shortlist históricas. |
| G07 | Inventário e taxonomia | PASS | E/reviews/review_import.json; E/{caso}/crosscheck.json | Blobs históricos e julgamentos preservados. |
| G08 | Métricas e denominadores | PASS | E/{caso}/crosscheck.json | Razões C/P, magnitude e seis indisponibilidades. |
| G09 | Estatística descritiva | PASS | E/{caso}/crosscheck.json | Quantis, concentração, séries e sensibilidade. |
| G10 | Seleção qualitativa | PASS | E/qualitative/crosscheck.json | PRs preservados, cotas, empates e déficits. |
| G11 | Identidade e pertinência das fontes | PASS | E/closure/G11.json | Integridade e julgamento de conteúdo separados. |
| G12 | Alinhamento operacional | PASS | E/closure/G12.json | Seis perguntas abertas e autoria da decisão. |
| G13 | Vínculos do finalizador | PASS | E/finalization_contract.json | Rechecagem obrigatória e candidato. |
| G14 | Restauração isolada | PASS | restoration/restoration_report.json, na execução confirmada | Saída 0, nenhuma divergência ou falha técnica. |
| G15 | Manuscrito, catálogo e parecer | PASS | [recibo final](evidencias/recibo_final_dm027.json), campo manuscript | 101 afirmações conferidas; parecer técnico. |

`{caso}` corresponde a `ultralytics__ultralytics`, `pymc-labs__pymc-marketing` e
`open-edge-platform__anomalib`. O recibo empírico cobre G00–G13. O recibo da fase 9
autoriza o candidato antes de G14/G15 e conserva aceite falso. Apenas o recibo
final agrega a aprovação posterior; os recibos anteriores não foram promovidos.

### Restauração e acesso ao acervo

G14 restaurou código e fontes em diretório independente, sem rede, hardlinks,
symlinks ou alternates para substituir cópias dos clones. Recalculou histórico,
atividade, C/P, magnitude, descrições e seleção, sem divergências. Contagens e
identidades exigem igualdade; floats usam tolerância absoluta de `1e-12`.
Coleta original, contagens do scanner estático, julgamentos e redação receberam
conferência de integridade, não nova coleta ou avaliação.

O interpretador e as dependências foram compartilhados com o ambiente original.
A restauração não demonstra portabilidade para outro sistema operacional.
São necessários o ZIP candidato, o bundle do instrumento e **todos** os arquivos
de `external_sources` com os hashes de `source_hashes` no relatório G14. O
[procedimento preservado](G14_RESTAURACAO_ISOLADA.md) explica essa recuperação.

O manifesto distingue `git` de `local_ignored` e aponta os caminhos relativos à
raiz do repositório. Os arquivos locais existem no acervo examinado, mas não há
URL pública de depósito do acervo completo registrada. Para auditoria com recálculo,
o pesquisador deverá entregar essas dependências à orientadora. Isso é uma
pendência de distribuição do acervo, não de nova coleta; o checkout ou o ZIP
isoladamente não garantem restauração.

## 5. Resultados científicos disponíveis

O problema científico original é a rastreabilidade entre código, dados,
configuração, ambiente e versões de modelos. O recorte executado preserva esse
problema e delimita o que as fontes públicas permitem observar. Seu objetivo
operacional, formalizado posteriormente à proposta original, é:

> Caracterizar mudanças conjuntas de código e configuração e examinar os mecanismos de integração MLflow documentados nos projetos públicos selecionados, delimitando o alcance e as lacunas das evidências de rastreabilidade.

São `observed` nos três casos: `code_config_cochange`, `config_magnitude`,
`static_mlflow_param_calls`, `static_mlflow_metric_calls`,
`static_mlflow_artifact_calls` e `static_mlflow_model_calls`.

| Caso | code_config_cochange (C∩P / C) | config_magnitude (chaves / commits CONFIG) |
|---|---|---|
| Ultralytics | 249/3272 = 0.0761002444987775 | 20723/299 = 69.3076923076923 |
| PyMC Marketing | 14/879 = 0.015927189988623434 | 469/16 = 29.3125 |
| Anomalib | 115/668 = 0.1721556886227545 | 11254/128 = 87.921875 |

Valores transcritos do [manuscrito técnico aceito](MANUSCRITO_DM027.md), sem novo
cálculo científico. A tabela `metricas_consolidadas.csv`, as séries mensais,
distribuições, sensibilidade e figuras do run
`20260911T204458152055Z_1ce60b65_phase8_report` são indexadas no manifesto e na
[rodada de referência](evidencias/rodada_referencia_1_2_0.md).
Os indicadores estáticos contam posições sintáticas no SHA; zero observado pelo
scanner não demonstra ausência de operações herdadas, wrappers ou uso efetivo.

As análises qualitativas dos **45 eventos** estão disponíveis na
[síntese](SINTESE_QUALITATIVA_DM027.md), no manuscrito e no catálogo de 101 afirmações.
A seleção agrupou commits do mesmo PR verificado e preservou commits sem vínculo
como unidades documentais. Aplicou cinco posições em Q1 (integração/chamadores),
Q2 (coalteração C/P) e Q3 (maiores magnitudes positivas), nessa ordem, sem reposição,
com regras de distribuição temporal, desempate e preenchimento de déficits.
O [método](DECISOES_METODOLOGICAS.md#análise-qualitativa) detalha o procedimento;
G10 confrontou a seleção usando associações de PR já preservadas.

## 6. Perguntas e métricas não respondidas

| Métrica | Estado nos três casos | Motivo |
|---|---|---|
| `data_code_ratio_original` | `not_available` | Dimensão D não validada para dados MLflow; DATA_META detecta DVC. |
| `data_code_cochange` | `not_available` | Mesma ausência de dimensão D validada. |
| `cace_index` | `not_available` | Coalteração tripla exige a dimensão D validada. |
| `provenance_coverage` | `not_available` | Não foram ingeridas fontes de runs e registry. |
| `env_versioning_rate` | `not_available` | Não há universo de runs com ambiente por execução nas fontes finais. |
| `experiment_redundancy` | `not_available` | Tracking e promoções de modelos no registry não integram o universo. |

Essas perguntas pertencem ao projeto original. **Ausência de fonte não é zero
nem resultado negativo.** C/P não responde ao CACE e contagens estáticas não
substituem proveniência. O recorte não será artificialmente completado por DVC,
tracking ou registry. O [mapa GQM](GQM_MAPA_METRICAS.md) e o
[parecer](ALINHAMENTO_DM027.md) preservam a diferença entre proposta e execução.

## 7. Escopo das conclusões

O estudo permite caracterizar coalterações de código/configuração, avaliar a
magnitude de mudanças CONFIG, examinar mecanismos públicos/documentados de
integração MLflow, comparar estruturalmente os três casos e discutir os limites
da rastreabilidade auditável publicamente.

O estudo não permite inferir causalidade, afirmar que MLflow reduz acoplamento,
provar uso efetivo em produção, avaliar proveniência completa de runs/modelos,
estimar prevalência estatística de práticas no ecossistema MLOps, tratar commits
como réplicas independentes ou generalizar para organizações industriais fechadas.
Mantêm-se as [limitações e ameaças à validade](LIMITACOES_E_VALIDADE.md), inclusive
CONFIG em Python, renomeações, categorias raras, datas reconstruídas e fontes LFS
posteriores explicitamente separadas da coleta original.

## 8. Próxima etapa

> Próxima etapa científica: transposição dos resultados consolidados para o manuscrito final do TCC, seguida de revisão da orientadora. O DM-027 não deve receber novas alterações metodológicas sem abertura formal de uma nova rodada.

A orientadora deverá avaliar o aceite acadêmico do recorte operacional e a
adequação da mudança entre proposta original e execução. Se exigir resposta a
alguma GQM `not_available`, será necessário formalizar outra rodada com fontes,
instrumento e decisões próprios. A confirmação do pesquisador já realizada não
antecipa essa decisão acadêmica.

> Alterações futuras no instrumento, taxonomia, casos, métricas ou fontes devem constituir uma nova rodada científica e não podem ser incorporadas retroativamente ao DM-027.

## Auditoria e validação documental

A [auditoria da consolidação](AUDITORIA_CONSOLIDACAO_DM027.md) registra ocorrências,
tratamentos, gaps de entrega e o roteiro de 20 perguntas para revisão externa.
O baseline de CI do fechamento registra 310 testes, 93,81% de cobertura, lint,
formatação, tipagem e smoke aprovados. Os comandos e resultados desta rodada
documental são informados separadamente nessa auditoria; não geram novo aceite
científico.
