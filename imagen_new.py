import os
import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv
from docx import Document
from docx.shared import Inches
from datetime import datetime
from PIL import Image
import tempfile
import pandas as pd
import ast

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
    new_df = pd.DataFrame(columns=["imagen", "descripcion", "generated_description", "palabras_clave", "fecha"])

# Prompt para generar descripciones concisas
describe_system_prompt = '''
Eres un sistema especializado en generar descripciones breves y precisas para escenas culturales y eventos andinos, especialmente de la festividad de la Mamacha Carmen en Paucartambo. Describe de manera clara y objetiva la escena principal, destacando solo los elementos visibles y relevantes sin adornos adicionales. Mantente directo y conciso.
'''

# Prompt para extraer palabras clave
keyword_system_prompt = '''
Eres un sistema especializado en generar palabras clave relevantes para escenas culturales y eventos andinos. Extrae términos significativos que describan la identidad cultural y ritual andina en un formato de lista de cadenas JSON válido.
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

def generate_keywords(description):
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
    try:
        return ast.literal_eval(response.choices[0].message.content.strip())
    except (SyntaxError, ValueError):
        st.error("Error al analizar las palabras clave generadas. Revisa el formato de la respuesta.")
        return []

def export_to_word(img_url, description, keywords):
    doc = Document()
    doc.add_heading("Resumen Cultural", level=1)
    doc.add_paragraph(f"Descripción: {description}")
    doc.add_paragraph(f"Palabras clave: {', '.join(keywords)}")
    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
        tmp_file.write(requests.get(img_url).content)
        doc.add_picture(tmp_file.name, width=Inches(4))
    file_path = "resumen_cultural.docx"
    doc.save(file_path)
    return file_path

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
                st.write("Descripción en español:")
                st.write(description)
                keywords = generate_keywords(description)
                st.write("**Palabras clave:**")
                cols = st.columns(max(1, len(keywords)))
                for col, keyword in zip(cols, keywords):
                    with col:
                        st.button(keyword)
                new_row = {
                    "imagen": img_url,
                    "descripcion": title,
                    "generated_description": description,
                    "palabras_clave": ", ".join(keywords),
                    "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                new_df = pd.concat([new_df, pd.DataFrame([new_row])], ignore_index=True)
                new_df.to_csv(new_dataset_path, sep=';', index=False, encoding='ISO-8859-1')
                if st.button("Exportar a Word"):
                    file_path = export_to_word(img_url, description, keywords)
                    with open(file_path, "rb") as file:
                        st.download_button(
                            label="Descargar Resumen Cultural",
                            data=file,
                            file_name="resumen_cultural.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                        )
            except Exception as e:
                st.error(f"Error al generar la descripción: {e}")
