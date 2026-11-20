# AquaTrace Web – Plataforma de Monitoreo de Calidad del Agua

Aplicación web desarrollada para la recepción, almacenamiento, procesamiento y visualización de mediciones ambientales obtenidas mediante el sistema de boyas sensoriales AquaTrace.

La plataforma permite monitorear variables fisicoquímicas del agua en tiempo real, consultar registros históricos, visualizar la ubicación geográfica de las boyas y establecer umbrales de referencia para identificar mediciones fuera de los rangos definidos por el experto.

## 1. Descripción del proyecto

AquaTrace Web constituye la interfaz de supervisión del sistema AquaTrace. Su función principal es recibir las mediciones transmitidas por el nodo Edge (Raspberry Pi), almacenarlas en una base de datos y presentarlas mediante un dashboard interactivo.

La aplicación está desarrollada con Python y Flask para el backend, SQLite para el almacenamiento de información y tecnologías web para la interfaz gráfica.

## 2. Objetivos

- Recibir mediciones ambientales provenientes de las boyas sensoriales.
- Almacenar los registros en una base de datos local.
- Visualizar las variables fisicoquímicas mediante gráficas dinámicas.
- Consultar el historial de mediciones.
- Visualizar geográficamente las boyas mediante coordenadas GPS.
- Gestionar valores faltantes sin perder el resto de la información.
- Configurar umbrales mínimos y máximos para identificar mediciones fuera de rango.
- Generar alertas visuales para facilitar la supervisión de la calidad del agua.

## 3. Arquitectura del sistema

La plataforma forma parte de una arquitectura distribuida en la que la información se origina en las boyas sensoriales y posteriormente es procesada por un nodo Edge.

```text
BOYA SENSORIAL
      |
      | Mediciones ambientales
      v
NODO EDGE - RASPBERRY PI
      |
      | HTTP / JSON
      v
SERVIDOR WEB - FLASK
      |
      +------------------+
      |                  |
      v                  v
BASE DE DATOS        API REST
   SQLite                |
                         v
                  INTERFAZ WEB
                         |
          +--------------+--------------+
          |              |              |
          v              v              v
       GRÁFICAS       HISTORIAL        MAPA
                         |
                         v
                  ALERTAS Y UMBRALES
```

## 4. Tecnologías utilizadas

| Tecnología | Aplicación |
|---|---|
| Python | Lenguaje principal del backend |
| Flask | Framework para el servidor web y API |
| SQLite | Base de datos relacional |
| HTML5 | Estructura de la interfaz |
| CSS3 | Diseño y presentación visual |
| JavaScript | Lógica e interacción de la página |
| Chart.js | Visualización de gráficas |
| Leaflet | Visualización geográfica de las boyas |
| ngrok | Exposición experimental del servidor a Internet |

## 5. Estructura del proyecto

```text
AquaTrace_Web/
│
├── templates/
│   └── index.html
│
├── aquatrace.db
│
├── servidor.py
│
├── simulador.py
│
└── README.md
```

### Descripción de los archivos

| Archivo | Función |
|---|---|
| `servidor.py` | Gestiona el servidor Flask, las rutas API, la validación de datos y las operaciones con SQLite. |
| `index.html` | Contiene la interfaz gráfica, las gráficas, el mapa, el historial y los controles de configuración. |
| `aquatrace.db` | Almacena las mediciones y la configuración persistente del sistema. |
| `simulador.py` | Permite generar y transmitir mediciones simuladas para realizar pruebas. |

## 6. Variables monitoreadas

La plataforma permite visualizar las siguientes variables:

| Variable | Unidad |
|---|---|
| pH | Unidades de pH |
| Temperatura | °C |
| Oxígeno disuelto | mg/L |
| Turbidez | NTU |
| Latitud | Grados decimales |
| Longitud | Grados decimales |
| Fecha y hora | ISO 8601 |

Cada registro se identifica mediante un ID de boya.

## 7. Funcionalidades de la plataforma

### 7.1. Dashboard principal

Presenta una vista general del sistema y permite consultar el comportamiento de las mediciones recibidas.

Incluye indicadores y representaciones gráficas para facilitar la interpretación de las variables ambientales.

### 7.2. Visualización de mediciones

Utiliza Chart.js para representar el comportamiento temporal de las variables monitoreadas.

Las gráficas permiten observar tendencias y variaciones de las mediciones recibidas.

### 7.3. Mapa de boyas

Implementado mediante Leaflet.

Permite visualizar la ubicación geográfica de las boyas utilizando las coordenadas proporcionadas por el GPS.

Cuando una boya no dispone de coordenadas válidas en su última medición, su ubicación no se representa en el mapa.

### 7.4. Historial de mediciones

Permite consultar los registros almacenados en SQLite.

Incluye información de fecha y hora, identificación de boya y variables ambientales.

La plataforma admite valores faltantes (`NULL`), representándolos explícitamente en el historial sin convertirlos artificialmente en cero.

### 7.5. Filtros de consulta

Permite filtrar los registros mediante:

- Identificación de la boya.
- Fecha inicial.
- Fecha final.
- Límite de resultados.

### 7.6. Gestión de valores nulos

