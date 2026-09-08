# MLOps Traceability Mining

Este repositório reúne os scripts e os dados de apoio do TCC sobre rastreabilidade
em projetos de aprendizado de máquina. O estudo acompanha mudanças de código e
configuração no histórico Git e examina como a integração com MLflow aparece nos
artefatos públicos dos projetos.

O protocolo atual é o **2.1.0**. A amostra piloto reúne Ultralytics, PyMC Marketing e
Anomalib. O Composer foi substituído na proposta após falhar no critério de atividade.
A seleção definitiva, a validação da taxonomia e a interpretação qualitativa ainda
precisam de revisão do pesquisador. O andamento e as evidências estão no
[registro dos casos](docs/INSPECAO_MANUAL_AMOSTRA.md).

## Documentação

| Documento | Conteúdo |
|---|---|
| [Método](docs/DECISOES_METODOLOGICAS.md) | Delineamento, seleção, validação, plano de análise e temas qualitativos. |
| [Casos e resultados](docs/INSPECAO_MANUAL_AMOSTRA.md) | Fontes, justificativas da amostra, execuções e pendências. |
| [Métricas](docs/GQM_MAPA_METRICAS.md) | Perguntas, fórmulas, denominadores e interpretação. |
| [Dicionário de dados](docs/DICIONARIO_DADOS.md) | Configuração, tabelas, manifestos e arquivos de revisão. |
| [Limitações](docs/LIMITACOES_E_VALIDADE.md) | Alcance das conclusões e ameaças à validade. |
| [Política de dados](data/DECISOES_DADOS.md) | Armazenamento, preservação e publicação. |

## Preparação do ambiente

São necessários Git, GNU Make, Python 3.12 e acesso à internet para as consultas ao
GitHub. O ambiente virtual fica em `.venv/`; as dependências estão nos arquivos
`requirements.txt` e `requirements-dev.txt`, com versões e hashes fixados.

```bash
uv python install 3.12
make setup
cp .env.example .env
```

Preencha `GITHUB_TOKEN` em `.env` com uma credencial de leitura dos repositórios
públicos. Os comandos de coleta carregam `.env` e `.env.local`. Esses arquivos são
locais e ignorados pelo Git.

## Execução do estudo

As execuções que compõem a cadeia científica precisam usar código e configuração
commitados, com worktree limpo. Comece pelas verificações do projeto:

```bash
make check
```

Esse comando verifica estilo, tipos, testes e o smoke test. Durante o desenvolvimento,
`make lint format-check typecheck test smoke-dev` permite verificar alterações ainda
não commitadas. `ALLOW_DIRTY=1` habilita execuções de desenvolvimento das fases do
estudo, que preservam um snapshot do instrumento e permanecem preliminares.

### Coleta e triagem

A amostra atual deriva da coleta de 31/08/2026. Seus arquivos originais devem continuar
nos caminhos registrados em `config/amostra_final.yaml`; o checkout sozinho não
contém esses insumos. Uma nova busca produziria outra observação do GitHub.

Para iniciar uma coleta independente, use:

```bash
make search
make screen
```

`make pipeline` executa `check`, `search` e `screen`, nessa ordem. As fases seguintes
são chamadas separadamente. A triagem lê a busca apontada por
`data/interim/latest/phase1_search_candidates.json` e confere a origem dos CSVs.

### Congelamento, mineração e métricas

Execute as três etapas para cada repositório em `config/amostra_final.yaml`, usando
o SHA da seleção. O exemplo abaixo mostra um caso; substitua os identificadores de
execução pelos valores apresentados no terminal.

```bash
make clone REPO=ultralytics/ultralytics
make mine REPO=ultralytics/ultralytics SOURCE_RUN_ID=RUN_FASE3
make metrics REPO=ultralytics/ultralytics SOURCE_RUN_ID=RUN_FASE4
```

As fontes são explícitas para impedir que uma execução use, por engano, o último
resultado de outro caso. Um identificador inválido interrompe o processamento.
Os clones completos são reutilizados, enquanto cada execução recebe um novo `run_id`.
O código dos projetos analisados não é executado.

### Índice e revisão

Crie um YAML com uma entrada para cada um dos três casos:

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

Os caminhos de integração dos demais casos estão em `config/casos.yaml`.

```bash
make study-index RUNS_FILE=caminho/runs.yaml
```

O índice fica em `data/interim/runs/<run_id>/study_index.json`. O mesmo diretório
contém o inventário, a amostra da taxonomia e os modelos de revisão dos casos,
alinhamento acadêmico e mapa commit–PR. Preserve os originais e preencha cópias.

