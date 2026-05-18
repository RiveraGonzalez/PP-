"""
PPFormularios.py
================
Lógica de captura, validación y gestión de formularios del sistema.

Módulos:
    - FormularioDia      : Configuración del día de trabajo
    - FormularioPaquete  : Registro y validación de paquetes
    - GestorFormularios  : Coordinador de ambos formularios

Proyecto: Sistema Inteligente de Gestión y Optimización de Entregas
Materia : Algoritmos Metaheurísticos
"""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum
import uuid


# ==============================================================================
# ENUMERACIONES
# ==============================================================================

class DiaSemana(Enum):
    LUNES     = "Lunes"
    MARTES    = "Martes"
    MIERCOLES = "Miércoles"
    JUEVES    = "Jueves"
    VIERNES   = "Viernes"
    SABADO    = "Sábado"
    DOMINGO   = "Domingo"


class Actividad(Enum):
    REGISTRAR_PAQUETES  = "paquetes"
    REALIZAR_ENTREGAS   = "entregas"
    AMBAS               = "ambas"


class TipoPaquete(Enum):
    BOLSA_PEQUENA = "bolsa"
    CAJA_CHICA    = "caja-chica"
    CAJA_MEDIANA  = "caja-mediana"
    CAJA_GRANDE   = "caja-grande"


class Prioridad(Enum):
    ROJO  = "rojo"   # Entrega inmediata
    AZUL  = "azul"   # 1 a 3 días
    VERDE = "verde"  # 1 a 7 días


# ==============================================================================
# CONSTANTES DE DIMENSIONES
# ==============================================================================

DIMENSIONES: dict[str, dict] = {
    TipoPaquete.BOLSA_PEQUENA.value: {
        "largo_cm": 30,
        "ancho_cm": 20,
        "alto_cm":  10,
        "volumen_m3": 0.006,
        "peso_max_kg": 5.0,
    },
    TipoPaquete.CAJA_CHICA.value: {
        "largo_cm": 30,
        "ancho_cm": 30,
        "alto_cm":  30,
        "volumen_m3": 0.027,
        "peso_max_kg": 15.0,
    },
    TipoPaquete.CAJA_MEDIANA.value: {
        "largo_cm": 50,
        "ancho_cm": 40,
        "alto_cm":  30,
        "volumen_m3": 0.060,
        "peso_max_kg": 40.0,
    },
    TipoPaquete.CAJA_GRANDE.value: {
        "largo_cm": 80,
        "ancho_cm": 60,
        "alto_cm":  50,
        "volumen_m3": 0.240,
        "peso_max_kg": 200.0,
    },
}

DIAS_ENTREGA: dict[str, str] = {
    Prioridad.ROJO.value:  "Entrega inmediata",
    Prioridad.AZUL.value:  "1 a 3 días",
    Prioridad.VERDE.value: "1 a 7 días",
}


# ==============================================================================
# DATACLASSES
# ==============================================================================

@dataclass
class Paquete:
    """Representa un paquete registrado en el sistema."""
    id:           str
    tipo:         str
    peso_kg:      float
    prioridad:    str
    coord_x:      float
    coord_y:      float
    volumen_m3:   float     = 0.0
    largo_cm:     int       = 0
    ancho_cm:     int       = 0
    alto_cm:      int       = 0
    estado:       str       = "pendiente"   # pendiente | entregado | conservado
    dia_registro: str       = ""

    def __post_init__(self):
        """Calcula dimensiones automáticamente al crear el paquete."""
        if self.tipo in DIMENSIONES:
            dims = DIMENSIONES[self.tipo]
            self.volumen_m3 = dims["volumen_m3"]
            self.largo_cm   = dims["largo_cm"]
            self.ancho_cm   = dims["ancho_cm"]
            self.alto_cm    = dims["alto_cm"]

    @property
    def distancia_almacen(self) -> float:
        """Distancia euclidiana desde el almacén (0, 0)."""
        return round((self.coord_x ** 2 + self.coord_y ** 2) ** 0.5, 2)

    @property
    def score_prioridad(self) -> int:
        """Puntuación numérica de prioridad para ordenamiento."""
        scores = {
            Prioridad.ROJO.value:  100,
            Prioridad.AZUL.value:  60,
            Prioridad.VERDE.value: 20,
        }
        return scores.get(self.prioridad, 0)

    def to_dict(self) -> dict:
        """Serializa el paquete a diccionario."""
        return {
            "id":           self.id,
            "tipo":         self.tipo,
            "peso_kg":      self.peso_kg,
            "prioridad":    self.prioridad,
            "coord_x":      self.coord_x,
            "coord_y":      self.coord_y,
            "volumen_m3":   self.volumen_m3,
            "largo_cm":     self.largo_cm,
            "ancho_cm":     self.ancho_cm,
            "alto_cm":      self.alto_cm,
            "estado":       self.estado,
            "dia_registro": self.dia_registro,
            "distancia":    self.distancia_almacen,
        }

    def __repr__(self) -> str:
        return (f"Paquete({self.id} | {self.tipo} | "
                f"{self.peso_kg}kg | ({self.coord_x},{self.coord_y}) | "
                f"{self.prioridad})")


