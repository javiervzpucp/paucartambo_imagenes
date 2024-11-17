import os
import streamlit as st
from firebase_admin import credentials, initialize_app, firestore
from openai import OpenAI
from dotenv import load_dotenv
import pandas as pd
from datetime import datetime

# Cargar las variables de entorno desde el archivo .env
load_dotenv()

# Leer credenciales desde st.secrets para OpenAI y Firebase
openai_api_key = st.secrets['openai']["OPENAI_API_KEY"]
firebase_creds = st.secrets["firebase"]

# Inicializar cliente OpenAI
client = OpenAI(api_key=openai_api_key)

# Crear el objeto de credenciales usando las claves de Firebase desde st.secrets
cred = credentials.Certificate({
    "type": firebase_creds["type"],
    "project_id": firebase_creds["project_id"],
    "private_key_id": firebase_creds["private_key_id"],
    "private_key": firebase_creds["private_key"].replace("\\n", "\n"),  # Reemplazar saltos de línea
    "client_email": firebase_creds["client_email"],
    "client_id": firebase_creds["client_id"],
    "auth_uri": firebase_creds["auth_uri"],
    "token_uri": firebase_creds["token_uri"],
    "auth_provider_x509_cert_url": firebase_creds["auth_provider_x509_cert_url"],
    "client_x509_cert_url": firebase_creds["client_x509_cert_url"]
})

# Inicializar Firebase
if not firestore.client():
    initialize_app(cred)

# Usar Firestore
db = firestore.client()

# Rutas de archivos CSV
dataset_path = "imagenes/imagenes.csv"
new_dataset_path = "imagenes/nuevas_descripciones.csv"

# Cargar o inicializar los DataFrames
df = pd.read_csv(dataset_path, delimiter=';', encoding='ISO-8859-1')
if os.path.exists(new_dataset_path):
    new_df = pd.read_csv(new_dataset_path, delimiter=';', encoding='ISO-8859-1')
else:
    new_df = pd.DataFrame(columns=["imagen", "descripcion", "generated_description", "fecha"])

# Prompt para generar descripciones
describe_system_prompt = '''
Eres un sistema especializado en generar descripciones breves y precisas para escenas culturales y eventos andinos, especialmente de la festividad de la Mamacha Carmen en Paucartambo. Describe de manera clara y objetiva la escena principal, destacando solo los elementos visibles y relevantes sin adornos adicionales. Mantente directo y conciso.
'''

# Guardar datos en Firebase Firestore
def guardar_datos_en_firestore(collection, document, data):
    doc_ref = db.collection(collection).document(document)
    doc_ref.set(data)
    st.success(f"Datos guardados en Firestore: {data}")

# Generar descripción de imagen
def describe_image(img_url, title):
    prompt = f"{describe_system_prompt}\nTítulo: {title}\nImagen URL: {img_url}\n"
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

# Inicializar la aplicación Streamlit
st.title("Generador de Descripciones de Imágenes de Danzas de Paucartambo")

# Sidebar para historial
with st.sidebar:
    st.write("Opciones")
    if st.checkbox("Mostrar historial"):
        st.dataframe(new_df[["imagen", "descripcion", "generated_description"]])
        csv = new_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Descargar historial como CSV",
            data=csv,
            file_name="historial_descripciones.csv",
            mime="text/csv",
        )

# Entrada para URL o archivo de imagen
option = st.radio("Seleccione el método para proporcionar una imagen:", ("URL de imagen", "Subir imagen"))

if option == "URL de imagen":
    img_url = st.text_input("Ingrese la URL de la imagen")
    title = st.text_input("Ingrese un título o descripción breve de la imagen")
    if img_url and title:
        st.image(img_url, caption="Imagen desde URL", use_column_width=True)
        if st.button("Generar Descripción"):
            try:
                description = describe_image(img_url, title)
                st.write("Descripción generada:")
                st.write(description)
                new_row = {
                    "imagen": img_url,
                    "descripcion": title,
                    "generated_description": description,
                    "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                new_df = pd.concat([new_df, pd.DataFrame([new_row])], ignore_index=True)
                new_df.to_csv(new_dataset_path, sep=';', index=False, encoding='ISO-8859-1')
                guardar_datos_en_firestore("descripciones", title, new_row)
            except Exception as e:
                st.error(f"Error al generar la descripción: {e}")
else:
    uploaded_file = st.file_uploader("Cargue una imagen", type=["jpg", "jpeg", "png"])
    title = st.text_input("Ingrese un título o descripción breve de la imagen")
    if uploaded_file and title:
        st.image(uploaded_file, caption="Imagen cargada", use_column_width=True)
        if st.button("Generar Descripción"):
            try:
                img_url = f"imagen_cargada_{uploaded_file.name}"
                description = describe_image(img_url, title)
                st.write("Descripción generada:")
                st.write(description)
                new_row = {
                    "imagen": img_url,
                    "descripcion": title,
                    "generated_description": description,
                    "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                new_df = pd.concat([new_df, pd.DataFrame([new_row])], ignore_index=True)
                new_df.to_csv(new_dataset_path, sep=';', index=False, encoding='ISO-8859-1')
                guardar_datos_en_firestore("descripciones", title, new_row)
            except Exception as e:
                st.error(f"Error al generar la descripción: {e}")
