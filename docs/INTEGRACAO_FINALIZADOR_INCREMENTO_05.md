# Integração da verificação ao finalizador — incremento 5

Este incremento implementa o controle G13 na branch
`feat/integracao-verificacao-finalizador`, após o merge do incremento 4.
A política de verificação passa a **1.3.0**. Protocolo científico 2.1.0,
taxonomia 1.1.0, análise 1.0.0 e locks permanecem iguais.

## Contrato da finalização

`make finalize-study` exige `VERIFICATION_RECEIPT`; a CLI recebe
`--verification-receipt`. Sua ausência na CLI produz recusa registrada, sem
suprimir os controles de seleção dos casos, validação taxonômica, alinhamento
acadêmico, codificação, seleção qualitativa, relatório e cadeia científica.

O novo módulo `verification/finalization.py` confere:

- Versões do recibo e da política, hash do índice, manifestos e artefatos das
  fontes explícitas, seleção e relatório. O manifesto da seleção agora também
  aparece no inventário de manifestos do recibo empírico.
- Inventário obrigatório de revisões, origens e cópias preservadas. A amostra
  usada na validação taxonômica e os três arquivos de revisão usados na
  finalização devem ter os mesmos hashes dos arquivos verificados.
- Hashes e caminhos relativos das provas, incluindo bloqueio de caminhos que
  saem da raiz declarada. Todas as provas citadas pelos critérios devem estar
  vinculadas no inventário.
- Escopo empírico, worktree limpo, revisão Git atual, exatamente G00–G13 e todos
  os critérios obrigatórios aprovados. Recibo sintético, parcial ou com erro não
  libera candidato.
- Reexecução empírica obrigatória para qualquer recibo que alegue PASS completo.
  A reexecução deve passar, manter os vínculos e reproduzir os resultados dos
  critérios. Recalcular hashes de um recibo forjado não substitui essa execução.

Recibos já reprovados são recusados sem repetir todo o oráculo Git. O diagnóstico
fica em `verification_assessment.json` e no recibo de finalização. Se houver
reexecução, inclusive recusada, suas provas são preservadas em
`verification_replay.zip`, vinculado pelo manifesto do run. Isso conserva o
contrato existente de nomes únicos dos artefatos, apesar dos subdiretórios das provas.

G13 confere os vínculos do próprio recibo por meio desse mesmo controle e registra
`finalization_contract.json`. Essa conferência não transforma os demais critérios
pendentes em aprovados; alterações locais no verificador continuam reprovando G13.

## Candidato e aceite final

`candidate_eligible` requer simultaneamente os controles anteriores e a verificação
empírica. Somente nessa condição o finalizador pode gerar `reproduction.zip`.
O manifesto interno identifica `package_status=candidate`,
`scientific_result_accepted=false` e G14/G15 pendentes.

O pacote inclui as provas fornecidas, as recalculadas e as entradas vinculadas em
`verification_evidence.zip`. O recibo agregado `study_acceptance.json` fica **fora**
do candidato e contém seu hash, evitando autorreferência. O rascunho registra a
condição de candidato e não alega assinatura ou aprovação acadêmica.

G14 e G15 ainda não têm verificadores neste incremento. Portanto, nenhuma execução
atual emite aceite científico final, mesmo no caminho de geração do candidato;
a CLI de finalização continua retornando 1. Não há opção para ignorar esses critérios.
Os testes que simulam um futuro verificador completo validam apenas a montagem
do pacote e são explicitamente sintéticos.

## Reprodução da execução local

O índice permanece `20260909T144632500174Z_af5a0048_study_index`; a pasta de revisões
é `data/interim/reviews/reprocessamento_20260909T144632500174Z_af5a0048_study_index`.
Não houve nova mineração, seleção produtiva ou consulta à API.

Antes das alterações, a amostra local foi avaliada em
`20260910T013606153734Z_8a7ca990_phase6_validate_taxonomy`, com worktree limpo.
O processamento terminou com SUCCESS e a validação foi recusada, como esperado
para os campos humanos vazios disponíveis. Isso descreve os arquivos locais;
não contradiz a informação do pesquisador sobre revisões já realizadas.

Após commit e merge, execute a verificação com worktree limpo:

