## 1. Configuração e roteamento

- [x] 1.1 Adicionar configuração/roteamento do grupo Sales usando `XANO_SALES_URL` quando definido ou a origem configurada de `XANO_API_URL` com `api:EjdVpi9b`; verificar URL, token Bearer e preservação dos roteamentos existentes com testes mockados.

## 2. Operações e validação de payloads

- [x] 2.1 Implementar `criar_venda` para `POST /sale`, validar campos permitidos, itens, custos, valores e omissão de opcionais; verificar payload e rejeições antes de HTTP em `tests/test_xano_sales.py`.
- [x] 2.2 Implementar `listar_vendas` para `GET /sale`, filtros e paginação documentados; validar status, limites e envelope paginado, verificando parâmetros e respostas com mocks.
- [x] 2.3 Implementar `consultar_venda` para `GET /sale/{id}`, validar ID e resposta detalhada/financeira sem preencher ausências; verificar casos válidos e incompletos com mocks.

## 3. Falhas e validação final

- [x] 3.1 Tratar erros HTTP, JSON inválido, timeout e conexão; verificar que timeout/conexão no POST são inconclusivos e que não há retry automático com testes mockados.
- [x] 3.2 Executar testes específicos e suíte completa `unittest`, `python -m compileall app tests`, `git diff --check` e validação estrita OpenSpec; confirmar que a mudança permanece ativa e que não houve chamadas reais ao Xano.
