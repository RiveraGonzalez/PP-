"""
PPAlgoritmos.py
===============
Módulo de algoritmos metaheurísticos para el Sistema Inteligente de Gestión
y Optimización de Entregas.

Algoritmos implementados:
  1. Algoritmo Genético (GA)   — selección de paquetes a entregar y asignación
  2. Colonia de Hormigas (ACO) — generación de rutas óptimas por vehículo

Flujo principal:
  optimizar(datos) → lista de rutas optimizadas
"""

import math
import random
import copy
from typing import Optional

# Se importa el módulo de datos para usar sus constantes y poder hacer pruebas
# independientes.  En el programa principal PPFormularios.py importará ambos.
try:
    from PPDatos import (
        DatosSistema,
        PRIORIDADES,
        VEHICULOS_CONFIG,
        datos as _datos_global,
    )
except ImportError:
    # Permite ejecutar el archivo de forma aislada para pruebas
    DatosSistema = None
    PRIORIDADES = {
        "Verde": {"urgencia": 1},
        "Azul":  {"urgencia": 2},
        "Rojo":  {"urgencia": 3},
    }
    VEHICULOS_CONFIG = {}
    _datos_global = None


# ─────────────────────────────────────────────
# UTILIDADES COMUNES
# ─────────────────────────────────────────────

def distancia_euclidea(x1: float, y1: float, x2: float, y2: float) -> float:
    """Distancia euclidea entre dos puntos en el plano cartesiano."""
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


def distancia_ruta(puntos: list[tuple]) -> float:
    """
    Calcula la distancia total de una ruta que parte del almacén (0,0),
    visita todos los puntos en orden y regresa al almacén.

    puntos: lista de (x, y)
    """
    if not puntos:
        return 0.0
    total = distancia_euclidea(0, 0, puntos[0][0], puntos[0][1])
    for i in range(len(puntos) - 1):
        total += distancia_euclidea(
            puntos[i][0], puntos[i][1],
            puntos[i + 1][0], puntos[i + 1][1],
        )
    total += distancia_euclidea(puntos[-1][0], puntos[-1][1], 0, 0)
    return round(total, 4)


# ─────────────────────────────────────────────
# ALGORITMO GENÉTICO (GA)
# ─────────────────────────────────────────────
# Objetivo: dado un conjunto de paquetes y vehículos,
# decide QUÉ paquetes se entregan y a QUÉ vehículo se
# asigna cada uno maximizando el fitness global.

