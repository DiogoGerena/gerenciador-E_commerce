## Why

A consulta de movimentações aceita filtros opcionais e paginação, mas o cliente valida apenas a chave `movements` e a tela não oferece navegação explícita entre páginas nem apresenta metadados de paginação. Além disso, os HTTP 400 anteriormente registrados para `product_id` e `movement_type` não foram reproduzidos contra a versão publicada do Xano, portanto a compatibilidade do contrato continua incerta.

## What Changes

- Manter a omissão de filtros opcionais ausentes ou em branco e encaminhar os nomes de parâmetros documentados sem filtros artificiais.
- Normalizar respostas paginadas do histórico que contenham `items` e/ou `movements`, preservando e interpretando somente os metadados de paginação efetivamente reconhecidos.
- Fornecer navegação explícita de página e limites de tamanho de página compatíveis com o contrato documentado, sem enviar a consulta antes da ação explícita do usuário.
- Manter erros HTTP diagnósticos e sanitizados, sem expor tokens, e acrescentar testes mockados para respostas, filtros, limites e navegação.
- Registrar a incerteza do contrato publicado: erros HTTP 400 previamente registrados não comprovam que os parâmetros sejam obrigatórios, e não devem justificar filtros artificiais.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `movimentacoes-cmv`: definir consulta paginada do histórico de movimentações, interpretação das listas e navegação explícita entre páginas.

## Impact

- Afeta `app/xano_client.py`, `app/erp_modules.py` e testes de movimentações.
- Usa o grupo já configurado por `XANO_STOCK_MOVEMENTS_URL` e a rota GET `/stock-movement`; não altera endpoint, dados ou configuração do Xano.
- Não inclui chamadas reais ao Xano nos testes. A versão publicada do endpoint e a semântica exata dos metadados de paginação permanecem pendentes de confirmação por fonte contratual autorizada.
