# Mudanças de código e configuração e mecanismos MLflow em projetos públicos

Versão documental produzida em 2026-09-13T22:21:52Z. Autoria técnica: assistant:codex-dm027-fechamento; revisão autoral mediante confirmação registrada.

## Resumo

O recorte inclui 3 casos e 45 eventos selecionados intencionalmente, com 15 eventos por caso; a amostra taxonômica de avaliação contém 180 unidades. [afirmação:desenho]

O estudo caracteriza a organização das mudanças e examina mecanismos públicos de integração. A análise combina histórico Git, taxonomia de arquivos, medidas descritivas e leitura temática de eventos. Os resultados permitem comparar mecanismos documentados e expor os limites das medidas; não permitem inferir execução pública de treinamento, causalidade ou maturidade organizacional.

## Objetivo e perguntas

Caracterizar mudanças conjuntas de código e configuração e examinar os mecanismos de integração MLflow documentados nos projetos públicos selecionados, delimitando o alcance e as lacunas das evidências de rastreabilidade. [afirmação:alinhamento]

As perguntas operacionais tratam de mudanças conjuntas de código/configuração, magnitude dessas mudanças e ligação estrutural entre chamadores, componentes e operações MLflow. As perguntas sobre proveniência de versões, coalteração com dados, ambiente por run e redundância experimental permanecem abertas. A decisão de recorte e o plano alternativo de fontes adicionais constam do parecer acadêmico técnico.

## Método

O índice definitivo identifica os SHAs congelados e os runs de coleta, mineração, métricas e seleção. Mantiveram-se respostas originais da coleta e associações de PRs; novas consultas não substituíram essas observações. A elegibilidade aplica filtros declarados de bots, merges e mudanças grandes. Atividade utiliza identidades normalizadas do Git; aliases e contas não equivalem necessariamente a pessoas. As estrelas são as da coleta histórica.

A coalteração usa como denominador os commits elegíveis com CODE e como numerador os que também modificam CONFIG. A magnitude usa commits CONFIG elegíveis, inclusive quando foram observadas zero alterações de chaves. O parser compara chaves normalizadas; remoção/adição de caminhos, sequências, mapas de classes e configuração visual afetam o significado dessa contagem. CODE inclui código de interface pela DM-027. Na DM-026, a leitura da integração considera delegação a dependências preservadas, com escopo estrutural.

As unidades da avaliação anterior foram reservadas à calibração; não se reaproveitaram seus rótulos como avaliações da nova amostra. [afirmação:calibracao]

A avaliação atual mascarou predições por unidade antes da emissão dos rótulos. O mascaramento é limitado pela conservação da ordem estratificada e pelo conhecimento anterior do método. As interpretações foram redigidas por IA e devem ser assumidas pelo pesquisador por um ato final explícito; esse ato não transforma a classificação em replicação independente.

## Casos e resultados quantitativos

ultralytics/ultralytics: code_config_cochange = 0.0761002444987775 proportion; numerador 249, denominador 3272; status observed. [afirmação:ultralytics:code_config_cochange]

ultralytics/ultralytics: config_magnitude = 69.3076923076923 keys/config_commit; numerador 20723, denominador 299; status observed. [afirmação:ultralytics:config_magnitude]

ultralytics/ultralytics: data_code_ratio_original permanece indisponível (Dimensão D não validada para dados MLflow; DATA_META detecta DVC.); ausência de valor não significa zero. [afirmação:ultralytics:data_code_ratio_original]

ultralytics/ultralytics: data_code_cochange permanece indisponível (Dimensão D não validada para dados MLflow; DATA_META detecta DVC.); ausência de valor não significa zero. [afirmação:ultralytics:data_code_cochange]

ultralytics/ultralytics: cace_index permanece indisponível (Dimensão D não validada para dados MLflow; DATA_META detecta DVC.); ausência de valor não significa zero. [afirmação:ultralytics:cace_index]

ultralytics/ultralytics: provenance_coverage permanece indisponível (No runs/registry source ingested; tree scan is not a runtime census.); ausência de valor não significa zero. [afirmação:ultralytics:provenance_coverage]

ultralytics/ultralytics: env_versioning_rate permanece indisponível (No runs/registry source ingested; tree scan is not a runtime census.); ausência de valor não significa zero. [afirmação:ultralytics:env_versioning_rate]

ultralytics/ultralytics: experiment_redundancy permanece indisponível (No runs/registry source ingested; tree scan is not a runtime census.); ausência de valor não significa zero. [afirmação:ultralytics:experiment_redundancy]

ultralytics/ultralytics: static_mlflow_param_calls = 1.0 syntactic_call_sites_at_sha; numerador 1, denominador 1; status observed. [afirmação:ultralytics:static_mlflow_param_calls]

