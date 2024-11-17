import os
import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv
from docx import Document
from datetime import datetime
from PIL import Image
import tempfile
import pandas as pd

# Cargar las variables de entorno desde el archivo .env
#load_dotenv()
openai_api_key = st.secrets['openai']["OPENAI_API_KEY"]
client = OpenAI(api_key=openai_api_key)

# Rutas de archivos CSV
dataset_path = "imagenes/imagenes.csv"
new_dataset_path = "imagenes/nuevas_descripciones.csv"

# Cargar o inicializar los DataFrames
df = pd.read_csv(dataset_path, delimiter=';', encoding='ISO-8859-1')
if os.path.exists(new_dataset_path):
    new_df = pd.read_csv(new_dataset_path, delimiter=';', encoding='ISO-8859-1')
else:
    new_df = pd.DataFrame(columns=["imagen", "descripcion", "generated_description", "fecha"])

# Prompt para generar descripciones concisas
describe_system_prompt = '''
Eres un sistema especializado en generar descripciones breves y precisas para escenas culturales y eventos andinos, especialmente de la festividad de la Mamacha Carmen en Paucartambo. Describe de manera clara y objetiva la escena principal, destacando solo los elementos visibles y relevantes sin adornos adicionales. Mantente directo y conciso.
'''

def get_combined_examples(df):
    if 'generated_description' not in df.columns:
        return "No hay descripciones generadas previas."
    combined_examples = "Ejemplos de descripciones previas:\n\n"
    for _, row in df.iterrows():
        if pd.notna(row.get('generated_description')) and pd.notna(row.get('descripcion')):
            combined_examples += f"Título: {row['descripcion']}\nDescripción: {row['generated_description']}\n\n"
    return combined_examples

def describe_image(img_url, title, example_descriptions):
    prompt = f"{describe_system_prompt}\n\n{example_descriptions}\n\nGenera una descripción para la siguiente imagen:\nTítulo: {title}"
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

# Función para generar palabras clave
def generate_keywords(description):
    prompt = f"Eres un experto en identificar palabras clave culturales. Basándote en la descripción: '{description}', extrae palabras clave relacionadas con elementos culturales, rituales, e identidad andina."
    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[
            {"role": "system", "content": "Eres un experto en palabras clave culturales."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=100,
        temperature=0.5
    )
    return response.choices[0].message.content.strip().split(',')

# Función para generar un resumen cultural
def generate_summary(title, keywords):
    summary = f"Esta imagen representa los temas de {', '.join(keywords)}, elementos clave de las festividades de la Mamacha Carmen en Paucartambo."
    return summary

# Función para exportar a un archivo Word
def export_to_doc(title, summary, keywords):
    doc = Document()
    doc.add_heading("Resumen Cultural", level=1)
    doc.add_paragraph(f"Título: {title}")
    doc.add_paragraph(f"Resumen: {summary}")
    doc.add_paragraph("Palabras clave:")
    for keyword in keywords:
        doc.add_paragraph(f"- {keyword.strip()}")
    filename = f"resumen_cultural_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
    doc.save(filename)
    return filename

# Inicializar la aplicación Streamlit
st.title("Generador de Descripciones de Imágenes de Danzas de Paucartambo")

option = st.radio("Seleccione el método para proporcionar una imagen:", ("URL de imagen", "Subir imagen"))

if option == "URL de imagen":
    img_url = st.text_input("Ingrese la URL de la imagen")
    title = st.text_input("Ingrese un título o descripción breve de la imagen")
    if img_url and title:
        st.image(img_url, caption="Imagen desde URL", use_column_width=True)
        example_descriptions = get_combined_examples(new_df)
        if st.button("Generar Descripción"):
            try:
                description = describe_image(img_url, title, example_descriptions)
                st.write("Descripción generada:")
                st.write(description)

                keywords = generate_keywords(description)
                st.write("Palabras clave:")
                st.write(", ".join(keywords))

                summary = generate_summary(title, keywords)
                st.write("Resumen cultural:")
                st.write(summary)

                filename = export_to_doc(title, summary, keywords)
                with open(filename, "rb") as file:
                    st.download_button(
                        label="Descargar Resumen como Word",
                        data=file,
                        file_name=filename,
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )
            except Exception as e:
                st.error(f"Error: {e}")
else:
    uploaded_file = st.file_uploader("Cargue una imagen", type=["jpg", "jpeg", "png"])
    title = st.text_input("Ingrese un título o descripción breve de la imagen")
    if uploaded_file and title:
        image = Image.open(uploaded_file)
        st.image(image, caption="Imagen cargada", use_column_width=True)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_file:
            temp_file.write(uploaded_file.getbuffer())
            img_url = temp_file.name

        example_descriptions = get_combined_examples(new_df)
        if st.button("Generar Descripción"):
            try:
                description = describe_image(img_url, title, example_descriptions)
                st.write("Descripción generada:")
                st.write(description)

                keywords = generate_keywords(description)
                st.write("Palabras clave:")
                st.write(", ".join(keywords))

                summary = generate_summary(title, keywords)
                st.write("Resumen cultural:")
                st.write(summary)

                filename = export_to_doc(title, summary, keywords)
                with open(filename, "rb") as file:
                    st.download_button(
                        label="Descargar Resumen como Word",
                        data=file,
                        file_name=filename,
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )
            except Exception as e:
                st.error(f"Error: {e}")