class AlgoritmoGenetico:
    """
    Representación del cromosoma:
        Una lista de longitud N (número de paquetes).
        Cada gen es un entero:
          -1  → paquete conservado (no se entrega hoy)
          0..M-1 → índice del vehículo al que se asigna

    Fitness:
        + puntos por urgencia de los paquetes entregados
        - penalización por distancia extra
        - penalización si se excede la capacidad del vehículo
    """

    # ── Parámetros por defecto ─────────────────────
    POBLACION_TAM    = 60
    GENERACIONES     = 150
    PROB_CRUCE       = 0.80
    PROB_MUTACION    = 0.15
    ELITISMO_FRAC    = 0.10   # fracción de la población que pasa directa
    TORNEO_K         = 3      # tamaño del torneo de selección

    def __init__(
        self,
        paquetes: list[dict],
        vehiculos: list[dict],
        generaciones: int = GENERACIONES,
        poblacion_tam: int = POBLACION_TAM,
    ):
        """
        paquetes  : lista de dicts (de PPDatos)
        vehiculos : lista de dicts de vehículos disponibles (de PPDatos)
        """
        self.paquetes      = paquetes
        self.vehiculos     = vehiculos
        self.n_paq         = len(paquetes)
        self.n_veh         = len(vehiculos)
        self.generaciones  = generaciones
        self.poblacion_tam = poblacion_tam

        self._mejor_individuo: Optional[list[int]] = None
        self._historial_fitness: list[float] = []

    # ── Inicialización ─────────────────────────────

    def _crear_individuo(self) -> list[int]:
        """Cromosoma aleatorio."""
        individuo = []
        for p in self.paquetes:
            urgencia = PRIORIDADES[p["prioridad"]]["urgencia"]
            # Paquetes urgentes tienen más probabilidad de ser asignados
            prob_asignar = 0.4 + urgencia * 0.2   # Verde:0.6, Azul:0.8, Rojo:1.0 (capped)
            prob_asignar = min(prob_asignar, 1.0)
            if random.random() < prob_asignar:
                individuo.append(random.randint(0, self.n_veh - 1))
            else:
                individuo.append(-1)
        return individuo

    def _crear_poblacion(self) -> list[list[int]]:
        return [self._crear_individuo() for _ in range(self.poblacion_tam)]

    # ── Fitness ────────────────────────────────────

    def calcular_fitness(self, individuo: list[int]) -> float:
        """
        Evalúa un cromosoma y retorna su puntaje de fitness.
        Mayor = mejor solución.
        """
        # Acumuladores por vehículo
        cargas  = [0.0] * self.n_veh   # kg
        volumenes = [0.0] * self.n_veh
        paquetes_veh = [[] for _ in range(self.n_veh)]

        fitness = 0.0
        PENALIZACION_EXCESO = 1000.0

        for idx, gen in enumerate(individuo):
            paq = self.paquetes[idx]
            if gen == -1:
                # Paquete conservado: penalizar según urgencia
                fitness -= PRIORIDADES[paq["prioridad"]]["urgencia"] * 5
                continue

            veh = self.vehiculos[gen]
            cargas[gen]    += paq["peso_kg"]
            volumenes[gen] += paq["volumen_m3"]
            paquetes_veh[gen].append(paq)

            # Recompensa por entregar el paquete (urgencia × peso como proxy)
            fitness += PRIORIDADES[paq["prioridad"]]["urgencia"] * 10

        # Penalización por exceso de capacidad
        for i, veh in enumerate(self.vehiculos):
            if cargas[i] > veh["capacidad_kg"]:
                exceso = cargas[i] - veh["capacidad_kg"]
                fitness -= PENALIZACION_EXCESO * exceso

            if volumenes[i] > veh["volumen_m3"]:
                exceso = volumenes[i] - veh["volumen_m3"]
                fitness -= PENALIZACION_EXCESO * exceso * 500   # volumen en m³

            # Premio por eficiencia: no usar un vehículo grande para poco carga
            if paquetes_veh[i]:
                uso_pct = cargas[i] / veh["capacidad_kg"]
                fitness += uso_pct * 20

        return fitness

    # ── Selección (torneo) ─────────────────────────

    def _seleccion_torneo(
        self, poblacion: list[list[int]], fitness_vals: list[float]
    ) -> list[int]:
        competidores = random.sample(range(len(poblacion)), self.TORNEO_K)
        ganador = max(competidores, key=lambda i: fitness_vals[i])
        return copy.copy(poblacion[ganador])

    # ── Cruce (un punto) ───────────────────────────

    def _cruce(self, padre1: list[int], padre2: list[int]) -> tuple[list[int], list[int]]:
        if random.random() > self.PROB_CRUCE or self.n_paq < 2:
            return copy.copy(padre1), copy.copy(padre2)
        punto = random.randint(1, self.n_paq - 1)
        hijo1 = padre1[:punto] + padre2[punto:]
        hijo2 = padre2[:punto] + padre1[punto:]
        return hijo1, hijo2

    # ── Mutación ───────────────────────────────────

    def _mutar(self, individuo: list[int]) -> list[int]:
        for i in range(self.n_paq):
            if random.random() < self.PROB_MUTACION:
                # Toggle: si estaba asignado → conservar, si estaba conservado → asignar
                if individuo[i] == -1:
                    individuo[i] = random.randint(0, self.n_veh - 1)
                else:
                    individuo[i] = random.choice(
                        [-1] + list(range(self.n_veh))
                    )
        return individuo

    # ── Ciclo principal ────────────────────────────

    def ejecutar(self) -> dict:
        """
        Ejecuta el GA y retorna un dict con:
          - asignaciones: {paquete_id: vehiculo_id | None}
          - fitness_final: float
          - historial_fitness: [float]
          - generaciones_ejecutadas: int
        """
        if not self.paquetes or not self.vehiculos:
            return {
                "asignaciones": {},
                "fitness_final": 0.0,
                "historial_fitness": [],
                "generaciones_ejecutadas": 0,
            }

        poblacion  = self._crear_poblacion()
        n_elite    = max(1, int(self.poblacion_tam * self.ELITISMO_FRAC))

        for gen in range(self.generaciones):
            fitness_vals = [self.calcular_fitness(ind) for ind in poblacion]
            mejor_idx    = max(range(len(poblacion)), key=lambda i: fitness_vals[i])
            self._historial_fitness.append(fitness_vals[mejor_idx])

            # Elitismo: los mejores pasan directamente
            orden = sorted(range(len(poblacion)), key=lambda i: fitness_vals[i], reverse=True)
            nueva_poblacion = [copy.copy(poblacion[i]) for i in orden[:n_elite]]

            # Llenar el resto con cruce + mutación
            while len(nueva_poblacion) < self.poblacion_tam:
                p1 = self._seleccion_torneo(poblacion, fitness_vals)
                p2 = self._seleccion_torneo(poblacion, fitness_vals)
                h1, h2 = self._cruce(p1, p2)
                nueva_poblacion.append(self._mutar(h1))
                if len(nueva_poblacion) < self.poblacion_tam:
                    nueva_poblacion.append(self._mutar(h2))

            poblacion = nueva_poblacion

        # Extraer el mejor individuo final
        fitness_vals = [self.calcular_fitness(ind) for ind in poblacion]
        mejor_idx    = max(range(len(poblacion)), key=lambda i: fitness_vals[i])
        self._mejor_individuo = poblacion[mejor_idx]

        # Construir mapa de asignaciones
        asignaciones = {}
        for idx, gen in enumerate(self._mejor_individuo):
            pid = self.paquetes[idx]["id"]
            asignaciones[pid] = self.vehiculos[gen]["id"] if gen != -1 else None

        return {
            "asignaciones":            asignaciones,
            "fitness_final":           fitness_vals[mejor_idx],
            "historial_fitness":       self._historial_fitness,
            "generaciones_ejecutadas": self.generaciones,
        }


