"""
PPTablas.py
===========
Administración de todas las tablas y registros del sistema.

Módulos:
    - TablaIniciales    : Paquetes disponibles al iniciar el día
    - TablaEntregados   : Paquetes asignados a rutas y vehículos
    - TablaConservados  : Paquetes no enviados y sus motivos
    - ResumenSemanal    : Estadísticas acumuladas por día
    - GestorTablas      : Coordinador central de todas las tablas

Proyecto: Sistema Inteligente de Gestión y Optimización de Entregas
Materia : Algoritmos Metaheurísticos
"""

from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING
from datetime import datetime

if TYPE_CHECKING:
    from PPFormularios import Paquete
    from PPVehiculos   import Vehiculo


# ==============================================================================
# CONSTANTES
# ==============================================================================

DIAS_SEMANA = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

RAZONES_CONSERVACION = {
    "muy_lejos":      "Muy lejos",
    "exceso_peso":    "Exceso de peso",
    "exceso_vol":     "Exceso de volumen",
    "baja_prioridad": "Baja prioridad",
    "sin_vehiculo":   "Sin vehículo disponible",
    "eficiencia":     "Baja eficiencia logística",
}


# ==============================================================================
# DATACLASSES DE REGISTRO
# ==============================================================================

@dataclass
class RegistroEntregado:
    """Entrada en la tabla de paquetes entregados."""
    paquete_id:   str
    vehiculo_id:  str
    vehiculo_nom: str
    ruta_id:      str
    distancia_km: float
    estado:       str   = "En ruta"    # En ruta | Entregado
    hora_salida:  str   = ""

    def __post_init__(self):
        if not self.hora_salida:
            self.hora_salida = datetime.now().strftime("%H:%M")

    def to_dict(self) -> dict:
        return {
            "id":           self.paquete_id,
            "vehiculo_id":  self.vehiculo_id,
            "vehiculo":     self.vehiculo_nom,
            "ruta":         self.ruta_id,
            "distancia_km": self.distancia_km,
            "estado":       self.estado,
            "hora_salida":  self.hora_salida,
        }


@dataclass
class RegistroConservado:
    """Entrada en la tabla de paquetes conservados."""
    paquete_id:   str
    razon_clave:  str
    distancia_km: float
    prioridad:    str

    @property
    def razon_texto(self) -> str:
        return RAZONES_CONSERVACION.get(self.razon_clave, self.razon_clave)

    def to_dict(self) -> dict:
        return {
            "id":           self.paquete_id,
            "razon":        self.razon_texto,
            "distancia_km": self.distancia_km,
            "prioridad":    self.prioridad,
        }


@dataclass
class RegistroDiaSemanal:
    """Estadísticas de un día específico para el resumen semanal."""
    dia:              str
    iniciales:        int   = 0
    entregados:       int   = 0
    conservados:      int   = 0
    distancia_km:     float = 0.0
    combustible_l:    float = 0.0
    vehiculos_usados: int   = 0

    @property
    def eficiencia_pct(self) -> float:
        """Porcentaje de paquetes entregados sobre iniciales."""
        if self.iniciales == 0:
            return 0.0
        return round((self.entregados / self.iniciales) * 100, 1)

    @property
    def activo(self) -> bool:
        """True si el día tiene datos registrados."""
        return self.iniciales > 0

    def to_dict(self) -> dict:
        return {
            "dia":              self.dia,
            "iniciales":        self.iniciales,
            "entregados":       self.entregados,
            "conservados":      self.conservados,
            "distancia_km":     round(self.distancia_km, 2),
            "combustible_l":    round(self.combustible_l, 2),
            "vehiculos_usados": self.vehiculos_usados,
            "eficiencia_pct":   self.eficiencia_pct,
        }


# ==============================================================================
# TABLA PAQUETES INICIALES
# ==============================================================================

