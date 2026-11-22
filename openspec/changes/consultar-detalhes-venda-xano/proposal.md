## Why

A listagem de vendas já consulta registros reais, e o cliente já oferece uma consulta detalhada autenticada por ID, mas a interface ainda não permite abrir e compreender uma venda individual. Esta mudança conecta a seleção de uma venda da listagem à visualização dos dados e valores financeiros confirmados pelo Xano.

## What Changes

- Permitir abrir os detalhes de uma venda a partir da listagem existente.
- Consultar o registro, itens, custos e resumo financeiro pela função de cliente já existente.
- Apresentar somente os campos retornados pelo backend, sem preencher ausências ou recalcular valores financeiros.
- Tratar carregamento, sessão, autorização, não encontrado e falhas de integração na visualização.
- Adicionar testes mockados para a interação entre listagem e detalhe.

## Capabilities

### New Capabilities
- `sales-detail-ui`: consulta e apresentação de detalhes de uma venda a partir da listagem.

### Modified Capabilities

## Impact

- Interface: `app/erp_modules.py`, na listagem existente e em sua visualização detalhada.
- Testes: testes mockados da interface de vendas.
- Cliente: utiliza `consultar_venda(token, venda_id)` existente em `app/xano_client.py`, sem alterar seu contrato.
- Cadastro, edição, cancelamento, exclusão, importação e cálculos financeiros no frontend permanecem fora do escopo.
