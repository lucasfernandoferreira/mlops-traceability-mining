# Auditoria da consolidação documental DM-027

Data: 15/09/2026. Baseline: `7318222096720b0f2c74bb0c1859beaed89591da`,
`main`, PR #17. Worktree inicialmente limpo; branch própria
`docs/dm027-consolidacao-final`. Escopo estritamente documental, sem nova coleta,
mineração, classificação, seleção qualitativa ou julgamento humano.

## A. Arquivos alterados e justificativas

| Caminho | Motivo e tipo de alteração | Natureza |
|---|---|---|
| `README.md` | Corrige estado corrente, distingue recibos, aponta entrada canônica e próxima etapa. | Documental |
| `docs/ESTADO_FINAL_DM027.md` | Nova página canônica: identidade, casos, avaliações, gates, resultados e limites. | Documental |
| `docs/evidencias/manifesto_final_dm027.json` | Novo índice estruturado, com caminhos, disponibilidade e hashes de origem. | Estrutural/documental |
| `docs/evidencias/recibo_final_dm027.json` | Nova cópia literal do recibo local aceito; nenhuma edição de status. | Documental/evidência preservada |
| `docs/evidencias/confirmacao_pesquisador_dm027_extrato.json` | Novo extrato explicitamente identificado, com referência à confirmação integral. | Estrutural/documental |
| `docs/evidencias/README.md` | Novo índice temporal de snapshots, rascunhos e fechamento; orientação de acesso. | Documental |
| `docs/evidencias/auditoria_estados_dm027.csv` | Nova relação de ocorrências no baseline e tratamentos individuais. | Estrutural/documental |
| `docs/AUDITORIA_CONSOLIDACAO_DM027.md` | Este relatório e roteiro de auditoria externa. | Documental |
| `docs/CRITERIOS_ACEITE_E_EVIDENCIAS.md` | Atualiza introdução e delimita explicitamente o histórico dos incrementos. | Documental |
| `docs/DECISOES_METODOLOGICAS.md` | Corrige avaliação atual e estado da seleção, mantendo método e decisões. | Documental |
| `docs/GQM_MAPA_METRICAS.md` | Esclarece universo final e confirmação posterior, sem mudar fórmulas. | Documental |
| `docs/INSPECAO_MANUAL_AMOSTRA.md` | Atualiza apenas cabeçalho de estado, preservando narrativa histórica. | Documental |
| `docs/DM027_TAXONOMIA_1_2_0.md` | Atualiza apenas cabeçalho de estado, preservando diagnóstico e prévias. | Documental |
| `docs/LIMITACOES_E_VALIDADE.md` | Acrescenta contexto do fechamento e desvio em relação à proposta original. | Documental |

Nenhum arquivo de código, teste, configuração científica ou evidência preexistente
foi alterado. Manuscrito, síntese, parecer e procedimento G14 foram examinados e
preservados por seus vínculos de hash, conforme o [índice temporal](evidencias/README.md).

## B. Inconsistências encontradas

A [planilha de auditoria](evidencias/auditoria_estados_dm027.csv) registra
**456 linhas**, com os termos encontrados, trechos originais, localização e
tratamento: **279 histórico legítimo**, **170 ambígua**, **6 documentação corrente
desatualizada** e **1 erro factual documental**. Linhas e trechos referem-se ao
baseline acima; o relatório local ignorado refere-se à versão de 14/09 examinada.
Múltiplos termos na mesma linha ficam juntos, sem perder sua localização.

A busca cobriu arquivos textuais rastreados, incluindo código, testes e contratos,
e o relatório local de pré-confirmação. Procurou `pending`, `pilot`/`piloto`,
`aguarda`, `pendente`, os campos de estado solicitados, implementação/avaliação
ausentes e expressões de ato humano futuro. A leitura contextual dos documentos
adicionou ocorrências sem esses termos exatos. Identificadores e estados genéricos
legítimos foram preservados como contratos, sem confundi-los com o estado do estudo.
Arquivos de restaurações, dependências e caches não foram tratados como documentos
correntes; os recibos locais finais foram lidos diretamente para conferir o baseline.

### Corrigidas ou esclarecidas

- README e método ainda indicavam avaliação da 1.2.0 e seleção definitiva em aberto.
  Agora registram fechamento, confirmação e concordância reais.
- README descrevia G14/G15 como ainda não implementados. A implementação existe;
  o texto agora distingue fase 9, restauração e recibo final.