class TablaIniciales:
    """
    Contiene todos los paquetes disponibles al iniciar el día:
    - Nuevos registrados ese día.
    - Conservados (pendientes) de días anteriores.

    Uso:
        tabla = TablaIniciales()
        tabla.cargar(paquetes_nuevos, paquetes_pendientes)
        tabla.mostrar()
    """

    def __init__(self):
        self._registros: list["Paquete"] = []

    def cargar(
        self,
        paquetes_nuevos:     list["Paquete"],
        paquetes_pendientes: list["Paquete"] | None = None,
    ):
        """
        Carga los paquetes del día. Combina nuevos y pendientes.

        Args:
            paquetes_nuevos     : Paquetes registrados hoy.
            paquetes_pendientes : Paquetes conservados de días anteriores.
        """
        self._registros = list(paquetes_nuevos)
        if paquetes_pendientes:
            self._registros.extend(paquetes_pendientes)

    def agregar(self, paquete: "Paquete"):
        """Agrega un paquete individual a la tabla."""
        self._registros.append(paquete)

    def todos(self) -> list["Paquete"]:
        return list(self._registros)

    def filtrar_por_prioridad(self, prioridad: str) -> list["Paquete"]:
        return [p for p in self._registros if p.prioridad == prioridad]

    def ordenar_por_prioridad(self) -> list["Paquete"]:
        """Ordena: rojo → azul → verde (mayor urgencia primero)."""
        orden = {"rojo": 0, "azul": 1, "verde": 2}
        return sorted(self._registros, key=lambda p: orden.get(p.prioridad, 9))

    def ordenar_por_distancia(self) -> list["Paquete"]:
        """Ordena de más cercano a más lejano al almacén."""
        return sorted(self._registros, key=lambda p: p.distancia_almacen)

    def total(self) -> int:
        return len(self._registros)

    def peso_total(self) -> float:
        return round(sum(p.peso_kg for p in self._registros), 2)

    def limpiar(self):
        self._registros.clear()

    def mostrar(self, encabezado: bool = True):
        """Imprime la tabla en consola en formato legible."""
        if encabezado:
            print(f"\n{'─'*65}")
            print(f"  TABLA: Paquetes Iniciales ({self.total()} registros)")
            print(f"{'─'*65}")
            print(f"  {'ID':<10} {'Peso':>6} {'Tipo':<15} {'Ubic':>10} {'Prior':<8}")
            print(f"{'─'*65}")
        for p in self._registros:
            print(
                f"  {p.id:<10} {p.peso_kg:>5}kg {p.tipo:<15} "
                f"({p.coord_x},{p.coord_y}){'':<4} {p.prioridad.upper():<8}"
            )

    def to_list(self) -> list[dict]:
        return [p.to_dict() for p in self._registros]


# ==============================================================================
# TABLA PAQUETES ENTREGADOS
# ==============================================================================

class TablaEntregados:
    """
    Registra los paquetes seleccionados para entrega y su asignación.

    Uso:
        tabla = TablaEntregados()
        tabla.registrar(paquete, vehiculo, ruta_id="Ruta-M1")
        tabla.marcar_entregado("PKG-001")
    """

    _ruta_counter: int = 1

    def __init__(self):
        self._registros: list[RegistroEntregado] = []

    def registrar(
        self,
        paquete:  "Paquete",
        vehiculo: "Vehiculo",
        ruta_id:  str = "",
    ) -> RegistroEntregado:
        """
        Registra la asignación de un paquete a un vehículo.

        Args:
            paquete  : Objeto Paquete asignado.
            vehiculo : Objeto Vehiculo que lo transporta.
            ruta_id  : Identificador de ruta (se genera si está vacío).

        Returns:
            RegistroEntregado creado.
        """
        if not ruta_id:
            ruta_id = f"Ruta-{vehiculo.id}-{TablaEntregados._ruta_counter:02d}"
            TablaEntregados._ruta_counter += 1

        reg = RegistroEntregado(
            paquete_id   = paquete.id,
            vehiculo_id  = vehiculo.id,
            vehiculo_nom = vehiculo.nombre,
            ruta_id      = ruta_id,
            distancia_km = paquete.distancia_almacen,
        )
        self._registros.append(reg)
        return reg

    def marcar_entregado(self, paquete_id: str):
        """Cambia el estado de un paquete a 'Entregado'."""
        for r in self._registros:
            if r.paquete_id == paquete_id:
                r.estado = "Entregado"
                return

    def marcar_todos_entregados(self):
        for r in self._registros:
            r.estado = "Entregado"

    def todos(self) -> list[RegistroEntregado]:
        return list(self._registros)

    def en_ruta(self) -> list[RegistroEntregado]:
        return [r for r in self._registros if r.estado == "En ruta"]

    def completados(self) -> list[RegistroEntregado]:
        return [r for r in self._registros if r.estado == "Entregado"]

    def total(self) -> int:
        return len(self._registros)

    def distancia_total(self) -> float:
        return round(sum(r.distancia_km for r in self._registros), 2)

    def vehiculos_usados(self) -> set[str]:
        return {r.vehiculo_id for r in self._registros}

    def limpiar(self):
        self._registros.clear()
        TablaEntregados._ruta_counter = 1

    def mostrar(self):
        print(f"\n{'─'*72}")
        print(f"  TABLA: Paquetes Entregados ({self.total()} registros)")
        print(f"{'─'*72}")
        print(f"  {'ID':<10} {'Vehículo':<20} {'Ruta':<18} {'Dist':>6} {'Estado':<12}")
        print(f"{'─'*72}")
        for r in self._registros:
            print(
                f"  {r.paquete_id:<10} {r.vehiculo_nom:<20} {r.ruta_id:<18} "
                f"{r.distancia_km:>5}km {r.estado:<12}"
            )

    def to_list(self) -> list[dict]:
        return [r.to_dict() for r in self._registros]


