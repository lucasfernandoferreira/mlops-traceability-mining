# Log do fechamento DM-027

Solicitação original preservada em `data/interim/fechamento_dm027/prompt_recebido.txt`.
Reconhecimento: `pwd`, `git status --short`, leitura integral dos cinco documentos, Makefile, pyproject.toml e CLIs; `git branch -a`, `git tag`, `git stash list`, `git log --all`, `git reflog --all`, `git fsck --full --no-reflogs --unreachable`.
Branch `feat/dm027-fechamento` criada com escalonamento de sandbox porque `.git` é somente leitura no sandbox.
Comandos seguintes, saídas, códigos e hashes preservados em `data/interim/fechamento_dm027/comandos/`. A atualização deste log ocorre entre execuções, para manter worktree limpo nas verificações.

Bloco 1: `python tools/dm027_prepare.py`. Fontes verificadas por `verified_run(scientific=True)`; especificação confrontada com o índice; origens mantidas; cópia cega sem predições; inventário calculado por leitura dos bytes. Nenhuma consulta ao GitHub ou alteração da taxonomia.

Bloco 2: `python /tmp/dm027_block2.py` (cópia preservada na pasta da tarefa). Métricas indisponíveis extraídas da tabela registrada. Busca em arquivos, arquivos compactados e objetos Git documentada em `busca_registros.json` e `busca_historico.json`; notas anteriores identificadas como rascunhos de IA. Parecer técnico concluído com autoria explícita. Datas da revisão humana anterior importadas como reconstruídas, com suas limitações.

Bloco 3: `dossiers.py` preservou blobs e logs históricos; leitura documentada nos logs de comandos por posição. `julgamentos_cegos.tsv` foi selado por SHA-256 antes do join; `taxonomy.py` produziu a cópia revista e diagnóstico. Dois payloads LFS foram recuperados por media.githubusercontent.com e conferidos contra os ponteiros; a falha DNS inicial e a recuperação estão em logs separados. Nova observação não modifica coleta original. A imagem causal_ladder foi inspecionada visualmente. O controle de proveniência recusa aceite de rascunho de IA sem confirmação.

### Correção da propagação de autoria na fase 6

O run `20260913T180404708895Z_815dd4d7_phase6_validate_taxonomy` revelou perda do sidecar ao copiar `taxonomia_revisada.csv` para `input_sample.csv`: seu aceite é inválido para o fechamento e fica preservado como contraprova. A concordância calculada não mudou. A fase agora transporta os metadados, adapta apenas o nome do arquivo de destino e conserva o hash declarado; a importação empírica também preserva e verifica a autoria. Uma planilha explicitamente atribuída ao assistente sem sidecar é recusada. O teste de integração reproduz a passagem pela fase e exige recusa do rascunho mesmo com concordância integral. Os sete testes selecionados passaram; o comando isolado saiu com código 1 pela cobertura global inaplicável ao subconjunto (37,55%). Ruff passou; a suíte completa será executada no fechamento. Comandos e saídas em `data/interim/fechamento_dm027/comandos/`.