Na amostra da taxonomia, o pesquisador informa `expected_category`, `reviewer` e
`reviewed_at_utc`. Caminhos com mais de uma observação histórica também exigem
`role_change_review`. A amostra contém até 20 caminhos por categoria; grupos com
menos de 20 são avaliados integralmente. A concordância mínima é 95%.

```bash
make validate-taxonomy STUDY_INDEX=caminho/study_index.json SAMPLE=caminho/taxonomia_revisada.csv INVENTORY=caminho/taxonomy_inventory.json
```

### Análise e conclusão

O mapa commit–PR precisa cobrir todos os commits elegíveis, com fonte e data da
consulta. Sem esse mapa, a seleção qualitativa é preliminar e deverá ser regenerada.
Para coletá-lo pela API do GitHub, use um diretório de saída novo:

```bash
make collect-pr-map STUDY_INDEX=caminho/study_index.json OUTPUT_DIR=data/interim/pr_maps/rodada
```

O diretório reúne `mapa_prs.json`, as respostas consultadas e `collection.json`, com
hashes e cobertura. Associações ambíguas e consultas incompletas permanecem como erro.
As regras de seleção e os temas iniciais de codificação estão no
[método](docs/DECISOES_METODOLOGICAS.md#análise-qualitativa).

```bash
make qualitative STUDY_INDEX=caminho/study_index.json PR_MAP=caminho/mapa_prs.json
make report STUDY_INDEX=caminho/study_index.json
```

A seleção gera os eventos e uma tabela de codificação vazia. O relatório reúne as
métricas por caso, as séries mensais, a distribuição de magnitude, as análises de
sensibilidade e três figuras em 300 dpi. Com a revisão concluída, execute:

```bash
make finalize-study STUDY_INDEX=caminho/study_index.json VALIDATION_RUN_ID=RUN_VALIDACAO QUALITATIVE_RUN_ID=RUN_QUALITATIVO REPORT_RUN_ID=RUN_RELATORIO CASE_REVIEW=caminho/casos_revisados.json ACADEMIC_REVIEW=caminho/alinhamento_academico.json QUALITATIVE_REVIEW=caminho/codificacao_revisada.csv
```

Os scripts de validação e finalização retornam código 1 quando os critérios de
aceite não foram atendidos, mesmo que o processamento tenha terminado. Quando
chamados pelo Make, esse encerramento aparece como código 2. O motivo está em
`taxonomy_validation.json` ou `study_acceptance.json`. O campo `processing_status`
informa o funcionamento da etapa; os demais estados registram seleção, revisão e
alinhamento acadêmico. Uma fonte de desenvolvimento mantém toda a cadeia preliminar.

Quando o estudo é aceito, a finalização produz tabelas validadas, integração
qualitativa, um rascunho de Resultados e Discussão e `reproduction.zip`, sem clones.
Esses materiais subsidiam a redação e a revisão do TCC.

## Acompanhamento e retomada

A busca e a triagem informam progresso a cada dez segundos. Após 60 segundos sem
avanço, a estimativa de término é suspensa e o estado passa a `waiting`. Os logs
ficam em `tmp/logs/<run_id>.jsonl`.

A triagem usa quatro workers e espaça as requisições em 250 ms. Um limite secundário
do GitHub pausa as consultas por 60 segundos, com até duas novas tentativas. Se o
bloqueio persistir, a execução preserva os resultados e registra os itens pendentes
como erro. A configuração desses limites fica em `config/config.yaml`.

Após uma interrupção, `make screen` retoma resultados compatíveis do cache. Para
reutilizar a última triagem e consultar novamente apenas os erros, use
`make screen-retry-errors`. A busca de origem deve ser a mesma. A compatibilidade
considera hashes das entradas, configuração, protocolo e semântica da triagem;
uma alteração operacional de código, isoladamente, não invalida o cache.
Qualquer erro remanescente impede o aceite da triagem.

## Organização e manutenção

`src/` contém o pacote Python; `scripts/`, os pontos de entrada; `config/`, o
instrumento de pesquisa; `tests/`, as verificações automatizadas. As saídas empíricas
ficam em `data/interim/runs/<run_id>/`, com manifestos em `data/processed/manifests/`.
Os ponteiros `latest` podem mudar, mas os diretórios concluídos são preservados.

Use `make preserve-runs` para migrar artefatos locais legados. Após alterar as
dependências de `pyproject.toml`, execute `make lock` e `make setup`. O comando
`make clean` remove caches e `tmp/`, incluindo logs e manifestos de smoke tests;
preserve antes qualquer arquivo necessário ao registro da pesquisa.
