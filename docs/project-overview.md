# Visão geral do projeto CodBar

## 1. Objetivo

Desenvolver um sistema para gerenciar o estoque e acompanhar os resultados financeiros de uma operação de e-commerce, centralizando informações sobre produtos, fornecedores, entradas, vendas e custos.

## 2. Arquitetura do sistema

- **Frontend:** Streamlit, responsável pela interface e pela interação com os usuários.
- **Backend:** Xano, responsável pela autenticação, permissões, regras de negócio, banco de dados e APIs.
- **Versionamento:** Git e GitHub, para controle de alterações e colaboração.
- **Especificações:** OpenSpec, para documentar requisitos e orientar a implementação.

## 3. Perfis de usuário

- **Adm:** perfil administrativo, com permissões de gerenciamento definidas nas especificações.
- **aux.ecommerce:** perfil operacional, com acesso às funcionalidades autorizadas para suas atividades.

As permissões devem ser verificadas no backend, mesmo quando a interface ocultar funcionalidades não autorizadas.

## 4. Funcionalidades previstas

1. Cadastro de produtos, categorias e fornecedores.
2. Registro de entradas de mercadorias e custos de aquisição.
3. Controle de saldo e histórico de movimentações de estoque.
4. Registro manual e importação de vendas por arquivos CSV e Excel.
5. Cálculo do custo médio ponderado e do Custo das Mercadorias Vendidas (CMV).
6. Registro dos custos relacionados às vendas.
7. Cálculo de receita, resultado após custos e margem.
8. Dashboard e relatórios financeiros e de estoque.
9. Autenticação e controle de permissões.

## 5. Regras de negócio importantes

- O custo de aquisição deve considerar o preço de compra, o frete de entrada e outros custos aplicáveis.
- O estoque deve manter um histórico rastreável de suas movimentações.
- Os itens vendidos devem preservar o custo unitário histórico utilizado no cálculo do CMV.
- Os custos compartilhados de uma venda devem ser distribuídos proporcionalmente ao valor de venda dos itens.
- O sistema deve impedir baixas duplicadas e saídas que resultem em estoque negativo.
- As importações devem permitir validação e pré-visualização antes da confirmação.
- O resultado financeiro apresentado não deve ser confundido com o lucro líquido contábil.

## 6. Limites do escopo inicial

A primeira versão não prevê integração automática com APIs de marketplaces nem processamento de pagamentos. O registro manual e a importação de vendas serão os meios previstos para inserir os dados das operações.

## 7. Documentação de referência

Os requisitos funcionais estão documentados em:

`openspec/changes/controle-financeiro-estoque/`

O arquivo `tasks.md` contém as tarefas planejadas para a implementação.

## 8. Estado atual

O projeto está na fase de revisão das especificações e preparação da documentação e da estrutura de desenvolvimento. A implementação deverá avançar progressivamente, com testes e validações a cada etapa.

## 9. Segurança

Credenciais, tokens e outros segredos não devem ser armazenados diretamente no código-fonte nem enviados ao GitHub. A aplicação deverá utilizar variáveis de ambiente ou mecanismos seguros de configuração.