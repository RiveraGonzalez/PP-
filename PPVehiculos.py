"""
PPVehiculos.py
==============
Lógica completa de la flota de vehículos del sistema de entregas.

Módulos:
    - Vehiculo          : Clase base con atributos y validaciones
    - Moto              : Subclase especializada para motos
    - CamionetaChica    : Subclase para camionetas medianas
    - CamionetaGrande   : Subclase para camioneta de carga
    - FlotaVehiculos    : Gestor de toda la flota

Proyecto: Sistema Inteligente de Gestión y Optimización de Entregas
Materia : Algoritmos Metaheurísticos
"""

from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING
from enum import Enum

if TYPE_CHECKING:
    from PPFormularios import Paquete


# ==============================================================================
# ENUMERACIONES
# ==============================================================================

class TipoVehiculo(Enum):
    MOTO           = "moto"
    CAMIONETA_CHICA  = "chica"
    CAMIONETA_GRANDE = "grande"


class EstadoVehiculo(Enum):
    DISPONIBLE = "disponible"
    EN_RUTA    = "en_ruta"
    LLENO      = "lleno"


# ==============================================================================
# CLASE BASE: VEHÍCULO
# ==============================================================================

@dataclass
class Vehiculo:
    """
    Clase base que representa un vehículo de la flota.

    Atributos:
        id              : Identificador único (ej. "M1", "CC2").
        nombre          : Nombre descriptivo (ej. "Moto 1").
        tipo            : Categoría del vehículo (TipoVehiculo).
        capacidad_kg    : Carga máxima en kilogramos.
        dist_max_km     : Distancia máxima por jornada en km.
        consumo_litros  : Consumo de combustible por ruta (litros).
        velocidad_kmh   : Velocidad promedio en km/h.
        vol_max_m3      : Volumen máximo de carga en m³.
    """
    id:             str
    nombre:         str
    tipo:           str
    capacidad_kg:   float
    dist_max_km:    float
    consumo_litros: float
    velocidad_kmh:  float
    vol_max_m3:     float

    # Estado dinámico (no se pasan al constructor)
    _carga_actual_kg:  float = field(default=0.0,  init=False, repr=False)
    _vol_actual_m3:    float = field(default=0.0,  init=False, repr=False)
    _dist_recorrida:   float = field(default=0.0,  init=False, repr=False)
    _paquetes:         list  = field(default_factory=list, init=False, repr=False)
    _estado:           str   = field(default=EstadoVehiculo.DISPONIBLE.value, init=False, repr=False)

    # ------------------------------------------------------------------
    # PROPIEDADES DE ESTADO
    # ------------------------------------------------------------------

    @property
    def carga_actual_kg(self) -> float:
        return round(self._carga_actual_kg, 2)

    @property
    def vol_actual_m3(self) -> float:
        return round(self._vol_actual_m3, 4)

    @property
    def dist_recorrida(self) -> float:
        return round(self._dist_recorrida, 2)

    @property
    def paquetes_asignados(self) -> list:
        return list(self._paquetes)

    @property
    def estado(self) -> str:
        return self._estado

    @property
    def disponible(self) -> bool:
        return self._estado == EstadoVehiculo.DISPONIBLE.value

    # ------------------------------------------------------------------
    # CAPACIDAD RESTANTE
    # ------------------------------------------------------------------

    @property
    def capacidad_restante_kg(self) -> float:
        return round(self.capacidad_kg - self._carga_actual_kg, 2)

    @property
    def vol_restante_m3(self) -> float:
        return round(self.vol_max_m3 - self._vol_actual_m3, 4)

    @property
    def dist_restante_km(self) -> float:
        return round(self.dist_max_km - self._dist_recorrida, 2)

    @property
    def porcentaje_carga(self) -> float:
        """Porcentaje de carga utilizado (0–100)."""
        if self.capacidad_kg == 0:
            return 0.0
        return round((self._carga_actual_kg / self.capacidad_kg) * 100, 1)

    # ------------------------------------------------------------------
    # VALIDACIONES
    # ------------------------------------------------------------------

    def puede_cargar(self, paquete: "Paquete") -> tuple[bool, str]:
        """
        Verifica si el vehículo puede aceptar un paquete adicional.

        Returns:
            (True, "") si puede cargar.
            (False, motivo) si no puede.
        """
        if not self.disponible:
            return False, f"{self.nombre} no está disponible (estado: {self._estado})."

        distancia_pkg = paquete.distancia_almacen
        if distancia_pkg > self.dist_restante_km:
            return False, (
                f"Distancia del paquete ({distancia_pkg} km) supera "
                f"el alcance restante ({self.dist_restante_km} km)."
            )

        if paquete.peso_kg > self.capacidad_restante_kg:
            return False, (
                f"Peso del paquete ({paquete.peso_kg} kg) supera "
                f"la capacidad restante ({self.capacidad_restante_kg} kg)."
            )

        if paquete.volumen_m3 > self.vol_restante_m3:
            return False, (
                f"Volumen del paquete ({paquete.volumen_m3} m³) supera "
                f"el volumen restante ({self.vol_restante_m3} m³)."
            )

        return True, ""

    # ------------------------------------------------------------------
    # ASIGNACIÓN Y LIBERACIÓN
    # ------------------------------------------------------------------

    def asignar_paquete(self, paquete: "Paquete") -> bool:
        """
        Asigna un paquete al vehículo si hay capacidad.

        Returns:
            True si fue asignado, False si no.
        """
        puede, motivo = self.puede_cargar(paquete)
        if not puede:
            return False

        self._paquetes.append(paquete)
        self._carga_actual_kg += paquete.peso_kg
        self._vol_actual_m3   += paquete.volumen_m3
        self._dist_recorrida  += paquete.distancia_almacen

        # Actualizar estado
        if self._carga_actual_kg >= self.capacidad_kg * 0.95:
            self._estado = EstadoVehiculo.LLENO.value
        else:
            self._estado = EstadoVehiculo.EN_RUTA.value

        paquete.estado = "entregado"
        return True

    def liberar(self):
        """Resetea el vehículo al finalizar la jornada."""
        self._paquetes.clear()
        self._carga_actual_kg = 0.0
        self._vol_actual_m3   = 0.0
        self._dist_recorrida  = 0.0
        self._estado          = EstadoVehiculo.DISPONIBLE.value

    # ------------------------------------------------------------------
    # CÁLCULOS LOGÍSTICOS
    # ------------------------------------------------------------------

    def tiempo_estimado_horas(self) -> float:
        """Tiempo estimado de ruta basado en velocidad y distancia."""
        if self.velocidad_kmh == 0:
            return 0.0
        return round(self._dist_recorrida / self.velocidad_kmh, 2)

    def combustible_consumido(self) -> float:
        """Litros de combustible consumidos en la ruta actual."""
        if self.dist_max_km == 0:
            return 0.0
        return round((self._dist_recorrida / self.dist_max_km) * self.consumo_litros, 2)

    def fitness_vehiculo(self) -> float:
        """
        Función de aptitud del vehículo para el algoritmo GA.

        f(v) = (paquetes_entregados × peso_promedio) / (distancia + 1)
        Premia entregas eficientes de mayor peso en menor distancia.
        """
        n = len(self._paquetes)
        if n == 0 or self._dist_recorrida == 0:
            return 0.0
        peso_promedio = self._carga_actual_kg / n
        return round((n * peso_promedio) / (self._dist_recorrida + 1), 4)

    # ------------------------------------------------------------------
    # SERIALIZACIÓN
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "id":                  self.id,
            "nombre":              self.nombre,
            "tipo":                self.tipo,
            "estado":              self._estado,
            "capacidad_kg":        self.capacidad_kg,
            "carga_actual_kg":     self.carga_actual_kg,
            "capacidad_restante":  self.capacidad_restante_kg,
            "porcentaje_carga":    self.porcentaje_carga,
            "vol_max_m3":          self.vol_max_m3,
            "vol_actual_m3":       self.vol_actual_m3,
            "dist_max_km":         self.dist_max_km,
            "dist_recorrida_km":   self.dist_recorrida,
            "dist_restante_km":    self.dist_restante_km,
            "velocidad_kmh":       self.velocidad_kmh,
            "consumo_litros":      self.consumo_litros,
            "combustible_usado":   self.combustible_consumido(),
            "tiempo_estimado_h":   self.tiempo_estimado_horas(),
            "paquetes_asignados":  len(self._paquetes),
            "fitness":             self.fitness_vehiculo(),
        }

    def __repr__(self) -> str:
        return (f"{self.nombre} [{self._estado.upper()}] "
                f"Carga: {self.carga_actual_kg}/{self.capacidad_kg} kg "
                f"| Pkgs: {len(self._paquetes)}")


