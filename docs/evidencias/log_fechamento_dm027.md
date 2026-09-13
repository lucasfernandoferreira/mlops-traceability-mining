# Log do fechamento DM-027

Solicitação original preservada em `data/interim/fechamento_dm027/prompt_recebido.txt`.
Reconhecimento: `pwd`, `git status --short`, leitura integral dos cinco documentos, Makefile, pyproject.toml e CLIs; `git branch -a`, `git tag`, `git stash list`, `git log --all`, `git reflog --all`, `git fsck --full --no-reflogs --unreachable`.
Branch `feat/dm027-fechamento` criada com escalonamento de sandbox porque `.git` é somente leitura no sandbox.
Comandos seguintes, saídas, códigos e hashes preservados em `data/interim/fechamento_dm027/comandos/`. A atualização deste log ocorre entre execuções, para manter worktree limpo nas verificações.

Bloco 1: `python tools/dm027_prepare.py`. Fontes verificadas por `verified_run(scientific=True)`; especificação confrontada com o índice; origens mantidas; cópia cega sem predições; inventário calculado por leitura dos bytes. Nenhuma consulta ao GitHub ou alteração da taxonomia.

Bloco 2: `python /tmp/dm027_block2.py` (cópia preservada na pasta da tarefa). Métricas indisponíveis extraídas da tabela registrada. Busca em arquivos, arquivos compactados e objetos Git documentada em `busca_registros.json` e `busca_historico.json`; notas anteriores identificadas como rascunhos de IA. Parecer técnico concluído com autoria explícita. Datas da revisão humana anterior importadas como reconstruídas, com suas limitações.
