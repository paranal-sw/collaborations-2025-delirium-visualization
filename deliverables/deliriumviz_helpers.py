"""
deliriumviz_helpers.py
=====================

Módulo de funciones auxiliares (helpers) para el procesamiento de
reportes de correcciones en formato HTML.

Este módulo encapsula la lógica de bajo nivel utilizada por el módulo
principal "deliriumviz", incluyendo:

- Lectura de archivos HTML desde disco.
- Extracción de tablas HTML mediante pandas.
- Parsing de información específica desde el contenido HTML (por ejemplo, humedad relativa).
- Procesamiento y consolidación de tablas en estructuras pandas.
- Búsqueda robusta de reportes HTML dentro de un rango de fechas,
  incluso si los archivos están mal organizados en carpetas.

Las funciones definidas en este módulo son internas
y NO están pensadas para ser utilizadas directamente por el usuario
final. Deben ser llamadas únicamente desde "deliriumviz.py".
"""

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------
import re
from datetime import datetime
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup


# -----------------------------------------------------------------------------
# Lectura de archivos
# -----------------------------------------------------------------------------
def _leer_html(path):
    """
    Lee el contenido completo de un archivo HTML y lo retorna como texto.
    """
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _leer_tablas(path, nombre_archivo):
    """
    Lee las tablas HTML de un archivo utilizando pandas.
    """
    try:
        return pd.read_html(path, index_col=0)
    except Exception as e:
        print(f"Error leyendo tablas en {nombre_archivo}: {e}")
        return []


# -----------------------------------------------------------------------------
# Utilidades de parsing HTML
# -----------------------------------------------------------------------------
def _extraer_humedad(soup, nombre_archivo):
    """
    Extrae el valor de humedad relativa desde etiquetas <h3> del HTML.
    """
    try:
        for tag in soup.find_all("h3"):
            match = re.search(r"(\d+(\.\d+)?)%", tag.get_text())
            if match:
                return float(match.group(1))
    except Exception as e:
        print(f"Error extrayendo humedad en {nombre_archivo}: {e}")

    return None


def _asegurar_datetime(fecha, nombre_parametro):
    """
    Asegura que una fecha esté en formato datetime.datetime.
    """
    if isinstance(fecha, str):
        try:
            return datetime.strptime(fecha, "%Y-%m-%d")
        except ValueError:
            raise ValueError(
                f"{nombre_parametro} debe tener formato 'YYYY-MM-DD'"
            )

    if isinstance(fecha, datetime):
        return fecha

    if hasattr(fecha, "strftime"):
        return datetime.combine(fecha, datetime.min.time())

    raise TypeError(
        f"{nombre_parametro} debe ser datetime o string 'YYYY-MM-DD'"
    )


# -----------------------------------------------------------------------------
# Búsqueda robusta de archivos HTML
# -----------------------------------------------------------------------------
from pathlib import Path
from datetime import datetime
import re


def _buscar_reportes_html(
    data_dir,
    nombre_base,
    fecha_inicio,
    fecha_fin,
    formato_fecha="%Y-%m-%d"
):
    """
    Busca archivos HTML de reportes dentro de un rango de fechas,
    independientemente de la organización de carpetas.

    La fecha se extrae desde el nombre del archivo, por ejemplo:
    corrections_report_2022-06-15.html

    Se ignoran explícitamente archivos basura generados por macOS
    (prefijo '._'), los cuales NO son HTML válidos.

    Parámetros
    ----------
    data_dir : pathlib.Path or str
        Directorio base donde se almacenan los reportes.
    nombre_base : str
        Prefijo base del archivo (ej. "corrections_report").
    fecha_inicio : datetime.datetime
        Fecha inicial del rango.
    fecha_fin : datetime.datetime
        Fecha final del rango.
    formato_fecha : str, optional
        Formato esperado de la fecha en el nombre del archivo.
        Por defecto "%Y-%m-%d".

    Retorna
    -------
    list[pathlib.Path]
        Lista ordenada de rutas a archivos HTML válidos dentro del rango.
    """
    data_dir = Path(data_dir)
    resultados = []

    # Patrón: corrections_report_YYYY-MM-DD.html
    patron = re.compile(
        rf"^{re.escape(nombre_base)}_(\d{{4}}-\d{{2}}-\d{{2}})\.html$"
    )

    for path in data_dir.rglob("*.html"):
        nombre = path.name

        # ------------------------------------------------------------------
        # Ignorar archivos basura de macOS (AppleDouble)
        # ------------------------------------------------------------------
        if nombre.startswith("._"):
            continue

        match = patron.match(nombre)
        if not match:
            continue

        try:
            fecha_archivo = datetime.strptime(
                match.group(1), formato_fecha
            )
        except ValueError:
            continue

        if fecha_inicio <= fecha_archivo <= fecha_fin:
            resultados.append(path)

    return sorted(resultados)

# -----------------------------------------------------------------------------
# Procesamiento principal de tablas
# -----------------------------------------------------------------------------
def _procesar_tablas(tablas, soup, nombre_archivo):
    """
    Procesa las tablas extraídas de un archivo HTML y genera DataFrames
    consolidados con la información de correcciones.
    """
    resultados = []

    for i in range(0, len(tablas) - 1, 2):
        try:
            n_repeat = tablas[i + 1].shape[0]
            if n_repeat == 0:
                continue

            tabla_transpuesta = tablas[i].T

            columnas_req = {"Timestamp", "Delay line number"}
            if not columnas_req.issubset(tabla_transpuesta.columns):
                continue

            test_pd = tabla_transpuesta[list(columnas_req)].copy()
            test_pd["Timestamp"] = pd.to_datetime(
                test_pd["Timestamp"], errors="coerce"
            )

            if test_pd.empty:
                continue

            test_pd_repeated = pd.concat(
                [test_pd] * n_repeat
            ).reset_index(drop=True)

            tabla_correcciones = (
                tablas[i + 1]
                .droplevel(0, axis=1)
                .rename_axis("Rail number")
                .reset_index(drop=False)
            )

            humidity = _extraer_humedad(soup, nombre_archivo)

            humedad_df = pd.DataFrame({
                "Tunnel Relative Humidity": [
                    f"{humidity}%" if humidity is not None else None
                ] * n_repeat
            })

            resultados.append(
                pd.concat(
                    [test_pd_repeated, humedad_df, tabla_correcciones],
                    axis=1
                )
            )

        except Exception as e:
            print(f"Error procesando tablas en {nombre_archivo}: {e}")

    return resultados
