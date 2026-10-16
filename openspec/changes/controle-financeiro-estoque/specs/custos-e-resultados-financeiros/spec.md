## Objetivo

Definir os requisitos para registrar os custos relacionados às vendas e calcular o faturamento, o CMV, o resultado financeiro e a margem das operações de e-commerce.

## ADDED Requirements

### Requirement: Registro manual de vendas

O sistema DEVE permitir que um usuário autorizado registre manualmente uma venda, informando o canal de venda, o número do pedido quando disponível, a data da operação e os itens vendidos.

Cada item da venda DEVE conter o produto, a quantidade, o preço unitário de venda e os descontos aplicáveis, quando houver.

O sistema DEVE validar os dados obrigatórios, as quantidades e os valores informados antes de confirmar a venda.

O sistema DEVE preservar o preço de venda e o custo unitário histórico de cada item no momento do registro, para que alterações posteriores no cadastro do produto ou no custo médio não modifiquem os resultados históricos da venda.

O sistema DEVE integrar a confirmação da venda ao registro das movimentações de estoque e aos cálculos financeiros, impedindo baixas duplicadas e operações que resultem em estoque negativo.

#### Cenário: Registrar venda manual válida

- **QUANDO** um usuário autorizado informar os dados de uma venda e seus itens com valores válidos e estoque suficiente
- **ENTÃO** o sistema DEVE registrar a venda, preservar os valores históricos dos itens, atualizar o estoque e calcular os valores financeiros correspondentes

#### Cenário: Registrar venda com estoque insuficiente

- **QUANDO** um usuário tentar confirmar uma venda cuja quantidade exceda o estoque disponível
- **ENTÃO** o sistema DEVE rejeitar a operação sem efetuar a baixa de estoque nem confirmar os registros financeiros

#### Cenário: Impedir registro duplicado

- **QUANDO** o sistema identificar uma venda já registrada com o mesmo canal e número de pedido, quando disponíveis
- **ENTÃO** o sistema DEVE impedir o registro duplicado e informar o motivo ao usuário

### Requirement: Registro dos custos de venda

O sistema DEVE permitir registrar os custos relacionados a cada venda, incluindo comissão do marketplace, impostos, frete de saída, embalagem e outros custos adicionais.

O sistema DEVE permitir informar os custos individualmente por venda e, quando aplicável, por item vendido.

O sistema DEVE validar os valores informados, impedindo custos negativos.

O sistema DEVE preservar os valores utilizados nos cálculos para permitir consultas e conferências futuras.

#### Cenário: Registrar custos de uma venda

- **QUANDO** um usuário autorizado informar os custos de uma venda com valores válidos
- **ENTÃO** o sistema DEVE registrar os custos e utilizá-los nos cálculos financeiros da venda

#### Cenário: Informar custo inválido

- **QUANDO** um usuário informar um custo negativo
- **ENTÃO** o sistema DEVE rejeitar o valor e solicitar sua correção

### Requirement: Cálculo da receita de vendas

O sistema DEVE calcular a receita bruta de uma venda a partir da soma dos valores dos itens vendidos, considerando suas quantidades e preços unitários.

O sistema DEVE manter os valores de receita associados aos respectivos registros de venda.

#### Cenário: Calcular receita bruta

- **QUANDO** uma venda possuir um ou mais itens com quantidades e preços válidos
- **ENTÃO** o sistema DEVE somar os valores dos itens e apresentar a receita bruta da venda

### Requirement: Distribuição proporcional dos custos compartilhados

O sistema DEVE permitir distribuir custos compartilhados por uma venda entre seus itens de forma proporcional ao valor de venda de cada item.

O sistema DEVE utilizar o valor total de venda de cada item como base de cálculo da proporção.

A soma dos custos distribuídos entre os itens DEVE corresponder ao valor total do custo compartilhado, respeitando o arredondamento monetário.

#### Cenário: Distribuir frete entre itens

- **QUANDO** uma venda possuir vários itens e um custo de frete compartilhado
- **ENTÃO** o sistema DEVE distribuir o frete entre os itens proporcionalmente aos seus valores de venda

#### Cenário: Conferir a distribuição dos custos

- **QUANDO** o sistema concluir a distribuição de um custo compartilhado
- **ENTÃO** a soma dos valores atribuídos aos itens DEVE corresponder ao custo total informado, considerando os centavos e o arredondamento

### Requirement: Cálculo do CMV e dos custos totais

O sistema DEVE utilizar o CMV registrado para os itens vendidos no cálculo do resultado financeiro.

O sistema DEVE calcular o custo total da venda somando o CMV e os custos relacionados à venda.

Os custos de aquisição já considerados no custo médio ponderado NÃO DEVEM ser contabilizados novamente como custos de venda.

#### Cenário: Calcular custo total da venda

- **QUANDO** uma venda possuir CMV e custos de venda registrados
- **ENTÃO** o sistema DEVE somar esses valores para apresentar o custo total da operação

### Requirement: Cálculo do resultado financeiro

O sistema DEVE calcular o resultado após os custos registrados subtraindo da receita de vendas o CMV e os custos relacionados às vendas.

O sistema DEVE apresentar os valores de receita, CMV, custos de venda e resultado de forma separada, permitindo compreender a composição do resultado.

O resultado calculado NÃO DEVE ser apresentado como lucro líquido contábil, pois o sistema não contempla necessariamente todas as despesas, obrigações e ajustes de uma contabilidade completa.

#### Cenário: Calcular resultado positivo

- **QUANDO** a receita de uma venda for superior à soma do CMV e dos custos de venda
- **ENTÃO** o sistema DEVE apresentar um resultado positivo

#### Cenário: Calcular resultado negativo

- **QUANDO** a soma do CMV e dos custos de venda for superior à receita
- **ENTÃO** o sistema DEVE apresentar um resultado negativo e permitir identificar os custos que contribuíram para esse resultado

### Requirement: Cálculo da margem

O sistema DEVE calcular a margem de resultado como o resultado após os custos dividido pela receita de vendas, multiplicado por 100.

Quando a receita for igual a zero, o sistema NÃO DEVE realizar uma divisão por zero e DEVE apresentar a margem como não aplicável.

#### Cenário: Calcular margem de resultado

- **QUANDO** uma venda possuir receita diferente de zero e resultado financeiro calculado
- **ENTÃO** o sistema DEVE apresentar a margem percentual correspondente

#### Cenário: Venda sem receita

- **QUANDO** uma venda possuir receita igual a zero
- **ENTÃO** o sistema DEVE indicar que a margem não é aplicável

### Requirement: Histórico e atualização dos cálculos financeiros

O sistema DEVE preservar os valores e os critérios utilizados nos cálculos financeiros das vendas registradas.

O sistema DEVE manter a rastreabilidade das alterações nos custos e nos registros financeiros.

Quando um lançamento precisar ser corrigido, o sistema DEVE atualizar os cálculos afetados sem apagar o histórico original da operação.

#### Cenário: Consultar resultado histórico

- **QUANDO** um usuário consultar uma venda já registrada
- **ENTÃO** o sistema DEVE apresentar a receita, o CMV, os custos de venda, o resultado e a margem calculados com os dados registrados para aquela operação

#### Cenário: Corrigir um custo de venda

- **QUANDO** um usuário autorizado corrigir um custo registrado
- **ENTÃO** o sistema DEVE recalcular os valores financeiros afetados e preservar a rastreabilidade da correção