"""
app_auditoria.py
----------------
Interfaz (la "vitrina") de la auditoría de comentarios de Instagram de Café Martínez.
El cálculo está en auditoria_model.py (el "motor"); acá solo se muestra.

Para correrla en tu compu:   streamlit run app_auditoria.py
"""

import matplotlib.pyplot as plt
import streamlit as st

import auditoria_model as modelo

st.set_page_config(page_title="Auditoría de Instagram", page_icon="☕", layout="wide")

st.title("☕ Auditoría de comentarios en Instagram")
st.caption("Prototipo del Trabajo Integrador · el notebook es el motor y esta app es la vitrina")

# ---------------------------------------------------------------------------
# Panel lateral: datos y umbrales
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Negocio")
    negocio = st.text_input("Nombre del negocio", "Café Martínez")

    st.header("Datos")
    archivo = st.file_uploader("CSV de comentarios", type="csv",
                               help="Subí el comentarios_analizados.csv que exporta el notebook, "
                                    "o un CSV con las columnas publicacion, usuario y comentario.")
    st.caption("Sin archivo, la app usa los comentarios de ejemplo.")

    st.header("Umbrales de clasificación")
    umbral_positivo = st.slider("Positivo: de acá para arriba", 0.50, 0.95, 0.60, 0.05)
    umbral_negativo = st.slider("Negativo: de acá para abajo", 0.05, 0.50, 0.40, 0.05)

# ---------------------------------------------------------------------------
# Datos: cargar, clasificar y calcular
# ---------------------------------------------------------------------------
try:
    df, origen_datos, metodo = modelo.cargar_datos(archivo)
except Exception as error:
    st.error(f"No se pudo cargar el archivo: {error}")
    st.stop()

df = modelo.agregar_sentimiento(df, umbral_positivo, umbral_negativo)
general = modelo.resumen_general(df)
por_pub = modelo.resumen_por_publicacion(df)
peores = modelo.peores_comentarios(df, 5)
cantidad_publicaciones = df["publicacion"].nunique()

st.info(f"**Origen de los datos:** {origen_datos}  \n**Método de análisis:** {metodo}")

# ---------------------------------------------------------------------------
# Indicadores
# ---------------------------------------------------------------------------
st.subheader("Puntaje general de la marca")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Puntaje general (0 a 1)", f"{general['puntaje']:.2f}")
col2.metric("Comentarios analizados", general["total"])
col3.metric("Positivos", f"{general['porc_positivos']:.1f}%")
col4.metric("Negativos", f"{general['porc_negativos']:.1f}%")

if general["puntaje"] >= umbral_positivo:
    st.success("La percepción de la marca es buena.")
elif general["puntaje"] <= umbral_negativo:
    st.error("La percepción de la marca es mala y requiere atención urgente.")
else:
    st.warning("La percepción de la marca es intermedia.")

peor = por_pub.index[0]
if por_pub.loc[peor, "porc_negativos"] > 30:
    st.warning(f"Alerta: la publicación N° {peor} tiene {por_pub.loc[peor, 'porc_negativos']}% "
               f"de comentarios negativos.")

# ---------------------------------------------------------------------------
# Gráficos
# ---------------------------------------------------------------------------
st.subheader("Gráficos")
tab1, tab2, tab3 = st.tabs(["Por publicación", "Por sentimiento", "Distribución de puntajes"])

with tab1:
    fig1 = plt.figure(figsize=(8, 5))
    plt.barh(por_pub.index.astype(str), por_pub["puntaje"], color="steelblue")
    plt.axvline(general["puntaje"], color="gray", linestyle="--", label="Puntaje general")
    plt.title("Puntaje por publicación (0 a 1)")
    plt.xlabel("Puntaje promedio")
    plt.ylabel("Publicación")
    plt.legend()
    plt.tight_layout()
    st.pyplot(fig1)

with tab2:
    conteo = df["sentimiento"].value_counts()
    fig2 = plt.figure(figsize=(6, 4))
    plt.bar(conteo.index, conteo.values, color="steelblue")
    plt.title("Comentarios por sentimiento")
    plt.ylabel("Cantidad de comentarios")
    plt.tight_layout()
    st.pyplot(fig2)

with tab3:
    fig3 = plt.figure(figsize=(7, 4))
    plt.hist(df["puntaje"], bins=20, color="steelblue")
    plt.axvline(umbral_negativo, color="red", linestyle="--", label="Umbral negativo")
    plt.axvline(umbral_positivo, color="green", linestyle="--", label="Umbral positivo")
    plt.title("Distribución de los puntajes")
    plt.xlabel("Puntaje (0 a 1)")
    plt.ylabel("Cantidad de comentarios")
    plt.legend()
    plt.tight_layout()
    st.pyplot(fig3)

# ---------------------------------------------------------------------------
# Tablas
# ---------------------------------------------------------------------------
st.subheader("Detalle por publicación")
st.dataframe(por_pub)

st.subheader("Los 5 comentarios más negativos")
st.caption("Son los que el dueño debería leer y responder primero.")
st.dataframe(peores)

st.subheader("Explorar una publicación")
numero = st.selectbox("Elegí la publicación", sorted(df["publicacion"].unique()))
comentarios_pub = df[df["publicacion"] == numero]
st.write(f"La publicación {numero} tiene {len(comentarios_pub)} comentarios analizados.")
st.dataframe(comentarios_pub[["usuario", "comentario", "puntaje", "sentimiento"]])

# ---------------------------------------------------------------------------
# Reporte por email (vista previa y descarga)
# ---------------------------------------------------------------------------
st.subheader("Reporte para el dueño")

resumen = modelo.armar_resumen_texto(negocio, cantidad_publicaciones, general, por_pub,
                                     umbral_positivo, umbral_negativo)
cuerpo_html = modelo.armar_email_html(negocio, cantidad_publicaciones, general, por_pub, peores,
                                      resumen, metodo, origen_datos)

st.write(resumen)

with st.expander("Ver vista previa del email"):
    st.html(cuerpo_html)

destinatario = st.text_input("Enviar el reporte a", "dueno@cafemartinez.com")
if st.button("Enviar reporte por email"):
    st.success(f"Simulación: el reporte se enviaría a {destinatario}. "
               f"El envío real está en la sección 6 del notebook (smtplib con Gmail).")

col_a, col_b = st.columns(2)
col_a.download_button("Descargar el reporte (HTML)", cuerpo_html, file_name="reporte_instagram.html")
col_b.download_button("Descargar el detalle por publicación (CSV)", por_pub.to_csv(),
                      file_name="resumen_por_publicacion.csv")