El sistema permite almacenar registros aunque una o varias variables no tengan una lectura disponible.

Los valores nulos se gestionan de la siguiente manera:

- No se convierten en cero.
- No se generan valores artificiales.
- Las gráficas interrumpen la línea cuando reciben un dato nulo.
- El historial representa los valores faltantes como `NULL`.
- Las boyas sin coordenadas válidas no aparecen en el mapa.

### 7.7. Configuración de umbrales y alertas

La plataforma incorpora una funcionalidad de configuración de límites para las variables ambientales.

El experto puede establecer valores mínimos y máximos para:

- pH.
- Temperatura.
- Oxígeno disuelto.
- Turbidez.

Cuando una medición supera los límites establecidos, la plataforma permite identificarla mediante alertas visuales de alto contraste.

Los registros que se encuentran fuera de los rangos configurados también se destacan en el historial mediante indicadores visuales rojos.

Los umbrales se almacenan en SQLite para conservar su configuración entre sesiones.

## 8. API del servidor

El backend utiliza Flask para gestionar las solicitudes HTTP.

### Endpoints principales

| Método | Endpoint | Descripción |
|---|---|---|
| POST | `/api/mediciones` | Recibe y almacena una medición. |
| GET | `/api/mediciones` | Consulta las últimas 100 mediciones. |
| GET | `/api/boyas` | Consulta las identificaciones de las boyas registradas. |
| GET | `/api/mediciones/filtrar` | Consulta mediciones mediante filtros. |
| GET | `/` | Carga la interfaz web. |

### Ejemplo de datos recibidos

```json
{
    "ID": 1,
    "FechaHora": "2026-11-19T10:30:00-05:00",
    "Temp": 24.50,
    "Turbidez": 10.50,
    "Ph": 7.18,
    "OxigenoDisuelto": 8.98,
    "Latitud": 2.446308,
    "Longitud": -76.598130
}
```

Los campos de medición pueden contener valores numéricos o `null`.

Ejemplo de una medición con datos faltantes:

```json
{
    "ID": 1,
    "FechaHora": null,
    "Temp": null,
    "Turbidez": 10.50,
    "Ph": 7.18,
    "OxigenoDisuelto": 8.98,
    "Latitud": null,
    "Longitud": null
}
```

El identificador de la boya continúa siendo obligatorio.

## 9. Instalación y ejecución

### Requisitos

- Python 3.
- pip.
- Visual Studio Code (recomendado).
- Conexión a Internet para instalar las dependencias.

### 9.1. Clonar el repositorio

```bash
git clone URL_DEL_REPOSITORIO
```

Ingresar a la carpeta:

```bash
cd AquaTrace_Web
```

### 9.2. Instalar dependencias

```bash
pip install flask
```

### 9.3. Ejecutar el servidor

```bash
python servidor.py
```

El servidor se ejecuta en el puerto 5000.

### 9.4. Acceder a la plataforma

Abrir el navegador y acceder a:

```text
http://localhost:5000
```

Para permitir conexiones desde otros dispositivos de la red local, Flask utiliza:

```python
app.run(host="0.0.0.0", port=5000, debug=False)
```

## 10. Acceso remoto mediante ngrok

Para realizar pruebas de acceso remoto se puede utilizar ngrok.

Con el servidor Flask ejecutándose, abrir una segunda terminal y ejecutar:

```bash
ngrok http 5000
```

Ngrok genera una dirección HTTPS pública que permite acceder al servidor desde Internet.

Esta modalidad se utiliza para pruebas experimentales y no representa por sí sola una implementación de producción.

## 11. Actualización de información

La interfaz realiza consultas periódicas al servidor para actualizar la información presentada.

El dashboard utiliza un intervalo de actualización de aproximadamente 3 segundos, permitiendo visualizar las nuevas mediciones sin necesidad de recargar manualmente la página.

## 12. Consideraciones técnicas

- La base de datos SQLite se encuentra en el directorio principal del proyecto.
- Los registros históricos se conservan mientras no se ejecute una operación de limpieza.
- Los campos nulos se almacenan como valores SQL `NULL`.
- La fecha y hora se recibe en formato ISO 8601.
- Las coordenadas GPS se validan antes de su almacenamiento.
- Los umbrales configurados deben corresponder a criterios técnicos definidos por el experto.
- Las credenciales y configuraciones sensibles no deben publicarse en el repositorio.
- Para despliegues permanentes se recomienda implementar mecanismos adicionales de seguridad, autenticación y protección de la API.

## 13. Desarrollo futuro

Entre las posibles mejoras del sistema se contemplan:

- Integración con comunicación LoRa.
- Incorporación de nuevas boyas sensoriales.
- Ampliación de las herramientas de análisis histórico.
- Exportación de mediciones a formatos CSV y Excel.
- Implementación de mecanismos de autenticación y gestión de usuarios.
- Optimización del almacenamiento y consulta de grandes volúmenes de información.

---

**AquaTrace Web – Plataforma de monitoreo de calidad del agua**

Proyecto de desarrollo tecnológico orientado a la adquisición, almacenamiento, visualización y supervisión de variables ambientales mediante un sistema distribuido de boyas sensoriales y nodos Edge.