- Introduções de critérios, casos e dossiê apontavam ao relatório local antigo.
  Agora apontam ao estado aceito em 15/09.
- Mapa GQM apresentava confirmação como futura. O texto preserva o parecer
  original e identifica sua confirmação posterior, sem inferir aprovação externa.
- `rodada_atual.json`, catálogo e pareceres preliminares tinham temporalidade
  ambígua para um novo leitor. O índice explicita suas etapas e cópias confirmadas.

### Preservadas por serem históricas ou vinculadas por hash

- `config/amostra_final.yaml`: snapshot histórico e entrada científica. Seu hash
  `4c3b492dbae6e46fca697731fa006f4777b8670abe7628134583c0cbbc9ca38c` integra a
  confirmação. Nenhum metadado foi acrescentado; a explicação fica fora do arquivo.
- Reprovação da taxonomia 1.1.0, prévias, incrementos, modelos vazios e recibos FAIL,
  NOT_RUN ou de ensaio: preservam as decisões e controles na etapa correspondente.
- Redações `draft_pending_confirmation`, manuscrito e log: preservam autoria e
  instantes originais. A confirmação posterior não reescreve essas datas.
- Recibo intermediário de 15/09 com aceite falso: antecede G14/G15. O recibo final
  posterior tem aceite verdadeiro; não há contradição científica entre seus escopos.

### Ainda abertas

**D01 — distribuição do acervo:** os dados, revisões confirmadas integrais,
recibo empírico, relatório G14, candidato, bundle e clones estão disponíveis
localmente, mas são ignorados pelo Git. Não há URL pública integral registrada.
O manifesto declara esse limite e indexa os caminhos. Para recálculo externo,
o pesquisador precisa entregar o acervo inventariado à orientadora. Não se deve
refazer coleta para suprir uma lacuna de distribuição.

Não foi encontrada inconsistência científica material nas fontes examinadas.
O erro factual identificado é de documentação corrente, corrigido sem modificar
qualquer resultado. D01 é uma lacuna de entrega, não uma reprovação de G14.

## C. Estado científico final

Protocolo **TCC-MLOPS-TRACE-2026 2.1.0**, taxonomia **1.2.0**, **173/180 = 96,11%**
de concordância, limiar **95%**, **45 eventos (15 por caso)**, **G00–G15 PASS**,
restauração sem divergências e **`scientific_result_accepted: true`**.

| Caso | SHA preservado |
|---|---|
| `ultralytics/ultralytics` | `fa34184a5080c81fff453670394e13303ac781b2` |
| `pymc-labs/pymc-marketing` | `fabba92c96aa6a4ec6d42fb3241a8ed725995d0a` |
| `open-edge-platform/anomalib` | `0b7fdb9dde453f6474ac93f77188f4224d442999` |

Os seis `not_available` permanecem sem valor. O objetivo operacional e as limitações
permanecem conforme o [estado final](ESTADO_FINAL_DM027.md).

## D. Validação desta consolidação

| Comando | Resultado real nesta rodada |
|---|---|
| `make lint format-check typecheck test smoke-dev` | Saída 0: lint aprovado; 103 arquivos com formatação correta; mypy sem problemas em 77 arquivos; **310 testes aprovados, 93,81% de cobertura**; smoke de desenvolvimento aprovado. |
| `make check` | Saída 0 em `5f46e7a` (antes de acrescentar este registro de validação): lint, formatação, tipagem, **310 testes**, **93,81% de cobertura** e smoke com worktree limpo aprovados. Log `tmp/consolidacao_dm027/make-check.log`. |
| `.venv/bin/python tmp/consolidacao_dm027/validate_dm027_docs.py` | Conferência documental aprovada: 146 arquivos científicos preexistentes idênticos ao baseline; 17 documentos/configurações vinculados à confirmação intactos; 27 artefatos existentes; 23 hashes preexistentes coincidentes; três SHAs e 16 gates coerentes. |
| `git diff --check 7318222096720b0f2c74bb0c1859beaed89591da` | Saída 0; nenhuma falha de whitespace. |

Os três JSONs novos foram lidos sem erro; nenhum YAML foi modificado. Foram
conferidos 102 links relativos e âncoras dos documentos novos/alterados, sem
referências quebradas. As provas dos gates no manifesto também existem, com seus
37 hashes coincidentes. As 36 linhas de métricas mantêm 18 resultados observados
e 18 indisponibilidades sem valor (seis por caso). Nenhuma evidência histórica foi
removida. A leitura das fontes confirmou os 45 eventos, 15 por caso, e o aceite
taxonômico, sem nova execução científica.

