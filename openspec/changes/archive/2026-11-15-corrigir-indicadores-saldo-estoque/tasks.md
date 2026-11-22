## 1. Normalização e classificação do estoque

- [x] 1.1 Ajustar a normalização dos campos `stock_quantity`, `average_cost` e `min_stock` para preservar zero e distinguir indisponível de inválido; verificar com testes unitários sem requisições HTTP.
- [x] 1.2 Calcular situação do produto somente com quantidade e estoque mínimo válidos, mantendo as regras atuais para zero, estoque baixo e normal; verificar casos de limite e dados desconhecidos.

## 2. Indicadores, tabela e gráficos

- [x] 2.1 Atualizar indicadores para mostrar totais de quantidade e valor apenas quando os campos necessários forem completos, indicando produtos indisponíveis ou inválidos; verificar cenários completos e mistos.
- [x] 2.2 Ajustar tabela e gráficos para não converter valores desconhecidos em zero e apresentar mensagens de incompletude ou indisponibilidade quando não houver dados plotáveis; verificar a renderização com Streamlit AppTest.
- [x] 2.3 Preservar o estado vazio para lista sem produtos e confirmar que nenhuma informação demonstrativa aparece na página de estoque; verificar lista vazia via mock.

## 3. Validação da mudança

- [x] 3.1 Cobrir quantidades, custos e mínimos ausentes, nulos, inválidos e zerados, além de dados completos, vazios, mistos, limites de classificação, quantidade negativa e conversão numérica excedente em `tests/test_erp_stock_page.py`; executar os testes direcionados e confirmar que nenhuma chamada real ao Xano ocorre.
- [x] 3.2 Executar `python -B -m unittest discover -s tests -p 'test_*.py' -v` e `git diff --check`; confirmar a aprovação da suíte e ausência de erros de whitespace sem alterar arquivos fora de `app/erp_modules.py` e dos testes de estoque.
