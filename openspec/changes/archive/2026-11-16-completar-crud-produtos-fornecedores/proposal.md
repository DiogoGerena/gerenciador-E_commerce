## Why

O módulo de produtos cobre pesquisa e cadastro, mas ainda não oferece consulta individual, edição ou inativação; a tela de fornecedores permanece demonstrativa apesar de existir consulta no cliente. Completar esses fluxos permitirá que o sistema use o Xano como fonte oficial sem simular persistência nem modificar dados de estoque.

## What Changes

- Ampliar a consulta de produtos com filtros combináveis documentados, consulta individual, edição cadastral e inativação lógica.
- Substituir a tela demonstrativa de fornecedores por listagem, detalhe, cadastro, edição e inativação lógica integrados ao Xano.
- Reutilizar a consulta existente de categorias ativas e preservar os dados de contato retornados para fornecedores.
- Exigir confirmação válida do backend para indicar sucesso e apresentar erros sem credenciais.
- Excluir desta mudança vínculos produto-fornecedor e qualquer alteração da política de permissões.
- Implementar as operações cujos contratos foram confirmados na auditoria técnica, sem inferir rotas, campos ou respostas além do que foi fornecido.

## Capabilities

### New Capabilities

Nenhuma.

### Modified Capabilities

- `cadastro-produtos-fornecedores`: definir os fluxos de consulta, filtros, detalhe, edição e inativação de produtos e fornecedores, incluindo limites de contrato e confirmação das operações.

## Impact

- Código potencialmente afetado: `app/xano_client.py`, `app/erp_modules.py`, `.env.example` e `README.md`.
- Testes potencialmente afetados ou adicionados: `tests/test_erp_product_form.py`, `tests/test_xano_config.py`, `tests/test_stock_entry_client.py` e testes específicos de produtos/fornecedores.
- APIs existentes do Xano de produtos, categorias e fornecedores; nenhuma rota ou dado do backend será alterado.
- Sem dependências novas. A integração real não será presumida por testes mockados.
