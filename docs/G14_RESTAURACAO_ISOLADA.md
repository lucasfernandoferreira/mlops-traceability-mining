# Restauração isolada do estudo DM-027

O procedimento `verification.release.restore_study` recebe explicitamente o índice definitivo,
o recibo empírico, o ZIP, o diretório de revisões e um diretório de saída inexistente.
A política é `config/verification.yaml`. O instrumento é recuperado por `git clone`
do `instrument.bundle` vinculado ao recibo e `checkout --detach` no SHA do verificador.
Não se usam ponteiros `latest` nem consultas de rede.

A restauração consome as entradas do ZIP e confere os hashes do manifesto antes de
escrever. Recusa caminhos que escapem do diretório, arquivos divergentes do instrumento
e hashes incompatíveis. Recupera os demais insumos dos inventários vinculados ao recibo.
Os clones de casos não integram o ZIP: seus arquivos, inclusive objetos Git, são copiados
literalmente do acervo local inventariado para armazenamento independente. Não se usam
hardlinks, symlinks ou alternates para substituir as cópias. A posse do ZIP isoladamente
não basta: os arquivos listados em `external_sources` no relatório devem ser preservados
com os hashes de `source_hashes`. O inventário suplementar preserva os dossiês examinados
na revisão, incluindo as novas observações LFS identificadas separadamente da coleta.

O ambiente restaurado possui worktree limpo. Executa-se `scripts/verify_study.py`
a partir do código recuperado, com `PYTHONPATH` apontando para seu próprio `src`.
O interpretador Python e as dependências instaladas são compartilhados com o ambiente
de origem; seus locks, a versão do ambiente no recibo e o comando utilizado documentam
esse limite de isolamento. Trata-se de restauração de código e fontes em diretório
independente, sem alegação de reprodução em sistema operacional diferente. Para recuperar
as dependências em outra máquina, use os locks `requirements-dev.txt`, Python indicado
no projeto e `make setup`; não substitua versões para acomodar divergências.

## O que é recalculado

O runner percorre novamente o DAG alcançável dos clones congelados, identifica commits
incluídos e excluídos, atividade e mudanças; confronta configurações históricas com pares
de árvores; recalcula razões e denominadores, estatísticas temporais e sensibilidade;
reconstitui associações preservadas de PR e a seleção qualitativa determinística.
Executa também as fixtures e contraprovas declaradas na política, vinculadas ao código
recuperado. A comparação examina `source_commits.json`, `source_changes.json` e
`crosscheck.json` de cada caso, mais a seleção e o confronto qualitativos.

Contagens, identidades, tipos e ordem das listas devem coincidir exatamente.
Floats admitem tolerância absoluta de `1e-12`, já adotada pelo oráculo aritmético do
projeto, para diferenças de representação numérica sem arredondamento editorial.
Todas as diferenças são registradas com esperado, observado, caminho e
`within_tolerance`, inclusive quando aceitas pela tolerância. Diferença inteira ou
identitária não recebe tolerância. Uma falha técnica obrigatória reprova G14 mesmo
quando os arquivos comparados coincidirem.

## O que recebe apenas conferência de integridade

A coleta original e suas respostas preservadas não são refeitas. Contagens de chamadas
estáticas do scanner, julgamentos taxonômicos e qualitativos, redação e decisões de
alinhamento mantêm os bytes/fontes declarados; o procedimento não simula uma nova
avaliação humana nem executa treinamento nos projetos dos casos. G15 vincula o manuscrito,
o catálogo de afirmações e o parecer; G11 distingue identidade da fonte e pertinência
julgada do conteúdo. A confirmação humana não é inferida desses testes.

## Ensaio, candidato e aceite

Antes da confirmação do pesquisador, `review_package` gera `pacote_revisao.zip`,
com `package_status: review_rehearsal` e `candidate_eligible: false`. Pode-se executar
G14 sobre esse pacote para testar concretamente a recuperação e o recálculo técnico.
Esse resultado não autoriza a emissão de um candidato científico nem o aceite final.

Após a revisão efetiva do conteúdo, o pesquisador executa, na raiz do projeto:

```sh
.venv/bin/python tools/confirmar_revisao.py --responsavel 'Nome completo do pesquisador' --assumo-revisao
```

O script valida o inventário `data/interim/fechamento_dm027/confirmation_lock.json`,
preserva o rascunho e cria uma cópia confirmada com autoria original, responsável e data
UTC real. Em seguida executa uma nova avaliação taxonômica e verificação G00–G13;
chama o finalizador existente, que repete a verificação antes de autorizar o candidato;
restaura esse candidato e emite `recibo_final.json`. Cada execução usa caminhos novos.
Qualquer recusa interrompe a promoção e preserva os recibos. Uma segunda chamada conserva
a confirmação existente se seus hashes e responsável coincidirem, mas repete a execução.

O recibo final vincula os hashes do índice, recibo empírico, candidato, relatório G14,
manuscrito, catálogo e confirmação. Reconfere as fontes e provas nos dois diretórios.
`scientific_result_accepted` somente pode ser verdadeiro quando a verificação original
e a restaurada satisfazem todos os critérios anteriores à restauração, G14 e G15 passam,
o pacote é candidato e a confirmação corresponde aos arquivos examinados. Nenhum recibo
histórico é promovido por edição de seu campo de status.

Os resultados efetivamente executados, caminhos e hashes ficam no
`RELATORIO_FECHAMENTO_DM027.md`, gerado localmente, e no log de fechamento. Este documento
especifica o procedimento; por si só não prova execução nem aprovação.
