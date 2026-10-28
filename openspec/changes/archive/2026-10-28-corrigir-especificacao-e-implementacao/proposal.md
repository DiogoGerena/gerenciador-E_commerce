## Why

Esta alteração preserva e corrige a documentação e a implementação do cadastro de produtos para refletirem o contrato real do backend Xano, sem assumir que qualquer resposta HTTP bem-sucedida representa confirmação de criação.

O principal motivo foi alinhar a lógica de cadastro ao comportamento confirmado do sistema: validar campos obrigatórios, rejeitar quantidade mínima negativa, não exigir `status` no payload do produto porque o backend define `ativo` por padrão e garantir que a interface só informe sucesso após uma confirmação compatível da criação no Xano.

Também foi necessário manter os cenários e requisitos existentes, incluindo falhas de comunicação, rejeições do backend e respostas inconclusivas, sem declarar validação de persistência real no Xano para a descrição do produto enquanto os testes de integração real permanecem pendentes.

## What Changes

- Ajustou a descrição do contrato do payload de cadastro para refletir que o backend define `status = "ativo"` por padrão e que o frontend não precisa enviar esse campo.
- Manteve os requisitos e cenários relevantes do cadastro de produtos, incluindo campos obrigatórios, quantidade mínima inválida, confirmação do backend, falha de comunicação e resposta sem confirmação.
- Preservou a regra de que a interface não deve apresentar sucesso sem evidência compatível de criação confirmada pelo Xano.
- Mantém a documentação coerente com as evidências disponíveis e registra que a validação real do Xano para persistência de `description` e testes 4.1/4.2 continuam pendentes.
- Não altera endpoints do Xano nem declara a persistência real da descrição como validada.