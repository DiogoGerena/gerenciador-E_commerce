# CodBar — Controle Financeiro e Estoque para E-commerce

## Objetivo

O CodBar é um projeto acadêmico para apoiar o controle de produtos, estoque e informações financeiras de operações de e-commerce. A aplicação atual usa Streamlit como interface e o Xano como backend configurável.

## Tecnologias

- **Python** para a lógica da aplicação e integração HTTP.
- **Streamlit** para a interface web.
- **Xano** como backend de autenticação, dados e endpoints.
- **Git** para controle de versão.
- **OpenSpec** para especificações e acompanhamento das tarefas.

## Estado do projeto

O desenvolvimento é incremental. Os itens abaixo distinguem implementação local de integração confirmada no backend.

### Implementado localmente e coberto por testes automatizados

- Cliente Xano com configuração por variáveis de ambiente ou `st.secrets`, separando URLs de autenticação e recursos.
- Fluxo de login que obtém o token e consulta `/auth/me`; normalização local dos perfis `Adm` e `aux.ecommerce`.
- Sessão autenticada na interface e ação de logout local.
- Pesquisa de produtos por nome, usando o endpoint de recursos `GET /product`.
- Formulário de cadastro integrado ao contrato atual de `POST /product`: envia `name`, `sku`, `category_id`, `sale_price` e `min_stock`. Como não há evidência conclusiva de que o endpoint publicado persista descrição, ela não é enviada nem apresentada como parte do cadastro. Fornecedores, quantidade inicial, custo de aquisição e custo de embalagem também não são aceitos pelo endpoint e não são enviados.
- Função `criar_produto()` que envia JSON para `POST /product` com o token Bearer da sessão. Os testes usam mocks e não criam registros reais.
- Consulta individual, edição cadastral e inativação lógica de produtos integradas aos contratos de `GET /product/{product_id}`, `PATCH /product/{product_id}` e `PATCH /product/{product_id}/deactivate`. A edição não envia descrição, saldo ou custo médio.
- Consulta, cadastro, edição e inativação lógica de fornecedores integradas ao grupo `/api:-ryuPWna`; o CNPJ é validado localmente e duplicidade/e-mail inválido continuam sujeitos à validação do Xano.
- Tratamento local de erros HTTP e conexão, com proteção para não exibir tokens ou credenciais.
- Integração mockada da seção de estoque: visão geral, entradas paginadas, kardex, ajustes, perdas/avarias e devoluções.
- Integração mockada do módulo de vendas: registro com UUID v4, histórico paginado, filtros e detalhes.
- Preservação do payload e da chave em operações de venda inconclusivas, sem geração automática de nova chave.
- Operações administrativas de estoque são ocultadas para perfis operacionais; o backend continua sendo a autoridade das permissões.

Os testes utilizam mocks: cobrem os contratos e fluxos locais, mas não comprovam que a API publicada no ambiente atual do Xano esteja compatível.

### Pendências e limitações conhecidas

