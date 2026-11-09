#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ruteo consistente con ventanas de tiempo (conVRP) – BioSur Distribución Farmacéutica
Adaptado de tarea3_gurobi.ipynb para ejecución local multiplataforma (Linux, Windows, macOS).

Grupo: Nicolás López, Ignacio Soto, Marcos Martínes, Gabriela Zambrano
"""

import os
import sys
import json
import math
import shutil
import platform
import argparse
from pathlib import Path

# ==============================================================================
# 1. CONFIGURACIÓN DE LICENCIA GUROBI MULTIPLATAFORMA
# ==============================================================================

def configurar_licencia(lic_path_param=None):
    """
    Busca y configura automáticamente el archivo de licencia gurobi.lic
    de forma multiplataforma (Linux, Windows, macOS).

    Cada integrante del grupo puede tener un sistema operativo y una licencia
    académica individual diferente (con su propio HOSTNAME, LICENSEID, HOSTID y KEY).

    Prioridad de búsqueda:
      1. Parámetro explícito (--lic o lic_path_param)
      2. Variable de entorno GRB_LICENSE_FILE
      3. Carpeta actual de ejecución (./gurobi.lic)
      4. Carpeta donde reside este script
      5. Directorio de usuario (~ o %USERPROFILE%)
      6. Rutas estándar por sistema operativo:
         - Linux: /opt/gurobi/gurobi.lic, /usr/local/gurobi/gurobi.lic
         - macOS: /Library/gurobi/gurobi.lic, ~/Library/gurobi.lic
         - Windows: C:\\gurobi\\gurobi.lic, C:\\gurobi\\license\\gurobi.lic
    """
    candidatos = []

    # 1. Parámetro explícito
    if lic_path_param:
        candidatos.append(Path(lic_path_param))

    # 2. Variable de entorno ya definida
    env_lic = os.environ.get("GRB_LICENSE_FILE")
    if env_lic:
        candidatos.append(Path(env_lic))

    # 3. Directorio de trabajo y del script
    script_dir = Path(__file__).resolve().parent
    cwd = Path.cwd()
    candidatos.append(cwd / "gurobi.lic")
    candidatos.append(script_dir / "gurobi.lic")

    # 4. Carpeta de usuario
    home = Path.home()
    candidatos.append(home / "gurobi.lic")

    # 5. Rutas estándar según el sistema operativo
    so = platform.system().lower()
    if "windows" in so:
        user_prof = os.environ.get("USERPROFILE")
        if user_prof:
            candidatos.append(Path(user_prof) / "gurobi.lic")
        candidatos.extend([
            Path("C:/gurobi/gurobi.lic"),
            Path("C:/gurobi/license/gurobi.lic"),
        ])
    elif "darwin" in so:  # macOS
        candidatos.extend([
            Path("/Library/gurobi/gurobi.lic"),
            home / "Library" / "gurobi.lic",
        ])
    else:  # Linux (Fedora, Ubuntu, Debian, etc.)
        candidatos.extend([
            Path("/opt/gurobi/gurobi.lic"),
            Path("/usr/local/gurobi/gurobi.lic"),
            Path("/etc/gurobi.lic"),
        ])

    licencia_encontrada = None
    for cand in candidatos:
        try:
            if cand and cand.is_file():
                licencia_encontrada = cand.resolve()
                break
        except Exception:
            continue

    if licencia_encontrada:
        os.environ["GRB_LICENSE_FILE"] = str(licencia_encontrada)
        print(f"[Licencia Gurobi] Detectada y configurada exitosamente:")
        print(f"  -> Archivo: {licencia_encontrada}")
        print(f"  -> Sistema Operativo: {platform.system()} ({platform.release()})")
        print(f"  -> Hostname actual: {platform.node()}")
        return str(licencia_encontrada)
    else:
        print("=" * 80)
        print("[AVISO] No se encontró automáticamente un archivo 'gurobi.lic'.")
        print(f"Sistema Operativo detectado: {platform.system()} | Hostname: {platform.node()}")
        print("Lugares verificados:")
        for c in candidatos:
            print(f"  - {c}")
        print("\nPara ejecutar el modelo, cada integrante debe:")
        print("  1. Obtener su licencia académica individual en gurobi.com")
        print("  2. Ejecutar 'grbgetkey <TU_CODIGO_KEY>' o colocar el archivo 'gurobi.lic'")
        print("     en la misma carpeta de este script o en su directorio de usuario.")
        print("  3. Alternativamente, pasar la ruta con: python tarea3_gurobi.py --lic /ruta/a/gurobi.lic")
        print("=" * 80)
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
    ventana = {c["id"]: (c["ready"], c["due"]) for c in clientes}   # todos tienen ventana
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
# 3. CONSTRUCCIÓN DEL MODELO MATEMÁTICO (conVRP)
# ==============================================================================

def construir_modelo(inst):
    """
    Construye el modelo MIP en Gurobi según Campelo et al. (2019) adaptado:
      - X[r, i, j, t]: variable binaria de arco recorrido en día t por ruta r
      - Z[r, i]: variable binaria de asignación consistente cliente-ruta
      - W[i, t]: variable continua de inicio de servicio en cliente i, día t
      - dW[r]: variable continua de salida del depósito de ruta r (constante los 3 días)
      - rW[r, t]: variable continua de retorno al depósito de ruta r en día t
    """
    from gurobipy import Model, GRB, quicksum

    N, V, T, R, dist, tt, s, ventana, d, Q, t_open, t_close = inst
    m = Model("conVRP_BioSur")

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

    # Variables
    X  = m.addVars(arcos, vtype=GRB.BINARY, name="x")
    Z  = m.addVars(R, N, vtype=GRB.BINARY, name="z")
    W  = m.addVars(N, T, lb=0, ub=t_close, name="w")     # inicio de servicio (sin ruta)
    dW = m.addVars(R, lb=0, ub=t_close, name="dW")       # salida de la ruta (sin día)
    rW = m.addVars(R, T, lb=0, ub=t_close, name="rW")    # retorno al depósito

    # (1) Función Objetivo: minimizar distancia total recorrida
    m.setObjective(quicksum(dist[i, j] * X[r, i, j, t] for (r, i, j, t) in arcos), GRB.MINIMIZE)

    # (2) Asignación única cliente-ruta en todo el horizonte
    for i in N:
        m.addConstr(Z.sum('*', i) == 1, name=f"asig_{i}")

    # (3) Entrada a cada cliente y (4) salida de cada cliente
    for r in R:
        for t in T:
            for j in N:
                if d[j, t] > 0:
                    # Si el cliente tiene demanda el día t, lo visita su ruta asignada
                    m.addConstr(X.sum(r, '*', j, t) == Z[r, j], name=f"entra_{r}_{j}_{t}")
                    m.addConstr(X.sum(r, j, '*', t) == Z[r, j], name=f"sale_{r}_{j}_{t}")
                else:
                    # Si no tiene demanda ese día, ningún vehículo entra ni sale de este cliente
                    m.addConstr(X.sum(r, '*', j, t) == 0, name=f"entra_{r}_{j}_{t}")
                    m.addConstr(X.sum(r, j, '*', t) == 0, name=f"sale_{r}_{j}_{t}")

    # (5) Cada ruta sale del depósito cada día
    for r in R:
        for t in T:
            m.addConstr(X.sum(r, 0, '*', t) == 1, name=f"sale_dep_{r}_{t}")

    # (7) Tiempos de inicio de servicio entre clientes consecutivos (Big-M)
    for r in R:
        for t in T:
            for i in N:
                for j in N:
                    if i != j:
                        M_ij = max(0, ventana[i][1] + s[i] + tt[i, j] - ventana[j][0])
                        m.addConstr(W[i, t] + s[i] + tt[i, j] <= W[j, t] + M_ij * (1 - X[r, i, j, t]),
                                    name=f"tiempo_{r}_{i}_{j}_{t}")

    # (8) Ventanas de tiempo para cada cliente
    for i in N:
        for t in T:
            m.addConstr(W[i, t] >= ventana[i][0], name=f"vent_lo_{i}_{t}")
            m.addConstr(W[i, t] <= ventana[i][1], name=f"vent_up_{i}_{t}")

    # (9) Salida del depósito -> primer cliente (dW constante para todos los días)
    for r in R:
        for t in T:
            for j in N:
                M_0j = max(0, t_close + tt[0, j] - ventana[j][0])
                m.addConstr(dW[r] + tt[0, j] <= W[j, t] + M_0j * (1 - X[r, 0, j, t]),
                            name=f"salida_{r}_{j}_{t}")

    # (10) Último cliente -> retorno al depósito (nodo fin)
    for r in R:
        for t in T:
            for i in N:
                M_if = max(0, ventana[i][1] + s[i] + tt[i, fin] - t_open)
                m.addConstr(W[i, t] + s[i] + tt[i, fin] <= rW[r, t] + M_if * (1 - X[r, i, fin, t]),
                            name=f"retorno_{r}_{i}_{t}")

    # (11)-(12) Horario de apertura y cierre del depósito
    for r in R:
        m.addConstr(dW[r] >= t_open, name=f"apertura_{r}")
        for t in T:
            m.addConstr(rW[r, t] <= t_close, name=f"cierre_{r}_{t}")

    # (14) Capacidad máxima de cada vehículo en cada día
    for r in R:
        for t in T:
            m.addConstr(quicksum(d[i, t] * Z[r, i] for i in N) <= Q, name=f"cap_{r}_{t}")

    m.update()
    return m, X, Z, W, dW, rW


# ==============================================================================
# 4. FUNCIONES DE RESOLUCIÓN Y EXPERIMENTACIÓN
# ==============================================================================

def resolver(m, out_dir, tl=600, nombre=None, **params):
    """Resuelve un modelo Gurobi con límite de tiempo, 1 thread y guarda logs/soluciones."""
    m.Params.Threads = 1
    m.Params.TimeLimit = tl

    if nombre:
        ruta_log = out_dir / f"log_{nombre}.txt"
        if ruta_log.exists():
            try:
                ruta_log.unlink()
            except Exception:
                pass
        m.Params.LogFile = str(ruta_log)

    for k, v in params.items():
        m.setParam(k, v)

    m.optimize()

    ok = m.SolCount > 0
    if ok and nombre:
        ruta_sol = out_dir / f"sol_{nombre}.sol"
        m.write(str(ruta_sol))

    return dict(
        obj=m.ObjVal if ok else None,
        gap=m.MIPGap if ok else None,
        cota=m.ObjBound if ok else None,
        tiempo=m.Runtime,
        estado=m.Status
    )


def relajacion(inst):
    """Calcula la cota inferior mediante la relajación continua (LP)."""
    m, *_ = construir_modelo(inst)
    rel = m.relax()
    rel.Params.Threads = 1
    rel.optimize()
    return rel.ObjVal


def leer_prm(path):
    """Lee un archivo .prm generado por Gurobi tuning."""
    d = {}
    with open(path, "r", encoding="utf-8") as f:
        for l in f:
            l = l.strip()
            if l and not l.startswith("#"):
                partes = l.split(None, 1)
                if len(partes) == 2:
                    d[partes[0]] = partes[1]
    return d


def tunear(inst, nombre, out_dir, tune_time=1800, trial_limit=300):
    """Ejecuta el proceso automático de ajuste de hiperparámetros (tune) de Gurobi."""
    m, *_ = construir_modelo(inst)
    m.Params.Threads = 1
    m.Params.TimeLimit = trial_limit
    m.Params.TuneTimeLimit = tune_time
    m.Params.LogFile = str(out_dir / f"log_tune_{nombre}.txt")

    print(f"\n[Tuning] Iniciando tuning para {nombre} (TuneTimeLimit={tune_time}s)...")
    m.tune()

    if m.TuneResultCount == 0:
        return {"nota": "tune no encontró nada mejor"}

    m.getTuneResult(0)
    prm = out_dir / f"tune_{nombre}.prm"
    m.write(str(prm))

    m2, *_ = construir_modelo(inst)
    m2.read(str(prm))
    res = resolver(m2, out_dir=out_dir, tl=600, nombre=f"tuned_{nombre}")
    ignorar = {"Threads", "TimeLimit", "LogFile", "TuneTimeLimit"}
    res["parametros"] = {k: v for k, v in leer_prm(prm).items() if k not in ignorar}
    return res


def sensibilidad(inst, nombre, out_dir):
    """Realiza análisis de sensibilidad fijando las variables enteras y resolviendo el modelo fijo."""
    from gurobipy import GRB
    import pandas as pd

    N, V, T, R, dist, tt, s, ventana, d, Q, t_open, t_close = inst
    m, X, Z, W, dW, rW = construir_modelo(inst)

    sol_path = out_dir / f"sol_{nombre}.sol"
    if not sol_path.exists():
        print(f"[Sensibilidad] AVISO: No se encontró la solución {sol_path}. Ejecute baseline primero.")
        return None

    m.read(str(sol_path))
    m.update()

    for v in m.getVars():
        if v.VType == GRB.BINARY:
            v.LB = v.UB = round(v.Start)

    m.Params.Threads = 1
    m.optimize()
    print(f"[Sensibilidad {nombre}] Objetivo con enteros fijos: {m.ObjVal:.2f}")

    f = m.fixed()
    f.Params.Threads = 1
    f.Params.Presolve = 0
    f.Params.Method = 1  # Simplex Dual
    f.optimize()

    filas = []
    for r in R:
        for t in T:
            c = f.getConstrByName(f"cap_{r}_{t}")
            carga = sum(d[i, t] * round(Z[r, i].X) for i in N)
            filas.append(dict(
                ruta=r,
                dia=t,
                carga=carga,
                Q=Q,
                holgura=c.Slack,
                precio_sombra=c.Pi,
                SARHSLow=c.SARHSLow,
                SARHSUp=c.SARHSUp
            ))

    df_sens = pd.DataFrame(filas)
    return df_sens


def inspeccionar_solucion(inst, nombre, out_dir):
    """Muestra hora de salida más tardía desde depósito y la carga por vehículo/día."""
    N, V, T, R, dist, tt, s, ventana, d, Q, t_open, t_close = inst
    sol_path = out_dir / f"sol_{nombre}.sol"
    if not sol_path.exists():
        return

    m, X, Z, W, dW, rW = construir_modelo(inst)
    m.read(str(sol_path))
    m.update()

    print(f"\n=======================================================")
    print(f"ANÁLISIS DE RUTAS Y HORAS: {nombre}")
    print(f"=======================================================")
    print("--- HORA DE SALIDA DEL DEPÓSITO (la más tardía compatible con la solución) ---")
    for r in R:
        salidas = [
            W[j, t].Start - tt[0, j]
            for t in T for j in N
            if X[r, 0, j, t].Start > 0.5
        ]
        if salidas:
            print(f"  Vehículo {r}: sale como máximo a las {min(salidas):.2f}")

    print(f"\n--- CARGA POR VEHÍCULO Y DÍA (Capacidad Q = {Q}) ---")
    for t in T:
        print(f"\n  Día {t}:")
        for r in R:
            clientes_r = [i for i in N if Z[r, i].Start > 0.5]
            carga = sum(d[i, t] for i in clientes_r)
            print(f"    Vehículo {r}: Carga = {carga}/{Q} (Clientes: {clientes_r})")


# ==============================================================================
# 5. PIPELINE PRINCIPAL
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Optimización conVRP con Gurobi (BioSur Distribución Farmacéutica)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("--lic", type=str, default=None,
                        help="Ruta específica al archivo gurobi.lic individual.")
    parser.add_argument("--dir", type=str, default="tarea_convrp",
                        help="Carpeta donde guardar los archivos de salida, logs y soluciones.")
    parser.add_argument("--time-limit", type=int, default=600,
                        help="Límite de tiempo en segundos por corrida.")
    parser.add_argument("--skip-tuning", action="store_true",
                        help="Omitir el ajuste automático (tuning), que puede tomar hasta 1 hora.")
    parser.add_argument("--only-summary", action="store_true",
                        help="Solo leer los resultados existentes e imprimir las tablas de resumen.")
    args = parser.parse_args()

    # Configuración de carpeta de trabajo (local al script)
    script_dir = Path(__file__).resolve().parent
    out_dir = script_dir / args.dir
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"[Directorio de Resultados] {out_dir}")

    # Configuración de licencia
    configurar_licencia(args.lic)

    # Verificar importación de gurobipy
    try:
        import gurobipy as gp
        print(f"[Gurobi Version] {gp.gurobi.version()}")
    except ImportError:
        print("\n[ERROR FATAL] La librería 'gurobipy' no está instalada en este entorno Python.")
        print("Instálala ejecutando:")
        print("    pip install gurobipy")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR DE GUROBI] {e}")
        print("Verifica que tu archivo gurobi.lic sea válido y corresponda al HOSTNAME de esta máquina.")
        sys.exit(1)

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
        configs = {
            "Baseline": {},
            "Cuts=0": {"Cuts": 0},
            "Presolve=0": {"Presolve": 0},
            "MIPFocus=1": {"MIPFocus": 1},
            "MIPFocus=3": {"MIPFocus": 3},
            "Heuristics=0": {"Heuristics": 0},
        }

        print("\n" + "=" * 80)
        print("EJECUTANDO RELAJACIONES Y CONFIGURACIONES DEL SOLVER")
        print("=" * 80)

        for nom_i, inst in instancias.items():
            resultados.setdefault(nom_i, {})
            # Relajación continua
            if "LP" not in resultados[nom_i]:
                print(f"\n[LP] Calculando relajación continua para {nom_i}...")
                resultados[nom_i]["LP"] = relajacion(inst)
                guardar_resultados()
                print(f"  -> LP Obj: {resultados[nom_i]['LP']:.2f}")

            # Configuraciones MIP
            for nom_c, params in configs.items():
                if nom_c in resultados[nom_i]:
                    print(f"[Omitiendo] {nom_i} - {nom_c} ya está resuelto en {RES_FILE}")
                    continue

                print(f"\n[Resolviendo] {nom_i} con configuración '{nom_c}' (TimeLimit={args.time_limit}s)...")
                m, *_ = construir_modelo(inst)
                nombre_run = f"{nom_c}_{nom_i.replace(' ', '')}"
                r = resolver(m, out_dir=out_dir, tl=args.time_limit, nombre=nombre_run, **params)
                resultados[nom_i][nom_c] = r
                guardar_resultados()
                print(f"  -> Resultado: Obj={r['obj']}, Gap={r['gap']}, Tiempo={r['tiempo']:.1f}s, Estado={r['estado']}")

        # ----------------------------------------------------------------------
        # B. Ajuste automático con model.tune()
        # ----------------------------------------------------------------------
        TUNE_FILE = out_dir / "resultados_tune.json"
        res_tune = json.load(open(TUNE_FILE, "r", encoding="utf-8")) if TUNE_FILE.exists() else {}

        if not args.skip_tuning:
            print("\n" + "=" * 80)
            print("EJECUTANDO TUNING (Ajuste automático de parámetros)")
            print("=" * 80)
            for nom_i, inst in instancias.items():
                if nom_i in res_tune:
                    print(f"[Omitiendo] Tuning para {nom_i} ya existe en {TUNE_FILE}")
                    continue
                tag = nom_i.replace(" ", "")
                res_tune[nom_i] = tunear(inst, tag, out_dir=out_dir, tune_time=1800, trial_limit=300)
                with open(TUNE_FILE, "w", encoding="utf-8") as f:
                    json.dump(res_tune, f, indent=2)
                print(f"  -> Tuning {nom_i} completado: {res_tune[nom_i]}")
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
            print("EVALUACIÓN DE VARIABILIDAD POR SEMILLA (Instancia 1)")
            print("=" * 80)
            res_seed = {}
            for cfg, params in [("Baseline", {}), ("Cuts=0", {"Cuts": 0})]:
                for sd in [1, 2, 3]:
                    print(f"  -> Evaluando {cfg} con Semilla {sd}...")
                    m, *_ = construir_modelo(inst1)
                    m.Params.LogToConsole = 0
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
        print("GENERACIÓN DE SOLUCIONES BASELINE PARA SENSIBILIDAD")
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
        print("ANÁLISIS DE SENSIBILIDAD (Precios sombra y holguras)")
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
    print("RESUMEN GENERAL DE RESULTADOS Y BRECHA DE INTEGRALIDAD")
    print("=" * 80)
    if RES_FILE.exists():
        R = json.load(open(RES_FILE, "r", encoding="utf-8"))
        filas = []
        for nom_i, res in R.items():
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
                    estado_str = "óptimo" if v.get("estado") == 2 else ("límite de tiempo" if v.get("estado") == 9 else str(v.get("estado")))
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