ultralytics/ultralytics: static_mlflow_metric_calls = 1.0 syntactic_call_sites_at_sha; numerador 1, denominador 1; status observed. [afirmação:ultralytics:static_mlflow_metric_calls]

ultralytics/ultralytics: static_mlflow_artifact_calls = 2.0 syntactic_call_sites_at_sha; numerador 2, denominador 1; status observed. [afirmação:ultralytics:static_mlflow_artifact_calls]

ultralytics/ultralytics: static_mlflow_model_calls = 0.0 syntactic_call_sites_at_sha; numerador 0, denominador 1; status observed. [afirmação:ultralytics:static_mlflow_model_calls]

pymc-labs/pymc-marketing: code_config_cochange = 0.015927189988623434 proportion; numerador 14, denominador 879; status observed. [afirmação:pymc-marketing:code_config_cochange]

pymc-labs/pymc-marketing: config_magnitude = 29.3125 keys/config_commit; numerador 469, denominador 16; status observed. [afirmação:pymc-marketing:config_magnitude]

pymc-labs/pymc-marketing: data_code_ratio_original permanece indisponível (Dimensão D não validada para dados MLflow; DATA_META detecta DVC.); ausência de valor não significa zero. [afirmação:pymc-marketing:data_code_ratio_original]

pymc-labs/pymc-marketing: data_code_cochange permanece indisponível (Dimensão D não validada para dados MLflow; DATA_META detecta DVC.); ausência de valor não significa zero. [afirmação:pymc-marketing:data_code_cochange]

pymc-labs/pymc-marketing: cace_index permanece indisponível (Dimensão D não validada para dados MLflow; DATA_META detecta DVC.); ausência de valor não significa zero. [afirmação:pymc-marketing:cace_index]

pymc-labs/pymc-marketing: provenance_coverage permanece indisponível (No runs/registry source ingested; tree scan is not a runtime census.); ausência de valor não significa zero. [afirmação:pymc-marketing:provenance_coverage]

pymc-labs/pymc-marketing: env_versioning_rate permanece indisponível (No runs/registry source ingested; tree scan is not a runtime census.); ausência de valor não significa zero. [afirmação:pymc-marketing:env_versioning_rate]

pymc-labs/pymc-marketing: experiment_redundancy permanece indisponível (No runs/registry source ingested; tree scan is not a runtime census.); ausência de valor não significa zero. [afirmação:pymc-marketing:experiment_redundancy]

pymc-labs/pymc-marketing: static_mlflow_param_calls = 24.0 syntactic_call_sites_at_sha; numerador 24, denominador 1; status observed. [afirmação:pymc-marketing:static_mlflow_param_calls]

pymc-labs/pymc-marketing: static_mlflow_metric_calls = 6.0 syntactic_call_sites_at_sha; numerador 6, denominador 1; status observed. [afirmação:pymc-marketing:static_mlflow_metric_calls]

pymc-labs/pymc-marketing: static_mlflow_artifact_calls = 3.0 syntactic_call_sites_at_sha; numerador 3, denominador 1; status observed. [afirmação:pymc-marketing:static_mlflow_artifact_calls]

pymc-labs/pymc-marketing: static_mlflow_model_calls = 2.0 syntactic_call_sites_at_sha; numerador 2, denominador 1; status observed. [afirmação:pymc-marketing:static_mlflow_model_calls]

open-edge-platform/anomalib: code_config_cochange = 0.1721556886227545 proportion; numerador 115, denominador 668; status observed. [afirmação:anomalib:code_config_cochange]

open-edge-platform/anomalib: config_magnitude = 87.921875 keys/config_commit; numerador 11254, denominador 128; status observed. [afirmação:anomalib:config_magnitude]

open-edge-platform/anomalib: data_code_ratio_original permanece indisponível (Dimensão D não validada para dados MLflow; DATA_META detecta DVC.); ausência de valor não significa zero. [afirmação:anomalib:data_code_ratio_original]

open-edge-platform/anomalib: data_code_cochange permanece indisponível (Dimensão D não validada para dados MLflow; DATA_META detecta DVC.); ausência de valor não significa zero. [afirmação:anomalib:data_code_cochange]

open-edge-platform/anomalib: cace_index permanece indisponível (Dimensão D não validada para dados MLflow; DATA_META detecta DVC.); ausência de valor não significa zero. [afirmação:anomalib:cace_index]

open-edge-platform/anomalib: provenance_coverage permanece indisponível (No runs/registry source ingested; tree scan is not a runtime census.); ausência de valor não significa zero. [afirmação:anomalib:provenance_coverage]

