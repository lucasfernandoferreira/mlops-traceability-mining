# Proposta de amostra e registro da inspeção fornecida

Estado: **seleção operacional MLflow para piloto, protocolo 2.0.0**.
A seção histórica abaixo descreve o estado anterior; DM-018 a DM-021 registram a revisão.
Este registro não finaliza `config/amostra_final.yaml` e não substitui a shortlist
automática. Os seis candidatos pertencem ao estrato `apenas_mlflow`; portanto,
os três casos principais não satisfazem a exigência então vigente de três estratos.

## Origem e limites da verificação

As justificativas qualitativas abaixo foram fornecidas pelo pesquisador no texto
“O projeto está tecnicamente na Fase 2, mas cientificamente ainda está no gate…”.
Identificador do anexo: `7c70609e-9b84-4214-bba3-ed42e8bc24c2/pasted-text.txt`.
SHA-256 do texto original:
`22f74652ddf87a4eed30be1c706be5141690c19042cd35bc09e797ea5c04b485`.
O texto relata uma revisão remota, mas não contém os links específicos das issues,
PRs ou arquivos inspecionados. Esses links ainda precisam compor o registro final.
Não houve uma nova inspeção remota durante a transcrição deste documento.

Os nomes, SHAs, estratos e contagens foram conferidos contra a shortlist local:

- Fase 1: `20260831T030743921886Z_bb7d2ee1_phase1_search_candidates`.
- Fase 2: `20260831T121157885962Z_fc55f2d9_phase2_screen_sample`.
- Arquivo: `data/interim/runs/20260831T121157885962Z_fc55f2d9_phase2_screen_sample/shortlist.csv`.
- SHA-256: `69f0891d3a8d029d7e7ea44115c4ea7a88dbb5074eef4bfc5b843dc3d3acbfe2`.

Os manifestos locais dessas execuções registram `SUCCESS` e
`dirty_worktree=false`. A triagem contém 59 elegíveis e nenhum erro: 53 apenas
MLflow, quatro apenas DVC e dois com ambas as ferramentas. Os artefatos são locais
e ignorados pelo Git; a publicação do pacote empírico permanece uma tarefa distinta.

O anexo cita a revisão remota `d099449`. O checkout usado para esta conferência
estava em `fc55f2d945f36e64d3b2249d4615ff767bf91db7`, antes das alterações locais.
Não foi realizada atualização de branch para assumir equivalência entre revisões.

## Casos principais e reservas propostos

Contagens referentes à coleta de 31/08/2026, antes dos filtros de mineração.

| Ordem | Repositório | Commits brutos | Contribuidores | Justificativa fornecida e cuidado |
|---|---|---:|---:|---|
| Principal 1 | `ultralytics/ultralytics` | 4.974 | 441 | Treinamento registra parâmetros, métricas e artefatos de modelos; integração localizada. O parser deve reconhecer modelos registrados como artefatos. Caso proposto para o primeiro piloto. |
| Principal 2 | `pymc-labs/pymc-marketing` | 1.506 | 88 | Registro de dados de entrada, versões de bibliotecas, configuração e modelos, em domínio diferente de visão computacional. O anexo relata clone volumoso; medir custo no piloto. |
| Principal 3 | `mosaicml/composer` | 2.701 | 121 | Logger com operações explícitas de experimentos, hiperparâmetros e registro de modelos. |
| Reserva 1 | `open-edge-platform/anomalib` | 1.134 | 119 | Detecção de anomalias e histórico menor. Parte da instrumentação é delegada ao Lightning. |
| Reserva 2 | `axolotl-ai-cloud/axolotl` | 2.922 | 247 | Callback registra configuração de treinamento como artefato; acrescenta fine-tuning de LLMs e configurações mais complexas. |
| Reserva 3 | `roboflow/rf-detr` | 1.094 | 93 | Treinador instancia `MLFlowLogger`; exige interpretação de operações delegadas ao Lightning. |

Os principais somam **9.181 commits brutos**. Esse número não comprova o mínimo
de commits elegíveis após excluir merges, bots e mudanças acima do limite.

### SHAs observados para o futuro congelamento

| Repositório | `head_commit_sha` da shortlist |
|---|---|
| `ultralytics/ultralytics` | `fa34184a5080c81fff453670394e13303ac781b2` |
| `pymc-labs/pymc-marketing` | `fabba92c96aa6a4ec6d42fb3241a8ed725995d0a` |
| `mosaicml/composer` | `6405188805a0054b4551ec49e4919c54c971d0e8` |
| `open-edge-platform/anomalib` | `0b7fdb9dde453f6474ac93f77188f4224d442999` |
| `axolotl-ai-cloud/axolotl` | `917a3d041972eb33be5d6fcbb40ac1681fd2b8f4` |
| `roboflow/rf-detr` | `6674d8581b7694baf567b993a4f32000a6f4f4c2` |

As reservas só devem substituir casos por elegibilidade, acesso ou custo de
processamento, segundo critérios registrados antes de observar as métricas.
O motivo de cada substituição deve ser documentado; resultados pouco interessantes
não constituem critério de substituição.

## Candidatos não priorizados na inspeção fornecida

Esses julgamentos tratam da adequação ao objeto do TCC. As decisões automáticas
`eligible` permanecem intactas na shortlist original.