```sh
make verify-study \
  STUDY_INDEX=data/interim/runs/20260909T144632500174Z_af5a0048_study_index/study_index.json \
  REVIEW_DIR=data/interim/reviews/reprocessamento_20260909T144632500174Z_af5a0048_study_index
```

Use o caminho do novo recibo em `VERIFICATION_RECEIPT`. A finalização também
exige o run de validação correspondente aos mesmos bytes de revisão, os runs
qualitativo e de relatório e os três arquivos humanos. O exemplo genérico está
no [README](../README.md). Uma revisão atualizada exige nova validação e novo
recibo; não se reutiliza aprovação de outra rodada.

## Testes e contraprovas

A [suíte completa](evidencias/validacao_finalizador_incremento_05.txt) passou com
**258 testes e 94,28% de cobertura**. As
[51 contraprovas](evidencias/contraprovas_incremento_05.xml) passaram.
Os cenários novos exercitam revisão/índice/taxonomia/prova alterados, inventário
removido, caminhos fora da raiz, recibo sintético, escopo incompleto, critério
duplicado, NOT_RUN, erro de processamento, versão Git divergente e PASS forjado.
A recusa do PASS forjado é demonstrada com reexecução real sobre fontes sintéticas;
o caminho de empacotamento aprovado usa um verificador simulado e não constitui
evidência empírica de aceite.

O baseline `make check` passou antes das alterações. Depois delas, lint,
formatação, mypy e todos os testes passaram; o smoke científico recusou o worktree
dirty, conforme seu contrato. `make lint format-check typecheck smoke-dev` passou.
O log registra ambos os resultados, sem apresentar essa recusa como aprovação.

O run `20260910T014523835049Z_8a7ca990_phase9_finalize_study` demonstra a recusa do
recibo do incremento 4 por incompatibilidade da política 1.2.0 com a atual 1.3.0.
Seu processamento terminou em SUCCESS, sem candidato ou aceite, e preservou os
demais bloqueios de revisão e cadeia científica. O manifesto e seus nove artefatos
foram reconferidos. A execução usou `--allow-dirty` e não é uma finalização científica.

## Resultado empírico

A execução `data/interim/verification/incremento_05/empirical_01/` terminou com
**FAIL, saída 1, sem erros de processamento**. G03, G05, G06, G08, G09 e G10 passaram.
Os três casos não apresentaram diferenças no histórico, maturidade, métricas ou
estatísticas descritivas. A seleção qualitativa foi novamente reconciliada.

O controle de vínculos de G13 passou: **248 entradas, 12 manifestos e cinco
arquivos de revisão/origem**. O recibo final vincula **25 provas**, incluindo
`finalization_contract.json`. A contagem interna desse contrato é 24 porque ele
foi escrito após conferir as demais provas e foi acrescentado ao inventário final.
G13 ficou FAIL **somente por `dirty_verifier_worktree`**; o motivo anterior de
integração ausente deixou de existir.

G01 e G07 continuam FAIL pelos arquivos humanos disponíveis. G00, G02, G04, G11
e G12 continuam NOT_RUN. O agregado permanece bloqueado; os testes não completam
esses critérios por inferência. O código foi executado sobre a base Git do merge
`8a7ca99`, com alterações locais preservadas no snapshot do verificador.

O run `20260910T015606329783Z_8a7ca990_phase9_finalize_study` consumiu esse recibo
novo. Conferiu os vínculos das 248 entradas, 25 provas e cinco revisões/origens,
recusou sua condição de worktree dirty e manteve os controles humanos pendentes.
Não repetiu o oráculo porque o recibo já era FAIL, nem gerou candidato ou aceite.
Os 86 arquivos de código, testes, configuração e locks do snapshot foram
comparados com os arquivos usados nesta entrega, sem diferenças.

O [registro versionado](evidencias/integracao_finalizador_incremento_05.json)
preserva o recibo, os hashes das provas e os resultados das duas finalizações de
recusa. Os artefatos integrais permanecem locais nos caminhos registrados.

## Próximas entregas

Completar resolução de evidências e catálogo de afirmações (G02/G11/G12),
consolidar as provas obrigatórias de G00/G04 e incorporar os arquivos de revisão
concluídos quando sua origem estiver disponível. Depois, preparar o manuscrito,
gerar candidato e implementar a restauração isolada e a conferência G14/G15.
