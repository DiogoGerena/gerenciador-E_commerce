# entradas-estoque-custos Specification

## Purpose
TBD - created by archiving change controle-financeiro-estoque. Update Purpose after archive.

## Requirements

### Requirement: Registro de entrada de estoque

O sistema DEVE permitir que usuários autorizados registrem entradas de produtos no estoque.

Cada entrada DEVE informar o produto, o fornecedor, a quantidade recebida, o custo unitário de aquisição, o frete de entrada e outros custos adicionais de aquisição, quando existirem.

O sistema DEVE registrar a data da entrada e o usuário responsável pelo lançamento.

O sistema DEVE permitir consultar o histórico das entradas de cada produto.

#### Cenário: Registrar uma entrada válida

- **QUANDO** um usuário autorizado registrar uma entrada com produto, fornecedor, quantidade e custos válidos
- **ENTÃO** o sistema DEVE salvar a entrada, atualizar o estoque e recalcular o custo médio ponderado do produto

#### Cenário: Registrar entrada com dados inválidos

- **QUANDO** um usuário tentar registrar uma entrada com quantidade igual ou inferior a zero, ou com custos negativos
- **ENTÃO** o sistema DEVE rejeitar a operação e informar os dados que precisam ser corrigidos

#### Cenário: Consultar histórico de entradas

- **QUANDO** um usuário consultar o histórico de um produto
- **ENTÃO** o sistema DEVE apresentar as entradas registradas, incluindo data, fornecedor, quantidade e custos de aquisição

### Requirement: Cálculo do custo de aquisição

O sistema DEVE calcular o custo total de aquisição de cada entrada considerando o valor de compra das mercadorias, o frete de entrada e outros custos adicionais relacionados à aquisição.

O custo unitário de aquisição DEVE ser calculado dividindo o custo total de aquisição pela quantidade recebida.

O sistema DEVE armazenar os valores utilizados no cálculo para permitir consultas e conferências posteriores.

#### Cenário: Calcular custo unitário de aquisição

- **QUANDO** uma entrada possuir quantidade, valor de compra, frete e outros custos adicionais válidos
- **ENTÃO** o sistema DEVE somar os custos de aquisição e dividir o resultado pela quantidade recebida para obter o custo unitário

### Requirement: Cálculo do custo médio ponderado

O sistema DEVE calcular o custo médio ponderado de cada produto considerando o estoque existente e o custo das novas entradas.

O cálculo DEVE considerar a quantidade disponível antes da entrada, o custo médio anterior, a quantidade recebida e o custo unitário da nova entrada.

O sistema DEVE utilizar o custo médio ponderado como referência para calcular o CMV das vendas.

#### Cenário: Atualizar custo médio após uma entrada

- **QUANDO** um produto possuir estoque com custo médio registrado e receber uma nova entrada válida
- **ENTÃO** o sistema DEVE recalcular o custo médio ponderado considerando as quantidades e os custos anteriores e novos

#### Cenário: Primeira entrada de um produto

- **QUANDO** um produto sem estoque receber sua primeira entrada válida
- **ENTÃO** o sistema DEVE utilizar o custo unitário dessa entrada como custo médio inicial

### Requirement: Atualização e integridade do estoque

O sistema DEVE atualizar a quantidade em estoque após cada entrada confirmada.

O sistema DEVE manter o histórico das movimentações de estoque para permitir a rastreabilidade das alterações.

O sistema NÃO DEVE permitir que uma entrada seja contabilizada mais de uma vez por causa de uma repetição da mesma solicitação.

#### Cenário: Atualizar quantidade em estoque

- **QUANDO** uma entrada válida for confirmada
- **ENTÃO** o sistema DEVE somar a quantidade recebida à quantidade disponível do produto

#### Cenário: Evitar duplicidade de entrada

- **QUANDO** o sistema receber novamente uma solicitação já processada
- **ENTÃO** o sistema DEVE impedir que a mesma entrada seja contabilizada duas vezes

### Requirement: Correção de entradas registradas

O sistema DEVE preservar a rastreabilidade quando uma entrada precisar ser corrigida ou cancelada.

O sistema NÃO DEVE permitir que uma correção ou cancelamento gere uma quantidade de estoque negativa.

O sistema DEVE manter informações sobre a entrada original e a correção realizada.

#### Cenário: Corrigir uma entrada

- **QUANDO** um usuário autorizado solicitar a correção de uma entrada registrada
- **ENTÃO** o sistema DEVE validar os impactos no estoque e no custo médio antes de confirmar a alteração

#### Cenário: Cancelar entrada com impacto no estoque

- **QUANDO** um usuário solicitar o cancelamento de uma entrada cujas mercadorias já tenham sido utilizadas em saídas de estoque
- **ENTÃO** o sistema DEVE impedir que o cancelamento produza estoque negativo ou inconsistência nos custos e DEVE informar a necessidade de uma correção compatível com o histórico
