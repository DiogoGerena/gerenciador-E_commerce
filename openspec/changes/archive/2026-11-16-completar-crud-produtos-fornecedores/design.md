## Context

Consulte `proposal.md` para a motivação e `specs/cadastro-produtos-fornecedores/spec.md` para o comportamento esperado. O cliente roteia produtos, categorias e fornecedores por bases configuráveis; a interface de produtos consulta e cadastra, enquanto a tela de fornecedores usa os dados reais da listagem. Os contratos completos das operações pendentes foram fornecidos na auditoria técnica compartilhada e são a referência para esta implementação.

Além disso, a busca cobriu o cliente, testes, README, specs e snapshot local do workspace Xano. A matriz dos contratos confirmados é:

| Operação | Evidência disponível | Lacuna |
|---|---|---|
| Produto `GET /product` | Parâmetros `name`, `category_id`, `status`; ausência de filtros é omitida | Formato de resposta deve continuar usando os formatos já aceitos pelo cliente |
| Produto `POST /product` | Campos `name`, `sku`, `category_id`, `sale_price`, `min_stock`; resposta direta “As Self” | Nenhuma lacuna observada para o contrato atual |
| Produto `GET /product/{product_id}` | Requer autenticação operacional ou superior; retorna registro completo; inexistente retorna 404 | Nenhuma lacuna |
| Produto `PATCH /product/{product_id}` | Papel Adm; `name`, `sku`, `category_id`, `sale_price`, `min_stock`, `status`; retorna atualizado; null/omitidos preservam valor; erros 400/404 | Nenhuma; descrição, saldo e custo médio são proibidos |
| Produto `PATCH /product/{product_id}/deactivate` | Papel Adm; sem body; idempotente; retorna registro com `status = inativo`; inexistente retorna 404 | Nenhuma |
| Categoria `GET /category` | Função existente de consulta de categorias ativas | Nenhuma integração duplicada necessária |
| Fornecedor `GET /supplier` | Rota/listagem e filtros `name`/`status` presentes no cliente; campos de saída conhecidos incluem `id`, `name`, `cnpj`, `email`, `contact_name` e `phone` | Outros campos/resposta-envelope não devem ser presumidos |
| Fornecedor `GET /supplier/{supplier_id}` | Autenticação operacional; retorna registro completo; inexistente retorna 404 | Nenhuma |
| Fornecedor `POST /supplier` | Papel Adm; `name` obrigatório; contato, CNPJ, email e telefone opcionais; backend define `status = ativo`; 400 para CNPJ duplicado ou email inválido | Nenhuma; validar dígitos do CNPJ localmente |
| Fornecedor `PATCH /supplier/{supplier_id}` | Papel Adm; `name`, contato, CNPJ, email, telefone e status; retorna atualizado; omitidos/null preservam valor; erros 400/404 | Nenhuma |
| Fornecedor `PATCH /supplier/{supplier_id}/deactivate` | Papel Adm; sem body; idempotente; retorna registro com `status = inativo`; inexistente retorna 404 | Nenhuma |

## Goals / Non-Goals

**Goals:**

- Reutilizar o cliente HTTP, autenticação e tratamento de erros existentes.
- Conectar os fluxos de produto e fornecedor às rotas informadas e preservar compatibilidade com consumidores existentes.
- Reutilizar a consulta de categorias ativas.
- Garantir que sucesso dependa da resposta documentada do Xano e que a edição de produto não toque saldo ou custo médio.
- Manter os limites de escopo e separar testes mockados de validação de integração real.

**Non-Goals:**

- Criar ou alterar endpoints, registros ou permissões no Xano.
- Implementar ou simular associações produto-fornecedor enquanto não houver endpoints.
- Definir o mapeamento do perfil `member` ou alterar a política de autorização.
- Modificar operações, cálculos ou endpoints de estoque, entradas, movimentações, CMV ou vendas.
- Comprovar integração real por meio de testes mockados.

## Decisions

1. **Manter uma única camada de chamadas Xano.** As operações novas devem reutilizar `xano_request` e os padrões de validação/erro do cliente, em vez de criar chamadas HTTP paralelas. Isso conserva bearer token, timeout e propagação de erros; uma camada de transporte nova duplicaria comportamento e aumentaria o risco de regressão.

2. **Adicionar configuração própria para a base de fornecedores sem quebrar a URL existente.** Seguir o padrão de `XANO_PRODUCTS_URL` e `XANO_CATEGORIES_URL`, documentando a variável de fornecedores e mantendo a URL atualmente usada como fallback compatível. Não alterar as bases de estoque, entradas ou movimentações nem espalhar URLs de endpoint pelo código.

3. **Enviar apenas parâmetros e campos confirmados.** `GET /product` usa nome, categoria e status; filtros vazios são omitidos. As demais operações usam exatamente os campos e rotas confirmados na auditoria técnica. Edição de produto nunca envia descrição, saldo ou custo médio; desativação é bodyless e lógica.

4. **Preservar respostas documentadas sem expor campos não contratados.** A normalização de fornecedores deve manter os campos documentados retornados, inclusive dados de contato, sem reduzir silenciosamente os dados válidos. A interface apresenta somente campos confirmados para exibição e não serializa automaticamente a resposta inteira em payloads de escrita.

5. **Manter a autorização do backend como autoridade.** Enviar o token de sessão em operações protegidas, apresentar erros 401/403 de forma sanitizada e não reinterpretar perfis. Não equiparar `member` a `aux.ecommerce` nem introduzir uma nova política de visibilidade de ações; a divergência de permissões permanece uma decisão separada.

6. **Separar testes locais de validação real.** Cobrir métodos, parâmetros, respostas, erros e estados de interface com mocks. Não chamar Xano nesta entrega nem relatar mocks como confirmação de integração real.

## Risks / Trade-offs

- **[Divergência entre contrato fornecido e API publicada]** → Cobrir rotas, payloads, respostas e erros com mocks; manter claro que esses testes não validam a configuração ativa do Xano.
- **[Mudança de configuração pode quebrar a entrada de estoque]** → Preservar a assinatura e o comportamento compatível de `listar_fornecedores`, testar os chamadores existentes e manter fallback para a configuração atualmente usada.
- **[Perfil `member` e regras de mutação não alinhados]** → Não alterar o mapeamento nesta mudança; manter backend como autoridade e reportar 401/403 sem sucesso fictício.
- **[Normalização permissiva pode expor dados não destinados à interface]** → Preservar campos de contrato necessários e mapear explicitamente os campos exibidos, sem despejar a resposta completa na tela.
- **[Mock não detecta divergência do Xano publicado]** → Identificar os testes como mockados e deixar qualquer prova ponta a ponta para uma etapa autorizada com ambiente não produtivo.

## Migration Plan

Não há migração de dados. A nova configuração de fornecedor deve ser opcional para instalações existentes, com fallback para a URL atual; a documentação deve explicar a configuração sem valores secretos. Validar regressões da consulta de fornecedores usada pela entrada de estoque. Para rollback, reverter apenas as alterações desta mudança e remover a variável/documentação adicionada, preservando a configuração antiga.
