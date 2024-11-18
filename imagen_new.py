import os
import streamlit as st
from dotenv import load_dotenv
import pandas as pd
from openai import OpenAI
from datetime import datetime
from docx import Document
from docx.shared import Inches
import requests
from PIL import Image
from io import BytesIO
import tempfile

# Cargar las variables de entorno desde el archivo .env
load_dotenv()
openai_api_key = st.secrets["OPENAI_API_KEY"]
client = OpenAI(api_key=openai_api_key)

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

# Funciones principales
def describe_image(img_path, title):
    """Generar descripción basada en la imagen y el título."""
    prompt = f"{describe_system_prompt}\n\nGenera una descripción para la siguiente imagen:\nTítulo: {title}"
    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[
            {"role": "system", "content": describe_system_prompt},
            {"role": "user", "content": prompt}
        ],
        max_tokens=300,
        temperature=0.2
    )
    return response.choices[0].message.content.strip()

def generate_keywords(description):
    """Generar palabras clave a partir de la descripción."""
    prompt = f"{keyword_system_prompt}\n\nDescripción: {description}"
    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[
            {"role": "system", "content": keyword_system_prompt},
            {"role": "user", "content": prompt}
        ],
        max_tokens=100,
        temperature=0.2
    )
    response_text = response.choices[0].message.content.strip()
    try:
        keywords = eval(response_text)
        if isinstance(keywords, list):
            return keywords
        else:
            raise ValueError("La respuesta no es una lista válida.")
    except (SyntaxError, ValueError):
        st.error(f"Error al analizar las palabras clave generadas. Respuesta original: {response_text}")
        return []

def export_to_word(description, keywords, date, title, img_path):
    """Exportar la información generada a un archivo Word."""
    doc = Document()
    doc.add_heading("Resumen Imagen", level=1)
    doc.add_paragraph(f"Fecha: {date}")
    doc.add_paragraph(f"Título: {title}")
    doc.add_paragraph(f"Descripción: {description}")
    doc.add_paragraph(f"Palabras clave: {', '.join(keywords)}")
    try:
        doc.add_picture(img_path, width=Inches(5.0))
    except Exception as e:
        st.error(f"No se pudo agregar la imagen: {e}")
    file_path = "resumen_imagen.docx"
    doc.save(file_path)
    return file_path

# Interfaz de Streamlit
st.title("Generador de Descripciones de Imágenes de Danzas de Paucartambo")

# Pestañas para organizar funciones
tabs = st.tabs(["Historial", "Generar Descripción", "Compartir"])

# Tab 1: Historial
with tabs[0]:
    st.header("Historial de Descripciones")
    if not new_df.empty:
        st.dataframe(new_df[["imagen", "descripcion", "generated_description", "keywords"]])
        st.download_button(
            label="Descargar Historial",
            data=new_df.to_csv(index=False).encode("utf-8"),
            file_name="historial_descripciones.csv",
            mime="text/csv"
        )
    else:
        st.info("No hay descripciones generadas aún.")

# Tab 2: Generar descripción
with tabs[1]:
    st.header("Generar Nueva Descripción")
    option = st.radio("Seleccione el método para proporcionar una imagen:", ("URL de imagen", "Subir imagen"))

    if option == "URL de imagen":
        img_url = st.text_input("Ingrese la URL de la imagen")
        title = st.text_input("Ingrese un título o descripción breve de la imagen")

        if img_url:
            try:
                response = requests.get(img_url)
                image = Image.open(BytesIO(response.content))
                st.image(image, caption="Imagen desde URL", use_column_width=True)
                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_file:
                    image.save(temp_file.name)
                    img_path = temp_file.name

                if st.button("Generar Descripción"):
                    description = describe_image(img_path, title)
                    keywords = generate_keywords(description)

                    st.write(f"**Descripción generada:** {description}")
                    st.write(f"**Palabras clave generadas:** {', '.join(keywords)}")

            except Exception as e:
                st.error(f"Error al procesar la imagen: {e}")

# Tab 3: Compartir
with tabs[2]:
    st.header("Compartir Resultados")
    if not new_df.empty:
        st.write("Selecciona un registro para compartir.")
        selected_row = st.selectbox("Descripciones generadas", new_df.index, format_func=lambda x: new_df.iloc[x]["descripcion"])
        if selected_row is not None:
            description = new_df.iloc[selected_row]["generated_description"]
            keywords = new_df.iloc[selected_row]["keywords"]
            img_url = new_df.iloc[selected_row]["imagen"]
            st.write(f"**Descripción:** {description}")
            st.write(f"**Palabras clave:** {', '.join(keywords)}")
            st.image(img_url, caption="Imagen seleccionada")

            whatsapp_message = f"Descripción: {description}\nPalabras clave: {', '.join(keywords)}"
            st.write("Envía este mensaje por WhatsApp:")
            st.markdown(f"[Enviar por WhatsApp](https://api.whatsapp.com/send?text={whatsapp_message})")
