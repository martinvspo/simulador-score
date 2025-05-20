# app_score_gpt.py (con explicación, sugerencia y autocompletado por nombre o DNI)

import streamlit as st
import pandas as pd
import os

# --- Simulador de crédito ---
def calcular_cuota(monto, plazo_meses, tasa_interes_anual=0.20):
    i = tasa_interes_anual / 12
    cuota = monto * (i * (1 + i) ** plazo_meses) / ((1 + i) ** plazo_meses - 1)
    return round(cuota, 2)

# --- Evaluación automática ---
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
        resultado["justificacion"].append("El Score SBS es inferior al mínimo requerido (650). Esto indica mayor riesgo de incumplimiento.")
    if cliente["endeudamiento"] > REGLAS["endeudamiento_max"]:
        resultado["justificacion"].append("El nivel de endeudamiento supera el 45%, lo que indica carga financiera alta.")
    if ratio_cuota_ingreso > REGLAS["cuota_max_porcentaje"]:
        resultado["justificacion"].append("La cuota mensual excede el 35% de su ingreso, lo cual se considera poco sostenible.")
        resultado["sugerencia_monto"] = sugerir_monto_maximo(cliente["ingreso_mensual"], cliente["plazo_meses"])

    return resultado

# --- Interfaz con Streamlit ---
st.title("Evaluación de Crédito - Simulador Inteligente")

# Cargar base de datos de clientes
try:
    df_clientes = pd.read_csv("clientes.csv")
except FileNotFoundError:
    st.error("No se encontró el archivo 'clientes.csv'. Asegúrate de colocarlo en la misma carpeta que esta aplicación.")
    st.stop()

# Autocompletado por nombre
nombres_unicos = df_clientes["nombre"].unique().tolist()
nombre_seleccionado = st.selectbox("Buscar cliente por nombre", ["Seleccionar"] + nombres_unicos)

cliente_data = pd.DataFrame()

if nombre_seleccionado != "Seleccionar":
    cliente_data = df_clientes[df_clientes["nombre"] == nombre_seleccionado]
    if not cliente_data.empty:
        dni = str(cliente_data.iloc[0]["dni"])
        st.markdown(f"**DNI detectado automáticamente:** {dni}")
else:
    dni = st.text_input("DNI")
    if dni.isdigit():
        cliente_data = df_clientes[df_clientes["dni"] == int(dni)]

with st.form("formulario_credito"):
    if not cliente_data.empty:
        nombre = cliente_data.iloc[0]["nombre"]
        ingreso_mensual = cliente_data.iloc[0]["ingreso_mensual"]
        score_sbs = cliente_data.iloc[0]["score_sbs"]
        endeudamiento = cliente_data.iloc[0]["endeudamiento"]
        st.markdown(f"**Nombre:** {nombre}")
        st.markdown(f"**Ingreso mensual:** S/{ingreso_mensual}")
        st.markdown(f"**Score SBS:** {score_sbs}")
        st.markdown(f"**Endeudamiento:** {endeudamiento}%")
    else:
        nombre = st.text_input("Nombre completo")
        ingreso_mensual = st.number_input("Ingreso mensual (S/)", min_value=500, step=100)
        score_sbs = st.slider("Score SBS", min_value=400, max_value=900, value=700)
        endeudamiento = st.slider("Nivel de endeudamiento (%)", min_value=0, max_value=100, value=30)

    tipo_empleo = st.selectbox("Tipo de empleo", ["Dependiente", "Independiente"])
    monto_solicitado = st.number_input("Monto solicitado (S/)", min_value=1000, step=500)
    plazo_meses = st.selectbox("Plazo en meses", [12, 24, 36, 48, 60])
    enviar = st.form_submit_button("Evaluar solicitud")

if enviar:
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

    st.subheader("Resultado de la Evaluación")
    st.write(f"**Evaluación:** {resultado['evaluacion']}")
    st.write(f"**Cuota estimada mensual:** S/{resultado['cuota_mensual_estimada']}")
    st.write(f"**Relación cuota/ingreso:** {resultado['ratio_cuota_ingreso']}%")

    if resultado["justificacion"]:
        st.write("**Motivos detallados del rechazo:**")
        for motivo in resultado["justificacion"]:
            st.markdown(f"- {motivo}")

    if resultado["sugerencia_monto"]:
        st.warning(f"Según tu ingreso y plazo, podrías aplicar a un préstamo máximo aproximado de S/{resultado['sugerencia_monto']}")

    # Guardar el historial en un archivo CSV
    historial = pd.DataFrame([{
        "dni": dni,
        "nombre": nombre,
        "ingreso_mensual": ingreso_mensual,
        "score_sbs": score_sbs,
        "endeudamiento": endeudamiento,
        "tipo_empleo": tipo_empleo,
        "monto_solicitado": monto_solicitado,
        "plazo_meses": plazo_meses,
        "evaluacion": resultado["evaluacion"],
        "cuota_mensual": resultado["cuota_mensual_estimada"],
        "ratio_cuota_ingreso": resultado["ratio_cuota_ingreso"]
    }])

    historial_path = "historial_evaluaciones.csv"
    if os.path.exists(historial_path):
        historial.to_csv(historial_path, mode='a', header=False, index=False)
    else:
        historial.to_csv(historial_path, index=False)

    st.success("Evaluación registrada en el historial.")

# --- Mostrar historial de evaluaciones ---
st.markdown("---")
st.subheader("Historial de Evaluaciones")

if os.path.exists("historial_evaluaciones.csv"):
    df_historial = pd.read_csv("historial_evaluaciones.csv")
    st.dataframe(df_historial)
else:
    st.info("Aún no hay evaluaciones registradas.")