# ==============================================================================
# SUBCLASES ESPECIALIZADAS
# ==============================================================================

class Moto(Vehiculo):
    """
    Moto de reparto — entregas rápidas y ligeras.
    Ideal para paquetes pequeños y rutas cortas.
    """
    CAPACIDAD_KG   = 20.0
    DIST_MAX_KM    = 30.0
    CONSUMO_LITROS = 2.5
    VELOCIDAD_KMH  = 60.0
    VOL_MAX_M3     = 0.3

    def __init__(self, id: str, numero: int):
        super().__init__(
            id             = id,
            nombre         = f"Moto {numero}",
            tipo           = TipoVehiculo.MOTO.value,
            capacidad_kg   = self.CAPACIDAD_KG,
            dist_max_km    = self.DIST_MAX_KM,
            consumo_litros = self.CONSUMO_LITROS,
            velocidad_kmh  = self.VELOCIDAD_KMH,
            vol_max_m3     = self.VOL_MAX_M3,
        )

    def tipos_compatibles(self) -> list[str]:
        """Tipos de paquete que puede transportar una moto."""
        return ["bolsa", "caja-chica"]


class CamionetaChica(Vehiculo):
    """
    Camioneta chica — rutas medianas y carga moderada.
    Equilibrio entre capacidad y agilidad urbana.
    """
    CAPACIDAD_KG   = 300.0
    DIST_MAX_KM    = 80.0
    CONSUMO_LITROS = 10.0
    VELOCIDAD_KMH  = 40.0
    VOL_MAX_M3     = 2.5

    def __init__(self, id: str, numero: int):
        super().__init__(
            id             = id,
            nombre         = f"Camioneta Chica {numero}",
            tipo           = TipoVehiculo.CAMIONETA_CHICA.value,
            capacidad_kg   = self.CAPACIDAD_KG,
            dist_max_km    = self.DIST_MAX_KM,
            consumo_litros = self.CONSUMO_LITROS,
            velocidad_kmh  = self.VELOCIDAD_KMH,
            vol_max_m3     = self.VOL_MAX_M3,
        )

    def tipos_compatibles(self) -> list[str]:
        return ["bolsa", "caja-chica", "caja-mediana"]