# ==============================================================================
# TABLA PAQUETES CONSERVADOS
# ==============================================================================

class TablaConservados:
    """
    Registra los paquetes que NO fueron enviados y el motivo.

    Estos paquetes se transfieren al día siguiente como pendientes.

    Uso:
        tabla = TablaConservados()
        tabla.registrar(paquete, "muy_lejos")
    """

    def __init__(self):
        self._registros: list[RegistroConservado] = []

    def registrar(self, paquete: "Paquete", razon_clave: str) -> RegistroConservado:
        """
        Registra un paquete conservado.

        Args:
            paquete    : Objeto Paquete no enviado.
            razon_clave: Clave del motivo (ver RAZONES_CONSERVACION).

        Returns:
            RegistroConservado creado.
        """
        if razon_clave not in RAZONES_CONSERVACION:
            razon_clave = "sin_vehiculo"

        paquete.estado = "conservado"

        reg = RegistroConservado(
            paquete_id   = paquete.id,
            razon_clave  = razon_clave,
            distancia_km = paquete.distancia_almacen,
            prioridad    = paquete.prioridad,
        )
        self._registros.append(reg)
        return reg

    def todos(self) -> list[RegistroConservado]:
        return list(self._registros)

    def por_razon(self, razon_clave: str) -> list[RegistroConservado]:
        return [r for r in self._registros if r.razon_clave == razon_clave]

    def por_prioridad(self, prioridad: str) -> list[RegistroConservado]:
        return [r for r in self._registros if r.prioridad == prioridad]

    def total(self) -> int:
        return len(self._registros)

    def ids_conservados(self) -> list[str]:
        """Lista de IDs para transferir al siguiente día."""
        return [r.paquete_id for r in self._registros]

    def limpiar(self):
        self._registros.clear()

    def mostrar(self):
        print(f"\n{'─'*68}")
        print(f"  TABLA: Paquetes Conservados ({self.total()} registros)")
        print(f"{'─'*68}")
        print(f"  {'ID':<10} {'Razón':<28} {'Dist':>6} {'Prioridad':<10}")
        print(f"{'─'*68}")
        for r in self._registros:
            print(
                f"  {r.paquete_id:<10} {r.razon_texto:<28} "
                f"{r.distancia_km:>5}km {r.prioridad.upper():<10}"
            )

    def to_list(self) -> list[dict]:
        return [r.to_dict() for r in self._registros]


# ==============================================================================
# RESUMEN SEMANAL
# ==============================================================================

