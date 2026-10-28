## Contexto

A proposta desta alteração está descrita em `proposal.md`. A especificação modificada é `cadastro-produtos-fornecedores`, especialmente o requisito de cadastro de produtos.

O projeto utiliza Streamlit na interface e Xano como backend. O cadastro deve validar os dados, enviar a solicitação ao backend e distinguir uma criação confirmada de uma operação rejeitada, inconclusiva ou interrompida por falha de comunicação.

Antes de alterar o comportamento do sistema, será necessário revisar o código existente, os testes disponíveis e o contrato real do endpoint de criação no Xano.

## Objetivos e não objetivos

**Objetivos:**

- Manter a implementação alinhada à especificação do cadastro de produtos.
- Verificar como a interface valida os dados e interpreta as respostas do Xano.
- Garantir que mensagens de sucesso correspondam a uma criação confirmada.
- Identificar quais comportamentos já possuem testes automatizados e quais precisam de testes adicionais.
- Preservar os requisitos existentes que não fazem parte desta alteração.

**Não objetivos:**

- Implementar todo o sistema de controle financeiro e estoque nesta alteração.
- Criar novos endpoints no Xano sem antes verificar o contrato existente.
- Substituir a arquitetura atual de Streamlit e Xano.
- Considerar testes com respostas simuladas como prova de funcionamento da integração real.
- Alterar requisitos de outras funcionalidades sem justificativa e rastreabilidade.

## Decisões técnicas

### 1. Revisar a implementação existente antes de modificá-la

A análise deve começar pelo fluxo de cadastro de produtos, pelas funções responsáveis pela comunicação HTTP com o Xano e pelos testes existentes.

**Justificativa:** reutilizar a implementação atual reduz alterações desnecessárias e permite identificar precisamente o que está implementado e o que ainda precisa ser corrigido.

**Alternativa considerada:** reescrever o cadastro integralmente. Essa alternativa não será adotada sem evidências de que a implementação atual não pode ser aproveitada.

### 2. Utilizar o contrato real do Xano como referência

O método HTTP, o caminho do endpoint, os campos enviados, a autenticação e o formato da resposta devem ser conferidos na implementação existente e no backend Xano.

A aplicação não deve presumir que uma resposta representa a criação do produto sem verificar o resultado conforme esse contrato.

**Justificativa:** respostas HTTP e formatos de retorno variam conforme a configuração do endpoint. Não é seguro inventar campos de confirmação ou assumir que qualquer resposta bem-sucedida contém um produto criado.

**Alternativa considerada:** definir um formato de resposta presumido apenas para fazer o formulário funcionar. Essa alternativa não será adotada sem confirmação do contrato.

### 3. Separar validação, comunicação com o backend e apresentação do resultado

A validação dos campos deve ocorrer antes do envio. A comunicação com o Xano deve tratar respostas de erro e falhas de conexão. A interface deve apresentar o resultado correspondente ao que foi efetivamente confirmado.

Se não for possível confirmar a criação, a aplicação não deve apresentar a operação como concluída.

**Justificativa:** essa separação facilita a manutenção, os testes e a identificação da origem de cada falha.

**Alternativa considerada:** concentrar todas as responsabilidades no formulário. Essa abordagem dificulta a verificação isolada do comportamento e não será priorizada.

### 4. Diferenciar testes automatizados de testes de integração

Os testes automatizados devem verificar a validação dos campos, o tratamento das respostas e a apresentação correta de sucesso ou falha, utilizando respostas simuladas quando apropriado.

A integração real deve ser verificada separadamente, com configuração válida e acesso autorizado ao Xano, confirmando que o produto pode ser consultado após a criação.

**Justificativa:** testes simulados verificam o comportamento do código, mas não comprovam que o endpoint real está configurado corretamente ou persiste os dados.

**Alternativa considerada:** considerar os testes simulados suficientes para aprovar a integração. Essa alternativa não será adotada.

## Riscos e compensações

- **Contrato do endpoint desconhecido ou incompleto** → Conferir a configuração real do Xano antes de alterar a integração. Se não for possível confirmá-la, registrar a limitação e não declarar a integração validada.
- **Falso positivo de cadastro** → Exigir evidência compatível com o contrato do backend antes de apresentar sucesso.
- **Falha de conexão ou resposta inesperada** → Tratar a operação como não confirmada e apresentar uma mensagem adequada ao usuário.
- **Testes aprovados sem persistência real** → Registrar separadamente os resultados dos testes automatizados e dos testes de integração.
- **Alteração acidental de requisitos existentes** → Preservar os cenários e requisitos anteriores que não forem explicitamente modificados.

## Plano de migração e reversão

Não está prevista migração de banco de dados nesta alteração.

1. Revisar o código, os testes e o contrato do endpoint existente.
2. Ajustar a especificação para representar os critérios de cadastro e confirmação.
3. Implementar apenas as correções justificadas pela análise.
4. Executar os testes automatizados e registrar os resultados.
5. Quando houver acesso ao ambiente de teste do Xano, verificar a criação e a consulta posterior de um produto.
6. Revisar as alterações antes de integrá-las à branch principal.

Se uma alteração causar regressão, reverter somente as mudanças de implementação correspondentes, preservando os dados existentes e a documentação histórica. A reversão deve ser validada por testes.

## Questões em aberto

Nenhuma decisão arquitetural nova é necessária neste momento. O contrato real do endpoint e a disponibilidade de um ambiente de teste são informações a confirmar durante a inspeção técnica; não devem ser presumidos.