## 1. Listagem e estado da tela

- [x] 1.1 Substituir somente a tabela demonstrativa da função `render_vendas` por consulta autenticada a `listar_vendas`; validar token ausente, carregamento, lista real, vazia e mensagens para HTTP 401/403 e falha de conexão com AppTest e mocks.
- [x] 1.2 Implementar filtros documentados de canal, número do pedido, status e timestamps sem conversão; verificar parâmetros enviados e reinício para página 1 ao submeter filtros novos.
- [x] 1.3 Implementar navegação paginada usando metadados retornados, preservar filtros/página em `st.session_state` e comprovar com AppTest que a navegação envia página correta e mantém os filtros.
- [x] 1.4 Renderizar os campos existentes nos cabeçalhos retornados sem campos fictícios ou cálculos; verificar com resposta de mock que a tabela não apresenta cliente nem valores financeiros inventados.

## 2. Validação

- [x] 2.1 Executar os novos testes de listagem e a regressão pertinente, `python -m compileall -q app tests`, `git diff --check` e validação estrita OpenSpec; confirmar que somente a listagem de vendas foi alterada e nenhuma chamada real ao Xano ocorreu.
