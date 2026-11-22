## Purpose

Define o registro manual de vendas na interface usando o contrato existente do grupo Sales, com validação anterior ao envio e confirmação explícita do backend antes de apresentar sucesso.

## ADDED Requirements

### Requirement: Informar os dados gerais da venda

A interface MUST permitir informar um canal de venda como texto livre não vazio, um número do pedido opcional e uma data opcional no formato aceito pelo contrato. O campo `notes` MAY ser informado como texto opcional por ser previsto no contrato. A interface MUST encaminhar a data sem conversão e MUST NOT incluir dados de cliente ou campos não documentados.

#### Scenario: Informar campos gerais válidos

- **WHEN** o usuário informar um canal não vazio e os demais campos opcionais compatíveis com o contrato
- **THEN** a interface MUST enviar somente os campos gerais documentados, omitindo opcionais vazios ou não informados

#### Scenario: Canal ausente

- **WHEN** o usuário tentar enviar a venda sem canal ou com canal vazio
- **THEN** a interface MUST apresentar validação e MUST NOT chamar o endpoint de criação

#### Scenario: Informar data da venda

- **WHEN** o usuário preencher uma data no formato contratual aceito pelo backend
- **THEN** a interface MUST encaminhar o valor sem conversão ou substituição

### Requirement: Gerenciar múltiplos itens da venda

A interface MUST permitir incluir e remover itens e MUST exigir pelo menos um item antes do envio. Cada item MUST conter um produto identificado por `product_id`, quantidade inteira positiva e `unit_sale_price` numérico não negativo e finito. O desconto por item MUST ser opcional e, quando informado, MUST ser numérico não negativo e finito. A interface MUST NOT calcular CMV, resultado, margem, descontos agregados ou valores derivados.

#### Scenario: Registrar vários itens válidos

- **WHEN** o usuário informar um ou mais itens com produto, quantidade e preço unitário válidos
- **THEN** a interface MUST enviar cada item com os campos correspondentes e preservar os valores informados

#### Scenario: Remover item mantendo ao menos um

- **WHEN** o usuário remover um item de um formulário que ainda contém outros itens
- **THEN** a interface MUST atualizar os itens que serão enviados sem alterar os valores dos itens restantes

#### Scenario: Formulário sem item ou com item inválido

- **WHEN** não houver itens ou um item tiver ID inválido, quantidade não positiva/não inteira, preço inválido ou desconto inválido
- **THEN** a interface MUST explicar a validação e MUST NOT chamar o endpoint de criação

### Requirement: Gerenciar custos adicionais globais

A interface MUST permitir adicionar e remover custos globais opcionais da venda. Cada custo MUST utilizar um `cost_type` permitido (`embalagem`, `comissao_marketplace`, `impostos`, `frete_saida` ou `outros`) e um `amount` numérico não negativo e finito; `description` MUST ser opcional. A interface MUST NOT associar esses custos a itens nem calcular rateios.

#### Scenario: Enviar custos globais válidos

- **WHEN** o usuário informar custos com tipo permitido, valor válido e descrição opcional
- **THEN** a interface MUST enviar os custos na lista global `costs` sem associá-los a um item

#### Scenario: Custo inválido

- **WHEN** um custo tiver tipo não permitido, valor ausente, negativo ou não finito
- **THEN** a interface MUST informar a validação e MUST NOT enviar a venda

#### Scenario: Venda sem custos adicionais

- **WHEN** o usuário não adicionar custos globais
- **THEN** a interface MUST omitir `costs` ou enviá-lo vazio conforme o comportamento aceito pelo cliente, sem inventar custos

### Requirement: Confirmar registro pelo backend

A interface MUST enviar os dados validados usando a sessão autenticada e MUST apresentar sucesso somente após receber a resposta completa e válida definida pelo cliente. Uma resposta HTTP com erro ou resposta de sucesso incompleta MUST NOT ser apresentada como registro confirmado. A interface MUST NOT executar retry automático ou permitir repetir automaticamente uma criação de resultado inconclusivo.

#### Scenario: Registro confirmado

- **WHEN** o backend confirmar a venda com resposta válida
- **THEN** a interface MUST apresentar confirmação e os valores financeiros retornados, se exibidos, sem recalcular ou substituir valores

#### Scenario: Erro HTTP ou resposta incompleta

- **WHEN** a criação falhar por erro HTTP ou resposta incompleta/inválida
- **THEN** a interface MUST informar que não houve confirmação válida e MUST NOT apresentar sucesso

#### Scenario: Timeout ou falha de conexão

- **WHEN** ocorrer timeout ou falha de conexão durante o registro
- **THEN** a interface MUST informar que o resultado é inconclusivo, MUST NOT repetir a criação e MUST orientar a consultar as vendas antes de uma nova tentativa

#### Scenario: Evitar envio duplicado

- **WHEN** o envio estiver em andamento
- **THEN** a interface MUST impedir novos envios do mesmo formulário até que a operação seja concluída ou marcada como inconclusiva

### Requirement: Reutilizar chave de idempotência por operação lógica

A interface MUST gerar uma chave UUID v4 para uma operação de registro e mantê-la em `st.session_state` associada a uma identificação determinística do payload validado enviado ao Xano. A identificação MUST excluir a chave, preservar a ordem e repetição dos itens e custos, preservar a distinção entre campos omitidos e explicitamente enviados e MUST NOT normalizar valores monetários ou quantidades. Reruns com payload inalterado MUST reutilizar a mesma chave. Se não existir operação não resolvida, qualquer mudança no payload enviado MUST iniciar uma nova operação com chave nova. Enquanto existir operação em andamento ou inconclusiva, mudanças nos campos editáveis MUST ser tratadas apenas como rascunho e MUST NOT substituir a chave ou o payload da operação pendente, nem permitir uma nova venda. O cliente MUST enviar a chave como campo do objeto da venda e MUST NOT colocá-la em itens ou custos.

