## Contexto

A alteração introduz uma nova aplicação com interface desenvolvida em Streamlit e um backend no Xano. O backend será responsável pelo armazenamento dos dados, autenticação, autorização, regras de negócio e APIs. A interface se comunicará com o backend por meio de requisições HTTP.

O projeto utiliza o OpenSpec com o esquema `spec-driven`. Os requisitos e as motivações estão documentados em `proposal.md` e nas especificações da alteração.

## Objetivos e não objetivos

**Objetivos:**

- Definir uma separação clara entre a apresentação da interface e a lógica de negócio do backend.
- Manter a consistência entre os saldos de estoque, as movimentações, as vendas e os cálculos financeiros.
- Preservar os custos unitários históricos utilizados no cálculo do CMV.
- Disponibilizar uma etapa de validação e pré-visualização antes da importação de arquivos de vendas.
- Garantir que o controle de acesso seja aplicado pelo backend.

**Não objetivos:**

- Implementar a aplicação diretamente neste documento.
- Integrar automaticamente com APIs de marketplaces na primeira versão.
- Substituir um sistema completo de contabilidade ou gestão tributária.

## Decisões técnicas

### 1. Separação entre backend e frontend

O Xano fornecerá o banco de dados, a autenticação, as regras de negócio e as APIs HTTP. O Streamlit fornecerá a interface do usuário e consumirá essas APIs.

Essa abordagem mantém as validações importantes e os cálculos financeiros no backend, em vez de depender apenas do comportamento da interface.

**Alternativa considerada:** implementar os cálculos de negócio diretamente no Streamlit. Essa alternativa não foi escolhida porque outras aplicações ou chamadas diretas às APIs poderiam contornar as regras implementadas somente na interface.

### 2. Modelo de dados e relacionamentos

O modelo de dados inicial utilizará entidades separadas para usuários, categorias, fornecedores, produtos, relacionamentos entre produtos e fornecedores, entradas de estoque, vendas, itens de venda e movimentações de estoque.

Os relacionamentos utilizarão identificadores explícitos. Registros que possuam referências históricas deverão, em geral, ser desativados em vez de excluídos permanentemente.

**Alternativa considerada:** armazenar todas as informações em poucas tabelas com dados repetidos. Essa alternativa não foi escolhida porque aumenta a duplicação e dificulta a manutenção dos registros históricos.

### 3. Valorização do estoque

O sistema utilizará o método do custo médio ponderado. Cada entrada de estoque confirmada atualizará a quantidade disponível e o custo médio de aquisição do estoque.

O custo unitário utilizado em cada item de venda será armazenado como um registro histórico, para que compras posteriores não alterem o CMV de vendas já registradas.

**Alternativa considerada:** utilizar o método PEPS (Primeiro que Entra, Primeiro que Sai), com controle por lotes. Essa alternativa não foi escolhida para a primeira versão porque exige um gerenciamento adicional do estoque por lote.

### 4. Consistência do estoque

Todas as operações que alterem o estoque serão processadas pelas regras do backend. Cada operação deverá validar o saldo atual, registrar a movimentação e atualizar o saldo do produto de maneira consistente.

A implementação deverá impedir que requisições simultâneas provoquem baixas duplicadas ou saldos inconsistentes. Antes da implementação, deverão ser verificadas as ferramentas disponíveis no Xano para garantir atualizações seguras e consistentes.

**Alternativa considerada:** permitir que a interface atualize diretamente os saldos de estoque. Essa alternativa foi rejeitada porque poderia contornar as validações e gerar registros inconsistentes.

### 5. Importação de vendas

Os arquivos CSV e Excel serão validados antes da confirmação da importação. O sistema apresentará uma pré-visualização das linhas, informará os registros inválidos e identificará possíveis vendas duplicadas usando o canal de venda e o número do pedido, quando essas informações estiverem disponíveis.

O processo de importação deverá evitar a criação de vendas duplicadas e impedir que a mesma venda provoque mais de uma baixa no estoque.

**Alternativa considerada:** importar imediatamente todas as linhas assim que um arquivo for enviado. Essa alternativa foi rejeitada porque os usuários precisam revisar os erros e possíveis duplicidades antes de confirmar a importação.

### 6. Cálculos financeiros

Os cálculos financeiros serão realizados e validados no backend. Os valores monetários utilizarão campos numéricos compatíveis com números decimais, evitando cálculos com números de ponto flutuante binário quando for necessária precisão monetária.

Os custos registrados no nível da venda serão armazenados separadamente dos valores registrados nos itens, quando apropriado. Os custos compartilhados da venda serão distribuídos proporcionalmente ao valor de venda de cada item, garantindo que a soma dos valores distribuídos corresponda ao custo total original. Essa regra será utilizada no cálculo da rentabilidade por produto, evitando que os custos sejam contabilizados mais de uma vez.

**Alternativa considerada:** repetir o custo total da venda em cada item vendido. Essa alternativa foi rejeitada porque faria com que os custos totais fossem contabilizados mais de uma vez.

### 7. Autenticação e autorização

A autenticação do Xano será responsável pelo gerenciamento das credenciais. Os endpoints do backend verificarão o perfil do usuário autenticado antes de permitir operações protegidas.

O Streamlit poderá ocultar controles que determinado usuário não tenha permissão para utilizar, mas a autorização no backend continuará sendo obrigatória.

**Alternativa considerada:** depender exclusivamente da visibilidade dos elementos da interface ou das restrições de navegação. Essa alternativa foi rejeitada porque essas restrições não protegem as APIs.

## Riscos e compensações

- **Conflitos em operações simultâneas de estoque:** verificar e utilizar mecanismos adequados de proteção no backend antes de implementar as atualizações.
- **Mapeamento incorreto de arquivos:** validar colunas, tipos de dados e campos obrigatórios, além de apresentar uma pré-visualização.
- **Importações duplicadas:** aplicar verificações de duplicidade e impedir o processamento repetido do mesmo pedido.
- **Alterações no custo médio afetarem cálculos históricos:** armazenar o custo utilizado em cada item de venda confirmado.
- **Custos compartilhados serem contabilizados mais de uma vez:** definir e testar uma regra consistente de distribuição antes de implementar a rentabilidade por produto.
- **Diferenças entre as permissões da interface e do backend:** aplicar a autorização em todos os endpoints protegidos do backend.

## Plano de implantação

1. Revisar e aprovar as especificações e este documento de decisões técnicas antes da implementação.
2. Criar o modelo de dados, os relacionamentos e as regras de validação no Xano.
3. Implementar a autenticação, a autorização, as operações de estoque, as vendas e os cálculos financeiros.
4. Implementar e validar o processo de importação de arquivos CSV e Excel.
5. Desenvolver a interface no Streamlit e conectá-la às APIs do backend.
6. Testar os cálculos, a consistência do estoque, as permissões e o tratamento de duplicidades.
7. Disponibilizar a aplicação após a validação.

Durante o desenvolvimento inicial, os dados de teste deverão permanecer separados dos dados de produção. Se uma implantação falhar, novas importações e operações que alterem o estoque deverão ser interrompidas até que a versão anterior funcional ou um procedimento de recuperação verificado seja restaurado.

Os registros financeiros e de estoque não deverão ser excluídos indiscriminadamente como estratégia para reverter alterações.

## Questões em aberto

## Questões em aberto

Não há questões em aberto registradas neste documento neste momento.