class CamionetaGrande(Vehiculo):
    """
    Camioneta grande — cargas pesadas y largas distancias.
    Máxima capacidad de la flota.
    """
    CAPACIDAD_KG   = 1000.0
    DIST_MAX_KM    = 200.0
    CONSUMO_LITROS = 18.0
    VELOCIDAD_KMH  = 30.0
    VOL_MAX_M3     = 10.0

    def __init__(self, id: str, numero: int = 1):
        super().__init__(
            id             = id,
            nombre         = f"Camioneta Grande {numero}",
            tipo           = TipoVehiculo.CAMIONETA_GRANDE.value,
            capacidad_kg   = self.CAPACIDAD_KG,
            dist_max_km    = self.DIST_MAX_KM,
            consumo_litros = self.CONSUMO_LITROS,
            velocidad_kmh  = self.VELOCIDAD_KMH,
            vol_max_m3     = self.VOL_MAX_M3,
        )

    def tipos_compatibles(self) -> list[str]:
        return ["bolsa", "caja-chica", "caja-mediana", "caja-grande"]


# ==============================================================================
# GESTOR DE FLOTA
# ==============================================================================

class FlotaVehiculos:
    """
    Administra todos los vehículos de la flota.

    Flota fija:
        - 3 motos         (M1, M2, M3)
        - 2 cam. chicas   (CC1, CC2)
        - 1 cam. grande   (CG1)

    Uso:
        flota = FlotaVehiculos()
        disponibles = flota.vehiculos_disponibles()
        flota.asignar_mejor_vehiculo(paquete)
    """

    def __init__(self):
        self._flota: list[Vehiculo] = [
            Moto("M1", 1),
            Moto("M2", 2),
            Moto("M3", 3),
            CamionetaChica("CC1", 1),
            CamionetaChica("CC2", 2),
            CamionetaGrande("CG1", 1),
        ]

    # ------------------------------------------------------------------
    # CONSULTAS
    # ------------------------------------------------------------------

    def todos(self) -> list[Vehiculo]:
        return list(self._flota)

    def vehiculos_disponibles(self) -> list[Vehiculo]:
        return [v for v in self._flota if v.disponible]

    def por_tipo(self, tipo: str) -> list[Vehiculo]:
        return [v for v in self._flota if v.tipo == tipo]

    def por_id(self, vid: str) -> Optional[Vehiculo]:
        return next((v for v in self._flota if v.id == vid), None)

    def disponibles_por_tipo(self, tipo: str) -> list[Vehiculo]:
        return [v for v in self._flota if v.tipo == tipo and v.disponible]

    # ------------------------------------------------------------------
    # ASIGNACIÓN INTELIGENTE
    # ------------------------------------------------------------------

    def asignar_mejor_vehiculo(self, paquete: "Paquete") -> Optional[Vehiculo]:
        """
        Selecciona el vehículo más adecuado para el paquete usando
        la heurística: menor tipo que quepa → mayor capacidad restante.

        Prioriza motos para paquetes pequeños, camionetas para grandes.
        Dentro del mismo tipo, prefiere el más cargado (packing eficiente).

        Returns:
            Vehiculo asignado o None si ninguno puede aceptarlo.
        """
        candidatos = []
        for v in self._flota:
            puede, _ = v.puede_cargar(paquete)
            if puede:
                candidatos.append(v)

        if not candidatos:
            return None

        # Ordenar: primero por tipo (moto < chica < grande), luego por carga desc.
        orden_tipo = {
            TipoVehiculo.MOTO.value:           0,
            TipoVehiculo.CAMIONETA_CHICA.value:  1,
            TipoVehiculo.CAMIONETA_GRANDE.value: 2,
        }
        candidatos.sort(key=lambda v: (
            orden_tipo.get(v.tipo, 9),
            -v.carga_actual_kg,       # mayor carga primero (bin-packing)
        ))

        mejor = candidatos[0]
        mejor.asignar_paquete(paquete)
        return mejor

    def asignar_forzado(self, vid: str, paquete: "Paquete") -> tuple[bool, str]:
        """
        Intenta asignar un paquete a un vehículo específico por ID.

        Returns:
            (True, "") si fue exitoso.
            (False, motivo) si falló.
        """
        vehiculo = self.por_id(vid)
        if vehiculo is None:
            return False, f"No existe vehículo con ID '{vid}'."
        puede, motivo = vehiculo.puede_cargar(paquete)
        if not puede:
            return False, motivo
        vehiculo.asignar_paquete(paquete)
        return True, ""

    # ------------------------------------------------------------------
    # FIN DE JORNADA
    # ------------------------------------------------------------------

    def liberar_flota(self):
        """Resetea todos los vehículos al estado disponible."""
        for v in self._flota:
            v.liberar()
        print("[FLOTA] Todos los vehículos liberados.")

    # ------------------------------------------------------------------
    # ESTADÍSTICAS
    # ------------------------------------------------------------------

    def resumen(self) -> dict:
        """Estadísticas globales de la flota."""
        en_ruta = [v for v in self._flota if not v.disponible]
        total_paquetes = sum(len(v.paquetes_asignados) for v in self._flota)
        total_dist     = sum(v.dist_recorrida for v in self._flota)
        total_combust  = sum(v.combustible_consumido() for v in self._flota)
        total_peso     = sum(v.carga_actual_kg for v in self._flota)

        return {
            "total_vehiculos":     len(self._flota),
            "disponibles":         len(self.vehiculos_disponibles()),
            "en_ruta":             len(en_ruta),
            "total_paquetes":      total_paquetes,
            "distancia_total_km":  round(total_dist, 2),
            "combustible_total_L": round(total_combust, 2),
            "carga_total_kg":      round(total_peso, 2),
        }

    def detalle_flota(self) -> list[dict]:
        """Lista serializable con el estado de cada vehículo."""
        return [v.to_dict() for v in self._flota]


