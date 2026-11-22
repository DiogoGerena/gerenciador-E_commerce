## MODIFIED Requirements

### Requirement: Consulta e edição de produtos

O sistema MUST permitir que usuários autenticados consultem produtos cadastrados, pesquisem por nome e combinem os filtros de categoria e situação suportados pelo contrato do Xano. Filtros não informados MUST ser omitidos da requisição.

O sistema MUST permitir consultar um produto por `GET /product/{product_id}` para sessão autenticada de nível operacional ou superior. A resposta é o registro completo; produto inexistente retorna HTTP 404.

O sistema MUST permitir que o perfil Adm edite somente `name`, `sku`, `category_id`, `sale_price`, `min_stock` e `status` por `PATCH /product/{product_id}`. Campos omitidos ou null preservam os valores atuais; categoria inexistente/inativa e SKU duplicado são rejeitados pelo backend com HTTP 400, e produto inexistente retorna HTTP 404. A edição MUST NOT enviar nem alterar `description`, `stock_quantity` ou `average_cost`.

O sistema MUST preservar o histórico de movimentações e registros financeiros relacionados ao produto. A inativação MUST usar a operação lógica documentada do backend, nunca exclusão física.

#### Cenário: Pesquisa de produto

- **WHEN** um usuário autenticado consultar produtos com nome, categoria e/ou situação
- **THEN** o sistema MUST encaminhar somente os filtros informados e suportados pelo contrato
- **AND** o sistema MUST apresentar os produtos retornados pelo Xano sem substituir resultados vazios por dados demonstrativos

#### Cenário: Consulta individual de produto

- **WHEN** um usuário selecionar um produto e a consulta por seu identificador retornar um registro válido
- **THEN** o sistema MUST exibir os dados cadastrais retornados pelo Xano
- **AND** o sistema MUST apresentar erro, sem inventar dados, quando o registro não existir ou a resposta for vazia ou inválida

#### Cenário: Edição de produto

- **WHEN** um usuário autorizado editar um produto existente com campos aceitos e valores válidos
- **THEN** o sistema MUST enviar somente os campos cadastrais confirmados pelo contrato
- **AND** o sistema MUST NOT enviar `description`, `stock_quantity` nem `average_cost`
- **AND** o sistema MUST preservar o histórico de estoque e financeiro relacionado ao produto

#### Cenário: Inativação lógica de produto

- **WHEN** um usuário Adm confirmar a inativação de um produto existente
- **THEN** o sistema MUST chamar `PATCH /product/{product_id}/deactivate` sem body
- **AND** o sistema MUST aceitar sucesso somente se a resposta confirmar o mesmo produto com `status = inativo`
- **AND** uma repetição da inativação MUST permanecer segura e idempotente

### Requirement: Cadastro de fornecedores

O sistema MUST listar e consultar fornecedores a partir dos dados retornados pelo Xano. `GET /supplier/{supplier_id}` retorna o registro completo para sessão autenticada de nível operacional; fornecedor inexistente retorna HTTP 404.

O perfil Adm MUST ser exigido pelo backend para criar, editar e inativar fornecedores. `POST /supplier` aceita `name` obrigatório e `contact_name`, `cnpj`, `email` e `phone` opcionais; o status inicial é definido pelo backend como `ativo`. `PATCH /supplier/{supplier_id}` aceita esses campos e `status` opcional. Campos omitidos ou null preservam o valor atual. CNPJ duplicado ou e-mail inválido são rejeitados com HTTP 400; fornecedor inexistente retorna HTTP 404.

O sistema MUST preservar os campos de contato presentes na resposta documentada, incluindo contato e telefone quando fornecidos, sem descartar dados válidos durante a normalização. A interface MUST usar somente campos e filtros confirmados pelo contrato; filtros não documentados MUST NOT ser enviados.

O formulário MUST usar somente os campos acima. O sistema MUST validar localmente formato e dígitos verificadores do CNPJ quando informado, sem enviar CNPJ vazio como identificador; a validação de duplicidade do backend MUST continuar autoritativa. O backend não valida os dígitos verificadores do CNPJ.

#### Cenário: Listagem de fornecedores do Xano

- **WHEN** um usuário autenticado abrir a consulta de fornecedores
- **THEN** o sistema MUST exibir os fornecedores retornados pelo Xano e preservar seus campos documentados, incluindo dados de contato disponíveis
- **AND** o sistema MUST exibir um estado vazio quando o backend retornar uma lista vazia
- **AND** o sistema MUST NOT exibir fornecedores ou indicadores demonstrativos

#### Cenário: Pesquisa e filtros de fornecedores

- **WHEN** um usuário pesquisar ou filtrar fornecedores usando critérios documentados pelo contrato
- **THEN** o sistema MUST enviar somente os parâmetros confirmados e apresentar os resultados correspondentes
- **AND** o sistema MUST NOT enviar parâmetros vazios ou não documentados

#### Cenário: Consulta individual de fornecedor

- **WHEN** um usuário selecionar um fornecedor e a consulta por seu identificador retornar um registro válido
- **THEN** o sistema MUST exibir os dados cadastrais e de contato documentados
- **AND** o sistema MUST informar que o fornecedor não foi encontrado ou que a resposta é inválida quando aplicável