open-edge-platform/anomalib: env_versioning_rate permanece indisponível (No runs/registry source ingested; tree scan is not a runtime census.); ausência de valor não significa zero. [afirmação:anomalib:env_versioning_rate]

open-edge-platform/anomalib: experiment_redundancy permanece indisponível (No runs/registry source ingested; tree scan is not a runtime census.); ausência de valor não significa zero. [afirmação:anomalib:experiment_redundancy]

open-edge-platform/anomalib: static_mlflow_param_calls = 0.0 syntactic_call_sites_at_sha; numerador 0, denominador 1; status observed. [afirmação:anomalib:static_mlflow_param_calls]

open-edge-platform/anomalib: static_mlflow_metric_calls = 0.0 syntactic_call_sites_at_sha; numerador 0, denominador 1; status observed. [afirmação:anomalib:static_mlflow_metric_calls]

open-edge-platform/anomalib: static_mlflow_artifact_calls = 0.0 syntactic_call_sites_at_sha; numerador 0, denominador 1; status observed. [afirmação:anomalib:static_mlflow_artifact_calls]

open-edge-platform/anomalib: static_mlflow_model_calls = 0.0 syntactic_call_sites_at_sha; numerador 0, denominador 1; status observed. [afirmação:anomalib:static_mlflow_model_calls]

Inclusão tecnicamente sustentada pelo histórico congelado, atividade e estrelas da coleta original. BaseTrainer registra callbacks via add_integration_callbacks, e o componente mlflow envia argumentos, métricas e artefatos sob SETTINGS e guards. No evento 620f3eb2181c1b686c9bdd2ee805dee483d4f116, o caminho é renomeado de ultralytics/yolo/utils/callbacks/mlflow.py; o marco selecionado não é adoção inicial. Integração estrutural, sem alegação de uso público em execução. [afirmação:caso:ultralytics/ultralytics]

Inclusão tecnicamente sustentada pelo histórico congelado e diversidade do domínio. pymc_marketing/mlflow.py conecta autolog à amostragem e ao fit e registra informações do modelo, parâmetros e inferência. ModelBuilder recebe model_config e sampler_config como objetos Python: a taxonomia os conta em CODE, portanto CONFIG não cobre integralmente a configuração operacional. Evidência de wrappers e testes, sem medir proveniência de runs públicos. [afirmação:caso:pymc-labs/pymc-marketing]

Inclusão tecnicamente sustentada como reserva ordenada do protocolo após inelegibilidade do Composer, preservando a decisão anterior às métricas. O Engine repassa logger ao Trainer e converte ausência em desativação. AnomalibMLFlowLogger herda operações do Lightning; a fonte externa preservada da DM-026 identifica a implementação examinada. Checkpoints dependem de log_model; add_image é API disponível sem ligação automática demonstrada no congelamento. Não há comprovação de uso por terceiros. [afirmação:caso:open-edge-platform/anomalib]

## Avaliação da taxonomia

A avaliação da taxonomia obteve 173/180 concordâncias (96.11%), com 7 divergências. O limiar global é 95%. O resultado é de julgamento redigido pela IA sob mascaramento das predições individuais; não é concordância humana independente. [afirmação:taxonomia]

Categoria CI: universo 106, avaliações 20, status sampled_category, concordância 1.0. [afirmação:categoria:CI]

Categoria CODE: universo 2005, avaliações 20, status sampled_category, concordância 1.0. [afirmação:categoria:CODE]

Categoria CONFIG: universo 424, avaliações 20, status sampled_category, concordância 0.95. [afirmação:categoria:CONFIG]

Categoria DATA_META: universo 0, avaliações 0, status absent_in_validated_universe, concordância não estimável por ausência de itens. [afirmação:categoria:DATA_META]

Categoria DATA_RAW: universo 40, avaliações 20, status sampled_category, concordância 1.0. [afirmação:categoria:DATA_RAW]

Categoria DOC: universo 2018, avaliações 20, status sampled_category, concordância 1.0. [afirmação:categoria:DOC]

Categoria ENV: universo 57, avaliações 20, status sampled_category, concordância 0.95. [afirmação:categoria:ENV]

Categoria NOTEBOOK: universo 163, avaliações 20, status sampled_category, concordância 1.0. [afirmação:categoria:NOTEBOOK]

Categoria OUTRO: universo 2251, avaliações 20, status sampled_category, concordância 0.75. [afirmação:categoria:OUTRO]

Categoria TEST: universo 567, avaliações 20, status sampled_category, concordância 1.0. [afirmação:categoria:TEST]

