# MLOps Traceability Mining

Pipeline de mineração reprodutível para estudar rastreabilidade, proveniência e
acoplamento entre código, dados e configuração em repositórios públicos de aprendizado
de máquina.

## Estado do projeto

O protocolo **2.1.0** incorpora o parecer de 07/09/2026. Fases 0–9 e índice do estudo
estão implementados; revisão humana, alinhamento acadêmico e redação final permanecem
pendentes. Busca/triagem 1.5.0 e piloto Ultralytics 2.0.0 são registros históricos.
A amostra de três casos MLflow continua `pilot`, sem representatividade estatística.

- [Roteiro vigente](ROTEIRO_IMPLEMENTACAO.md) e [respostas ao parecer](docs/PARECER_ORIENTADORA_E_RESPOSTAS.md).
- [Plano de análise](docs/PLANO_ANALISE.md), [casos](docs/DEFINICAO_DOS_CASOS.md), [codebook](docs/CODEBOOK_QUALITATIVO.md).
- [Entrega e pendências](docs/ENTREGA_PARECER_ORIENTADORA.md).
- [Baseline](docs/BASELINE_PARECER_ORIENTADORA.md), [GQM](docs/GQM_MAPA_METRICAS.md), [piloto histórico](docs/PILOTO_ULTRALYTICS.md).

### Executar o estudo

Preservar os insumos originais referidos em `config/amostra_final.yaml`. O checkout
sozinho não reproduz a busca de 31/08. Para runs científicos, código/configuração
commitados e worktree limpo; para desenvolvimento, adicionar `ALLOW_DIRTY=1` aos
alvos abaixo. Isso preserva snapshot e impede a promoção científica da cadeia.

```bash
make clone REPO=ultralytics/ultralytics
make mine REPO=ultralytics/ultralytics SOURCE_RUN_ID=RUN_FASE3
make metrics REPO=ultralytics/ultralytics SOURCE_RUN_ID=RUN_FASE4
```

Repetir para PyMC Marketing e Composer, sempre com os SHAs da seleção. Os scripts
04/05 aceitam `--source-run-id`; se omitido, mantêm `latest` global legado, que pode
apontar a outro caso e será rejeitado. Os wrappers exigem fontes explícitas. Um run
solicitado inexistente/incompatível nunca é substituído por outro. Os novos artefatos
usam caminhos relativos; a regra de leitura legada está no dicionário de dados.

Criar um YAML com os três casos (o exemplo mostra o formato de uma entrada):

```yaml
cases:
  - repository_id: ultralytics/ultralytics
    head_commit_sha: fa34184a5080c81fff453670394e13303ac781b2
    runs:
      freeze: RUN_FASE3
      mine: RUN_FASE4
      metrics: RUN_FASE5
    integration_paths:
      - ultralytics/engine/trainer.py
      - ultralytics/utils/callbacks/base.py
      - ultralytics/utils/callbacks/mlflow.py
```

Caminhos confirmados e contexto técnico: `config/casos.yaml`. Registrar alterações
nessa delimitação antes da seleção qualitativa; fontes diferentes geram novo índice.

```bash
make study-index RUNS_FILE=caminho/runs.yaml
make validate-taxonomy STUDY_INDEX=caminho/study_index.json SAMPLE=caminho/revisada.csv INVENTORY=caminho/taxonomy_inventory.json
make qualitative STUDY_INDEX=caminho/study_index.json
make report STUDY_INDEX=caminho/study_index.json
make finalize-study STUDY_INDEX=caminho/study_index.json VALIDATION_RUN_ID=RUN_VALIDACAO QUALITATIVE_RUN_ID=RUN_QUALITATIVO REPORT_RUN_ID=RUN_RELATORIO CASE_REVIEW=caminho/casos_revisados.json ACADEMIC_REVIEW=caminho/alinhamento.json QUALITATIVE_REVIEW=caminho/codificacao_revisada.csv
```

O índice é gerado em `data/interim/runs/<run_id>/study_index.json`; não editar seus
bytes. Inclui inventário histórico consolidado, amostra original e modelos de fichas,
alinhamento e mapa commit–PR. Preencher **cópias**: expected_category, reviewer,
reviewed_at_utc em UTC e role_change_review para caminhos com observações históricas
múltiplas. Rótulos da IA não são avaliação humana. Cota global por categoria: 20;
1–19 = censo; zero em universo completo = ausência registrada, sem validação empírica
da categoria. Inventário incompleto e concordância abaixo de 95% bloqueiam o aceite.

`PR_MAP=caminho/mapa.json` permite mapa manual verificável para `make qualitative`.
O modelo cobre todos os commits elegíveis. Presença/ausência de PR requer URL pública,
responsável e data; not_collected e error não são pr_not_found. Sem mapa completo,
a seleção é preliminar por commit e precisa ser regenerada quando o mapa for concluído.
A codificação nasce vazia e segue o codebook; nenhuma interpretação humana é inventada.

