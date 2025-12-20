"""
deliriumviz_helpers.py
=====================

Módulo de funciones auxiliares (helpers) para el procesamiento de
reportes de correcciones en formato HTML.

Este módulo encapsula la lógica de bajo nivel utilizada por el módulo
principal "deliriumviz", incluyendo:

- Lectura de archivos HTML desde disco.
- Extracción de tablas HTML mediante pandas.
- Parsing de información específica desde el contenido HTML
  (por ejemplo, humedad relativa).
- Procesamiento y consolidación de tablas en estructuras pandas.

Las funciones definidas en este módulo son internas (prefijo "_")
y NO están pensadas para ser utilizadas directamente por el usuario
final. Deben ser llamadas únicamente desde "deliriumviz.py".
"""

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------
import re
from datetime import datetime

import pandas as pd
from bs4 import BeautifulSoup


# -----------------------------------------------------------------------------
# Lectura de archivos
# -----------------------------------------------------------------------------
def _leer_html(path):
    """
    Lee el contenido completo de un archivo HTML y lo retorna como texto.

    Parámetros
    ----------
    path : str o pathlib.Path
        Ruta al archivo HTML.

    Retorna
    -------
    str
        Contenido completo del archivo HTML.

    Excepciones
    -----------
    IOError
        Si el archivo no puede abrirse o leerse.
    """
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _leer_tablas(path, nombre_archivo):
    """
    Lee las tablas HTML de un archivo utilizando pandas.

    Esta función intenta extraer todas las tablas presentes en el
    archivo HTML. En caso de error, se imprime un mensaje descriptivo
    y se retorna una lista vacía.

    Parámetros
    ----------
    path : str o pathlib.Path
        Ruta al archivo HTML.
    nombre_archivo : str
        Nombre del archivo, utilizado para mensajes de error.

    Retorna
    -------
    list of pandas.DataFrame
        Lista de DataFrames correspondientes a las tablas encontradas.
        Si ocurre un error, retorna una lista vacía.
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

    La función busca expresiones del tipo "45%" o "45.3%" dentro del
    texto de las etiquetas <h3>. Si se encuentra un valor válido,
    se retorna como número flotante.

    Parámetros
    ----------
    soup : bs4.BeautifulSoup
        Objeto BeautifulSoup con el HTML parseado.
    nombre_archivo : str
        Nombre del archivo, utilizado para mensajes de error.

    Retorna
    -------
    float or None
        Valor de humedad relativa encontrado.
        Retorna None si no se encuentra o si ocurre un error.
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

    Esta función permite que las fechas de entrada se entreguen en
    distintos formatos comunes y las normaliza a datetime.datetime.

    Acepta:
    - datetime.datetime
    - datetime.date
    - string en formato "YYYY-MM-DD"

    Parámetros
    ----------
    fecha : str, datetime.date o datetime.datetime
        Fecha a validar y convertir.
    nombre_parametro : str
        Nombre del parámetro, usado para mensajes de error claros.

    Retorna
    -------
    datetime.datetime
        Fecha convertida o validada.

    Excepciones
    -----------
    ValueError
        Si la fecha es string pero no cumple el formato "YYYY-MM-DD".
    TypeError
        Si la fecha no es de un tipo soportado.
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
        # Permite manejar objetos datetime.date
        return datetime.combine(fecha, datetime.min.time())

    raise TypeError(
        f"{nombre_parametro} debe ser datetime o string 'YYYY-MM-DD'"
    )


# -----------------------------------------------------------------------------
# Procesamiento principal de tablas
# -----------------------------------------------------------------------------
def _procesar_tablas(tablas, soup, nombre_archivo):
    """
    Procesa las tablas extraídas de un archivo HTML y genera DataFrames
    consolidados con la información de correcciones.

    El procesamiento se realiza en pares de tablas:
    - Una tabla informativa con "Timestamp" y "Delay line number"
    - Una tabla con los valores de corrección por "Rail number"

    A cada bloque se le añade información adicional extraída del HTML,
    como la humedad relativa del túnel.

    Parámetros
    ----------
    tablas : list of pandas.DataFrame
        Lista de tablas extraídas del archivo HTML.
    soup : bs4.BeautifulSoup
        Objeto BeautifulSoup con el HTML parseado.
    nombre_archivo : str
        Nombre del archivo, utilizado para mensajes de error.

    Retorna
    -------
    list of pandas.DataFrame
        Lista de DataFrames, cada uno correspondiente a un bloque
        de correcciones procesado correctamente.
    """
    resultados = []

    # Se recorren las tablas en pares:
    # (tabla informativa, tabla de correcciones)
    for i in range(0, len(tablas) - 1, 2):
        try:
            # Número de correcciones (filas) a repetir
            n_repeat = tablas[i + 1].shape[0]
            if n_repeat == 0:
                continue

            # Transponer la tabla informativa para obtener columnas
            tabla_transpuesta = tablas[i].T

            columnas_req = {"Timestamp", "Delay line number"}
            if not columnas_req.issubset(tabla_transpuesta.columns):
                continue

            # Selección de columnas relevantes
            test_pd = tabla_transpuesta[list(columnas_req)].copy()
            test_pd["Timestamp"] = pd.to_datetime(
                test_pd["Timestamp"], errors="coerce"
            )

            if test_pd.empty:
                continue

            # Repetir filas para alinear con la tabla de correcciones
            test_pd_repeated = pd.concat(
                [test_pd] * n_repeat
            ).reset_index(drop=True)

            # Procesar tabla de correcciones
            tabla_correcciones = (
                tablas[i + 1]
                .droplevel(0, axis=1)
                .rename_axis("Rail number")
                .reset_index(drop=False)
            )

            # Extraer humedad desde el HTML
            humidity = _extraer_humedad(soup, nombre_archivo)

            humedad_df = pd.DataFrame({
                "Tunnel Relative Humidity": [
                    f"{humidity}%" if humidity is not None else None
                ] * n_repeat
            })

            # Consolidar toda la información en un único DataFrame
            resultados.append(
                pd.concat(
                    [test_pd_repeated, humedad_df, tabla_correcciones],
                    axis=1
                )
            )

        except Exception as e:
            print(f"Error procesando tablas en {nombre_archivo}: {e}")

    return resultados
