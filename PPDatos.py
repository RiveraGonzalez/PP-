"""
PPDatos.py
==========
Módulo de memoria dinámica temporal para el Sistema Inteligente de Gestión
y Optimización de Entregas.

Responsabilidades:
- Guardar datos temporalmente durante la semana
- Administrar información semanal (paquetes, rutas, vehículos, estadísticas)
- Borrar datos al cerrar el sistema
"""

import json
import os
from datetime import datetime

# ─────────────────────────────────────────────
# CONSTANTES
# ─────────────────────────────────────────────

DIAS_SEMANA = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

TIPOS_PAQUETE = {
    "Bolsa pequeña": {"largo": 0.3, "ancho": 0.2, "alto": 0.1, "volumen": 0.006},
    "Caja chica":    {"largo": 0.4, "ancho": 0.3, "alto": 0.3, "volumen": 0.036},
    "Caja mediana":  {"largo": 0.6, "ancho": 0.5, "alto": 0.4, "volumen": 0.120},
    "Caja grande":   {"largo": 1.0, "ancho": 0.8, "alto": 0.6, "volumen": 0.480},
}

PRIORIDADES = {
    "Verde": {"label": "Baja",      "dias_max": 7,  "urgencia": 1},
    "Azul":  {"label": "Media",     "dias_max": 3,  "urgencia": 2},
    "Rojo":  {"label": "Inmediata", "dias_max": 0,  "urgencia": 3},
}

VEHICULOS_CONFIG = {
    "Moto": {
        "cantidad":        3,
        "capacidad_kg":    15,
        "volumen_m3":      0.05,
        "distancia_max_km":20,
        "combustible_km_l":40,
        "velocidad_kmh":   60,
        "costo_km":        1.5,
    },
    "Camioneta chica": {
        "cantidad":        2,
        "capacidad_kg":    500,
        "volumen_m3":      2.0,
        "distancia_max_km":80,
        "combustible_km_l":12,
        "velocidad_kmh":   80,
        "costo_km":        4.0,
    },
    "Camioneta grande": {
        "cantidad":        1,
        "capacidad_kg":    2000,
        "volumen_m3":      10.0,
        "distancia_max_km":200,
        "combustible_km_l":8,
        "velocidad_kmh":   90,
        "costo_km":        7.0,
    },
}

# ─────────────────────────────────────────────
# CLASE PRINCIPAL DE DATOS
# ─────────────────────────────────────────────

