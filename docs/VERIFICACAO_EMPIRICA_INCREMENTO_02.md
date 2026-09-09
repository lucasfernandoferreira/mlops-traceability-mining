# Verificação empírica — incremento 2

O incremento parte do merge `7863bd6`, com worktree limpo e `make check` aprovado
(179 testes). A política de verificação passa a **1.1.0**; protocolo, taxonomia,
configuração científica e locks permanecem iguais aos da coleta. O objetivo deste
incremento é confrontar as tabelas preservadas com os objetos Git, sem repetir a
busca ou atualizar observações do GitHub.

## Implementação

`make verify-study` agora recebe índice e revisões explicitamente. O destino é novo
por execução, com recibos JSON, fontes recontadas e relatório Markdown. O comando
não infere `latest`, não consulta GitHub e não sobrescreve as tabelas originais.

```sh
make verify-study \
  STUDY_INDEX=data/interim/runs/20260908T004303820864Z_43a2dae0_study_index/study_index.json \
  REVIEW_DIR=data/interim/reviews/trio_20260908T003438Z \
  OUTPUT_DIR=data/interim/verification/minha_conferencia
```

Sem `OUTPUT_DIR`, o comando cria um diretório com timestamp UTC. A CLI retorna 0
apenas para todo o escopo aprovado, 1 para critérios reprovados/não executados e 2
para entradas ausentes/incompatíveis ou falhas que impediram a conferência. O Make
pode representar qualquer falha de receita por seu próprio código 2; o código da
CLI é registrado no recibo.

| Componente | Conferência independente |
|---|---|
| `git_oracle.py` | Percorre o DAG com `rev-list`, lê commits/blobs com `cat-file --batch`, verifica o SHA-1 do cabeçalho e conteúdo e extrai diffs raw contra o primeiro pai. Confere todos os SHAs, exclusões, arquivos, flags, tipos e blobs. Recusa clones shallow/promisor. |
| `semantics.py` | Compara árvores CONFIG em pares, sem importar o flattening produtivo; chaves tipadas, listas atômicas, erros explícitos e cache por par de blobs/parser. |
| `oracles.py` | Recalcula inteiros, numeradores, denominadores e os seis estados de indisponibilidade, sem transformar ausência em zero. |
| `descriptive.py` | Recalcula média, mediana, quantis lineares, zeros, concentração, meses UTC e variantes de sensibilidade em Python, sem a agregação pandas produtiva. |
| `tables.py` | Normaliza apenas o transporte de inteiros anuláveis do Parquet/CSV; representações como `7820.0` são interpretadas com Decimal exato, sem truncar frações. |
| `runner.py` | Confere manifestos, incorpora revisões por cópia, verifica inventário e blobs da amostra, executa os oráculos e registra G00–G13, inclusive os não executados. |

A comparação usa inteiros e hashes exatos; floats seguem a tolerância absoluta de
`1e-12` definida antes das execuções. As identidades de atividade são calculadas
em memória, sem persistir nomes/emails no novo relatório. O filtro de grandes
commits não é aplicado à atividade, e o corte temporal é estritamente posterior.

Git, regex, PyYAML e a serialização JSON de escalares são dependências comuns
declaradas. Diversidade de extração/comparação não autentica uma interpretação
humana. Os contadores AST de MLflow não foram reimplementados neste incremento.

## Resultado da execução real

A execução final está em
`data/interim/verification/incremento_02/empirical_03/verification_receipt.json`.
O [resumo versionado](evidencias/verificacao_empirica_incremento_02.json) preserva
seu hash, os resultados por caso e os vínculos das provas. Os 20 arquivos de prova
e os hashes das entradas vinculadas foram reconferidos após a execução.

| Caso | Alcançáveis | Elegíveis | Identidades ativas | C∩P / C | Chaves / commits CONFIG | Blobs da amostra |
|---|---:|---:|---:|---:|---:|---:|
| Ultralytics | 4.974 | 4.914 | 175 | 224 / 3.220 | 8.136 / 276 | 51 |
| PyMC Marketing | 1.506 | 1.257 | 40 | 14 / 876 | 469 / 16 | 70 |
| Anomalib | 1.134 | 1.011 | 39 | 108 / 668 | 10.883 / 119 | 59 |

Foram confrontados 7.614 commits, 7.631 caminhos do inventário e 180 blobs históricos
da amostra. Os pares CONFIG foram comparados em 1.476 entradas de cache por
blobs/parser. O funil reconciliou 7.182 incluídos, 399 bots, 32 merges e um commit
grande. As identidades ativas são apresentadas por caso, sem somá-las como pessoas.

Os numeradores, denominadores, estados, quantis, concentração, meses e variantes
de sensibilidade coincidiram com as tabelas preservadas, dentro da tolerância
prévia. A [tabela de reconciliação](evidencias/reconciliacao_metricas_incremento_02.csv)
separa concordância aritmética de concordância integral das fontes.

