"""
auditoria_model.py
------------------
Lógica de la auditoría de comentarios de Instagram de Café Martínez.

Es el "motor" del Trabajo Integrador: son las mismas funciones del notebook,
ordenadas en un archivo para que las use la app de Streamlit (app_auditoria.py).
Solo usa pandas y numpy, nada que no hayamos visto en clase.
"""

import os
import html
import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Configuración (escala de puntaje de 0 a 1)
# ---------------------------------------------------------------------------
UMBRAL_POSITIVO = 0.60   # de acá para arriba, el comentario es positivo
UMBRAL_NEGATIVO = 0.40   # de acá para abajo, es negativo

# Diccionario del plan B (se usa solo si el CSV no trae el puntaje de la red neuronal)
palabras_positivas = ["excelente", "mejor", "rico", "ricas", "encanta", "fascina", "lindo",
                      "perfecto", "buenísimo", "recomiendo", "gracias", "buena", "cómodo", "vuelvo"]
palabras_negativas = ["esperé", "nunca", "carísimo", "frío", "pésima", "mal", "duras",
                      "sucias", "decepción", "tardaron", "ruido", "no vuelvo", "subieron"]


def puntaje_con_palabras(texto):
    """Plan B: cuenta palabras positivas y negativas y arma un puntaje de 0 a 1."""
    texto = texto.lower()
    positivas = 0
    negativas = 0

    for palabra in palabras_positivas:
        if palabra in texto:
            positivas = positivas + 1

    for palabra in palabras_negativas:
        if palabra in texto:
            negativas = negativas + 1

    if positivas == 0 and negativas == 0:
        return 0.5                                  # sin pistas: neutro
    return positivas / (positivas + negativas)


# ---------------------------------------------------------------------------
# 1. Obtención de los comentarios
# ---------------------------------------------------------------------------
def generar_comentarios_simulados(cantidad_publicaciones=10, semilla=42):
    """Comentarios simulados (idénticos a los del notebook). La publicación 4 y la 9 tienen más quejas."""
    np.random.seed(semilla)

    comentarios_positivos = [
        "Excelente atención, siempre vuelvo",
        "El mejor café de la zona",
        "Muy ricas las medialunas, recién hechas",
        "Me encanta este lugar, muy cómodo",
        "Atención de primera, gracias",
        "Buenísimo todo, lo recomiendo",
        "Qué lindo local, volvemos seguro",
        "El capuccino estaba perfecto",
        "Muy buena onda los chicos del mostrador",
        "Me fascina el aroma del café de ustedes",
    ]
    comentarios_negativos = [
        "Esperé 40 minutos y nunca me atendieron",
        "Carísimo para lo que es",
        "El café estaba frío, muy mal",
        "Pésima atención, no vuelvo más",
        "Subieron todo de precio otra vez",
        "Las medialunas estaban duras",
        "Mucho ruido y las mesas sucias",
        "Pedí sin azúcar y me lo trajeron con azúcar",
        "Una decepción, esperaba más",
        "Tardaron muchísimo en traer el pedido",
    ]
    comentarios_neutros = [
        "A qué hora abren los domingos",
        "Hacen delivery",
        "Tienen opciones sin TACC",
        "Dónde queda esta sucursal",
        "Cuánto sale el café con leche",
    ]
    comentarios_basura = ["", "   ", "🔥🔥🔥", "❤️", "👏👏"]

    publicaciones = []
    for n in range(1, cantidad_publicaciones + 1):
        if n == 4 or n == 9:
            porcentaje_negativo = 0.55      # publicaciones problemáticas
        else:
            porcentaje_negativo = 0.15
        publicaciones.append({
            "publicacion": n,
            "cantidad": np.random.randint(25, 60),
            "porc_negativo": porcentaje_negativo,
        })

    filas = []
    id_comentario = 1
    for pub in publicaciones:
        for i in range(pub["cantidad"]):
            sorteo = np.random.randint(0, 100) / 100

            if sorteo < pub["porc_negativo"]:
                texto = comentarios_negativos[np.random.randint(0, len(comentarios_negativos))]
            elif sorteo < pub["porc_negativo"] + 0.12:
                texto = comentarios_neutros[np.random.randint(0, len(comentarios_neutros))]
            elif sorteo > 0.93:
                texto = comentarios_basura[np.random.randint(0, len(comentarios_basura))]
            else:
                texto = comentarios_positivos[np.random.randint(0, len(comentarios_positivos))]

            filas.append({
                "id_comentario": id_comentario,
                "publicacion": pub["publicacion"],
                "usuario": f"usuario_{np.random.randint(100, 999)}",
                "comentario": texto,
            })
            id_comentario = id_comentario + 1

    comentarios = pd.DataFrame(filas)

    # Duplicados, como pasa cuando alguien comenta dos veces por error
    duplicados = comentarios.head(15)
    comentarios = pd.concat([comentarios, duplicados], ignore_index=True)
    return comentarios


