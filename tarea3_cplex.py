#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ruteo consistente con ventanas de tiempo (conVRP) – BioSur Distribución Farmacéutica
Implementación en IBM ILOG CPLEX (DOcplex) para ejecución local multiplataforma (Linux, Windows, macOS).
Adaptado a partir de tarea3_gurobi.py.

Grupo: Nicolás López, Ignacio Soto, Marcos Martínez, Gabriela Zambrano
"""

import os
import sys
import json
import math
import shutil
import platform
import argparse
from pathlib import Path
from functools import reduce

# ==============================================================================
# 1. CONFIGURACIÓN Y DETECCIÓN DE CPLEX MULTIPLATAFORMA
# ==============================================================================

def configurar_cplex(cplex_dir_param=None):
    """
    Busca y configura automáticamente la instalación de IBM ILOG CPLEX Optimization Studio
    de forma multiplataforma (Linux, Windows, macOS), o verifica los paquetes pip (docplex, cplex).

    Prioridad de búsqueda de CPLEX Studio:
      1. Parámetro explícito (--cplex-dir o cplex_dir_param)
      2. Variable de entorno CPLEX_STUDIO_DIR (o CPLEX_STUDIO_DIR2211, etc.)
      3. Rutas estándar por sistema operativo:
         - Windows: C:\\Program Files\\IBM\\ILOG\\CPLEX_Studio*
         - Linux: /opt/ibm/ILOG/CPLEX_Studio*, /opt/IBM/ILOG/CPLEX_Studio*
         - macOS: /Applications/CPLEX_Studio*
    """
    import glob
    candidatos = []

    # 1. Parámetro explícito
    if cplex_dir_param:
        candidatos.append(Path(cplex_dir_param))

    # 2. Variables de entorno
    for env_k, env_v in os.environ.items():
        if env_k.startswith("CPLEX_STUDIO_DIR"):
            candidatos.append(Path(env_v))

    # 3. Directorios estándar por SO
    so = platform.system().lower()
    if "windows" in so:
        rutas_glob = (
            glob.glob(r"C:\Program Files\IBM\ILOG\CPLEX_Studio*") +
            glob.glob(r"C:\Program Files (x86)\IBM\ILOG\CPLEX_Studio*") +
            glob.glob(r"C:\IBM\ILOG\CPLEX_Studio*")
        )
        candidatos.extend([Path(p) for p in rutas_glob])
    elif "darwin" in so:
        candidatos.extend([Path(p) for p in glob.glob("/Applications/CPLEX_Studio*")])
    else:
        rutas_glob = (
            glob.glob("/opt/ibm/ILOG/CPLEX_Studio*") +
            glob.glob("/opt/IBM/ILOG/CPLEX_Studio*") +
            glob.glob("/usr/local/CPLEX_Studio*")
        )
        candidatos.extend([Path(p) for p in rutas_glob])

    cplex_encontrado = None
    for cand in candidatos:
        try:
            if cand and cand.is_dir():
                cplex_encontrado = cand.resolve()
                break
        except Exception:
            continue

    if cplex_encontrado:
        print(f"[CPLEX Studio] Detectado en: {cplex_encontrado}")
        # Agregar binarios al PATH según arquitectura
        if "windows" in so:
            bin_dir = cplex_encontrado / "cplex" / "bin" / "x64_win64"
        elif "darwin" in so:
            bin_dir = cplex_encontrado / "cplex" / "bin" / "x86-64_osx"
        else:
            bin_dir = cplex_encontrado / "cplex" / "bin" / "x86-64_linux"

        if bin_dir.is_dir():
            os.environ["PATH"] = str(bin_dir) + os.pathsep + os.environ.get("PATH", "")

        # Incorporar bindings de Python si existen en la instalación de CPLEX Studio
        py_base = cplex_encontrado / "cplex" / "python"
        if py_base.is_dir():
            for sub in py_base.glob("python*/*"):
                if sub.is_dir() and str(sub) not in sys.path:
                    sys.path.insert(0, str(sub))
        return str(cplex_encontrado)

    return None


# ==============================================================================
# 2. DEFINICIÓN Y LECTURA DE INSTANCIAS
# ==============================================================================

texto_inst1 = """
========================================================================================
CASO: BioSur Distribución Farmacéutica
INSTANCIA 1: BioSur_Urbana_Clustered_15C (Base C101 adaptada)
DESCRIPCIÓN: Red con farmacias agrupadas espacialmente y alta tasa de ocupación por vehículo.
========================================================================================
METADATA
HORIZON_DAYS: 3
VEHICLES_PER_DAY: 3
VEHICLE_CAPACITY_Q: 95

DEPOT
ID   NAME                    XCOORD   YCOORD   READY_TIME   DUE_DATE   SERVICE_TIME
0    Centro_Distribucion     40       50       0            1200       0

