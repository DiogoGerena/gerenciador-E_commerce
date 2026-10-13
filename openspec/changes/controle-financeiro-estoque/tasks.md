## 1. Preparação do projeto

- [ ] 1.1 Revisar as especificações, o documento de decisões técnicas e os requisitos do projeto, verificando se as funcionalidades previstas estão documentadas.
- [ ] 1.2 Organizar a estrutura dos arquivos do projeto e confirmar que os arquivos necessários estão versionados no GitHub.
- [ ] 1.3 Definir e documentar as variáveis de configuração necessárias para conectar o Streamlit ao Xano, verificando que credenciais não sejam armazenadas diretamente no código.

## 2. Modelagem do banco de dados no Xano

- [ ] 2.1 Criar a estrutura de usuários utilizando a autenticação do Xano e verificar se os usuários podem ser identificados e associados aos seus respectivos perfis.
- [ ] 2.2 Criar a tabela de categorias e verificar se é possível cadastrar, consultar, editar e desativar categorias.
- [ ] 2.3 Criar a tabela de fornecedores e verificar o cadastro, a consulta, a edição e a desativação de fornecedores.
- [ ] 2.4 Criar a tabela de produtos com os campos de identificação, categoria, estoque mínimo, preço de venda e situação, verificando os tipos de dados e os relacionamentos.
- [ ] 2.5 Criar o relacionamento entre produtos e fornecedores, verificando se um produto pode possuir vários fornecedores e se um fornecedor pode atender vários produtos.
- [ ] 2.6 Criar a estrutura de entradas de estoque, registrando quantidade, custo de aquisição, frete de entrada, outros custos de aquisição, fornecedor e data de entrada, verificando se os valores ficam associados ao registro correto.
- [ ] 2.7 Criar as tabelas de vendas e itens de venda, verificando se uma venda pode conter vários itens e se cada item mantém seu preço e custo unitário histórico.
- [ ] 2.8 Criar a estrutura de movimentações de estoque para entradas, saídas por venda, ajustes, perdas, avarias e devoluções, verificando se cada movimentação possui identificação, tipo, quantidade e referência válida.
- [ ] 2.9 Definir os relacionamentos, campos obrigatórios e regras de integridade, verificando se os registros não podem referenciar entidades inexistentes.

## 3. Autenticação e permissões

- [ ] 3.1 Configurar a autenticação de usuários no Xano e verificar o acesso com credenciais válidas e inválidas.
- [ ] 3.2 Implementar a diferenciação entre os perfis Adm e aux.ecommerce, verificando se o perfil de cada usuário é reconhecido pelo backend.
- [ ] 3.3 Proteger os endpoints de acordo com as permissões de cada perfil, verificando que operações não autorizadas sejam bloqueadas mesmo quando solicitadas diretamente à API.
- [ ] 3.4 Implementar a recuperação adequada de sessão e o tratamento de falhas de autenticação, verificando o comportamento após o encerramento ou a expiração da sessão.

## 4. Cadastro e gerenciamento de produtos

- [ ] 4.1 Implementar os endpoints de cadastro, consulta, edição e desativação de produtos, verificando cada operação por meio de requisições à API.
- [ ] 4.2 Implementar validações de campos obrigatórios, valores numéricos, quantidades e relacionamentos, verificando que dados inválidos sejam rejeitados.
- [ ] 4.3 Implementar o cadastro e a consulta dos vínculos entre produtos e fornecedores, verificando a associação correta entre os registros.
- [ ] 4.4 Implementar consultas e filtros de produtos por nome, categoria e situação do estoque, verificando se os resultados correspondem aos critérios informados.

## 5. Controle e valorização do estoque

- [ ] 5.1 Implementar o registro de entradas de mercadorias com quantidade e custos de aquisição, verificando se os dados ficam associados ao produto e ao fornecedor corretos.
- [ ] 5.2 Implementar o cálculo do custo médio ponderado, considerando o valor do estoque existente e o custo total da nova entrada, verificando o resultado com exemplos numéricos.
- [ ] 5.3 Implementar as movimentações de entrada, saída, ajuste, perda, avaria e devolução, verificando se cada operação registra seu histórico e atualiza o saldo corretamente.
- [ ] 5.4 Implementar a validação de saldo antes das saídas, verificando que operações que deixariam o estoque negativo sejam bloqueadas, exceto se uma regra específica for aprovada posteriormente.
- [ ] 5.5 Implementar proteções contra atualizações simultâneas inconsistentes e baixas duplicadas, verificando o comportamento de operações concorrentes com os mecanismos disponíveis no Xano.
- [ ] 5.6 Implementar a identificação de produtos com estoque igual ou inferior ao mínimo definido, verificando os resultados com produtos em diferentes níveis de estoque.
- [ ] 5.7 Implementar consultas do histórico de movimentações por produto e período, verificando se cada registro apresenta tipo, quantidade, data e referência correspondentes.

## 6. Registro de vendas e cálculos financeiros

