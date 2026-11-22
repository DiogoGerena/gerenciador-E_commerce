## Purpose

Define o contrato da camada cliente para consumir com segurança as operações de venda já disponibilizadas pelo grupo Sales do Xano, sem transferir cálculos financeiros ou regras de estoque para o frontend.

## ADDED Requirements

### Requirement: Configuração e autenticação do grupo Sales

O cliente MUST direcionar as operações de venda ao grupo Xano `EjdVpi9b`, usando o domínio configurado para a instância no projeto, sem incorporar domínios privados ou credenciais no código. As três operações MUST enviar o token de sessão no cabeçalho Bearer.

#### Scenario: Consumir operação autenticada do grupo Sales

- **QUANDO** o cliente executar uma operação de venda com token de sessão
- **ENTÃO** MUST usar a rota documentada do grupo `EjdVpi9b` e enviar `Authorization: Bearer <token>`

### Requirement: Registro de venda conforme contrato

O cliente MUST permitir registrar vendas por `POST /sale`, validar os campos documentados e enviar somente os campos aceitos pelo contrato: `sales_channel`, `order_number`, `sale_date`, `notes`, `items` e `costs`. O canal MUST ser texto livre não vazio; a venda MUST conter pelo menos um item; cada item MUST conter `product_id`, `quantity` e `unit_sale_price`, com `discount_amount` opcional; `costs` MUST ser enviado como uma lista, inclusive quando vazia; cada custo MUST conter `cost_type`, com `description` opcional e `amount`. Custos MUST representar custos globais da venda. Campos opcionais ausentes ou nulos, exceto `costs`, MUST ser omitidos. Quando informado, `sale_date` MUST ser convertido para timestamp Unix inteiro em milissegundos; timestamps em segundos MUST ser rejeitados. Filtros de data da consulta continuam sendo enviados sem conversão.

O cliente MUST rejeitar IDs de produto inválidos, quantidades menores que um, valores negativos ou não finitos, canais inválidos, tipos de custo não documentados e campos não aceitos. Os tipos de custo aceitos são `embalagem`, `comissao_marketplace`, `impostos`, `frete_saida` e `outros`.

#### Scenario: Enviar venda válida com múltiplos itens e custos

- **QUANDO** os dados contiverem canal livre válido, itens e custos válidos conforme o contrato
- **ENTÃO** o cliente MUST enviar os campos documentados ao endpoint de criação sem adicionar campos de cliente, estoque ou resultados financeiros

#### Scenario: Rejeitar payload de venda inválido antes do envio

- **QUANDO** faltarem itens obrigatórios ou houver campo não aceito, ID inválido, quantidade inferior a um, valor negativo/não finito ou tipo de custo não permitido
- **ENTÃO** o cliente MUST rejeitar os dados sem executar a requisição HTTP

#### Scenario: Omitir campos opcionais ausentes

- **QUANDO** campos opcionais da venda, item ou custo não forem informados
- **ENTÃO** o cliente MUST NOT enviá-los como `null` nem substituir datas por valores convertidos

### Requirement: Confirmação do registro de venda

O cliente MUST considerar uma criação confirmada somente quando a resposta incluir um registro `sale` válido, arrays `items` e `costs`, e `financial_summary` com os campos `gross_amount`, `discount_amount`, `net_revenue`, `total_cmv`, `total_costs`, `result` e `profit_margin_percent` válidos. O cliente MUST NOT preencher campos financeiros ausentes com zero nem recalcular valores financeiros.

#### Scenario: Confirmar resposta completa da criação

- **QUANDO** `POST /sale` retornar as estruturas e campos financeiros obrigatórios em tipos válidos
- **ENTÃO** o cliente MUST retornar os dados do backend sem recalcular o resumo

#### Scenario: Tratar resposta incompleta da criação como inconclusiva

- **QUANDO** a resposta de sucesso estiver ausente, inválida ou sem qualquer estrutura/campo obrigatório da confirmação
- **ENTÃO** o cliente MUST informar que não obteve confirmação e MUST NOT representar a criação como bem-sucedida

