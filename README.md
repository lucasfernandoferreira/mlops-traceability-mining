# MLOps Traceability Mining

Pipeline de mineração reprodutível para estudar rastreabilidade, proveniência e
acoplamento entre código, dados e configuração em repositórios públicos de aprendizado
de máquina.

## Estado do projeto

O repositório está na Fase 0: fundação técnica e contrato metodológico. Já estão
disponíveis:

- configuração do protocolo validada por Pydantic;
- taxonomia ordenada e mutuamente exclusiva para caminhos versionados;
- manifesto de execução com hashes dos principais insumos;
- repositório Git sintético e smoke test da fundação;
- gates locais de lint, formatação, tipagem e testes.

A descoberta de candidatos, a coleta do histórico, o cálculo das métricas GQM e a
seleção da amostra final ainda não foram implementados. O arquivo
`config/amostra_final.yaml` registra esse estado como `pending` e não representa uma
amostra real.

## Requisitos

- Git;
- GNU Make;
- [`uv`](https://docs.astral.sh/uv/);
- acesso à internet para instalar o Python e as dependências na primeira execução.

O projeto aceita apenas Python 3.12 (`>=3.12,<3.13`). O ambiente virtual local fica em
`.venv/` e não deve ser versionado.

## Configuração do ambiente

Na raiz do repositório:

```bash
uv python install 3.12
make setup
```

Confirme o interpretador instalado:

```bash
.venv/bin/python --version
```

Quando as dependências declaradas em `pyproject.toml` mudarem, regenere os arquivos
travados e reinstale o ambiente:

```bash
make lock
make setup
```

Os arquivos `requirements.txt` e `requirements-dev.txt` são artefatos versionados de
reprodutibilidade. Alterações neles devem acompanhar a alteração correspondente em
`pyproject.toml`.

## Validação

Os gates podem ser executados separadamente:

```bash
make lint
make format-check
make typecheck
make test
```

O gate completo inclui também o smoke test:

```bash
make check
```

Por padrão, o smoke test exige um worktree limpo para que o manifesto aponte para um
estado reproduzível do código. Durante o desenvolvimento, é possível validar a
fundação sem relaxar essa regra para execuções oficiais:

```bash
make smoke-dev
```

Manifestos locais do smoke são escritos em `tmp/manifests/`, diretório ignorado pelo
Git.

| Alvo | Finalidade |
|---|---|
| `make bootstrap` | Cria, valida ou repara o ambiente Python 3.12 em `.venv`. |
| `make lock` | Gera locks com hashes a partir de `pyproject.toml`. |
| `make setup` | Instala dependências de desenvolvimento e o pacote editável. |
| `make lint` | Executa as regras estáticas do Ruff. |
| `make format-check` | Verifica a formatação sem alterar arquivos. |
| `make typecheck` | Executa o Mypy em modo estrito. |
| `make test` | Executa Pytest e apresenta cobertura. |
| `make smoke` | Valida configuração, taxonomia, fixture sintética e manifesto. |
| `make smoke-dev` | Executa o smoke local permitindo alterações não commitadas. |
| `make check` | Executa todos os gates da Fase 0. |

## Configuração da pesquisa

Os limiares e decisões executáveis ficam em `config/config.yaml`. As regras de
classificação ficam em `config/file_taxonomy.yaml`; como a primeira regra compatível
vence, sua ordem faz parte do protocolo.

Consultas futuras à API do GitHub usarão somente o nome da variável definido na
configuração. Crie um `.env` local a partir do exemplo e nunca versione o token:

```bash
cp .env.example .env
```

O projeto ainda não carrega `.env` automaticamente; exporte `GITHUB_TOKEN` no ambiente
do processo quando a etapa de coleta for implementada.

## Estrutura principal

```text
config/                     protocolo, taxonomia e estado da amostra
data/                       política e futuros dados da pesquisa
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
