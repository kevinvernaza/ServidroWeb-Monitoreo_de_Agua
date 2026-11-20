# ==========================================
# AQUATRACE - SERVIDOR WEB
# Ejecutar: python servidor.py
# python -c "import sqlite3; c=sqlite3.connect('aquatrace.db'); c.execute('DELETE FROM mediciones'); c.execute('DELETE FROM sqlite_sequence WHERE name=?', ('mediciones',)); c.commit(); c.close(); print('Base de datos limpiada correctamente')"
# ngrok http 5000    
# ==========================================

from datetime import datetime
from pathlib import Path
import math
import sqlite3

from flask import Flask, jsonify, render_template, request

app = Flask(__name__)
DB_PATH = Path(__file__).with_name("aquatrace.db")

CAMPOS = (
    "ID", "FechaHora", "Temp", "Turbidez", "Ph",
    "OxigenoDisuelto", "Latitud", "Longitud"
)

CAMPOS_NUMERICOS = (
    "Temp", "Turbidez", "Ph", "OxigenoDisuelto", "Latitud", "Longitud"
)

MAX_FILTRADOS = 5000

# Métricas configurables por el experto. Las claves coinciden con la API.
METRICAS_UMBRALES = {
    "Ph": "pH",
    "Temp": "Temperatura",
    "Turbidez": "Turbidez",
    "OxigenoDisuelto": "Oxígeno disuelto",
}


def conectar_db():
    conexion = sqlite3.connect(DB_PATH)
    conexion.row_factory = sqlite3.Row
    return conexion


def crear_tabla_mediciones(conexion):
    """Crea la tabla permitiendo NULL en todos los campos excepto ID."""
    conexion.execute("""
        CREATE TABLE IF NOT EXISTS mediciones (
            registro_id INTEGER PRIMARY KEY AUTOINCREMENT,
            ID INTEGER NOT NULL,
            FechaHora TEXT,
            Temp REAL,
            Turbidez REAL,
            Ph REAL,
            OxigenoDisuelto REAL,
            Latitud REAL,
            Longitud REAL
        )
    """)


