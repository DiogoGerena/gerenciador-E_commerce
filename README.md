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
- Formulário local de cadastro com validação de nome, descrição, ID da categoria, estoque mínimo, preço e situação. O SKU é opcional. O cliente exclui `id` e custo de aquisição do payload.
- Função `criar_produto()` que envia JSON para `POST /product` com o token Bearer da sessão. Os testes usam mocks e não criam registros reais.
- Tratamento local de erros HTTP e conexão, com proteção para não exibir tokens ou credenciais.
- Integração mockada da seção de estoque: visão geral, entradas paginadas, kardex, ajustes, perdas/avarias e devoluções.
- Integração mockada do módulo de vendas: registro com UUID v4, histórico paginado, filtros e detalhes.
- Preservação do payload e da chave em operações de venda inconclusivas, sem geração automática de nova chave.
- Operações administrativas de estoque são ocultadas para perfis operacionais; o backend continua sendo a autoridade das permissões.

Os testes do cliente não comprovam que o contrato de `POST /product` esteja compatível com a configuração atual do Xano.

### Pendências e limitações conhecidas

- **Cadastro real de produtos:** o formulário e o cliente foram implementados, mas o payload ainda precisa ser confirmado contra os inputs reais de `POST /product`. Não há comprovação de criação bem-sucedida no Xano.
- **Validação ponta a ponta:** login válido, consulta real de `/auth/me`, criação e consulta do produto criado dependem de credenciais autorizadas e do contrato ativo no Xano. Credenciais não são fornecidas neste README.
- **Validação real de estoque:** os endpoints de estoque foram integrados conforme os contratos fornecidos, mas dependem de homologação autorizada no Xano.
- **Devolução de cliente:** a interface usa `reference_id` para identificar a venda original e não inventa `sale_item_id`; a relação exata do item vendido deve ser validada no endpoint real.
- **Validação real de vendas:** os mocks cobrem o cliente e a interface, mas `POST /sale`, `GET /sale` e `GET /sale/{id}` dependem de homologação autorizada no Xano.
- **Dashboard financeiro:** os indicadores são consultados em tempo real por `GET /sale/metrics`, com filtros de canal, status e período. A disponibilidade ponta a ponta depende da publicação desse endpoint no Xano; enquanto estiver indisponível, a interface apresenta o erro sem substituir os dados por valores zerados. Não há gráficos históricos, pois o endpoint agregado não fornece séries temporais.
- **Marketplaces:** integração automática não está implementada.
- **Contrato de listagem:** conforme configuração do Xano inspecionada para `GET /product`, a busca usa `name includes input:name`; `category_id` e `status` são condições adicionais. A interface atual pesquisa pelo nome e não promete listagem global.
- O formulário de cadastro usa campos sustentados pela especificação e pelos nomes já usados na interface. A aceitação desses nomes, tipos, obrigatoriedade, valores de `status` e relacionamento de categoria precisa ser validada no endpoint remoto antes de considerar o cadastro integrado.
- As tarefas pendentes e o estado completo estão em [`openspec/changes/controle-financeiro-estoque/tasks.md`](openspec/changes/controle-financeiro-estoque/tasks.md).

## Pré-requisitos

- Windows com PowerShell.
- Python 3 instalado e disponível pelo comando `py` ou `python`.
- Acesso autorizado ao workspace Xano para usar a aplicação com backend.

O repositório declara as dependências diretamente usadas pela aplicação em `requirements.txt`: Streamlit, pandas e requests.

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

Não coloque senhas, tokens ou URLs privadas em arquivos versionados. `.env.example` contém placeholders; o código atual não carrega `.env` automaticamente. Use uma das opções abaixo.

### Opção A: Streamlit secrets

Crie `.streamlit/secrets.toml` localmente, substituindo os placeholders pelas URLs do seu workspace Xano:

```toml
XANO_API_URL = "https://SEU-DOMINIO.xano.io/api:GRUPO_PADRAO"
XANO_AUTH_URL = "https://SEU-DOMINIO.xano.io/api:GRUPO_AUTH"
XANO_RESOURCES_URL = "https://SEU-DOMINIO.xano.io/api:GRUPO_RECURSOS"
XANO_SALES_URL = "https://SEU-DOMINIO.xano.io/api:EjdVpi9b"
XANO_API_TOKEN = ""
```

O arquivo `.streamlit/secrets.toml` está ignorado pelo Git. Não compartilhe nem versione credenciais reais.

### Opção B: variáveis de ambiente no PowerShell

Defina os valores no terminal em que executará o Streamlit. Use as URLs fornecidas pelo seu workspace Xano; não cole valores secretos no código:

```powershell
$env:XANO_API_URL = "https://SEU-DOMINIO.xano.io/api:GRUPO_PADRAO"
$env:XANO_AUTH_URL = "https://SEU-DOMINIO.xano.io/api:GRUPO_AUTH"
$env:XANO_RESOURCES_URL = "https://SEU-DOMINIO.xano.io/api:GRUPO_RECURSOS"
```

`XANO_API_TOKEN` é opcional para o fluxo de login da aplicação. Se necessário no seu ambiente, configure-o somente no terminal ou em um secret local.

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

Após autenticar, selecione **Dashboard**. A consulta usa `XANO_SALES_URL` e o token da sessão; configure a base do grupo Sales e confirme que `GET /sale/metrics` está publicado no Xano para validar os indicadores reais.

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

1. Confirmar no painel do Xano os inputs, tipos, campos obrigatórios, relacionamentos, permissões e resposta de `POST /product`.
2. Validar o cadastro com uma conta autorizada e dados fictícios, sem alterar ou remover produtos reais.
3. Verificar a consulta do produto criado e ajustar o mapeamento local somente conforme o contrato confirmado.
4. Continuar as tarefas pendentes de modelagem e operações financeiras no OpenSpec.
