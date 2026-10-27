## ADDED Requirements

### Requirement: Cálculo de indicadores financeiros gerenciais

O sistema DEVE calcular CMV, margem bruta, margem de contribuição, ponto de equilíbrio, lucro operacional, lucro líquido gerencial e ticket médio com base nos registros válidos do período selecionado.

Os cálculos DEVEM utilizar as regras documentadas em `design.md`, utilizar valores monetários com precisão decimal e evitar contabilizar o mesmo custo mais de uma vez.

#### Scenario: Calcular CMV e margem bruta

- **QUANDO** houver vendas válidas com itens e custos unitários históricos registrados
- **ENTÃO** o sistema DEVE calcular o CMV usando a quantidade considerada válida multiplicada pelo custo unitário histórico de cada item
- **E** DEVE calcular a margem bruta como receita líquida menos CMV

#### Scenario: Calcular margem de contribuição

- **QUANDO** existirem receita líquida e custos variáveis classificados para o período
- **ENTÃO** o sistema DEVE subtrair os custos variáveis da receita líquida
- **E** DEVE evitar contabilizar novamente custos já incluídos em outro componente do cálculo

#### Scenario: Ponto de equilíbrio sem dados suficientes

- **QUANDO** não houver dados suficientes para calcular uma taxa de margem de contribuição positiva
- **ENTÃO** o sistema DEVE informar que não é possível calcular o ponto de equilíbrio, sem apresentar um valor enganoso

#### Scenario: Calcular lucro gerencial

- **QUANDO** houver registros de custos, despesas e resultado financeiro para o período
- **ENTÃO** o sistema DEVE calcular os indicadores de lucro operacional e lucro líquido gerencial conforme os componentes explicitamente documentados
- **E** DEVE informar que esses indicadores são gerenciais e não substituem a contabilidade oficial

#### Scenario: Calcular ticket médio

- **QUANDO** houver pedidos válidos no período selecionado
- **ENTÃO** o sistema DEVE dividir o valor das vendas válidas pela quantidade de pedidos válidos
- **E** DEVE tratar períodos sem pedidos válidos sem dividir por zero

### Requirement: Despesas fixas

O sistema DEVE permitir registrar e consultar despesas fixas mensais com descrição, categoria, valor, recorrência, vencimento e situação de pagamento.

#### Scenario: Registrar despesa fixa

- **QUANDO** um usuário autorizado registrar uma despesa fixa com os campos obrigatórios válidos
- **ENTÃO** o sistema DEVE salvar a despesa para consulta e análise financeira

### Requirement: Fluxo de caixa realizado e projetado

O sistema DEVE apresentar separadamente o fluxo de caixa realizado e o fluxo de caixa projetado.

O fluxo realizado DEVE considerar entradas efetivamente recebidas e saídas efetivamente pagas. O fluxo projetado DEVE considerar valores previstos e suas datas esperadas, sem somar novamente valores que já foram realizados.

#### Scenario: Consultar fluxo realizado

- **QUANDO** o usuário consultar o fluxo de caixa realizado de um período
- **ENTÃO** o sistema DEVE incluir apenas lançamentos com recebimento ou pagamento efetivo no período

#### Scenario: Consultar fluxo projetado

- **QUANDO** o usuário consultar o fluxo de caixa projetado
- **ENTÃO** o sistema DEVE apresentar os valores previstos separadamente dos realizados
- **E** DEVE impedir que um lançamento realizado continue sendo contado como previsão pendente

### Requirement: Tratamento de cancelamentos e reembolsos

O sistema DEVE documentar e aplicar regras consistentes para cancelamentos e reembolsos nos cálculos de receita e ticket médio.

#### Scenario: Pedido cancelado

- **QUANDO** um pedido estiver cancelado
- **ENTÃO** o sistema NÃO DEVE contabilizá-lo como venda válida para receita e ticket médio
- **E** DEVE preservar o histórico da operação para conferência
