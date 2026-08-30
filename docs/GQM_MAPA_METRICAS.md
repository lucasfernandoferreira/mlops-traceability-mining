# Mapa GQM e contrato das métricas

Este documento traduz os objetivos da pesquisa em perguntas e métricas. As funções
citadas são nomes planejados para a etapa de mineração; ainda não estão implementadas.

## Convenções

Para cada commit elegível:

- `C`: alterou ao menos um arquivo `CODE` ou `NOTEBOOK`;
- `D`: alterou ao menos um arquivo `DATA_META`;
- `P`: alterou ao menos um arquivo `CONFIG`.

Commits de merge, bots e commits acima do limite de arquivos seguem as exclusões de
`config/config.yaml`. Uma interseção representa coalteração no mesmo commit, não uma
relação causal.

Os resultados devem separar `value` de `status`:

| Status | Uso |
|---|---|
| `observed` | Há evidência e o valor foi calculado. |
| `not_available` | A evidência necessária não é pública ou não foi coletada. |
| `not_applicable` | A métrica não se aplica ao caso analisado. |
| `undefined` | O universo é aplicável, mas o denominador elegível é zero. |
| `error` | A coleta ou o cálculo falhou; não é um resultado científico. |

Somente `observed` carrega valor numérico. O valor zero é válido quando o denominador é
positivo e nenhum evento satisfaz o numerador.

## Objetivo 1 — Avaliar a rastreabilidade entre artefatos

### GQM 1.1 — Qual parcela das versões de modelos possui proveniência recuperável?

`provenance_coverage`

```text
versões de modelo com vínculo verificável a código, dados e execução
--------------------------------------------------------------------
versões de modelo observadas
```

- Unidade: repositório e período analisado.
- Escala: proporção entre 0 e 1.
- Estado especial: `not_available` se as versões ou seus vínculos não forem públicos;
  `undefined` se a fonte for observável, mas não contiver versões no período.

### GQM 1.2 — Com que frequência mudanças de código acompanham mudanças de dados?

`data_code_coupling`

```text
commits elegíveis em C ∩ D
-------------------------
commits elegíveis em C
```

- Unidade: repositório e período analisado.
- Escala: proporção entre 0 e 1.
- Estado especial: `undefined` quando não houver commits em `C`.

## Objetivo 2 — Caracterizar o acoplamento de configuração

### GQM 2.1 — Qual a incidência de coalterações entre código, dados e parâmetros?

`cace_index`

```text
commits elegíveis em C ∩ D ∩ P
-----------------------------
commits elegíveis em C ∪ D ∪ P
```

- Unidade: repositório e período analisado.
- Escala: proporção entre 0 e 1.
- Estado especial: `undefined` quando a união não contiver commits.

O nome da função é mantido por compatibilidade com o plano de pesquisa; a interpretação
operacional é a proporção de commits triplos no universo das três dimensões.

### GQM 2.2 — Qual a magnitude das alterações de configuração?

`config_magnitude`

```text
chaves de configuração adicionadas, removidas ou alteradas
----------------------------------------------------------
commits elegíveis que alteram CONFIG
```

- Unidade: repositório e período analisado.
- Escala: média de chaves alteradas por commit de configuração.
- Estado especial: `undefined` quando não houver commits em `P`; `not_applicable` para
  formatos sem parser semântico definido.
- Regra de contagem: uma chave é identificada por seu caminho hierárquico normalizado;
  alteração de valor conta uma vez no commit.

## Objetivo 3 — Avaliar a reprodutibilidade de experimentos e modelos

### GQM 3.1 — Em que proporção as execuções registram o ambiente?

`env_versioning_rate`

```text
runs com referência recuperável a dependências ou imagem de ambiente
--------------------------------------------------------------------
runs observadas
```

- Unidade: repositório e período analisado.
- Escala: proporção entre 0 e 1.
- Estado especial: `not_available` quando as runs não forem públicas; `undefined` se a
  fonte for observável, mas não houver runs no período.

### GQM 3.2 — Quantas execuções antecedem cada modelo promovido?

`experiment_redundancy`

```text
runs observadas vinculadas a modelos promovidos
-----------------------------------------------
versões de modelo promovidas observadas
```

- Unidade: repositório e período analisado.
- Escala: razão não negativa; valores acima de 1 são esperados.
- Estado especial: `not_available` quando runs ou promoções não forem públicas;
  `undefined` quando a fonte for observável e não houver modelos promovidos.

## Campos mínimos do resultado

Cada resultado deve registrar, no mínimo: `repository_id`, `metric_id`, início e fim do
período UTC, `value`, `status`, numerador, denominador, quantidade de commits excluídos,
versão do protocolo, versão da taxonomia e `run_id` do manifesto. A ausência de valor
deve ser explicada em `status_detail`.
