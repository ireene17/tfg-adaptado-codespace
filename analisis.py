import pandas as pd
import re
import nltk
import spacy
import numpy as np
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer, pipeline
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from bertopic import BERTopic
from sentence_transformers import SentenceTransformer
from nltk.corpus import stopwords

try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')
    nltk.download('stopwords')

stop_words = set(stopwords.words("spanish"))
nlp = spacy.load("es_core_news_sm")

embedding_model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

sentiment_pipeline = pipeline(
    "sentiment-analysis",
    model="finiteautomata/beto-sentiment-analysis"
)

def limpiar_texto(texto):
    if not isinstance(texto, str) or "respuesta de" in texto.lower():
        return ""
    texto = texto.replace("Ver más", "")
    texto = re.sub(r"[^a-zA-ZáéíóúÁÉÍÓÚñÑ\s]", "", texto)
    return texto.lower().strip()

def preprocesar_spacy(texto):
    doc = nlp(texto)
    return " ".join([token.lemma_.lower() for token in doc 
                     if not token.is_stop and not token.is_punct and len(token.text) > 2])

#palabras mas importantes: 
def get_top_tfidf(dataframe, n=15):
    if len(dataframe) < 2:
        return pd.DataFrame(columns=["palabra", "importancia", "doc_count", "total_count", "total_reviews"])
    
    textos = dataframe["texto_lemma"].dropna()
    total_reviews = len(textos)
    if textos.empty:
        return pd.DataFrame(columns=["palabra", "importancia", "doc_count", "total_count", "total_reviews"])

    vec_tfidf = TfidfVectorizer(max_features=n)
    
    try:
        X_tfidf = vec_tfidf.fit_transform(textos)
        importancia = np.asarray(X_tfidf.sum(axis=0)).flatten()
        palabras = vec_tfidf.get_feature_names_out()

        vec_count = CountVectorizer(vocabulary=palabras)
        X_count = vec_count.fit_transform(textos)
        
        total_count = np.asarray(X_count.sum(axis=0)).flatten() 
        doc_count = np.asarray((X_count > 0).sum(axis=0)).flatten()

        return pd.DataFrame({
            "palabra": palabras,
            "importancia": importancia,
            "doc_count": doc_count,
            "total_count": total_count,
            "total_reviews": total_reviews
        }).sort_values(by="importancia", ascending=False)
    except:
        return pd.DataFrame(columns=["palabra", "importancia", "doc_count", "total_count", "total_reviews"])

def generar_resumen_ia(df, resultados_previos):
    if df.empty:
        return "No hay reseñas suficientes para generar un resumen."

    total = len(df)
    pos = resultados_previos['sentimiento_pct'].get('positivo', 0)
    neg = resultados_previos['sentimiento_pct'].get('negativo', 0)
    
    t_neg = list(resultados_previos['temas_neg'].index)
    t_pos = list(resultados_previos['temas_pos'].index)
    
    tema_malo_1 = t_neg[0].lower() if len(t_neg) > 0 else "el servicio general"
    tema_malo_2 = t_neg[1].lower() if len(t_neg) > 1 else "otros asuntos variados"
    
    tema_bueno_1 = t_pos[0].lower() if len(t_pos) > 0 else "la atención al cliente"
    tema_bueno_2 = t_pos[1].lower() if len(t_pos) > 1 else "la calidad del servicio"

    # Evaluamos el tono general para la frase introductoria
    if pos >= 60:
        tono = "mayoritariamente positiva"
    elif pos >= 40:
        tono = "mixta"
    else:
        tono = "crítica y con áreas de mejora urgentes"

    # Construimos el párrafo final directamente con f-strings para que suene humano
    resumen_final = (
        f"Se han analizado un total de {total} reseñas, revelando una percepción {tono} por parte de los usuarios. "
        f"Por un lado, el {pos:.1f}% de las opiniones son favorables, destacando fuertemente aspectos como {tema_bueno_1} y {tema_bueno_2}. "
        f"Por otro lado, se registra un nivel de insatisfacción del {neg:.1f}%, donde los clientes expresan frustración "
        f"principalmente con {tema_malo_1} y {tema_malo_2}."
    )

    return resumen_final


