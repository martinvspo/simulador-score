# app_score_gpt.py (compatible con OpenAI >= 1.0.0)

import streamlit as st
import pandas as pd
import os
from openai import OpenAI

# --- Simulador de crédito ---
def calcular_cuota(monto, plazo_meses, tasa_interes_anual=0.20):
    i = tasa_interes_anual / 12
    cuota = monto * (i * (1 + i) ** plazo_meses) / ((1 + i) ** plazo_meses - 1)
    return round(cuota, 2)

REGLAS = {
    "score_minimo": 650,
    "endeudamiento_max": 45,
    "cuota_max_porcentaje": 35
}

def sugerir_monto_maximo(ingreso_mensual, plazo_meses, tasa_interes_anual=0.20):
    cuota_max = ingreso_mensual * (REGLAS["cuota_max_porcentaje"] / 100)
    i = tasa_interes_anual / 12
    if i == 0:
        return cuota_max * plazo_meses
    monto_max = cuota_max * ((1 + i) ** plazo_meses - 1) / (i * (1 + i) ** plazo_meses)
    return round(monto_max, 2)

def evaluar_cliente(cliente):
    cuota = calcular_cuota(cliente["monto_solicitado"], cliente["plazo_meses"])
    ratio_cuota_ingreso = cuota / cliente["ingreso_mensual"] * 100

    aprobado = (
        cliente["score_sbs"] >= REGLAS["score_minimo"] and
        cliente["endeudamiento"] <= REGLAS["endeudamiento_max"] and
        ratio_cuota_ingreso <= REGLAS["cuota_max_porcentaje"]
    )

    resultado = {
        "cuota_mensual_estimada": cuota,
        "ratio_cuota_ingreso": round(ratio_cuota_ingreso, 2),
        "evaluacion": "APROBADO" if aprobado else "RECHAZADO",
        "justificacion": [],
        "sugerencia_monto": None
    }

    if cliente["score_sbs"] < REGLAS["score_minimo"]:
        resultado["justificacion"].append("El Score SBS es inferior al mínimo requerido (650).")
    if cliente["endeudamiento"] > REGLAS["endeudamiento_max"]:
        resultado["justificacion"].append("El nivel de endeudamiento supera el 45%.")
    if ratio_cuota_ingreso > REGLAS["cuota_max_porcentaje"]:
        resultado["justificacion"].append("La cuota mensual excede el 35% del ingreso.")
        resultado["sugerencia_monto"] = sugerir_monto_maximo(cliente["ingreso_mensual"], cliente["plazo_meses"])

    return resultado

# --- Interfaz ---
st.title("Evaluación de Crédito - Simulador Inteligente")

try:
    df_clientes = pd.read_csv("clientes.csv")
except:
    st.error("Archivo clientes.csv no encontrado.")
    st.stop()

nombres = ["Seleccionar"] + df_clientes["nombre"].unique().tolist()
nombre_seleccionado = st.selectbox("Buscar cliente por nombre", nombres)

cliente_data = pd.DataFrame()
if nombre_seleccionado != "Seleccionar":
    cliente_data = df_clientes[df_clientes["nombre"] == nombre_seleccionado]

if not cliente_data.empty:
    dni = cliente_data.iloc[0]["dni"]
    nombre = cliente_data.iloc[0]["nombre"]
    ingreso_mensual = cliente_data.iloc[0]["ingreso_mensual"]
    score_sbs = cliente_data.iloc[0]["score_sbs"]
    endeudamiento = cliente_data.iloc[0]["endeudamiento"]
else:
    dni = st.text_input("DNI")
    nombre = st.text_input("Nombre")
    ingreso_mensual = st.number_input("Ingreso mensual", min_value=0)
    score_sbs = st.slider("Score SBS", 400, 900, 650)
    endeudamiento = st.slider("Endeudamiento (%)", 0, 100, 20)

tipo_empleo = st.selectbox("Tipo de empleo", ["Dependiente", "Independiente"])
monto_solicitado = st.number_input("Monto solicitado", min_value=1000)
plazo_meses = st.selectbox("Plazo (meses)", [12, 24, 36, 48, 60])

if st.button("Evaluar solicitud"):
    cliente = {
        "nombre": nombre,
        "dni": dni,
        "ingreso_mensual": ingreso_mensual,
        "tipo_empleo": tipo_empleo,
        "score_sbs": score_sbs,
        "endeudamiento": endeudamiento,
        "monto_solicitado": monto_solicitado,
        "plazo_meses": plazo_meses
    }

    resultado = evaluar_cliente(cliente)

    st.subheader("Resultado de Evaluación")
    st.write("Evaluación:", resultado["evaluacion"])
    st.write("Cuota mensual estimada:", resultado["cuota_mensual_estimada"])
    st.write("Relación cuota/ingreso:", f"{resultado['ratio_cuota_ingreso']}%")

    if resultado["justificacion"]:
        st.warning("Motivos:")
        for motivo in resultado["justificacion"]:
            st.markdown(f"- {motivo}")

    if resultado["sugerencia_monto"]:
        st.info(f"Podrías aplicar a un monto aproximado de: S/ {resultado['sugerencia_monto']}")

# --- GPT Integración ---
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

def preguntar_a_gpt(pregunta):
    try:
        respuesta = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": pregunta}]
        )
        return respuesta.choices[0].message.content.strip()
    except Exception as e:
        return f"⚠️ Error al consultar GPT: {e}"

st.markdown("### 🤖 ¿Tienes dudas sobre tu evaluación?")
pregunta = st.text_input("Haz una pregunta al asesor GPT")
if pregunta:
    st.info("Consultando a GPT...")
    respuesta = preguntar_a_gpt(pregunta)
    st.success(f"Asistente GPT:

{respuesta}")
