import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
import numpy as np
import tempfile
from fpdf import FPDF
from analisis import analizar_reviews
from scraper import scrape_trustpilot, obtener_nombre_limpio

#antes de analizar el negocio comprobamos que no esté ya en la db para ahorrarnos tiempo 
def buscar_en_bd(nombre_negocio):
    try:
        conn = sqlite3.connect('mi_proyecto.db')
        
        query = f"SELECT * FROM analisis_negocios WHERE LOWER(business_name) = '{nombre_negocio.lower()}'"
        
        df_db = pd.read_sql(query, conn)
        conn.close()
        
        if df_db.empty:
            print(f"no hay datos aún para '{nombre_negocio}', recopilando...")
            return None
        else:
            print(f"encontradas {len(df_db)} filas para '{nombre_negocio}' ")
            return df_db
            
    except Exception as e:
        print(f"Error leyendo la Base de Datos: {e}")
        return None

def generar_pdf_informe(nombre_empresa, resultados, score):
    pdf = FPDF()
    pdf.add_page()
    
    def texto_seguro(texto):
        return str(texto).encode('latin-1', 'ignore').decode('latin-1')

    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, texto_seguro(f"Informe de Reputacion Online: {nombre_empresa.upper()}"), ln=True, align='C')
    pdf.ln(5)

    #Generales
    pdf.set_font("Arial", 'B', 12)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, texto_seguro("1. Metricas Principales"), ln=True)
    
    pdf.set_font("Arial", '', 11)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 8, texto_seguro(f"  - Total de resenas analizadas: {len(resultados['df'])}"), ln=True)
    pdf.cell(0, 8, texto_seguro(f"  - Indice de Satisfaccion General: {score:.1f}%"), ln=True)
    pdf.ln(5)

    #Resumen
    pdf.set_font("Arial", 'B', 12)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, texto_seguro("2. Resumen Ejecutivo (Generado por IA)"), ln=True)
    
    pdf.set_font("Arial", '', 11)
    pdf.set_text_color(0, 0, 0)
    pdf.multi_cell(0, 6, texto_seguro(resultados["resumen_ia"]))
    pdf.ln(5)

    #Puntos Clave
    pdf.set_font("Arial", 'B', 12)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, texto_seguro("3. Puntos Clave de la Experiencia"), ln=True)
    
    pdf.set_font("Arial", '', 11)
    pdf.set_text_color(0, 0, 0)
    t_pos = ", ".join(list(resultados['temas_pos'].index[:3])) if not resultados['temas_pos'].empty else "No hay datos claros"
    t_neg = ", ".join(list(resultados['temas_neg'].index[:3])) if not resultados['temas_neg'].empty else "No hay quejas claras"
    
    pdf.multi_cell(0, 6, texto_seguro(f"  - Lo mas elogiado: {t_pos}"))
    pdf.multi_cell(0, 6, texto_seguro(f"  - Mayores quejas: {t_neg}"))
    pdf.ln(5)
    
    #Recomendaciones
    pdf.set_font("Arial", 'B', 12)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, texto_seguro("4. Recomendaciones Estrategicas"), ln=True)
    
    pdf.set_font("Arial", '', 11)
    pdf.set_text_color(0, 0, 0)
    tema_critico = list(resultados['temas_neg'].index)[0] if not resultados['temas_neg'].empty else "las areas operativas"
    tema_exito = list(resultados['temas_pos'].index)[0] if not resultados['temas_pos'].empty else "la atencion al cliente"
    
    rec_texto = (f"Accion Prioritaria: Las metricas indican que la urgencia principal recae sobre '{tema_critico}'. "
                 f"Abordar esta area tendria el mayor impacto inmediato en la mejora de la valoracion.\n\n"
                 f"Mantenimiento: Los usuarios valoran muy positivamente '{tema_exito}'. "
                 f"Este aspecto debe mantenerse como estandarte de la marca para fidelizar a los clientes.")
    
    pdf.multi_cell(0, 6, texto_seguro(rec_texto))

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        pdf.output(tmp.name)
        with open(tmp.name, "rb") as f:
            pdf_bytes = f.read()
            
    return pdf_bytes
st.set_page_config(page_title="Análisis de reseñas", layout="wide")

st.title("Análisis de reseñas de clientes con IA")
st.markdown("Introduce un negocio o sube un dataset para analizar")

