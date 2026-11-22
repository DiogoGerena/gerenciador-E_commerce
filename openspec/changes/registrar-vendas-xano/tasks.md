## 1. Formulário e payload

- [x] 1.1 Substituir somente o cadastro manual demonstrativo por campos gerais documentados e seleção de produtos reais do catálogo; verificar com AppTest o payload e o envio da data sem conversão.
- [x] 1.2 Implementar inclusão/remoção de vários itens com estado estável e validação de ID do produto, quantidade, preço e desconto; verificar preservação das linhas e bloqueio de payload inválido com AppTest.
- [x] 1.3 Implementar inclusão/remoção de custos globais e validação dos tipos e valores permitidos; verificar payload, custo sem descrição e bloqueio de valores inválidos com AppTest.

## 2. Registro e atualização da listagem

- [x] 2.1 Integrar o envio autenticado a `criar_venda` sem alterar o cliente; testar payload permitido, token ausente, erros HTTP, resposta incompleta e ausência de retry.
- [x] 2.2 Tratar timeout/conexão como inconclusivos sem reenvio e preservar os dados do formulário; verificar estado, mensagem e chamada única com mocks.
- [x] 2.3 Após confirmação válida, apresentar sucesso e valores financeiros retornados sem recálculo, limpar o formulário de modo controlado e atualizar a listagem existente preservando filtros; verificar rerun, paginação adequada e dados usados na renderização com AppTest.

## 3. Validação

- [x] 3.1 Executar testes específicos e regressão `unittest` sem chamadas reais ao Xano, `python -m compileall -q app tests`, `git diff --check` e validação OpenSpec estrita; confirmar que somente o escopo do registro manual foi implementado.

## 4. Idempotência do registro

- [x] 4.1 Aceitar e validar `idempotency_key` UUID v4 em `criar_venda`, enviando-a no nível do objeto da venda e preservando o restante do contrato; cobrir validação, POST e ausência de retry nos testes do cliente.
- [x] 4.2 Associar UUID v4 a fingerprint SHA-256 determinístico do payload efetivamente enviado, reutilizar chave para payload idêntico, emitir chave nova ao mudar o payload e preservar chave/dados em resultado inconclusivo; tratar os quatro códigos de conflito sem declarar sucesso.
- [x] 4.3 Testar geração, reutilização, troca, sucesso, timeout, conexão, respostas incompletas e erros de idempotência com mocks; executar regressão completa sem chamadas reais, compilação, `git diff --check` e validação OpenSpec estrita.
