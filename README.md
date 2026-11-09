# Tarea 3: Ruteo Consistente con Ventanas de Tiempo (conVRP)
**BioSur Distribución Farmacéutica**  
**Grupo:** Nicolás López, Ignacio Soto, Marcos Martínez, Gabriela Zambrano

---

## 🚀 Guía de Ejecución Local Multiplataforma

Este proyecto cuenta con dos implementaciones equivalentes para resolver el problema de ruteo consistente con ventanas de tiempo (conVRP):
1. **Gurobi**: `tarea3_gurobi.py`
2. **IBM ILOG CPLEX (DOcplex)**: `tarea3_cplex.py`

Ambos scripts soportan ejecución local en cualquier sistema operativo (**Linux**, **Windows**, **macOS**).

---

### 1. Requisitos Previos

1. **Python 3.8 o superior** instalado.
2. Instalar las dependencias del proyecto:
   ```bash
   pip install -r requirements.txt
   ```
   *(o `pip install gurobipy docplex pandas`)*

   > 💡 Para resolver con CPLEX, asegúrate de contar con el motor CPLEX instalado (`pip install cplex` para Python ≤ 3.11, o mediante el instalador académico de IBM ILOG CPLEX Optimization Studio).

---

### 2. Configuración de Solvers y Licencias

#### A. Gurobi (`gurobi.lic`)
El script busca automáticamente el archivo `gurobi.lic` en:
1. En la misma carpeta del script (`./gurobi.lic`).
2. En tu carpeta de usuario (`~` o `%USERPROFILE%`).
3. Vía parámetro: `python tarea3_gurobi.py --lic /ruta/a/gurobi.lic`.
4. Vía variable de entorno: `GRB_LICENSE_FILE`.

#### B. IBM ILOG CPLEX
El script `tarea3_cplex.py` detecta automáticamente la instalación de CPLEX Optimization Studio en las rutas estándar de Windows (`C:\Program Files\IBM\ILOG\CPLEX_Studio*`), Linux (`/opt/ibm/ILOG/CPLEX_Studio*`) y macOS (`/Applications/CPLEX_Studio*`), o mediante el parámetro:
```bash
python tarea3_cplex.py --cplex-dir /ruta/a/CPLEX_Studio
```

---

### 3. Modos de Ejecución

Ambos scripts soportan las mismas banderas CLI:

#### Ejecución con Gurobi:
- **Flujo completo**:
  ```bash
  python tarea3_gurobi.py
  ```
- **Omitir tuning** *(Recomendado para pruebas rápidas)*:
  ```bash
  python tarea3_gurobi.py --skip-tuning
  ```
- **Ajustar límite de tiempo**:
  ```bash
  python tarea3_gurobi.py --time-limit 300 --skip-tuning
  ```
- **Ver solo resumen**:
  ```bash
  python tarea3_gurobi.py --only-summary
  ```

#### Ejecución con CPLEX:
- **Flujo completo**:
  ```bash
  python tarea3_cplex.py
  ```
- **Omitir tuning** *(Recomendado para pruebas rápidas)*:
  ```bash
  python tarea3_cplex.py --skip-tuning
  ```
- **Ajustar límite de tiempo**:
  ```bash
  python tarea3_cplex.py --time-limit 300 --skip-tuning
  ```
- **Ver solo resumen**:
  ```bash
  python tarea3_cplex.py --only-summary
  ```

---

### 4. Equivalencia de Parámetros entre Gurobi y CPLEX

| Configuración | Parámetro Gurobi | Parámetro CPLEX (DOcplex) | Descripción |
| :--- | :--- | :--- | :--- |
| **Baseline** | Default | Default | Configuración predeterminada del solver |
| **Cuts=0** | `Cuts=0` | `mip.limits.cutpasses=-1` | Desactiva la generación de cortes |
| **Presolve=0** | `Presolve=0` | `preprocessing.presolve=0` | Desactiva el preprocesamiento |
| **MIPFocus=1** | `MIPFocus=1` | `emphasis.mip=1` | Énfasis en encontrar soluciones factibles |
| **MIPFocus=3** | `MIPFocus=3` | `emphasis.mip=3` | Énfasis en mejorar la cota dual / cota mejor |
| **Heuristics=0** | `Heuristics=0` | `mip.strategy.heuristicfreq=-1` | Desactiva heurísticas de búsqueda periódicas |
| **Seed** | `Seed=s` | `randomseed=s` | Semilla aleatoria del solver (1, 2, 3) |

---

### 5. Salidas y Resultados

- Salidas de Gurobi: carpeta `tarea_convrp/`
- Salidas de CPLEX: carpeta `tarea_convrp_cplex/`

Ambas carpetas contienen:
- `resultados.json`: Resultados de relajación continua y configuraciones MIP.
- `resultados_tune.json` y `*.prm`: Parámetros encontrados por el tuning.
- `resultados_seeds_inst1.json`: Tiempos y estados de variabilidad con semillas 1, 2 y 3.
- `sol_*.sol` y `sol_*.json`: Archivos de soluciones de cada configuración.
- `sensibilidad_inst1.csv` y `sensibilidad_inst2.csv`: Precios sombra y rangos de las restricciones de capacidad.
- `resumen_configuraciones.csv`: Tabla consolidada con función objetivo, gap, tiempos y estados.