def analizar_reviews(df):
    if df.empty:
        return None

    ya_procesado = "sentimiento_ia" in df.columns
    if ya_procesado:
        df = df.rename(columns={"sentimiento_ia": "sentimiento"}).copy()
    else:
        df = df.drop_duplicates(subset=["review"]).copy()
        df["clean_review"] = df["review"].apply(limpiar_texto)
        df = df[df["clean_review"] != ""]
        
        def fast_sentiment(t):
            res = sentiment_pipeline(t[:512])[0]
            mapping = {"NEG": "negativo", "NEU": "neutro", "POS": "positivo"}
            return mapping.get(res["label"], "neutro")
        
        df["sentimiento"] = df["clean_review"].apply(fast_sentiment)

    if "texto_lemma" not in df.columns:
        df["texto_lemma"] = df["review"].apply(limpiar_texto).apply(preprocesar_spacy)

    if "tema_ia" not in df.columns:
        if len(df) >= 5:
            vectorizer_model = CountVectorizer(stop_words=list(stop_words), ngram_range=(1, 3), min_df=1)
            topic_model = BERTopic(
                embedding_model=embedding_model,
                vectorizer_model=vectorizer_model,
                min_topic_size=3, nr_topics=10, top_n_words=10,
                calculate_probabilities=False 
            )
            topics, _ = topic_model.fit_transform(df["review"].tolist())
            
            info = topic_model.get_topic_info()
            
            def crear_nombre_natural(representacion):
                if not isinstance(representacion, list):
                    return "Asuntos generales"
                    
                palabras_validas = []
                raices_vistas = set()
                palabras_prohibidas = ["solo", "sólo", "mas", "más", "tan", "hacer", "tener"]
                
                for palabra in representacion:
                    p = palabra.lower().strip()
                    
                    if len(p) <= 3 or p in palabras_prohibidas: 
                        continue
                    
                    raiz = p[:4] 
                    if raiz not in raices_vistas:
                        raices_vistas.add(raiz)
                        palabras_validas.append(p.capitalize())
                        
                    if len(palabras_validas) == 3:
                        break
                        
                if not palabras_validas:
                    return "Otros asuntos variados"
                elif len(palabras_validas) == 1:
                    return f"Conceptos de {palabras_validas[0]}"
                elif len(palabras_validas) == 2:
                    return f"{palabras_validas[0]} y {palabras_validas[1]}"
                else:
                    return f"{palabras_validas[0]}, {palabras_validas[1]} y {palabras_validas[2]}"

            temas_dict = {}
            for _, row in info.iterrows():
                if row.Topic == -1:
                    temas_dict[row.Topic] = "Otros temas variados"
                else:
                    temas_dict[row.Topic] = crear_nombre_natural(row.Representation)

            df["tema_ia"] = [temas_dict.get(t, "Otros temas variados") for t in topics]
        else:
            df["tema_ia"] = "General"

    sentimiento_pct = df["sentimiento"].value_counts(normalize=True) * 100
    
    counts_pos = df[df["sentimiento"] == "positivo"]["tema_ia"].value_counts()
    counts_neg = df[df["sentimiento"] == "negativo"]["tema_ia"].value_counts()

    todos_los_temas = set(counts_pos.index) | set(counts_neg.index)
    
    dict_pos_exclusivo = {}
    dict_neg_exclusivo = {}
    
    for tema in todos_los_temas:
        if tema in ["Otros temas", "General"]: 
            continue
            
        votos_positivos = counts_pos.get(tema, 0)
        votos_negativos = counts_neg.get(tema, 0)
        
        if votos_positivos > votos_negativos:
            dict_pos_exclusivo[tema] = votos_positivos
        elif votos_negativos > votos_positivos:
            dict_neg_exclusivo[tema] = votos_negativos
        else:
            pass

    temas_pos_final = pd.Series(dict_pos_exclusivo).sort_values(ascending=False)
    temas_neg_final = pd.Series(dict_neg_exclusivo).sort_values(ascending=False)
    temas_gen_final = df["tema_ia"].value_counts()

    res_prov = {
        'sentimiento_pct': sentimiento_pct,
        'temas_pos': temas_pos_final,
        'temas_neg': temas_neg_final
    }
    resumen_final = generar_resumen_ia(df, res_prov)

    df["longitud"] = df["review"].apply(lambda x: len(str(x).split()))
    longitud_media = df.groupby("sentimiento")["longitud"].mean()
    
    map_num = {"positivo": 1, "neutro": 0, "negativo": -1}
    df["sent_val"] = df["sentimiento"].map(map_num)
    df_trend = df.iloc[::-1].copy()
    df_trend["tendencia_suave"] = df_trend["sent_val"].rolling(window=min(10, len(df)), min_periods=1).mean()

    return {
        "df": df,
        "sentimiento_pct": sentimiento_pct,
        "top_palabras_gen": get_top_tfidf(df),
        "top_palabras_neg": get_top_tfidf(df[df["sentimiento"] == "negativo"]),
        "top_palabras_pos": get_top_tfidf(df[df["sentimiento"] == "positivo"]),
        "longitud_media": longitud_media,
        "tendencia": df_trend["tendencia_suave"].tolist(),
        "temas_gen": temas_gen_final,
        "temas_pos": temas_pos_final,
        "temas_neg": temas_neg_final,
        "resumen_ia": resumen_final
    }