O resultado agregado foi **FAIL, código 1**, sem erros que impedissem a execução.
G03 e G06 passaram. G05 falhou pela ocorrência descrita abaixo; G08 e G09 também
mantêm o bloqueio de integridade das fontes, embora seus recálculos tenham
coincidido. G01/G07 permanecem reprovados pela falta dos registros humanos
preenchidos. Os critérios restantes mantêm seus bloqueios ou `NOT_RUN`, inclusive
G13, cuja integração ao finalizador ainda não existe.

O teste da correção também foi aplicado ao caminho empírico afetado, sem regenerar
o dataset: [evidência da regressão](evidencias/regressao_blob_tree_incremento_02.json).
As tentativas anteriores permanecem preservadas: uma recusou a representação CSV
inteira `7820.0` por limitação do novo leitor, corrigida com Decimal exato; outra
foi interrompida antes do recibo final. Nenhuma é apresentada como rodada aprovada.

A [validação final](evidencias/validacao_verificacao_incremento_02.txt) passou com
**203 testes, cobertura de 94,17%, lint, formatação, mypy e smoke-dev**.
As [15 contraprovas executadas](evidencias/contraprovas_incremento_02.xml) passaram;
isso não completa automaticamente todas as mutações exigidas por G04.

## Divergência demonstrada e correção

A conferência identificou uma divergência no PyMC Marketing:

- Commit: `003b1a2916e57e6baafac826eab849433e1fa7ad`.
- Caminho: `.cursor/skills/mmm-modeling`.
- Operação: substituição de diretório por link simbólico, representada pelo Git
  como adição do link e remoção dos arquivos do diretório.
- Campo preservado: `before_blob_sha=227a6606a6a04d47b8ebbe0f0c1a82a19d5c0159`.
- Tipo real desse objeto: **tree**, não blob. O valor correto para o blob anterior
  da adição é **null**.

O extrator buscava qualquer objeto no caminho e registrava seu SHA como blob.
`mining.py` agora exige `git.Blob` tanto nos metadados quanto em `read_blob`.
Uma fixture de diretório → link simbólico confirma o resultado correto; adulterar
sua cópia com o SHA do diretório reproduz a divergência esperada no oráculo.

As tabelas históricas não foram editadas. Os resultados de C/P e magnitude não
mudam nesta ocorrência, classificada como OUTRO, mas a inconsistência permanece
nos dados antigos e bloqueia os critérios que dependem de plena concordância com
as fontes. Corrigir o extrator não equivale a corrigir retroativamente um Parquet.

## Escopo e pendências

O recibo declara G00–G13. Campos não executados continuam `NOT_RUN`; o relatório
não é aceite científico final. G14–G15, restauração do estudo e finalização estão
fora desse escopo. `scientific_result_accepted` permanece `false`. Este incremento
ainda não integra o recibo novo ao finalizador antigo; use o recibo de verificação
para acompanhar as divergências, sem apresentar a finalização antiga como G13.

Os arquivos locais de revisão continuam sem os julgamentos preenchidos. Isso
registra os arquivos encontrados e não contradiz a revisão concluída informada
pelo pesquisador. G01/G07 não recebem aprovação por inferência. As fontes físicas
da amostra podem ser conferidas mesmo enquanto os registros humanos estão pendentes.

A implementação de G10 (reconstrução independente da seleção agrupada por PR),
a resolução completa das afirmações/documentos, o conjunto restante de mutações,
a integração ao aceite e a restauração isolada permanecem próximos incrementos.

## Reexecução por impacto

Após versionar esta correção e obter worktree limpo:

1. Reexecutar a mineração **apenas de PyMC Marketing**, reutilizando o freeze
   `20260908T003854721749Z_43a2dae0_phase3_clone_repos` e o mesmo SHA do caso.
2. Produzir a execução de métricas vinculada à nova mineração; a finalidade é
   atualizar a cadeia, mesmo que os números permaneçam iguais.
3. Criar novo índice reutilizando as execuções válidas de Ultralytics e Anomalib.
   Atualizar os derivados e seus vínculos, sem refazer busca/triagem ou consultas
   históricas de PR apenas para mudar o índice.
4. Incorporar as revisões concluídas quando localizadas, documentando a
   compatibilidade/transformação dos campos de origem sem inventar julgamentos.
5. Rodar o verificador sobre o novo índice e guardar o recibo de recusa antigo.

A mineração afetada pode ser iniciada, após o commit, com:

```sh
make mine REPO=pymc-labs/pymc-marketing \
  SOURCE_RUN_ID=20260908T003854721749Z_43a2dae0_phase3_clone_repos
```

Usar o run ID emitido por esse comando como entrada explícita das métricas e do
novo índice. Não substituir hashes ou o `code_commit_sha` dos manifestos históricos.