class DatosSistema:
    """
    Almacena y gestiona toda la memoria temporal del sistema durante la semana.
    Los datos se pierden al cerrar la aplicación (no hay persistencia en disco
    salvo exportación explícita).
    """

    def __init__(self):
        self._reiniciar_todo()

    # ── Inicialización ─────────────────────────────

    def _reiniciar_todo(self):
        """Crea la estructura de datos vacía."""
        self._contador_paquetes = 0          # autoincremental para IDs
        self._dia_actual: str = ""           # día de trabajo activo
        self._actividad_dia: str = ""        # "Registrar paquetes" | "Realizar entregas" | "Ambas"

        # Listas principales
        self._paquetes_iniciales: list[dict] = []   # todos los paquetes del día
        self._paquetes_entregados: list[dict] = []  # asignados a rutas y entregados
        self._paquetes_conservados: list[dict] = [] # no enviados

        # Vehículos: copia de trabajo con estado mutable
        self._vehiculos: dict = self._inicializar_vehiculos()

        # Rutas generadas por los algoritmos
        self._rutas: list[dict] = []

        # Resumen semanal: lista de dicts por día
        self._resumen_semanal: list[dict] = []

        # Estadísticas del día actual
        self._estadisticas_dia: dict = {
            "combustible_total_l": 0.0,
            "distancia_total_km":  0.0,
            "costo_total":         0.0,
            "tiempo_total_h":      0.0,
        }

    def _inicializar_vehiculos(self) -> dict:
        """Crea instancias de vehículos basadas en la configuración."""
        vehiculos = {}
        for tipo, cfg in VEHICULOS_CONFIG.items():
            for i in range(1, cfg["cantidad"] + 1):
                vid = f"{tipo} {i}"
                vehiculos[vid] = {
                    "tipo":             tipo,
                    "id":               vid,
                    "capacidad_kg":     cfg["capacidad_kg"],
                    "volumen_m3":       cfg["volumen_m3"],
                    "distancia_max_km": cfg["distancia_max_km"],
                    "combustible_km_l": cfg["combustible_km_l"],
                    "velocidad_kmh":    cfg["velocidad_kmh"],
                    "costo_km":         cfg["costo_km"],
                    # Estado dinámico
                    "peso_actual_kg":   0.0,
                    "volumen_actual_m3":0.0,
                    "paquetes":         [],
                    "disponible":       True,
                    "distancia_recorrida_km": 0.0,
                }
        return vehiculos

    # ── Día de trabajo ─────────────────────────────

    def iniciar_dia(self, dia: str, actividad: str):
        """Configura el día de trabajo. Reinicia los datos del día anterior."""
        if dia not in DIAS_SEMANA:
            raise ValueError(f"Día inválido: {dia}. Opciones: {DIAS_SEMANA}")
        opciones_actividad = ["Registrar paquetes", "Realizar entregas", "Ambas"]
        if actividad not in opciones_actividad:
            raise ValueError(f"Actividad inválida. Opciones: {opciones_actividad}")

        # Guardar resumen del día anterior si existe
        if self._dia_actual:
            self._guardar_resumen_dia()

        # Reiniciar estado del día (pero conservar semana y conservados)
        conservados_anteriores = list(self._paquetes_conservados)
        self._paquetes_iniciales  = list(conservados_anteriores)  # pasan al siguiente día
        self._paquetes_entregados = []
        self._paquetes_conservados = []
        self._vehiculos = self._inicializar_vehiculos()
        self._rutas = []
        self._estadisticas_dia = {
            "combustible_total_l": 0.0,
            "distancia_total_km":  0.0,
            "costo_total":         0.0,
            "tiempo_total_h":      0.0,
        }
        self._dia_actual   = dia
        self._actividad_dia = actividad

    def get_dia_actual(self) -> str:
        return self._dia_actual

    def get_actividad_dia(self) -> str:
        return self._actividad_dia

    # ── Paquetes ───────────────────────────────────

    def generar_id_paquete(self) -> str:
        self._contador_paquetes += 1
        return f"PKG-{self._contador_paquetes:03d}"

    def registrar_paquete(
        self,
        tipo: str,
        peso_kg: float,
        prioridad: str,
        coord_x: float,
        coord_y: float,
    ) -> dict:
        """
        Crea y registra un nuevo paquete.
        Retorna el dict del paquete creado.
        """
        if tipo not in TIPOS_PAQUETE:
            raise ValueError(f"Tipo de paquete inválido: {tipo}")
        if prioridad not in PRIORIDADES:
            raise ValueError(f"Prioridad inválida: {prioridad}")
        if peso_kg <= 0:
            raise ValueError("El peso debe ser mayor a 0.")

        dims = TIPOS_PAQUETE[tipo]
        paquete = {
            "id":        self.generar_id_paquete(),
            "tipo":      tipo,
            "peso_kg":   round(peso_kg, 2),
            "prioridad": prioridad,
            "urgencia":  PRIORIDADES[prioridad]["urgencia"],
            "coord_x":   coord_x,
            "coord_y":   coord_y,
            "largo_m":   dims["largo"],
            "ancho_m":   dims["ancho"],
            "alto_m":    dims["alto"],
            "volumen_m3":dims["volumen"],
            "estado":    "pendiente",   # pendiente | asignado | entregado | conservado
            "vehiculo_asignado": None,
            "ruta_asignada":     None,
            "distancia_almacen_km": round(
                (coord_x**2 + coord_y**2) ** 0.5, 4
            ),
            "fecha_registro": datetime.now().strftime("%H:%M:%S"),
            "dia_registro":   self._dia_actual,
        }
        self._paquetes_iniciales.append(paquete)
        return paquete

    def get_paquetes_iniciales(self) -> list[dict]:
        return list(self._paquetes_iniciales)

    def get_paquetes_pendientes(self) -> list[dict]:
        """Paquetes que aún no han sido asignados ni descartados."""
        return [p for p in self._paquetes_iniciales if p["estado"] == "pendiente"]

    def get_paquetes_entregados(self) -> list[dict]:
        return list(self._paquetes_entregados)

    def get_paquetes_conservados(self) -> list[dict]:
        return list(self._paquetes_conservados)

    def marcar_entregado(self, paquete_id: str, vehiculo_id: str, ruta_id: str, distancia_km: float):
        """Mueve un paquete al registro de entregados."""
        paquete = self._buscar_paquete(paquete_id)
        paquete["estado"]            = "entregado"
        paquete["vehiculo_asignado"] = vehiculo_id
        paquete["ruta_asignada"]     = ruta_id
        paquete["distancia_ruta_km"] = round(distancia_km, 4)
        if paquete not in self._paquetes_entregados:
            self._paquetes_entregados.append(paquete)

    def marcar_conservado(self, paquete_id: str, razon: str):
        """Mueve un paquete al registro de conservados (no enviados)."""
        razones_validas = [
            "muy lejos", "baja prioridad", "exceso de peso",
            "falta de espacio", "baja eficiencia logística",
        ]
        paquete = self._buscar_paquete(paquete_id)
        paquete["estado"] = "conservado"
        paquete["razon_conservado"] = razon
        if paquete not in self._paquetes_conservados:
            self._paquetes_conservados.append(paquete)

    def _buscar_paquete(self, paquete_id: str) -> dict:
        for p in self._paquetes_iniciales:
            if p["id"] == paquete_id:
                return p
        raise KeyError(f"Paquete no encontrado: {paquete_id}")

    # ── Vehículos ──────────────────────────────────

    def get_vehiculos(self) -> dict:
        return dict(self._vehiculos)

    def get_vehiculos_disponibles(self) -> dict:
        return {vid: v for vid, v in self._vehiculos.items() if v["disponible"]}

    def asignar_paquete_vehiculo(self, vehiculo_id: str, paquete_id: str):
        """Asigna un paquete a un vehículo y actualiza su carga."""
        if vehiculo_id not in self._vehiculos:
            raise KeyError(f"Vehículo no encontrado: {vehiculo_id}")
        paquete  = self._buscar_paquete(paquete_id)
        vehiculo = self._vehiculos[vehiculo_id]

        # Validar capacidad
        if vehiculo["peso_actual_kg"] + paquete["peso_kg"] > vehiculo["capacidad_kg"]:
            raise ValueError(
                f"Excede capacidad de peso del vehículo {vehiculo_id}. "
                f"Disponible: {vehiculo['capacidad_kg'] - vehiculo['peso_actual_kg']:.1f} kg"
            )
        if vehiculo["volumen_actual_m3"] + paquete["volumen_m3"] > vehiculo["volumen_m3"]:
            raise ValueError(f"Excede capacidad de volumen del vehículo {vehiculo_id}.")

        vehiculo["peso_actual_kg"]    += paquete["peso_kg"]
        vehiculo["volumen_actual_m3"] += paquete["volumen_m3"]
        vehiculo["paquetes"].append(paquete_id)

    def registrar_ruta_vehiculo(self, vehiculo_id: str, distancia_km: float):
        """Actualiza la distancia recorrida y calcula combustible/costo del vehículo."""
        vehiculo = self._vehiculos[vehiculo_id]
        vehiculo["distancia_recorrida_km"] += distancia_km
        combustible = distancia_km / vehiculo["combustible_km_l"]
        costo       = distancia_km * vehiculo["costo_km"]
        tiempo_h    = distancia_km / vehiculo["velocidad_kmh"]

        self._estadisticas_dia["combustible_total_l"] += combustible
        self._estadisticas_dia["distancia_total_km"]  += distancia_km
        self._estadisticas_dia["costo_total"]         += costo
        self._estadisticas_dia["tiempo_total_h"]      += tiempo_h

    def liberar_vehiculo(self, vehiculo_id: str):
        """Marca el vehículo como disponible de nuevo."""
        self._vehiculos[vehiculo_id]["disponible"] = True

    # ── Rutas ──────────────────────────────────────

    def registrar_ruta(self, ruta: dict):
        """
        Guarda una ruta generada por los algoritmos.
        Estructura esperada:
        {
            "id":          str,
            "vehiculo_id": str,
            "paquetes":    [str],   # lista de IDs
            "orden_visita":[str],   # IDs en orden de entrega
            "distancia_km":float,
            "fitness":     float,
        }
        """
        self._rutas.append(ruta)

    def get_rutas(self) -> list[dict]:
        return list(self._rutas)

    # ── Resumen semanal ────────────────────────────

    def _guardar_resumen_dia(self):
        """Calcula y almacena el resumen del día actual en el historial semanal."""
        if not self._dia_actual:
            return
        entrada = {
            "dia":                 self._dia_actual,
            "iniciales":           len(self._paquetes_iniciales),
            "entregados":          len(self._paquetes_entregados),
            "conservados":         len(self._paquetes_conservados),
            "combustible_l":       round(self._estadisticas_dia["combustible_total_l"], 2),
            "distancia_km":        round(self._estadisticas_dia["distancia_total_km"],  2),
            "costo_total":         round(self._estadisticas_dia["costo_total"],          2),
            "tiempo_total_h":      round(self._estadisticas_dia["tiempo_total_h"],       2),
            "rutas_generadas":     len(self._rutas),
            "eficiencia_pct":      round(
                len(self._paquetes_entregados) / max(len(self._paquetes_iniciales), 1) * 100, 1
            ),
        }
        self._resumen_semanal.append(entrada)

    def cerrar_dia(self):
        """Cierra el día activo y guarda su resumen."""
        self._guardar_resumen_dia()

    def get_resumen_semanal(self) -> list[dict]:
        return list(self._resumen_semanal)

    def get_estadisticas_dia(self) -> dict:
        return dict(self._estadisticas_dia)

    # ── Exportación / Borrado ──────────────────────

    def exportar_json(self, ruta_archivo: str):
        """Exporta todos los datos actuales a un archivo JSON."""
        datos = {
            "exportado_en":       datetime.now().isoformat(),
            "dia_actual":         self._dia_actual,
            "paquetes_iniciales": self._paquetes_iniciales,
            "paquetes_entregados":self._paquetes_entregados,
            "paquetes_conservados":self._paquetes_conservados,
            "rutas":              self._rutas,
            "resumen_semanal":    self._resumen_semanal,
            "estadisticas_dia":   self._estadisticas_dia,
        }
        with open(ruta_archivo, "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False, indent=2)

    def borrar_todo(self):
        """Elimina todos los datos (se llama al cerrar el sistema)."""
        self._reiniciar_todo()
        print("[PPDatos] Todos los datos han sido eliminados.")

    # ── Utilidades de consulta ─────────────────────

    def resumen_rapido(self) -> str:
        """Retorna un string con el estado actual del sistema."""
        lines = [
            f"Día: {self._dia_actual or 'Sin iniciar'}",
            f"Actividad: {self._actividad_dia or '-'}",
            f"Paquetes iniciales : {len(self._paquetes_iniciales)}",
            f"Paquetes entregados: {len(self._paquetes_entregados)}",
            f"Paquetes conservados: {len(self._paquetes_conservados)}",
            f"Rutas generadas    : {len(self._rutas)}",
            f"Distancia total    : {self._estadisticas_dia['distancia_total_km']:.1f} km",
            f"Combustible        : {self._estadisticas_dia['combustible_total_l']:.2f} L",
        ]
        return "\n".join(lines)


# ─────────────────────────────────────────────
# INSTANCIA GLOBAL (singleton)
# ─────────────────────────────────────────────

datos = DatosSistema()


# ─────────────────────────────────────────────
# DEMO / TEST BÁSICO
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("=== PRUEBA DE PPDatos.py ===\n")

    datos.iniciar_dia("Lunes", "Ambas")

    p1 = datos.registrar_paquete("Caja chica",   5.0,  "Rojo",   4, 7)
    p2 = datos.registrar_paquete("Bolsa pequeña",1.5,  "Verde",  2, 3)
    p3 = datos.registrar_paquete("Caja mediana", 12.0, "Azul",  -5, 6)
    p4 = datos.registrar_paquete("Caja grande",  50.0, "Verde",  30, 30)

    print("Paquetes registrados:")
    for p in datos.get_paquetes_iniciales():
        print(f"  {p['id']} | {p['tipo']} | {p['peso_kg']}kg | {p['prioridad']} | ({p['coord_x']},{p['coord_y']})")

    datos.asignar_paquete_vehiculo("Moto 1", p1["id"])
    datos.marcar_entregado(p1["id"], "Moto 1", "RUTA-001", 8.6)

    datos.marcar_conservado(p4["id"], "muy lejos")

    datos.registrar_ruta_vehiculo("Moto 1", 8.6)

    print("\n" + datos.resumen_rapido())

    datos.cerrar_dia()
    print("\nResumen semanal:", datos.get_resumen_semanal())