# ─────────────────────────────────────────────
# ALGORITMO DE COLONIA DE HORMIGAS (ACO)
# ─────────────────────────────────────────────
# Objetivo: dado un conjunto de paquetes asignados a un vehículo,
# encontrar el ORDEN DE VISITA (ruta) que minimice la distancia total.

class ColoniaHormigas:
    """
    Implementa ACO para el Problema del Viajante de Comercio (TSP)
    adaptado para rutas de entrega con origen en el almacén (0,0).

    Los nodos son: almacén (índice 0) + paquetes (índices 1..N)
    """

    # ── Parámetros por defecto ─────────────────────
    N_HORMIGAS   = 20
    ITERACIONES  = 100
    ALPHA        = 1.0    # peso de la feromona
    BETA         = 2.0    # peso de la heurística (1/distancia)
    RHO          = 0.1    # tasa de evaporación
    Q            = 100.0  # constante de depósito de feromona
    FEROMONA_INI = 1.0    # feromona inicial en todos los arcos

    def __init__(
        self,
        paquetes: list[dict],
        n_hormigas: int = N_HORMIGAS,
        iteraciones: int = ITERACIONES,
    ):
        """
        paquetes: lista de dicts con coord_x, coord_y, id
        El almacén está implícito en (0, 0).
        """
        self.paquetes    = paquetes
        self.n_hormigas  = n_hormigas
        self.iteraciones = iteraciones
        self.n_nodos     = len(paquetes) + 1   # +1 por el almacén

        self._mejor_ruta: list[int] = []
        self._mejor_distancia: float = float("inf")
        self._historial: list[float] = []

        # Coordenadas: nodo 0 = almacén, nodos 1..N = paquetes
        self._coords: list[tuple] = [(0.0, 0.0)] + [
            (p["coord_x"], p["coord_y"]) for p in paquetes
        ]

        # Matriz de distancias
        self._dist = self._calcular_matriz_distancias()

        # Matriz de feromonas
        self._feromona = [
            [self.FEROMONA_INI] * self.n_nodos for _ in range(self.n_nodos)
        ]

    # ── Inicialización ─────────────────────────────

    def _calcular_matriz_distancias(self) -> list[list[float]]:
        n = self.n_nodos
        dist = [[0.0] * n for _ in range(n)]
        for i in range(n):
            for j in range(n):
                if i != j:
                    x1, y1 = self._coords[i]
                    x2, y2 = self._coords[j]
                    dist[i][j] = distancia_euclidea(x1, y1, x2, y2)
        return dist

    # ── Construcción de solución ───────────────────

    def _construir_ruta(self) -> list[int]:
        """Una hormiga construye una ruta completa partiendo del almacén."""
        visitados = {0}
        ruta = [0]
        nodo_actual = 0

        nodos_paquetes = list(range(1, self.n_nodos))
        random.shuffle(nodos_paquetes)   # orden inicial aleatorio

        while len(visitados) < self.n_nodos:
            candidatos = [n for n in nodos_paquetes if n not in visitados]
            if not candidatos:
                break

            probabilidades = []
            for c in candidatos:
                d = self._dist[nodo_actual][c]
                heuristica = 1.0 / d if d > 0 else 1e6
                tau  = self._feromona[nodo_actual][c] ** self.ALPHA
                eta  = heuristica ** self.BETA
                probabilidades.append(tau * eta)

            total = sum(probabilidades)
            if total == 0:
                siguiente = random.choice(candidatos)
            else:
                probs_norm = [p / total for p in probabilidades]
                siguiente  = random.choices(candidatos, weights=probs_norm, k=1)[0]

            ruta.append(siguiente)
            visitados.add(siguiente)
            nodo_actual = siguiente

        ruta.append(0)   # regresa al almacén
        return ruta

    def _calcular_longitud_ruta(self, ruta: list[int]) -> float:
        total = 0.0
        for i in range(len(ruta) - 1):
            total += self._dist[ruta[i]][ruta[i + 1]]
        return round(total, 4)

    # ── Actualización de feromonas ─────────────────

    def _evaporar_feromonas(self):
        for i in range(self.n_nodos):
            for j in range(self.n_nodos):
                self._feromona[i][j] *= (1.0 - self.RHO)
                self._feromona[i][j] = max(self._feromona[i][j], 0.001)

    def _depositar_feromonas(self, rutas: list[list[int]], longitudes: list[float]):
        for ruta, longitud in zip(rutas, longitudes):
            deposito = self.Q / longitud if longitud > 0 else 0
            for i in range(len(ruta) - 1):
                self._feromona[ruta[i]][ruta[i + 1]] += deposito
                self._feromona[ruta[i + 1]][ruta[i]] += deposito

    # ── Ciclo principal ────────────────────────────

    def ejecutar(self) -> dict:
        """
        Ejecuta el ACO y retorna un dict con:
          - orden_visita: [paquete_id, ...]   (sin incluir el almacén)
          - distancia_km: float
          - historial_distancias: [float]
          - iteraciones_ejecutadas: int
        """
        if not self.paquetes:
            return {
                "orden_visita":          [],
                "distancia_km":          0.0,
                "historial_distancias":  [],
                "iteraciones_ejecutadas":0,
            }

        for _ in range(self.iteraciones):
            rutas_iter    = []
            longitudes_iter = []

            for _ in range(self.n_hormigas):
                ruta    = self._construir_ruta()
                longitud = self._calcular_longitud_ruta(ruta)
                rutas_iter.append(ruta)
                longitudes_iter.append(longitud)

                if longitud < self._mejor_distancia:
                    self._mejor_distancia = longitud
                    self._mejor_ruta      = list(ruta)

            self._evaporar_feromonas()
            self._depositar_feromonas(rutas_iter, longitudes_iter)
            self._historial.append(self._mejor_distancia)

        # Convertir índices de nodos a IDs de paquetes (excluir nodo 0 = almacén)
        orden_paquete_ids = [
            self.paquetes[n - 1]["id"]
            for n in self._mejor_ruta
            if n != 0
        ]

        return {
            "orden_visita":          orden_paquete_ids,
            "distancia_km":          self._mejor_distancia,
            "historial_distancias":  self._historial,
            "iteraciones_ejecutadas":self.iteraciones,
        }


