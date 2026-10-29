
# ==========================================
# AQUATRACE - SIMULADOR DE BOYAS
# Cliente HTTP
# python -u .\simulador.py
# ==========================================

import requests
import random
import time

from datetime import datetime, timezone

# ==========================================
# CONFIGURACION
# ==========================================

SERVIDOR = "http://127.0.0.1:5000/api/mediciones"

INTERVALO = 5

# Boyas con ubicaciones simuladas
BOYAS = {
    1: {
        "lat": 2.444814,
        "lon": -76.614739,
        "temp": 22.0,
        "turbidez": 20.0,
        "ph": 7.0,
        "oxigeno": 7.0
    },

    2: {
        "lat": 2.451200,
        "lon": -76.607500,
        "temp": 24.0,
        "turbidez": 35.0,
        "ph": 7.4,
        "oxigeno": 6.5
    }
}


# ==========================================
# VARIACION DE MEDICIONES
# ==========================================

def variar(valor, cambio, minimo, maximo):

    nuevo = valor + random.uniform(
        -cambio, cambio
    )

    return round(
        max(minimo, min(maximo, nuevo)),
        2
    )


# ==========================================
# GENERAR MEDICIONES
# ==========================================

def generar_medicion(id_boya, boya):

    boya["temp"] = variar(
        boya["temp"], 0.4, 15, 35
    )

    boya["turbidez"] = variar(
        boya["turbidez"], 3.0, 0, 100
    )

    boya["ph"] = variar(
        boya["ph"], 0.15, 0, 14
    )

    boya["oxigeno"] = variar(
        boya["oxigeno"], 0.3, 0, 20
    )

    return {
        "ID": id_boya,

        "FechaHora": datetime.now(
            timezone.utc
        ).isoformat(timespec="seconds"),

        "Temp": boya["temp"],
        "Turbidez": boya["turbidez"],
        "Ph": boya["ph"],
        "OxigenoDisuelto": boya["oxigeno"],

        "Latitud": boya["lat"],
        "Longitud": boya["lon"]
    }


# ==========================================
# ENVIAR MEDICIONES
# ==========================================

def enviar_medicion(datos):

    try:

        respuesta = requests.post(
            SERVIDOR,
            json=datos,
            timeout=5
        )

        print("------------------------------")
        print("Boya:", datos["ID"])
        print("Temperatura:", datos["Temp"], "C")
        print("Turbidez:", datos["Turbidez"], "NTU")
        print("pH:", datos["Ph"])
        print(
            "Oxigeno:",
            datos["OxigenoDisuelto"],
            "mg/L"
        )
        print("HTTP:", respuesta.status_code)

        if respuesta.status_code == 201:
            print("Registro almacenado")
        else:
            print("Error:", respuesta.text)

    except requests.RequestException as error:

        print("Error de conexion:", error)


# ==========================================
# BUCLE PRINCIPAL
# ==========================================

print("Simulador AquaTrace iniciado")

while True:

    for id_boya, boya in BOYAS.items():

        medicion = generar_medicion(
            id_boya,
            boya
        )

        enviar_medicion(medicion)

    time.sleep(INTERVALO)
