## Why

A tela atual de Vendas apresenta pedidos e clientes demonstrativos e não consulta as vendas reais disponíveis no Xano. Esta etapa substitui somente a listagem operacional por consulta autenticada, filtrável e paginada, evitando apresentar dados fictícios como registros reais.

## What Changes

- Conectar a listagem de `render_vendas` à função já existente `listar_vendas`.
- Adicionar filtros de canal, número do pedido, status e intervalo de datas, com paginação baseada no envelope do Xano.
- Preservar filtros e página na sessão, apresentar estados de carregamento, vazio e erro e remover dados demonstrativos da listagem.
- Criar testes mockados focados na tela de listagem.

## Capabilities

### New Capabilities
- `sales-list-ui`: listagem visual de vendas reais com filtros, paginação e estados de consulta.

### Modified Capabilities

## Impact

- Código: `app/erp_modules.py`, exclusivamente a listagem de `render_vendas`.
- Testes: novo arquivo de testes de interface para listagem de vendas, usando mocks.
- Dependência: função `listar_vendas` existente em `app/xano_client.py`.
- Cadastro, detalhe, importação, cancelamento e demais fluxos de vendas permanecem fora desta etapa.