Avaliação em open-edge-platform/anomalib: 61 unidades; concordância 0.9836065573770492. [afirmação:avaliacao:open-edge-platform/anomalib]

Avaliação em pymc-labs/pymc-marketing: 73 unidades; concordância 0.9726027397260274. [afirmação:avaliacao:pymc-labs/pymc-marketing]

Avaliação em ultralytics/ultralytics: 46 unidades; concordância 0.9130434782608695. [afirmação:avaliacao:ultralytics/ultralytics]

As divergências concentram-se em arquivos de compilação, metadados de ferramentas e automação. CMakeLists de exemplos mantêm função de construção; roteamento de issues e configuração de lint não são configuração do modelo. A análise por unidade está preservada no dossiê de divergências, sem mudanças retroativas nos rótulos.

## Resultados documentais e discussão

A análise identifica mecanismos distintos: deslocamento de descritores no Ultralytics e Anomalib, configuração em Python e builders declarativos no PyMC, e ativação condicional das integrações. Os registros seguintes sustentam os contrastes e delimitam suas explicações alternativas.

As interpretações abaixo explicitam a relação com eventos específicos. O catálogo preserva fontes, método e limites de cada afirmação.

A reorganização do pacote desloca callbacks e descritores de datasets; o marco de caminho selecionado não é adoção inicial de MLflow. [afirmação:evento-1]
Conclusão documental sobre ultralytics/utils/callbacks/mlflow.py no SHA indicado. O próprio diff identifica renomeação e conserva o callback, contrariando uma leitura de introdução funcional. A seleção intencional de eventos não autoriza estimar a prevalência dos temas no projeto inteiro.

A ativação do callback passa a depender da preferência persistida pelo SettingsManager, expressa em Python. [afirmação:evento-2]
Conclusão documental sobre ultralytics/utils/callbacks/mlflow.py no SHA indicado. A presença da guarda permite desabilitar o envio; modificar integração não implica alteração de arquivo CONFIG. A seleção intencional de eventos não autoriza estimar a prevalência dos temas no projeto inteiro.

O lançamento YOLO11 combina arquiteturas declarativas com implementação e opção de aumento de dados; Q1 também captura evolução geral do trainer. [afirmação:evento-3]
Conclusão documental sobre ultralytics/cfg/default.yaml no SHA indicado. Os YAMLs de arquitetura e a alteração de copy_paste_mode explicam coalteração sem demonstrar mudança do callback MLflow. A seleção intencional de eventos não autoriza estimar a prevalência dos temas no projeto inteiro.

A escolha automática entre MuSGD e AdamW muda dentro do trainer; parâmetros operacionais podem mudar em CODE sem CONFIG. [afirmação:evento-4]
Conclusão documental sobre ultralytics/engine/trainer.py no SHA indicado. O diff está restrito à estratégia do otimizador e não altera chamadas de tracking. A seleção intencional de eventos não autoriza estimar a prevalência dos temas no projeto inteiro.

A manutenção remove Neptune da lista de callbacks e atualiza Ray Tune; no arquivo MLflow remove apenas uma instrução operacional da docstring. [afirmação:evento-5]
Conclusão documental sobre ultralytics/utils/callbacks/base.py no SHA indicado. A mudança em mlflow.py é textual; o evento Q1 não demonstra nova operação MLflow. A seleção intencional de eventos não autoriza estimar a prevalência dos temas no projeto inteiro.

A introdução do trainer e defaults aproxima opções de treino e persistência de train.yaml no diretório do experimento. [afirmação:evento-6]
Conclusão documental sobre ultralytics/yolo/engine/trainer.py no SHA indicado. Salvar YAML localmente não estabelece identidade de run num servidor MLflow nem vínculo verificável com dados externos. A seleção intencional de eventos não autoriza estimar a prevalência dos temas no projeto inteiro.

A mudança para novos caminhos de datasets ocorre junto à exportação TensorFlow; remoções e adições de descritores elevam a magnitude por caminho. [afirmação:evento-7]
Conclusão documental sobre ultralytics/datasets/ImageNet.yaml no SHA indicado. A similaridade registrada na renomeação mostra que magnitude alta pode refletir deslocamento e não alteração equivalente de hiperparâmetros. A seleção intencional de eventos não autoriza estimar a prevalência dos temas no projeto inteiro.

Os descritores YOLOv9 nomeiam blocos também introduzidos no código, documentando dependência entre arquitetura declarada e implementação. [afirmação:evento-8]
Conclusão documental sobre ultralytics/cfg/models/v9/yolov9c.yaml no SHA indicado. A topologia declarada não é prova de treinamento ou de melhoria de desempenho; não há vínculo de execução neste diff. A seleção intencional de eventos não autoriza estimar a prevalência dos temas no projeto inteiro.

