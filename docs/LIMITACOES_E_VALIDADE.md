# Limitações e ameaças à validade

## Estado atual

O projeto executa as Fases 0–5 e o piloto preliminar Ultralytics no SHA selecionado.
O protocolo operacional 2.0.0 estuda três casos MLflow, sem comparação entre ferramentas.
A amostra está em `pilot`; faltam validação humana da taxonomia, alinhamento acadêmico
e gates suplementares dos outros casos. Testes e números observados demonstram o
funcionamento do instrumento; não substituem validade empírica independente.

## Validade de construto

- Caminhos e extensões são aproximações do papel de um arquivo. Um nome compatível não
  garante que o artefato seja usado na execução do sistema.
- A categoria é mutuamente exclusiva, embora um arquivo possa exercer múltiplos papéis.
  A regra de primeira correspondência reduz ambiguidade operacional, mas perde nuances.
- `CODE + NOTEBOOK` representa a dimensão de código; notebooks podem misturar código,
  dados e narrativa.
- Coalteração no mesmo commit mede associação temporal e não prova dependência ou
  causalidade.
- Arquivos DVC e evidências públicas do MLflow não garantem uso completo, contínuo ou
  correto das ferramentas.
- Quantidade de chaves modificadas depende de parsers e normalização de formatos. Sem
  parser suportado, `config_magnitude` não é aplicável, em vez de assumir magnitude zero.
- Proveniência, runs e promoções privadas ou apagadas não são observáveis. A ausência
  pública será registrada como `not_available`, não como inexistência do fenômeno.
- A triagem atual procura `mlruns/` na raiz. Um resultado negativo não exclui
  diretórios aninhados ou evidências em commits anteriores. A inspeção final deve
  distinguir esse limite de detecção da indisponibilidade confirmada das fontes.
- CONFIG 1.1.0 cobre cfg/config/configs/config_files, mas a calibração por exemplos
  ainda precisa da revisão humana de 20 arquivos por categoria. Alguns grupos têm
  poucos exemplos no piloto e precisam ser complementados nos outros casos/histórico.
- DATA_META continua restrito a DVC e não valida a dimensão de dados em MLflow.
  Arquivos de definição de datasets e rótulos podem cair em CONFIG: sua quantidade
  de chaves não equivale a quantidade de hiperparâmetros ou ajustes de treinamento.
- O recorte MLflow seleciona bibliotecas/frameworks; mecanismos oferecidos no código
  não comprovam experimentos efetivamente executados por organizações usuárias.
- O AST produz candidatos sintáticos com aliases de imports; não resolve escopos,
  reatribuições, wrappers, clientes ou delegação. Chamadas a log_artifact podem salvar
  pesos, sem demonstrar registro ou promoção. Autolog não é expandido em eventos.
- Toda a árvore do SHA é verificada por caminhos mlruns, inclusive aninhados; a
  ausência não exclui outros formatos, histórico anterior ou serviços externos.
- A magnitude usa adição/remoção para renomeações e conta nomes de classes em mapas
  de datasets. Migrações podem dominar a média; revisar os maiores contribuintes.

Mitigações: versionar e validar a taxonomia, manter exemplos rotulados, registrar versão
das regras em cada resultado e auditar manualmente casos limítrofes.

## Validade interna

- Repositórios podem reescrever histórico, alterar a branch padrão ou remover tags após
  a coleta.
- Filtros textuais de bots podem classificar incorretamente pessoas ou automações.
- A exclusão de merges evita dupla contagem em algumas estratégias, mas também pode
  ocultar integração feita diretamente no merge.
- Commits com mais de 1.000 arquivos são excluídos da análise semântica; migrações e
  grandes refatorações podem ficar sub-representadas.
- Renomeações e movimentos podem ser interpretados como exclusão e adição conforme a
  estratégia usada pelo Git.
- Consultas distintas podem encontrar o mesmo repositório e a API pode devolver estado
  parcialmente atualizado ou sofrer limites de requisição.
- A confirmação de MLflow usa caminhos encontrados na Fase 1 e até 50 manifestos de
  dependência observados na árvore. Como o Code Search ou a própria árvore podem
  truncar resultados, um uso real fora dessas evidências ainda pode não ser observado.
