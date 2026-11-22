## Why

A tela atual ainda apresenta um cadastro manual demonstrativo, embora o cliente Xano já tenha `criar_venda` com validação do contrato e tratamento de resultado inconclusivo. Esta mudança permitirá registrar vendas reais sem duplicar regras financeiras ou de estoque no frontend.

## What Changes

- Substituir o formulário demonstrativo de cadastro manual por um formulário de venda conectado ao Xano.
- Permitir informar canal livre, número do pedido opcional, data conforme o formato aceito pelo contrato e demais campos gerais documentados.
- Permitir adicionar e remover vários itens com produto, quantidade, preço unitário e desconto opcional por item.
- Permitir adicionar e remover custos globais documentados.
- Validar os dados antes do envio e apresentar estados de sucesso confirmado, erro e resultado inconclusivo sem retry automático.
- Atualizar a listagem existente somente após confirmação válida do backend, preservando filtros e retornando à página inicial da consulta quando necessário.
- Criar testes de interface com mocks; não realizar chamadas reais ao Xano.

## Capabilities

### New Capabilities
- `sales-registration-ui`: formulário manual e registro autenticado de vendas usando o contrato existente.

### Modified Capabilities

## Impact

- Interface: `app/erp_modules.py`, na área de cadastro da tela existente de vendas.
- Testes: testes mockados de interface para validação, payload, respostas, erros e atualização da listagem.
- Cliente: uso de `criar_venda(token, dados)` já disponível em `app/xano_client.py`, sem alteração do contrato.
- OpenSpec: nova capability para o comportamento de registro manual; mudanças anteriores de integração, listagem e detalhe permanecem independentes.