def cargar_datos(archivo=None):
    """
    Devuelve (df_limpio, origen_datos, metodo).

    Orden de prioridad:
      1. el CSV que sube el usuario en la app,
      2. el archivo comentarios_analizados.csv junto a este módulo (el que exporta el notebook),
      3. los comentarios simulados.
    El CSV tiene que traer, como mínimo, las columnas `publicacion` y `comentario`.
    Si además trae `puntaje` (el de la red neuronal), se usa ese puntaje.
    """
    ruta_local = os.path.join(os.path.dirname(os.path.abspath(__file__)), "comentarios_analizados.csv")

    if archivo is not None:
        comentarios = pd.read_csv(archivo)
        origen_datos = "archivo subido (datos reales)"
    elif os.path.exists(ruta_local):
        comentarios = pd.read_csv(ruta_local)
        origen_datos = "comentarios_analizados.csv (exportado desde el notebook)"
    else:
        comentarios = generar_comentarios_simulados()
        origen_datos = "comentarios simulados de ejemplo"

    # Validamos las columnas mínimas
    faltan = []
    for columna in ["publicacion", "comentario"]:
        if columna not in comentarios.columns:
            faltan.append(columna)
    if len(faltan) > 0:
        raise ValueError(f"Al CSV le faltan estas columnas: {', '.join(faltan)}")

    if "usuario" not in comentarios.columns:
        comentarios["usuario"] = "sin_dato"

    # --- Limpieza (igual que en el notebook) ---
    df = comentarios.drop_duplicates().copy()                 # 1) sin duplicados
    df = df.drop(columns=["largo"], errors="ignore")
    df["comentario"] = df["comentario"].astype(str).str.strip()   # 2) sin espacios en los extremos
    df = df[df["comentario"].str.len() >= 10]                 # 3) solo con texto suficiente
    df = df.reset_index(drop=True)

    # --- Puntaje: el del CSV si viene, o el plan B ---
    if "puntaje" in df.columns and df["puntaje"].notna().all():
        metodo = "puntaje que ya traía el archivo (calculado en el notebook)"
    else:
        puntajes = []
        for texto in df["comentario"]:
            puntajes.append(puntaje_con_palabras(texto))
        df["puntaje"] = puntajes
        metodo = "diccionario de palabras (plan B)"

    df["puntaje"] = df["puntaje"].astype(float).round(3)
    return df, origen_datos, metodo


# ---------------------------------------------------------------------------
# 2. Clasificación y resultados
# ---------------------------------------------------------------------------
def clasificar(puntaje, umbral_positivo=UMBRAL_POSITIVO, umbral_negativo=UMBRAL_NEGATIVO):
    if puntaje >= umbral_positivo:
        return "Positivo"
    elif puntaje <= umbral_negativo:
        return "Negativo"
    else:
        return "Neutro"


def agregar_sentimiento(df, umbral_positivo=UMBRAL_POSITIVO, umbral_negativo=UMBRAL_NEGATIVO):
    """Devuelve una copia del DataFrame con la columna `sentimiento`."""
    df = df.copy()
    sentimientos = []
    for p in df["puntaje"]:
        sentimientos.append(clasificar(p, umbral_positivo, umbral_negativo))
    df["sentimiento"] = sentimientos
    return df


def resumen_general(df):
    """Indicadores de toda la marca, en un diccionario."""
    total = len(df)
    positivos = len(df[df["sentimiento"] == "Positivo"])
    negativos = len(df[df["sentimiento"] == "Negativo"])
    neutros = len(df[df["sentimiento"] == "Neutro"])
    return {
        "total": total,
        "puntaje": df["puntaje"].mean(),
        "positivos": positivos,
        "neutros": neutros,
        "negativos": negativos,
        "porc_positivos": positivos / total * 100,
        "porc_neutros": neutros / total * 100,
        "porc_negativos": negativos / total * 100,
    }


def resumen_por_publicacion(df):
    """Una fila por publicación, ordenada de peor a mejor puntaje."""
    por_pub = pd.DataFrame({
        "comentarios": df.groupby("publicacion")["puntaje"].count(),
        "puntaje": df.groupby("publicacion")["puntaje"].mean().round(3),
    })

    solo_negativos = df[df["sentimiento"] == "Negativo"]
    por_pub["negativos"] = solo_negativos.groupby("publicacion")["puntaje"].count()
    por_pub["negativos"] = por_pub["negativos"].fillna(0).astype(int)
    por_pub["porc_negativos"] = (por_pub["negativos"] / por_pub["comentarios"] * 100).round(1)

    por_pub = por_pub.sort_values("puntaje")
    return por_pub


