# Limitações e validade

O estudo descreve três casos selecionados intencionalmente entre projetos públicos
do GitHub. Suas conclusões dependem das fontes disponíveis, dos critérios de seleção
e da capacidade do instrumento de reconhecer os artefatos. O protocolo 2.1.0 trata
essas condições separadamente da conclusão técnica das etapas de processamento.

## O que as medidas representam

Caminhos e extensões aproximam o papel de um arquivo. Uma categoria única facilita
a contagem, mas perde situações em que o mesmo arquivo tem mais de uma função ou
muda de papel ao longo do tempo. Notebooks, por exemplo, podem misturar código,
dados e narrativa. A revisão da taxonomia inclui exemplos históricos e registra
essas ambiguidades; sua concordância estratificada não mede automaticamente a
precisão em todo o universo.

A coalteração identifica mudanças no mesmo commit. Ela não prova dependência nem
causalidade entre código e configuração. Da mesma forma, chaves CONFIG podem ser
nomes de classes, descrições de datasets ou opções de ambiente, além de parâmetros
de treinamento. Renomeações contadas como adição e remoção podem aumentar a
magnitude sem mudança de valores. Distribuição, concentração e sensibilidade são
apresentadas para tornar esses efeitos examináveis.

DATA_META reconhece artefatos DVC e não cobre a dimensão de dados em geral.
Uma categoria vazia em inventário completo indica ausência sob aquelas regras e
naquele universo, sem validar empiricamente a categoria ou demonstrar ausência de
dados no projeto.

Os casos são bibliotecas ou frameworks que oferecem mecanismos de integração.
Código e testes associados mostram como a integração foi implementada, mas não
comprovam execução por organizações usuárias. O parser AST identifica aliases de
imports e posições sintáticas; wrappers, escopos, clientes e delegação ao Lightning
podem escapar da contagem. Esse limite é particularmente relevante no Anomalib.
Zero chamadas detectadas não equivale a ausência de integração.

## Cobertura das fontes

A descoberta depende das consultas e da indexação do GitHub Code Search. Resultados
truncados, ordenação da API e inspeção dirigida de dependências limitam a cobertura.
As consultas também favorecem projetos associados a Python. A triagem procura
`mlruns/` na raiz; a inspeção do SHA congelado cobre caminhos aninhados, mas nenhuma
das duas comprova ausência de tracking em serviços externos ou em outras revisões.

Não foram ingeridas fontes públicas de runs ou registry. Assim, as perguntas de
proveniência, ambiente por run e promoções permanecem sem resposta empírica. Os
motivos `not_collected` e `parser_not_implemented` não são interpretados como uma
busca negativa. A consulta commit–PR descreve as associações retornadas pela API
na data registrada; pode mudar com o estado público do repositório.

## Seleção e interpretação

Os critérios de estrelas, commits e atividade favorecem projetos visíveis e mantidos.
Termos de exclusão podem retirar projetos legítimos ou deixar passar demonstrações.
As identidades de autor usam email normalizado, sem resolver todas as pessoas com
mais de um alias. Padrões textuais de bots também podem classificar autores de forma
incorreta. A decisão sobre casos próximos dos limites exige conferência.

Anomalib e Ultralytics compartilham o domínio de visão computacional. O contraste
entre seus mecanismos de integração não elimina essa proximidade. O resultado não
se generaliza automaticamente para projetos privados, outras plataformas ou práticas
corporativas de MLOps.

Commits do mesmo projeto têm dependência temporal e organizacional. Por isso, a
comparação é descritiva por caso; milhares de commits não são milhares de réplicas
independentes. Proporções com poucos eventos devem ser lidas junto com seus
numeradores e denominadores. Indisponibilidade, denominador zero e zero observado
permanecem separados nas tabelas.

O plano qualitativo foi definido depois do piloto exploratório do Ultralytics.
As cotas selecionam eventos de interesse analítico e não estimam frequência dos
temas. A interpretação deve considerar evidência contrária e explicações alternativas.
Se houver um único codificador, essa condição será declarada; assistência técnica
não constitui avaliação independente.

## Reprodutibilidade e tratamento dos dados

O SHA fixado delimita o histórico, mas não garante acesso futuro se a origem for
apagada ou tornada privada. A exclusão de merges pode omitir mudanças introduzidas
na própria integração; o limite de 1.000 arquivos pode reduzir a presença de grandes
migrações. Ambos os efeitos ficam visíveis no funil de commits.

Locks e hashes reduzem variação, mas não eliminam diferenças de sistema operacional,
ferramentas externas ou serviços remotos. Manifestos identificam os insumos usados;
a preservação dos artefatos continua necessária. Execuções de desenvolvimento
conservam snapshots e permanecem preliminares, mesmo depois de o código ser commitado.

Os relatórios registram período, funil, exclusões, disponibilidade, validação e versões
do instrumento. Exemplos textuais e arquivos de terceiros exigem revisão antes da
publicação. Autores são tratados transitoriamente para filtros e contagens; suas
identidades e as credenciais de acesso não integram as tabelas analíticas. A
[política de dados](../data/DECISOES_DADOS.md) descreve a preservação dos materiais.
