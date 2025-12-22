"""
deliriumviz.py
==============

Módulo principal de análisis de correcciones y visualización de resultados.

Este módulo provee funciones públicas para:
- Cargar y consolidar reportes de correcciones almacenados en archivos 
HTML dentro de un rango de fechas.
- Generar mapas de calor que resumen la cantidad de ajustes realizados 
por día, línea de retardo y grupos de rieles.

La lógica de bajo nivel (lectura de HTML, parsing de tablas, validación
de fechas, búsqueda de archivos y extracción de información adicional)
se encuentra encapsulada en el módulo "deliriumviz_helpers".
"""

# -----------------------------------------------------------------------------
# Imports estándar
# -----------------------------------------------------------------------------
from pathlib import Path
from zoneinfo import ZoneInfo

# -----------------------------------------------------------------------------
# Imports de terceros
# -----------------------------------------------------------------------------
import pandas as pd
from bs4 import BeautifulSoup
import matplotlib.pyplot as plt
import seaborn as sns
import streamlit as st

# -----------------------------------------------------------------------------
# Imports locales (helpers internos)
# -----------------------------------------------------------------------------
from deliriumviz_helpers import (
    _leer_html,
    _leer_tablas,
    _procesar_tablas,
    _asegurar_datetime,
    _buscar_reportes_html,
)

# -----------------------------------------------------------------------------
# Configuración global
# -----------------------------------------------------------------------------

#: Zona horaria local utilizada para validación de fechas
ZONA_LOCAL = "America/Santiago"

#: Prefijo base de los archivos HTML de correcciones
NOMBRE_BASE = "corrections_report"

#: Formato esperado para las fechas en los nombres de archivo
FORMATO_FECHA = "%Y-%m-%d"

#: Directorio base del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent  # Para GitHub

#: Directorio donde se almacenan los reportes HTML
DATA_DIR = BASE_DIR / "data"

# -----------------------------------------------------------------------------
# Funciones públicas
# -----------------------------------------------------------------------------
def corrections_loader(fecha_inicio, fecha_fin):
    """
    Procesa reportes de correcciones en formato HTML dentro de un rango
    de fechas y retorna un DataFrame consolidado con los resultados.

    La función busca archivos HTML cuyo nombre siga el patrón::

        corrections_report_YYYY-MM-DD.html

    independientemente de cómo estén organizados en el árbol de carpetas.

    Parameters
    ----------
    fecha_inicio : str, datetime.date o datetime.datetime
        Fecha inicial del rango.

    fecha_fin : str, datetime.date o datetime.datetime
        Fecha final del rango.

    Returns
    -------
    pandas.DataFrame
        DataFrame consolidado con todas las correcciones encontradas.
        Si no se encuentran archivos válidos, se retorna un DataFrame vacío.
    """

    # -----------------------------------------------------------------
    # Normalización y validación de fechas
    # -----------------------------------------------------------------
    fecha_inicio = _asegurar_datetime(fecha_inicio, "fecha_inicio")
    fecha_fin = _asegurar_datetime(fecha_fin, "fecha_fin")

    try:
        fecha_inicio.replace(
            tzinfo=ZoneInfo(ZONA_LOCAL)
        ).astimezone(ZoneInfo("UTC"))

        fecha_fin.replace(
            tzinfo=ZoneInfo(ZONA_LOCAL)
        ).astimezone(ZoneInfo("UTC"))
    except Exception as e:
        st.error(f"Error convirtiendo fechas: {e}")
        return pd.DataFrame()

    # -----------------------------------------------------------------
    # Búsqueda flexible de archivos HTML
    # -----------------------------------------------------------------
    paths_html = _buscar_reportes_html(
        data_dir=DATA_DIR,
        nombre_base=NOMBRE_BASE,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        formato_fecha=FORMATO_FECHA,
    )

    if not paths_html:
        st.warning("No se encontraron archivos HTML en el rango indicado.")
        return pd.DataFrame()

    # -----------------------------------------------------------------
    # Procesamiento de archivos encontrados
    # -----------------------------------------------------------------
    resultados = []

    for path in paths_html:
        nombre_archivo = path.name

        try:
            html = _leer_html(path)
            soup = BeautifulSoup(html, "lxml")
            tablas = _leer_tablas(path, nombre_archivo)

            resultados.extend(
                _procesar_tablas(tablas, soup, nombre_archivo)
            )

            st.success(f"Archivo procesado: {nombre_archivo}")

        except Exception as e:
            st.error(f"Error procesando {nombre_archivo}: {e}")

    # -----------------------------------------------------------------
    # Consolidación final
    # -----------------------------------------------------------------
    if resultados:
        df_final = pd.concat(resultados, ignore_index=True)

        df_final["Timestamp"] = pd.to_datetime(
            df_final["Timestamp"], errors="coerce"
        )

        return df_final

    st.warning("No se generaron resultados")
    return pd.DataFrame()


def heatmap(df_final):
    """
    Genera mapas de calor de la cantidad de ajustes por día,
    agrupando por línea de retardo y por intervalos de Rail number.

    Parameters
    ----------
    df_final : pandas.DataFrame
        DataFrame generado por "corrections_loader".
    """

    if df_final is None or df_final.empty:
        st.warning("El DataFrame está vacío.")
        return

    columnas_req = {"Timestamp", "Rail number", "Delay line number"}
    if not columnas_req.issubset(df_final.columns):
        st.error(f"Faltan columnas: {columnas_req - set(df_final.columns)}")
        return

    if not pd.api.types.is_datetime64_any_dtype(df_final["Timestamp"]):
        df_final["Timestamp"] = pd.to_datetime(
            df_final["Timestamp"], errors="coerce"
        )

    df_final["Fecha"] = df_final["Timestamp"].dt.date

    for fecha in sorted(df_final["Fecha"].dropna().unique()):
        df_dia = df_final[df_final["Fecha"] == fecha]
        if df_dia.empty:
            continue

        max_rail = df_dia["Rail number"].max()
        if pd.isna(max_rail):
            continue

        df_dia = df_dia.copy()
        df_dia["rail_bin"] = pd.cut(
            df_dia["Rail number"],
            bins=range(0, int(max_rail) + 10, 5)
        )

        tabla = pd.crosstab(
            df_dia["Delay line number"],
            df_dia["rail_bin"]
        )

        if tabla.empty:
            continue

        st.subheader(f"Mapa de calor – {fecha}")

        fig, ax = plt.subplots(figsize=(12, 6))
        sns.heatmap(
            tabla,
            annot=True,
            fmt="d",
            cmap="YlGnBu",
            linewidths=0.5,
            ax=ax
        )

        ax.set_xlabel("Grupo de rieles")
        ax.set_ylabel("Línea de retardo")

        st.pyplot(fig)
        plt.close(fig)