st.subheader("Entrada de datos")

opcion = st.radio(
    "Selecciona una opción:",
    ["Subir CSV", "Introducir nombre/URL"],
    horizontal=True 
)

df = None
negocio = None
archivo = None

if opcion == "Subir CSV":
    archivo = st.file_uploader("Sube tu archivo CSV", type=["csv"])
elif opcion == "Introducir nombre/URL":
    negocio = st.text_input("Nombre del negocio o URL", placeholder="Ej: nombre_web.es")

#Botón analizar
st.write("")
analizar = st.button("Analizar")


def display_landing_content():
    st.divider()
    st.subheader("Algunos ejemplos de lo que la IA es capaz de analizar:")

    st.write("") 

    col1_img, col1_txt = st.columns([2, 3]) 
    with col1_img:
        st.info("Ejemplo 1: Distribución de Sentimiento")
        st.image("./img/distribucion-sentimiento.png")
        st.markdown(
            """
            <style>
            [data-testid="stImage"] img {
                box-shadow: 0px 0px 5px 2px rgba(0, 0, 0, 0.1); 
            }
            </style>
            """, 
            unsafe_allow_html=True
        )
    with col1_txt:
        st.write("Análisis detallado con gráficos descriptivos, tablas de datos y texto informativo sobre lo que se ve en la imagen. Por ejemplo, porcentajes y total de reseñas analizadas. En este caso, tenemos un pie chart donde aparece el porcentaje de reseñas positivas, negativas y neutras que hay en las reseñas.")

    st.write("") 

    col2_txt, col2_img = st.columns([3, 2])
    with col2_txt:
        st.write("Análisis detallado de palabras clave más comunes. Te mostramos las palabras que definen la experiencia del cliente y las quejas más frecuentes para guiar tus mejoras.")
    with col2_img:
        st.info("Ejemplo 2: Nube de Palabras Clave")
        st.image("./img/palabras-clave.png")


    st.write("") 

    col3_img, col3_txt = st.columns([2, 3])
    with col3_img:
        st.info("Ejemplo 3: Agrupación Temática (BERTopic)")
        st.image("./img/temas-clave.png")

    with col3_txt:
        st.write("Análisis avanzado para identificar temas recurrentes y agrupar las quejas. Te ayuda a entender la causa raíz de los problemas más frecuentes de manera automatizada.")


if "analisis_activo" not in st.session_state:
    st.session_state.analisis_activo = False

if analizar:
    st.session_state.analisis_activo = True