| Repositório | Evidência relatada | Encaminhamento proposto |
|---|---|---|
| `pathwaycom/pathway` | DVC em teste de grafo e MLflow em avaliações RAG de integração. | Não usar como caso de integração DVC+MLflow sem demonstrar uso no mesmo pipeline. |
| `hongbo-miao/hongbomiao.com` | Pipeline DVC com dados, parâmetros e modelo; treinamento inspecionado registra no W&B. | Não selecionar como combinado sem vínculo com MLflow; monorepositório com 45.160 commits. |
| `evidentlyai/evidently` | DVC associado a dados e snapshots de testes visuais. | Não priorizar como evidência de proveniência dataset de treinamento–modelo. |
| `owid/etl` | Snapshots DVC em sistema real de processamento de dados. | Treinamento pertinente ao objetivo não confirmado; 17.053 commits. |
| `ROCm/rocm-systems` | DVC para bibliotecas PAL de interoperabilidade. | Baixa aderência ao objeto dataset–treinamento–modelo; 86.209 commits. |
| `ROCm/rocm-libraries` | DVC armazena bancos de kernels no MIOpen. | Objeto diferente e custo elevado de mineração; 101.610 commits. |

## Decisão sobre o recorte e GQM 3

O recorte proposto é estudar mecanismos públicos de rastreabilidade de
configurações, dados e modelos em três projetos maduros com integração MLflow.
A decisão de adotá-lo ainda precisa ser formalizada no protocolo, no mapa GQM e
nas limitações, incluindo a retirada da comparação entre ferramentas.

O detector automático marcou `mlruns_detected=false` nos 59 elegíveis, mas só
procura `mlruns/` na raiz. O texto fornecido relata inspeção adicional, inclusive
de diretórios aninhados, sem encontrar `mlruns` nos seis recomendados. Essa segunda
observação deve ser acompanhada de evidência na finalização da inspeção; não prova
ausência em todo o histórico nem em serviços externos.

Se as fontes necessárias continuarem indisponíveis, métricas diretas de runs e
promoções recebem `not_available`. Evidência estática MLflow/AST deve ficar em
colunas próprias e não comprova que a instrumentação foi executada. O trilho DVC
estrutural exige saída de modelo, dependência de dado e hash no `dvc.lock`.

## Pendências registradas antes da revisão 2.0.0

1. Registrar a decisão sobre manter os três estratos ou adotar o recorte MLflow.
2. Completar os links e caminhos nos SHAs inspecionados, justificativas finais,
   responsável e data da decisão de inclusão/exclusão.
3. Calibrar CONFIG: `ultralytics/cfg/default.yaml`,
   `data/config_files/basic_model.yml` e `examples/configs/model/patchcore.yaml`
   não são cobertos pelas regras atuais. Validar precedência e falsos positivos.
4. Rever a dimensão de dados, hoje restrita a `DATA_META`/DVC. Falta de metadados
   observáveis não deve produzir uma conclusão de desacoplamento.
5. Consolidar fórmulas, denominadores e status antes de implementar métricas.
6. Definir cobertura de chamadas diretas, `log_artifact(s)`, callbacks e delegação
   ao Lightning no parser, com limites explícitos de inferência.
7. Finalizar `amostra_final.yaml` e implementar clonagem completa no SHA observado,
   manifesto, retomada e idempotência. Medir o custo de obtenção do PyMC Marketing.

As decisões e os limites de custo devem anteceder a substituição de um caso.
O piloto proposto para Ultralytics deve percorrer clonagem, classificação, métrica
e tabela antes da mineração completa dos três casos.


## Atualização executada em 05/09/2026

Responsável pelo registro técnico: Codex, a pedido do pesquisador. Não constitui
validação humana independente ou aprovação da orientadora. Os hashes de todos os
artefatos dos runs citados foram rechecados, incluindo instrumentos no commit original.
O congelamento registra `source_audit.json` com essa proveniência.

| Caso | Uso no SHA inspecionado | Manutenção vinculada ao SHA | Decisão |
|---|---|---|---|
| Ultralytics | [callbacks MLflow](https://github.com/ultralytics/ultralytics/blob/fa34184a5080c81fff453670394e13303ac781b2/ultralytics/utils/callbacks/mlflow.py) | [histórico](https://github.com/ultralytics/ultralytics/commits/fa34184a5080c81fff453670394e13303ac781b2/) | Piloto; parâmetros, métricas e pesos como artefatos |
| PyMC Marketing | [integração MLflow](https://github.com/pymc-labs/pymc-marketing/blob/fabba92c96aa6a4ec6d42fb3241a8ed725995d0a/pymc_marketing/mlflow.py) | [histórico](https://github.com/pymc-labs/pymc-marketing/commits/fabba92c96aa6a4ec6d42fb3241a8ed725995d0a/) | Caso seguinte; contraste de domínio e dados |
| Composer | [logger MLflow](https://github.com/mosaicml/composer/blob/6405188805a0054b4551ec49e4919c54c971d0e8/composer/loggers/mlflow_logger.py) | [histórico](https://github.com/mosaicml/composer/commits/6405188805a0054b4551ec49e4919c54c971d0e8/) | Caso seguinte; log_model/register_model e cliente |

Os três arquivos foram consultados remotamente nesta sessão. Os links de histórico
são localizadores para a conferência humana de manutenção; não atestam revisão de
issues/PRs específicas. Os SHAs não foram atualizados para heads mais recentes.
A conferência automatizada exaustiva da árvore e do histórico é executada somente para
o piloto Ultralytics nesta entrega. O gate de atividade suplementar dos outros dois
casos será executado antes da seleção final.

CONFIG 1.1.0 cobre cfg/config/configs/config_files aninhados e conserva precedência
TEST → CI → ENV → DATA_META → CONFIG. Os três exemplos do parecer e controles negativos
compõem regressões automatizadas. A amostra real para revisão humana é saída da Fase 4.
Ela ainda não comprova concordância de 95%.
