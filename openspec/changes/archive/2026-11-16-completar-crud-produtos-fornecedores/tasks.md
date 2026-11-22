## 1. Confirmar contratos e configuração

- [x] 1.1 Reunir evidências de métodos, rotas, parâmetros, campos e respostas disponíveis; registrar lacunas por operação em `design.md`, sem inferir contratos
- [x] 1.2 Configurar a base de fornecedores com fallback compatível e documentar as variáveis; verificar com testes sem alterar URLs de estoque, entradas ou movimentações

## 2. Cliente de produtos

- [x] 2.1 Completar a listagem de produtos com filtros documentados e validar omissão de filtros ausentes, respostas e erros com testes mockados
- [x] 2.2 Implementar consulta individual de produto com confirmação do registro retornado e propagação de 404; cobrir resposta inválida e falha de conexão com testes mockados
- [x] 2.3 Implementar edição somente dos campos cadastrais aceitos e inativação lógica sem body; validar campos omitidos/null, confirmação da resposta e ausência de `stock_quantity`, `average_cost` e `description` no payload

## 3. Cliente de fornecedores

- [x] 3.1 Preservar campos documentados retornados pela listagem, incluindo contato e telefone, sem quebrar a consulta usada por entradas; verificar resposta vazia, inválida e compatibilidade com testes existentes
- [x] 3.2 Completar listagem/pesquisa com critérios confirmados e verificar parâmetros, respostas vazias/malformadas e erros com testes mockados
- [x] 3.3 Implementar consulta individual, cadastro, edição e inativação lógica de fornecedores conforme contratos confirmados; cobrir campos aceitos, omissão de vazios/null, duplicidade de CNPJ, e-mail inválido e confirmação do backend
- [x] 3.4 Implementar e testar função local independente de validação de formato/dígitos do CNPJ, sem substituir a validação de duplicidade do backend
- [x] 3.5 Integrar a validação local de CNPJ ao cadastro e edição de fornecedor; omitir CNPJ vazio e manter a duplicidade sob validação autoritativa do Xano

## 4. Interfaces

- [x] 4.1 Conectar filtros de listagem de produtos à consulta Xano e validar estados vazio/erro e reutilização da consulta de categorias em testes de interface
- [x] 4.2 Conectar detalhe, edição e inativação lógica de produtos à API; exigir confirmação explícita, exibir sucesso somente após resposta válida e atualizar a consulta
- [x] 4.3 Substituir a listagem demonstrativa de fornecedores por consulta real e filtros confirmados; validar campos de contato e estados vazio/erro
- [x] 4.4 Conectar cadastro, detalhe, edição e inativação lógica de fornecedores; reutilizar validação de CNPJ, confirmação explícita e atualização da listagem
- [x] 4.5 Confirmar que não há vínculos produto-fornecedor simulados e que política de perfis e mapeamento de `member` permanecem inalterados; nenhuma associação ou alteração de permissões foi incluída

## 5. Validação

- [x] 5.1 Executar testes específicos de produtos, fornecedores e entrada de estoque e a suíte completa; identificar mocks como testes locais, não como integração real
- [x] 5.2 Executar verificação sintática, validação estrita desta mudança e `git diff --check`; registrar eventuais falhas preexistentes da spec principal sem fazer limpeza fora do escopo

## 6. Correções da revisão final

- [x] 6.1 Validar a estrutura obrigatória das respostas de consulta, edição e inativação de produto sem restringir respostas de outras entidades; cobrir registros incompletos, tipos incorretos, ID divergente e campos opcionais
- [x] 6.2 Atualizar visualmente as listagens após edição/inativação de produto e cadastro/edição/inativação de fornecedor com refresh único, sucesso transitório e preservação de filtros; cobrir estados visíveis de sucesso e erro
