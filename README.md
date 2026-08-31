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
- a Fase 2 usa paralelismo limitado, ETA e checkpoint para retomada após interrupções.

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

`make screen` não repete a busca. Ele exige os CSVs produzidos por um `make search`
anterior e valida se ambos pertencem ao mesmo `run_id` de origem.

## Observabilidade

Durante a execução, o terminal informa:

- etapa, consulta, página ou último repositório concluído;
- itens concluídos e percentual;
- elegíveis, rejeitados e erros na triagem;
- tempo decorrido, itens por minuto e ETA;
- início e duração prevista de espera por rate limit;
- caminho do log estruturado da execução.

Os logs completos ficam em `tmp/logs/<run_id>.jsonl`, diretório ignorado pelo Git. O
heartbeat padrão é emitido a cada 10 segundos, inclusive quando não há novo candidato
concluído. No começo da execução o ETA aparece como `calculando` e pode oscilar até que
haja uma amostra representativa de itens processados.

A Fase 2 usa quatro workers por padrão. Esse valor e o intervalo do heartbeat ficam em
`config/config.yaml`:

```yaml
execution:
  screening_workers: 4
  progress_interval_seconds: 10
```

Mais workers não garantem menor duração porque a API do GitHub impõe cotas. Valores
acima do padrão devem ser avaliados junto com os eventos de rate limit e a taxa de
erros, sem alterar a configuração durante uma execução oficial.

## Interrupção e retomada

A Fase 2 grava cada candidato concluído em
`data/interim/.phase2_screen_checkpoint.jsonl`. Se o processo for interrompido, execute
novamente:

```bash
make screen
```

O checkpoint só é reutilizado quando o `run_id` da Fase 1, os hashes das entradas, a
versão do protocolo, a configuração e o SHA do código continuam compatíveis. O terminal
informa quantos candidatos foram recuperados e quantos ainda faltam. Depois da
consolidação completa, o checkpoint é removido automaticamente, mesmo que os gates da
shortlist não sejam satisfeitos.

Para descartar deliberadamente uma execução parcial e reiniciar a triagem do zero:

```bash
rm -f data/interim/.phase2_screen_checkpoint.jsonl
make screen
```

## Artefatos

| Fase | Artefato | Finalidade |
|---|---|---|
| 0 | `tmp/manifests/<run_id>.json` | Evidência local do smoke test. |
| 1 | `data/interim/candidatos_brutos.csv` | Repositórios deduplicados por ID numérico. |
| 1 | `data/interim/evidencias_busca.csv` | Evidências por consulta, página e arquivo. |
| 1 | `data/interim/resumo_busca.csv` | Cobertura, truncamento e totais por consulta. |
| 1 | `data/interim/resumo_execucao_fase1.json` | Resumo e hashes da coleta. |
| 2 | `data/interim/funil_amostral.csv` | Decisão e motivo para cada candidato. |
| 2 | `data/interim/shortlist.csv` | Repositórios elegíveis para inspeção manual. |
| 2 | `data/interim/resumo_execucao_fase2.json` | Gates, descartes e distribuição por estrato. |
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
