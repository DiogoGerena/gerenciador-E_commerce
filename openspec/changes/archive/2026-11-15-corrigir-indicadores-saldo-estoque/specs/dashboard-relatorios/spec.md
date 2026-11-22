## MODIFIED Requirements

### Requirement: Indicadores de estoque

Este requisito é normativo (MUST).

O sistema DEVE apresentar a quantidade disponível dos produtos e o valor estimado do estoque.

O valor do estoque DEVE considerar as quantidades disponíveis e os custos unitários de referência calculados pelo sistema.

O sistema DEVE identificar os produtos cuja quantidade disponível seja igual ou inferior ao estoque mínimo cadastrado.

O sistema DEVE distinguir valores numéricos conhecidos, inclusive zero, de dados ausentes, nulos ou inválidos. Dados ausentes ou inválidos NÃO DEVEM ser convertidos ou apresentados como zero.

O sistema DEVE apresentar totais de quantidade e valor financeiro somente quando todos os produtos incluídos tiverem os campos necessários conhecidos e válidos. Quando houver dados incompletos, DEVE indicar que o total está indisponível e informar quantos produtos possuem campos indisponíveis ou inválidos.

O sistema DEVE classificar um produto como sem estoque quando sua quantidade conhecida for zero, mesmo que o estoque mínimo não esteja disponível. Para quantidade positiva, o sistema DEVE classificar como estoque baixo quando a quantidade for igual ou inferior ao estoque mínimo conhecido, e como normal somente quando for maior que o estoque mínimo conhecido. Quando a quantidade estiver ausente, nula ou inválida, ou quando a quantidade for positiva e o estoque mínimo estiver ausente, nulo ou inválido, a classificação DEVE ser indeterminada.

#### Cenário: Consultar indicadores com dados completos

- **QUANDO** todos os produtos retornados possuírem quantidade, custo médio e estoque mínimo numéricos
- **ENTÃO** o sistema DEVE apresentar os totais de quantidade e valor do estoque e classificar os produtos conforme seus valores conhecidos

#### Cenário: Consultar indicadores com quantidade ausente ou inválida

- **QUANDO** um ou mais produtos não possuírem quantidade disponível válida
- **ENTÃO** o sistema NÃO DEVE tratar essas quantidades como zero nem apresentar a soma das demais quantidades como total completo
- **E** DEVE indicar a quantidade de produtos com dados indisponíveis ou inválidos

#### Cenário: Consultar valor do estoque com custo médio ausente ou inválido

- **QUANDO** um ou mais produtos não possuírem custo médio válido
- **ENTÃO** o sistema NÃO DEVE apresentar o valor financeiro parcial como total completo nem representar os custos desconhecidos como zero
- **E** DEVE indicar a quantidade de produtos sem valor financeiro calculável

#### Cenário: Classificar produto positivo sem estoque mínimo conhecido

- **QUANDO** um produto possuir quantidade positiva conhecida e seu estoque mínimo estiver ausente, nulo ou inválido
- **ENTÃO** o sistema DEVE apresentar a classificação como indeterminada e NÃO DEVE classificá-lo como normal ou baixo por inferência do mínimo

#### Cenário: Classificar quantidade zero sem estoque mínimo conhecido

- **QUANDO** um produto possuir quantidade igual a zero e seu estoque mínimo estiver ausente, nulo ou inválido
- **ENTÃO** o sistema DEVE classificá-lo como sem estoque porque a quantidade zero é conhecida

#### Cenário: Preservar valores legítimos iguais a zero

- **QUANDO** a quantidade ou o custo médio informado pelo serviço for zero
- **ENTÃO** o sistema DEVE preservar o zero como valor conhecido e aplicá-lo nos cálculos e classificações correspondentes

#### Cenário: Identificar estoque baixo

- **QUANDO** a quantidade disponível de um produto for igual ou inferior ao estoque mínimo cadastrado
- **ENTÃO** o sistema DEVE destacar o produto no dashboard como um item que exige atenção

#### Cenário: Consultar valor do estoque

- **QUANDO** um usuário consultar os indicadores de estoque
- **ENTÃO** o sistema DEVE apresentar o valor estimado dos produtos disponíveis com base nos custos registrados

#### Cenário: Consultar estoque sem produtos

- **QUANDO** o serviço retornar uma lista vazia de produtos
- **ENTÃO** o sistema DEVE apresentar um estado vazio apropriado e NÃO DEVE exibir produtos ou valores demonstrativos

### Requirement: Relatórios de estoque

Este requisito é normativo (MUST).

O sistema DEVE permitir consultar relatórios de produtos com quantidade disponível, estoque mínimo, custo médio e valor estimado em estoque.

O sistema DEVE permitir identificar produtos abaixo ou no limite do estoque mínimo.

O sistema DEVE disponibilizar o histórico de entradas e movimentações para consulta.

Quando os dados de quantidade, custo médio ou estoque mínimo estiverem ausentes, nulos ou inválidos, o relatório DEVE apresentá-los como indisponíveis ou indeterminados. Os gráficos quantitativos DEVEM omitir os valores desconhecidos em vez de plotá-los como zero e DEVEM informar quando os dados estiverem incompletos ou não forem suficientes para gerar um gráfico.

#### Cenário: Consultar relatório de estoque baixo

- **QUANDO** um usuário solicitar a relação de produtos com estoque baixo
- **ENTÃO** o sistema DEVE apresentar os produtos cuja quantidade disponível seja igual ou inferior ao estoque mínimo cadastrado

#### Cenário: Consultar movimentações de um produto

- **QUANDO** um usuário selecionar um produto em um relatório de estoque
- **ENTÃO** o sistema DEVE permitir consultar o histórico de entradas, saídas, ajustes, perdas e devoluções registradas para esse produto

#### Cenário: Exibir gráficos com dados incompletos

- **QUANDO** produtos retornados possuírem quantidade ou valor estimado indisponível
- **ENTÃO** os gráficos DEVEM omitir esses valores do eixo numérico, identificar a incompletude e NÃO DEVEM representá-los como zero

#### Cenário: Exibir gráfico sem dados suficientes

- **QUANDO** não houver valores conhecidos e válidos suficientes para um gráfico
- **ENTÃO** o sistema DEVE apresentar uma mensagem de indisponibilidade em vez de um gráfico que sugira valores inexistentes
