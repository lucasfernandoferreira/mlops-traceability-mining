# Método da pesquisa

O estudo examina mecanismos públicos de rastreabilidade em três projetos de
aprendizado de máquina que integram MLflow. A análise combina medidas do histórico
Git com a leitura dos artefatos e dos eventos de mudança. O protocolo vigente é
2.1.0, definido em `config/config.yaml`, com taxonomia 1.1.0.

## Delineamento e unidade de análise

Cada caso corresponde a um projeto de software, delimitado por seu repositório
canônico, pelo SHA observado na seleção e por todo o histórico alcançável a partir
desse SHA. Commits, arquivos e eventos são observações internas ao caso. Runs e
versões de modelos só podem ser analisados quando houver fontes públicas que
permitam identificá-los e vinculá-los ao projeto.

A escolha de três casos mantém o intervalo de três a cinco previsto na proposta e
permite aprofundar a leitura documental dentro do prazo disponível. Busca-se
contraste entre mecanismos de integração e contextos de uso, sem representatividade
estatística dos projetos do GitHub. O número de commits descreve a extensão dos
históricos; não aumenta, por si só, o número de casos independentes.

## Seleção dos casos

A descoberta exige pelo menos 300 candidatos e produz uma shortlist entre 10 e 200
repositórios. As consultas são paginadas e os candidatos são deduplicados pelo ID
numérico do GitHub. Limites e respostas incompletas da API ficam registrados.
A triagem exclui forks, projetos arquivados e os termos de material didático
configurados no protocolo. A presença de MLflow é inicialmente verificada por
imports e dependências, com confirmação dos caminhos encontrados na busca e de até
50 manifestos. Essa verificação funciona como pré-filtro da inspeção do caso.

Os critérios de maturidade são pelo menos 300 commits alcançáveis, 100 estrelas no
instante da coleta e cinco identidades de autor com atividade posterior a
01/09/2025 UTC. Para atividade, contam-se commits não merge e não bot. O identificador
usa email em minúsculas, com nome como alternativa quando não há email; aliases
podem representar a mesma pessoa. A contagem agregada de contribuidores da triagem
não substitui essa verificação no histórico congelado.

A evidência mínima de integração é uma ligação observável entre entrada ou
orquestração, componente MLflow e operação de registro. A ficha descreve a ligação,
as condições de habilitação e os caminhos no SHA inspecionado. Os estados
`dependency_only`, `functional_integration_observed`, `execution_publicly_verified`
e `insufficient_evidence` indicam a natureza da evidência e não formam uma escala
numérica. O critério proposto é `functional_integration_observed`. Uma exigência
acadêmica de execução comprovada demandaria reavaliar as fontes e os casos.

### DM-026 — operações herdadas de frameworks (variante A)

Em 11/09/2026, o pesquisador escolheu expressamente a variante A na conversa de
implementação. A decisão foi motivada pela divergência na ficha do Anomalib, após
conhecer os casos atuais. É uma clarificação retrospectiva do critério de integração;
a mesma regra será aplicada aos casos e a qualquer avaliação futura das reservas.
Não representa pré-registro da seleção original nem aprovação acadêmica do recorte.

Uma operação herdada é evidência estrutural de integração quando o código do caso,
no SHA congelado, conecta a entrada ao componente do framework e aciona a interface
pública de registro; a versão da dependência é identificada no lockfile desse SHA;
e a implementação externa correspondente é inspecionada, preservada e citada com
revisão, hashes e trechos. Uma declaração de dependência isolada não satisfaz o critério.
As condições de habilitação e de propagação dos registros devem ser explicitadas.

Operações apenas disponíveis na API, sem ligação demonstrada no fluxo descrito,
permanecem fora dessa cadeia. No Anomalib, a ficha passa a descrever a injeção de
logger no Trainer e as operações herdadas de parâmetros e métricas. O Engine não
registra mais o callback que chamava `add_image`; esse método permanece disponível
para chamada explícita. A cadeia principal usa os modelos; o esclarecimento da vinculação dinâmica do
`Evaluator` (V1) está no dossiê e não implica teste de execução.

O [dossiê DM-026](DM026_E_FECHAMENTO_TAXONOMIA.md) registra as fontes técnicas e o
impacto. A evidência permanece `structural`, sem execução de treinamento, certificação
de uso histórico ou promoção de proxy a causalidade. Protocolo de execução 2.1.0,
fórmulas, filtros, taxonomia 1.1.0 e plano 1.0.0 permanecem preservados; a revisão da
ficha exige novo índice e novos derivados qualitativos, com proveniência própria.

