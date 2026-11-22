## 1. Contrato e cliente

- [x] 1.1 Confirmar, usando a referência contratual fornecida e sem requisições reais, os campos de registros/metadados da resposta e o estado publicado dos filtros opcionais; documentar qualquer discrepância sem criar parâmetros artificiais. O contrato informado admite `items` e `movements`, mantém os filtros como opcionais e não especifica metadados para determinar o fim da paginação.
- [x] 1.2 Ajustar a validação e normalização do cliente para aceitar os formatos de lista documentados, omitir filtros ausentes/em branco e limitar `per_page` a 100; verificar formatos e query params com mocks.

## 2. Interface e navegação

- [x] 2.1 Adicionar navegação explícita anterior/próxima, preservando filtros e tamanho da página e reiniciando na página 1 ao mudar filtros; verificar a página e os parâmetros enviados com Streamlit AppTest.
- [x] 2.2 Apresentar somente os registros da página corrente, contagem e estado vazio/erro apropriados, mantendo diagnóstico HTTP sanitizado; verificar com respostas mockadas e sem dados demonstrativos.

## 3. Validação

- [x] 3.1 Cobrir respostas com `movements` e `items`, parâmetros opcionais omitidos e fornecidos, limites de página, navegação, filtros alterados e erros 400 com token redigido; executar os testes direcionados sem chamadas reais ao Xano.
- [x] 3.2 Executar a suíte completa de testes e `git diff --check`; validar a mudança OpenSpec em modo estrito e confirmar que nenhuma configuração ou dado do Xano foi alterado.
