# ==========================================
# AQUATRACE - SERVIDOR WEB
# Flask + SQLite3 + consultas filtradas
#python servidor.py
# ==========================================

from datetime import datetime
from pathlib import Path
import math
import sqlite3

from flask import Flask, jsonify, render_template, request

app = Flask(__name__)
DB_PATH = Path(__file__).with_name('aquatrace.db')
CAMPOS = (
    'ID', 'FechaHora', 'Temp', 'Turbidez', 'Ph',
    'OxigenoDisuelto', 'Latitud', 'Longitud'
)
MAX_FILTRADOS = 5000


def conectar_db():
    conexion = sqlite3.connect(DB_PATH)
    conexion.row_factory = sqlite3.Row
    return conexion


def inicializar_db():
    with conectar_db() as conexion:
        conexion.execute('''
            CREATE TABLE IF NOT EXISTS mediciones (
                registro_id INTEGER PRIMARY KEY AUTOINCREMENT,
                ID INTEGER NOT NULL,
                FechaHora TEXT NOT NULL,
                Temp REAL,
                Turbidez REAL,
                Ph REAL,
                OxigenoDisuelto REAL,
                Latitud REAL,
                Longitud REAL
            )
        ''')
    print('Base de datos inicializada correctamente')


@app.route('/api/mediciones', methods=['POST'])
def recibir_medicion():
    datos = request.get_json(silent=True)
    if not isinstance(datos, dict):
        return jsonify({'error': 'JSON invalido'}), 400
    if not all(campo in datos for campo in CAMPOS):
        return jsonify({'error': 'Faltan campos'}), 400
    try:
        valores = {
            'ID': int(datos['ID']),
            'FechaHora': str(datos['FechaHora']),
            'Temp': float(datos['Temp']),
            'Turbidez': float(datos['Turbidez']),
            'Ph': float(datos['Ph']),
            'OxigenoDisuelto': float(datos['OxigenoDisuelto']),
            'Latitud': float(datos['Latitud']),
            'Longitud': float(datos['Longitud'])
        }
        if valores['ID'] < 1:
            raise ValueError('ID de boya invalido')
        datetime.fromisoformat(valores['FechaHora'].replace('Z', '+00:00'))
        for campo in CAMPOS:
            if campo not in ('ID', 'FechaHora') and not math.isfinite(valores[campo]):
                raise ValueError(f'Valor invalido en {campo}')
        if not -90 <= valores['Latitud'] <= 90:
            raise ValueError('Latitud invalida')
        if not -180 <= valores['Longitud'] <= 180:
            raise ValueError('Longitud invalida')
    except (ValueError, TypeError, OverflowError) as error:
        return jsonify({'error': str(error)}), 400

    with conectar_db() as conexion:
        cursor = conexion.execute('''
            INSERT INTO mediciones (
                ID, FechaHora, Temp, Turbidez, Ph,
                OxigenoDisuelto, Latitud, Longitud
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', tuple(valores[campo] for campo in CAMPOS))
        registro_id = cursor.lastrowid
    return jsonify({'mensaje': 'Medicion almacenada', 'registro_id': registro_id}), 201


@app.route('/api/mediciones', methods=['GET'])
def consultar_mediciones():
    # Contrato original: los 100 registros mas recientes.
    with conectar_db() as conexion:
        registros = conexion.execute('''
            SELECT ID, FechaHora, Temp, Turbidez, Ph,
                   OxigenoDisuelto, Latitud, Longitud
            FROM mediciones
            ORDER BY registro_id DESC
            LIMIT 100
        ''').fetchall()
    return jsonify([dict(registro) for registro in registros])


@app.route('/api/boyas', methods=['GET'])
def consultar_boyas():
    # Incluye boyas con registros antiguos, no solo recientes.
    with conectar_db() as conexion:
        filas = conexion.execute('SELECT DISTINCT ID FROM mediciones ORDER BY ID').fetchall()
    return jsonify([fila['ID'] for fila in filas])


def parsear_instante_utc(valor, nombre):
    try:
        instante = datetime.fromisoformat(valor.replace('Z', '+00:00'))
        if instante.tzinfo is None:
            raise ValueError('Se requiere zona horaria UTC')
        return instante.isoformat()
    except (TypeError, AttributeError, ValueError):
        raise ValueError(f'{nombre} debe ser fecha/hora ISO 8601 con zona horaria')


@app.route('/api/mediciones/filtrar', methods=['GET'])
def filtrar_mediciones():
    boya = request.args.get('boya', '').strip()
    desde = request.args.get('desde', '').strip()
    hasta = request.args.get('hasta', '').strip()
    limite_solicitado = request.args.get('limite', '5000')

    try:
        limite = int(limite_solicitado)
        if not 1 <= limite <= MAX_FILTRADOS:
            raise ValueError(f'El limite debe estar entre 1 y {MAX_FILTRADOS}')

        condiciones = []
        parametros = []

        if boya:
            id_boya = int(boya)
            if id_boya < 1:
                raise ValueError('ID de boya invalido')
            condiciones.append('ID = ?')
            parametros.append(id_boya)

        if desde:
            condiciones.append('datetime(FechaHora) >= datetime(?)')
            parametros.append(parsear_instante_utc(desde, 'desde'))

        if hasta:
            condiciones.append('datetime(FechaHora) < datetime(?)')
            parametros.append(parsear_instante_utc(hasta, 'hasta'))

        if desde and hasta:
            if datetime.fromisoformat(desde.replace('Z', '+00:00')) >= datetime.fromisoformat(hasta.replace('Z', '+00:00')):
                raise ValueError('La fecha inicial debe ser anterior a la final')

    except (ValueError, TypeError) as error:
        return jsonify({'error': str(error)}), 400

    donde = ' WHERE ' + ' AND '.join(condiciones) if condiciones else ''
    with conectar_db() as conexion:
        total = conexion.execute(
            'SELECT COUNT(*) AS total FROM mediciones' + donde,
            parametros
        ).fetchone()['total']
        filas = conexion.execute('''
            SELECT ID, FechaHora, Temp, Turbidez, Ph,
                   OxigenoDisuelto, Latitud, Longitud
            FROM mediciones
        ''' + donde + ' ORDER BY registro_id DESC LIMIT ?',
            [*parametros, limite]
        ).fetchall()

    return jsonify({
        'registros': [dict(fila) for fila in filas],
        'total': total,
        'limite': limite,
        'truncado': total > limite
    })


@app.route('/')
def inicio():
    return render_template('index.html')


if __name__ == '__main__':
    inicializar_db()
    app.run(host='0.0.0.0', port=5000, debug=False)
