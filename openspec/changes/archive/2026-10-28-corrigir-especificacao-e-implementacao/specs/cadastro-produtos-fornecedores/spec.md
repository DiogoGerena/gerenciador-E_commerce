## MODIFIED Requirements

### Requirement: Cadastro de produtos

O sistema DEVE permitir que usuários autorizados cadastrem produtos com nome, descrição, categoria, quantidade mínima de estoque e situação do cadastro.

O sistema DEVE permitir a identificação de cada produto por um identificador único.

O sistema DEVE validar os campos obrigatórios antes de salvar um produto.

O sistema DEVE alinhar o payload de criação ao contrato do endpoint Xano, sem exigir que o frontend envie o campo `status` quando o backend define o valor padrão `ativo`.

O sistema DEVE permitir que o usuário selecione a categoria pelo nome a partir das categorias ativas disponíveis e envie o `category_id` correspondente no cadastro do produto.

O sistema NÃO DEVE armazenar o custo de aquisição diretamente no cadastro principal do produto, pois os custos de aquisição serão registrados nas entradas de estoque.

O sistema MUST confirmar a criação do produto no backend Xano antes de informar que o cadastro foi concluído.

#### Cenário: Cadastro de produto válido

- **WHEN** um usuário autorizado preencher os campos obrigatórios de um produto com dados válidos e solicitar o cadastro
- **THEN** o sistema DEVE salvar o produto e disponibilizá-lo para consulta

#### Cenário: Cadastro com campos obrigatórios ausentes

- **WHEN** um usuário tentar cadastrar um produto sem preencher um ou mais campos obrigatórios
- **THEN** o sistema DEVE informar quais campos precisam ser preenchidos e NÃO DEVE salvar o cadastro incompleto

#### Cenário: Cadastro com quantidade mínima inválida

- **WHEN** um usuário informar uma quantidade mínima de estoque negativa
- **THEN** o sistema DEVE rejeitar o valor e informar que a quantidade mínima não pode ser negativa

#### Cenário: Cadastro confirmado pelo backend

- **WHEN** um usuário enviar um formulário válido e o Xano confirmar a criação do produto
- **THEN** o sistema DEVE informar que o cadastro foi concluído
- **AND** o produto cadastrado DEVE poder ser consultado novamente no backend

#### Cenário: Falha ao cadastrar produto

- **WHEN** um usuário enviar o formulário e o backend rejeitar a solicitação ou ocorrer uma falha de comunicação
- **THEN** o sistema DEVE informar que o cadastro não foi confirmado
- **AND** o sistema NÃO DEVE apresentar a operação como concluída

#### Cenário: Resposta sem confirmação de criação

- **WHEN** o backend retornar uma resposta que não permita confirmar a criação do produto
- **THEN** o sistema NÃO DEVE informar sucesso sem verificar o resultado da operação