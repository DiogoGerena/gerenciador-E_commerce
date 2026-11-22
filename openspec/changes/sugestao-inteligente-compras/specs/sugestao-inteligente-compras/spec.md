# Sugestão inteligente de compras

## ADDED Requirements

### Requirement: Seleção do período histórico de vendas

O sistema DEVE permitir que o usuário selecione o período histórico utilizado para calcular a demanda dos produtos.

O sistema DEVE considerar somente vendas válidas e excluir vendas canceladas dos cálculos.

A média diária de unidades vendidas DEVE ser calculada dividindo a quantidade total de unidades vendidas no período pelo número de dias corridos do período selecionado, incluindo as datas inicial e final.

#### Scenario: Calcular a média diária de vendas

- **WHEN** houver vendas válidas no período selecionado
- **THEN** o sistema DEVE calcular a média diária de unidades vendidas para cada produto com dados suficientes.

#### Scenario: Excluir vendas canceladas

- **WHEN** existirem vendas canceladas no período selecionado
- **THEN** o sistema NÃO DEVE incluir as quantidades dessas vendas no cálculo da demanda.

### Requirement: Previsão de demanda para 15 dias

O sistema DEVE estimar a demanda dos próximos 15 dias utilizando a média diária de unidades vendidas no período histórico selecionado.

A demanda prevista DEVE ser calculada multiplicando a média diária de unidades vendidas por 15.

Para calcular a quantidade de reposição, a demanda prevista DEVE ser arredondada para o próximo número inteiro quando houver uma fração de unidade.

O sistema DEVE identificar previsões como estimativas, e NÃO como garantias de vendas futuras.

#### Scenario: Calcular a demanda prevista

- **WHEN** houver histórico de vendas suficiente para o produto
- **THEN** o sistema DEVE apresentar a demanda estimada para os próximos 15 dias.

### Requirement: Calcular a quantidade sugerida para compra

O sistema DEVE calcular a quantidade sugerida considerando a demanda prevista para 15 dias, o estoque mínimo cadastrado e o estoque atual disponível.

A quantidade sugerida DEVE utilizar a seguinte fórmula:

`quantidade_sugerida = max(0, ceil(demanda_prevista_15_dias) + estoque_minimo - estoque_atual)`

O sistema DEVE utilizar o estoque mínimo como uma reserva adicional à demanda prevista.

A quantidade sugerida DEVE ser um número inteiro não negativo.

#### Scenario: Sugerir reposição considerando demanda e estoque mínimo

- **WHEN** a demanda prevista, o estoque mínimo e o estoque atual estiverem disponíveis
- **THEN** o sistema DEVE calcular a quantidade sugerida conforme a fórmula definida.

#### Scenario: Estoque suficiente para a meta calculada

- **WHEN** o estoque atual for igual ou superior à soma da demanda prevista arredondada para cima e do estoque mínimo
- **THEN** o sistema DEVE recomendar zero unidades de compra.

#### Scenario: Produto sem estoque disponível

- **WHEN** o estoque atual for zero e houver dados suficientes para estimar a demanda
- **THEN** o sistema DEVE calcular a reposição considerando a demanda prevista e o estoque mínimo.

### Requirement: Estimar o investimento da compra

O sistema DEVE calcular o investimento estimado da compra sugerida utilizando a quantidade recomendada e o custo unitário de aquisição disponível.

O custo de aquisição DEVE respeitar as regras existentes de entradas de estoque, incluindo mercadoria, frete de entrada e outros custos adicionais de aquisição, bem como o custo médio ponderado vigente.

O investimento estimado DEVE ser identificado como projeção e NÃO DEVE ser registrado como despesa realizada ou entrada de estoque.

Quando não houver custo de aquisição confiável disponível, o sistema DEVE informar que não é possível calcular o investimento com os dados existentes.

#### Scenario: Calcular investimento com custo disponível

- **WHEN** houver quantidade sugerida e custo unitário de aquisição disponível
- **THEN** o sistema DEVE apresentar o investimento estimado da compra.

#### Scenario: Custo de aquisição indisponível

- **WHEN** não houver custo confiável para um produto
- **THEN** o sistema DEVE informar que o investimento não pode ser calculado e NÃO DEVE inventar um valor.

### Requirement: Apresentar indicadores financeiros projetados

O sistema DEVE apresentar somente indicadores financeiros que possam ser calculados com os dados disponíveis e pelas regras financeiras existentes.

O CMV DEVE respeitar o custo histórico registrado nos itens de venda e as regras existentes de custo médio ponderado.

Os custos da venda, incluindo comissão, impostos, frete de saída, embalagem e outros custos aplicáveis, NÃO DEVEM ser contabilizados duas vezes.

Receita, CMV, custos e resultados futuros, quando calculáveis, DEVEM ser identificados claramente como projeções.

O sistema NÃO DEVE apresentar projeções como resultados realizados ou como lucro líquido contábil.

#### Scenario: Dados suficientes para projeções financeiras

- **WHEN** houver dados suficientes para calcular um indicador financeiro
- **THEN** o sistema DEVE apresentar o valor estimado e identificar que se trata de uma projeção.

#### Scenario: Dados insuficientes para projeções financeiras

- **WHEN** faltarem preços, custos ou outras informações necessárias
- **THEN** o sistema DEVE informar quais indicadores não podem ser calculados sem inventar valores.

### Requirement: Explicar recomendações e limitações

O sistema DEVE apresentar, para cada recomendação, os dados relevantes para sua compreensão, incluindo o período histórico selecionado, a média diária de vendas, a demanda prevista, o estoque atual, o estoque mínimo e a quantidade sugerida.

Quando houver dados suficientes, o sistema DEVE apresentar também o investimento estimado.

O sistema DEVE informar quando os dados históricos forem insuficientes ou inconsistentes para produzir uma estimativa confiável.

A ausência de vendas válidas NÃO DEVE ser tratada automaticamente como prova de demanda futura igual a zero.

#### Scenario: Explicar uma recomendação

- **WHEN** o sistema gerar uma recomendação com dados suficientes
- **THEN** o usuário DEVE conseguir identificar os principais valores utilizados no cálculo.

#### Scenario: Histórico insuficiente

- **WHEN** não houver histórico válido suficiente para estimar a demanda de um produto
- **THEN** o sistema DEVE indicar que a recomendação é indisponível ou não confiável e informar o motivo.

### Requirement: Respeitar permissões e preservar os dados

O sistema DEVE aplicar no backend as permissões de acesso existentes.

A funcionalidade DEVE consultar os dados internos disponíveis no Xano e NÃO DEVE depender de APIs externas de marketplaces ou da Cargoos.

A geração de recomendações NÃO DEVE criar pedidos de compra, registrar entradas, alterar quantidades em estoque, modificar vendas ou gerar movimentações de estoque.

A funcionalidade DEVE ser somente consultiva.

#### Scenario: Consultar recomendações

- **WHEN** um usuário autorizado solicitar as sugestões de compra
- **THEN** o sistema DEVE apresentar as recomendações sem modificar os registros existentes.

#### Scenario: Usuário sem permissão

- **WHEN** um usuário não autorizado tentar acessar os dados ou executar operações protegidas
- **THEN** o backend DEVE negar o acesso conforme as permissões existentes.

#### Scenario: Verificar ausência de efeitos colaterais

- **WHEN** uma recomendação for calculada ou consultada
- **THEN** o sistema NÃO DEVE alterar o estoque, as vendas ou o histórico de movimentações.
