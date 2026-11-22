## MODIFIED Requirements

### Requirement: Cadastro de produtos

O sistema DEVE permitir que usuários autorizados cadastrem produtos com nome, categoria, quantidade mínima de estoque e preço de venda. Esses quatro campos são obrigatórios. O SKU é opcional. A descrição pode ser exibida na interface, mas o endpoint atual não a aceita; a interface DEVE identificá-la como não salva e NÃO DEVE enviá-la. O sistema DEVE respeitar os valores padrão definidos pelo backend para campos não recebidos.

O sistema DEVE permitir a identificação de cada produto por um identificador único.

O sistema DEVE validar os campos obrigatórios antes de salvar um produto.

O sistema DEVE alinhar o payload de criação ao contrato do endpoint Xano, sem exigir que o frontend envie o campo `status` quando o backend define o valor padrão `ativo`.

O sistema DEVE permitir que o usuário selecione uma categoria ativa disponível e enviar o `category_id` correspondente no cadastro do produto.

O sistema DEVE informar quando categorias não puderem ser carregadas ou não houver categoria ativa e NÃO DEVE permitir um envio sem categoria válida.

O formulário DEVE enviar somente os inputs confirmados do cadastro atual: `name` (texto), `category_id` (inteiro), `min_stock` (inteiro), `sale_price` (decimal) e `sku` (texto opcional). Descrição, fornecedores, quantidade inicial em estoque, custo de aquisição e custo de embalagem não fazem parte do contrato atual, DEVEM ser identificados como não persistidos e NÃO DEVEM ser enviados nem apresentados como salvos.

O sistema NÃO DEVE armazenar o custo de aquisição diretamente no cadastro principal do produto, pois os custos de aquisição serão registrados nas entradas de estoque.

O sistema MUST confirmar a criação do produto no backend Xano antes de informar que o cadastro foi concluído.

Para o `POST /product` atual, a confirmação DEVE ser baseada no objeto direto do registro retornado como `product` (“As Self”). Se o objeto incluir `id`, esse identificador DEVE ser válido. O sistema NÃO DEVE aceitar resposta vazia, envelope não documentado ou status genérico como confirmação.

#### Cenário: Cadastro de produto válido

- **WHEN** um usuário autorizado preencher os campos suportados com dados válidos e selecionar uma categoria ativa
- **THEN** o sistema DEVE enviar os valores do formulário e o ID real da categoria selecionada para criação do produto
- **AND** o sistema DEVE informar sucesso somente após receber confirmação válida do backend

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

- **WHEN** o formulário exibir descrição ou outros campos que não fazem parte dos inputs do endpoint
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