class ResumenSemanal:
    """
    Acumula estadísticas por día de la semana.
    Los datos se mantienen en memoria y se eliminan al cerrar el sistema.

    Uso:
        semanal = ResumenSemanal()
        semanal.registrar_dia("Lunes", iniciales=30, entregados=22, ...)
        semanal.mostrar()
    """

    def __init__(self):
        self._dias: dict[str, RegistroDiaSemanal] = {
            dia: RegistroDiaSemanal(dia=dia) for dia in DIAS_SEMANA
        }

    def registrar_dia(
        self,
        dia:              str,
        iniciales:        int,
        entregados:       int,
        conservados:      int,
        distancia_km:     float,
        combustible_l:    float,
        vehiculos_usados: int,
    ):
        """
        Guarda o sobreescribe las estadísticas de un día.

        Args:
            dia              : Nombre del día (ej. "Lunes").
            iniciales        : Paquetes disponibles al inicio.
            entregados       : Paquetes enviados.
            conservados      : Paquetes pendientes para mañana.
            distancia_km     : Distancia total recorrida.
            combustible_l    : Litros de combustible consumidos.
            vehiculos_usados : Cantidad de vehículos usados ese día.
        """
        if dia not in self._dias:
            raise ValueError(f"Día inválido: '{dia}'. Usa uno de: {DIAS_SEMANA}")

        self._dias[dia] = RegistroDiaSemanal(
            dia              = dia,
            iniciales        = iniciales,
            entregados       = entregados,
            conservados      = conservados,
            distancia_km     = distancia_km,
            combustible_l    = combustible_l,
            vehiculos_usados = vehiculos_usados,
        )

    def dia(self, nombre: str) -> Optional[RegistroDiaSemanal]:
        return self._dias.get(nombre)

    def dias_activos(self) -> list[RegistroDiaSemanal]:
        """Días que tienen datos registrados."""
        return [d for d in self._dias.values() if d.activo]

    # ------------------------------------------------------------------
    # TOTALES SEMANALES
    # ------------------------------------------------------------------

    def total_iniciales(self) -> int:
        return sum(d.iniciales for d in self._dias.values())

    def total_entregados(self) -> int:
        return sum(d.entregados for d in self._dias.values())

    def total_conservados(self) -> int:
        return sum(d.conservados for d in self._dias.values())

    def total_distancia(self) -> float:
        return round(sum(d.distancia_km for d in self._dias.values()), 2)

    def total_combustible(self) -> float:
        return round(sum(d.combustible_l for d in self._dias.values()), 2)

    def eficiencia_semanal(self) -> float:
        total = self.total_iniciales()
        if total == 0:
            return 0.0
        return round((self.total_entregados() / total) * 100, 1)

    def mejor_dia(self) -> Optional[RegistroDiaSemanal]:
        """Día con mayor eficiencia de entregas."""
        activos = self.dias_activos()
        if not activos:
            return None
        return max(activos, key=lambda d: d.eficiencia_pct)

    # ------------------------------------------------------------------
    # VISUALIZACIÓN
    # ------------------------------------------------------------------

    def mostrar(self):
        """Imprime el resumen semanal completo en consola."""
        print(f"\n{'═'*82}")
        print(f"  RESUMEN SEMANAL")
        print(f"{'═'*82}")
        header = f"  {'Métrica':<22}"
        for dia in DIAS_SEMANA:
            header += f" {dia[:3]:>8}"
        print(header)
        print(f"{'─'*82}")

        metricas = [
            ("Iniciales",        lambda d: str(d.iniciales)),
            ("Entregados",       lambda d: str(d.entregados)),
            ("Conservados",      lambda d: str(d.conservados)),
            ("Distancia (km)",   lambda d: f"{d.distancia_km:.1f}"),
            ("Combustible (L)",  lambda d: f"{d.combustible_l:.1f}"),
            ("Eficiencia (%)",   lambda d: f"{d.eficiencia_pct:.0f}%"),
        ]

        for nombre, fn in metricas:
            fila = f"  {nombre:<22}"
            for dia in DIAS_SEMANA:
                reg = self._dias[dia]
                valor = fn(reg) if reg.activo else "—"
                fila += f" {valor:>8}"
            print(fila)

        print(f"{'─'*82}")
        print(f"  Eficiencia semanal: {self.eficiencia_semanal()}% | "
              f"Distancia total: {self.total_distancia()} km | "
              f"Combustible total: {self.total_combustible()} L")

    def limpiar(self):
        """Borra todos los datos (cierre del sistema)."""
        for dia in DIAS_SEMANA:
            self._dias[dia] = RegistroDiaSemanal(dia=dia)

    def to_dict(self) -> dict:
        return {
            "dias":               [d.to_dict() for d in self._dias.values()],
            "total_iniciales":    self.total_iniciales(),
            "total_entregados":   self.total_entregados(),
            "total_conservados":  self.total_conservados(),
            "total_distancia_km": self.total_distancia(),
            "total_combustible_l":self.total_combustible(),
            "eficiencia_pct":     self.eficiencia_semanal(),
        }


# ==============================================================================
# GESTOR CENTRAL
# ==============================================================================

class GestorTablas:
    """
    Coordinador de todas las tablas del sistema.
    Punto único de acceso para el módulo PPAlgoritmos.

    Uso:
        tablas = GestorTablas()
        tablas.cargar_iniciales(paquetes)
        tablas.registrar_entrega(paquete, vehiculo)
        tablas.registrar_conservado(paquete, "muy_lejos")
        tablas.cerrar_dia("Lunes", flota)
    """

    def __init__(self):
        self.iniciales  = TablaIniciales()
        self.entregados = TablaEntregados()
        self.conservados = TablaConservados()
        self.semanal    = ResumenSemanal()

    # ------------------------------------------------------------------
    # OPERACIONES DEL DÍA
    # ------------------------------------------------------------------

    def cargar_iniciales(
        self,
        paquetes_nuevos:     list["Paquete"],
        paquetes_pendientes: list["Paquete"] | None = None,
    ):
        """Carga la tabla de paquetes iniciales."""
        self.iniciales.cargar(paquetes_nuevos, paquetes_pendientes)

    def registrar_entrega(
        self,
        paquete:  "Paquete",
        vehiculo: "Vehiculo",
        ruta_id:  str = "",
    ) -> RegistroEntregado:
        """Registra un paquete como asignado para entrega."""
        return self.entregados.registrar(paquete, vehiculo, ruta_id)

    def registrar_conservado(
        self,
        paquete:     "Paquete",
        razon_clave: str,
    ) -> RegistroConservado:
        """Registra un paquete como conservado (no enviado)."""
        return self.conservados.registrar(paquete, razon_clave)

    def cerrar_dia(self, dia: str, flota: "FlotaVehiculos" = None):
        """
        Consolida las estadísticas del día en el resumen semanal.

        Args:
            dia   : Nombre del día que se cierra.
            flota : Objeto FlotaVehiculos para obtener distancias y combustible.
        """
        distancia   = self.entregados.distancia_total()
      
