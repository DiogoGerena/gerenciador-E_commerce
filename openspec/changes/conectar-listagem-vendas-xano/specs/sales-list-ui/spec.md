## Purpose

Define o comportamento da listagem operacional de vendas conectada ao Xano, para que usuários consultem registros reais com filtros, paginação e estados de carregamento/erro sem confundir dados demonstrativos com dados persistidos.

## ADDED Requirements

### Requirement: Consultar e apresentar vendas reais

A tela de Vendas MUST consultar os cabeçalhos reais de vendas do Xano usando o token de sessão ativo e apresentar somente os registros retornados. A listagem MUST NOT inventar ou exibir clientes, CMV, lucro, margem, custos ou outros campos que não estejam presentes na resposta. Uma resposta vazia MUST ser apresentada como lista vazia e não substituída por dados demonstrativos.

#### Scenario: Carregar vendas existentes

- **WHEN** a listagem for consultada com sessão válida e o Xano retornar vendas
- **THEN** a tela MUST apresentar os campos existentes nos cabeçalhos recebidos sem adicionar dados fictícios ou financeiros calculados localmente

#### Scenario: Não há vendas na página consultada

- **WHEN** o Xano retornar uma lista `items` vazia
- **THEN** a tela MUST informar que não há vendas correspondentes e MUST NOT apresentar registros demonstrativos

### Requirement: Filtrar e paginar a listagem

A tela MUST disponibilizar filtros de canal, número do pedido, status, data inicial e data final usando somente os parâmetros documentados. A paginação MUST utilizar `page`, `per_page`, `nextPage`, `prevPage`, `itemsTotal` e `pageTotal` da resposta e MUST preservar os filtros ativos ao navegar. Datas DEVEM ser enviadas sem conversão até confirmação do formato contratual.

#### Scenario: Consultar com filtros aplicados

- **WHEN** o usuário submeter filtros preenchidos
- **THEN** a tela MUST consultar o Xano com somente os filtros não vazios e reiniciar a página para a primeira página do novo conjunto filtrado

#### Scenario: Navegar entre páginas

- **WHEN** o usuário selecionar uma página seguinte ou anterior disponível
- **THEN** a tela MUST consultar a página indicada pelos metadados do Xano, preservando os filtros e o tamanho de página

#### Scenario: Preservar consulta após rerun

- **WHEN** a tela rerenderizar após interação de filtro ou paginação
- **THEN** MUST preservar os filtros e a página atual na sessão e não MUST substituir o resultado por dados demonstrativos

### Requirement: Comunicar estados de consulta e falhas

A tela MUST indicar carregamento durante a consulta, apresentar erros de autenticação e autorização com orientação compreensível e informar falhas de conexão ou serviço sem apresentar uma listagem como sucesso. A ausência de token MUST ser tratada como sessão expirada, sem efetuar chamada ao Xano.

#### Scenario: Token ausente

- **WHEN** a tela não possuir token de sessão
- **THEN** MUST informar que a sessão expirou e não MUST chamar o endpoint de vendas

#### Scenario: Xano rejeita autenticação ou permissão

- **WHEN** o Xano retornar HTTP 401 ou 403
- **THEN** a tela MUST informar sessão inválida ou permissão insuficiente sem exibir dados fictícios

#### Scenario: Falha HTTP ou de conexão

- **WHEN** uma consulta falhar por erro HTTP, conexão ou resposta inválida
- **THEN** a tela MUST informar a falha e MUST NOT apresentar a consulta como concluída com dados demonstrativos
