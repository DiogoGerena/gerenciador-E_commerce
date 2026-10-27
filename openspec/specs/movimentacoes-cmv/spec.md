# movimentacoes-cmv Specification

## Purpose
TBD - created by archiving change controle-financeiro-estoque. Update Purpose after archive.

## Requirements

### Requirement: Registro de movimentações de estoque

O sistema DEVE registrar as movimentações que alterem a quantidade disponível dos produtos.

As movimentações DEVEM incluir entradas, saídas por venda, ajustes de estoque, perdas ou danos e devoluções.

Cada movimentação DEVE registrar o produto, a quantidade movimentada, o tipo de movimentação, a data e o usuário responsável.

O sistema DEVE manter um histórico das movimentações realizadas, permitindo consultar as alterações de estoque de cada produto.

#### Cenário: Registrar uma saída por venda

- **QUANDO** uma venda válida for registrada e confirmada
- **ENTÃO** o sistema DEVE registrar a saída das unidades vendidas e atualizar a quantidade disponível do produto

#### Cenário: Registrar perda ou dano

- **QUANDO** um usuário autorizado registrar a perda ou o dano de unidades de um produto
- **ENTÃO** o sistema DEVE registrar a movimentação, reduzir a quantidade disponível e preservar o motivo informado

#### Cenário: Consultar histórico de movimentações

- **QUANDO** um usuário consultar o histórico de um produto
- **ENTÃO** o sistema DEVE apresentar as movimentações com suas datas, quantidades, tipos e responsáveis

### Requirement: Integridade do estoque

O sistema NÃO DEVE permitir movimentações que resultem em quantidade disponível negativa.

O sistema DEVE validar a quantidade disponível antes de confirmar uma saída de estoque.

O sistema DEVE garantir que a atualização da quantidade e o registro da movimentação sejam realizados de forma consistente.

#### Cenário: Saída com estoque insuficiente

- **QUANDO** um usuário tentar registrar uma saída superior à quantidade disponível
- **ENTÃO** o sistema DEVE rejeitar a saída, informar que o estoque é insuficiente e manter inalterados o saldo e o histórico de movimentações.