#### Cenário: Cadastro de fornecedor

- **WHEN** um usuário Adm cadastrar um fornecedor usando campos aceitos e valores válidos
- **THEN** o sistema MUST enviar os dados conforme o payload documentado
- **AND** o sistema MUST indicar sucesso somente após uma resposta válida de confirmação
- **AND** erros de duplicidade de CNPJ retornados pelo backend MUST ser apresentados sem simular sucesso

#### Cenário: Edição de fornecedor

- **WHEN** um usuário Adm editar um fornecedor existente usando campos aceitos e valores válidos
- **THEN** o sistema MUST enviar somente os campos informados e aceitos pelo contrato
- **AND** campos omitidos ou null MUST preservar os valores atuais
- **AND** erros de CNPJ duplicado retornados pelo backend MUST ser apresentados sem simular sucesso

#### Cenário: Inativação lógica de fornecedor

- **WHEN** um usuário Adm confirmar a inativação de um fornecedor existente
- **THEN** o sistema MUST chamar `PATCH /supplier/{supplier_id}/deactivate` sem body
- **AND** o sistema MUST aceitar sucesso somente se a resposta confirmar o mesmo fornecedor com `status = inativo`
- **AND** uma repetição da inativação MUST permanecer segura e idempotente
- **AND** o sistema MUST preservar o fornecedor e o histórico de entradas de estoque

#### Cenário: Inativação de fornecedor

- **WHEN** o usuário confirmar a inativação de um fornecedor existente
- **THEN** o sistema MUST atualizar a listagem somente após confirmação válida do backend
- **AND** o sistema MUST NOT excluir fisicamente o fornecedor

#### Cenário: Validação local de CNPJ

- **WHEN** o usuário informar um CNPJ com formato ou dígitos verificadores inválidos
- **THEN** o sistema MUST informar a validação local e MUST NOT enviar o formulário
- **AND** a validação local MUST NOT substituir a verificação de duplicidade do backend

### Requirement: Relacionamento entre produtos e fornecedores

O sistema MUST persistir relações entre produtos e fornecedores somente por endpoints documentados do backend. Enquanto esses endpoints não estiverem disponíveis, o sistema MUST NOT simular, armazenar localmente ou apresentar como persistidos vínculos que o backend não confirmou. Quando endpoints compatíveis forem disponibilizados, as relações MUST preservar a cardinalidade e os dados opcionais definidos pelo contrato.

#### Cenário: Associação sem endpoint de persistência

- **WHEN** o backend não disponibilizar endpoints documentados para criar, consultar e remover associações entre produtos e fornecedores
- **THEN** o sistema MUST NOT apresentar uma associação como salva nem usá-la como vínculo persistido
- **AND** o sistema MUST manter a funcionalidade de associação pendente de suporte do backend

#### Cenário: Vincular fornecedor a produto

- **WHEN** endpoints documentados de associação estiverem disponíveis e um usuário autorizado vincular um produto a um fornecedor ativo
- **THEN** o sistema MUST persistir o vínculo por meio do backend

#### Cenário: Vincular vários fornecedores ao mesmo produto

- **WHEN** endpoints documentados de associação estiverem disponíveis e um usuário autorizado vincular mais de um fornecedor ativo ao mesmo produto
- **THEN** o sistema MUST manter os vínculos confirmados pelo backend para consulta e utilização nas entradas de estoque

#### Cenário: Impedir vínculo duplicado

- **WHEN** endpoints documentados de associação estiverem disponíveis e um usuário tentar repetir um vínculo já persistido
- **THEN** o sistema MUST NOT duplicar a relação e MUST informar o resultado retornado pelo backend

## ADDED Requirements

### Requirement: Confirmação e erros das operações cadastrais

O sistema MUST enviar o token de sessão nas operações protegidas e MUST tratar autenticação, autorização, erros HTTP, falhas de comunicação e respostas vazias ou malformadas sem expor tokens, credenciais ou dados pessoais desnecessários.

O sistema MUST apresentar sucesso somente quando a resposta satisfizer o formato de confirmação documentado para aquela operação. Para operações de leitura e atualização, a resposta MUST ser o registro direto com o identificador solicitado; criações MUST retornar o registro criado com identificador válido. Inativação MUST retornar o registro com status `inativo`. O sistema MUST propagar erros HTTP 400, 401, 403 e 404 e tratar falhas de conexão, sem sucesso fictício.

#### Cenário: Erro de backend ou comunicação

- **WHEN** uma operação cadastral receber erro HTTP, falhar por conexão ou retornar resposta inválida
- **THEN** o sistema MUST informar que a operação não foi confirmada e apresentar diagnóstico sanitizado
- **AND** o sistema MUST NOT apresentar sucesso nem expor token ou credenciais

#### Cenário: Contrato de confirmação não documentado

- **WHEN** não houver evidência suficiente do formato de payload ou resposta de uma operação
- **THEN** a operação MUST NOT ser implementada com campos, rotas ou formatos presumidos
- **AND** a lacuna MUST ser registrada para resolução antes da implementação