@dataclass
class ConfigDia:
    """Configuración del día de trabajo activo."""
    dia:       str
    actividad: str
    activo:    bool = False

    @property
    def permite_paquetes(self) -> bool:
        return self.actividad in (
            Actividad.REGISTRAR_PAQUETES.value,
            Actividad.AMBAS.value,
        )

    @property
    def permite_entregas(self) -> bool:
        return self.actividad in (
            Actividad.REALIZAR_ENTREGAS.value,
            Actividad.AMBAS.value,
        )


# ==============================================================================
# VALIDACIONES
# ==============================================================================

class ErrorValidacion(Exception):
    """Excepción personalizada para errores de validación de formularios."""
    pass


def _validar_dia(dia: str) -> str:
    """Valida que el día sea uno de los permitidos."""
    dias_validos = [d.value for d in DiaSemana]
    if dia not in dias_validos:
        raise ErrorValidacion(
            f"Día inválido: '{dia}'. Opciones: {', '.join(dias_validos)}"
        )
    return dia


def _validar_actividad(actividad: str) -> str:
    """Valida que la actividad sea una de las permitidas."""
    actividades_validas = [a.value for a in Actividad]
    if actividad not in actividades_validas:
        raise ErrorValidacion(
            f"Actividad inválida: '{actividad}'. Opciones: {', '.join(actividades_validas)}"
        )
    return actividad


def _validar_tipo_paquete(tipo: str) -> str:
    """Valida el tipo de paquete y comprueba su existencia en DIMENSIONES."""
    tipos_validos = [t.value for t in TipoPaquete]
    if tipo not in tipos_validos:
        raise ErrorValidacion(
            f"Tipo de paquete inválido: '{tipo}'. Opciones: {', '.join(tipos_validos)}"
        )
    return tipo


def _validar_peso(peso: float, tipo: str) -> float:
    """Valida que el peso sea positivo y no supere el máximo del tipo."""
    if peso <= 0:
        raise ErrorValidacion("El peso debe ser mayor a 0 kg.")
    peso_max = DIMENSIONES[tipo]["peso_max_kg"]
    if peso > peso_max:
        raise ErrorValidacion(
            f"El peso {peso} kg supera el máximo permitido para '{tipo}': {peso_max} kg."
        )
    return round(peso, 2)


def _validar_prioridad(prioridad: str) -> str:
    """Valida que la prioridad sea una de las permitidas."""
    prioridades_validas = [p.value for p in Prioridad]
    if prioridad not in prioridades_validas:
        raise ErrorValidacion(
            f"Prioridad inválida: '{prioridad}'. Opciones: {', '.join(prioridades_validas)}"
        )
    return prioridad


def _validar_coordenadas(x: float, y: float) -> tuple[float, float]:
    """Valida que las coordenadas estén dentro del rango operativo."""
    RANGO_MAX = 100
    if not (-RANGO_MAX <= x <= RANGO_MAX) or not (-RANGO_MAX <= y <= RANGO_MAX):
        raise ErrorValidacion(
            f"Coordenadas fuera de rango. Deben estar entre -{RANGO_MAX} y {RANGO_MAX}."
        )
    return round(x, 2), round(y, 2)


# ==============================================================================
# FORMULARIO DÍA DE TRABAJO
# ==============================================================================