- **Confirmação de criação:** `POST /product` retorna o registro criado diretamente como `product` (“As Self”). O cliente só aceita um objeto direto compatível com o registro de produto; se houver `id`, ele também precisa ser um identificador válido. Os testes locais usam mocks e não comprovam a criação no backend.
- **Validação ponta a ponta:** login válido, consulta real de `/auth/me`, criação e consulta do produto criado dependem de credenciais autorizadas e do contrato ativo no Xano. Credenciais não são fornecidas neste README.
- **Validação real de estoque:** os endpoints de estoque foram integrados conforme os contratos fornecidos, mas dependem de homologação autorizada no Xano.
- **Devolução de cliente:** a interface usa `reference_id` para identificar a venda original e não inventa `sale_item_id`; a relação exata do item vendido deve ser validada no endpoint real.
- **Validação real de vendas:** os mocks cobrem o cliente e a interface, mas `POST /sale`, `GET /sale` e `GET /sale/{id}` dependem de homologação autorizada no Xano.
- **Dashboard financeiro:** os indicadores são consultados em tempo real por `GET /sale/metrics`, com filtros de canal, status e período. A disponibilidade ponta a ponta depende da publicação desse endpoint no Xano; enquanto estiver indisponível, a interface apresenta o erro sem substituir os dados por valores zerados. Não há gráficos históricos, pois o endpoint agregado não fornece séries temporais.
- **Integração real:** a compatibilidade das operações de produtos e fornecedores com o workspace Xano ativo ainda não foi validada ponta a ponta.
- **Relacionamento produto-fornecedor:** não há endpoints para persistir associações; a funcionalidade permanece pendente e não é simulada.
- **Outros recursos de negócio:** entradas e movimentações de estoque, vendas, cálculos financeiros e dashboards seguem o estado de suas mudanças OpenSpec específicas.
- **Marketplaces:** integração automática não está implementada.
- **Contrato de listagem:** conforme configuração do Xano inspecionada para `GET /product`, a busca usa `name includes input:name`; `category_id` e `status` são condições adicionais. A interface atual pesquisa pelo nome e não promete listagem global.
- O formulário de cadastro respeita os inputs confirmados do endpoint: `name` (texto), `sku` (texto opcional), `category_id` (inteiro), `sale_price` (decimal) e `min_stock` (inteiro). O Xano exige papel `Adm`, categoria ativa e SKU único quando informado. O formato “As Self” foi confirmado, mas a criação ponta a ponta ainda não foi executada neste ambiente.
- O escopo e as tarefas do CRUD estão em [`openspec/changes/completar-crud-produtos-fornecedores/tasks.md`](openspec/changes/completar-crud-produtos-fornecedores/tasks.md); a mudança `sugestao-inteligente-compras` é independente.

## Pré-requisitos

- Windows com PowerShell.
- Python 3 instalado e disponível pelo comando `py` ou `python`.
- Acesso autorizado ao workspace Xano para usar a aplicação com backend.

As dependências da aplicação estão declaradas em `requirements.txt`.

## Configuração do Xano

O cliente reconhece estas configurações:

- `XANO_API_URL`: base padrão/fallback.
- `XANO_AUTH_URL`: base para `POST /auth/login` e `GET /auth/me`; se omitida, usa `XANO_API_URL`.
- `XANO_RESOURCES_URL`: base para endpoints de negócio, como `/product`; se omitida, usa `XANO_API_URL`.
- `XANO_CATEGORIES_URL`: base para endpoints de categorias.
- `XANO_PRODUCTS_URL`: base para endpoints de produtos.
- `XANO_SUPPLIERS_URL`: base para endpoints de fornecedores.
- `XANO_STOCK_ENTRIES_URL`: base para endpoints de entradas de estoque.
- `XANO_STOCK_MOVEMENTS_URL`: base para endpoints de movimentações de estoque.
- `XANO_SALES_URL`: base para endpoints de vendas.
- `XANO_API_TOKEN`: token opcional de configuração. O fluxo de login usa o token retornado pelo endpoint e o envia como Bearer nas chamadas autenticadas.

Não coloque senhas, tokens ou URLs privadas em arquivos versionados. `.env.example` contém placeholders. O cliente carrega automaticamente o `.env` da raiz do projeto, independentemente do diretório de execução, sem sobrescrever variáveis já presentes no ambiente. O processo do Streamlit e os testes usam a mesma configuração centralizada em `app/xano_client.py`.

### Opção A: Streamlit secrets

Crie `.streamlit/secrets.toml` localmente, substituindo os placeholders pelas URLs do seu workspace Xano:

```toml
XANO_API_URL = "https://SEU-DOMINIO.xano.io/api:GRUPO_PADRAO"
XANO_AUTH_URL = "https://SEU-DOMINIO.xano.io/api:GRUPO_AUTH"
XANO_RESOURCES_URL = "https://SEU-DOMINIO.xano.io/api:GRUPO_RECURSOS"
XANO_SALES_URL = "https://SEU-DOMINIO.xano.io/api:EjdVpi9b"
XANO_CATEGORIES_URL = "https://SEU-DOMINIO.xano.io/api:pi5tdncF"
XANO_PRODUCTS_URL = "https://SEU-DOMINIO.xano.io/api:4FsHXYfS"
XANO_SUPPLIERS_URL = "https://SEU-DOMINIO.xano.io/api:-ryuPWna"
XANO_STOCK_MOVEMENTS_URL = "https://SEU-DOMINIO.xano.io/api:GRUPO_MOVIMENTACOES"
XANO_API_TOKEN = ""
```