Cada entrega salva manifesto e hashes, inclusive revisão rejeitada. O validador e a
finalização retornam código 1 quando o processamento terminou mas o aceite foi
bloqueado; consultar `taxonomy_validation.json`/`study_acceptance.json` e execution.json.
`processing_status`, `sample_status`, `measurement_validation_status` e
`academic_alignment_status` são distintos. status: final isolado não aprova o estudo.
Uma execução limpa com fonte de desenvolvimento continua inelegível cientificamente.

O relatório produz tabelas reconciliadas, sensibilidade de magnitude e três figuras
300 dpi. A finalização aceita gera nova tabela validada, integração qualitativa,
rascunho de Resultados/Discussão e `reproduction.zip` com hashes e sem clones. A redação
autoral e sua revisão acadêmica continuam responsabilidades do pesquisador.
Nenhum treinamento dos projetos externos é executado. `make pipeline` cobre apenas
check, busca e triagem; não executa todo o estudo.

## Requisitos

- Git;
- GNU Make;
- [`uv`](https://docs.astral.sh/uv/);
- acesso à internet;
- token do GitHub com acesso de leitura a repositórios públicos.

O projeto aceita Python 3.12 (`>=3.12,<3.13`). O ambiente virtual local fica em
`.venv/` e não é versionado.

## Preparação

Na raiz do repositório, instale o Python e as dependências:

```bash
uv python install 3.12
make setup
```

Crie o arquivo local de credenciais:

```bash
cp .env.example .env
```

Preencha `GITHUB_TOKEN` em `.env`. Os alvos `search` e `screen` carregam `.env` e
`.env.local` automaticamente. Esses arquivos são ignorados pelo Git; o token não deve
aparecer em commits, logs ou comandos versionados.

## Ordem de execução

O padrão recomendado para uma execução científica é trabalhar com o código commitado
e o worktree limpo, então executar:

```bash
make check
make search
make screen
```

O mesmo fluxo pode ser iniciado sequencialmente com:

```bash
make pipeline
```

O encadeamento é:

```text
Fase 0 / check
    -> Fase 1 / search
        -> candidatos_brutos.csv + evidencias_busca.csv
            -> Fase 2 / screen
                -> funil_amostral.csv + shortlist.csv
```

`make screen` não repete a busca. Ele resolve os CSVs pelo ponteiro
`data/interim/latest/phase1_search_candidates.json` e valida se ambos pertencem ao
mesmo `run_id` de origem.

## Observabilidade

Durante a execução, o terminal informa:

- etapa, consulta, página ou último repositório concluído;
- itens concluídos e percentual;
- elegíveis, rejeitados e erros na triagem;
- tempo decorrido, itens por minuto, tempo desde o último avanço e ETA;
- estado do rate limit, workers bloqueados e duração restante do cooldown;
- abertura do circuito quando o GitHub continua bloqueando após os retries configurados;
- caminho do log estruturado da execução.

Os logs completos ficam em `tmp/logs/<run_id>.jsonl`, diretório ignorado pelo Git. O
heartbeat padrão é emitido a cada 10 segundos, inclusive quando não há novo candidato
concluído. Após 60 segundos sem avanço, o status muda para `waiting`, o campo `stalled`
fica verdadeiro e a ETA passa a `indisponivel`, evitando previsões enganosas durante
esperas externas.

A Fase 2 usa quatro workers por padrão. Esse valor e o intervalo do heartbeat ficam em
`config/config.yaml`:

```yaml
execution:
  screening_workers: 4
  progress_interval_seconds: 10
  progress_stall_threshold_seconds: 60
```

As requisições dos workers passam por um coordenador único. Por padrão, seus inícios são
espaçados em 250 ms; um limite secundário pausa todos os workers por 60 segundos e
permite no máximo dois retries. Se o bloqueio persistir, o circuito abre, os candidatos
pendentes são registrados como `error` e a execução termina normalmente para permitir
reprocessamento posterior, em vez de aguardar indefinidamente. Esses valores podem ser
explicitados em `github.rate_limit` quando necessário:

```yaml
github:
  rate_limit:
    request_interval_seconds: 0.25
    secondary_cooldown_seconds: 60
    secondary_max_retries: 2
    max_rate_limit_wait_seconds: 300
```

Mais workers não garantem menor duração porque a API do GitHub impõe cotas. O
paralelismo continua útil para o processamento local, mas não cria rajadas simultâneas
de chamadas HTTP.

## Cache, interrupção e retry

A Fase 2 grava cada candidato concluído em um cache identificado pela versão da
semântica de triagem, configuração e hashes das entradas em
`data/interim/cache/phase2/`. Se o processo for interrompido, execute novamente:

```bash
make screen
```

O cache só é reutilizado quando o `run_id` da Fase 1, os hashes das entradas, a versão
do protocolo, a configuração e a versão da semântica científica continuam compatíveis.
Mudanças operacionais de código não invalidam resultados concluídos; caches legados são
migrados automaticamente. Alterações nos critérios de decisão exigem incrementar a
versão semântica. Resultados com decisão `error` nunca são reutilizados; uma nova
execução consulta apenas esses erros e itens ainda ausentes.

`Ctrl+C` solicita cancelamento cooperativo, acorda workers em cooldown e cancela itens
que ainda não começaram. Depois que o comando encerrar, `make screen` retoma o cache.

Para importar os resultados válidos da última Fase 2 e reprocessar somente seus erros:

```bash
make screen-retry-errors
```

Esse modo exige que a Fase 2 anterior e a entrada `latest` da Fase 1 compartilhem o
mesmo `source_run_id`. Árvores Git truncadas usam fallback dirigido pelos caminhos de
evidência encontrados na Fase 1.

Qualquer erro na triagem deixa o resumo, o manifesto e o ponteiro da execução com
status `FAILED`, mesmo com shortlist suficiente e todos os estratos requeridos presentes.
O gate `errors_absent` só passa quando todos os erros forem resolvidos. Os CSVs
parciais são preservados, e um retry ainda com erros permanece reprovado.

Antes de reutilizar uma busca, confira manifesto `SUCCESS`, worktree de origem
limpo, no mínimo 300 candidatos únicos, hashes, configuração e `run_id` comum nos
CSVs de candidatos e evidências. Não presuma compatibilidade depois de editar o
protocolo: inclusive explicitar defaults no YAML altera seu hash e o cache.

## Artefatos

| Fase | Artefato | Finalidade |
|---|---|---|
| 0 | `tmp/manifests/<run_id>.json` | Evidência local do smoke test. |
| 1 | `data/interim/runs/<run_id>/candidatos_brutos.csv` | Repositórios deduplicados por ID numérico. |
| 1 | `data/interim/runs/<run_id>/evidencias_busca.csv` | Evidências por consulta, página e arquivo. |
| 1 | `data/interim/runs/<run_id>/resumo_busca.csv` | Cobertura, truncamento e totais por consulta. |
| 1 | `data/interim/runs/<run_id>/resumo_execucao_fase1.json` | Resumo e hashes da coleta. |
| 2 | `data/interim/runs/<run_id>/funil_amostral.csv` | Decisão e motivo para cada candidato. |
| 2 | `data/interim/runs/<run_id>/shortlist.csv` | Repositórios elegíveis para inspeção manual. |
| 2 | `data/interim/runs/<run_id>/resumo_execucao_fase2.json` | Gates, descartes e distribuição por estrato. |
| 1 e 2 | `data/interim/latest/<stage>.json` | Ponteiro para a última execução da etapa. |
| 1 e 2 | `data/processed/manifests/<run_id>.json` | Proveniência da execução e hashes dos artefatos. |

`data/interim/`, `tmp/` e os manifestos locais são ignorados pelo Git. Assim, executar o
pipeline não deixa o worktree sujo. O requisito de worktree limpo continua protegendo
execuções oficiais contra mudanças de código ou configuração ainda não commitadas. Um
manifesto destinado a publicação deve ser revisado e incluído explicitamente com
`git add -f`.

## Validação e desenvolvimento

Os gates podem ser executados separadamente:

```bash
make lint
make format-check
make typecheck
make test
```

`make check` executa todos os gates e o smoke oficial, que exige worktree limpo. Durante
o desenvolvimento, use o smoke que permite alterações locais:

```bash
make smoke-dev
```

Quando as dependências declaradas em `pyproject.toml` mudarem:

```bash
make lock
make setup
```

## Alvos principais

| Alvo | Finalidade |
|---|---|
| `make bootstrap` | Cria, valida ou repara o ambiente Python 3.12. |
| `make setup` | Instala dependências e o pacote editável. |
| `make check` | Executa lint, formato, tipos, testes e smoke oficial. |
| `make smoke-dev` | Executa o smoke permitindo alterações locais. |
| `make search` | Executa a descoberta paginada da Fase 1. |
| `make screen` | Executa ou retoma a triagem paralela da Fase 2. |
| `make screen-retry-errors` | Reutiliza decisões válidas e reprocessa apenas erros. |
| `make preserve-runs` | Migra artefatos legados para diretórios imutáveis por `run_id`. |
| `make pipeline` | Executa `check`, `search` e `screen` em ordem. |
| `make clean` | Remove caches, cobertura e arquivos temporários. |

## Estrutura e método

```text
config/                     protocolo, taxonomia e estado da amostra
data/                       política e dados locais reconstruíveis
docs/                       decisões, métricas, dicionário e limitações
scripts/                    pontos de entrada executáveis
src/mlops_traceability/     pacote Python
tests/                      testes automatizados
```

As definições metodológicas complementares estão em:

- `docs/DECISOES_METODOLOGICAS.md`;
- `docs/GQM_MAPA_METRICAS.md`;
- `docs/DICIONARIO_DADOS.md`;
- `docs/LIMITACOES_E_VALIDADE.md`;
- `data/DECISOES_DADOS.md`.
