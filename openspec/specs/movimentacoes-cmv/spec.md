# movimentacoes-cmv Specification

## Purpose

Esta capacidade registra, mantém íntegro e permite consultar o histórico de movimentações de estoque, assegurando que alterações de quantidade sejam rastreáveis e consistentes.

## Requirements

### Requirement: Registro de movimentações de estoque

**MUST:** O sistema DEVE registrar as movimentações que alterem a quantidade disponível dos produtos.

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

**MUST:** O sistema NÃO DEVE permitir movimentações que resultem em quantidade disponível negativa.

O sistema DEVE validar a quantidade disponível antes de confirmar uma saída de estoque.

O sistema DEVE garantir que a atualização da quantidade e o registro da movimentação sejam realizados de forma consistente.

#### Cenário: Saída com estoque insuficiente

- **QUANDO** um usuário tentar registrar uma saída superior à quantidade disponível
- **ENTÃO** o sistema DEVE rejeitar a saída, informar que o estoque é insuficiente e manter inalterados o saldo e o histórico de movimentações.

### Requirement: Consulta paginada de movimentações de estoque

**MUST:** O sistema DEVE permitir consultar o histórico de movimentações por página, sem exigir filtros opcionais não informados. Deve enviar os nomes de parâmetros aceitos pelo serviço, omitir filtros ausentes ou em branco, e limitar `per_page` ao intervalo de 1 a 100. A primeira consulta deve usar página 1 e 20 registros por página por padrão.

**MUST:** O sistema DEVE apresentar os registros da página atual retornados pelo serviço em resposta paginada que contenha `movements` e/ou `items`, sem descartar a página solicitada nem apresentar registros demonstrativos. A interface DEVE permitir navegar entre páginas e indicar a página atual e a quantidade retornada.

**MUST:** Na ausência de metadados de paginação confirmados, a interface NÃO DEVE inferir que não há próxima página pelo número de registros retornados, inclusive quando a página contiver 100 registros. A navegação para a próxima página DEVE permanecer disponível após uma consulta bem-sucedida, mesmo quando a página estiver vazia ou incompleta.

**MUST:** A consulta DEVE ocorrer somente após uma ação explícita do usuário. Quando o serviço rejeitar a solicitação, o sistema DEVE apresentar o status HTTP e uma mensagem diagnóstica sanitizada, sem expor tokens ou dados de autenticação.

#### Cenário: Consultar movimentações sem filtros opcionais

- **QUANDO** o usuário solicitar o histórico sem informar produto, tipo ou datas
- **ENTÃO** o sistema DEVE omitir esses parâmetros opcionais da requisição e consultar a primeira página com o tamanho padrão

#### Cenário: Enviar filtros informados

- **QUANDO** o usuário informar filtros opcionais válidos
- **ENTÃO** o sistema DEVE encaminhar cada filtro usando o nome de parâmetro correspondente aceito pelo serviço e omitir os demais

#### Cenário: Exibir uma resposta paginada

- **QUANDO** o serviço retornar os registros da página em `movements` ou `items`
- **ENTÃO** o sistema DEVE apresentar os registros retornados para a página solicitada sem duplicá-los ou substituir a resposta por dados demonstrativos

#### Cenário: Navegar entre páginas

- **QUANDO** o usuário solicitar a página seguinte ou anterior
- **ENTÃO** o sistema DEVE consultar explicitamente a página correspondente, preservar os filtros atuais e indicar a página efetivamente exibida

#### Cenário: Limitar o tamanho da página

- **QUANDO** o usuário escolher a quantidade de registros por página
- **ENTÃO** o sistema DEVE aceitar somente valores entre 1 e 100 e reiniciar a navegação na primeira página quando os filtros ou o tamanho da página mudarem

#### Cenário: Informar erro HTTP sem expor credenciais

- **QUANDO** o serviço rejeitar a consulta com erro HTTP
- **ENTÃO** o sistema DEVE apresentar o status e os detalhes úteis retornados pelo serviço após sanitização, sem revelar token ou cabeçalho de autenticação
