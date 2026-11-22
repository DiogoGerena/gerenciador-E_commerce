# dashboard-relatorios Specification

## Purpose

Esta capacidade define os indicadores e relatórios operacionais e financeiros usados para acompanhar vendas, estoque, custos e resultados, mantendo consistência entre as visualizações.

## Requirements

### Requirement: Indicadores financeiros do dashboard

**MUST:** O sistema DEVE apresentar um dashboard com os principais indicadores financeiros do período selecionado.

Os indicadores DEVEM incluir receita de vendas, CMV, custos de venda, resultado após os custos registrados e margem de resultado.

O sistema DEVE calcular os indicadores com base nas vendas e nos custos registrados, sem contabilizar os mesmos custos mais de uma vez.

#### Cenário: Consultar indicadores financeiros

- **QUANDO** um usuário acessar o dashboard e selecionar um período
- **ENTÃO** o sistema DEVE apresentar os indicadores financeiros correspondentes às operações registradas naquele período

#### Cenário: Consultar período sem vendas

- **QUANDO** o período selecionado não possuir vendas registradas
- **ENTÃO** o sistema DEVE apresentar os indicadores sem vendas e evitar divisões por zero no cálculo das margens

### Requirement: Indicadores de estoque

Este requisito é normativo (MUST).

O sistema DEVE apresentar a quantidade disponível dos produtos e o valor estimado do estoque.

O valor do estoque DEVE considerar as quantidades disponíveis e os custos unitários de referência calculados pelo sistema.

O sistema DEVE identificar os produtos cuja quantidade disponível seja igual ou inferior ao estoque mínimo cadastrado.

O sistema DEVE distinguir valores numéricos conhecidos, inclusive zero, de dados ausentes, nulos ou inválidos. Dados ausentes ou inválidos NÃO DEVEM ser convertidos ou apresentados como zero.

O sistema DEVE apresentar totais de quantidade e valor financeiro somente quando todos os produtos incluídos tiverem os campos necessários conhecidos e válidos. Quando houver dados incompletos, DEVE indicar que o total está indisponível e informar quantos produtos possuem campos indisponíveis ou inválidos.

O sistema DEVE classificar um produto como sem estoque quando sua quantidade conhecida for zero, mesmo que o estoque mínimo não esteja disponível. Para quantidade positiva, o sistema DEVE classificar como estoque baixo quando a quantidade for igual ou inferior ao estoque mínimo conhecido, e como normal somente quando for maior que o estoque mínimo conhecido. Quando a quantidade estiver ausente, nula ou inválida, ou quando a quantidade for positiva e o estoque mínimo estiver ausente, nulo ou inválido, a classificação DEVE ser indeterminada.

#### Cenário: Consultar indicadores com dados completos

- **QUANDO** todos os produtos retornados possuírem quantidade, custo médio e estoque mínimo numéricos
- **ENTÃO** o sistema DEVE apresentar os totais de quantidade e valor do estoque e classificar os produtos conforme seus valores conhecidos

#### Cenário: Consultar indicadores com quantidade ausente ou inválida

- **QUANDO** um ou mais produtos não possuírem quantidade disponível válida
- **ENTÃO** o sistema NÃO DEVE tratar essas quantidades como zero nem apresentar a soma das demais quantidades como total completo
- **E** DEVE indicar a quantidade de produtos com dados indisponíveis ou inválidos

#### Cenário: Consultar valor do estoque com custo médio ausente ou inválido

- **QUANDO** um ou mais produtos não possuírem custo médio válido
- **ENTÃO** o sistema NÃO DEVE apresentar o valor financeiro parcial como total completo nem representar os custos desconhecidos como zero
- **E** DEVE indicar a quantidade de produtos sem valor financeiro calculável

#### Cenário: Classificar produto positivo sem estoque mínimo conhecido

- **QUANDO** um produto possuir quantidade positiva conhecida e seu estoque mínimo estiver ausente, nulo ou inválido
- **ENTÃO** o sistema DEVE apresentar a classificação como indeterminada e NÃO DEVE classificá-lo como normal ou baixo por inferência do mínimo

#### Cenário: Classificar quantidade zero sem estoque mínimo conhecido

- **QUANDO** um produto possuir quantidade igual a zero e seu estoque mínimo estiver ausente, nulo ou inválido
- **ENTÃO** o sistema DEVE classificá-lo como sem estoque porque a quantidade zero é conhecida

#### Cenário: Preservar valores legítimos iguais a zero

- **QUANDO** a quantidade ou o custo médio informado pelo serviço for zero
- **ENTÃO** o sistema DEVE preservar o zero como valor conhecido e aplicá-lo nos cálculos e classificações correspondentes

#### Cenário: Identificar estoque baixo

- **QUANDO** a quantidade disponível de um produto for igual ou inferior ao estoque mínimo cadastrado
- **ENTÃO** o sistema DEVE destacar o produto no dashboard como um item que exige atenção

#### Cenário: Consultar valor do estoque

- **QUANDO** um usuário consultar os indicadores de estoque
- **ENTÃO** o sistema DEVE apresentar o valor estimado dos produtos disponíveis com base nos custos registrados

#### Cenário: Consultar estoque sem produtos

- **QUANDO** o serviço retornar uma lista vazia de produtos
- **ENTÃO** o sistema DEVE apresentar um estado vazio apropriado e NÃO DEVE exibir produtos ou valores demonstrativos

### Requirement: Gráficos financeiros

