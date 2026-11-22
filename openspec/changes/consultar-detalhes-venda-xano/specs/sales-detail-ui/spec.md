## Purpose

Define como usuários abrem e consultam os dados completos de uma venda selecionada na listagem, mantendo os valores financeiros e históricos como retornados pelo Xano.

## ADDED Requirements

### Requirement: Consultar detalhes da venda selecionada

A tela MUST permitir selecionar uma venda da listagem existente e consultar seu detalhe pelo identificador retornado. A consulta MUST usar a sessão ativa e MUST apresentar os dados recebidos sem criar ou presumir campos ausentes.

#### Scenario: Abrir uma venda da listagem

- **WHEN** o usuário selecionar uma venda com identificador válido
- **THEN** a interface MUST consultar e apresentar o detalhe correspondente retornado pelo Xano

#### Scenario: Resposta de detalhe não corresponde à seleção

- **WHEN** o Xano retornar uma resposta inválida, incompleta ou referente a outro identificador
- **THEN** a interface MUST informar que não foi possível confirmar os detalhes e MUST NOT apresentar o conteúdo como se correspondesse à venda selecionada

### Requirement: Apresentar dados da venda, itens e custos retornados

A visualização MUST apresentar os campos existentes em `sale`, os itens retornados em `items` e os custos retornados em `costs`, respeitando os campos disponíveis no contrato. Campos opcionais não retornados DEVEM ser omitidos ou indicados claramente como indisponíveis, nunca preenchidos com valores inventados.

#### Scenario: Exibir detalhes disponíveis

- **WHEN** uma consulta detalhada válida retornar a venda, seus itens e seus custos
- **THEN** a interface MUST apresentar os dados retornados sem adicionar relacionamentos, produtos, descrições ou valores não fornecidos

#### Scenario: Campo opcional ausente

- **WHEN** um campo opcional não estiver presente na resposta
- **THEN** a interface MUST omiti-lo ou indicá-lo como indisponível, sem apresentar zero ou texto fictício como valor recebido

### Requirement: Exibir resumo financeiro do backend sem recálculo

A interface MUST apresentar os valores disponíveis em `financial_summary`, incluindo receita bruta, desconto, receita líquida, CMV total, custos totais, resultado e margem percentual. Os valores DEVEM ser exibidos como retornados pelo backend; a interface MUST NOT recalcular, substituir valores ausentes por zero ou apresentar o resultado como lucro líquido contábil.

#### Scenario: Resumo financeiro completo

- **WHEN** o detalhe retornar os campos do resumo financeiro
- **THEN** a interface MUST exibir os valores retornados sem cálculo ou transformação que altere seu significado

#### Scenario: Campo financeiro indisponível

- **WHEN** um campo financeiro não estiver presente na resposta
- **THEN** a interface MUST indicar indisponibilidade ou omitir o campo, sem inventar um valor

### Requirement: Tratar sessão e falhas na consulta detalhada

A visualização MUST comunicar carregamento, sessão ausente/expirada, permissão insuficiente, venda não encontrada e falha de conexão ou resposta inválida sem apresentar detalhe como sucesso. A seleção da venda e o retorno à listagem DEVEM preservar o estado necessário da consulta anterior.

#### Scenario: Sessão indisponível

- **WHEN** não houver token de sessão ao solicitar os detalhes
- **THEN** a interface MUST informar que é necessário autenticar novamente e MUST NOT tratar a venda como carregada

#### Scenario: Venda inexistente ou acesso negado

- **WHEN** a consulta retornar HTTP 404, 401 ou 403
- **THEN** a interface MUST informar respectivamente que a venda não foi encontrada, que a sessão não foi aceita ou que o perfil não possui permissão

#### Scenario: Retornar à listagem

- **WHEN** o usuário fechar ou sair da visualização detalhada
- **THEN** a interface MUST retornar à listagem preservando os filtros e a página anteriormente ativos
