# MLOps Traceability Mining

Pipeline de mineração reprodutível para estudar rastreabilidade, proveniência e
acoplamento entre código, dados e configuração em repositórios públicos de aprendizado
de máquina.

## Estado do projeto

As Fases 0, 1 e 2 estão executáveis:

- a Fase 0 valida configuração, taxonomia, ambiente e repositório sintético;
- a Fase 1 pesquisa, pagina e deduplica candidatos encontrados no GitHub;
- a Fase 2 confirma critérios de elegibilidade e produz o funil e a shortlist;
- todas as fases emitem eventos no terminal e logs JSONL locais;
- a Fase 2 usa paralelismo limitado, requisições coordenadas, circuit breaker, cache
  persistente e retomada após interrupções.

A coleta detalhada do histórico, o cálculo das métricas GQM e a seleção final da
amostra ainda não foram implementados. `config/amostra_final.yaml` permanece com
status `pending` e não representa uma amostra real.

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
