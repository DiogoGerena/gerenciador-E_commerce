## Why

O ERP já possui infraestrutura comum de autenticação e requisições ao Xano, mas ainda não oferece métodos de cliente para registrar e consultar vendas. A camada precisa consumir o grupo Sales com validação explícita para evitar confirmar gravações cuja resposta não comprove o resultado.

## What Changes

- Adicionar configuração e roteamento do cliente para o grupo Sales `EjdVpi9b`, usando o domínio configurado no projeto.
- Implementar registro, listagem paginada com filtros e consulta detalhada de vendas.
- Validar payloads e respostas conforme o contrato documentado, sem enviar campos extras nem calcular valores financeiros.
- Tratar erros HTTP, timeout, conexão e respostas inválidas/incompletas sem retry automático de criação.
- Adicionar testes automatizados com mocks para as operações do cliente.

## Capabilities

### New Capabilities
- `sales-xano-client`: integração do cliente Python com as operações documentadas de vendas no grupo Sales.

### Modified Capabilities

## Impact

- Código: `app/xano_client.py`.
- Testes: novo arquivo `tests/test_xano_sales.py`.
- API: grupo Xano `EjdVpi9b`, rotas `POST /sale`, `GET /sale` e `GET /sale/{id}`.
- Interface, navegação, importação, clientes, cancelamento e demais operações de venda ficam fora desta etapa.