#### Scenario: Repetir operação com payload idêntico

- **WHEN** a mesma operação for submetida novamente com payload idêntico, inclusive após timeout ou perda de conexão
- **THEN** o cliente MUST enviar a mesma chave UUID v4, preservar o payload da operação e MUST NOT repetir a chamada automaticamente

#### Scenario: Alterar payload sem operação pendente

- **WHEN** qualquer campo efetivamente enviado ao Xano for alterado, adicionado ou omitido e não existir operação não resolvida
- **THEN** a interface MUST identificar a diferença e associar uma nova chave UUID v4 ao novo payload

#### Scenario: Editar formulário enquanto existe operação pendente

- **WHEN** o usuário alterar campos enquanto uma operação anterior estiver em andamento ou inconclusiva
- **THEN** a interface MUST preservar o payload e a chave originais, MUST NOT enviar outra venda e MUST informar que as alterações são apenas um rascunho

#### Scenario: Operação confirmada

- **WHEN** a resposta HTTP e o envelope completo da venda forem validados
- **THEN** a interface MUST limpar a chave e a identificação da operação concluída e MUST atualizar a listagem pelo fluxo existente

### Requirement: Classificar conflitos de idempotência

A interface MUST inspecionar o campo `message` de erros HTTP e distinguir `IDEMPOTENCY_LOCKED`, `IDEMPOTENCY_CONCURRENT_REQUEST`, `IDEMPOTENCY_LOCK_FAILED` e `IDEMPOTENCY_PAYLOAD_MISMATCH` de erros de autenticação ou validação comuns. Todos esses códigos MUST preservar a chave e o payload original e manter a operação sem confirmação bloqueando novas vendas. Nenhum deles MUST ser apresentado como sucesso. `IDEMPOTENCY_PAYLOAD_MISMATCH` MUST ser mantido para reconciliação administrativa e MUST NOT liberar nova operação apenas porque o formulário foi alterado.

#### Scenario: Backend informa chave ocupada ou conflito concorrente

- **WHEN** a resposta HTTP indicar `IDEMPOTENCY_LOCKED`, `IDEMPOTENCY_CONCURRENT_REQUEST` ou `IDEMPOTENCY_LOCK_FAILED`
- **THEN** a interface MUST mostrar uma mensagem específica, preservar a chave original e não executar retry automático

#### Scenario: Backend informa divergência entre payload e chave

- **WHEN** a resposta HTTP indicar `IDEMPOTENCY_PAYLOAD_MISMATCH`
- **THEN** a interface MUST preservar a operação original, impedir qualquer nova venda, explicar a inconsistência e MUST NOT apresentar confirmação

### Requirement: Bloquear novas vendas até reconciliar operação inconclusiva

A interface MUST representar explicitamente os estados `new`, `in_progress`, `inconclusive` e `completed`. Ao iniciar o POST, MUST persistir na sessão o snapshot do payload validado junto com a chave e fingerprint. Timeout, perda de conexão, resposta incompleta e qualquer erro HTTP, inclusive 400 e 500, MUST deixar a operação inconclusiva até uma confirmação segura. Alterar o formulário MUST NOT alterar esse snapshot ou liberar nova chave. A interface MAY oferecer uma ação manual de reconciliação que reenvie exclusivamente o snapshot original com a mesma chave; MUST NOT fazer retry automático. A operação pendente só pode ser liberada após resposta completa e válida da reconciliação ou confirmação equivalente. Sem mecanismo seguro que prove ausência de gravação, a interface MUST manter o cadastro bloqueado para análise administrativa.

#### Scenario: Reconciliar a mesma operação

- **WHEN** o usuário solicitar explicitamente a reconciliação de uma operação pendente
- **THEN** a interface MUST enviar o payload original e a chave original uma única vez e MUST permanecer bloqueada se não receber confirmação completa e válida

#### Scenario: Tentar iniciar outra venda antes da reconciliação

- **WHEN** existir operação pendente e o usuário editar o formulário ou tentar iniciar outro cadastro
- **THEN** a interface MUST NOT enviar outro payload nem gerar/substituir a chave pendente

#### Scenario: Liberar nova operação após confirmação segura

- **WHEN** a reconciliação confirmar a operação original com resposta completa e válida
- **THEN** a interface MUST marcar a operação como concluída, limpar somente o estado idempotente concluído e permitir que a próxima venda gere uma chave nova

### Requirement: Atualizar a listagem após confirmação

A interface MUST atualizar a listagem existente somente após uma resposta de criação válida. A atualização MUST reutilizar o fluxo de consulta já existente, preservar os filtros ativos e ajustar a página para que a consulta atualizada seja válida. Erro ou resultado inconclusivo MUST NOT provocar mensagem de sucesso nem atualização apresentada como confirmação.

#### Scenario: Atualizar após venda confirmada

- **WHEN** o cliente confirmar o registro
- **THEN** a interface MUST atualizar os dados da listagem usando os filtros ativos e apresentar a confirmação após a atualização visual

#### Scenario: Manter listagem após falha

- **WHEN** o registro falhar ou ficar inconclusivo
- **THEN** a interface MUST manter os dados da listagem sem apresentá-los como atualizados por uma venda confirmada
