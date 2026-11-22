## Context

Consulte `proposal.md` e `specs/sales-xano-client/spec.md` para motivação e contrato. `app/xano_client.py` já centraliza configuração, roteamento por grupo, autenticação Bearer, timeout HTTP, status HTTP e decodificação de respostas. A configuração existente obtém o domínio por `XANO_API_URL` e aceita URLs específicas de grupos via ambiente ou `st.secrets`.

## Goals / Non-Goals

**Goals:**
- Adicionar o roteamento Sales ao cliente HTTP já existente e preservar os roteamentos atuais.
- Implementar as três operações do contrato com validação própria e testes mockados.
- Distinguir falha HTTP de resultado inconclusivo em uma criação interrompida por timeout ou conexão.

**Non-Goals:**
- Alterar telas, navegação, papéis, estoque ou cálculos financeiros.
- Criar operações que não existem no contrato ou fazer chamadas ao ambiente Xano.

## Decisions

- **Reutilizar a infraestrutura HTTP existente.** Adicionar a configuração/seleção do grupo Sales ao roteamento de `xano_client.py` e usar os helpers comuns para Bearer, timeout, status e decodificação. Isso evita um segundo cliente e reduz o risco de regressão em outros grupos.
- **Configurar somente a rota do grupo, não um domínio novo.** Aceitar `XANO_SALES_URL` por ambiente ou `st.secrets` seguindo o padrão dos grupos existentes; quando ausente, derivar a origem (esquema e host) da `XANO_API_URL` configurada e anexar o identificador confirmado `api:EjdVpi9b`. Não codificar domínio. Se não houver origem configurada, falhar explicitamente.
- **Validar entradas por listas permitidas.** Construir o payload a partir dos campos documentados, validar cada item/custo e omitir opcionais ausentes ou nulos. Não repassar chaves extras nem realizar cálculos de estoque ou financeiros. Converter `sale_date` para timestamp Unix inteiro em milissegundos; os filtros `start_date` e `end_date` continuam sendo encaminhados como texto.
- **Validar estruturas de resposta antes de retornar.** Validadores específicos para criação, listagem e detalhe verificam o envelope, os tipos e os campos financeiros obrigatórios; dados retornados são preservados. Resposta de sucesso incompleta gera erro de confirmação, não um valor padrão.
- **Não repetir a criação.** O helper HTTP não implementa retry. Timeout ou falha de conexão no POST será traduzido em erro explícito de resultado inconclusivo; erros HTTP permanecem erros HTTP e nenhuma resposta incompleta será tratada como confirmação.
- **Testar sem rede.** Um novo `tests/test_xano_sales.py` usa mocks em `requests.request` para provar URL, método, token, parâmetros/payload, validações, respostas e exceções. A suíte existente será executada como regressão.

## Risks / Trade-offs

- [O Xano pode ter concluído uma venda antes de a conexão cair] → O cliente sinaliza resultado inconclusivo, não repete o POST e orienta reconciliação fora desta etapa.
- [O domínio de Sales pode diferir do grupo padrão] → `XANO_SALES_URL` permite configuração explícita; o fallback usa somente a origem já configurada e o identificador Sales confirmado.
- [O formato de datas não está documentado] → Não converter nem inferir unidade; encaminhar os valores sem alteração e deixar a validação de ordenação ao Xano até o contrato de formato ser confirmado.

## Migration Plan

Não há migração de dados. Configurar `XANO_SALES_URL` somente se o grupo Sales não compartilhar a origem configurada em `XANO_API_URL`. A implementação pode ser revertida removendo os métodos e o roteamento Sales sem alterar operações ou dados existentes.
