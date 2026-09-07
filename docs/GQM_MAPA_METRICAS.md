# Mapa GQM e contrato das métricas — protocolo 2.0.0

Recorte operacional: mecanismos de rastreabilidade publicamente observáveis e
instrumentação de treinamento em três bibliotecas/frameworks com MLflow. Não há
comparação entre ferramentas nem inferência sobre a execução nas organizações usuárias.
A alteração foi adotada para o piloto solicitado em 05/09/2026; o alinhamento acadêmico
com a orientadora permanece pendente. A proposta original não foi editada.

## Universo e fontes

Unidade de comparação: repositório. Unidade longitudinal: commit alcançável a partir
do SHA da seleção, em todo o DAG, desde a origem, sem incluir descendentes posteriores.
Datas usam `committed_at` em UTC; início/fim reportados são mínimo/máximo do universo.
A data de atividade da seleção não restringe o período das métricas.

`C` = altera CODE ou NOTEBOOK; `P` = altera CONFIG; `D` = altera um artefato de dados
cujo papel foi validado. DATA_META continua sendo o detector estrutural de DVC, sem
representar automaticamente D no recorte MLflow. `C_only` exige que todas as mudanças
sejam CODE/NOTEBOOK. Exclusões: merge, bot, commit com mais de 1.000 arquivos, nessa
precedência exclusiva. Bots são identificados pelo nome/e-mail do autor e pelos padrões
versionados. A coalteração indica associação temporal, sem causalidade.

## Contratos fechados antes do piloto

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

GQM 3.2 conserva o numerador original, inclusive runs sem vínculo com promoção. A versão
anterior, restrita a runs vinculadas, foi retirada do contrato executável. Mesmo com
fontes, essa razão agregada não determina causalmente quantas tentativas antecederam
cada promoção. O identificador antigo `data_code_coupling` foi substituído pelos dois
nomes distintos acima; nenhuma série anterior deve ser concatenada implicitamente.

O piloto implementa `code_config_cochange`, `config_magnitude` e os indicadores
estáticos abaixo. Os seis resultados que dependem de D validada ou de runs/registry
são emitidos com `not_available`; não existe ainda parser dessas fontes. A simples
presença futura de `mlruns` não habilita cálculos sem uma nova implementação validada.

## Diferenças semânticas

YAML/YML (incluindo MLproject), JSON e TOML são lidos com parsers seguros, sem executar
arquivos do caso. Folhas de mapas são identificadas por caminho hierárquico com tipo
da chave; listas contam como um valor atômico, mapas vazios como folhas. Comparação de
valores preserva a distinção booleano/número. Comentários e ordem das chaves não contam.
Adições/remoções de arquivos contam suas folhas. Identidade é `(caminho do arquivo,
caminho da chave)` por commit, evitando fundir chaves de arquivos diferentes.

Renomeações são deliberadamente tratadas como remoção e adição (`--no-renames`);
portanto, mudanças de diretório podem aumentar a magnitude sem mudar parâmetros.
Chaves duplicadas, aliases recursivos, bytes inválidos e sintaxe inválida geram erro
observável. A média integral nunca é substituída por uma média dos parsers que passaram.
O YAML usa a semântica do PyYAML SafeLoader, incluindo resolução de escalares; isso
pode diferir do loader efetivo de um projeto e exige revisão dos casos limítrofes.

## Indicadores estáticos próprios

| Identificador | Numerador | Denominador / unidade |
|---|---|---|
| `static_mlflow_param_calls` | posições sintáticas `log_param` e `log_params` | 1 / posições no SHA |
| `static_mlflow_metric_calls` | posições `log_metric` e `log_metrics` | 1 / posições no SHA |
| `static_mlflow_artifact_calls` | posições `log_artifact` e `log_artifacts` | 1 / posições no SHA |
| `static_mlflow_model_calls` | posições `log_model` e `register_model` | 1 / posições no SHA |

Fonte: AST dos arquivos Python da árvore congelada. Contam-se somente caminhos CODE;
testes, exemplos classificados fora de CODE e notebooks não entram nesses indicadores.
A tabela `tree_inspection.json` preserva também os candidatos nas demais categorias.
Cada posição conta uma vez, independentemente de loops e quantidade de execuções.
Chamadas de artefatos podem registrar pesos; não são automaticamente modelos promovidos.

O parser resolve imports diretos e aliases sintáticos de MLflow. Não resolve fluxo de
controle, reatribuições, escopo de aliases, objetos MlflowClient, wrappers, delegação ao
Lightning ou chamadas dinâmicas. Assim, os números são **candidatos sintáticos**, sujeitos
a falsos positivos e negativos, com conferência qualitativa dos arquivos de integração.
Falha de parse Python gera `error`, não contagem completa. Nenhuma dessas contagens é
proxy numérico das métricas de runs ou proveniência.

## Status e campos

Somente `observed` carrega valor. Zero é válido com denominador positivo e ausência de
evento. `not_available`: fonte não observável/ingerida ou dimensão não validada;
`not_applicable`: operação fora do domínio implementado; `undefined`: denominador zero;
`error`: falha de processamento, bloqueia aceite técnico da Fase 5.

Cada linha registra repositório, SHA, período UTC, identificador, numerador, denominador,
valor, unidade, status e detalhe, exclusões, versões de protocolo/taxonomia, `run_id` e
`validation_status`. `observed` descreve cálculo, não certificação da taxonomia.
Resultados do piloto são preliminares até a validação humana mínima de 95%.

## Revisão 2.1.0 — perguntas e força de evidência

Dos seis objetivos métricos originais, magnitude CONFIG é operacionalizável nas
fontes coletadas; proveniência, frequência D/C, CACE, ambiente e runs/promoções não
são respondíveis atualmente. C/P complementa CACE, mas não responde à dimensão D.
AST complementa descrição da integração, sem substituir proveniência/execução.
DATA_META continua DVC. availability_reason distingue dimension_not_validated das
fontes de runtime not_collected; parser futuro continua necessário.
Plano quantitativo/qualitativo normativo: PLANO_ANALISE.md. Fórmulas principais
2.0.0 preservadas; acrescentam-se distribuições, séries e sensibilidade separadas.