CUSTOMERS
ID   NAME                    XCOORD   YCOORD   DEMAND_D1  DEMAND_D2  DEMAND_D3  READY_TIME  DUE_DATE  SERVICE_TIME
1    Farmacia_Central_1      45       68       25         0          25         700         980       45
2    Clinica_Norte_2         45       70       30         30         0          650         900       45
3    Farmacia_Ahumada_3      42       66       20         20         20         50          250       45
4    Drogueria_Sur_4         42       68       0          25         25         600         850       45
5    Farmacia_Cruz_5         42       65       20         20         0          10          200       45
6    Clinica_Especialidad_6  40       69       35         0          35         500         750       45
7    Farmacia_Salcobrand_7   40       66       0          30         30         120         350       45
8    Hospital_Comunal_8      38       68       25         25         25         200         420       45
9    Farmacia_Popular_9      38       70       0          30         0          450         700       45
10   Farmacia_San_Juan_10    35       66       25         0          25         300         550       45
11   Centro_Salud_11         35       69       20         20         0          380         600       45
12   Clinica_Andes_12        25       85       30         0          30         550         800       45
13   Farmacia_Comunitaria_13 22       75       0          35         35         30          250       45
14   Farmacia_RedSalud_14    22       85       15         15         15         450         720       45
15   Farmacia_BioBio_15      20       80       35         25         0          300         550       45
"""

texto_inst2 = """
========================================================================================
CASO: BioSur Distribución Farmacéutica
INSTANCIA 2: BioSur_Interurbana_Mixed_15C (Base RC101 adaptada)
DESCRIPCIÓN: Red semi-dispersa con dos clústeres geográficos y ventanas temporales solapadas.
========================================================================================
METADATA
HORIZON_DAYS: 3
VEHICLES_PER_DAY: 3
VEHICLE_CAPACITY_Q: 95

DEPOT
ID   NAME                    XCOORD   YCOORD   READY_TIME   DUE_DATE   SERVICE_TIME
0    Centro_Distribucion     40       50       0            1200       0