class FormularioDia:
    """
    Gestiona la configuración del día de trabajo.

    Uso:
        form = FormularioDia()
        config = form.iniciar(dia="Lunes", actividad="ambas")
    """

    def __init__(self):
        self._config: Optional[ConfigDia] = None

    def iniciar(self, dia: str, actividad: str) -> ConfigDia:
        """
        Valida y activa la configuración del día.

        Args:
            dia       : Día de la semana (ej. "Lunes").
            actividad : Actividad del día (ej. "ambas").

        Returns:
            ConfigDia con el día y actividad configurados.

        Raises:
            ErrorValidacion: Si los datos no son válidos.
        """
        dia_validado       = _validar_dia(dia)
        actividad_validada = _validar_actividad(actividad)

        self._config = ConfigDia(
            dia=dia_validado,
            actividad=actividad_validada,
            activo=True,
        )
        return self._config

    @property
    def config(self) -> Optional[ConfigDia]:
        return self._config

    @property
    def dia_activo(self) -> bool:
        return self._config is not None and self._config.activo

    def resetear(self):
        """Limpia la configuración del día."""
        self._config = None


# ==============================================================================
# FORMULARIO REGISTRO DE PAQUETES
# ==============================================================================

class FormularioPaquete:
    """
    Gestiona el registro, validación y generación de IDs de paquetes.

    Uso:
        form_pkg = FormularioPaquete()
        paquete  = form_pkg.registrar(tipo="caja-chica", peso=5.0,
                                       prioridad="rojo", x=4, y=7)
    """

    def __init__(self, dia_activo: str = ""):
        self._contador: int          = 1
        self._dia_activo: str        = dia_activo
        self._paquetes: list[Paquete] = []

    # ------------------------------------------------------------------
    # ID AUTOMÁTICO
    # ------------------------------------------------------------------

    def generar_id(self) -> str:
        """Genera el siguiente ID de paquete en formato PKG-XXX."""
        return f"PKG-{self._contador:03d}"

    # ------------------------------------------------------------------
    # DIMENSIONES
    # ------------------------------------------------------------------

    def obtener_dimensiones(self, tipo: str) -> dict:
        """
        Retorna las dimensiones del tipo de paquete indicado.

        Args:
            tipo: Clave del tipo (ej. "caja-chica").

        Returns:
            Diccionario con largo, ancho, alto, volumen y peso máximo.
        """
        tipo = _validar_tipo_paquete(tipo)
        return DIMENSIONES[tipo]

    # ------------------------------------------------------------------
    # REGISTRO
    # ------------------------------------------------------------------

    def registrar(
        self,
        tipo:      str,
        peso:      float,
        prioridad: str,
        x:         float,
        y:         float,
    ) -> Paquete:
        """
        Valida los datos y crea un nuevo Paquete en el sistema.

        Args:
            tipo      : Tipo de paquete (ver TipoPaquete).
            peso      : Peso en kilogramos.
            prioridad : Nivel de urgencia (ver Prioridad).
            x         : Coordenada X de entrega.
            y         : Coordenada Y de entrega.

        Returns:
            Objeto Paquete registrado.

        Raises:
            ErrorValidacion: Si algún campo no es válido.
        """
        tipo_v      = _validar_tipo_paquete(tipo)
        peso_v      = _validar_peso(peso, tipo_v)
        prioridad_v = _validar_prioridad(prioridad)
        x_v, y_v    = _validar_coordenadas(x, y)

        paquete = Paquete(
            id           = self.generar_id(),
            tipo         = tipo_v,
            peso_kg      = peso_v,
            prioridad    = prioridad_v,
            coord_x      = x_v,
            coord_y      = y_v,
            dia_registro = self._dia_activo,
        )

        self._paquetes.append(paquete)
        self._contador += 1
        return paquete

    # ------------------------------------------------------------------
    # CONSULTAS
    # ------------------------------------------------------------------

    def limpiar_campos(self) -> dict:
        """Retorna un diccionario con campos vacíos (para resetear el UI)."""
        return {
            "id":        self.generar_id(),
            "tipo":      "",
            "peso":      "",
            "prioridad": "",
            "x":         "",
            "y":         "",
        }

    def obtener_todos(self) -> list[Paquete]:
        return list(self._paquetes)

    def obtener_por_prioridad(self, prioridad: str) -> list[Paquete]:
        return [p for p in self._paquetes if p.prioridad == prioridad]

    def obtener_pendientes(self) -> list[Paquete]:
        return [p for p in self._paquetes if p.estado == "pendiente"]

    def total_registrados(self) -> int:
        return len(self._paquetes)

    def total_peso(self) -> float:
        return round(sum(p.peso_kg for p in self._paquetes), 2)

    def total_volumen(self) -> float:
        return round(sum(p.volumen_m3 for p in self._paquetes), 4)