def inicializar_db():
    """
    Crea la tabla si no existe. Si la base de datos ya tenía FechaHora
    u otros campos con NOT NULL, reconstruye la tabla conservando registros.
    """
    with conectar_db() as conexion:
        existe = conexion.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type = 'table' AND name = 'mediciones'
        """).fetchone()

        if not existe:
            crear_tabla_mediciones(conexion)
        else:
            columnas = {
                fila["name"]: fila
                for fila in conexion.execute(
                    "PRAGMA table_info(mediciones)"
                ).fetchall()
            }

            campos_que_deben_aceptar_null = (
                "FechaHora", "Temp", "Turbidez", "Ph",
                "OxigenoDisuelto", "Latitud", "Longitud"
            )

            requiere_migracion = any(
                campo not in columnas or columnas[campo]["notnull"] == 1
                for campo in campos_que_deben_aceptar_null
            )

            if requiere_migracion:
                nombre_temporal = "mediciones_anterior_migracion"

                conexion.execute(
                    f"DROP TABLE IF EXISTS {nombre_temporal}"
                )
                conexion.execute(
                    f"ALTER TABLE mediciones RENAME TO {nombre_temporal}"
                )
                crear_tabla_mediciones(conexion)

                columnas_anteriores = {
                    fila["name"]
                    for fila in conexion.execute(
                        f"PRAGMA table_info({nombre_temporal})"
                    ).fetchall()
                }

                campos_copiar = [
                    campo for campo in ("registro_id",) + CAMPOS
                    if campo in columnas_anteriores
                ]

                lista_campos = ", ".join(campos_copiar)
                conexion.execute(f"""
                    INSERT INTO mediciones ({lista_campos})
                    SELECT {lista_campos}
                    FROM {nombre_temporal}
                """)

                conexion.execute(f"DROP TABLE {nombre_temporal}")
                print("Migración completada: ahora los campos de medición aceptan NULL.")

        conexion.execute("""
            CREATE TABLE IF NOT EXISTS umbrales (
                metrica TEXT PRIMARY KEY,
                minimo REAL NOT NULL,
                maximo REAL NOT NULL,
                actualizado TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

    print("Base de datos inicializada correctamente")


def convertir_numero_opcional(valor, campo):
    """Convierte un número o conserva None; rechaza valores no numéricos."""
    if valor is None:
        return None

    if isinstance(valor, bool):
        raise ValueError(f"Valor invalido en {campo}")

    try:
        numero = float(valor)
    except (ValueError, TypeError, OverflowError):
        raise ValueError(f"Valor invalido en {campo}")

    if not math.isfinite(numero):
        raise ValueError(f"Valor invalido en {campo}")

    return numero


def convertir_fecha_opcional(valor):
    """Conserva NULL o valida una fecha/hora ISO 8601."""
    if valor is None:
        return None

    if not isinstance(valor, str) or not valor.strip():
        raise ValueError("FechaHora debe ser ISO 8601 o null")

    try:
        datetime.fromisoformat(valor.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("FechaHora debe ser ISO 8601 o null")

    return valor


@app.route("/api/mediciones", methods=["POST"])
def recibir_medicion():
    datos = request.get_json(silent=True)

    if not isinstance(datos, dict):
        return jsonify({"error": "JSON invalido"}), 400

    if not all(campo in datos for campo in CAMPOS):
        return jsonify({"error": "Faltan campos"}), 400

    try:
        # ID identifica la boya y continúa siendo obligatorio.
        if datos["ID"] is None or isinstance(datos["ID"], bool):
            raise ValueError("ID de boya invalido")

        valores = {
            "ID": int(datos["ID"]),
            "FechaHora": convertir_fecha_opcional(datos["FechaHora"]),
        }

        if valores["ID"] < 1:
            raise ValueError("ID de boya invalido")

        # Cada variable puede llegar como número o como JSON null.
        for campo in CAMPOS_NUMERICOS:
            valores[campo] = convertir_numero_opcional(datos[campo], campo)

        # Validar rangos solamente cuando las coordenadas existen.
        if valores["Latitud"] is not None:
            if not -90 <= valores["Latitud"] <= 90:
                raise ValueError("Latitud invalida")

        if valores["Longitud"] is not None:
            if not -180 <= valores["Longitud"] <= 180:
                raise ValueError("Longitud invalida")

    except (ValueError, TypeError, OverflowError) as error:
        return jsonify({"error": str(error)}), 400

    with conectar_db() as conexion:
        cursor = conexion.execute("""
            INSERT INTO mediciones (
                ID, FechaHora, Temp, Turbidez, Ph,
                OxigenoDisuelto, Latitud, Longitud
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, tuple(valores[campo] for campo in CAMPOS))

        registro_id = cursor.lastrowid

    return jsonify({
        "mensaje": "Medicion almacenada",
        "registro_id": registro_id
    }), 201


@app.route("/api/mediciones", methods=["GET"])
def consultar_mediciones():
    # Contrato original: los 100 registros más recientes.
    with conectar_db() as conexion:
        registros = conexion.execute("""
            SELECT ID, FechaHora, Temp, Turbidez, Ph,
                   OxigenoDisuelto, Latitud, Longitud
            FROM mediciones
            ORDER BY registro_id DESC
            LIMIT 100
        """).fetchall()

    return jsonify([dict(registro) for registro in registros])


@app.route("/api/boyas", methods=["GET"])
def consultar_boyas():
    # Incluye boyas con registros antiguos, no solo recientes.
    with conectar_db() as conexion:
        filas = conexion.execute("""
            SELECT DISTINCT ID
            FROM mediciones
            ORDER BY ID
        """).fetchall()

    return jsonify([fila["ID"] for fila in filas])


def parsear_instante_utc(valor, nombre):
    try:
        instante = datetime.fromisoformat(valor.replace("Z", "+00:00"))
        if instante.tzinfo is None:
            raise ValueError("Se requiere zona horaria UTC")
        return instante.isoformat()
    except (TypeError, AttributeError, ValueError):
        raise ValueError(
            f"{nombre} debe ser fecha/hora ISO 8601 con zona horaria"
        )


@app.route("/api/mediciones/filtrar", methods=["GET"])
def filtrar_mediciones():
    boya = request.args.get("boya", "").strip()
    desde = request.args.get("desde", "").strip()
    hasta = request.args.get("hasta", "").strip()
    limite_solicitado = request.args.get("limite", "5000")

    try:
        limite = int(limite_solicitado)
        if not 1 <= limite <= MAX_FILTRADOS:
            raise ValueError(
                f"El limite debe estar entre 1 y {MAX_FILTRADOS}"
            )

        condiciones = []
        parametros = []

        if boya:
            id_boya = int(boya)
            if id_boya < 1:
                raise ValueError("ID de boya invalido")
            condiciones.append("ID = ?")
            parametros.append(id_boya)

        # SQLite excluye automáticamente FechaHora NULL de estos filtros.
        if desde:
            condiciones.append("datetime(FechaHora) >= datetime(?)")
            parametros.append(parsear_instante_utc(desde, "desde"))

        if hasta:
            condiciones.append("datetime(FechaHora) < datetime(?)")
            parametros.append(parsear_instante_utc(hasta, "hasta"))

        if desde and hasta:
            fecha_desde = datetime.fromisoformat(
                desde.replace("Z", "+00:00")
            )
            fecha_hasta = datetime.fromisoformat(
                hasta.replace("Z", "+00:00")
            )
            if fecha_desde >= fecha_hasta:
                raise ValueError(
                    "La fecha inicial debe ser anterior a la final"
                )

    except (ValueError, TypeError) as error:
        return jsonify({"error": str(error)}), 400

    donde = " WHERE " + " AND ".join(condiciones) if condiciones else ""

    with conectar_db() as conexion:
        total = conexion.execute(
            "SELECT COUNT(*) AS total FROM mediciones" + donde,
            parametros
        ).fetchone()["total"]

        filas = conexion.execute("""
            SELECT ID, FechaHora, Temp, Turbidez, Ph,
                   OxigenoDisuelto, Latitud, Longitud
            FROM mediciones
        """ + donde + " ORDER BY registro_id DESC LIMIT ?",
            [*parametros, limite]
        ).fetchall()

    return jsonify({
        "registros": [dict(fila) for fila in filas],
        "total": total,
        "limite": limite,
        "truncado": total > limite
    })


@app.route("/api/umbrales", methods=["GET"])
def consultar_umbrales():
    """Devuelve los límites configurados para cada métrica."""
    with conectar_db() as conexion:
        filas = conexion.execute(
            "SELECT metrica, minimo, maximo FROM umbrales"
        ).fetchall()

    configurados = {
        fila["metrica"]: {"minimo": fila["minimo"], "maximo": fila["maximo"]}
        for fila in filas
    }
    return jsonify({
        metrica: configurados.get(metrica)
        for metrica in METRICAS_UMBRALES
    })


@app.route("/api/umbrales", methods=["POST"])
def guardar_umbrales():
    """Valida y guarda los cuatro pares de límites en SQLite."""
    datos = request.get_json(silent=True)
    if not isinstance(datos, dict):
        return jsonify({"error": "JSON invalido"}), 400

    valores = {}
    try:
        for metrica in METRICAS_UMBRALES:
            par = datos.get(metrica)
            if not isinstance(par, dict) or "minimo" not in par or "maximo" not in par:
                raise ValueError(f"Faltan los límites de {METRICAS_UMBRALES[metrica]}")

            minimo = float(par["minimo"])
            maximo = float(par["maximo"])
            if not math.isfinite(minimo) or not math.isfinite(maximo):
                raise ValueError(f"Límites inválidos para {METRICAS_UMBRALES[metrica]}")
            if minimo >= maximo:
                raise ValueError(f"El mínimo debe ser menor que el máximo para {METRICAS_UMBRALES[metrica]}")
            valores[metrica] = (minimo, maximo)

    except (ValueError, TypeError, OverflowError) as error:
        return jsonify({"error": str(error)}), 400

    with conectar_db() as conexion:
        for metrica, (minimo, maximo) in valores.items():
            conexion.execute("""
                INSERT INTO umbrales (metrica, minimo, maximo, actualizado)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(metrica) DO UPDATE SET
                    minimo = excluded.minimo,
                    maximo = excluded.maximo,
                    actualizado = CURRENT_TIMESTAMP
            """, (metrica, minimo, maximo))

    return jsonify({"mensaje": "Umbrales guardados correctamente"}), 200


@app.route("/")
def inicio():
    return render_template("index.html")


if __name__ == "__main__":
    inicializar_db()
    app.run(host="0.0.0.0", port=5000, debug=False)
