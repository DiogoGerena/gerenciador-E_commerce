# dashboard-relatorios Specification

## Purpose
TBD - created by archiving change controle-financeiro-estoque. Update Purpose after archive.

## Requirements

### Requirement: Indicadores financeiros do dashboard

O sistema DEVE apresentar um dashboard com os principais indicadores financeiros do período selecionado.

Os indicadores DEVEM incluir receita de vendas, CMV, custos de venda, resultado após os custos registrados e margem de resultado.

O sistema DEVE calcular os indicadores com base nas vendas e nos custos registrados, sem contabilizar os mesmos custos mais de uma vez.

#### Cenário: Consultar indicadores financeiros

- **QUANDO** um usuário acessar o dashboard e selecionar um período
- **ENTÃO** o sistema DEVE apresentar os indicadores financeiros correspondentes às operações registradas naquele período

#### Cenário: Consultar período sem vendas

- **QUANDO** o período selecionado não possuir vendas registradas
- **ENTÃO** o sistema DEVE apresentar os indicadores sem vendas e evitar divisões por zero no cálculo das margens

### Requirement: Indicadores de estoque

O sistema DEVE apresentar a quantidade disponível dos produtos e o valor estimado do estoque.

O valor do estoque DEVE considerar as quantidades disponíveis e os custos unitários de referência calculados pelo sistema.

O sistema DEVE identificar os produtos cuja quantidade disponível seja igual ou inferior ao estoque mínimo cadastrado.

#### Cenário: Identificar estoque baixo

- **QUANDO** a quantidade disponível de um produto for igual ou inferior ao seu estoque mínimo
- **ENTÃO** o sistema DEVE destacar o produto no dashboard como um item que exige atenção

#### Cenário: Consultar valor do estoque

- **QUANDO** um usuário consultar os indicadores de estoque
- **ENTÃO** o sistema DEVE apresentar o valor estimado dos produtos disponíveis com base nos custos registrados

### Requirement: Gráficos financeiros

O sistema DEVE disponibilizar gráficos para facilitar a análise do desempenho financeiro ao longo do tempo.

Os gráficos DEVEM permitir visualizar a evolução da receita, do CMV e do resultado após os custos registrados.

O sistema DEVE utilizar os dados das operações registradas e respeitar o período selecionado.

#### Cenário: Visualizar evolução financeira

- **QUANDO** um usuário selecionar um período com operações registradas
- **ENTÃO** o sistema DEVE apresentar gráficos com a evolução dos indicadores financeiros disponíveis

### Requirement: Filtros do dashboard

O sistema DEVE permitir filtrar os indicadores por período.

Quando existirem dados suficientes, o sistema DEVE permitir filtrar ou agrupar informações por produto, categoria e canal de venda.

Os filtros DEVEM atualizar os indicadores, gráficos e tabelas relacionados.

#### Cenário: Aplicar filtro de período

- **QUANDO** um usuário selecionar uma data inicial e uma data final válidas
- **ENTÃO** o sistema DEVE atualizar as informações para considerar somente as operações correspondentes ao período selecionado

#### Cenário: Aplicar filtro por categoria

- **QUANDO** um usuário selecionar uma categoria
- **ENTÃO** o sistema DEVE apresentar os dados dos produtos e das operações correspondentes à categoria selecionada, conforme o indicador consultado

### Requirement: Relatórios de vendas e resultados

O sistema DEVE permitir consultar relatórios de vendas com data, canal de origem, receita, CMV, custos de venda, resultado e margem.

O sistema DEVE permitir consultar os resultados de forma consolidada e por venda.

Os relatórios DEVEM respeitar os filtros selecionados pelo usuário.

#### Cenário: Consultar relatório financeiro

- **QUANDO** um usuário solicitar um relatório financeiro para determinado período
- **ENTÃO** o sistema DEVE apresentar os valores consolidados e permitir consultar os detalhes das vendas incluídas no resultado

### Requirement: Relatórios de estoque

O sistema DEVE permitir consultar relatórios de produtos com quantidade disponível, estoque mínimo, custo médio e valor estimado em estoque.

O sistema DEVE permitir identificar produtos abaixo ou no limite do estoque mínimo.

O sistema DEVE disponibilizar o histórico de entradas e movimentações para consulta.

#### Cenário: Consultar relatório de estoque baixo

- **QUANDO** um usuário solicitar a relação de produtos com estoque baixo
- **ENTÃO** o sistema DEVE apresentar os produtos cuja quantidade disponível seja igual ou inferior ao estoque mínimo cadastrado

#### Cenário: Consultar movimentações de um produto

- **QUANDO** um usuário selecionar um produto em um relatório de estoque
- **ENTÃO** o sistema DEVE permitir consultar o histórico de entradas, saídas, ajustes, perdas e devoluções registradas para esse produto

### Requirement: Consistência dos indicadores e relatórios

O sistema DEVE utilizar as mesmas regras de cálculo financeiro e de estoque nos indicadores, gráficos e relatórios.

O sistema NÃO DEVE apresentar valores que incluam operações canceladas como se fossem vendas válidas.

O sistema DEVE atualizar as informações apresentadas quando houver alterações confirmadas nos registros que afetam os indicadores.

#### Cenário: Conferir indicador com relatório

- **QUANDO** um usuário comparar um indicador do dashboard com o relatório correspondente, utilizando os mesmos filtros
- **ENTÃO** os valores DEVEM ser consistentes entre as duas visualizações

#### Cenário: Considerar venda cancelada

- **QUANDO** uma venda estiver cancelada
- **ENTÃO** o sistema DEVE tratar seus valores e suas movimentações conforme as regras de cancelamento, sem contabilizá-la como uma venda válida
