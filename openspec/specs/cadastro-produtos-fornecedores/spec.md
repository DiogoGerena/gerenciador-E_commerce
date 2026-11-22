# cadastro-produtos-fornecedores Specification

## Purpose
TBD - created by archiving change controle-financeiro-estoque. Update Purpose after archive.

## Requirements

### Requirement: Cadastro de produtos

O sistema DEVE permitir que usuários autorizados cadastrem produtos com nome, categoria, quantidade mínima de estoque e preço de venda. Esses quatro campos são obrigatórios. O SKU é opcional. `description` é um campo opcional e anulável de texto no JSON Body do `POST /product`, persistido na coluna `product.description`; o backend normaliza espaços e inclui o campo na resposta. O cliente DEVE enviar a descrição não vazia e DEVE omitir uma descrição vazia. O sistema DEVE respeitar os valores padrão definidos pelo backend para campos não recebidos.

O sistema DEVE permitir a identificação de cada produto por um identificador único.

O sistema DEVE validar os campos obrigatórios antes de salvar um produto.

O sistema DEVE alinhar o payload de criação ao contrato do endpoint Xano, sem exigir que o frontend envie o campo `status` quando o backend define o valor padrão `ativo`.

O sistema DEVE permitir que o usuário selecione uma categoria ativa disponível e enviar o `category_id` correspondente no cadastro do produto.

O sistema DEVE informar quando categorias não puderem ser carregadas ou não houver categoria ativa e NÃO DEVE permitir um envio sem categoria válida.

O formulário DEVE enviar somente os inputs confirmados do cadastro atual: `name` (texto), `category_id` (inteiro), `min_stock` (inteiro), `sale_price` (decimal), `sku` (texto opcional) e `description` (texto opcional e anulável). Fornecedores, quantidade inicial em estoque, custo de aquisição e custo de embalagem não fazem parte do contrato atual, DEVEM ser identificados como não persistidos e NÃO DEVEM ser enviados nem apresentados como salvos.

O sistema NÃO DEVE armazenar o custo de aquisição diretamente no cadastro principal do produto, pois os custos de aquisição serão registrados nas entradas de estoque.

O sistema MUST confirmar a criação do produto no backend Xano antes de informar que o cadastro foi concluído.

Para o `POST /product` atual, a confirmação DEVE ser baseada no objeto direto do registro retornado como `product` (“As Self”). Se o objeto incluir `id`, esse identificador DEVE ser válido. O sistema NÃO DEVE aceitar resposta vazia, envelope não documentado ou status genérico como confirmação.

#### Cenário: Cadastro de produto válido

- **WHEN** um usuário autorizado preencher os campos suportados com dados válidos e selecionar uma categoria ativa
- **THEN** o sistema DEVE enviar os valores do formulário e o ID real da categoria selecionada para criação do produto
- **AND** o sistema DEVE informar sucesso somente após receber confirmação válida do backend

#### Cenário: Cadastro com descrição preenchida

- **WHEN** o usuário informar uma descrição não vazia
- **THEN** o cliente DEVE enviar o texto em `description` no JSON Body do `POST /product`
- **AND** o cliente DEVE confirmar que a resposta contém a descrição normalizada pelo backend antes de informar sucesso

#### Cenário: Cadastro com descrição vazia

- **WHEN** a descrição estiver vazia ou contiver somente espaços
- **THEN** o cliente DEVE omitir `description` do payload
- **AND** aceitar somente uma resposta confirmada com descrição nula ou vazia

#### Cenário: Campos sem persistência no contrato atual

- **WHEN** o formulário também exibir fornecedores, quantidade em estoque, custo de aquisição ou custo de embalagem
- **THEN** o sistema DEVE identificar esses campos como não persistidos pelo cadastro atual
- **AND** a confirmação de criação NÃO DEVE afirmar que esses valores foram salvos

#### Cenário: Categorias ativas carregadas para seleção

- **WHEN** um usuário autenticado abrir o formulário e o endpoint retornar categorias ativas válidas
- **THEN** o sistema DEVE apresentar essas categorias para seleção e associar a opção escolhida ao seu `category_id`

#### Cenário: Falha ou ausência de categoria ativa

- **WHEN** a consulta de categorias falhar ou não retornar categorias ativas válidas
- **THEN** o sistema DEVE informar que não é possível selecionar uma categoria
- **AND** o sistema NÃO DEVE enviar a criação com categoria demonstrativa, vazia ou inválida

#### Cenário: Cadastro com campos obrigatórios ausentes

- **WHEN** um usuário tentar cadastrar um produto sem preencher um ou mais campos obrigatórios
- **THEN** o sistema DEVE informar quais campos precisam ser preenchidos e NÃO DEVE enviar o cadastro

#### Cenário: Campos não aceitos pelo endpoint

- **WHEN** o formulário exibir campos demonstrativos que não fazem parte dos inputs do endpoint
- **THEN** a interface DEVE identificá-los como não persistidos
- **AND** o sistema NÃO DEVE incluí-los no payload de criação

#### Cenário: Cadastro com quantidade mínima inválida

- **WHEN** um usuário informar uma quantidade mínima de estoque negativa
- **THEN** o sistema DEVE rejeitar o valor e informar que a quantidade mínima não pode ser negativa
- **AND** o sistema NÃO DEVE enviar o cadastro

