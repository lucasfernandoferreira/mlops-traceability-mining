# Casos e andamento da pesquisa

A amostra piloto reúne Ultralytics, PyMC Marketing e Anomalib. Os três apresentam
integração funcional observável com MLflow e passaram na contagem técnica de
atividade. A decisão definitiva sobre os casos, a revisão da taxonomia e o
alinhamento acadêmico permanecem pendentes. Os critérios estão no
[método](DECISOES_METODOLOGICAS.md).

## Origem da amostra

A busca e a triagem de 31/08/2026 foram preservadas com os seguintes identificadores:

| Etapa | Execução |
|---|---|
| Busca | `20260831T030743921886Z_bb7d2ee1_phase1_search_candidates` |
| Triagem | `20260831T121157885962Z_fc55f2d9_phase2_screen_sample` |

A shortlist tem SHA-256
`69f0891d3a8d029d7e7ea44115c4ea7a88dbb5074eef4bfc5b843dc3d3acbfe2`.
Os manifestos registram `SUCCESS`, origem com worktree limpo e 59 elegíveis, sem
erros de triagem: 53 apenas MLflow, quatro apenas DVC e dois com ambas as ferramentas.
Esses CSVs e manifestos são locais. A auditoria está em
[baseline_audit.json](evidencias/baseline_audit.json).

A inspeção inicial priorizou Ultralytics, PyMC Marketing e Composer, com Anomalib,
Axolotl e RF-DETR como reservas, nessa ordem. Os SHAs permanecem os observados na
shortlist; nenhum foi atualizado para uma revisão mais recente.

| Projeto | SHA selecionado | Commits alcançáveis | Identidades ativas | Estrelas na coleta |
|---|---|---:|---:|---:|
| Ultralytics | `fa34184a5080c81fff453670394e13303ac781b2` | 4.974 | 175 | 61.103 |
| PyMC Marketing | `fabba92c96aa6a4ec6d42fb3241a8ed725995d0a` | 1.506 | 40 | 1.250 |
| Anomalib | `0b7fdb9dde453f6474ac93f77188f4224d442999` | 1.134 | 39 | 6.099 |
| Composer, caso histórico | `6405188805a0054b4551ec49e4919c54c971d0e8` | 2.701 | 2 | 5.495 |

As identidades ativas correspondem a autores de commits não merge/não bot posteriores
a 01/09/2025 UTC. A regra não resolve todos os aliases em pessoas distintas. As
estrelas são referentes à coleta de 31/08, não ao estado atual dos projetos.

## Ultralytics

