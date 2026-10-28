# cadastro-produtos-fornecedores Specification

## Purpose
TBD - created by archiving change controle-financeiro-estoque. Update Purpose after archive.

## Requirements

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

### Requirement: Consulta e edição de produtos

O sistema DEVE permitir que usuários autorizados consultem produtos cadastrados, pesquisem por nome e filtrem produtos por categoria e situação.

O sistema DEVE permitir a edição dos dados cadastrais de um produto existente.

O sistema DEVE preservar o histórico de movimentações de estoque e os registros financeiros relacionados ao produto quando seus dados cadastrais forem editados.

#### Cenário: Pesquisa de produto

- **QUANDO** um usuário pesquisar um produto pelo nome
- **ENTÃO** o sistema DEVE apresentar os produtos correspondentes à pesquisa

#### Cenário: Edição de produto

- **QUANDO** um usuário autorizado alterar os dados de um produto existente com informações válidas
- **ENTÃO** o sistema DEVE salvar as alterações sem apagar o histórico de estoque e financeiro relacionado ao produto

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

O sistema DEVE permitir cadastrar, consultar e editar fornecedores.

O cadastro DEVE permitir informar nome do fornecedor e, opcionalmente, dados de contato, como telefone, e-mail e observações.

O sistema DEVE permitir identificar se um fornecedor está ativo ou inativo.

#### Cenário: Cadastro de fornecedor

- **QUANDO** um usuário autorizado cadastrar um fornecedor com nome preenchido
- **ENTÃO** o sistema DEVE salvar o fornecedor para utilização nos registros de entrada de estoque

#### Cenário: Inativação de fornecedor

- **QUANDO** um usuário inativar um fornecedor que possua entradas de estoque registradas
- **ENTÃO** o sistema DEVE preservar o fornecedor e seu histórico de entradas e NÃO DEVE permitir que ele seja selecionado em novas entradas de estoque

### Requirement: Relacionamento entre produtos e fornecedores

O sistema DEVE permitir que um produto esteja relacionado a vários fornecedores.

O sistema DEVE permitir que um fornecedor esteja relacionado a vários produtos.

O relacionamento DEVE permitir registrar, para cada vínculo, informações opcionais como código do produto no fornecedor e observações.

O sistema DEVE impedir a criação de vínculos duplicados entre o mesmo produto e o mesmo fornecedor.

#### Cenário: Vincular fornecedor a produto

- **QUANDO** um usuário autorizado relacionar um produto a um fornecedor ativo
- **ENTÃO** o sistema DEVE registrar o vínculo entre eles

#### Cenário: Vincular vários fornecedores ao mesmo produto

- **QUANDO** um usuário autorizado relacionar um produto a mais de um fornecedor ativo
- **ENTÃO** o sistema DEVE manter todos os vínculos válidos para consulta e utilização nas entradas de estoque

#### Cenário: Impedir vínculo duplicado

- **QUANDO** um usuário tentar criar novamente um vínculo que já existe entre o mesmo produto e fornecedor
- **ENTÃO** o sistema NÃO DEVE duplicar o vínculo e DEVE informar que a relação já está cadastrada
