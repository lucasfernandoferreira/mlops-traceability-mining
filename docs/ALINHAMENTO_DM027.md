# Parecer técnico sobre o recorte operacional DM-027

Autoria: assistant:codex-dm027-fechamento. Modalidade: ai_drafted_pending_confirmation.
Este parecer é uma análise técnica redigida por IA para revisão e assunção autoral pelo pesquisador.
Não representa manifestação nem aprovação da orientadora ou de uma instituição.

## Decisão fundamentada

Recomendo aceitar o recorte operacional abaixo como estudo descritivo de casos de engenharia de software. A contribuição é examinar mecanismos e limites observáveis de rastreabilidade nos artefatos públicos. A contribuição não inclui medir a rastreabilidade efetivamente praticada por organizações usuárias nem comparar a eficácia de ferramentas. O recorte só sustenta submissão se o objetivo e as perguntas do manuscrito adotarem essa delimitação.

Objetivo operacional: Caracterizar mudanças conjuntas de código e configuração e examinar os mecanismos de integração MLflow documentados nos projetos públicos selecionados, delimitando o alcance e as lacunas das evidências de rastreabilidade.

## Resolução do escopo MLflow

MLflow delimita a seleção e a investigação documental dos mecanismos. As medidas de coalteração e magnitude derivam do Git, não de execuções MLflow. Logo, diferenças entre casos não podem ser atribuídas ao uso de MLflow. Bibliotecas que disponibilizam uma integração constituem casos estruturais pertinentes; disponibilizar uma API não comprova sua ativação.

A DM-026 explicita operações herdadas do Lightning no Anomalib: a cadeia depende da injeção do logger no Trainer, do modelo e da configuração. O callback de imagem removido não sustenta envio automático atual. A decisão de manter operações herdadas é retrospectiva e deve permanecer identificada.

## Resolução do mapeamento de métricas

Pergunta operacional PO1: qual proporção dos commits elegíveis com código também altera configuração? Respondida descritivamente por code_config_cochange, condicionada à validação da taxonomia. Numerador C∩P, denominador C; não mede dependência causal nem completude da proveniência.

PO2: qual a magnitude e a distribuição das mudanças CONFIG? Respondida por config_magnitude, quantis, séries e sensibilidade; folhas YAML de classes, datasets e movimentos de caminho podem dominar a medida. Ela não conta somente hiperparâmetros.

PO3: quais mecanismos de integração MLflow são sustentados pelo código e pelos eventos selecionados? Parcialmente respondida pelas fichas, codificação e contadores static_mlflow_param_calls, static_mlflow_metric_calls, static_mlflow_artifact_calls e static_mlflow_model_calls. AST é um indício sintático com falsos positivos e negativos; operações delegadas e wrappers exigem leitura documental.

As perguntas GQM sem fonte continuam sem resposta: cace_index, data_code_cochange, data_code_ratio_original, env_versioning_rate, experiment_redundancy, provenance_coverage. Não são convertidas em zero ou respondidas por substituição terminológica. O objetivo operacional adotado comporta essas lacunas porque se restringe a mecanismos documentados e sinais de mudança.

## Efeito da DM-027

A ampliação de CODE para código de interface e novas extensões altera C; configurações de modelos/datasets reconhecidas alteram P e magnitude. Isso melhora a cobertura de papéis observados, mas amplia a distância entre CODE e código de treinamento. A versão anterior e a nova devem ser comparadas como sensibilidade metodológica, sem selecionar a mais conveniente. A calibração informada por divergências e o papel da IA na nova avaliação devem ser declarados. Confirmação de rascunhos de IA não cria um segundo avaliador independente.

## Adequação e alternativa de escopo

As lacunas são aceitáveis para o objetivo operacional descrito, condicionadas a validade taxonômica e conferência das fontes. Se o compromisso acadêmico exigir cobertura de proveniência, ambientes por run ou promoções, será preciso um estudo ampliado: definir universo de versões/runs, verificar acesso público, preservar uma nova observação separada, implementar ingestão de tracking/registry e validar vínculos código–dados–run. Essa extensão modifica fontes e unidades; não pode ser retroativamente atribuída à coleta atual.

A seleção é intencional. A análise não estima prevalência dos temas nem estabelece representatividade estatística dos projetos MLOps. Milhares de commits de um mesmo caso não constituem réplicas independentes. Nenhuma aprovação acadêmica externa foi localizada na busca desta sessão.

## Fontes e decisão registrada

Fontes: docs/GQM_MAPA_METRICAS.md; docs/DECISOES_METODOLOGICAS.md; docs/DM026_E_FECHAMENTO_TAXONOMIA.md; docs/DM027_TAXONOMIA_1_2_0.md; metricas_consolidadas.csv da rodada de referência; rascunhos anteriores preservados em data/interim/documentation/validacao_amostra_recebida_20260911T145350982191Z/originais/.
Os rascunhos anteriores declaram autoria de IA e não foram importados como decisões humanas. O registro estruturado desta análise usa as chaves canônicas do projeto e aliases em português solicitados no fechamento.