A opção visualize conserva seu valor no YAML, mas passa a orientar visualização de acertos e erros no validador. [afirmação:evento-9]
Conclusão documental sobre ultralytics/cfg/default.yaml no SHA indicado. A edição é de comentário no YAML; coalteração por arquivo e magnitude semântica zero são compatíveis. A seleção intencional de eventos não autoriza estimar a prevalência dos temas no projeto inteiro.

A opção channels_last passa de falsa para escolha automática, ligada à detecção de CPU, sistema operacional e backend. [afirmação:evento-10]
Conclusão documental sobre ultralytics/cfg/default.yaml no SHA indicado. Os testes condicionam o resultado ao ambiente; a configuração versionada não determina sozinha o formato de memória efetivo. A seleção intencional de eventos não autoriza estimar a prevalência dos temas no projeto inteiro.

A inclusão de descritores de datasets e catálogos de classes aumenta a magnitude CONFIG e oferece referências de entrada para o código. [afirmação:evento-11]
Conclusão documental sobre ultralytics/yolo/data/datasets/ImageNet.yaml no SHA indicado. Nomes e caminhos de datasets não são hashes do conteúdo usado em cada execução e não validam a dimensão D. A seleção intencional de eventos não autoriza estimar a prevalência dos temas no projeto inteiro.

O suporte a YOLO-World inclui descritor LVIS e reorganiza get_dataset, ligando preparação de dados e configuração. [afirmação:evento-12]
Conclusão documental sobre ultralytics/cfg/datasets/lvis.yaml no SHA indicado. A lista extensa de classes pesa na magnitude; sua extensão não mede esforço de implementação nem cobertura de proveniência. A seleção intencional de eventos não autoriza estimar a prevalência dos temas no projeto inteiro.

A retomada passa a recuperar argumentos do checkpoint, enquanto o YAML ImageNet recebe um mapa de nomes legíveis. [afirmação:evento-13]
Conclusão documental sobre ultralytics/yolo/engine/trainer.py no SHA indicado. O grande mapa de classes e a correção de retomada coexistem; atribuir toda a magnitude a rastreabilidade de checkpoints seria indevido. A seleção intencional de eventos não autoriza estimar a prevalência dos temas no projeto inteiro.

O suporte a Open Images incorpora catálogo de classes e lógica de preparação do dataset, ampliando o conteúdo declarativo. [afirmação:evento-14]
Conclusão documental sobre ultralytics/cfg/datasets/open-images-v7.yaml no SHA indicado. Os links e nomes no descritor não comprovam execução nem recuperação de uma versão imutável das imagens. A seleção intencional de eventos não autoriza estimar a prevalência dos temas no projeto inteiro.

A extensão para segmentação semântica combina novos datasets, arquitetura e tratamento específico no trainer. [afirmação:evento-15]
Conclusão documental sobre ultralytics/engine/trainer.py no SHA indicado. Mudanças de comentários no default.yaml coexistem com descritores novos; o total não é medida exclusiva de hiperparâmetros de treino. A seleção intencional de eventos não autoriza estimar a prevalência dos temas no projeto inteiro.

O módulo MLflow introduz wrappers de amostragem e MMM.fit e utilitários de registro; a mensagem curta sobre BLAS não descreve toda a alteração. [afirmação:evento-16]
Conclusão documental sobre pymc_marketing/mlflow.py no SHA indicado. Os testes e exemplos são evidência de código; a associação PR preservada não encontrou um PR, portanto não atribuo discussão inexistente ao evento. A seleção intencional de eventos não autoriza estimar a prevalência dos temas no projeto inteiro.

A incorporação de ModelBuilder internaliza contratos de configuração e amostragem antes do componente MLflow selecionado. [afirmação:evento-17]
Conclusão documental sobre pymc_marketing/model_builder.py no SHA indicado. Ser parte dos caminhos Q1 não significa que esta incorporação introduziu MLflow; model_config e sampler_config são objetos Python. A seleção intencional de eventos não autoriza estimar a prevalência dos temas no projeto inteiro.

O autolog passa a registrar atributos e nomes das transformações antes de executar fit, preservando contexto mesmo antes da etapa demorada terminar. [afirmação:evento-18]
Conclusão documental sobre pymc_marketing/mlflow.py no SHA indicado. O diff não demonstra que uma execução tenha falhado ou completado; a vantagem em falhas é uma possibilidade do ordenamento, não observação de run. A seleção intencional de eventos não autoriza estimar a prevalência dos temas no projeto inteiro.