if st.session_state.analisis_activo:
    
    nombre_bonito = obtener_nombre_limpio(negocio if negocio else "la empresa")
    
    df_db = buscar_en_bd(nombre_bonito) 
    
    es_nuevo = False
    
    if df_db is not None and not df_db.empty:
        st.info(f"Mostrando {len(df_db)} reseñas de '{nombre_bonito}' recuperadas de la Base de Datos.")
        print("########################################################################")
        print("####################### DATABASE FUNCIONANDO ###########################")
        print("########################################################################")
        df = df_db
        es_nuevo = False 
        
    else:
        with st.spinner('Fase 1/2: Obteniendo reseñas...'):
            if opcion == "Subir CSV" and archivo:
                df = pd.read_csv(archivo)
                es_nuevo = True 
            elif opcion == "Introducir nombre/URL" and negocio:
                df = scrape_trustpilot(negocio)
                es_nuevo = True 
            else:
                st.error("Introduce los datos necesarios.")
                st.stop()
        
    if df is not None and not df.empty:
        with st.spinner('Fase 2/2: Analizando con IA (BETO & BERTopic)...'):
            resultados = analizar_reviews(df) 

            if es_nuevo and resultados:
                try:
                    df_para_guardar = resultados["df"].copy()
                    df_para_guardar["business_name"] = nombre_bonito 
                    
                    conn = sqlite3.connect('mi_proyecto.db')
                    df_para_guardar.to_sql('analisis_negocios', conn, if_exists='append', index=False)
                    conn.close()
                    
                    st.success(f"{len(df_para_guardar)} reseñas de '{nombre_bonito}' analizadas y almacenadas en la base de datos.")
                    print(f" Guardado {nombre_bonito} en SQLite.")
                except Exception as e:
                    print(f" error al guardar en la base de datos: {e}")

        if resultados:
            score_global = (resultados["df"]["sent_val"].mean() + 1) / 2 * 100

            st.success(f"Análisis completado sobre {len(resultados['df'])} reseñas únicas.")

            col_titulo, col_boton = st.columns([3, 1]) 
            
            with col_titulo:
                st.markdown(f"## Resultados para {nombre_bonito}")
                
            with col_boton:
                pdf_bytes = generar_pdf_informe(nombre_bonito, resultados, score_global)
                
                st.download_button(
                    label="Descargar Informe PDF",
                    data=pdf_bytes,
                    file_name=f"Reporte_Reputacion_{nombre_bonito}.pdf",
                    mime="application/pdf",
                    use_container_width=True 
                )

            #TABS
            tab1, tab2, tab3, tab4, tab5 = st.tabs(["Sentimiento", "Palabras Clave", "Temas Destacados", "Métricas Avanzadas", "Recomendaciones Personalizadas"])
            
            with tab1:

                pos = resultados["sentimiento_pct"].get("positivo", 0)
                neg = resultados["sentimiento_pct"].get("negativo", 0)
                neu = resultados["sentimiento_pct"].get("neutro", 0)
                nombre_empresa = nombre_bonito

                if abs(pos - neg) <= 10:
                    sent_status = "neutro"
                elif neg > pos:
                    sent_status = "negativo"
                else:
                    sent_status = "positivo"

                tendencia_data = resultados["tendencia"]
                if len(tendencia_data) > 1:
                    inicio = tendencia_data[0]
                    fin = tendencia_data[-1]
                    diff = fin - inicio

                    if diff > 0.1:
                        trend_status = "mejor"
                    elif diff < -0.1: 
                        trend_status = "peor"
                    else: 
                        trend_status = "estable"
                else:
                    trend_status = "estable"

                textos = {
                    "negativo": {
                        "mejor": f"Vaya... parece que los clientes no están muy contentos con {nombre_empresa}. Es el momento de plantearse unos cambios. La evolución de las opiniones positivas a lo largo de estos últimos meses ha ido a mejor pero sigue sin ser suficiente por lo que habrá que seguir esforzándose en mejorar la calidad de las reseñas.",
                        "peor": f"Vaya... parece que los clientes no están muy contentos con {nombre_empresa}. Es el momento de plantearse unos cambios. Además, la evolución de las opiniones positivas a lo largo de estos últimos meses ha ido a peor por lo que habrá que concentrarse en mejorar la calidad de las reseñas.",
                        "estable": f"Vaya... parece que los clientes no están muy contentos con {nombre_empresa}. Es el momento de plantearse unos cambios. La evolución de la opinión es neutra; es decir, que prácticamente no han habido cambios en la opinión de los usuarios durante estos últimos meses. Habrá que seguir esforzándose en mejorar la calidad de las reseñas."
                    },
                    "positivo": {
                        "mejor": f"¡Genial! parece que los clientes están muy contentos con {nombre_empresa}. Ahora hay que encargarse de mantener esto. La evolución de las opiniones positivas a lo largo de estos últimos meses ha ido a mejor por lo que, ¡enhorabuena, que así siga!",
                        "peor": f"¡Genial! parece que los clientes están muy contentos con {nombre_empresa}. Ahora hay que encargarse de mantener esto. La evolución de opiniones positivas a lo largo de estos últimos meses ha ido a peor por lo que habrá que concentrarse en mejorar la calidad de las reseñas para no estropear la buena reputación que existe actualmente.",
                        "estable": f"¡Genial! parece que los clientes están muy contentos con {nombre_empresa}. Ahora hay que encargarse de mantener esto. La evolución de la opinión es neutra; es decir, que prácticamente no han habido cambios en la opinión de los usuarios durante estos últimos meses. Habrá que esforzarse en mantener la calidad de las reseñas y procurar que vaya al alza."
                    },
                    "neutro": {
                        "mejor": f"Bueno... parece que los clientes están contentos y con quejas a partes iguales en cuanto a la opinión de {nombre_empresa}. Ahora hay que encargarse de mejorar esto un poco. La evolución de las opiniones positivas a lo largo de estos últimos meses ha ido a mejor por lo que, hay que profundizar en ello y procurar que siga aumentando.",
                        "peor": f"Bueno... parece que los clientes están contentos y con quejas a partes iguales en cuanto a la opinión de {nombre_empresa}. Ahora hay que encargarse de mejorar esto un poco. La evolución de las opiniones positivas a lo largo de estos últimos meses ha ido a peor por lo que habrá que concentrarse en mejorar la calidad de las reseñas para no estropear la actual reputación.",
                        "estable": f"Bueno... parece que los clientes están contentos y con quejas a partes iguales en cuanto a la opinión de {nombre_empresa}. Ahora hay que encargarse de mejorar esto un poco. La evolución de la opinión es neutra; es decir, que prácticamente no han habido cambios en la opinión de los usuarios durante estos últimos meses. Habrá que esforzarse en aumentar la calidad de las reseñas para conseguir que la gran mayoría sean positivas."
                    }
                }

                resumen_final = textos[sent_status][trend_status]

                col_a, col_b = st.columns(2)
                with col_a:
                    st.subheader("Proporción Crítica")
                    fig_pie = px.pie(
                        values=resultados["sentimiento_pct"].values,
                        names=resultados["sentimiento_pct"].index,
                        color=resultados["sentimiento_pct"].index,
                        color_discrete_map={'positivo':'#2ecc71', 'neutro':'#f1c40f', 'negativo':'#e74c3c'},
                        hole=0.4
                    )
                    st.plotly_chart(fig_pie, use_container_width=True)

                with col_b:
                    st.subheader("Evolución de la Opinión")
                    
                    tendencia_y = resultados["tendencia"]
                    tendencia_x = list(range(1, len(tendencia_y) + 1))
                    
                    fig_line = px.line(
                        x=tendencia_x, 
                        y=tendencia_y,
                        labels={"x": "Línea temporal (Antiguas ➔ Recientes)", "y": ""}
                    )
                    
                    fig_line.update_layout(
                        yaxis=dict(
                            tickmode='array',
                            tickvals=[-1, 0, 1], 
                            ticktext=['🔴 Negativo', '🟡 Neutro', '🟢 Positivo'], 
                            range=[-1.2, 1.2], 
                            zeroline=True, 
                            zerolinecolor='lightgrey'
                        ),
                        xaxis=dict(
                            showticklabels=False 
                        ),
                        margin=dict(l=0, r=0, t=10, b=0),
                        hovermode="x unified" 
                    )
                    
                    fig_line.update_traces(line_color="#3498db", line_shape="spline")
                    
                    st.plotly_chart(fig_line, use_container_width=True)
                    st.caption("Evolución cronológica. Muestra cómo ha cambiado el humor de los clientes desde las reseñas más antiguas hasta hoy.")

                st.write("")
                st.info(resumen_final) 

            with tab2:
                st.markdown("###¿De qué hablan exactamente los clientes?")

                if not resultados["top_palabras_gen"].empty:
                    pos_pct = resultados["sentimiento_pct"].get("positivo", 0)
                    neg_pct = resultados["sentimiento_pct"].get("negativo", 0)
                    
                    max_total_burbujas = 30
                    total_voto = pos_pct + neg_pct
                    
                    if total_voto > 0:
                        n_pos = int(max_total_burbujas * (pos_pct / total_voto))
                        n_neg = max_total_burbujas - n_pos
                    else:
                        n_pos, n_neg = 15, 15

                    n_pos = max(5, n_pos)
                    n_neg = max(5, n_neg)

                    max_pos = resultados["top_palabras_pos"]["total_count"].max() if not resultados["top_palabras_pos"].empty else 0
                    max_neg = resultados["top_palabras_neg"]["total_count"].max() if not resultados["top_palabras_neg"].empty else 0
                    max_global = max(max_pos, max_neg, 1) 

                    def crear_grafico_burbujas_pro(df_palabras, n_limite, color_hex, max_referencia):
                        if df_palabras.empty:
                            return None
                        
                        df_plot = df_palabras.head(n_limite).sample(frac=1).reset_index(drop=True)
                        
                        cols = np.linspace(0.25, 0.75, 5)
                        filas = np.linspace(0.25, 0.75, 6)
                        slots = [(c, f) for c in cols for f in filas]
                        np.random.shuffle(slots)
                        
                        x_coords, y_coords = [], []
                        for i in range(len(df_plot)):
                            slot_x, slot_y = slots[i % len(slots)]
                            x_coords.append(slot_x + np.random.uniform(-0.03, 0.03))
                            y_coords.append(slot_y + np.random.uniform(-0.03, 0.03))
                        
                        df_plot['x'] = x_coords
                        df_plot['y'] = y_coords
                        
                        ratio = df_plot['total_count'] / max_referencia
                        
                        df_plot['size_viz'] = (ratio ** 1.5) * 110 + 16

                        hover_texts = [
                            f"<b>{row['palabra'].upper()}</b><br>Dicha {row['total_count']} veces<br>en {row['doc_count']} reseñas."
                            for _, row in df_plot.iterrows()
                        ]

                        fig = px.scatter(df_plot, x='x', y='y', text='palabra')

                        fig.update_traces(
                            marker=dict(
                                size=df_plot['size_viz'],
                                sizemode='diameter',
                                color='white',
                                line=dict(width=3, color=color_hex), 
                                opacity=1
                            ),
                            textfont=dict(color=color_hex, size=13, family="Arial Black"),
                            customdata=hover_texts,
                            hovertemplate="%{customdata}<extra></extra>"
                        )

                        fig.update_layout(
                            xaxis=dict(visible=False, range=[-0.1, 1.1]),
                            yaxis=dict(visible=False, range=[-0.1, 1.1]),
                            margin=dict(l=0, r=0, t=10, b=0),
                            height=450,
                            plot_bgcolor='white',
                            shapes=[
                                dict(type="line", x0=0.0, y0=1.0, x1=0.0, y1=0.0, line=dict(color="rgba(200,200,200,0.5)", width=3)),
                                dict(type="line", x0=1.0, y0=1.0, x1=1.0, y1=0.0, line=dict(color="rgba(200,200,200,0.5)", width=3)),
                                dict(type="line", x0=0.0, y0=0.0, x1=1.0, y1=0.0, line=dict(color="rgba(200,200,200,0.5)", width=3)),
                            ]
                        )
                        return fig

                    st.divider()
                    st.markdown("##### Comparativa de Frecuencia por Contexto")
                    st.caption("El tamaño de cada burbuja indica su frecuencia real.")

                    col_w_pos, col_w_neg = st.columns(2)

                    with col_w_pos:
                        st.markdown("🟢 **Vocabulario Positivo**")
                        fig_pos = crear_grafico_burbujas_pro(resultados["top_palabras_pos"], n_pos, "#2ecc71", max_global)
                        if fig_pos:
                            st.plotly_chart(fig_pos, use_container_width=True)

                    with col_w_neg:
                        st.markdown("🔴 **Vocabulario Negativo**")
                        fig_neg = crear_grafico_burbujas_pro(resultados["top_palabras_neg"], n_neg, "#e74c3c", max_global)
                        if fig_neg:
                            st.plotly_chart(fig_neg, use_container_width=True)
                else:
                    st.warning("No hay datos suficientes para mostrar un análisis")
            with tab3:
                st.markdown(f"### ¿Cuáles son los grandes temas en {nombre_empresa}?")

                if not resultados["temas_gen"].empty:
                    total_reviews = len(resultados["df"])
                    top_tema = resultados["temas_gen"].index[0]
                    votos_top_tema = resultados["temas_gen"].iloc[0]
                    porcentaje_top = int((votos_top_tema / total_reviews) * 100) if total_reviews > 0 else 0

                    ejemplo_resena = resultados["df"][resultados["df"]["tema_ia"] == top_tema]["review"].iloc[0]
                    if len(ejemplo_resena) > 200:
                        ejemplo_resena = ejemplo_resena[:197] + "..."

                    st.write("")
                    col_badge, col_text = st.columns([1, 6])

                    with col_badge:
                        st.markdown(f"""
                            <div style="
                                background-color: #E0E0E0;
                                border-radius: 50%;
                                width: 70px;
                                height: 70px;
                                display: flex;
                                align-items: center;
                                justify-content: center;
                                font-size: 30px;
                                font-weight: bold;
                                color: #333;
                                border: 2px solid #CCC;
                            ">1</div>
                        """, unsafe_allow_html=True)

                    with col_text:
                        st.markdown(f"**EL TEMA ESTRELLA: '{top_tema.upper()}'**")
                        st.write(f"Aproximadamente el **{porcentaje_top}% de las opiniones** giran en torno a este concepto. Es lo primero que se le viene a la cabeza a tus clientes.")
                        st.caption("Un ejemplo de un cliente real hablando sobre esto sería:")
                        st.info(f" *\"{ejemplo_resena.strip()}\"*")

                    st.write("")

                    top_pos_tema = resultados["temas_pos"].index[0] if not resultados["temas_pos"].empty else None
                    top_neg_tema = resultados["temas_neg"].index[0] if not resultados["temas_neg"].empty else None
                    
                    if top_pos_tema and top_neg_tema:
                        st.success(f"""
                        **Conclusiones de los temas:** Lo que más enamora y fideliza a los clientes está relacionado con **{top_pos_tema.lower()}**. 
                        Sin embargo, el mayor problema actual, y donde se pierden más puntos, es en todo lo referente a **{top_neg_tema.lower()}**.
                        """)

                    st.divider()
                    st.markdown("##### El peso de cada tema por contexto")
                    st.caption("Pasa el ratón sobre las barras para ver en cuántas reseñas exactas se menciona cada tema.")

                    def crear_grafico_temas(serie_temas, color):
                        if serie_temas.empty:
                            return None
                        df_plot = serie_temas.reset_index()
                        df_plot.columns = ["Tema", "Menciones"]
                        df_plot = df_plot.sort_values(by="Menciones", ascending=True).tail(7) 
                        
                        fig = px.bar(
                            df_plot, 
                            x="Menciones", 
                            y="Tema", 
                            orientation='h',
                            color_discrete_sequence=[color]
                        )
                        fig.update_traces(
                            hovertemplate="<b>%{y}</b><br>Mencionado en %{x} reseñas<extra></extra>"
                        )
                        fig.update_layout(
                            xaxis=dict(visible=False), 
                            yaxis=dict(title=""), 
                            margin=dict(l=0, r=0, t=10, b=0), 
                            height=300
                        )
                        return fig

                    col_pos, col_neg = st.columns(2)

                    with col_pos:
                        st.markdown("🟢 **Temas Positivos**")
                        fig_pos = crear_grafico_temas(resultados["temas_pos"], '#2ecc71')
                        if fig_pos:
                            st.plotly_chart(fig_pos, use_container_width=True)
                        else:
                            st.info("No hay suficientes temas positivos.")

                    with col_neg:
                        st.markdown("🔴 **Temas Negativos**")
                        fig_neg = crear_grafico_temas(resultados["temas_neg"], '#e74c3c')
                        if fig_neg:
                            st.plotly_chart(fig_neg, use_container_width=True)
                        else:
                            st.info("No hay suficientes temas negativos.")
                else:
                    st.warning("No hay suficientes datos para generar el análisis de temas.")

            with tab4:
                st.header("Estadísticas de Comportamiento")

                c1, c2 = st.columns(2)
                with c1:
                    st.subheader("¿Cuánto escriben según su humor?")
                    fig_len = px.bar(
                        resultados["longitud_media"],
                        labels={'value': 'Palabras de media', 'sentimiento': 'Tipo de reseña'},
                        color=resultados["longitud_media"].index,
                        color_discrete_map={'positivo':'#2ecc71', 'neutro':'#f1c40f', 'negativo':'#e74c3c'}
                    )
                    fig_len.update_layout(showlegend=False)
                    st.plotly_chart(fig_len, use_container_width=True)

                    media_neg = resultados["longitud_media"].get("negativo", 0)
                    media_pos = resultados["longitud_media"].get("positivo", 0)
                    
                    if media_neg > media_pos:
                        st.info("Se observa una correlación entre el sentimiento negativo y la extensión del texto, sugiriendo que el cliente insatisfecho invierte más esfuerzo en detallar los puntos de fallo.")

                with c2:
                    st.subheader("Resumen de Datos Brutos")
                    st.metric("Total Reseñas", len(resultados["df"]))
                    
                    st.metric("Índice de Satisfacción", f"{score_global:.1f}%")

                st.divider()
                st.subheader("Mapa de Calor: Puntos de Dolor y Éxito")
                st.caption("Cruza los temas detectados con el sentimiento para ver dónde se concentra exactamente la frustración o la satisfacción.")
                
                df_heat = resultados["df"].copy()
                
                fig_heat = px.density_heatmap(
                    df_heat,
                    x="sentimiento",
                    y="tema_ia",
                    category_orders={"sentimiento": ["negativo", "neutro", "positivo"]}, 
                    color_continuous_scale="Blues", 
                    labels={'tema_ia': 'Tema Detectado (BERTopic)', 'sentimiento': 'Polaridad'}
                )
                
                fig_heat.update_layout(
                    xaxis_title="",
                    yaxis_title="",
                    coloraxis_colorbar_title="Nº Reseñas",
                    height=450 
                )
                
                st.plotly_chart(fig_heat, use_container_width=True)

            with tab5:
                st.subheader("Resumen Ejecutivo proporcionado por la IA")
                st.write(resultados["resumen_ia"])
                
                st.divider() 
            
                st.header(f"Recomendaciones personales para {nombre_empresa}")
                
                temas_neg = list(resultados["temas_neg"].index)
                temas_pos = list(resultados["temas_pos"].index)
                
                tema_critico_1 = temas_neg[0] if len(temas_neg) > 0 else "la gestión operativa"
                tema_exito_1 = temas_pos[0] if len(temas_pos) > 0 else "el trato al cliente"
                
                tema_critico_2 = temas_neg[1] if len(temas_neg) > 1 else "los tiempos de respuesta"
                tema_exito_2 = temas_pos[1] if len(temas_pos) > 1 else "la calidad del servicio"

                st.subheader("Diagnóstico Estratégico")
                
                st.markdown(f"""
                **Foco de fricción:** Las métricas indican que la urgencia principal actualmente recae sobre problemas relacionados con **{tema_critico_1.lower()}**. Abordar este área específica tendría el mayor impacto inmediato en la satisfacción general.
                """)
                
                if len(temas_pos) > 0:
                    st.markdown(f"""
                    **Ventaja competitiva:** Los usuarios valoran muy positivamente la experiencia vinculada a **{tema_exito_1.lower()}**. Este aspecto debe mantenerse como estandarte de la marca frente a la competencia.
                    """)
                else:
                    st.markdown("**Puntos fuertes:** Actualmente hay un margen de mejora importante para consolidar aspectos positivos claros.")

                st.divider()

                col_rec_a, col_rec_b = st.columns(2)
                
                verbos_pos = ["Potenciar", "Mantener altos estándares en", "Fomentar", "Seguir invirtiendo recursos en"]
                verbos_neg = ["Auditar procesos de", "Optimizar urgentemente", "Recopilar más feedback sobre", "Mitigar incidencias en"]

                with col_rec_a:
                    st.markdown("#### Acciones a potenciar")
                    if len(temas_pos) > 0:
                        for i, t in enumerate(temas_pos[:4]):
                            verbo = verbos_pos[i % len(verbos_pos)]
                            st.markdown(f"🔹 **{verbo}** los aspectos de *{t.lower()}*.")
                    else:
                        st.write("• No hay datos suficientes para recomendar acciones positivas.")
                
                with col_rec_b:
                    st.markdown("#### Acciones a corregir")
                    if len(temas_neg) > 0:
                        for i, t in enumerate(temas_neg[:4]):
                            verbo = verbos_neg[i % len(verbos_neg)]
                            st.markdown(f"🔸 **{verbo}** el área de *{t.lower()}*.")
                    else:
                        st.write("• Todo parece estar bajo control.")

                st.divider()

                with st.expander("Análisis profundo del Consultor", expanded=True):
                    st.write(f"""
                        Analizando la estructura de las opiniones, se evidencia que la fidelidad hacia **{nombre_empresa}** depende fuertemente de cómo se logre consolidar **{tema_exito_2.lower()}**, que actúa como un soporte de confianza para los clientes, 
                        más allá del éxito ya mencionado en {tema_exito_1.lower()}.
                        
                        Sin embargo, la presencia de quejas concurrentes relacionadas con **{tema_critico_2.lower()}** sugiere que 
                        hay cuellos de botella operativos que van más allá del problema principal. Se recomienda que el departamento 
                        de operaciones establezca KPIs (Indicadores Clave de Rendimiento) específicos para monitorear ambas áreas durante el próximo trimestre, 
                        evitando así que este ruido negativo eclipse el buen trabajo realizado en el resto de la operativa comercial.
                    """)

        else:
            st.error("No se pudo procesar el análisis. Asegúrate de que las reseñas tengan contenido suficiente.")
    else:
        st.warning("No se encontraron datos.")
else:
    display_landing_content()