**MUST:** O sistema DEVE disponibilizar gráficos para facilitar a análise do desempenho financeiro ao longo do tempo.

Os gráficos DEVEM permitir visualizar a evolução da receita, do CMV e do resultado após os custos registrados.

O sistema DEVE utilizar os dados das operações registradas e respeitar o período selecionado.

#### Cenário: Visualizar evolução financeira

- **QUANDO** um usuário selecionar um período com operações registradas
- **ENTÃO** o sistema DEVE apresentar gráficos com a evolução dos indicadores financeiros disponíveis

### Requirement: Filtros do dashboard

**MUST:** O sistema DEVE permitir filtrar os indicadores por período.

Quando existirem dados suficientes, o sistema DEVE permitir filtrar ou agrupar informações por produto, categoria e canal de venda.

Os filtros DEVEM atualizar os indicadores, gráficos e tabelas relacionados.

#### Cenário: Aplicar filtro de período

- **QUANDO** um usuário selecionar uma data inicial e uma data final válidas
- **ENTÃO** o sistema DEVE atualizar as informações para considerar somente as operações correspondentes ao período selecionado

#### Cenário: Aplicar filtro por categoria

- **QUANDO** um usuário selecionar uma categoria
- **ENTÃO** o sistema DEVE apresentar os dados dos produtos e das operações correspondentes à categoria selecionada, conforme o indicador consultado

### Requirement: Relatórios de vendas e resultados

**MUST:** O sistema DEVE permitir consultar relatórios de vendas com data, canal de origem, receita, CMV, custos de venda, resultado e margem.

O sistema DEVE permitir consultar os resultados de forma consolidada e por venda.

Os relatórios DEVEM respeitar os filtros selecionados pelo usuário.

#### Cenário: Consultar relatório financeiro

- **QUANDO** um usuário solicitar um relatório financeiro para determinado período
- **ENTÃO** o sistema DEVE apresentar os valores consolidados e permitir consultar os detalhes das vendas incluídas no resultado

### Requirement: Relatórios de estoque

Este requisito é normativo (MUST).

O sistema DEVE permitir consultar relatórios de produtos com quantidade disponível, estoque mínimo, custo médio e valor estimado em estoque.

O sistema DEVE permitir identificar produtos abaixo ou no limite do estoque mínimo.

O sistema DEVE disponibilizar o histórico de entradas e movimentações para consulta.

Quando os dados de quantidade, custo médio ou estoque mínimo estiverem ausentes, nulos ou inválidos, o relatório DEVE apresentá-los como indisponíveis ou indeterminados. Os gráficos quantitativos DEVEM omitir os valores desconhecidos em vez de plotá-los como zero e DEVEM informar quando os dados estiverem incompletos ou não forem suficientes para gerar um gráfico.

#### Cenário: Consultar relatório de estoque baixo

- **QUANDO** um usuário solicitar a relação de produtos com estoque baixo
- **ENTÃO** o sistema DEVE apresentar os produtos cuja quantidade disponível seja igual ou inferior ao estoque mínimo cadastrado

#### Cenário: Consultar movimentações de um produto

- **QUANDO** um usuário selecionar um produto em um relatório de estoque
- **ENTÃO** o sistema DEVE permitir consultar o histórico de entradas, saídas, ajustes, perdas e devoluções registradas para esse produto

#### Cenário: Exibir gráficos com dados incompletos

- **QUANDO** produtos retornados possuírem quantidade ou valor estimado indisponível
- **ENTÃO** os gráficos DEVEM omitir esses valores do eixo numérico, identificar a incompletude e NÃO DEVEM representá-los como zero

#### Cenário: Exibir gráfico sem dados suficientes

- **QUANDO** não houver valores conhecidos e válidos suficientes para um gráfico
- **ENTÃO** o sistema DEVE apresentar uma mensagem de indisponibilidade em vez de um gráfico que sugira valores inexistentes

### Requirement: Consistência dos indicadores e relatórios

**MUST:** O sistema DEVE utilizar as mesmas regras de cálculo financeiro e de estoque nos indicadores, gráficos e relatórios.

O sistema NÃO DEVE apresentar valores que incluam operações canceladas como se fossem vendas válidas.

O sistema DEVE atualizar as informações apresentadas quando houver alterações confirmadas nos registros que afetam os indicadores.

#### Cenário: Conferir indicador com relatório

- **QUANDO** um usuário comparar um indicador do dashboard com o relatório correspondente, utilizando os mesmos filtros
- **ENTÃO** os valores DEVEM ser consistentes entre as duas visualizações

#### Cenário: Considerar venda cancelada

- **QUANDO** uma venda estiver cancelada
- **ENTÃO** o sistema DEVE tratar seus valores e suas movimentações conforme as regras de cancelamento, sem contabilizá-la como uma venda válida

## Estado atual da integração

O dashboard e os relatórios usam `GET /product` para consultar o saldo atual dos produtos ativos. Os indicadores de vendas usam `GET /sale` com `sales_channel`, status `registrada`, período e paginação, e consultam `GET /sale/{id}` para obter o resumo financeiro validado pelo Xano. A listagem de vendas exige um canal; não há consulta global de vendas sem esse filtro.

O endpoint de produtos fornece uma fotografia atual, não um histórico de estoque por período. Os contratos disponíveis também não sustentam agrupamento de vendas por categoria nem relatórios de movimentações históricas nestas telas. Esses dados permanecem indisponíveis até que existam endpoints e campos confirmados para atendê-los. Falhas ou respostas incompletas do Xano não são substituídas por dados demonstrativos.
