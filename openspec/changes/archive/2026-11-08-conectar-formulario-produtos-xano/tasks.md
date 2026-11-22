## 1. Preparar o contrato e o fluxo de seleção

- [x] 1.1 Adicionar uma exceção específica de resultado inconclusivo em `app/xano_client.py`, compatível com `ValueError`, e usá-la somente quando a resposta não confirmar a criação; verificar os testes existentes de confirmação e resposta inconclusiva.
- [x] 1.2 Carregar categorias ativas com o token autenticado e associar cada opção de seleção ao ID validado do registro; verificar com mocks que IDs reais são mantidos e que erro/lista vazia bloqueiam o envio.

## 2. Conectar e apresentar a submissão do formulário

- [x] 2.1 Conectar o botão de cadastro a `criar_produto()` com `name`, `category_id`, `min_stock`, `sale_price` e SKU opcional; não enviar `description`, status nem valores de campos sem suporte; verificar os argumentos da chamada por mock.
- [x] 2.2 Validar nome, categoria ativa, estoque mínimo inteiro não negativo e preço decimal não negativo antes da requisição; identificar descrição, fornecedor, quantidade inicial, custo de aquisição e custo de embalagem como não persistidos, e verificar que valores inválidos não chamam o cliente.
- [x] 2.3 Apresentar estados distintos para confirmação, erro HTTP/rede e resultado inconclusivo; após confirmação, limpar os campos e manter a mensagem de sucesso; em falha, preservar os valores sem mostrar sucesso nem reenviar automaticamente; verificar os estados com mocks e garantir que não há token ou segredo nas mensagens.

## 3. Testar a integração local da interface

- [x] 3.1 Adicionar testes locais mockados para envio confirmado, falha HTTP/rede, validação, categorias indisponíveis e resposta inconclusiva; verificar que não ocorre chamada externa ao Xano e que a suíte direcionada passa.
- [x] 3.2 Registrar o estado inicial do worktree antes da implementação; executar `python -m unittest discover -s tests` e uma verificação de renderização da tela de Produtos com dependências externas mockadas; confirmar que a tela não gera exceção e que a implementação não descartou, sobrescreveu ou incorporou mudanças locais preexistentes nem acrescentou alterações em `app/Home.py`, login, autenticação ou outros arquivos fora do escopo, comparando o worktree final com o estado inicial registrado.
