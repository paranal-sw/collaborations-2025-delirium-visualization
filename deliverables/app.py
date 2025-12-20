"""
app.py
======

Aplicación Streamlit para la visualización de reportes de correcciones.

Esta aplicación permite:
- Seleccionar un rango de fechas mediante la interfaz gráfica.
- Cargar y consolidar reportes de correcciones en formato HTML.
- Visualizar los resultados en una tabla interactiva.
- Generar mapas de calor por día, línea de retardo y grupos
  de rieles.

La lógica de procesamiento y visualización se encuentra encapsulada
en el módulo "deliriumviz", el cual es importado desde este archivo.

Este script debe ejecutarse con:

    streamlit run app.py
"""

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------
import streamlit as st
from datetime import date

# Importación de funciones públicas del módulo principal
# (estructura compatible con GitHub y Streamlit Cloud)
from deliriumviz import corrections_loader, heatmap


# -----------------------------------------------------------------------------
# Configuración general de la aplicación
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Corrections report viewer",
    layout="wide"
)

st.title("Corrections report viewer")


# -----------------------------------------------------------------------------
# Inputs de fechas
# -----------------------------------------------------------------------------
# Se utilizan dos columnas para seleccionar la fecha de inicio y fin
col1, col2 = st.columns(2)

with col1:
    fecha_inicio = st.date_input(
        "Fecha inicio",
        value=date(2022, 7, 10),
        help="Seleccione la fecha inicial del rango a analizar."
    )

with col2:
    fecha_fin = st.date_input(
        "Fecha fin",
        value=date(2022, 7, 15),
        help="Seleccione la fecha final del rango a analizar."
    )


# -----------------------------------------------------------------------------
# Acción principal
# -----------------------------------------------------------------------------
# Al presionar el botón se cargan y procesan los reportes
if st.button("Cargar reportes"):

    # Llamada a la función principal de carga
    # Las fechas tipo `date` son convertidas internamente a `datetime`
    df = corrections_loader(fecha_inicio, fecha_fin)

    # Validación del resultado
    if df.empty:
        st.warning("No se encontraron datos para el rango seleccionado.")
    else:
        # Visualización de la tabla consolidada
        st.subheader("Tabla de correcciones")
        st.dataframe(df, use_container_width=True)

        # Visualización de los mapas de calor
        st.subheader("Heatmap de correcciones")
        heatmap(df)