- [ ] 6.1 Implementar o registro manual de vendas com canal de venda, número do pedido quando disponível, data, valores e custos associados, verificando a persistência dos dados.
- [ ] 6.2 Implementar o registro dos itens de cada venda, incluindo produto, quantidade, preço unitário, descontos aplicáveis e custo unitário histórico, verificando se os valores ficam preservados após novas entradas de estoque.
- [ ] 6.3 Implementar o cálculo do CMV a partir das quantidades vendidas e dos custos unitários históricos, verificando o resultado com casos de teste conhecidos.
- [ ] 6.4 Implementar o registro dos custos de venda, incluindo embalagem, comissão do marketplace, impostos, frete de saída e outros custos, verificando se cada custo é contabilizado corretamente.
- [ ] 6.5 Implementar a distribuição proporcional dos custos compartilhados da venda entre os itens, de acordo com o valor de venda de cada item, verificando se a soma das parcelas corresponde ao custo original.
- [ ] 6.6 Implementar o cálculo da receita após descontos, do CMV, dos custos de venda, do resultado após custos e da margem, verificando os resultados com exemplos numéricos e tratando vendas sem receita positiva.
- [ ] 6.7 Implementar a prevenção de registros duplicados de vendas e de baixas repetidas de estoque, verificando o comportamento ao tentar registrar o mesmo pedido mais de uma vez.
- [ ] 6.8 Implementar consultas financeiras por período, produto e canal de venda, verificando se os totais apresentados correspondem aos registros armazenados.

## 7. Importação de vendas por arquivos

- [ ] 7.1 Implementar o recebimento de arquivos CSV e Excel, verificando se os formatos suportados são reconhecidos e se arquivos inválidos geram mensagens compreensíveis.
- [ ] 7.2 Implementar o mapeamento das colunas dos arquivos para os campos internos de venda e itens, verificando se os dados são interpretados corretamente.
- [ ] 7.3 Implementar a validação das linhas importadas, verificando campos obrigatórios, tipos de dados, quantidades, valores e referências a produtos.
- [ ] 7.4 Implementar a pré-visualização dos dados e dos erros antes da confirmação, verificando se o usuário consegue identificar registros válidos e inválidos.
- [ ] 7.5 Implementar a identificação de possíveis pedidos duplicados utilizando o canal de venda e o número do pedido quando disponíveis, verificando que a mesma venda não seja processada novamente.
- [ ] 7.6 Implementar a confirmação da importação e o relatório de resultados, verificando a quantidade de registros importados, rejeitados e identificados como duplicados.
- [ ] 7.7 Testar a importação com arquivos válidos, vazios, incompletos, com valores inválidos e com pedidos duplicados, verificando que os erros não provoquem alterações indevidas no estoque ou nos valores financeiros.

## 8. Desenvolvimento da interface no Streamlit

- [ ] 8.1 Configurar a estrutura inicial da aplicação Streamlit, verificando se ela inicia corretamente no ambiente de desenvolvimento.
- [ ] 8.2 Implementar as telas de login e controle de sessão, verificando o acesso e a saída de usuários autenticados.
- [ ] 8.3 Implementar a navegação principal e o controle visual de funcionalidades por perfil, verificando se cada usuário visualiza as opções correspondentes às suas permissões.
- [ ] 8.4 Implementar as telas de cadastro e consulta de produtos, categorias e fornecedores, verificando a integração das operações com as APIs do Xano.
- [ ] 8.5 Implementar as telas de entradas de mercadorias e histórico de movimentações, verificando se os dados exibidos correspondem às respostas do backend.
- [ ] 8.6 Implementar as telas de registro manual de vendas e consulta financeira, verificando se os dados são enviados e recuperados corretamente.
- [ ] 8.7 Implementar a tela de importação de arquivos com pré-visualização, mensagens de validação e confirmação, verificando o fluxo completo de importação.
- [ ] 8.8 Implementar o tratamento de carregamento, erros de API, respostas vazias e falhas de conexão, verificando se a interface apresenta mensagens compreensíveis.
- [ ] 8.9 Aplicar um padrão visual consistente, com tabelas, formulários, indicadores e navegação, verificando a legibilidade e o uso adequado em diferentes tamanhos de tela.

## 9. Painel financeiro e indicadores

- [ ] 9.1 Implementar os indicadores de produtos cadastrados, quantidade em estoque, valor do estoque e produtos com estoque baixo, verificando os valores com os dados do Xano.
- [ ] 9.2 Implementar os indicadores de receita, CMV, custos de venda, resultado após custos e margem, verificando os cálculos para o período selecionado.
- [ ] 9.3 Implementar gráficos e tabelas para análise por período, produto e canal de venda, verificando se os filtros atualizam corretamente os dados apresentados.
- [ ] 9.4 Verificar se os indicadores e gráficos utilizam as mesmas regras de cálculo dos registros financeiros e não contabilizam custos compartilhados mais de uma vez.

## 10. Integração, testes e validação

- [ ] 10.1 Validar a comunicação entre Streamlit e Xano, verificando operações de leitura, criação, atualização e tratamento de erros por meio das APIs.
- [ ] 10.2 Executar testes de ponta a ponta para cadastro de produto, entrada de estoque, registro de venda, baixa de estoque e atualização dos indicadores, verificando a consistência dos dados.
- [ ] 10.3 Testar os cálculos de custo médio, CMV, distribuição de custos compartilhados e margem com valores esperados previamente definidos.
- [ ] 10.4 Testar os perfis Adm e aux.ecommerce nas operações permitidas e proibidas, verificando que o backend aplique as permissões corretamente.
- [ ] 10.5 Testar cenários de falha, incluindo importações inválidas, pedidos duplicados, estoque insuficiente e indisponibilidade da API, verificando que não sejam geradas alterações indevidas.
- [ ] 10.6 Corrigir os problemas encontrados nos testes e executá-los novamente, verificando que as correções não prejudiquem funcionalidades existentes.
- [ ] 10.7 Documentar a configuração, as funcionalidades implementadas, os procedimentos de execução e os resultados dos testes no README, verificando se outro integrante consegue seguir as instruções.
- [ ] 10.8 Preparar a aplicação para demonstração, verificando o funcionamento do fluxo principal com dados de teste e sem exposição de credenciais.