- Erros de fuso horário podem alterar a classificação na data de corte se timestamps não
  forem normalizados para UTC.

Mitigações: deduplicar pelo identificador canônico, fixar o SHA analisado, registrar
contagens e motivos de exclusão, preservar logs de coleta e usar manifestos com hashes.

## Validade externa

- A origem prevista são repositórios públicos do GitHub; resultados não se generalizam
  automaticamente para projetos privados, outras forjas ou ambientes corporativos.
- Os limiares de 100 estrelas, 300 commits e 5 contribuidores agregados favorecem projetos mais
  visíveis, antigos e colaborativos.
- As consultas atuais privilegiam artefatos DVC, MLflow e projetos associados a Python.
- Termos de exclusão reduzem tutoriais, mas podem excluir projetos legítimos ou deixar
  passar demonstrações sem esses termos.
- A atividade após `2025-09-01T00:00:00Z` favorece projetos mantidos recentemente.
- A amostra intencional de 3 casos permite profundidade, não representatividade
  estatística.

A análise deve ser apresentada como estudo de casos múltiplos dentro dos critérios
declarados. Generalizações devem ser analíticas e acompanhadas da descrição do funil.

## Validade de conclusão

- Uma amostra pequena reduz poder estatístico e torna medidas sensíveis a um único
  repositório ou período atípico.
- Métricas com poucos eventos têm grande instabilidade; numerador, denominador e volume
  excluído devem acompanhar toda proporção.
- Razões como `experiment_redundancy` não são limitadas a 1 e não devem ser comparadas
  como percentuais.
- Denominador zero, dado indisponível e valor observado zero têm interpretações
  diferentes e não podem ser agregados entre si.
- Comparações exploratórias múltiplas elevam o risco de padrões ocasionais; efeitos,
  incerteza e contexto são mais importantes que significância isolada.

Antes da análise, devem ser congelados período, fórmulas, critérios de exclusão e plano
de agregação. Análises de sensibilidade devem considerar commits grandes, merges e
notebooks quando o volume permitir.

## Confiabilidade e reprodutibilidade

- Arquivos de dependências com hashes reduzem variação local, mas sistema operacional e
  ferramentas externas ainda podem produzir diferenças.
- APIs e repositórios remotos são mutáveis; uma reconstrução futura pode falhar se a
  origem desaparecer ou se tornar privada.
- Um manifesto prova quais insumos locais foram usados, mas não substitui o arquivamento
  permitido de respostas da API e SHAs de origem.
- O smoke test usa um histórico sintético pequeno e não cobre escala, redes instáveis,
  formatos malformados ou todas as variantes de histórico Git.
- Paralelismo reduz o tempo de parede, mas não remove as cotas do GitHub; throughput e
  ETA podem variar quando a execução aguarda renovação de rate limit.

Pilotos com `--allow-dirty` preservam snapshot exato do instrumento e permanecem
preliminares. O snapshot e seus hashes não substituem uma execução oficial limpa.

Mitigações: executar com worktree limpo, usar Python 3.12 e locks versionados, registrar
SHA integral das origens, hashes e horários UTC, e nunca sobrescrever resultados de runs
anteriores.

## Ética, privacidade e licenças

Históricos públicos podem conter nomes, e-mails, mensagens sensíveis ou segredos
acidentalmente versionados. A pesquisa deve minimizar coleta e publicação, trabalhar com
contagens agregadas e revisar manualmente qualquer exemplo. Tokens nunca devem integrar
artefatos ou logs. O conteúdo de terceiros permanece sujeito às licenças originais; um
clone público não deve ser redistribuído automaticamente.

## Registro de limitações por execução

Cada relatório empírico deve declarar:

1. data e período da coleta;
2. consultas, critérios e tamanho de cada etapa do funil;
3. repositórios indisponíveis e campos não observáveis;
4. commits excluídos por merges, bots, tamanho ou erro;
5. cobertura e resultado da validação da taxonomia;
6. versões do protocolo, taxonomia e código;
7. desvios deste documento e análise de seu impacto.
