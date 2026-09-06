# Piloto Ultralytics — resultados preliminares

O piloto percorreu clonagem completa, congelamento, mineração e cálculo de uma tabela
rastreável. O protocolo operacional é 2.0.0 e a taxonomia 1.1.0. A execução permite
worktree com alterações e preserva o instrumento exato em snapshots com SHA-256;
não é uma execução científica oficial nem certificação humana da taxonomia.

## Caso, universo e funil

Repositório: `ultralytics/ultralytics`.
SHA: `fa34184a5080c81fff453670394e13303ac781b2`.
Período dos commits alcançáveis: 11/09/2022 16:39:46 a 30/08/2026 17:38:24 UTC.
O histórico inclui todos os ancestrais do SHA; a data de atividade não corta a série.

| Etapa | Commits |
|---|---:|
| Alcançáveis | 4.974 |
| Excluídos como merge | 0 |
| Excluídos como bot | 60 |
| Excluídos por mais de 1.000 arquivos | 0 |
| Incluídos | 4.914 |
| Incluídos com código C | 3.220 |
| Incluídos com configuração P | 276 |
| Incluídos com C e P | 224 |

O gate suplementar encontrou 175 identidades ativas de autor após 01/09/2025,
excluindo merges e bots, acima do mínimo de cinco. A deduplicação usa e-mail
normalizado, sem mailmap; não é uma estimativa independente de pessoas únicas.
Nenhuma identidade foi persistida nas tabelas analíticas.

## Tabela interpretável

| Métrica | Numerador | Denominador | Resultado |
|---|---:|---:|---|
| Coalteração código–configuração | 224 commits C∩P | 3.220 commits C | 6,96% |
| Magnitude de configuração | 8.136 chaves alteradas | 276 commits P | 29,48 chaves/commit |
| Chamadas estáticas de parâmetros | 1 posição | 1 snapshot | 1 |
| Chamadas estáticas de métricas | 1 posição | 1 snapshot | 1 |
| Chamadas estáticas de artefatos | 2 posições | 1 snapshot | 2 |
| Chamadas estáticas log_model/register_model | 0 posições | 1 snapshot | 0 |
| Razão dados/código original; coalteração dados/código; CACE triplo | — | — | `not_available`: D não validada em MLflow |
| Proveniência; ambiente por run; runs/promoções | — | — | `not_available`: fontes de runs/registry não ingeridas |

Os valores observados são tecnicamente calculáveis, mas permanecem preliminares até
validação humana. Zero chamadas de log_model/register_model não significa ausência
de pesos salvos, ausência de modelos ou ausência de experimentos.

## Conferência qualitativa inicial