Ultralytics representa o treinamento de modelos de visão computacional com integração
por callbacks. O [treinador](https://github.com/ultralytics/ultralytics/blob/fa34184a5080c81fff453670394e13303ac781b2/ultralytics/engine/trainer.py)
registra callbacks e dispara eventos; o
[componente MLflow](https://github.com/ultralytics/ultralytics/blob/fa34184a5080c81fff453670394e13303ac781b2/ultralytics/utils/callbacks/mlflow.py)
encaminha argumentos de treinamento, métricas e arquivos de saída.

A habilitação depende da configuração MLflow, da disponibilidade do pacote e das
condições de execução do callback. `log_artifact` recebe pesos e outros arquivos,
sem comprovar promoção no registry. O caso permite examinar a relação entre mudanças
de configuração e instrumentação de treinamento. Os testes de integração são
fontes documentais e não foram executados como parte da pesquisa.

## PyMC Marketing

PyMC Marketing acrescenta modelos probabilísticos e contexto de dados de marketing.
A [integração MLflow](https://github.com/pymc-labs/pymc-marketing/blob/fabba92c96aa6a4ec6d42fb3241a8ed725995d0a/pymc_marketing/mlflow.py)
envolve operações de amostragem e, com `log_mmm`, o ajuste do modelo MMM. Configuração,
entrada e dados de inferência aparecem nas operações de registro.

A ligação foi examinada junto ao
[model builder](https://github.com/pymc-labs/pymc-marketing/blob/fabba92c96aa6a4ec6d42fb3241a8ed725995d0a/pymc_marketing/model_builder.py)
e aos testes `tests/test_mlflow.py`. O contraste está na instrumentação do contexto
probabilístico, em comparação com callbacks de treinamento visual. A existência dos
wrappers não comprova que uma organização tenha executado ou persistido esses runs.

## Anomalib e substituição do Composer

O Composer oferece um logger conectado ao Trainer e operações de parâmetros,
métricas e modelos. Entretanto, a mineração encontrou apenas duas identidades
ativas, abaixo do mínimo de cinco. Seus resultados foram mantidos como históricos,
e a primeira reserva passou a ser avaliada por esse motivo de elegibilidade.

O Anomalib apresentou 1.134 commits alcançáveis e 39 identidades ativas no SHA
original. O clone completo e a contagem foram conferidos antes do cálculo de suas
métricas. A substituição técnica foi registrada em 08/09/2026 UTC, ainda em 07/09 no
horário de São Paulo, sem alterar os critérios de inclusão. O recibo está em
[anomalib_elegibilidade.json](evidencias/anomalib_elegibilidade.json).

O Engine recebe o logger e o repassa ao Trainer do Lightning; quando nenhum logger
é fornecido, o registro fica desligado. O AnomalibMLFlowLogger especializa o logger
MLflow do Lightning. A ligação documentada envolve os hiperparâmetros salvos pelo
AnomalibModule e as métricas enviadas por modelos LightningModule, encaminhadas
às operações herdadas de parâmetros e métricas. A versão 2.6.5 do lockfile foi
conferida no commit `be98784a1a03581b7051a355ae1084fd352d7cea` do Lightning.
As fontes e os trechos estão no [dossiê DM-026](DM026_E_FECHAMENTO_TAXONOMIA.md).

O usuário precisa instalar o extra de loggers e fornecer o logger ao Engine.
`log_model=False` é o padrão; a disponibilidade de registro de checkpoints é
condicional e não comprova uma promoção de modelo ou execução pública.

**Correção da ficha em 11/09/2026:** o Engine removeu o registro de
`_VisualizationCallback` no commit `084331dad4e320c7dc200823aa8ae8857ec94d4b`
(v2.0.0). A cadeia automática de imagens anteriormente descrita não se sustenta
no SHA estudado. `add_image`, `log_image` e `log_figure` continuam disponíveis
para chamada explícita, mas não justificam o contraste originalmente atribuído.
Os runs e fichas anteriores são históricos e permanecem preservados.

O contraste corrigido é a injeção de logger num framework de treinamento, com
operações herdadas verificadas conforme DM-026 A. O domínio ainda se aproxima do
Ultralytics. A correção técnica não preenche as decisões humanas dos casos.
O novo índice e seus derivados precisam ser registrados com worktree limpo.

## Reservas e candidatos não priorizados

As próximas reservas permanecem Axolotl, SHA
`917a3d041972eb33be5d6fcbb40ac1681fd2b8f4`, e RF-DETR, SHA
`6674d8581b7694baf567b993a4f32000a6f4f4c2`. A primeira acrescentaria fine-tuning de
LLMs; a segunda, outra integração delegada ao Lightning. Uma nova substituição
exigiria justificativa e avaliação segundo as mesmas regras.

A inspeção inicial não priorizou Pathway, pois as evidências de DVC e MLflow não
confirmavam uso no mesmo pipeline; Hongbomiao, pelo tracking observado em outra
ferramenta e pelo custo do monorepositório; Evidently, por artefatos associados a
testes visuais; OWID ETL, sem treinamento pertinente confirmado; e os repositórios
ROCm, cujos bancos de kernels e bibliotecas tinham outro objeto. Esses julgamentos
não alteraram as decisões automáticas da shortlist.

## Execuções anteriores

A fundação do projeto foi validada em 30/08, com 32 testes e 96,93% de cobertura.
O baseline de 07/09, no commit `11e480b5eac8d283cf98bd65031dd06c209a5866`, registrou
112 testes, 92,69% de cobertura e `make check` aprovado. O ambiente era Python
3.12.13 em WSL2. O log está em [baseline_check.txt](evidencias/baseline_check.txt).
Esses números são verificações de software, não medidas de conclusão científica.

O primeiro piloto Ultralytics usou o protocolo 2.0.0. Seus runs de congelamento,
mineração e métricas foram, respectivamente,
`20260905T232906312900Z_b1b31b5b_phase3_clone_repos`,
`20260905T232916405045Z_b1b31b5b_phase4_mine_commits` e
`20260905T233337569768Z_b1b31b5b_phase5_compute_metrics`.

Foram incluídos 4.914 dos 4.974 commits; os 60 descartes eram bots. Houve 224 commits
C∩P entre 3.220 commits C (6,96%) e 8.136 chaves em 276 commits P
(29,48 chaves por commit). A mediana foi uma chave, e 80 commits P tiveram magnitude
zero. Um movimento de diretórios contribuiu com 3.281 chaves, cerca de 40,33% do total.
Esses resultados motivaram as análises de distribuição e sensibilidade, preservando
a fórmula principal. Os valores permanecem preliminares.

A rodada de desenvolvimento de 07/09 processou Ultralytics, PyMC Marketing e Composer.
Produziu um inventário de 6.214 caminhos, amostra de 178 unidades e 45 eventos
qualitativos preliminares. Composer não teve commits CONFIG elegíveis; sua magnitude
foi indefinida, o que não demonstra ausência de configurações no projeto. A
finalização registrou pendências de cadeia limpa, seleção, taxonomia, alinhamento e
codificação. Os runs e hashes estão no
[índice da rodada](evidencias/indice_entrega_parecer.json); a verificação técnica
registrou 125 testes em [parecer_quality.txt](evidencias/parecer_quality.txt).

## Rodada atual: 08/09/2026 UTC

O trio com Anomalib foi processado no commit `43a2dae0804ed3a2e0f2ec1c64dd02386d956a35`,
com worktree limpo. Essa revisão foi preservada em arquivo local antes da
reorganização dos commits; os identificadores das execuções continuam vinculados
ao instrumento original. As nove execuções das fases 3–5 e as etapas derivadas tiveram
suas fontes e hashes conferidos. Os três inventários ficaram completos e nenhum
erro semântico foi encontrado. Ultralytics e PyMC Marketing reproduziram os valores
e estados das 12 métricas da rodada anterior.

| Caso | Commits incluídos | C∩P / C | Coalteração | Chaves / commits P | Magnitude média |
|---|---:|---|---:|---|---:|
| ultralytics/ultralytics | 4.914 | 224 / 3.220 | 6,96% | 8.136 / 276 | 29,48 |
| pymc-labs/pymc-marketing | 1.257 | 14 / 876 | 1,60% | 469 / 16 | 29,31 |
| open-edge-platform/anomalib | 1.011 | 108 / 668 | 16,17% | 10.883 / 119 | 91,45 |

Esses valores descrevem o cálculo e continuam preliminares até a revisão do
instrumento. O inventário reúne 7.631 caminhos e a amostra de revisão contém
180 unidades, 20 em cada categoria presente. DATA_META não foi encontrada
sob as regras no universo inventariado; isso não demonstra ausência de dados.

A API foi consultada para os 7.182 commits elegíveis: 6.955 tiveram associação única
com PR e 227 não tiveram vínculo retornado. Não restaram
erros ou consultas pendentes. A seleção qualitativa produziu 45 eventos,
com cinco eventos por grupo em cada caso, sem déficits nas cotas.

O [registro da rodada](evidencias/rodada_atual.json) reúne os identificadores, hashes,
contagens e recibos. A verificação `make check` passou com 140 testes e 93,07% de
cobertura; o log está em [validacao_atual.txt](evidencias/validacao_atual.txt).

## Revisão e continuidade

O [guia de revisão](../data/interim/reviews/trio_20260908T003438Z/revisao.html) reúne as prévias dos
arquivos, seus históricos e os eventos selecionados. As quatro cópias de trabalho
ficam no mesmo diretório: taxonomia, fichas dos casos, alinhamento acadêmico e
codificação qualitativa. O [pacote de revisão](../data/interim/executions/trio_20260908T003438Z/revisao.zip)
contém esses arquivos, o inventário e as respostas da consulta commit–PR.
Os links apontam para artefatos locais e não estarão disponíveis em um checkout
que contenha somente os arquivos versionados.

A finalização desta rodada confirmou a cadeia limpa e manteve quatro pendências:
decisão sobre os casos, validação humana da taxonomia, alinhamento acadêmico e
codificação qualitativa. Depois de preencher as cópias, o comando abaixo executa
nova validação e, se aceita, tenta a finalização com as fontes desta rodada:

```bash
.venv/bin/python data/interim/reviews/trio_20260908T003438Z/retomar.py
```

No alinhamento acadêmico, permanecem sem fonte ou dimensão validada
`provenance_coverage`, `data_code_ratio_original`, `data_code_cochange`, `cace_index`,
`env_versioning_rate` e `experiment_redundancy`. A decisão deve explicar como essas
lacunas se relacionam ao objetivo do TCC e às condições do parecer.

A documentação foi reunida nos arquivos de método, casos, métricas, dados e limitações
para evitar versões concorrentes. O [roteiro recebido](../data/interim/documentation/roteiro_recebido_2026-09-07.txt)
e os registros originais continuam preservados. Seis documentos ausentes foram
recuperados de um snapshot conferido por hash antes da consolidação; a origem está
em [recuperacao_documentos.json](evidencias/recuperacao_documentos.json).
