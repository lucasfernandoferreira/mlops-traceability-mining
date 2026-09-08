# Critérios de aceite e evidências — primeiro incremento

Política de verificação **1.0.0**, separada do protocolo científico **2.1.0**,
da taxonomia **1.1.0** e do plano de análise **1.0.0**. O arquivo
`config/config.yaml`, a taxonomia e os locks da coleta foram preservados sem alterações.
Este incremento implementa a primeira entrega indicada no plano de 08/09/2026.
**Não é um parecer de aprovação G00–G15.**

## Entrega executada

O baseline corresponde a `a0a8de1f94b9307b03ad364d0d5b9d481f21202e`, com worktree
limpo antes das alterações. `make check` passou com 140 testes e cobertura de 93,07%.
Os 14 manifestos da rodada documentada e suas cadeias foram conferidos com o
verificador original. O relatório está em [baseline_verificacao.json](evidencias/baseline_verificacao.json).

A preservação local está em `data/interim/verification/baseline_20260908/`:

| Arquivo | Conteúdo e verificação |
|---|---|
| `baseline_verificacao.json` | SHA real, resultado anterior, executores, hashes e pendências. |
| `make_check.log` | Saída integral dos gates antes das alterações. |
| `inventario_preservacao.json` | Caminhos, tamanhos e hashes dos insumos disponíveis. |
| `insumos.tar.gz` | Busca, triagem, caches, Parquets, inventários, PRs, revisões locais, manifestos e snapshots; membros confrontados com os hashes. |
| `instrumentos.bundle` | Objetos Git do instrumento, com referências `refs/preservation/verification-baseline/<sha>`. |
| `restored_instrument.git/` | Recuperação do bundle em outro banco de objetos, com todos os executores conferidos, inclusive `43a2dae0804ed3a2e0f2ec1c64dd02386d956a35`. |
| `git_sources.tar` | Cópia dos clones bare locais, incluindo o histórico de Composer; checksum registrado no baseline. |
| `plano_recebido.txt` | Plano fornecido, preservado com hash. |

Esses arquivos são locais e ignorados pelo Git. O checksum e a restauração do
instrumento não representam a reprodução isolada do estudo exigida em G14.

## Revisões humanas

Os arquivos examinados em `data/interim/reviews/trio_20260908T003438Z/` ainda contêm
campos humanos vazios: 180 unidades de taxonomia, 45 eventos qualitativos e três
casos. O alinhamento também está pendente nesses arquivos. Isso descreve os bytes
locais, **não contradiz a informação do pesquisador de que a revisão foi realizada**.
A localização dos arquivos preenchidos permanece necessária; não se pede a repetição
da revisão nem se completam responsável, julgamento ou data por inferência.

A execução local foi registrada em
[importacao_revisoes_inicial.json](evidencias/importacao_revisoes_inicial.json),
que referencia o recibo integral em
`data/interim/verification/importacao_local_20260908_02/review_import.json`.
O resultado foi `FAIL`, código 1, com pendências discriminadas; as cópias preservadas
e os vínculos de hashes foram reconferidos após a importação.

O importador exige índice, diretório de revisão e destino novo:

```sh
make import-reviews \
  STUDY_INDEX=data/interim/runs/20260908T004303820864Z_43a2dae0_study_index/study_index.json \
  REVIEW_DIR=data/interim/reviews/trio_20260908T003438Z \
  OUTPUT_DIR=data/interim/verification/importacao_revisoes_01
```

Arquivos de entrada: `origens.json`, `taxonomia_revisada.csv`, `casos_revisados.json`,
`codificacao_revisada.csv` e `alinhamento_academico.json`. O formato `origens.json`
já existe no pacote de revisão: identifica o índice, a execução qualitativa e os
caminhos/hashes dos modelos originais. Estes são resolvidos nos manifestos e devem
pertencer à mesma rodada. Não há inferência de `latest`.

O destino contém cópias byte a byte em `original_reviews/`, um snapshot recuperável
do código efetivamente usado (inclusive alterações locais), e `review_import.json`.
O recibo registra origem, hashes, contagens, erros por unidade/campo, matrizes e
limitações. Destinos existentes são recusados. Códigos de saída do script: **0** para
registros válidos no escopo da importação, **1** para decisões incompletas/divergentes,
**2** para entradas ausentes/incompatíveis. O GNU Make pode representar qualquer
falha de receita por seu próprio código 2; o código específico consta no recibo.

A importação não aprova o estudo: `scientific_result_accepted` permanece `false`,
mesmo quando `review_import_status` é `PASS`. A pertinência das evidências, a
identidade autêntica do revisor e a aprovação acadêmica não são certificadas pelo
preenchimento. Ausências de ambiguidade ou contraprova podem ser declaradas com seu
escopo; o software não exige inventar uma ocorrência.

Os seis temas iniciais foram transcritos do codebook em
[Decisões metodológicas](DECISOES_METODOLOGICAS.md). Temas emergentes podem ser
fornecidos em `temas_emergentes.json`, preservado e vinculado ao recibo:

```json
[
  {
    "theme_id": "identificador_novo",
    "definition": "Definição elaborada pelo pesquisador",
    "reviewer": "Responsável real pelo registro",
    "registered_at_utc": "2026-09-08T12:00:00Z"
  }
]
```

