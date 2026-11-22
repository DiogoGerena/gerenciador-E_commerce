## 1. Consulta e apresentação dos detalhes

- [x] 1.1 Adicionar seleção de venda na listagem e consulta sob demanda do detalhe; verificar ID/token enviados e carregamento com AppTest e mock de `consultar_venda`.
- [x] 1.2 Apresentar os dados de venda, itens e custos presentes na resposta; testar campos opcionais ausentes sem valores inventados.
- [x] 1.3 Apresentar o resumo financeiro retornado sem recálculo; testar valores iguais aos do backend e campos ausentes como indisponíveis/omitidos.
- [x] 1.4 Tratar sessão ausente, HTTP 401/403/404, falhas de conexão e resposta inválida; testar que falhas não renderizam detalhe como sucesso.
- [x] 1.5 Preservar a listagem ao abrir e fechar detalhes, incluindo filtros, página e resultado carregado; verificar o estado com AppTest.

## 2. Validação

- [x] 2.1 Executar os testes mockados de detalhes e regressão pertinente, `python -m compileall -q app tests`, `git diff --check` e validação estrita OpenSpec; confirmar que somente a visualização detalhada foi implementada e não houve chamada real ao Xano.