O aviso de depreciação orienta migração para MMM multidimensional; a evolução da API pode afetar quais chamadores se conectam ao autolog. [afirmação:evento-19]
Conclusão documental sobre pymc_marketing/mmm/mmm.py no SHA indicado. A mudança visível acrescenta aviso, sem mostrar reconfiguração do tracking ou migração efetiva dos usuários. A seleção intencional de eventos não autoriza estimar a prevalência dos temas no projeto inteiro.

A serialização de model_config passa a lidar com objetos de prior e decomposição, tornando explícito o desafio de persistir configuração expressa em código. [afirmação:evento-20]
Conclusão documental sobre pymc_marketing/mmm/mmm.py no SHA indicado. Serialização e testes não demonstram que todos esses atributos chegaram a um run MLflow; CONFIG não cobre essas alterações Python. A seleção intencional de eventos não autoriza estimar a prevalência dos temas no projeto inteiro.

A aplicação Streamlit combina código executável de explicação de priors com configuração visual; a DM-027 inclui a interface em CODE. [afirmação:evento-21]
Conclusão documental sobre streamlit/mmm-explainer/config.toml no SHA indicado. As opções visuais do TOML contribuem para C/P sem representar hiperparâmetros de um modelo treinado. A seleção intencional de eventos não autoriza estimar a prevalência dos temas no projeto inteiro.

A atualização de exemplo muda opções do sampler junto à depreciação da otimização antiga de orçamento e a dados simulados. [afirmação:evento-22]
Conclusão documental sobre data/config_files/multi_dimensional_example_model.yml no SHA indicado. A magnitude usa o conteúdo normalizado pelo parser do instrumento; não equivale à simples contagem visual das linhas modificadas. A seleção intencional de eventos não autoriza estimar a prevalência dos temas no projeto inteiro.

O builder passa a validar e resolver etapas de calibração declaradas em YAML, conectando explicitamente o documento de configuração a métodos do modelo. [afirmação:evento-23]
Conclusão documental sobre pymc_marketing/mmm/builders/yaml.py no SHA indicado. As recusas por estrutura inválida são contratos no código; não constituem incidentes de tracking observados em execução. A seleção intencional de eventos não autoriza estimar a prevalência dos temas no projeto inteiro.

O exemplo de custo por unidade materializa classe, canais, sampler e variáveis em escala original em YAML para construção do modelo. [afirmação:evento-24]
Conclusão documental sobre data/config_files/cost_per_unit_example.yml no SHA indicado. O título do commit menciona notebook; o diff deve prevalecer sobre a mensagem para identificar o que foi efetivamente acrescentado. A seleção intencional de eventos não autoriza estimar a prevalência dos temas no projeto inteiro.

A construção de modelos de funil passa a preservar extra_vars e aceitar Dataset, aproximando esquema declarativo e estrutura de dados. [afirmação:evento-25]
Conclusão documental sobre pymc_marketing/mmm/builders/yaml.py no SHA indicado. A validação de alvo duplicado e de coluna de data limita os formatos aceitos; isso não valida a dimensão D do estudo nem a proveniência de runs. A seleção intencional de eventos não autoriza estimar a prevalência dos temas no projeto inteiro.

A introdução do builder YAML torna explícita uma alternativa aos objetos Python, com descritores, factories e entradas tabulares preservadas no repositório. [afirmação:evento-26]
Conclusão documental sobre pymc_marketing/mmm/builders/yaml.py no SHA indicado. A maior exposição de CONFIG pode decorrer dessa opção arquitetural; não autoriza comparar maturidade organizacional pela taxa C/P. A seleção intencional de eventos não autoriza estimar a prevalência dos temas no projeto inteiro.

A correção alinha o nome do alvo com os dados de exemplo e inclui outro descritor; a renomeação de arquivo também afeta a magnitude. [afirmação:evento-27]
Conclusão documental sobre data/config_files/basic_model.yml no SHA indicado. A mensagem de correção de typo resume um diff que inclui conteúdo novo; magnitude não representa apenas renomear o alvo. A seleção intencional de eventos não autoriza estimar a prevalência dos temas no projeto inteiro.

A migração das visualizações de validação temporal inclui configuração geográfica de exemplo e uma dependência de visualização. [afirmação:evento-28]
Conclusão documental sobre pymc_marketing/mmm/plotting/cv.py no SHA indicado. O exemplo é excluído da varredura genérica de YAMLs nos testes; sua presença não demonstra validação integral de todas as combinações declaradas. A seleção intencional de eventos não autoriza estimar a prevalência dos temas no projeto inteiro.