O arquivo `.streamlit/secrets.toml` está ignorado pelo Git. Não compartilhe nem versione credenciais reais.

### Opção B: variáveis de ambiente no PowerShell

Defina os valores no terminal em que executará o Streamlit. Use as URLs fornecidas pelo seu workspace Xano; não cole valores secretos no código:

```powershell
$env:XANO_API_URL = "https://SEU-DOMINIO.xano.io/api:GRUPO_PADRAO"
$env:XANO_AUTH_URL = "https://SEU-DOMINIO.xano.io/api:GRUPO_AUTH"
$env:XANO_RESOURCES_URL = "https://SEU-DOMINIO.xano.io/api:GRUPO_RECURSOS"
$env:XANO_CATEGORIES_URL = "https://SEU-DOMINIO.xano.io/api:pi5tdncF"
$env:XANO_PRODUCTS_URL = "https://SEU-DOMINIO.xano.io/api:4FsHXYfS"
$env:XANO_SUPPLIERS_URL = "https://SEU-DOMINIO.xano.io/api:-ryuPWna"
$env:XANO_STOCK_MOVEMENTS_URL = "https://SEU-DOMINIO.xano.io/api:GRUPO_MOVIMENTACOES"
```

`XANO_API_TOKEN` é opcional para iniciar o fluxo de login. Após autenticar, a sessão fornece o token usado pelas chamadas protegidas. Qualquer outra chamada sem token de sessão ou configuração falha explicitamente antes de enviar a requisição.

## Instalação e execução no Windows PowerShell

Na raiz do repositório:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Configure o Xano usando uma das opções acima e inicie a interface:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app/Home.py
```

Após autenticar, selecione **Visão geral**. A consulta usa `XANO_SALES_URL` e o token da sessão; configure a base do grupo Sales e confirme que `GET /sale/metrics` está publicado no Xano para validar os indicadores reais.

## Deploy na Streamlit Community Cloud

1. Publique o repositório no GitHub sem incluir `.env` nem `.streamlit/secrets.toml`.
2. Na Streamlit Community Cloud, crie ou selecione a aplicação e configure o arquivo principal como `app/Home.py`.
3. Configure em **Advanced settings → Secrets** as variáveis `XANO_API_URL`, `XANO_AUTH_URL`, `XANO_RESOURCES_URL` e as bases necessárias aos módulos utilizados (`XANO_CATEGORIES_URL`, `XANO_PRODUCTS_URL`, `XANO_SUPPLIERS_URL`, `XANO_STOCK_ENTRIES_URL`, `XANO_STOCK_MOVEMENTS_URL` e `XANO_SALES_URL`).
4. Não configure um token de usuário compartilhado como segredo da aplicação; o login fornece o token individual usado nas consultas autenticadas.
5. Inicie o deploy e valide a autenticação e os endpoints em um ambiente Xano autorizado. Os testes locais usam mocks e não substituem essa validação.

## Testes

Com o ambiente virtual ativado, execute os testes automatizados existentes:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

Os testes de cadastro usam respostas simuladas para validar mapeamento, autenticação e validações locais. Eles não enviam produtos ao Xano e não substituem um teste autorizado de ponta a ponta.

Para validar sintaxe dos módulos principais:

```powershell
.\.venv\Scripts\python.exe -m py_compile app/Home.py app/xano_client.py
```

## Estrutura principal

```text
app/
  Home.py          Interface Streamlit, sessão e fluxos de produtos
  Teste_Xano.py    Página auxiliar de teste da API
  xano_client.py   Configuração, autenticação e chamadas ao Xano
docs/
  project-overview.md
openspec/
  changes/          Propostas, especificações e tarefas do projeto
tests/
  test_xano_config.py
xano-workspace/
  workspace/       Metadados/export local do workspace Xano
.streamlit/
  secrets.toml     Configuração local ignorada pelo Git
.env.example       Exemplo de nomes de variáveis, sem credenciais reais
README.md
```

## Próximos passos

1. Validar em ambiente autorizado e não produtivo as operações CRUD de produtos e fornecedores, sem confundir essa etapa com os testes mockados.
2. Solicitar ao backend os endpoints necessários para persistir associações produto-fornecedor.
3. Continuar as tarefas pendentes de modelagem e operações financeiras nas respectivas mudanças OpenSpec.