# ==============================================================================
# DEMO
# ==============================================================================

if __name__ == "__main__":
    # Importación local solo para la demo
    import sys, os
    sys.path.insert(0, os.path.dirname(__file__))

    print("=" * 60)
    print("  PPVehiculos.py — Demo de prueba")
    print("=" * 60)

    from PPFormularios import GestorFormularios

    gestor = GestorFormularios()
    gestor.iniciar_dia("Martes", "ambas")

    datos = [
        ("bolsa",        0.5, "rojo",   2,  3),
        ("caja-chica",   8.0, "azul",   5,  1),
        ("caja-mediana", 25.0,"rojo",   7,  8),
        ("caja-grande",  95.0,"verde",  15, 10),
        ("caja-grande",  150.0,"azul",  20,  5),
    ]
    paquetes = []
    for t, p, pri, x, y in datos:
        pkg = gestor.registrar_paquete(t, p, pri, x, y)
        paquetes.append(pkg)

    print("\n--- Asignando a la flota ---")
    flota = FlotaVehiculos()
    for pkg in paquetes:
        vehiculo = flota.asignar_mejor_vehiculo(pkg)
        if vehiculo:
            print(f"  ✓ {pkg.id} → {vehiculo.nombre} | Carga: {vehiculo.carga_actual_kg} kg")
        else:
            print(f"  ✗ {pkg.id} → Sin vehículo disponible")

    print("\n--- Estado de la flota ---")
    for v in flota.todos():
        print(f"  {v}")

    print("\n--- Resumen global ---")
    for k, val in flota.resumen().items():
        print(f"  {k}: {val}")
