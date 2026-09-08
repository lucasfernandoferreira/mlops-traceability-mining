# Organização e preservação dos dados

Os dados da pesquisa são organizados por execução para manter a relação entre fonte,
instrumento e resultado. Uma nova coleta ou revisão produz novos arquivos; os
artefatos de uma execução concluída não são sobrescritos.

| Diretório | Conteúdo e preservação |
|---|---|
| `data/raw/repos/` | Clones completos dos casos, mantidos localmente. |
| `data/interim/runs/` | Tabelas, inventários, snapshots e recibos por `run_id`. |
| `data/interim/reviews/` | Cópias de trabalho destinadas à revisão do pesquisador. |
| `data/interim/documentation/` | Cópia local da documentação anterior à consolidação editorial. |
| `data/processed/manifests/` | Manifestos locais com hashes das entradas e saídas. |
| `docs/evidencias/` | Registros pequenos selecionados para acompanhar o código. |
| `reports/` | Materiais destinados ao TCC, incluídos quando revisados. |
| `tmp/` | Logs, caches e saídas temporárias; `make clean` remove esse diretório. |

Os diretórios intermediários, clones e manifestos são ignorados pelo Git. Isso
permite executar o estudo sem alterar o worktree. A inclusão de resultados no
repositório é uma etapa separada da geração dos arquivos.

## Identificação e integridade

Cada resultado identifica o repositório público, SHA integral, período em UTC,
protocolo, taxonomia, código executor e `run_id`. Manifestos registram hashes das
entradas e saídas. Caminhos usam `/` e são relativos à raiz apropriada; CSVs usam
UTF-8, booleanos `true`/`false` e células vazias para valores ausentes. Os estados
numéricos seguem o [contrato das métricas](../docs/GQM_MAPA_METRICAS.md).

Ponteiros em `data/interim/latest/` indicam a última execução, inclusive uma falha.
A reprodução usa identificadores explícitos e verifica a cadeia de fontes.
Amostras originais e índices são imutáveis; o pesquisador trabalha em cópias das
fichas e das tabelas de revisão. Os recibos preservam também revisões recusadas.

A coleta original de 31/08/2026 depende de respostas e CSVs locais. Uma consulta
posterior ao GitHub não reconstrói necessariamente aquela observação, mesmo com as
mesmas expressões. Esses insumos devem ser preservados junto com os manifestos.
Clones só podem ser removidos quando sua recuperação no SHA registrado continuar
viável. Indisponibilidade futura deve ser registrada, sem trocar silenciosamente
a revisão analisada.

## Dados pessoais e publicação

Nomes e emails de autores são usados transitoriamente na detecção de bots e na
contagem agregada de identidades. Não são incluídos nos Parquets ou nas tabelas de
resultados. Credenciais ficam no ambiente local; `.env` não é insumo da pesquisa.
Mensagens, trechos de código e exemplos públicos são revisados antes de publicação.

O conteúdo dos projetos mantém sua licença original. O pacote de reprodução não
inclui clones completos; reúne identificadores, insumos permitidos, transformações,
hashes e instruções. A publicação de um pacote exige conferir seu conteúdo e as
condições de redistribuição aplicáveis aos materiais selecionados.

Mudanças de esquema, filtro ou regra de normalização são registradas no instrumento
e no método. Tabelas anteriores conservam sua versão e proveniência, mesmo quando
o protocolo deixa de usar uma regra histórica.