CUSTOMERS
ID   NAME                    XCOORD   YCOORD   DEMAND_D1  DEMAND_D2  DEMAND_D3  READY_TIME  DUE_DATE  SERVICE_TIME
1    Farmacia_Central_1      45       68       20         20         0          200         500       40
2    Clinica_Norte_2         40       69       0          25         25         150         450       40
3    Farmacia_Ahumada_3      22       75       25         0          25         100         400       40
4    Drogueria_Sur_4         20       80       20         20         20         300         600       40
5    Farmacia_Cruz_5         30       50       25         25         0          50          350       40
6    Clinica_Especialidad_6  25       52       0          30         30         150         450       40
7    Farmacia_Salcobrand_7   10       35       30         0          30         250         550       40
8    Hospital_Comunal_8      10       40       15         15         15         100         400       40
9    Farmacia_Popular_9      35       30       0          30         0          200         500       40
10   Farmacia_San_Juan_10    33       32       25         0          25         80          380       40
11   Centro_Salud_11         44       5        30         30         0          300         650       40
12   Clinica_Andes_12        42       10       0          25         25         200         550       40
13   Farmacia_Comunitaria_13 40       15       20         20         20         50          350       40
14   Farmacia_RedSalud_14    50       35       25         0          25         250         550       40
15   Farmacia_BioBio_15      50       40       20         20         0          180         480       40
"""

def parsear_instancia(texto, Q_override=None):
    """Parsea el formato de texto de la instancia y retorna tupla con parámetros."""
    lineas = [l.strip() for l in texto.strip().splitlines()]
    meta, seccion = {}, None
    depot, clientes = None, []
    for l in lineas:
        if not l or l.startswith("=") or l.startswith(("CASO", "INSTANCIA", "DESCRIPCI")):
            continue
        if l in ("METADATA", "DEPOT", "CUSTOMERS"):
            seccion = l
            continue
        if l.startswith(("ID ", "ID\t")):          # encabezado de tabla
            continue
        if seccion == "METADATA":
            k, v = l.split(":")
            meta[k.strip()] = int(v)
        elif seccion == "DEPOT":
            p = l.split()
            depot = dict(x=int(p[2]), y=int(p[3]), ready=int(p[4]), due=int(p[5]))
        elif seccion == "CUSTOMERS":
            p = l.split()
            clientes.append(dict(id=int(p[0]), x=int(p[2]), y=int(p[3]),
                                 d=[int(p[4]), int(p[5]), int(p[6])],
                                 ready=int(p[7]), due=int(p[8]), serv=int(p[9])))

    N = range(1, len(clientes) + 1)
    V = range(0, len(clientes) + 1)
    T = range(1, meta["HORIZON_DAYS"] + 1)
    R = range(1, meta["VEHICLES_PER_DAY"] + 1)

    coords = {0: (depot["x"], depot["y"])}
    coords.update({c["id"]: (c["x"], c["y"]) for c in clientes})

    dist = {(i, j): round(math.dist(coords[i], coords[j]), 2)
            for i in V for j in V if i != j}
    tt = dict(dist)                                  # 1 unidad de distancia = 1 unidad de tiempo
    s = {c["id"]: c["serv"] for c in clientes}
    ventana = {c["id"]: (c["ready"], c["due"]) for c in clientes}
    d = {(c["id"], t): c["d"][t - 1] for c in clientes for t in T}
    Q = Q_override if Q_override else meta["VEHICLE_CAPACITY_Q"]
    return N, V, T, R, dist, tt, s, ventana, d, Q, depot["ready"], depot["due"]


def chequeo(inst, nombre_instancia="Instancia"):
    """Imprime chequeo de demanda total vs capacidad de flota por día."""
    N, V, T, R, dist, tt, s, ventana, d, Q, t_open, t_close = inst
    print(f"\n--- Chequeo de demanda: {nombre_instancia} ---")
    for t in T:
        demanda_dia = sum(d[i, t] for i in N)
        cap_total = len(R) * Q
        print(f"  Día {t}: demanda {demanda_dia} vs capacidad flota {cap_total}")


def texto_variante(texto, extra, Q, t_open=0, t_close=1200):
    """Ensancha ventanas de tiempo y sobreescribe capacidad Q."""
    salida, seccion = [], None
    for l in texto.splitlines():
        s_ = l.strip()
        if s_ in ("METADATA", "DEPOT", "CUSTOMERS"):
            seccion = s_
        if s_.startswith("VEHICLE_CAPACITY_Q"):
            l = f"VEHICLE_CAPACITY_Q: {Q}"
        elif seccion == "CUSTOMERS" and s_ and not s_.startswith("ID") and s_[0].isdigit():
            p = s_.split()
            p[7] = str(max(t_open, int(p[7]) - extra))
            p[8] = str(min(t_close, int(p[8]) + extra))
            l = (f"{p[0]:<5}{p[1]:<24}{p[2]:<9}{p[3]:<9}{p[4]:<11}{p[5]:<11}"
                 f"{p[6]:<11}{p[7]:<12}{p[8]:<10}{p[9]}")
        salida.append(l)
    return "\n".join(salida)


# ==============================================================================
# 3. CONSTRUCCIÓN DEL MODELO MATEMÁTICO EN CPLEX (conVRP)
# ==============================================================================

def construir_modelo(inst):
    """
    Construye el modelo MIP en IBM ILOG CPLEX (DOcplex) según Campelo et al. (2019) adaptado:
      - X[r, i, j, t]: variable binaria de arco recorrido en día t por ruta r
      - Z[r, i]: variable binaria de asignación consistente cliente-ruta
      - W[i, t]: variable continua de inicio de servicio en cliente i, día t
      - dW[r]: variable continua de salida del depósito de ruta r (constante los 3 días)
      - rW[r, t]: variable continua de retorno al depósito de ruta r en día t
    """
    from docplex.mp.model import Model

    N, V, T, R, dist, tt, s, ventana, d, Q, t_open, t_close = inst
    mdl = Model(name="conVRP_BioSur")

    fin = len(N) + 1                       # nodo de retorno n+1
    dist = dict(dist)
    tt = dict(tt)
    for i in N:
        dist[i, fin] = dist[i, 0]
        tt[i, fin] = tt[i, 0]
    dist[0, fin] = 0
    tt[0, fin] = 0

    arcos = []
    for r in R:
        for t in T:
            for j in N:
                arcos.append((r, 0, j, t))
            arcos.append((r, 0, fin, t))
            for i in N:
                for j in N:
                    if i != j:
                        arcos.append((r, i, j, t))
                arcos.append((r, i, fin, t))

    # Variables de decisión
    X  = mdl.binary_var_dict(arcos, name=lambda k: f"x_{k[0]}_{k[1]}_{k[2]}_{k[3]}")
    Z  = mdl.binary_var_dict([(r, i) for r in R for i in N], name=lambda k: f"z_{k[0]}_{k[1]}")
    W  = mdl.continuous_var_dict([(i, t) for i in N for t in T], lb=0, ub=t_close, name=lambda k: f"w_{k[0]}_{k[1]}")
    dW = mdl.continuous_var_dict(R, lb=0, ub=t_close, name=lambda k: f"dW_{k}")
    rW = mdl.continuous_var_dict([(r, t) for r in R for t in T], lb=0, ub=t_close, name=lambda k: f"rW_{k[0]}_{k[1]}")

    # (1) Función Objetivo: minimizar distancia total recorrida
    mdl.minimize(mdl.sum(dist[i, j] * X[r, i, j, t] for (r, i, j, t) in arcos))

    # (2) Asignación única cliente-ruta en todo el horizonte
    for i in N:
        mdl.add_constraint(mdl.sum(Z[r, i] for r in R) == 1, ctname=f"asig_{i}")

    # (3) Entrada a cada cliente y (4) salida de cada cliente
    for r in R:
        for t in T:
            for j in N:
                entra_expr = X[r, 0, j, t] + mdl.sum(X[r, i, j, t] for i in N if i != j)
                sale_expr = mdl.sum(X[r, j, k, t] for k in N if k != j) + X[r, j, fin, t]
                if d[j, t] > 0:
                    # Si el cliente tiene demanda el día t, lo visita su ruta asignada
                    mdl.add_constraint(entra_expr == Z[r, j], ctname=f"entra_{r}_{j}_{t}")
                    mdl.add_constraint(sale_expr == Z[r, j], ctname=f"sale_{r}_{j}_{t}")
                else:
                    # Si no tiene demanda ese día, ningún vehículo entra ni sale de este cliente
                    mdl.add_constraint(entra_expr == 0, ctname=f"entra_{r}_{j}_{t}")
                    mdl.add_constraint(sale_expr == 0, ctname=f"sale_{r}_{j}_{t}")

    # (5) Cada ruta sale del depósito cada día
    for r in R:
        for t in T:
            mdl.add_constraint(
                X[r, 0, fin, t] + mdl.sum(X[r, 0, j, t] for j in N) == 1,
                ctname=f"sale_dep_{r}_{t}"
            )

    # (7) Tiempos de inicio de servicio entre clientes consecutivos (Big-M)
    for r in R:
        for t in T:
            for i in N:
                for j in N:
                    if i != j:
                        M_ij = max(0, ventana[i][1] + s[i] + tt[i, j] - ventana[j][0])
                        mdl.add_constraint(
                            W[i, t] + s[i] + tt[i, j] <= W[j, t] + M_ij * (1 - X[r, i, j, t]),
                            ctname=f"tiempo_{r}_{i}_{j}_{t}"
                        )

    # (8) Ventanas de tiempo para cada cliente
    for i in N:
        for t in T:
            mdl.add_constraint(W[i, t] >= ventana[i][0], ctname=f"vent_lo_{i}_{t}")
            mdl.add_constraint(W[i, t] <= ventana[i][1], ctname=f"vent_up_{i}_{t}")

    # (9) Salida del depósito -> primer cliente (dW constante para todos los días)
    for r in R:
        for t in T:
            for j in N:
                M_0j = max(0, t_close + tt[0, j] - ventana[j][0])
                mdl.add_constraint(
                    dW[r] + tt[0, j] <= W[j, t] + M_0j * (1 - X[r, 0, j, t]),
                    ctname=f"salida_{r}_{j}_{t}"
                )

    # (10) Último cliente -> retorno al depósito (nodo fin)
    for r in R:
        for t in T:
            for i in N:
                M_if = max(0, ventana[i][1] + s[i] + tt[i, fin] - t_open)
                mdl.add_constraint(
                    W[i, t] + s[i] + tt[i, fin] <= rW[r, t] + M_if * (1 - X[r, i, fin, t]),
                    ctname=f"retorno_{r}_{i}_{t}"
                )

    # (11)-(12) Horario de apertura y cierre del depósito
    for r in R:
        mdl.add_constraint(dW[r] >= t_open, ctname=f"apertura_{r}")
        for t in T:
            mdl.add_constraint(rW[r, t] <= t_close, ctname=f"cierre_{r}_{t}")

    # (14) Capacidad máxima de cada vehículo en cada día
    for r in R:
        for t in T:
            mdl.add_constraint(
                mdl.sum(d[i, t] * Z[r, i] for i in N) <= Q,
                ctname=f"cap_{r}_{t}"
            )

    return mdl, X, Z, W, dW, rW


# ==============================================================================
# 4. FUNCIONES DE RESOLUCIÓN Y EXPERIMENTACIÓN
# ==============================================================================

def aplicar_parametro(m, clave, valor):
    """
    Aplica parámetros a CPLEX permitiendo tanto nombres estándar CPLEX
    (jerarquía con puntos) como los nombres análogos del benchmark de Gurobi.
    """
    mapeo_gurobi_a_cplex = {
        "Threads": "threads",
        "TimeLimit": "timelimit",
        "Seed": "randomseed",
        "Cuts": "mip.limits.cutpasses",
        "Presolve": "preprocessing.presolve",
        "MIPFocus": "emphasis.mip",
        "Heuristics": "mip.strategy.heuristicfreq",
    }

    ruta = mapeo_gurobi_a_cplex.get(clave, clave)

    # Ajustes semánticos específicos entre solvers:
    # Cuts=0 en Gurobi -> cutpasses=-1 en CPLEX (desactiva generación de cortes)
    if clave == "Cuts" and valor == 0:
        valor = -1
    # Heuristics=0 en Gurobi -> heuristicfreq=-1 en CPLEX (desactiva heurísticas periódicas)
    elif clave == "Heuristics" and valor == 0:
        valor = -1

    try:
        param_obj = reduce(getattr, ruta.split('.'), m.parameters)
        param_obj.set(valor)
    except Exception as e:
        print(f"[Aviso Parámetro CPLEX] No se pudo configurar '{clave}' ({ruta}) = {valor}: {e}")


def resolver(m, out_dir, tl=600, nombre=None, **params):
    """
    Resuelve un modelo CPLEX con límite de tiempo, 1 thread y guarda logs/soluciones.
    Retorna diccionario compatible con el esquema de resultados.
    """
    m.parameters.threads.set(1)
    m.parameters.timelimit.set(tl)

    for k, v in params.items():
        aplicar_parametro(m, k, v)

    ruta_log = None
    if nombre:
        ruta_log = out_dir / f"log_{nombre}.txt"
        if ruta_log.exists():
            try:
                ruta_log.unlink()
            except Exception:
                pass

    if ruta_log:
        with open(ruta_log, "w", encoding="utf-8") as f_log:
            sol = m.solve(log_output=f_log)
    else:
        sol = m.solve(log_output=False)

    ok = sol is not None
    details = m.solve_details

    tiempo = getattr(details, "time", 0.0) if details else 0.0
    estado = getattr(details, "status", ("optimal" if ok else "unknown")) if details else "unknown"
    gap = getattr(details, "mip_relative_gap", None) if ok and details else None
    cota = getattr(details, "best_bound", None) if ok and details else None
    obj = sol.objective_value if ok else None

    if ok and nombre:
        # 1. Guardar solución en formato JSON estructurado
        ruta_json = out_dir / f"sol_{nombre}.json"
        sol_dict = {
            "objective": obj,
            "status": str(estado),
            "gap": gap,
            "time": tiempo,
            "variables": {v.name: sol.get_value(v) for v in m.iter_variables()}
        }
        with open(ruta_json, "w", encoding="utf-8") as f_json:
            json.dump(sol_dict, f_json, indent=2)

        # 2. Guardar solución en formato .sol de texto plano compatible
        ruta_sol = out_dir / f"sol_{nombre}.sol"
        with open(ruta_sol, "w", encoding="utf-8") as f_sol:
            f_sol.write(f"# Solución CPLEX para {nombre}\n")
            f_sol.write(f"# Objective value = {obj}\n")
            f_sol.write(f"# Status = {estado}\n")
            for v in m.iter_variables():
                val = sol.get_value(v)
                if abs(val) > 1e-6:
                    f_sol.write(f"{v.name} {val:.6f}\n")

    return dict(
        obj=obj,
        gap=gap,
        cota=cota,
        tiempo=tiempo,
        estado=estado
    )


def relajacion(inst):
    """Calcula la cota inferior mediante la relajación continua (LP) en CPLEX."""
    from docplex.mp.relax_linear import LinearRelaxer

    m, *_ = construir_modelo(inst)
    rel = LinearRelaxer.make_relaxed_model(m)
    rel.parameters.threads.set(1)
    sol = rel.solve(log_output=False)
    return sol.objective_value if sol else None


def tunear(inst, nombre, out_dir, tune_time=1800, trial_limit=300):
    """
    Ejecuta el proceso automático de ajuste de hiperparámetros (tune) de CPLEX.
    Utiliza el motor subyacente cplex.parameters.tune_problem().
    """
    m, *_ = construir_modelo(inst)
    m.parameters.threads.set(1)
    m.parameters.timelimit.set(trial_limit)

    prm = out_dir / f"tune_{nombre}.prm"
    print(f"\n[Tuning CPLEX] Iniciando tuning para {nombre} (TuneTimeLimit={tune_time}s)...")

    try:
        cpx = m.get_engine().get_cplex()
        if cpx is None:
            return {"nota": "Motor nativo CPLEX no disponible para tuning automático"}

        cpx.parameters.tune.timelimit.set(tune_time)
        status = cpx.parameters.tune_problem()

        # Guardar archivo de parámetros encontrados (.prm)
        cpx.parameters.write_file(str(prm))

        # Resolver nuevamente con la configuración optimizada
        m2, *_ = construir_modelo(inst)
        cpx2 = m2.get_engine().get_cplex()
        if cpx2 is not None and prm.exists():
            cpx2.parameters.read_file(str(prm))

        res = resolver(m2, out_dir=out_dir, tl=600, nombre=f"tuned_{nombre}")

        tuned_params = {}
        for param, value in cpx.parameters.get_changed():
            p_str = str(param)
            if not any(ign in p_str.lower() for ign in ["thread", "timelimit", "logfile"]):
                tuned_params[p_str] = value

        res["parametros"] = tuned_params
        return res
    except Exception as e:
        print(f"[Tuning CPLEX] AVISO: El ajuste de parámetros no pudo completarse: {e}")
        return {"nota": f"Tuning no completado: {e}"}


def sensibilidad(inst, nombre, out_dir):
    """
    Realiza análisis de sensibilidad fijando las variables enteras y resolviendo el modelo fijo
    como un programa lineal continuo (Dual Simplex), obteniendo precios sombra, holguras
    y rangos de variación RHS (SARHSLow, SARHSUp).
    """
    import pandas as pd
    from docplex.mp.relax_linear import LinearRelaxer

    N, V, T, R, dist, tt, s, ventana, d, Q, t_open, t_close = inst

    sol_json = out_dir / f"sol_{nombre}.json"
    sol_sol = out_dir / f"sol_{nombre}.sol"

    val_dict = {}
    if sol_json.exists():
        with open(sol_json, "r", encoding="utf-8") as f:
            data = json.load(f)
            val_dict = data.get("variables", {})
    elif sol_sol.exists():
        with open(sol_sol, "r", encoding="utf-8") as f:
            for l in f:
                l = l.strip()
                if l and not l.startswith("#"):
                    partes = l.split(None, 1)
                    if len(partes) == 2:
                        try:
                            val_dict[partes[0]] = float(partes[1])
                        except ValueError:
                            pass
    else:
        print(f"[Sensibilidad] AVISO: No se encontró la solución {nombre}. Ejecute baseline primero.")
        return None

    # 1. Construir modelo original
    m, X, Z, W, dW, rW = construir_modelo(inst)

    # 2. Generar el modelo lineal relajado equivalente
    rel = LinearRelaxer.make_relaxed_model(m)

    # 3. Fijar las variables binarias a los valores de la solución
    for v in rel.iter_continuous_vars():
        if v.name.startswith("x_") or v.name.startswith("z_"):
            val = round(val_dict.get(v.name, 0.0))
            v.lb = val
            v.ub = val

    rel.parameters.threads.set(1)
    rel.parameters.preprocessing.presolve.set(0)
    try:
        rel.parameters.lpmethod.set(2)  # Simplex Dual en CPLEX
    except Exception:
        pass

    sol_fixed = rel.solve(log_output=False)
    if sol_fixed is None:
        print(f"[Sensibilidad {nombre}] AVISO: No se pudo resolver el LP fijo.")
        return None

    print(f"[Sensibilidad {nombre}] Objetivo con enteros fijos: {sol_fixed.objective_value:.2f}")

    # 4. Obtener rangos de sensibilidad RHS (SARHSLow, SARHSUp) del motor CPLEX
    rhs_ranges = {}
    try:
        cpx = rel.get_engine().get_cplex()
        if cpx is not None:
            names = cpx.linear_constraints.get_names()
            ranges = cpx.solution.sensitivity.rhs()
            rhs_ranges = dict(zip(names, ranges))
    except Exception:
        pass

    filas = []
    for r in R:
        for t in T:
            ct_name = f"cap_{r}_{t}"
            c = rel.get_constraint_by_name(ct_name)
            carga = sum(d[i, t] * round(val_dict.get(f"z_{r}_{i}", 0.0)) for i in N)

            holgura = None
            if hasattr(c, "slack_value"):
                holgura = c.slack_value
            elif hasattr(c, "slack"):
                holgura = c.slack

            precio_sombra = None
            if hasattr(c, "dual_value"):
                precio_sombra = c.dual_value
            elif hasattr(c, "dual"):
                precio_sombra = c.dual

            sarhs_low, sarhs_up = rhs_ranges.get(ct_name, (None, None))

            filas.append(dict(
                ruta=r,
                dia=t,
                carga=carga,
                Q=Q,
                holgura=holgura,
                precio_sombra=precio_sombra,
                SARHSLow=sarhs_low,
                SARHSUp=sarhs_up
            ))

    df_sens = pd.DataFrame(filas)
    return df_sens


def inspeccionar_solucion(inst, nombre, out_dir):
    """Muestra hora de salida más tardía desde depósito y la carga por vehículo/día."""
    N, V, T, R, dist, tt, s, ventana, d, Q, t_open, t_close = inst

    sol_json = out_dir / f"sol_{nombre}.json"
    sol_sol = out_dir / f"sol_{nombre}.sol"

    val_dict = {}
    if sol_json.exists():
        with open(sol_json, "r", encoding="utf-8") as f:
            data = json.load(f)
            val_dict = data.get("variables", {})
    elif sol_sol.exists():
        with open(sol_sol, "r", encoding="utf-8") as f:
            for l in f:
                l = l.strip()
                if l and not l.startswith("#"):
                    partes = l.split(None, 1)
                    if len(partes) == 2:
                        try:
                            val_dict[partes[0]] = float(partes[1])
                        except ValueError:
                            pass
    else:
        return

    print(f"\n=======================================================")
    print(f"ANÁLISIS DE RUTAS Y HORAS: {nombre}")
    print(f"=======================================================")
    print("--- HORA DE SALIDA DEL DEPÓSITO (la más tardía compatible con la solución) ---")
    for r in R:
        salidas = [
            val_dict.get(f"w_{j}_{t}", 0.0) - tt[0, j]
            for t in T for j in N
            if val_dict.get(f"x_{r}_0_{j}_{t}", 0.0) > 0.5
        ]
        if salidas:
            print(f"  Vehículo {r}: sale como máximo a las {min(salidas):.2f}")

    print(f"\n--- CARGA POR VEHÍCULO Y DÍA (Capacidad Q = {Q}) ---")
    for t in T:
        print(f"\n  Día {t}:")
        for r in R:
            clientes_r = [i for i in N if val_dict.get(f"z_{r}_{i}", 0.0) > 0.5]
            carga = sum(d[i, t] for i in clientes_r)
            print(f"    Vehículo {r}: Carga = {carga}/{Q} (Clientes: {clientes_r})")


# ==============================================================================
# 5. PIPELINE PRINCIPAL
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Optimización conVRP con IBM ILOG CPLEX (BioSur Distribución Farmacéutica)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("--cplex-dir", "--cplex-path", type=str, default=None,
                        help="Ruta al directorio de instalación de IBM ILOG CPLEX Optimization Studio.")
    parser.add_argument("--dir", type=str, default="tarea_convrp_cplex",
                        help="Carpeta donde guardar los archivos de salida, logs y soluciones.")
    parser.add_argument("--time-limit", type=int, default=600,
                        help="Límite de tiempo en segundos por corrida.")
    parser.add_argument("--skip-tuning", action="store_true",
                        help="Omitir el ajuste automático (tuning).")
    parser.add_argument("--only-summary", action="store_true",
                        help="Solo leer los resultados existentes e imprimir las tablas de resumen.")
    args = parser.parse_args()

    # Directorio de trabajo
    script_dir = Path(__file__).resolve().parent
    out_dir = script_dir / args.dir
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"[Directorio de Resultados] {out_dir}")

    # Configuración de CPLEX
    configurar_cplex(args.cplex_dir)

    # Verificación de librerías docplex / cplex
    if not args.only_summary:
        try:
            import docplex
            from docplex.mp.model import Model
            print(f"[DOcplex Version] {docplex.__version__}")
        except ImportError:
            print("\n[ERROR FATAL] La librería 'docplex' no está instalada en este entorno Python.")
            print("Instálala ejecutando:")
            print("    pip install docplex")
            print("Y asegúrate de contar con el solver CPLEX ('pip install cplex' o CPLEX Studio instalado).")
            sys.exit(1)

        try:
            import cplex
            print(f"[CPLEX Engine Version] {cplex.__version__}")
        except ImportError:
            print("[AVISO] El paquete 'cplex' no está importable directamente en Python.")
            print("        DOcplex intentará usar ejecutables del sistema o configuración de CPLEX Studio.")

    import pandas as pd

    # Preparación de instancias
    texto_inst1_final = texto_variante(texto_inst1, extra=100, Q=95)
    texto_inst2_final = texto_variante(texto_inst2, extra=150, Q=100)

    # Guardar instancias procesadas
    for nombre_archivo, txt in [("instancia1.txt", texto_inst1_final), ("instancia2.txt", texto_inst2_final)]:
        p_local = script_dir / nombre_archivo
        p_out = out_dir / nombre_archivo
        with open(p_local, "w", encoding="utf-8") as f:
            f.write(txt.strip() + "\n")
        shutil.copy(str(p_local), str(p_out))

    inst1 = parsear_instancia(texto_inst1_final)
    inst2 = parsear_instancia(texto_inst2_final)
    instancias = {"Instancia 1": inst1, "Instancia 2": inst2}

    chequeo(inst1, "Instancia 1")
    chequeo(inst2, "Instancia 2")

    RES_FILE = out_dir / "resultados.json"
    resultados = json.load(open(RES_FILE, "r", encoding="utf-8")) if RES_FILE.exists() else {}

    def guardar_resultados():
        with open(RES_FILE, "w", encoding="utf-8") as f:
            json.dump(resultados, f, indent=2)

    if not args.only_summary:
        # ----------------------------------------------------------------------
        # A. Relajación continua y configuraciones del solver
        # ----------------------------------------------------------------------
        # Mapeo de las 6 configuraciones experimentales a CPLEX
        configs = {
            "Baseline": {},
            "Cuts=0": {"mip.limits.cutpasses": -1},           # Desactiva pases de cortes en CPLEX
            "Presolve=0": {"preprocessing.presolve": 0},      # Desactiva presolve
            "MIPFocus=1": {"emphasis.mip": 1},                # Énfasis en factibilidad (CPX_MIPEMPHASIS_FEASIBILITY)
            "MIPFocus=3": {"emphasis.mip": 3},                # Énfasis en cota dual/optimalidad (CPX_MIPEMPHASIS_BESTBOUND)
            "Heuristics=0": {"mip.strategy.heuristicfreq": -1}# Desactiva heurísticas periódicas
        }

        print("\n" + "=" * 80)
        print("EJECUTANDO RELAJACIONES Y CONFIGURACIONES DE CPLEX")
        print("=" * 80)

        for nom_i, inst in instancias.items():
            resultados.setdefault(nom_i, {})
            # Relajación continua
            if "LP" not in resultados[nom_i]:
                print(f"\n[LP CPLEX] Calculando relajación continua para {nom_i}...")
                resultados[nom_i]["LP"] = relajacion(inst)
                guardar_resultados()
                lp_val = resultados[nom_i]["LP"]
                print(f"  -> LP Obj: {lp_val:.2f}" if lp_val is not None else "  -> LP Obj: No resuelto")

            # Configuraciones MIP
            for nom_c, params in configs.items():
                if nom_c in resultados[nom_i]:
                    print(f"[Omitiendo] {nom_i} - {nom_c} ya está resuelto en {RES_FILE}")
                    continue

                print(f"\n[Resolviendo CPLEX] {nom_i} con configuración '{nom_c}' (TimeLimit={args.time_limit}s)...")
                m, *_ = construir_modelo(inst)
                nombre_run = f"{nom_c}_{nom_i.replace(' ', '')}"
                r = resolver(m, out_dir=out_dir, tl=args.time_limit, nombre=nombre_run, **params)
                resultados[nom_i][nom_c] = r
                guardar_resultados()
                obj_str = f"{r['obj']:.2f}" if r['obj'] is not None else "None"
                gap_str = f"{100*r['gap']:.2f}%" if r['gap'] is not None else "None"
                print(f"  -> Resultado: Obj={obj_str}, Gap={gap_str}, Tiempo={r['tiempo']:.1f}s, Estado={r['estado']}")

        # ----------------------------------------------------------------------
        # B. Ajuste automático con tuning de CPLEX
        # ----------------------------------------------------------------------
        TUNE_FILE = out_dir / "resultados_tune.json"
        res_tune = json.load(open(TUNE_FILE, "r", encoding="utf-8")) if TUNE_FILE.exists() else {}

        if not args.skip_tuning:
            print("\n" + "=" * 80)
            print("EJECUTANDO TUNING CPLEX (Ajuste automático de parámetros)")
            print("=" * 80)
            for nom_i, inst in instancias.items():
                if nom_i in res_tune:
                    print(f"[Omitiendo] Tuning para {nom_i} ya existe en {TUNE_FILE}")
                    continue
                tag = nom_i.replace(" ", "")
                res_tune[nom_i] = tunear(inst, tag, out_dir=out_dir, tune_time=1800, trial_limit=300)
                with open(TUNE_FILE, "w", encoding="utf-8") as f:
                    json.dump(res_tune, f, indent=2)
                print(f"  -> Tuning CPLEX {nom_i} completado: {res_tune[nom_i]}")
        else:
            print("\n[Aviso] Se omitió el tuning (--skip-tuning activado).")

        # ----------------------------------------------------------------------
        # C. Variabilidad por semilla (Instancia 1)
        # ----------------------------------------------------------------------
        SEED_FILE = out_dir / "resultados_seeds_inst1.json"
        if SEED_FILE.exists():
            print(f"\n[Semillas] Cargadas previamente desde {SEED_FILE}")
            res_seed = json.load(open(SEED_FILE, "r", encoding="utf-8"))
        else:
            print("\n" + "=" * 80)
            print("EVALUACIÓN DE VARIABILIDAD POR SEMILLA EN CPLEX (Instancia 1)")
            print("=" * 80)
            res_seed = {}
            for cfg, params in [("Baseline", {}), ("Cuts=0", {"mip.limits.cutpasses": -1})]:
                for sd in [1, 2, 3]:
                    print(f"  -> Evaluando {cfg} con Semilla {sd}...")
                    m, *_ = construir_modelo(inst1)
                    r = resolver(m, out_dir=out_dir, tl=args.time_limit,
                                 nombre=f"seed_{cfg}_{sd}", Seed=sd, **params)
                    res_seed[f"{cfg}_seed{sd}"] = r
                    t_str = f"{round(r['tiempo'], 1)} s" if r['tiempo'] is not None else "N/A"
                    print(f"     Listo: {cfg} semilla {sd} -> {t_str}, estado {r['estado']}")
            with open(SEED_FILE, "w", encoding="utf-8") as f:
                json.dump(res_seed, f, indent=2)

        # ----------------------------------------------------------------------
        # D. Baseline de la sesión para Análisis de Sensibilidad
        # ----------------------------------------------------------------------
        print("\n" + "=" * 80)
        print("GENERACIÓN DE SOLUCIONES BASELINE PARA SENSIBILIDAD EN CPLEX")
        print("=" * 80)
        res_base_file = out_dir / "resultados_baseline_sesion.json"
        res_base = json.load(open(res_base_file, "r", encoding="utf-8")) if res_base_file.exists() else {}

        for nom_i, inst in instancias.items():
            sol_expected = out_dir / f"sol_baseline_{nom_i.replace(' ', '')}.sol"
            if not sol_expected.exists():
                print(f"  -> Resolviendo baseline sesión para {nom_i}...")
                m, *_ = construir_modelo(inst)
                res_base[nom_i] = resolver(m, out_dir=out_dir, tl=args.time_limit,
                                           nombre=f"baseline_{nom_i.replace(' ', '')}")
                with open(res_base_file, "w", encoding="utf-8") as f:
                    json.dump(res_base, f, indent=2)
            else:
                print(f"  -> Archivo de solución base ya existe: {sol_expected.name}")

        # ----------------------------------------------------------------------
        # E. Análisis de Sensibilidad
        # ----------------------------------------------------------------------
        print("\n" + "=" * 80)
        print("ANÁLISIS DE SENSIBILIDAD EN CPLEX (Precios sombra y holguras)")
        print("=" * 80)
        sens1 = sensibilidad(inst1, "baseline_Instancia1", out_dir=out_dir)
        sens2 = sensibilidad(inst2, "baseline_Instancia2", out_dir=out_dir)

        if sens1 is not None:
            sens1.to_csv(out_dir / "sensibilidad_inst1.csv", index=False)
            print(f"  -> Guardado: {out_dir / 'sensibilidad_inst1.csv'}")
            print(sens1)

        if sens2 is not None:
            sens2.to_csv(out_dir / "sensibilidad_inst2.csv", index=False)
            print(f"  -> Guardado: {out_dir / 'sensibilidad_inst2.csv'}")
            print(sens2)

        # ----------------------------------------------------------------------
        # F. Inspección detallada de salida y carga
        # ----------------------------------------------------------------------
        inspeccionar_solucion(inst1, "baseline_Instancia1", out_dir=out_dir)
        inspeccionar_solucion(inst2, "baseline_Instancia2", out_dir=out_dir)

    # --------------------------------------------------------------------------
    # G. Resumen final de resultados
    # --------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("RESUMEN GENERAL DE RESULTADOS Y BRECHA DE INTEGRALIDAD (CPLEX)")
    print("=" * 80)
    if RES_FILE.exists():
        R_data = json.load(open(RES_FILE, "r", encoding="utf-8"))
        filas = []
        for nom_i, res in R_data.items():
            objs_milp = [v["obj"] for k, v in res.items() if k != "LP" and v.get("obj") is not None]
            if objs_milp and "LP" in res and res["LP"] is not None:
                z_milp = min(objs_milp)
                z_lp = res["LP"]
                brecha = 100 * (z_milp - z_lp) / z_milp if z_milp != 0 else 0
                print(f"\n{nom_i}: zLP = {z_lp:.2f} | Mejor zMILP = {z_milp:.2f} | Brecha de integralidad = {brecha:.1f} %")

            for c, v in res.items():
                if c != "LP":
                    obj_val = round(v["obj"], 2) if v.get("obj") is not None else None
                    gap_val = round(100 * v["gap"], 2) if v.get("gap") is not None else None
                    t_val = round(v["tiempo"], 1) if v.get("tiempo") is not None else None

                    estado_raw = str(v.get("estado", "")).lower()
                    if "optimal" in estado_raw or estado_raw in ("1", "101", "102", "2"):
                        estado_str = "óptimo"
                    elif "time limit" in estado_raw or estado_raw in ("11", "107", "108", "9"):
                        estado_str = "límite de tiempo"
                    else:
                        estado_str = str(v.get("estado"))

                    filas.append(dict(
                        instancia=nom_i,
                        config=c,
                        obj=obj_val,
                        gap_pct=gap_val,
                        tiempo_s=t_val,
                        estado=estado_str
                    ))

        df_resumen = pd.DataFrame(filas)
        print("\nTabla comparativa de configuraciones:")
        print(df_resumen.to_string(index=False))
        df_resumen.to_csv(out_dir / "resumen_configuraciones.csv", index=False)
        print(f"\nTabla guardada en: {out_dir / 'resumen_configuraciones.csv'}")
    else:
        print(f"No se encontró el archivo de resultados {RES_FILE}")


if __name__ == "__main__":
    main()