O exemplo é apenas um formato, não uma decisão humana registrada. A definição,
responsável e data UTC são obrigatórios; temas iniciais não podem ser sobrescritos.
A validação da taxonomia agora exige `justification`, inclusive no comando antigo
`validate-taxonomy`. As fixtures antigas foram ajustadas com justificativas sintéticas
explícitas. Nenhuma revisão real foi alterada.

## Matriz de critérios e afirmações

A [matriz processável](evidencias/matriz_criterios_inicial.json) enumera G00–G15 sem
promover o incremento a aceite empírico. O [catálogo inicial](evidencias/catalogo_afirmacoes_inicial.json)
registra seis referências históricas de C/P e magnitude por caso, com índice,
SHA, fontes, denominadores e limites. Seus estados são `not_assessed` e seus
resultados observados são nulos até a dupla conferência. Os valores históricos
não são gabaritos para ajustar a coleta. O pesquisador ainda precisa delimitar e
complementar as afirmações centrais do manuscrito.

| Critérios | Implementado neste incremento | Trabalho necessário ao aceite |
|---|---|---|
| G00 | Baseline, hashes dos insumos disponíveis, backup dos clones e recuperação dos executores. | Localizar/preservar as origens da revisão concluída. |
| G01 | Importação imutável, identidades, datas UTC, justificativas, codebook e matriz SQL. | Incorporar arquivos preenchidos e resolver as lacunas discriminadas. |
| G02 | Contrato e catálogo inicial de afirmações, separado dos estados GQM. | Revisão autoral e fontes de todas as afirmações centrais. |
| G03–G04 | Oráculo aritmético, matriz SQL, fixture Git A–D, contratos e contraprovas iniciais. | Oráculos de fonte/semântica e todas as demais mutações do plano. |
| G05–G10 | Fontes históricas preservadas. | Dupla conferência empírica de histórico, atividade, taxonomia, métricas, estatística e seleção. |
| G11 | Resolvedor offline de arquivo e blob histórico com SHA, hash e trecho. | Aplicá-lo às fontes citadas; preservar discussões de PR e documentar pertinência. |
| G12 | Registro do alinhamento pode ser importado sem inventar aprovação. | Decisão acadêmica e revisão do alcance das conclusões. |
| G13 | Agregação recusa critério ausente, duplicado, sem prova ou inaplicável sem política. | Integrar recibo empírico à finalização, preservando os gates atuais. |
| G14–G15 | Insumos e código preservados. | Pacote candidato, manuscrito, restauração isolada e parecer agregado externo. |

Os contratos não resolvem as provas automaticamente. A função de agregação só
combina estados e cobertura; o futuro runner deve conferir fontes e vínculos antes
de utilizá-la. `check_import_bindings` detecta alteração dos arquivos vinculados e
não autentica o recibo nem substitui reavaliação. Os estados de indisponibilidade
GQM continuam intactos; um `NOT_RUN` obrigatório bloqueia a agregação.

## Testes e limites de independência

A [checagem final](evidencias/validacao_verificacao.txt) passou com **179 testes**,
**93,91% de cobertura**, lint, formatação, mypy e `smoke-dev`. Os subconjuntos
passaram com 26 testes rápidos e 13 contraprovas. Os comandos, hashes e limites
estão em [verificacao_incremento_01.json](evidencias/verificacao_incremento_01.json).

```sh
make test-evidence
make test-counterexamples
make lint format-check typecheck test smoke-dev
```

Os dois primeiros alvos usam somente fixtures locais, sem GitHub e sem aceite
empírico. Os novos testes também entram em `make check` pela descoberta normal do
pytest. A suíte completa mantém o piso global de cobertura de 90%; os alvos
selecionados usam `--no-cov` para não aplicar esse piso a um subconjunto.
`make check` continua exigindo worktree limpo; durante as alterações utiliza-se
`smoke-dev`, sem criar commit só para contornar esse requisito.

O fixture adicional tem A (CODE+CONFIG, duas chaves), B (CODE), C (comentário CONFIG,
zero chaves) e D (documentação), mais bot e merge excluídos. Os valores esperados
foram escritos manualmente: C=2, P=2, C∩P=1, C/P=1/2 e magnitude=2/2. Os testes
confrontam o minerador com esse resultado e com o oráculo separado. Há rejeição de
SHA duplicado, denominador adulterado, exclusão da CONFIG de magnitude zero,
indisponibilidade convertida em zero, revisão de outra rodada, justificativa vazia,
blob trocado e tentativa de aprovação com critérios faltantes. Mutações usam
somente cópias temporárias e exigem o motivo de falha esperado.

O oráculo aritmético não importa métricas, mineração, seleção ou diff produtivos.
A matriz de rótulos usa SQLite, separado do `Counter` do instrumento. Ambos leem
tabelas que ainda precisam ser confrontadas com Git: podem detectar divergência
aritmética, mas não confirmar sozinhos uma extração errada. O resolvedor usa Git
CLI; GitPython também depende de Git. Essa dependência comum é explícita.
Contagens/componentes inteiros são exatos e floats usam tolerância absoluta de
`1e-12`, sem arredondamento editorial.

Os comandos `verify-study`, `evidence-pack` e `reproduce-study` e a integração do
novo recibo com a finalização pertencem ao próximo incremento. Este documento não
os apresenta como disponíveis. O próximo trabalho técnico é implementar os
oráculos empíricos e sua orquestração, mantendo toda reprovação recuperável.