As reservas seguem a ordem registrada antes das métricas: Anomalib, Axolotl e
RF-DETR. A substituição depende de inelegibilidade, indisponibilidade ou custo
previamente delimitado, com motivo e data. Não há teto de custo definido como
critério automático. O Composer apresentou duas identidades ativas e foi substituído
tecnicamente pelo Anomalib, que apresentou 39, antes do cálculo das métricas da
reserva. A amostra permanece `pilot` até a decisão do pesquisador.

## Mineração e classificação

A mineração percorre todo o grafo de ancestrais do SHA selecionado, uma vez por
commit. O corte de atividade usado na seleção não restringe o período das métricas.
As datas de commit são normalizadas para UTC. O commit inicial é comparado à árvore
vazia; os demais, ao primeiro pai. Renomeações são tratadas como remoção e adição.

As exclusões obedecem à ordem merge, bot e commit com mais de 1.000 arquivos. Cada
commit excluído recebe um único motivo no funil. Bots são identificados pelos
padrões versionados de nome e email. A tabela de commits mantém os excluídos; a
tabela de mudanças contém somente os caminhos dos commits incluídos.

Cada caminho recebe a primeira categoria compatível com as regras de
`config/file_taxonomy.yaml`. A precedência faz parte do instrumento. CODE e
NOTEBOOK compõem a dimensão C; CONFIG compõe P. DATA_META identifica artefatos DVC
e permanece um indicador técnico, sem representar toda a dimensão de dados em
projetos MLflow. Os contratos das medidas estão no [mapa GQM](GQM_MAPA_METRICAS.md).

## Validação da taxonomia

A unidade de validação é um caminho por repositório, considerando os históricos
incluídos e a árvore congelada. Arquivos removidos são recuperados no primeiro pai
do commit de remoção. A revisão representativa é escolhida pela ordem dos SHAs do
commit e da revisão do blob. O inventário registra o blob e o número de observações
históricas, permitindo investigar mudanças de papel do mesmo caminho.

A amostra seleciona até 20 unidades por categoria, alternando os casos de forma
determinística. Categorias com uma a 19 unidades são avaliadas integralmente.
Uma categoria sem unidades em inventário completo é registrada como ausente naquele
universo e não recebe validação empírica. Inventários incompletos impedem o aceite.

Os exemplos de calibração são identificados e separados da avaliação quando há
unidades adicionais suficientes. Categorias raras avaliadas por censo mantêm essa
limitação explícita. A revisão registra classe esperada, responsável, data UTC,
justificativa e, quando necessário, a conferência de variação histórica de papel.
A concordância mínima é 95%, acompanhada de matriz de confusão e resultados por
categoria e caso. Como a amostra é estratificada, sua concordância não estima
automaticamente a precisão em todos os arquivos do estudo.

## Análise quantitativa

O plano de análise 1.0.0 foi registrado em 07/09/2026, após o piloto exploratório do
Ultralytics e antes da seleção qualitativa final. Portanto, não é um pré-registro
do piloto. A configuração normativa fica no bloco `analysis` do protocolo.

A coalteração código–configuração é descrita por caso e por mês UTC. Numeradores e
denominadores mensais devem reconciliar com os totais; a média simples das taxas
mensais não representa a taxa global. Meses sem commits C têm resultado indefinido.

Para a magnitude CONFIG, são calculados média, mediana, p90, p95, máximo, fração de
zeros e participação dos 10% maiores valores, arredondando a quantidade para cima.
Os quantis usam interpolação linear. Todos os commits P entram no denominador,
inclusive os que alteram somente comentários. Um erro de parser bloqueia a medida
afetada, sem recalcular uma média apenas com os arquivos que foram lidos.

A análise principal mantém remoção e adição de renomeações. A sensibilidade pareia
A/D no mesmo commit quando os blobs são idênticos, ordenando caminhos e pareando
um a um; ambas as contribuições são subtraídas apenas nessa variante. Outras
variantes distinguem a chave `str:names` e caminhos data/dataset(s), conforme a
configuração. Essas regras não tornam nomes de classes equivalentes a
hiperparâmetros, nem autorizam retirar valores extremos para reduzir a média.

As comparações são descritivas. A dependência temporal e organizacional entre
commits impede tratá-los como observações independentes em qui-quadrado,
Kruskal-Wallis ou bootstrap simples. Intervalos de incerteza só caberiam após
definição do estimando e de um modelo de dependência. A primeira integração
observável é um marco documental, sem interpretação causal.

## Análise qualitativa

A seleção prevê 15 eventos por caso, com cinco posições em cada grupo, na ordem
Q1, Q2 e Q3. Q1 cobre os caminhos de integração confirmados e seus chamadores; Q2,
a coalteração C/P; Q3, as maiores mudanças semânticas positivas em CONFIG.

Commits associados ao mesmo PR verificado são agrupados antes da seleção. Todos os
SHAs elegíveis e os grupos aos quais o evento pertence são preservados. Quando
não há vínculo verificável, o commit é a unidade documental. O mapa deve cobrir
todo o universo elegível para que a seleção deixe de ser preliminar.

