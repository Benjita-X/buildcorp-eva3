import re

from django.core.exceptions import ValidationError


def normalizar_rut(rut: str) -> str:
    """'12.345.678-k' -> '12345678-K'"""
    limpio = re.sub(r"[^0-9kK]", "", rut or "").upper()
    if len(limpio) < 2:
        return limpio
    return f"{limpio[:-1]}-{limpio[-1]}"


def digito_verificador(cuerpo: str) -> str:
    suma, multiplo = 0, 2
    for d in reversed(cuerpo):
        suma += int(d) * multiplo
        multiplo = 2 if multiplo == 7 else multiplo + 1
    resto = 11 - (suma % 11)
    return {11: "0", 10: "K"}.get(resto, str(resto))


def validar_rut(valor):
    rut = normalizar_rut(valor)
    if not re.fullmatch(r"\d{7,8}-[\dK]", rut):
        raise ValidationError("Formato de RUT inválido (ej: 12345678-9).")
    cuerpo, dv = rut.split("-")
    if digito_verificador(cuerpo) != dv:
        raise ValidationError("El dígito verificador del RUT no es válido.")
