import os
import streamlit as st
from dotenv import load_dotenv
import pandas as pd
from openai import OpenAI
from datetime import datetime
from docx import Document

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

# Prompt para generar descripciones concisas
describe_system_prompt = '''
Eres un sistema especializado en generar descripciones breves y precisas para escenas culturales y eventos andinos, especialmente de la festividad de la Mamacha Carmen en Paucartambo. 
Describe la escena de manera objetiva y clara, utilizando un estilo conciso. Asegúrate de destacar únicamente los elementos visibles y relevantes. 
No incluyas adornos adicionales ni interpretaciones extensas. Devuelve solo el texto de la descripción, sin formato adicional.
'''

# Prompt para generar palabras clave
keyword_system_prompt = '''
Eres un sistema experto en generar palabras clave concisas y relevantes para describir imágenes relacionadas con eventos culturales andinos. 
Tu respuesta debe incluir únicamente un arreglo de cadenas en formato JSON. 
Por ejemplo: ["máscara", "altar", "devoción", "sincretismo"]. 
No incluyas explicaciones ni texto adicional, solo las palabras clave en este formato exacto.
'''

# Prompt para exportar resúmenes culturales
export_prompt = '''
Eres un sistema especializado en generar resúmenes culturales para exportar en un documento. Tu tarea es organizar la información sobre una imagen seleccionada de la festividad de la Mamacha Carmen en Paucartambo.
Incluye:
1. Descripción de la imagen.
2. Palabras clave relevantes.
3. Fecha y detalles proporcionados por el usuario.
Devuelve un texto claro y bien estructurado, listo para ser exportado.
'''


def describe_image(img_url, title, example_descriptions):
    """
    Genera una descripción basada en el título y ejemplos previos.
    """
    prompt = f"{describe_system_prompt}\n\nEjemplos de descripciones previas:\n{example_descriptions}\n\nGenera una descripción para la siguiente imagen:\nTítulo: {title}"
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
    """
    Genera palabras clave basadas en la descripción proporcionada utilizando un modelo LLM.
    """
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
        # Intentar interpretar la respuesta como JSON válido
        keywords = eval(response_text)
        if isinstance(keywords, list):
            return keywords
        else:
            raise ValueError("La respuesta no es una lista válida.")
    except (SyntaxError, ValueError) as e:
        st.error(f"Error al analizar las palabras clave generadas. Respuesta original: {response_text}")
        return []


def export_to_word(description, keywords, date, title):
    """
    Exporta la información a un archivo Word.
    """
    doc = Document()
    doc.add_heading("Resumen Cultural", level=1)
    doc.add_paragraph(f"Fecha: {date}")
    doc.add_paragraph(f"Título: {title}")
    doc.add_paragraph(f"Descripción: {description}")
    doc.add_paragraph(f"Palabras clave: {', '.join(keywords)}")

    file_path = "resumen_cultural.docx"
    doc.save(file_path)
    return file_path


def get_combined_examples(df):
    """
    Genera ejemplos combinados de descripciones previas.
    """
    combined_examples = "Ejemplos de descripciones previas:\n\n"
    for _, row in df.iterrows():
        if pd.notna(row.get('generated_description')) and pd.notna(row.get('descripcion')):
            combined_examples += f"Título: {row['descripcion']}\nDescripción: {row['generated_description']}\n\n"
    return combined_examples


# Inicializar la aplicación Streamlit
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

    if img_url and title:
        st.image(img_url, caption="Imagen desde URL", use_column_width=True)
        example_descriptions = get_combined_examples(new_df)

        if st.button("Generar Descripción"):
            description = describe_image(img_url, title, example_descriptions)
            st.write("Descripción generada:")
            st.write(description)

            keywords = generate_keywords(description)
            st.write("Palabras clave generadas:")
            st.write(", ".join(keywords))

            # Guardar datos
            new_row = {
                "imagen": img_url,
                "descripcion": title,
                "generated_description": description,
                "keywords": keywords,
                "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            new_df = pd.concat([new_df, pd.DataFrame([new_row])], ignore_index=True)
            new_df.to_csv(new_dataset_path, sep=';', index=False, encoding='ISO-8859-1')

            # Exportar a Word
            file_path = export_to_word(description, keywords, new_row["fecha"], title)
            with open(file_path, "rb") as file:
                st.download_button(
                    label="Descargar Resumen Cultural",
                    data=file,
                    file_name="resumen_cultural.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
