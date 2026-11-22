## Context

Consulte `proposal.md` e a delta spec para motivação e comportamento esperado. O formulário ativo em `app/erp_modules.py::render_produtos()` atualmente contém nome, descrição, categoria, fornecedores, quantidade em estoque, estoque mínimo, custo de aquisição, custo de embalagem e preço de venda; seu botão Salvar não chama o cliente.

`app/xano_client.py` oferece `listar_categorias_ativas(token)` e `criar_produto(token, *, name, category_id, min_stock, sale_price, sku="")`. Conforme contrato confirmado, a criação envia somente os inputs `name`, `sku`, `category_id`, `sale_price` e `min_stock`. Descrição, fornecedor, quantidade inicial, custo de aquisição e custo de embalagem não são aceitos pelo endpoint. A lista de categorias ativa valida IDs inteiros positivos e o status ativo. `POST /product` retorna a variável `product` como “As Self”, ou seja, um objeto direto do registro criado; a confirmação valida esse registro e, quando presente, seu `id`.

O token e o usuário autenticado são mantidos em `st.session_state["auth_token"]` e `st.session_state["auth_user"]` por `app/Home.py`. O trabalho deve consumir essa sessão sem mudar o fluxo de login ou permissões. Os testes existentes em `tests/test_xano_config.py` mockam requisições HTTP para o cliente, mas não exercitam a submissão do formulário.

## Goals / Non-Goals

**Goals:**

- Fazer a submissão da tela ativa encaminhar apenas campos que o cliente já aceita e respeitar sua confirmação de criação.
- Carregar categorias ativas autenticadamente, mostrar uma seleção sem valor demonstrativo e transmitir o ID associado à opção selecionada.
- Distinguir confirmação, falha conhecida e resultado inconclusivo para não dar falso sucesso nem estimular duplicidade.
- Preservar os valores informados em falha e tornar explícito quais campos exibidos não são persistidos.
- Cobrir o caminho da interface com testes locais isolados por mocks.

**Non-Goals:**

- Alterar login, sessão, autenticação, autorização ou regras de permissões.
- Expandir o payload ou alterar o contrato remoto para persistir fornecedores, quantidade em estoque, custo de aquisição ou custo de embalagem.
- Fazer chamadas reais ao Xano nos testes locais ou criar dados reais.
- Alterar a listagem de produtos, outras telas ou `app/Home.py`.
- Descartar, sobrescrever ou incorporar alterações locais já existentes no início da implementação.

## Decisions

1. **Usar o cliente existente em vez de duplicar HTTP na tela.** `render_produtos()` deve chamar `listar_categorias_ativas()` e `criar_produto()` com o token autenticado em `st.session_state`. Isso preserva cabeçalhos, timeout, validação e mapeamento de payload já centralizados. A alternativa de fazer chamadas `requests` diretamente na tela duplicaria regras e facilitaria divergência do contrato.

2. **Usar registros de categoria como opções, não nomes demo nem uma seleção apenas textual.** Carregar as categorias ativas com o token e apresentar seus nomes; a opção selecionada deve manter associação inequívoca ao `id` validado retornado pelo cliente. Se necessário, desambiguar nomes iguais na apresentação com o ID, sem derivar ou inventar IDs. Falha de consulta ou lista vazia bloqueia o envio e mostra orientação clara; não há fallback para categorias fictícias.

3. **Mapear somente os inputs confirmados e identificar campos não persistidos.** Nome → `name`, categoria selecionada → `category_id`, estoque mínimo → `min_stock` e preço de venda → `sale_price` são obrigatórios; SKU → `sku` é opcional. Descrição pode permanecer como campo visual, mas deve ser identificada como não salva e nunca enviada. Fornecedor, quantidade inicial em estoque, custo de aquisição e custo de embalagem também não são aceitos, não são enviados e devem permanecer identificados como não persistidos. Não enviar `status`, pois o backend define o padrão.

4. **Representar o envio como evento de formulário e não limpar os dados antes da confirmação.** Usar o botão de submissão do formulário com chaves estáveis para os widgets. Validar nome, categoria ativa, SKU textual quando informado, estoque mínimo inteiro não negativo e preço decimal não negativo antes da chamada. Mostrar estado de carregamento durante o envio. Após confirmação válida, exibir sucesso e então limpar ou preparar um novo formulário; em qualquer falha ou resultado inconclusivo, preservar os valores para revisão.

5. **Classificar explicitamente os resultados do cliente.** O retorno normal de `criar_produto()` significa confirmação válida. Exceções de transporte/HTTP são falha; erros locais de validação mostram o problema do campo. Como hoje o cliente usa `ValueError` também para resposta sem confirmação, introduzir uma exceção específica de resultado inconclusivo que herde de `ValueError`, mantendo compatibilidade com chamadas existentes. A tela deve avisar que o cadastro não foi confirmado e recomendar consultar o resultado antes de reenviar, para reduzir risco de duplicidade. Não considerar HTTP 2xx, payload vazio, mensagem genérica ou exceção como sucesso.

6. **Testar sem serviços externos.** Adicionar testes locais seguindo o padrão `unittest` existente, usando mocks para funções de categoria/criação e widgets Streamlit ou uma pequena função de submissão isolável. Cobrir envio com payload e ID corretos, confirmação, erro HTTP/rede, validação local, categorias vazias/indisponíveis e resposta inconclusiva. Não usar credenciais nem instanciar chamadas reais ao Xano.

## Risks / Trade-offs

- [Uma resposta 2xx pode não conter o registro esperado] → Só considerar confirmação um objeto direto compatível com o registro de produto; não aceitar envelopes, status genéricos ou resposta vazia.
- [Categoria duplicada ou alteração entre carregamento e envio] → Ligar a seleção ao ID validado do registro carregado e não confiar em rótulos textuais como identificadores.
- [Resposta inconclusiva após o servidor talvez ter criado o produto] → Não declarar sucesso nem reenviar automaticamente; preservar os dados e orientar a verificar o resultado antes de tentar novamente.
- [Campos visíveis podem ser interpretados como persistidos] → Exibir indicação textual junto ao formulário e limitar o feedback de sucesso aos campos suportados.
- [Sessão sem token] → Não chamar o cliente; apresentar aviso de sessão/autenticação sem iniciar ou modificar o fluxo de login.

## Migration Plan

Não há migração de dados nem dependência nova. Antes de implementar, registrar o estado inicial do worktree sem substituir nem limpar mudanças existentes. Implementar a ligação na tela de produtos e a classificação de resposta no cliente, acrescentar testes mockados, executar a suíte local direcionada e validar renderização sem chamadas ao Xano. A verificação deve confirmar que a implementação não acrescentou alterações em `app/Home.py`, no login, na autenticação ou em outros arquivos fora do escopo, comparando com o estado inicial registrado. A reversão consiste em retirar somente as alterações desta implementação, preservando as funções de cliente existentes e todo o estado local preexistente.