def peores_comentarios(df, cantidad=5):
    """Los comentarios con menor puntaje: los que el dueño debería leer primero."""
    return df.sort_values("puntaje")[["publicacion", "usuario", "comentario", "puntaje"]].head(cantidad)


# ---------------------------------------------------------------------------
# 3. Reporte (texto y email en HTML)
# ---------------------------------------------------------------------------
def armar_resumen_texto(negocio, cantidad_publicaciones, general, por_pub, umbral_positivo, umbral_negativo):
    puntaje_general = general["puntaje"]
    peor_publicacion = por_pub.index[0]
    mejor_publicacion = por_pub.index[-1]

    if puntaje_general >= umbral_positivo:
        diagnostico = "La percepción de la marca es buena"
    elif puntaje_general <= umbral_negativo:
        diagnostico = "La percepción de la marca es mala y requiere atención urgente"
    else:
        diagnostico = "La percepción de la marca es intermedia"

    resumen = (f"Sobre las últimas {cantidad_publicaciones} publicaciones de {negocio} se analizaron "
               f"{general['total']} comentarios con un puntaje general de {puntaje_general:.2f} sobre 1. "
               f"{diagnostico}: el {general['porc_positivos']:.1f}% de los comentarios son positivos "
               f"y el {general['porc_negativos']:.1f}% son negativos. "
               f"La publicación con mejor recepción fue la N° {mejor_publicacion} "
               f"({por_pub.loc[mejor_publicacion, 'puntaje']:.2f}) y la peor fue la N° {peor_publicacion} "
               f"({por_pub.loc[peor_publicacion, 'puntaje']:.2f}, con "
               f"{por_pub.loc[peor_publicacion, 'porc_negativos']}% de comentarios negativos).")

    if por_pub.loc[peor_publicacion, "porc_negativos"] > 30:
        resumen = resumen + (f" Recomendación: revisar qué se publicó y qué pasó en el local "
                             f"alrededor de la publicación N° {peor_publicacion}, y responder los "
                             f"comentarios negativos listados.")
    else:
        resumen = resumen + " Recomendación: mantener la estrategia actual y seguir monitoreando."
    return resumen


def armar_email_html(negocio, cantidad_publicaciones, general, por_pub, peores, resumen, metodo, origen_datos):
    filas_pub = ""
    for pub in por_pub.index:
        puntaje_pub = por_pub.loc[pub, "puntaje"]
        cant = por_pub.loc[pub, "comentarios"]
        porc = por_pub.loc[pub, "porc_negativos"]
        filas_pub = filas_pub + f"<tr><td>{pub}</td><td>{cant}</td><td>{puntaje_pub}</td><td>{porc}%</td></tr>"

    filas_peores = ""
    for i in peores.head(3).index:
        # html.escape evita que un comentario con símbolos como < o > rompa el HTML del email
        texto_comentario = html.escape(str(peores.loc[i, "comentario"]))
        filas_peores = filas_peores + (f"<li>Publicación {peores.loc[i, 'publicacion']}: "
                                       f"\"{texto_comentario}\" (puntaje {peores.loc[i, 'puntaje']})</li>")

    cuerpo_html = f"""
<h2>{negocio} — Auditoría de comentarios en Instagram</h2>
<p><b>Últimas {cantidad_publicaciones} publicaciones · {general['total']} comentarios analizados</b></p>
<p>{resumen}</p>
<h3>Indicadores</h3>
<ul>
  <li>Puntaje general: <b>{general['puntaje']:.2f}</b> (escala 0 a 1)</li>
  <li>Comentarios positivos: <b>{general['positivos']}</b> ({general['porc_positivos']:.1f}%)</li>
  <li>Comentarios negativos: <b>{general['negativos']}</b> ({general['porc_negativos']:.1f}%)</li>
  <li>Método de análisis: {metodo}</li>
  <li>Origen de los datos: {origen_datos}</li>
</ul>
<h3>Detalle por publicación</h3>
<table border="1" cellpadding="6" style="border-collapse:collapse">
  <tr><th>Publicación</th><th>Comentarios</th><th>Puntaje</th><th>% negativos</th></tr>
  {filas_pub}
</table>
<h3>Comentarios que requieren respuesta</h3>
<ul>{filas_peores}</ul>
<p><i>Reporte generado automáticamente.</i></p>
"""
    return cuerpo_html
