# Baseline da Fase 0

Data UTC: 2026-08-30
Branch: `feat/fase-0-fundacao-reprodutivel`
Commit-base: `6739aa522e94b5ee27a8efc4c55b77e03f42a5cc`
Python: `3.12.13`
Worktree limpo: sim

O SHA acima identifica o ponto de partida da rodada. Os resultados abaixo foram obtidos
com as alterações ainda não commitadas, em um ambiente virtual recriado do zero a partir
de `requirements-dev.txt`.

## Estado funcional

- config/config.yaml criado: sim
- config/file_taxonomy.yaml criado: sim
- carregamento e validação do config implementados: sim
- taxonomia executável: sim
- manifesto de execução implementado: sim
- repositório sintético reproduzível: sim
- integração contínua configurada: sim

## Validação

- `make lint`: aprovado
- `make format-check`: aprovado
- `make typecheck`: aprovado em 11 arquivos-fonte
- `make test`: 32 testes aprovados
- cobertura: 96,93% (mínimo exigido: 90%)
- `python -m pip check`: aprovado
- `make smoke-dev`: aprovado
- `make check`: aprovado
- `CI`: aprovado

## Pendências conhecidas

- Não há pendencias

## Status
- Fase 0: encerrada