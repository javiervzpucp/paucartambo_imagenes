# -*- coding: utf-8 -*-
"""
App para generación de descripciones de imágenes con palabras clave y registro en Firebase.
"""

import os
import streamlit as st
from dotenv import load_dotenv
import pandas as pd
from openai import OpenAI
from PIL import Image
import tempfile
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore
from collections import Counter

# Configuración de Firebase
load_dotenv()
cred = credentials.Certificate("firebase-credentials.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# Configuración de OpenAI
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

# Prompt para descripciones
describe_system_prompt = '''
Eres un sistema especializado en generar descripciones breves y precisas para escenas culturales y eventos andinos. Describe de manera clara y objetiva la escena principal, destacando elementos visibles y relevantes. Sé conciso.
'''

# Prompt para palabras clave
keywords_system_prompt = '''
Eres un sistema que genera palabras clave relevantes para escenas culturales andinas. Extrae palabras como 'danza', 'procesión', 'altar' y similares que representen elementos culturales y rituales.
'''

# Funciones para Firebase
def save_to_firestore(collection, data):
    try:
        db.collection(collection).add(data)
    except Exception as e:
        st.error(f"Error al guardar en Firebase: {e}")

def save_keywords_to_firestore(user_id, image_url, keywords):
    save_to_firestore("keywords", {
        "user_id": user_id,
        "image_url": image_url,
        "keywords": keywords,
        "timestamp": firestore.SERVER_TIMESTAMP
    })

def save_feedback_to_firestore(user_id, query, response, is_useful):
    save_to_firestore("feedback", {
        "user_id": user_id,
        "query": query,
        "response": response,
        "is_useful": is_useful,
        "timestamp": firestore.SERVER_TIMESTAMP
    })

# Funciones auxiliares
def get_combined_examples(df):
    if 'generated_description' not in df.columns:
        return "No hay descripciones generadas previas."
    combined_examples = "Ejemplos previos:\n\n"
    for _, row in df.iterrows():
        if pd.notna(row.get('generated_description')) and pd.notna(row.get('descripcion')):
            combined_examples += f"Título: {row['descripcion']}\nDescripción: {row['generated_description']}\n\n"
    return combined_examples

def describe_image(img_url, title, example_descriptions):
    prompt = f"{describe_system_prompt}\n\n{example_descriptions}\n\nTítulo: {title}"
    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[{"role": "system", "content": describe_system_prompt},
                  {"role": "user", "content": prompt}],
        max_tokens=300,
        temperature=0.2
    )
    return response.choices[0].message.content.strip()

def generate_keywords(description):
    prompt = f"{keywords_system_prompt}\n\nDescripción: {description}"
    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[{"role": "system", "content": keywords_system_prompt},
                  {"role": "user", "content": prompt}],
        max_tokens=100,
        temperature=0.2
    )
    return response.choices[0].message.content.strip().split(',')

# Interfaz de Streamlit
st.title("Generador de Descripciones y Palabras Clave")

# Mostrar historial desde Firebase
st.sidebar.title("Opciones")
if st.sidebar.checkbox("Mostrar historial de Firebase"):
    docs = db.collection("keywords").stream()
    historial = [{"imagen": doc.to_dict()["image_url"], 
                  "keywords": ", ".join(doc.to_dict()["keywords"])} for doc in docs]
    st.sidebar.write(historial)

# Entrada de imagen
option = st.radio("Seleccione el método para proporcionar una imagen:", ("URL de imagen", "Subir imagen"))

if option == "URL de imagen":
    img_url = st.text_input("Ingrese la URL de la imagen")
    title = st.text_input("Ingrese un título para la imagen")
    if img_url and title:
        st.image(img_url, caption="Imagen cargada desde URL", use_column_width=True)
        example_descriptions = get_combined_examples(new_df)
        if st.button("Generar Descripción"):
            try:
                description = describe_image(img_url, title, example_descriptions)
                keywords = generate_keywords(description)
                st.write("Descripción:")
                st.write(description)
                st.write("Palabras clave:")
                st.write(", ".join(keywords))
                save_keywords_to_firestore("usuario_demo", img_url, keywords)
            except Exception as e:
                st.error(f"Error: {e}")
else:
    uploaded_file = st.file_uploader("Subir una imagen", type=["jpg", "jpeg", "png"])
    title = st.text_input("Ingrese un título para la imagen")
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
                keywords = generate_keywords(description)
                st.write("Descripción:")
                st.write(description)
                st.write("Palabras clave:")
                st.write(", ".join(keywords))
                save_keywords_to_firestore("usuario_demo", img_url, keywords)
            except Exception as e:
                st.error(f"Error: {e}")

# Retroalimentación del usuario
st.write("¿Fue útil esta información?")
if st.button("👍 Sí"):
    save_feedback_to_firestore("usuario_demo", "Última pregunta", "Última respuesta", True)
    st.success("Gracias por tu retroalimentación.")
if st.button("👎 No"):
    save_feedback_to_firestore("usuario_demo", "Última pregunta", "Última respuesta", False)
    st.warning("Gracias por tu retroalimentación.")