A atualização de orçamento multidimensional combina configuração, ambiente e declaração de armazenamento LFS para inferência NetCDF. [afirmação:evento-29]
Conclusão documental sobre .gitattributes no SHA indicado. O ponteiro LFS e as dependências são referências; o diff sozinho não comprova recuperação de cada payload nem ambiente por run. A seleção intencional de eventos não autoriza estimar a prevalência dos temas no projeto inteiro.

A validação estrutural passa a recusar seções YAML indevidamente aninhadas e alerta sobre chaves desconhecidas, reduzindo descarte silencioso de opções. [afirmação:evento-30]
Conclusão documental sobre pymc_marketing/mmm/builders/yaml.py no SHA indicado. As fixtures de erro demonstram casos previstos no código; não medem incidência desses erros entre usuários. A seleção intencional de eventos não autoriza estimar a prevalência dos temas no projeto inteiro.

O adaptador MLflow herda operações do Lightning e oferece interface de imagem, acompanhado de exemplo de logger injetável. [afirmação:evento-31]
Conclusão documental sobre src/anomalib/loggers/mlflow.py no SHA indicado. A herança e o notebook não comprovam uso público do serviço; disponibilidade de add_image não garante chamada automática no SHA congelado. A seleção intencional de eventos não autoriza estimar a prevalência dos temas no projeto inteiro.

A transição de arquitetura remove configurações antigas e introduz Engine; essa reorganização contribui para um evento de magnitude elevada. [afirmação:evento-32]
Conclusão documental sobre src/anomalib/models/ai_vad/config.yaml no SHA indicado. A mensagem agregada contém várias mudanças históricas; o diff de primeira revisão é a base, sem atribuir cada remoção a MLflow. A seleção intencional de eventos não autoriza estimar a prevalência dos temas no projeto inteiro.

A manutenção da exportação ajusta tipo aceito, ajuda de CLI e exemplos de checkpoint no Engine. [afirmação:evento-33]
Conclusão documental sobre src/anomalib/engine/engine.py no SHA indicado. Não há alteração do componente MLflow: pertencer a Q1 pelo caminho do Engine não implica mudança de tracking. A seleção intencional de eventos não autoriza estimar a prevalência dos temas no projeto inteiro.

O nome do modelo exportado passa a ser configurável e propagado pelo Engine para os formatos de saída. [afirmação:evento-34]
Conclusão documental sobre src/anomalib/models/components/base/export_mixin.py no SHA indicado. Nome de arquivo não é identificador imutável de versão nem evidência de registro automático em MLflow. A seleção intencional de eventos não autoriza estimar a prevalência dos temas no projeto inteiro.

O Engine passa a registrar callback que corrige a visualização de progresso para treino por passos, dentro de uma entrega com novos modelos. [afirmação:evento-35]
Conclusão documental sobre src/anomalib/engine/engine.py no SHA indicado. Trata-se de callback de progresso; nenhuma operação MLflow é acrescentada por essa linha. A seleção intencional de eventos não autoriza estimar a prevalência dos temas no projeto inteiro.

A árvore inicial já reúne opções de dados, modelos e Trainer, evidenciando uma base declarativa anterior ao logger MLflow. [afirmação:evento-36]
Conclusão documental sobre anomalib/models/dfkde/config.yaml no SHA indicado. O descritor inicial desabilita logger; a existência de configuração não prova registro de experimento. A seleção intencional de eventos não autoriza estimar a prevalência dos temas no projeto inteiro.

A padronização do console logger ocorre junto à remoção de linhas vazias em YAML; isso exemplifica C/P com magnitude semântica nula. [afirmação:evento-37]
Conclusão documental sobre anomalib/models/dfm/config.yaml no SHA indicado. Logging de console e logger de experimento são contratos distintos; o diff não deve ser interpretado como adoção MLflow. A seleção intencional de eventos não autoriza estimar a prevalência dos temas no projeto inteiro.

A otimização do cálculo PatchCore acompanha aumento do batch de teste, ligando parâmetro declarativo e tratamento de vizinhos no código. [afirmação:evento-38]
Conclusão documental sobre anomalib/models/patchcore/config.yaml no SHA indicado. As alterações de estilo em outros módulos não são novas funcionalidades e a alegação de desempenho não foi reproduzida com benchmark. A seleção intencional de eventos não autoriza estimar a prevalência dos temas no projeto inteiro.

O Engine recebe logger como argumento e centraliza criação de diretório versionado, preparando a injeção de integração e organização de saídas. [afirmação:evento-39]
Conclusão documental sobre src/anomalib/engine/engine.py no SHA indicado. A assinatura aceita ausência de logger; diretório versionado por convenção não comprova proveniência completa nem ativação MLflow. A seleção intencional de eventos não autoriza estimar a prevalência dos temas no projeto inteiro.

