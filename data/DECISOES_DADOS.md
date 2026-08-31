# Política de dados

## Classificação dos artefatos

| Local | Conteúdo | Versionamento |
|---|---|---|
| `data/raw/repos/` | Clones integrais usados como fonte. | Não versionado; reconstruível. |
| `data/interim/` | Respostas normalizadas, inventários e tabelas intermediárias. | Não versionado por padrão. |
| `data/processed/` | Tabelas analíticas derivadas e manifestos de execução. | Tabelas pequenas exigem revisão; manifestos são ignorados e sua publicação é explícita. |
| `reports/` | Figuras, tabelas e resultados destinados à dissertação. | Versionado quando for produto final revisado. |
| `tmp/` | Saídas locais descartáveis, inclusive smoke tests. | Nunca versionado. |

Diretórios ou formatos ainda não implementados descrevem a política pretendida; sua
criação não deve ser interpretada como evidência de que uma coleta ocorreu.

## Proveniência obrigatória

Todo dado processado deve permitir identificar:

- repositório de origem pelo identificador público `owner/name` e URL canônica;
- SHA integral do commit observado;
- instante de coleta em UTC e intervalo temporal considerado;
- consulta ou etapa que produziu o registro;
- versão do protocolo e da taxonomia;
- `run_id` e SHA do código registrados no manifesto;
- hash do artefato de entrada quando aplicável.

Uma execução oficial deve ocorrer com worktree limpo. Dados derivados por uma execução
falha devem permanecer separados e não podem ser promovidos a resultado final.
Manifestos locais ficam ignorados pelo Git para que uma execução não altere o estado do
worktree; quando forem parte de uma entrega científica, devem ser revisados e incluídos
explicitamente.

## Minimização e privacidade

- Tokens e outros segredos existem apenas no ambiente local; `.env` não é fonte de
  dados e não deve ser versionado.
- Nomes, e-mails e outros identificadores pessoais de autores de commits não serão
  publicados.
- Quando necessários aos filtros, autores serão tratados transitoriamente para detectar
  bots e produzir contagens agregadas.
- Mensagens de commit só serão preservadas quando indispensáveis à análise e deverão ser
  revisadas antes de qualquer publicação, pois podem conter dados pessoais ou segredos.
- Relatórios públicos devem preferir métricas agregadas. Exemplos textuais exigem
  justificativa e revisão manual.

## Licenças e redistribuição

Repositórios externos mantêm suas licenças e direitos autorais originais. O fato de um
repositório ser público não autoriza redistribuir seu conteúdo. Clones brutos não serão
incluídos neste repositório; quando permitido, serão publicados apenas identificadores,
metadados mínimos, transformações e instruções de reconstrução. Qualquer conjunto de
dados distribuído deve incluir sua licença e a data de obtenção.

## Integridade e retenção

- Arquivos tabulares devem usar esquema explícito, UTF-8 e datas ISO 8601 em UTC.
- Caminhos de arquivos devem usar `/` e ser relativos à raiz do repositório analisado.
- SHAs Git devem ser armazenados integralmente; abreviações servem apenas para exibição.
- Valores ausentes seguem os estados definidos em `docs/GQM_MAPA_METRICAS.md` e não são
  convertidos silenciosamente em zero.
- Artefatos brutos e intermediários podem ser removidos depois da validação se puderem
  ser reconstruídos a partir dos identificadores, SHAs, configuração e manifesto.
- Artefatos das Fases 1 e 2 são armazenados em `data/interim/runs/<run_id>/`; ponteiros
  em `data/interim/latest/` podem mudar, mas diretórios de runs concluídos são imutáveis.
- Se uma origem for apagada ou se tornar privada, a indisponibilidade deve ser registrada
  em vez de substituir o conteúdo por outra revisão.

## Controle de mudanças

Alterações de esquema, filtros, limiares ou regras de normalização exigem atualização
coordenada de configuração, documentação, testes e versão do protocolo. Uma tabela já
produzida não deve ser sobrescrita por uma execução com contrato diferente; use outro
`run_id` e preserve o vínculo com o manifesto correspondente.