Logs e script da conferência documental estão em `tmp/consolidacao_dm027/`,
local ignorado pelo Git. Os testes completos passaram sem skips ou falha por
insumos ausentes; suas fixtures não substituem as fontes empíricas locais exigidas
na conferência dos hashes do manifesto e na restauração G14. Nenhuma consulta ao
GitHub foi executada nesta rodada.

O registro final altera apenas este relatório. O baseline histórico de CI é
separado dos resultados desta consolidação; o código e os contratos científicos
permanecem idênticos. O diff integral para revisão é produzido por
`git diff --binary 7318222096720b0f2c74bb0c1859beaed89591da HEAD`, preservado em
`tmp/consolidacao_dm027/diff-completo.patch`. Não foi realizado merge ou push.

## E. Pendências do pesquisador e da orientadora

- Realizar a transposição para o manuscrito acadêmico final e sua revisão.
- Avaliar academicamente o recorte operacional e a adequação da mudança em
  relação ao projeto original. G12 e a confirmação do pesquisador não são aceite
  institucional ou da orientadora.
- Definir se alguma pergunta GQM indisponível será exigida. Se sim, formalizar nova
  rodada, sem incorporar fontes ou resultados retroativamente ao DM-027.
- Resolver a entrega do acervo necessário à auditoria com recálculo (D01).

## F. Recomendação

**READY_WITH_DOCUMENTATION_GAPS**, em razão de D01: a leitura documental está
organizada, mas o acervo completo necessário ao recálculo externo precisa ser
entregue por meio documentado. O fechamento científico permanece aceito.

## Roteiro de 20 perguntas para auditoria externa

| # | Pergunta | Onde responder | Gap |
|---|---|---|---|
| 1 | Qual era o problema científico? | Estado final, seção 5; mapa GQM e parecer de alinhamento. | Nenhum de leitura. |
| 2 | Qual era o protocolo? | Estado final, seção 1; config/config.yaml e método. | Nenhum. |
| 3 | Quais foram os casos? | Estado final, seção 2. | Nenhum. |
| 4 | Por que foram escolhidos? | Estado final, seção 2; inspeção manual. | Nenhum. |
| 5 | Quais SHAs foram analisados? | Estado final, seção 2; manifesto e runs_dm027.json. | Nenhum. |
| 6 | Qual taxonomia foi usada? | Estado final, seção 1; file_taxonomy.yaml. | Nenhum. |
| 7 | Como foi validada? | Estado final, seção 3; método e dossiê. | D01 para insumos integrais. |
| 8 | Qual foi a concordância? | Estado final, seção 3; avaliação preservada. | Nenhum de leitura. |
| 9 | Quais métricas foram observadas? | Estado final, seção 5; manuscrito técnico. | Nenhum de leitura. |
| 10 | Quais ficaram indisponíveis? | Estado final, seção 6; mapa GQM. | Nenhum. |
| 11 | Quais resultados quantitativos existem? | Estado final, seção 5; manuscrito e manifesto. | D01 para tabelas/figuras locais. |
| 12 | Como foram selecionados os eventos? | Estado final, seção 5; método, análise qualitativa. | D01 para PRs e provas integrais. |
| 13 | Quantos eventos foram analisados? | Estado final, seções 3 e 5; síntese. | Nenhum. |
| 14 | Quais são as limitações? | Estado final, seção 7; limitações e validade. | Nenhum. |
| 15 | Quais verificações automatizadas? | Estado final, seção 4; seção D deste relatório. | D01 para provas empíricas integrais. |
| 16 | O estudo pode ser restaurado? | Estado final, restauração e acesso; procedimento G14. | D01; ZIP/checkout sozinhos não bastam. |
| 17 | Onde está o catálogo? | Manifesto: draft_claims_catalog e confirmed_claims_catalog. | D01 para cópia confirmada integral. |
| 18 | Qual o estado final? | README, estado canônico e recibo final versionado. | Nenhum. |
| 19 | O que falta para o TCC? | Estado final, seção 8; seção E deste relatório. | Decisão acadêmica futura explicitada. |
| 20 | O que exige nova rodada? | Estado final, seção 8; aviso no README. | Nenhum. |
