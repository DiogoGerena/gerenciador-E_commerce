
## ADDED Requirements

### Requirement: Permissões do perfil Adm

O sistema DEVE permitir que usuários com o perfil `Adm` gerenciem os usuários, seus perfis de acesso e as configurações gerais do sistema.

O sistema DEVE permitir que o perfil `Adm` consulte e execute as operações autorizadas de cadastro, estoque, vendas, importação e controle financeiro.

#### Scenario: Administrar usuários

- **QUANDO** um usuário com perfil `Adm` acessar a área de gerenciamento de usuários
- **ENTÃO** o sistema DEVE permitir consultar usuários, cadastrar novos usuários, editar seus dados e ativar ou inativar suas contas conforme as regras de segurança

### Requirement: Permissões do perfil aux.ecommerce

O sistema DEVE permitir que usuários com o perfil `aux.ecommerce` executem as atividades operacionais autorizadas, incluindo consultar e manter dados de produtos, categorias e fornecedores, registrar movimentações de estoque e realizar importações de vendas.

O perfil `aux.ecommerce` NÃO DEVE ter permissão para gerenciar usuários, alterar perfis de acesso ou modificar configurações restritas à administração.

#### Scenario: Acesso a atividades operacionais

- **QUANDO** um usuário com perfil `aux.ecommerce` acessar uma funcionalidade operacional para a qual possui permissão
- **ENTÃO** o sistema DEVE permitir a execução da operação conforme as regras do módulo correspondente

#### Scenario: Tentativa de administrar usuários

- **QUANDO** um usuário com perfil `aux.ecommerce` tentar acessar uma operação de gerenciamento de usuários ou de alteração de permissões
- **ENTÃO** o sistema DEVE bloquear a operação e informar que o usuário não possui autorização

### Requirement: Proteção das operações no backend

O sistema DEVE validar a autenticação e as permissões do usuário no backend antes de executar operações protegidas.

O sistema NÃO DEVE depender apenas da interface para impedir acessos não autorizados.

#### Scenario: Requisição sem autenticação

- **QUANDO** uma requisição tentar executar uma operação protegida sem uma sessão ou credencial válida
- **ENTÃO** o backend DEVE rejeitar a requisição

#### Scenario: Requisição sem permissão

- **QUANDO** um usuário autenticado tentar executar uma operação que não esteja autorizada para seu perfil
- **ENTÃO** o backend DEVE rejeitar a operação sem realizar alterações nos dados