A coleta factual pode usar `associatedPullRequests` da API GraphQL do GitHub,
guardando consulta, resposta, data e hashes. Um único vínculo no repositório define
o PR do evento. Resposta completa sem vínculo registra `pr_not_found` no escopo
da API. Vínculos múltiplos, paginação incompleta, objeto ausente ou falha de acesso
permanecem `error` até resolução. A coleta automática é identificada como tal e
não substitui a codificação do pesquisador.

Em Q1, a primeira adição elegível do componente de integração é incluída, seguida
de posições distribuídas no tempo. A ausência de um marco recuperável é registrada.
Para Q1 e Q2, os candidatos são ordenados por data UTC e SHA; entre n candidatos,
escolhem-se k posições por `floor(i*(n-1)/(k-1))`. Quando k=1, usa-se a primeira
posição. Q3 é ordenado por magnitude decrescente, com desempate por data e SHA.

A seleção é sem reposição. Sobreposições e déficits ficam registrados; os lugares
restantes até 15 são preenchidos por seleção temporal dos eventos disponíveis, sem
atribuí-los aos grupos deficitários. Um universo com menos de 15 eventos é analisado
integralmente. Alterar o mapa PR exige nova seleção; alterar as regras após a leitura
dos eventos exige versão, data e justificativa.

A codificação parte dos temas abaixo. Eles orientam a leitura e não antecipam achados.

| Tema | Evidência pertinente | Limite de interpretação |
|---|---|---|
| `training_integration` | Entrada que registra ou invoca callback/logger habilitado. | Import isolado não comprova ligação ao fluxo. |
| `parameter_logging` | Valores ou configurações encaminhados a uma operação de registro. | Nome de arquivo não identifica o uso dos valores. |
| `artifact_tracking` | Saída do processamento ligada a um artefato registrado. | Registro de artefato não comprova promoção no registry. |
| `data_environment_reference` | Referências verificáveis a dados, versões ou dependências. | DATA_META não abrange todos os datasets. |
| `integration_failure` | Falha descrita em código, teste ou discussão vinculada. | Falta de log público não demonstra falha. |
| `configuration_refactoring` | Mudança de estrutura, caminho ou conteúdo de configuração. | Movimento de YAML não implica novos hiperparâmetros. |

Cada evento recebe evidência, interpretação, justificativa, ambiguidade, relação
com uma métrica, evidência contrária e limite da conclusão, além de responsável e
data UTC. Podem ser usados vários temas, separados por `;`. Temas emergentes exigem
registro datado e revisão do conjunto de códigos. A análise integrada relaciona o
padrão quantitativo ao evento e à explicação documental. Essa amostra intencional
não estima a prevalência dos temas. O número efetivo de codificadores será declarado,
considerando os pesquisadores que realizarem a leitura e o julgamento dos eventos.

## Histórico do protocolo e condições de conclusão

A busca e a triagem de 31/08/2026 usaram o protocolo 1.5.0, com descoberta de DVC,
MLflow e uso combinado. O piloto de 05/09 adotou o recorte MLflow no protocolo 2.0.0.
O protocolo 2.1.0 incorporou os cinco pontos do parecer de 07/09: definição e
quantidade dos casos, maturidade e integração, força das evidências, dependência
entre commits e seleção qualitativa integrada. As fórmulas principais e a taxonomia
1.1.0 foram mantidas.

Os registros DM-001 a DM-025 foram reunidos neste texto. A DM-026, variante A,
foi acrescentada em 11/09/2026 com a origem da decisão e seu caráter retrospectivo. As versões anteriores estão
no histórico Git e nos arquivos preservados, inclusive as regras substituídas.
A exigência antiga de 20 exemplos em todas as categorias foi ajustada para censo ou
ausência no universo.
O critério de contribuidores passou a impedir o aceite da amostra, sem impedir
que a etapa de métricas registre processamento bem-sucedido de um caso inelegível.
A contagem agregada de 1.500 commits deixou de ser justificativa de poder inferencial.

O parecer foi descrito no roteiro recebido como aprovação do delineamento com
condicionantes. O recorte exclusivamente MLflow e o mapeamento das perguntas ainda
precisam de alinhamento acadêmico documentado. Nenhuma aprovação específica foi
presumida a partir da implementação.

A conclusão exige três casos elegíveis com fichas revisadas, validação da taxonomia,
mapa PR completo, codificação qualitativa e alinhamento acadêmico. Também exige
cadeia de execuções com código commitado, fontes identificadas e hashes conferidos.
Cada etapa tem seu próprio estado; sucesso de processamento não certifica o estudo.
Revisões e finalizações recusadas são preservadas com seus motivos para permitir
retomada sem alterar os registros anteriores.