A entrega reúne novos dados/modelos e migra resolução de diretórios de datasets, compondo uma atualização ampla da biblioteca. [afirmação:evento-40]
Conclusão documental sobre src/anomalib/data/datamodules/depth/adam_3d.py no SHA indicado. As mudanças de release coexistem no mesmo evento; não atribuo a magnitude CONFIG exclusivamente à resolução de diretórios. A seleção intencional de eventos não autoriza estimar a prevalência dos temas no projeto inteiro.

A adoção do layout src desloca configurações e código sem alterar o conteúdo de vários YAMLs; a regra A/D amplia a magnitude medida. [afirmação:evento-41]
Conclusão documental sobre src/anomalib/models/cfa/config.yaml no SHA indicado. A similaridade integral nas renomeações contraria a interpretação de que todas as chaves contadas mudaram de significado. A seleção intencional de eventos não autoriza estimar a prevalência dos temas no projeto inteiro.

A retirada temporária de configurações da CLI na release reduz a superfície declarativa, mas ainda contribui positivamente à magnitude de mudanças. [afirmação:evento-42]
Conclusão documental sobre configs/model/cfa.yaml no SHA indicado. A mensagem anuncia retorno quando a CLI estiver pronta; remoção não demonstra abandono de configuração nem redução da rastreabilidade em uso. A seleção intencional de eventos não autoriza estimar a prevalência dos temas no projeto inteiro.

A nova CLI usa class_path e init_args para ligar classes de dados e modelos às configurações e callbacks. [afirmação:evento-43]
Conclusão documental sobre configs/model/cflow.yaml no SHA indicado. Declarar callbacks e classes não comprova que o treino foi executado ou que algum logger remoto recebeu os resultados. A seleção intencional de eventos não autoriza estimar a prevalência dos temas no projeto inteiro.

As configurações são movidas para dentro do pacote e o empacotamento é ajustado; a magnitude reflete A/D em caminhos diferentes. [afirmação:evento-44]
Conclusão documental sobre src/anomalib/configs/data/avenue.yaml no SHA indicado. As renomeações preservam conteúdo; o evento seguinte move novamente esses descritores, sem evidenciar mudança equivalente de parâmetros. A seleção intencional de eventos não autoriza estimar a prevalência dos temas no projeto inteiro.

As configurações retornam à raiz e deixam o pacote, revertendo a localização anterior; o movimento constitui evento próprio de magnitude elevada. [afirmação:evento-45]
Conclusão documental sobre configs/data/avenue.yaml no SHA indicado. Este evento pertence a Q3 e não a Q2; mudanças em configuração e teste não asseguram presença de CODE elegível. A seleção intencional de eventos não autoriza estimar a prevalência dos temas no projeto inteiro.

## Limitações

A seleção intencional de eventos não autoriza estimar a prevalência dos temas no projeto inteiro. Commits não são observações independentes e a atividade histórica não certifica práticas organizacionais. CONFIG não representa toda configuração em Python e inclui opções de interface. Renomeações tratadas como remoção/adição e mapas de classes podem dominar a magnitude. O limiar da taxonomia é global e não demonstra igual qualidade em categorias raras; DATA_META permanece ausente. Não foram executados modelos dos casos nem dependências de treino.

Fontes estáticas demonstram capacidade e condições de integração. A ausência de chamadas diretas no adaptador Anomalib não significa ausência de operações herdadas. Disponibilidade de imagem/exportação não prova envio automático a MLflow. As datas reconstruídas das revisões históricas são identificadas como estimativas por sessão, com intervalo e evidência no sidecar; a confirmação nova registra a hora real. Registros redigidos por IA não substituem avaliações independentes nem aprovação institucional. Conteúdo de discussões de PR não coletadas não fundamenta interpretações.

## Conclusão

O conjunto responde ao objetivo de caracterizar mudanças e examinar mecanismos documentados, dentro do recorte técnico proposto. A relação entre código e configuração depende da arquitetura e das representações adotadas; os eventos explicam mecanismos que as contagens isoladas não distinguem. O uso de callbacks, wrappers e delegação ao Lightning estabelece contrastes estruturais. Perguntas que exigem runs, registry ou identidade validada de dados continuam sem resposta; respondê-las requer nova coleta explicitamente separada.

## Fontes e material de auditoria

O catálogo claims_catalog.json contém a referência exata de cada afirmação. O índice definitivo, os manifestos de runs, os blobs/diffs preservados e o parecer docs/ALINHAMENTO_DM027.md integram a cadeia documental. Este texto constitui o manuscrito técnico do estudo; não se presume acesso ao template institucional ou a um manuscrito externo não fornecido.
