from datetime import date, datetime, time, timedelta, timezone
import math


_UNIX_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
_MIN_UNIX_MILLISECONDS = 100_000_000_000


def _validate_unix_milliseconds(value, field):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field} deve ser um timestamp Unix inteiro em ms.")
    if abs(value) < _MIN_UNIX_MILLISECONDS:
        raise ValueError(
            f"{field} deve estar em milissegundos; timestamps em segundos não são aceitos."
        )
    try:
        return _UNIX_EPOCH + timedelta(milliseconds=value)
    except OverflowError as error:
        raise ValueError(f"{field} está fora do intervalo de datas aceito.") from error


def sale_date_to_unix_milliseconds(value, field="sale_date"):
    if isinstance(value, bool):
        raise ValueError(f"{field} deve ser uma data ou timestamp válido.")

    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, date):
        parsed = datetime.combine(value, time.min)
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            raise ValueError(f"{field} deve ser uma data ou timestamp válido.")
        if text.lstrip("+-").isdigit():
            milliseconds = int(text)
            _validate_unix_milliseconds(milliseconds, field)
            return milliseconds
        try:
            parsed = datetime.fromisoformat(
                text[:-1] + "+00:00" if text.endswith("Z") else text
            )
        except ValueError as error:
            raise ValueError(
                f"{field} deve usar uma data ISO 8601 válida ou timestamp Unix em ms."
            ) from error
    elif isinstance(value, (int, float)):
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError(f"{field} deve ser finita.")
        if int(value) != value:
            raise ValueError(f"{field} deve ser um timestamp inteiro em ms.")
        milliseconds = int(value)
        _validate_unix_milliseconds(milliseconds, field)
        return milliseconds
    else:
        raise ValueError(
            f"{field} deve ser uma data ISO 8601 ou timestamp Unix em ms."
        )

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    utc_value = parsed.astimezone(timezone.utc)
    elapsed = utc_value - _UNIX_EPOCH
    milliseconds = (
        elapsed.days * 86_400_000
        + elapsed.seconds * 1_000
        + elapsed.microseconds // 1_000
    )
    _validate_unix_milliseconds(milliseconds, field)
    return milliseconds


def sale_date_from_unix_milliseconds(value):
    return _validate_unix_milliseconds(value, "sale_date")


def format_sale_date(value):
    milliseconds = sale_date_to_unix_milliseconds(value)
    return (
        sale_date_from_unix_milliseconds(milliseconds)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )
