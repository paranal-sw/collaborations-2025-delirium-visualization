"""
deliriumviz.py
==============

Módulo principal de análisis de correcciones y visualización de resultados.

Este módulo provee funciones públicas para:
- Cargar y consolidar reportes de correcciones almacenados en archivos
  HTML dentro de un rango de fechas.
- Generar mapas de calor (heatmaps) que resumen la cantidad de ajustes
  realizados por día, línea de retardo y grupos de rieles.

La lógica de bajo nivel (lectura de HTML, parsing de tablas, validación
de fechas y extracción de información adicional desde el HTML) se
encuentra encapsulada en el módulo "deliriumviz_helpers".

El módulo está diseñado para ser utilizado desde una aplicación
Streamlit, pero también puede ser importado desde otros scripts Python.
"""

# -----------------------------------------------------------------------------
# Imports estándar
# -----------------------------------------------------------------------------
from pathlib import Path
from datetime import timedelta
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
    _asegurar_datetime
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
BASE_DIR = Path(__file__).resolve().parent.parent

#: Directorio donde se almacenan los reportes HTML
DATA_DIR = BASE_DIR / "data"


# -----------------------------------------------------------------------------
# Funciones públicas
# -----------------------------------------------------------------------------
def corrections_loader(fecha_inicio, fecha_fin):
    """
    Procesa reportes de correcciones en formato HTML dentro de un rango
    de fechas y retorna un DataFrame consolidado con los resultados.

    La función recorre día a día el intervalo definido por "fecha_inicio"
    y "fecha_fin", busca archivos HTML cuyo nombre siga el patrón::

        corrections_report_YYYY-MM-DD.html

    y consolida la información de todas las correcciones encontradas.

    Parameters
    ----------
    fecha_inicio : str, datetime.date o datetime.datetime
        Fecha inicial del rango. Puede entregarse como string en formato
        "YYYY-MM-DD", objeto "date" o "datetime".

    fecha_fin : str, datetime.date o datetime.datetime
        Fecha final del rango. Se aceptan los mismos formatos que
        "fecha_inicio".

    Returns
    -------
    pandas.DataFrame
        DataFrame consolidado con todas las correcciones encontradas.
        Si no se encuentran archivos válidos, se retorna un DataFrame
        vacío.
    """

    # Normalizar fechas a datetime
    fecha_inicio = _asegurar_datetime(fecha_inicio, "fecha_inicio")
    fecha_fin = _asegurar_datetime(fecha_fin, "fecha_fin")

    # Validación de zona horaria (control de errores)
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

    resultados = []
    fecha_actual = fecha_inicio

    # Iteración día a día del rango de fechas
    while fecha_actual <= fecha_fin:
        fecha_str = fecha_actual.strftime(FORMATO_FECHA)
        anio = fecha_actual.strftime("%Y")
        mes = fecha_actual.strftime("%m")

        # Construcción portable de la ruta al archivo HTML
        path = DATA_DIR / anio / mes / f"{NOMBRE_BASE}_{fecha_str}.html"
        nombre_archivo = path.name

        # Si el archivo no existe, continuar al siguiente día
        if not path.exists():
            fecha_actual += timedelta(days=1)
            continue

        try:
            # Lectura y parsing del HTML
            html = _leer_html(path)
            soup = BeautifulSoup(html, "lxml")

            # Extracción de tablas HTML
            tablas = _leer_tablas(path, nombre_archivo)

            # Procesamiento y acumulación de resultados
            resultados.extend(
                _procesar_tablas(tablas, soup, nombre_archivo)
            )

            st.success(f"Archivo procesado: {nombre_archivo}")

        except Exception as e:
            st.error(f"Error procesando {nombre_archivo}: {e}")

        fecha_actual += timedelta(days=1)

    # Consolidación final
    if resultados:
        df_final = pd.concat(resultados, ignore_index=True)

        # Asegurar formato datetime en la columna Timestamp
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

    Para cada fecha presente en el DataFrame se genera un heatmap
    independiente, renderizado directamente en Streamlit.

    Parameters
    ----------
    df_final : pandas.DataFrame
        DataFrame generado por "corrections_loader". Debe contener al
        menos las columnas:
        - "Timestamp"
        - "Rail number"
        - "Delay line number"
    """

    # Validación del DataFrame
    if df_final is None or df_final.empty:
        st.warning("El DataFrame está vacío.")
        return

    columnas_req = {"Timestamp", "Rail number", "Delay line number"}
    if not columnas_req.issubset(df_final.columns):
        st.error(f"Faltan columnas: {columnas_req - set(df_final.columns)}")
        return

    # Asegurar Timestamp como datetime
    if not pd.api.types.is_datetime64_any_dtype(df_final["Timestamp"]):
        df_final["Timestamp"] = pd.to_datetime(
            df_final["Timestamp"], errors="coerce"
        )

    # Extraer la fecha (sin hora)
    df_final["Fecha"] = df_final["Timestamp"].dt.date

    # Generar un heatmap por cada fecha
    for fecha in sorted(df_final["Fecha"].dropna().unique()):
        df_dia = df_final[df_final["Fecha"] == fecha]
        if df_dia.empty:
            continue

        max_rail = df_dia["Rail number"].max()
        if pd.isna(max_rail):
            continue

        df_dia = df_dia.copy()

        # Agrupar rieles en intervalos de tamaño 5
        df_dia["rail_bin"] = pd.cut(
            df_dia["Rail number"],
            bins=range(0, int(max_rail) + 10, 5)
        )

        # Tabla de contingencia
        tabla = pd.crosstab(
            df_dia["Delay line number"],
            df_dia["rail_bin"]
        )

        if tabla.empty:
            continue

        # Visualización
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
