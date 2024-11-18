import os
import streamlit as st
from dotenv import load_dotenv
import pandas as pd
from datetime import datetime
from docx import Document
from docx.shared import Inches
import requests
from PIL import Image
from io import BytesIO
import tempfile
from googletrans import Translator

# Cargar las variables de entorno desde el archivo .env
load_dotenv()
openai_api_key = st.secrets["OPENAI_API_KEY"]

# Inicializar traductor de Google
translator = Translator()

# Rutas de archivos CSV
dataset_path = "imagenes/imagenes.csv"
new_dataset_path = "imagenes/nuevas_descripciones.csv"

# Cargar o inicializar los DataFrames
df = pd.read_csv(dataset_path, delimiter=';', encoding='ISO-8859-1')
if os.path.exists(new_dataset_path):
    new_df = pd.read_csv(new_dataset_path, delimiter=';', encoding='ISO-8859-1')
else:
    new_df = pd.DataFrame(columns=["imagen", "descripcion", "generated_description", "keywords", "fecha"])

# Prompts para descripciones y palabras clave
describe_system_prompt = '''
Eres un sistema especializado en generar descripciones breves y precisas para escenas culturales y eventos andinos, especialmente de la festividad de la Mamacha Carmen en Paucartambo. 
Describe la escena de manera objetiva y clara, utilizando un estilo conciso. Asegúrate de destacar únicamente los elementos visibles y relevantes. 
No incluyas adornos adicionales ni interpretaciones extensas. Devuelve solo el texto de la descripción, sin formato adicional.
'''

keyword_system_prompt = '''
Eres un sistema experto en generar palabras clave concisas y relevantes para describir imágenes relacionadas con eventos culturales andinos. 
Tu respuesta debe incluir únicamente un arreglo de cadenas en formato JSON. 
Por ejemplo: ["máscara", "altar", "devoción", "sincretismo"]. 
No incluyas explicaciones ni texto adicional, solo las palabras clave en este formato exacto.
'''

# Funciones
def validate_image_url(url):
    try:
        response = requests.head(url)
        return response.status_code == 200 and "image" in response.headers["content-type"]
    except Exception:
        return False

def describe_image(title):
    # Simular descripción generada
    return f"Descripción de ejemplo para el título: {title}"

def generate_keywords(description):
    # Simular palabras clave generadas
    return ["máscara", "danza", "devoción"]

def translate_to_quechua(text):
    try:
        translation = translator.translate(text, src="es", dest="qu")
        return translation.text
    except Exception as e:
        return f"Error al traducir: {e}"

def export_to_word(description, quechua_translation, keywords, date, title, img_path):
    doc = Document()
    doc.add_heading("Resumen Imagen", level=1)
    doc.add_paragraph(f"Fecha: {date}")
    doc.add_paragraph(f"Título: {title}")
    doc.add_paragraph(f"Descripción: {description}")
    doc.add_paragraph(f"Traducción al Quechua: {quechua_translation}")
    doc.add_paragraph(f"Palabras clave: {', '.join(keywords)}")
    try:
        doc.add_picture(img_path, width=Inches(5.0))
    except Exception as e:
        st.error(f"No se pudo agregar la imagen: {e}")
    file_path = "resumen_imagen.docx"
    doc.save(file_path)
    return file_path

def save_to_csv(dataframe, file_path):
    dataframe.to_csv(file_path, sep=';', index=False, encoding='ISO-8859-1')

def get_combined_examples(df):
    combined_examples = "Ejemplos de descripciones previas:\n\n"
    for _, row in df.iterrows():
        if pd.notna(row.get('generated_description')) and pd.notna(row.get('descripcion')):
            combined_examples += f"Título: {row['descripcion']}\nDescripción: {row['generated_description']}\n\n"
    return combined_examples

# Interfaz de Streamlit
st.title("Generador de Descripciones de Imágenes de Danzas de Paucartambo")

# Sidebar para mostrar historial y opciones
with st.sidebar:
    st.write("Opciones")
    if st.checkbox("Mostrar historial"):
        st.dataframe(new_df[["imagen", "descripcion", "generated_description", "keywords"]])

# Entrada de imagen y descripción
option = st.radio("Seleccione el método para proporcionar una imagen:", ("URL de imagen", "Subir imagen"))

if option == "URL de imagen":
    img_url = st.text_input("Ingrese la URL de la imagen")
    title = st.text_input("Ingrese un título o descripción breve de la imagen")

    if img_url and validate_image_url(img_url):
        response = requests.get(img_url)
        image = Image.open(BytesIO(response.content))
        st.image(image, caption="Imagen desde URL", use_column_width=True)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_file:
            image.save(temp_file.name)
            img_path = temp_file.name

        if st.button("Generar Descripción"):
            try:
                description = describe_image(title)
                quechua_translation = translate_to_quechua(description)
                keywords = generate_keywords(description)
                st.write("Descripción generada:")
                st.write(description)
                st.write("Traducción al Quechua:")
                st.write(quechua_translation)
                st.write("Palabras clave generadas:")
                st.write(", ".join(keywords))
                new_row = {
                    "imagen": img_url,
                    "descripcion": title,
                    "generated_description": description,
                    "keywords": keywords,
                    "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                new_df = pd.concat([new_df, pd.DataFrame([new_row])], ignore_index=True)
                new_df.to_csv(new_dataset_path, sep=';', index=False, encoding='ISO-8859-1')
                file_path = export_to_word(description, quechua_translation, keywords, new_row["fecha"], title, img_path)
                with open(file_path, "rb") as file:
                    st.download_button(
                        label="Descargar Resumen Cultural",
                        data=file,
                        file_name="resumen_imagen.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )
            except Exception as e:
                st.error(f"Error al generar la descripción: {e}")
else:
    uploaded_file = st.file_uploader("Cargue una imagen", type=["jpg", "jpeg", "png"])
    title = st.text_input("Ingrese un título o descripción breve de la imagen")
    if uploaded_file:
        image = Image.open(uploaded_file)
        st.image(image, caption="Imagen cargada", use_column_width=True)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_file:
            image.save(temp_file.name)
            img_path = temp_file.name

        if st.button("Generar Descripción"):
            try:
                description = describe_image(title)
                quechua_translation = translate_to_quechua(description)
                keywords = generate_keywords(description)
                st.write("Descripción generada:")
                st.write(description)
                st.write("Traducción al Quechua:")
                st.write(quechua_translation)
                st.write("Palabras clave generadas:")
                st.write(", ".join(keywords))
                new_row = {
                    "imagen": img_path,
                    "descripcion": title,
                    "generated_description": description,
                    "keywords": keywords,
                    "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                new_df = pd.concat([new_df, pd.DataFrame([new_row])], ignore_index=True)
                new_df.to_csv(new_dataset_path, sep=';', index=False, encoding='ISO-8859-1')
                file_path = export_to_word(description, quechua_translation, keywords, new_row["fecha"], title, img_path)
                with open(file_path, "rb") as file:
                    st.download_button(
                        label="Descargar Texto Resumen",
                        data=file,
                        file_name="resumen_imagen.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )
            except Exception as e:
                st.error(f"Error al generar la descripción: {e}")