### Requirement: Listagem paginada de vendas

O cliente MUST consultar `GET /sale` com somente os filtros documentados `sales_channel`, `order_number`, `status`, `start_date`, `end_date`, `page` e `per_page`. No workspace Xano, `sales_channel` é `text?` e o filtro usa `==?`, permitindo sua ausência; a versão publicada ainda retorna HTTP 400 `Missing param: sales_channel` até que a alteração passe por Review & Publish. Enquanto essa publicação externa estiver pendente, a interface e o cliente MUST evitar consultas sem um canal informado, sem presumir um padrão. A página padrão MUST ser 1; `per_page` MUST ter padrão 20 e aceitar valores de 1 a 100; status MUST ser `registrada` ou `cancelada`. Datas MUST ser encaminhadas sem conversão; enquanto o formato contratual não for confirmado, a ordenação entre datas informadas MUST ser validada pelo Xano.

A resposta DEVE conter `itemsReceived`, `curPage`, `nextPage`, `prevPage`, `offset`, `itemsTotal`, `pageTotal` e `items`, com envelope e lista em tipos válidos. O cliente MUST NOT presumir que os cabeçalhos da lista contenham itens, custos ou CMV.

#### Scenario: Listar vendas com filtros e paginação válidos

- **QUANDO** for informado um `sales_channel` não vazio, com filtros e limites de paginação válidos
- **ENTÃO** o cliente MUST encaminhar somente os filtros preenchidos e retornar o envelope paginado validado

#### Scenario: Omitir sales_channel obrigatório

- **QUANDO** `sales_channel` estiver ausente ou vazio
- **ENTÃO** o cliente MUST rejeitar a consulta antes de realizar a requisição HTTP

#### Scenario: Rejeitar filtros ou paginação inválidos

- **QUANDO** página, limite ou status estiverem fora dos valores permitidos
- **ENTÃO** o cliente MUST rejeitar os parâmetros antes da requisição HTTP

#### Scenario: Tratar envelope paginado incompleto como inválido

- **QUANDO** a resposta de listagem não contiver o envelope esperado ou `items` não for uma lista
- **ENTÃO** o cliente MUST gerar erro de validação, sem tratar a resposta como uma listagem válida

### Requirement: Consulta detalhada de venda

O cliente MUST consultar `GET /sale/{id}` para um identificador inteiro válido e aceitar a resposta somente quando contiver `sale`, `items`, `costs` e `financial_summary` com os mesmos campos financeiros obrigatórios definidos para a confirmação da criação. A resposta MUST preservar os valores retornados pelo backend, sem preencher ausências ou recalcular CMV, resultado ou margem.

#### Scenario: Consultar detalhe completo

- **QUANDO** um ID válido corresponder a uma resposta detalhada completa
- **ENTÃO** o cliente MUST retornar a venda, itens, custos e resumo financeiro recebidos do Xano

#### Scenario: Rejeitar ID ou detalhe inválido

- **QUANDO** o ID não for inteiro positivo ou a resposta detalhada estiver incompleta
- **ENTÃO** o cliente MUST rejeitar a operação sem apresentar detalhe incompleto como válido

### Requirement: Tratamento de falhas de integração de vendas

O cliente MUST propagar falhas HTTP e de transporte sem convertê-las em sucesso. Timeout ou falha de conexão durante a criação MUST ser sinalizados como resultado inconclusivo, pois não comprovam que o Xano deixou de registrar a venda. O cliente MUST NOT realizar retry automático de `POST /sale`.

#### Scenario: Falha HTTP durante operação de venda

- **QUANDO** o Xano retornar uma resposta HTTP de erro
- **ENTÃO** o cliente MUST expor a falha sem apresentar confirmação de operação

#### Scenario: Timeout ou desconexão durante criação

- **QUANDO** a conexão ou o timeout interromper `POST /sale`
- **ENTÃO** o cliente MUST sinalizar resultado inconclusivo e MUST NOT repetir automaticamente a requisição