# ==============================================================================
# GESTOR PRINCIPAL
# ==============================================================================

class GestorFormularios:
    """
    Coordinador central de todos los formularios del sistema.
    Expone una interfaz unificada para el resto de módulos.

    Uso:
        gestor = GestorFormularios()
        gestor.iniciar_dia("Lunes", "ambas")
        pkg = gestor.registrar_paquete("caja-chica", 5.0, "rojo", 4, 7)
    """

    def __init__(self):
        self.form_dia     = FormularioDia()
        self.form_paquete = FormularioPaquete()

    # ------------------------------------------------------------------
    # DÍA
    # ------------------------------------------------------------------

    def iniciar_dia(self, dia: str, actividad: str) -> ConfigDia:
        """Configura e inicia el día de trabajo."""
        config = self.form_dia.iniciar(dia, actividad)
        self.form_paquete._dia_activo = dia
        print(f"[DÍA INICIADO] {dia} — Actividad: {actividad}")
        return config

    def config_dia(self) -> Optional[ConfigDia]:
        return self.form_dia.config

    # ------------------------------------------------------------------
    # PAQUETES
    # ------------------------------------------------------------------

    def registrar_paquete(
        self,
        tipo:      str,
        peso:      float,
        prioridad: str,
        x:         float,
        y:         float,
    ) -> Paquete:
        """Valida que el día esté activo y registra el paquete."""
        if not self.form_dia.dia_activo:
            raise ErrorValidacion("Debes iniciar el día antes de registrar paquetes.")

        config = self.form_dia.config
        if not config.permite_paquetes:
            raise ErrorValidacion(
                f"La actividad '{config.actividad}' no incluye registro de paquetes."
            )

        paquete = self.form_paquete.registrar(tipo, peso, prioridad, x, y)
        print(f"[PAQUETE] {paquete}")
        return paquete

    def obtener_paquetes(self) -> list[Paquete]:
        return self.form_paquete.obtener_todos()

    def obtener_pendientes(self) -> list[Paquete]:
        return self.form_paquete.obtener_pendientes()

    def siguiente_id(self) -> str:
        return self.form_paquete.generar_id()

    def dimensiones_tipo(self, tipo: str) -> dict:
        return self.form_paquete.obtener_dimensiones(tipo)

    def resumen(self) -> dict:
        """Resumen rápido del estado actual de los formularios."""
        return {
            "dia":              self.form_dia.config.dia if self.form_dia.dia_activo else None,
            "actividad":        self.form_dia.config.actividad if self.form_dia.dia_activo else None,
            "total_paquetes":   self.form_paquete.total_registrados(),
            "total_peso_kg":    self.form_paquete.total_peso(),
            "total_volumen_m3": self.form_paquete.total_volumen(),
            "pendientes":       len(self.form_paquete.obtener_pendientes()),
        }


# ==============================================================================
# DEMO
# ==============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  PPFormularios.py — Demo de prueba")
    print("=" * 60)

    gestor = GestorFormularios()

    # Iniciar día
    config = gestor.iniciar_dia("Lunes", "ambas")
    print(f"\nDía: {config.dia} | Permite paquetes: {config.permite_paquetes} | Permite entregas: {config.permite_entregas}")

    # Registrar paquetes de prueba
    print("\n--- Registrando paquetes ---")
    datos = [
        ("caja-chica",   5.0,  "rojo",   4,  7),
        ("caja-mediana", 12.5, "azul",  -3,  5),
        ("bolsa",         0.8, "verde",  10, -2),
        ("caja-grande",  80.0, "rojo",   2,  9),
    ]
    for tipo, peso, prioridad, x, y in datos:
        try:
            pkg = gestor.registrar_paquete(tipo, peso, prioridad, x, y)
            dims = gestor.dimensiones_tipo(tipo)
            print(f"  ✓ {pkg} | Vol: {pkg.volumen_m3} m³ | Dist: {pkg.distancia_almacen} km")
        except ErrorValidacion as e:
            print(f"  ✗ Error: {e}")

    # Intentar un paquete con error
    print("\n--- Prueba de validación ---")
    try:
        gestor.registrar_paquete("bolsa", 999.0, "rojo", 5, 5)
    except ErrorValidacion as e:
        print(f"  ✗ Capturado correctamente: {e}")

    # Resumen
    print("\n--- Resumen ---")
    for k, v in gestor.resumen().items():
        print(f"  {k}: {v}")
