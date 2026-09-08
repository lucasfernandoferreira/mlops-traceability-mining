# Perguntas e métricas

As medidas do protocolo 2.1.0 descrevem o histórico dos casos e a instrumentação
MLflow visível no código. O caso é a unidade de comparação; o commit elegível é a
observação temporal. A análise cobre todos os ancestrais do SHA selecionado, desde
a origem do repositório, com datas de commit em UTC.

## Dimensões e denominadores

C indica mudança em CODE ou NOTEBOOK; P indica mudança em CONFIG. A dimensão D
exigiria artefatos cujo papel como dados fosse validado. A categoria DATA_META,
restrita a DVC, não satisfaz essa condição para o recorte MLflow. `C_only` designa
commits cujas mudanças são exclusivamente CODE ou NOTEBOOK.

Merges, bots e commits com mais de 1.000 arquivos são excluídos nessa ordem. As
contagens de descarte acompanham os resultados. A data de corte da atividade serve
à seleção do caso e não reduz o período das métricas.

## Relação com as perguntas da pesquisa

| Pergunta / identificador | Fórmula | Unidade / escala | Fonte e denominador | Ausência |
|---|---|---|---|---|
| GQM 1.1: versões com proveniência? `provenance_coverage` | versões com vínculo verificável a código, dados e run / versões observadas | proporção [0,1] | Fonte pública de versões e vínculos; todas as versões no período | `not_available` sem fonte; `undefined` sem versões |
| GQM 1.2.1 original: frequência relativa de dados e código exclusivo? `data_code_ratio_original` | commits D / commits C_only | razão não limitada a 1 | Histórico e dimensão D validada; commits exclusivamente de código | `not_available` sem D validada; `undefined` sem C_only |
| GQM 1.2 complementar: código acompanha dados? `data_code_cochange` | commits C ∩ D / commits C | proporção [0,1] | Histórico e D validada; commits C | `not_available` sem D validada; `undefined` sem C |
| GQM 2.1 original operacional: coalteração tripla? `cace_index` | commits C ∩ D ∩ P / commits C ∪ D ∪ P | proporção [0,1] | Histórico e D validada; união das dimensões | `not_available` sem D validada; `undefined` sem união |
| GQM 2.1 complementar prioritária: código acompanha configuração? `code_config_cochange` | commits C ∩ P / commits C | proporção [0,1] | `commits.parquet`, elegíveis com C | `undefined` sem C |
| GQM 2.2: magnitude de configuração? `config_magnitude` | soma das chaves alteradas / commits P | chaves por commit CONFIG | `changes.parquet`, todos os commits P, inclusive mudanças só de comentários | `undefined` sem P; `not_applicable` se formato não suportado; `error` se qualquer parser falhar |
| GQM 3.1: ambiente recuperável? `env_versioning_rate` | runs com dependências/imagem recuperável / runs observadas | proporção [0,1] | Fonte pública de runs; todas as runs no período | `not_available` sem fonte; `undefined` sem runs |
| GQM 3.2.1 original: runs por promoção? `experiment_redundancy` | todas as runs registradas no universo / versões promovidas observadas no mesmo universo | runs por versão promovida, razão >=0 | Tracking + registry públicos; todas as promoções no período | `not_available` sem fontes; `undefined` sem promoções |

A magnitude CONFIG é calculável nas fontes atuais. Coalteração C/P é uma medida
complementar, mas não responde à dimensão de dados do CACE. Proveniência, ambiente
de runs e promoções dependem de fontes ainda não ingeridas. As perguntas afetadas
permanecem visíveis na tabela, com `not_available`, e precisam constar no
alinhamento acadêmico do recorte.

`experiment_redundancy` mantém todas as runs no numerador, inclusive as sem vínculo
com promoção. Mesmo com fontes completas, a razão não determina quantas tentativas
causaram uma promoção. A antiga denominação `data_code_coupling` foi desdobrada em
`data_code_ratio_original` e `data_code_cochange`, pois razão de frequências e
proporção de coalteração têm interpretações diferentes.

## Magnitude de configuração

YAML/YML, MLproject, JSON e TOML são lidos por parsers estruturados. As folhas são
representadas por caminhos com tipos, permitindo distinguir uma chave numérica de
uma chave textual. Contam-se adições, remoções e alterações de valor por arquivo e
commit. Mudanças apenas de comentário podem produzir zero chaves e continuam no
denominador dos commits CONFIG.

Renomeações contam como remoção e adição na medida principal. Por isso, movimentos
de diretório e grandes mapas de classes podem concentrar a soma sem representar
ajustes de hiperparâmetros. Média, quantis, concentração e variantes de sensibilidade
seguem o [plano de análise](DECISOES_METODOLOGICAS.md#análise-quantitativa).

Chaves duplicadas, aliases recursivos, bytes inválidos e sintaxe inválida produzem
erro. Um erro impede o cálculo integral da magnitude; os arquivos bem-sucedidos não
são usados para fabricar uma média parcial. A leitura YAML segue o SafeLoader do
PyYAML, cuja resolução de escalares pode diferir da aplicação analisada.

## Instrumentação estática

| Identificador | Numerador | Denominador / unidade |
|---|---|---|
| `static_mlflow_param_calls` | posições sintáticas `log_param` e `log_params` | 1 / posições no SHA |
| `static_mlflow_metric_calls` | posições `log_metric` e `log_metrics` | 1 / posições no SHA |
| `static_mlflow_artifact_calls` | posições `log_artifact` e `log_artifacts` | 1 / posições no SHA |
| `static_mlflow_model_calls` | posições `log_model` e `register_model` | 1 / posições no SHA |

A fonte é a árvore sintática dos arquivos Python classificados como CODE no SHA
congelado. Uma posição conta uma vez, independentemente de loops ou de quantas
vezes o programa poderia ser executado. `tree_inspection.json` preserva também os
candidatos encontrados nas outras categorias, suas linhas, URLs e hashes.

O parser reconhece imports diretos e aliases sintáticos de MLflow. Não acompanha
reatribuições, escopos, objetos MlflowClient, wrappers nem delegação ao Lightning.
Essas limitações admitem falsos positivos e negativos; as fichas dos casos ajudam
a interpretar a diferença entre integração estrutural e chamadas detectadas.
Autolog não é expandido em operações presumidas. Pesos registrados como artefatos
não são automaticamente versões promovidas de modelos.

## Estados dos resultados

| Estado | Interpretação |
|---|---|
| `observed` | Cálculo realizado; zero é possível quando o denominador é positivo. |
| `not_available` | Fonte não coletada, inacessível, sem parser ou dimensão não validada. |
| `not_applicable` | Operação fora do domínio implementado. |
| `undefined` | Denominador igual a zero. |
| `error` | Falha de coleta ou processamento que impede aceitar a medida. |

Somente `observed` tem valor numérico. O campo `availability_reason` distingue
`not_found_in_inspected_scope`, `source_inaccessible`, `not_collected`,
`parser_not_implemented` e `dimension_not_validated`. A falta de coleta não é uma
busca com resultado negativo.

O tipo de evidência é informado separadamente: `direct` para registros públicos da
prática, `structural` para vínculos nos artefatos e `proxy` para sinais indiretos,
como candidatos sintáticos. Esses tipos não são somados em um escore de maturidade.
Cada medida registra caso, SHA, período, unidade, numerador, denominador, exclusões,
versões do instrumento e execução. O estado observado informa que o cálculo foi
feito; a validação da taxonomia consta em outro campo.