#### Cenário: Cadastro confirmado pelo backend

- **WHEN** um usuário enviar um formulário válido e o Xano confirmar a criação do produto
- **THEN** o sistema DEVE informar que o cadastro foi concluído
- **AND** o produto cadastrado DEVE poder ser consultado novamente no backend

#### Cenário: Falha ao cadastrar produto

- **WHEN** um usuário enviar o formulário e o backend rejeitar a solicitação ou ocorrer uma falha de comunicação
- **THEN** o sistema DEVE informar que o cadastro não foi confirmado
- **AND** o sistema NÃO DEVE apresentar a operação como concluída
- **AND** os valores preenchidos DEVEM permanecer disponíveis para correção ou nova tentativa

#### Cenário: Resposta sem confirmação de criação

- **WHEN** o backend retornar uma resposta que não permita confirmar a criação do produto
- **THEN** o sistema DEVE informar que o resultado não pôde ser confirmado
- **AND** o sistema NÃO DEVE informar sucesso nem limpar os valores preenchidos
- **AND** o sistema DEVE orientar a verificar o resultado antes de repetir o envio para evitar duplicidade

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

### Requirement: Categorias de produtos

O sistema DEVE permitir cadastrar, consultar e editar categorias para organizar os produtos.

O nome de cada categoria DEVE ser obrigatório.

O sistema DEVE impedir o cadastro de categorias com nomes duplicados, desconsiderando diferenças entre letras maiúsculas e minúsculas.

O sistema DEVE permitir identificar se uma categoria está ativa ou inativa.

#### Cenário: Cadastro de categoria

- **QUANDO** um usuário autorizado cadastrar uma categoria com nome válido e ainda não utilizado
- **ENTÃO** o sistema DEVE salvar a categoria

#### Cenário: Categoria duplicada

- **QUANDO** um usuário tentar cadastrar uma categoria cujo nome já exista, mesmo com diferenças entre letras maiúsculas e minúsculas
- **ENTÃO** o sistema NÃO DEVE criar uma categoria duplicada e DEVE informar o motivo

#### Cenário: Inativação de categoria em uso

- **QUANDO** um usuário inativar uma categoria vinculada a produtos existentes
- **ENTÃO** o sistema DEVE preservar os produtos e seus históricos e NÃO DEVE permitir que a categoria inativa seja utilizada em novos cadastros de produtos

### Requirement: Cadastro de fornecedores

O sistema MUST listar e consultar fornecedores a partir dos dados retornados pelo Xano. `GET /supplier/{supplier_id}` retorna o registro completo para sessão autenticada de nível operacional; fornecedor inexistente retorna HTTP 404.

`GET /supplier` exige o parâmetro de query `status`. A consulta padrão de fornecedores MUST enviar `status=ativo`, inclusive quando o usuário não informa um filtro de status.

O perfil Adm MUST ser exigido pelo backend para criar, editar e inativar fornecedores. `POST /supplier` aceita `name` obrigatório e `contact_name`, `cnpj`, `email` e `phone` opcionais; o status inicial é definido pelo backend como `ativo`. `PATCH /supplier/{supplier_id}` aceita esses campos e `status` opcional. Campos omitidos ou null preservam o valor atual. CNPJ duplicado ou e-mail inválido são rejeitados com HTTP 400; fornecedor inexistente retorna HTTP 404.

O sistema MUST preservar os campos de contato presentes na resposta documentada, incluindo contato e telefone quando fornecidos, sem descartar dados válidos durante a normalização. A interface MUST usar somente campos e filtros confirmados pelo contrato; filtros não documentados MUST NOT ser enviados.

O formulário MUST usar somente os campos acima. O sistema MUST validar localmente formato e dígitos verificadores do CNPJ quando informado, sem enviar CNPJ vazio como identificador; a validação de duplicidade do backend MUST continuar autoritativa. O backend não valida os dígitos verificadores do CNPJ.

#### Cenário: Listagem de fornecedores do Xano

- **WHEN** um usuário autenticado abrir a consulta de fornecedores
- **THEN** o sistema MUST exibir os fornecedores retornados pelo Xano e preservar seus campos documentados, incluindo dados de contato disponíveis
- **AND** a requisição MUST incluir `status=ativo` quando nenhum filtro de status for informado
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

#### Cenário: Vincular fornecedor a produto

- **WHEN** endpoints documentados de associação estiverem disponíveis e um usuário autorizado vincular um produto a um fornecedor ativo
- **THEN** o sistema MUST persistir o vínculo por meio do backend

#### Cenário: Vincular vários fornecedores ao mesmo produto

- **WHEN** endpoints documentados de associação estiverem disponíveis e um usuário autorizado vincular mais de um fornecedor ativo ao mesmo produto
- **THEN** o sistema MUST manter os vínculos confirmados pelo backend para consulta e utilização nas entradas de estoque

#### Cenário: Impedir vínculo duplicado

- **WHEN** endpoints documentados de associação estiverem disponíveis e um usuário tentar repetir um vínculo já persistido
- **THEN** o sistema MUST NOT duplicar a relação e MUST informar o resultado retornado pelo backend

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