# ─────────────────────────────────────────────
# FUNCIÓN PRINCIPAL DE OPTIMIZACIÓN
# ─────────────────────────────────────────────

def optimizar(sistema: "DatosSistema") -> list[dict]:
    """
    Orquesta el proceso completo de optimización:
      1. GA determina QUÉ paquetes se entregan y a QUÉ vehículo.
      2. ACO determina el ORDEN DE VISITA de cada vehículo.

    Retorna lista de rutas (dicts) listas para registrar en el sistema.
    Además, actualiza el sistema marcando paquetes como entregados o conservados.

    Estructura de cada ruta retornada:
    {
        "id":          str,
        "vehiculo_id": str,
        "paquetes":    [str],        # IDs de paquetes asignados
        "orden_visita":[str],        # IDs en orden de entrega
        "distancia_km":float,
        "fitness":     float,
        "historial_aco":[float],
    }
    """
    paquetes_pendientes = sistema.get_paquetes_pendientes()
    vehiculos_disp      = list(sistema.get_vehiculos_disponibles().values())

    if not paquetes_pendientes:
        print("[PPAlgoritmos] No hay paquetes pendientes para optimizar.")
        return []

    if not vehiculos_disp:
        print("[PPAlgoritmos] No hay vehículos disponibles.")
        return []

    print(f"[PPAlgoritmos] Iniciando GA con {len(paquetes_pendientes)} paquetes "
          f"y {len(vehiculos_disp)} vehículos...")

    # ── Paso 1: Algoritmo Genético ─────────────────
    ga = AlgoritmoGenetico(paquetes_pendientes, vehiculos_disp)
    resultado_ga = ga.ejecutar()
    asignaciones = resultado_ga["asignaciones"]

    print(f"  GA finalizado | fitness={resultado_ga['fitness_final']:.2f}")

    # Agrupar paquetes por vehículo
    paq_por_vehiculo: dict[str, list[dict]] = {}
    for paq in paquetes_pendientes:
        vid = asignaciones.get(paq["id"])
        if vid is None:
            # Determinar razón de conservación
            razon = _determinar_razon_conservacion(paq, vehiculos_disp)
            sistema.marcar_conservado(paq["id"], razon)
        else:
            if vid not in paq_por_vehiculo:
                paq_por_vehiculo[vid] = []
            paq_por_vehiculo[vid].append(paq)

    # ── Paso 2: ACO por vehículo ───────────────────
    rutas_generadas = []
    contador_ruta   = 1

    for vid, paquetes_veh in paq_por_vehiculo.items():
        print(f"  ACO vehículo {vid} | {len(paquetes_veh)} paquetes...")

        aco = ColoniaHormigas(paquetes_veh)
        resultado_aco = aco.ejecutar()

        ruta_id = f"RUTA-{contador_ruta:03d}"
        ruta = {
            "id":           ruta_id,
            "vehiculo_id":  vid,
            "paquetes":     [p["id"] for p in paquetes_veh],
            "orden_visita": resultado_aco["orden_visita"],
            "distancia_km": resultado_aco["distancia_km"],
            "fitness":      resultado_ga["fitness_final"],
            "historial_aco":resultado_aco["historial_distancias"],
        }
        rutas_generadas.append(ruta)
        sistema.registrar_ruta(ruta)

        # Actualizar estado de paquetes y vehículo
        for paq in paquetes_veh:
            try:
                sistema.asignar_paquete_vehiculo(vid, paq["id"])
                sistema.marcar_entregado(
                    paq["id"], vid, ruta_id, resultado_aco["distancia_km"]
                )
            except ValueError as e:
                # Si supera capacidad, conservar
                sistema.marcar_conservado(paq["id"], "exceso de peso")
                print(f"    [!] {paq['id']} conservado: {e}")

        sistema.registrar_ruta_vehiculo(vid, resultado_aco["distancia_km"])
  
