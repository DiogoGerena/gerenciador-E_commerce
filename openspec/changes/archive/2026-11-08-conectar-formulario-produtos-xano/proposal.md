## Why

O formulário ativo de produtos em `app/erp_modules.py` ainda é demonstrativo e não chama o cliente Xano já disponível, impedindo que um usuário autenticado cadastre um produto pela interface. Conectar o formulário ao contrato existente permite um fluxo real de criação sem alterar o login ou ampliar o contrato do backend nesta mudança.

## What Changes

- Conectar o envio do formulário ativo a `criar_produto()` em `app/xano_client.py`, usando o token da sessão autenticada.
- Carregar categorias ativas pelo cliente existente e enviar o ID da categoria selecionada.
- Validar os campos compatíveis antes da chamada e apresentar sucesso somente quando o cliente confirmar a criação.
- Tratar erros de requisição e respostas sem confirmação sem falso sucesso, preservando os dados digitados para correção ou nova tentativa.
- Manter visíveis os campos do formulário que não fazem parte do contrato atual, mas identificá-los claramente como não persistidos e excluí-los da confirmação de sucesso.
- Adicionar testes locais da integração da interface com o cliente usando mocks para sucesso, erros e resposta inconclusiva.

## Capabilities

### New Capabilities

Nenhuma.

### Modified Capabilities

- `cadastro-produtos-fornecedores`: especificar o fluxo de criação pela interface, seleção de categoria ativa e feedback fiel ao resultado confirmado pelo backend.

## Impact

- Código: `app/erp_modules.py`, com reutilização das funções existentes `listar_categorias_ativas()` e `criar_produto()` em `app/xano_client.py`.
- Testes: testes unitários de interface/handler com mocks, sem chamadas reais ao Xano.
- Autenticação: leitura do token e do usuário já existentes em `st.session_state`; nenhuma mudança ao login, à autenticação ou às permissões.
- Contrato: sem dependências novas nem alterações no Xano. O `POST /product` aceita `name`, `sku`, `category_id`, `sale_price` e `min_stock`; nome, categoria, preço e estoque mínimo são obrigatórios, e SKU é opcional. `description`, fornecedor, quantidade inicial, custo de aquisição e custo de embalagem não são aceitos pelo endpoint e não serão enviados nem apresentados como salvos. A resposta de sucesso é o registro criado diretamente como `product` (“As Self”).
- O estado inicial do worktree, incluindo alterações locais existentes em `app/Home.py`, deve ser preservado. A implementação não deve descartar, sobrescrever ou incorporar essas alterações nem acrescentar mudanças em login, autenticação ou outros arquivos fora do escopo.
