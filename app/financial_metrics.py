from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


_CENTAVO = Decimal("0.01")


def _decimalizar(valor, nome):
    try:
        numero = Decimal(str(valor))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError(f"{nome} deve ser numérico.") from None

    if not numero.is_finite():
        raise ValueError(f"{nome} deve ser um valor finito.")

    return numero


def calcular_cmv(quantidades_vendidas, custos_unitarios_historicos):
    """Calcula o CMV a partir das quantidades e custos históricos por item."""
    quantidades = list(quantidades_vendidas)
    custos = list(custos_unitarios_historicos)

    if len(quantidades) != len(custos):
        raise ValueError(
            "Cada quantidade vendida deve ter um custo unitário histórico correspondente."
        )

    total = Decimal("0")
    for quantidade, custo_unitario in zip(quantidades, custos):
        quantidade = _decimalizar(quantidade, "Quantidade vendida")
        custo_unitario = _decimalizar(
            custo_unitario,
            "Custo unitário histórico",
        )

        if quantidade < 0:
            raise ValueError("A quantidade vendida não pode ser negativa.")
        if custo_unitario < 0:
            raise ValueError("O custo unitário histórico não pode ser negativo.")

        total += quantidade * custo_unitario

    return total.quantize(_CENTAVO, rounding=ROUND_HALF_UP)


def calcular_indicadores_financeiros(
    receita_vendas,
    quantidades_vendidas,
    custos_unitarios_historicos,
    custos_venda,
):
    """Calcula os indicadores para valores já filtrados para o período válido.

    A seleção de vendas válidas, itens históricos e custos do período pertence à
    camada de dados; este projeto ainda não possui os endpoints Xano necessários.
    """
    receita = _decimalizar(receita_vendas, "Receita de vendas")
    custos_venda = _decimalizar(custos_venda, "Custos de venda")

    if receita < 0:
        raise ValueError("A receita de vendas não pode ser negativa.")
    if custos_venda < 0:
        raise ValueError("Os custos de venda não podem ser negativos.")

    cmv = calcular_cmv(
        quantidades_vendidas,
        custos_unitarios_historicos,
    )
    resultado = (receita - cmv - custos_venda).quantize(
        _CENTAVO,
        rounding=ROUND_HALF_UP,
    )
    margem = (
        None
        if receita == 0
        else (resultado / receita * Decimal("100")).quantize(
            _CENTAVO,
            rounding=ROUND_HALF_UP,
        )
    )

    return {
        "receita_vendas": receita.quantize(
            _CENTAVO,
            rounding=ROUND_HALF_UP,
        ),
        "cmv": cmv,
        "custos_venda": custos_venda.quantize(
            _CENTAVO,
            rounding=ROUND_HALF_UP,
        ),
        "resultado_apos_custos": resultado,
        "margem_percentual": margem,
    }