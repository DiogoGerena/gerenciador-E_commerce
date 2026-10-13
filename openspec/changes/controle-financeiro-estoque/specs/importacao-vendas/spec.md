## Objetivo

Definir os requisitos para importar vendas por arquivos CSV e Excel, validar os dados recebidos e registrar as informações de forma consistente no estoque e no controle financeiro.

## ADDED Requirements
### Requirement: Importação de vendas por arquivo

O sistema DEVE permitir que usuários autorizados importem vendas por arquivos CSV e Excel.

O sistema DEVE permitir identificar o canal de venda e relacionar cada registro aos produtos cadastrados.

O sistema DEVE validar o formato do arquivo antes de iniciar o processamento.

#### Cenário: Importar arquivo válido

- **QUANDO** um usuário autorizado enviar um arquivo CSV ou Excel em formato aceito
- **ENTÃO** o sistema DEVE ler os dados e apresentar uma pré-visualização antes da confirmação da importação

#### Cenário: Enviar arquivo inválido

- **QUANDO** um usuário enviar um arquivo em formato não aceito ou que não possa ser lido
- **ENTÃO** o sistema DEVE rejeitar o arquivo e informar o motivo

### Requirement: Pré-visualização e validação dos dados

O sistema DEVE apresentar os registros identificados no arquivo antes de confirmar a importação.

O sistema DEVE validar os campos necessários para registrar as vendas, incluindo identificação do pedido quando disponível, data, produto, quantidade e preço de venda.

O sistema DEVE identificar linhas com dados ausentes, inválidos ou incompatíveis com os cadastros existentes.

O sistema DEVE informar quais linhas apresentam problemas e os respectivos motivos.

#### Cenário: Encontrar dados inválidos

- **QUANDO** o arquivo possuir linhas com dados obrigatórios ausentes ou inválidos
- **ENTÃO** o sistema DEVE identificar as linhas problemáticas e explicar os erros encontrados antes da confirmação

#### Cenário: Confirmar importação após a pré-visualização

- **QUANDO** o usuário revisar os dados e confirmar a importação
- **ENTÃO** o sistema DEVE processar os registros válidos conforme as regras de importação e apresentar o resultado do processamento

### Requirement: Identificação de pedidos duplicados

O sistema DEVE identificar possíveis pedidos duplicados utilizando o canal de venda e o número do pedido, quando essas informações estiverem disponíveis.

O sistema NÃO DEVE importar novamente um pedido já registrado com a mesma identificação no mesmo canal.

Quando não houver um identificador confiável para verificar duplicidade, o sistema DEVE informar essa limitação ao usuário e aplicar as validações disponíveis.

#### Cenário: Importar pedido já registrado

- **QUANDO** o arquivo contiver um pedido que já esteja registrado para o mesmo canal de venda
- **ENTÃO** o sistema DEVE identificar a duplicidade e impedir que o pedido seja contabilizado novamente

#### Cenário: Arquivo com pedidos novos e duplicados

- **QUANDO** um arquivo possuir pedidos novos e pedidos já registrados
- **ENTÃO** o sistema DEVE distinguir os pedidos novos dos duplicados e informar o resultado da validação antes da confirmação

### Requirement: Consistência do estoque e dos dados financeiros

O sistema DEVE aplicar às vendas importadas as mesmas regras de validação e registro utilizadas nas vendas manuais.

O sistema DEVE calcular o CMV com base no custo unitário considerado no momento de cada venda.

O sistema DEVE atualizar o estoque e os registros financeiros de maneira consistente, sem duplicar movimentações ou valores.

O sistema NÃO DEVE confirmar uma venda que resulte em estoque negativo.

#### Cenário: Importar venda com estoque insuficiente

- **QUANDO** uma venda importada exigir uma quantidade superior ao estoque disponível
- **ENTÃO** o sistema DEVE identificar o problema e impedir que a venda seja confirmada de forma inconsistente

#### Cenário: Falha durante o processamento

- **QUANDO** ocorrer uma falha durante o processamento de uma venda importada
- **ENTÃO** o sistema DEVE impedir que a operação deixe registros financeiros e movimentações de estoque parcialmente aplicados

### Requirement: Relatório de resultado da importação

O sistema DEVE apresentar um resumo do processamento após cada importação.

O resumo DEVE informar a quantidade de pedidos importados, rejeitados e identificados como duplicados.

O sistema DEVE disponibilizar os motivos de rejeição para permitir a correção dos dados.

#### Cenário: Finalizar importação

- **QUANDO** o processamento de um arquivo for concluído
- **ENTÃO** o sistema DE