O [callback MLflow no SHA selecionado](https://github.com/ultralytics/ultralytics/blob/fa34184a5080c81fff453670394e13303ac781b2/ultralytics/utils/callbacks/mlflow.py)
contém uma posição log_params, uma log_metrics e duas log_artifact. A primeira chamada
de artefatos referencia o diretório de pesos; a segunda percorre arquivos de saída.
Loops não multiplicam posições estáticas. Condições de habilitação e tratamento de
falhas mostram por que presença no código não comprova execução ou persistência.
Autolog é detectado no inventário, mas não expandido em eventos presumidos.

Foram examinados 1.030 arquivos na árvore congelada. O AST encontrou 20 candidatos
sintáticos MLflow no total, dos quais oito em TEST e 12 em CODE; os quatro indicadores
selecionam apenas as operações indicadas na tabela. Não houve erros de parser Python.
Nenhum caminho de arquivo sob diretório `mlruns` foi encontrado nessa árvore,
inclusive aninhado. Isso não cobre outros formatos, revisões ou serviços externos.

A magnitude de 29,48 não descreve uma alteração típica de hiperparâmetros. A mediana
é uma chave; 80 dos 276 commits CONFIG têm zero mudança semântica. O maior commit,
[620f3eb2181c1b686c9bdd2ee805dee483d4f116](https://github.com/ultralytics/ultralytics/commit/620f3eb2181c1b686c9bdd2ee805dee483d4f116),
contribui com 3.281 chaves (40,33% do total), em uma refatoração de diretórios. A
comparação com detecção de renomeação confirma o movimento de cfg/default.yaml;
o contrato principal conta remoção e adição. Configurações de datasets contêm nomes
de classes, inclusive o mapa ImageNet com 2.005 folhas no arquivo adicionado.
Os quatro maiores commits somam 67,93% das chaves. Essa concentração sustenta análise
qualitativa e uma futura análise de sensibilidade, sem alterar retroativamente a fórmula.

## Validação e pendências

A amostra determinística real tem 115 arquivos: CODE 20, CONFIG 20, DOC 20, OUTRO 20,
CI 12, TEST 11, ENV 6, NOTEBOOK 4 e DATA_RAW 2. DATA_META não aparece no SHA.
Os rótulos humanos permanecem vazios. Para atingir 20 por categoria, faltam exemplos
nos grupos menores e em DATA_META, além da revisão de todos os itens. O gate de 95%
não foi declarado aprovado. Não transformar predições automáticas em rótulos esperados.

O protocolo/GQM, a seleção operacional dos três casos e o parser estão documentados.
Faltam alinhamento acadêmico, revisão humana, congelamento e gates suplementares de
PyMC Marketing/Composer, expansão da mineração e análise qualitativa completa.
Esta entrega encerra o percurso técnico do primeiro piloto, não o estudo de três casos.

## Como auditar e reproduzir

Execute as etapas 03, 04 e 05 conforme o README. Cada etapa preserva um novo diretório;
clones completos compatíveis são reutilizados. O `source_audit.json` da Fase 3 verifica
os artefatos originais da busca/triagem e os instrumentos no commit original.

`metric_membership.csv` enumera os SHAs de cada denominador. Para coalteração, some
in_numerator; para magnitude, some numerator_contribution. `commits.parquet` contém
o funil completo. `changes.parquet` liga cada contribuição aos caminhos e chaves,
permitindo recuperar os blobs pelo commit/parent_sha. `tree_inspection.json` liga
as posições AST aos arquivos, linhas, URLs e hashes. `metrics.csv` registra unidades,
status, numeradores, denominadores, versões e run_id.

A execução final desta sessão e seus hashes estão no registro abaixo. Artefatos
empíricos e manifestos continuam locais, sem inclusão automática no Git.


## Verificação técnica da implementação

`make lint format-check typecheck test smoke-dev`: aprovado, com 112 testes e
92,69% de cobertura. Os testes incluem histórico sintético com descendente fora do SHA,
bots, merge, commit grande, configuração inválida, aliases AST, binários Parquet,
reutilização de clone, execução das três etapas, adulteração de entradas e gate humano.
O smoke executado é de desenvolvimento; `make check` exige worktree limpo.

## Registro das execuções finais da sessão

Os hashes abaixo foram conferidos após a execução. Os três snapshots coincidem com
os bytes atuais de código, scripts, configuração e locks. As contagens dos membros
dos denominadores e a soma de suas contribuições reproduzem a tabela final.
Foram preservados 31.710 eventos de arquivos, dos quais 873 CONFIG.

| Etapa | Run | Manifesto SHA-256 |
|---|---|---|
| phase3_clone_repos | `20260905T232906312900Z_b1b31b5b_phase3_clone_repos` | `b36e44898cf9284cfec97ad8845b427bfa29b63b26a43d8f41c3e1468e5641d7` |
| phase4_mine_commits | `20260905T232916405045Z_b1b31b5b_phase4_mine_commits` | `307d5b3ca4aeeec2c7ae57de20f87c78e71a007f374c6fba3ea77fc87581a8e2` |
| phase5_compute_metrics | `20260905T233337569768Z_b1b31b5b_phase5_compute_metrics` | `f084376aeaf6cdc62bf4c4657f7eda977455f9e0bbf6a44a61b7f442fc0fcfba` |

| Artefato local | SHA-256 |
|---|---|
| [amostra_congelada.csv](../data/interim/runs/20260905T232906312900Z_b1b31b5b_phase3_clone_repos/amostra_congelada.csv) | `7e3aa897797ac703190e3eb14c1b22977e286080a0c28078f533e0c7a588c58d` |
| [source_audit.json](../data/interim/runs/20260905T232906312900Z_b1b31b5b_phase3_clone_repos/source_audit.json) | `2c04006a03e57f87ec3f9803159440006ee20bca6f7624fcff22302743ba166b` |
| [commits.parquet](../data/interim/runs/20260905T232916405045Z_b1b31b5b_phase4_mine_commits/commits.parquet) | `edd6a324ca56d278dd93a5d200bb32eed0b9f74ae9fdb164fa2d792b3adf07e9` |
| [changes.parquet](../data/interim/runs/20260905T232916405045Z_b1b31b5b_phase4_mine_commits/changes.parquet) | `d0007e9d6911edd0da69cb2e9516c1af2c73ed15d87b4a675af6f1be346bc0fb` |
| [amostra_validacao_taxonomia.csv](../data/interim/runs/20260905T232916405045Z_b1b31b5b_phase4_mine_commits/amostra_validacao_taxonomia.csv) | `77c5b421a4bc1d6faaeb0f1e87cfd875329080680ad8a888b24929426102ef84` |
| [tree_inspection.json](../data/interim/runs/20260905T232916405045Z_b1b31b5b_phase4_mine_commits/tree_inspection.json) | `228396a7480e608588929b1b89c7cfeb16b931716717bd70e544dfbda2df5a5e` |
| [source_snapshot.tar.gz](../data/interim/runs/20260905T232916405045Z_b1b31b5b_phase4_mine_commits/source_snapshot.tar.gz) | `b652b60ece4f09e73e4e261e24c9f1eef2599df2a35cf5127693bbf1de4a6889` |
| [metrics.csv](../data/interim/runs/20260905T233337569768Z_b1b31b5b_phase5_compute_metrics/metrics.csv) | `424d27b9c2fcb130e450f8936a89a165b21178cd436140aa269923357a8afe4d` |
| [metric_membership.csv](../data/interim/runs/20260905T233337569768Z_b1b31b5b_phase5_compute_metrics/metric_membership.csv) | `1e3c0d4ea745ea3505fa05e4d64384a246d8c7f72eb4cecc4bf24c00ab50f687` |
| [piloto.md](../data/interim/runs/20260905T233337569768Z_b1b31b5b_phase5_compute_metrics/piloto.md) | `c1da7eef325f055621bb92fa503b2073509de01b87f4f572c4a58a4bd889b7fa` |
