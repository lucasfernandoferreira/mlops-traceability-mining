# Baseline da Fase 0

Data UTC: 2026-08-30
Branch: `feat/fase-0-fundacao-reprodutivel`
Commit-base: `4460200e5a298fc0e787c2bd73cff914b4c3ce47`
Python: `3.12.13`
Worktree limpo: não — ajustes da Fase 0 aguardando commits atômicos

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

## Pendências conhecidas

- `make smoke` exige um worktree limpo por projeto e deve ser executado novamente depois
  dos commits atômicos.
- não há falhas funcionais conhecidas nesta baseline.
