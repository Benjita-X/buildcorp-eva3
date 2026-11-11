# =============================================================================
# Validación del RUT chileno (formato y dígito verificador).
# Se usa en los campos RUT de Contratista y ResponsableObra.
# =============================================================================
import re  # expresiones regulares (para limpiar y revisar el formato)

from django.core.exceptions import ValidationError


# Deja el RUT en un formato único: sin puntos, con guion y la K en mayúscula
def normalizar_rut(rut: str) -> str:
    """'12.345.678-k' -> '12345678-K'"""
    limpio = re.sub(r"[^0-9kK]", "", rut or "").upper()  # deja solo números y K
    if len(limpio) < 2:
        return limpio
    return f"{limpio[:-1]}-{limpio[-1]}"  # separa el último carácter con un guion


# Calcula el dígito verificador con el algoritmo "módulo 11" (multiplicadores 2 a 7)
def digito_verificador(cuerpo: str) -> str:
    suma, multiplo = 0, 2
    for d in reversed(cuerpo):  # recorre los dígitos de derecha a izquierda
        suma += int(d) * multiplo
        multiplo = 2 if multiplo == 7 else multiplo + 1
    resto = 11 - (suma % 11)
    return {11: "0", 10: "K"}.get(resto, str(resto))  # 11 -> 0, 10 -> K


# Validador: si el RUT está mal, lanza un error que se muestra en el formulario
def validar_rut(valor):
    rut = normalizar_rut(valor)
    if not re.fullmatch(r"\d{7,8}-[\dK]", rut):  # 7 u 8 números, guion y dígito o K
        raise ValidationError("Formato de RUT inválido (ej: 12345678-9).")
    cuerpo, dv = rut.split("-")
    if digito_verificador(cuerpo) != dv:  # compara el dígito escrito con el calculado
        raise ValidationError("El dígito verificador del RUT no es válido.")
