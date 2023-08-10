import requests
from xml.dom import minidom
import pandas as pd
import dash
from dash import html, dcc, dash_table, Input, Output, State

app = dash.Dash(
    __name__,
    external_stylesheets=[
        "https://fonts.googleapis.com/css2?family=Roboto&display=swap"
    ],
)
server = app.server

def buscar_localidades(nombre_localidad):
    url = f"https://www.meteored.com.ar/peticionBuscador.php?lang=ar&texto={nombre_localidad}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        return data
    else:
        print(
            f"Error al realizar la solicitud. Código de respuesta: {response.status_code}"
        )
        return localidades_encontradas


def obtener_datos_clima(id_localidad):
    url = f"http://api.meteored.com.ar/index.php?api_lang=ar&localidad={id_localidad}&affiliate_id=sb6pndn36a5p&v=2.0"
    response = requests.get(url)
    if response.status_code == 200:
        return response.text
    else:
        print(
            f"Error al obtener los datos del clima. Código de respuesta: {response.status_code}"
        )
        return None


def obtener_tabla_datos_clima(parsed_xml, emoji_option):
    data = []
    days = parsed_xml.getElementsByTagName("day")
    for day in days:
        date = day.getAttribute("value")
        day_name = day.getAttribute("name")

        hours = day.getElementsByTagName("hour")
        for hour in hours:
            time = hour.getAttribute("value")
            temp = hour.getElementsByTagName("temp")[0].getAttribute("value")
            symbol = hour.getElementsByTagName("symbol")[0].getAttribute("desc")
            wind_speed = hour.getElementsByTagName("wind")[0].getAttribute("value")
            wind_direction = hour.getElementsByTagName("wind")[0].getAttribute("dir")
            wind_gusts = hour.getElementsByTagName("wind-gusts")[0].getAttribute(
                "value"
            )
            rain = hour.getElementsByTagName("rain")[0].getAttribute("value")

            data.append(
                [date, time, temp, symbol, wind_speed, wind_direction, wind_gusts, rain]
            )

    df = pd.DataFrame(
        data,
        columns=[
            "Fecha",
            "Hora",
            "Temperatura (°C)",
            "Descripción del clima",
            "Velocidad del viento (km/h)",
            "Dirección del viento",
            "Ráfagas de viento (km/h)",
            "Lluvia (mm)",
        ],
    )

    df["Ráfagas de viento (km/h)"] = df["Ráfagas de viento (km/h)"].astype(float)
    df["Lluvia (mm)"] = df["Lluvia (mm)"].astype(float)

    if emoji_option == "RTK":
        df["RV"] = df["Ráfagas de viento (km/h)"].apply(asignar_emoji_viento)
        df["LL"] = df["Lluvia (mm)"].apply(asignar_emoji_lluvia)
    elif emoji_option == "DJI":
        df["RV"] = df["Ráfagas de viento (km/h)"].apply(asignar_emoji_viento_dji)
        df["LL"] = df["Lluvia (mm)"].apply(asignar_emoji_lluvia_dji)

    return df


def asignar_emoji_viento(valor):
    if valor < 30:
        return "\U0001F7E2"  # VERDE
    elif 30 <= valor < 50:
        return "\U0001F7E1"  # AMARRILLO
    else:
        return "\U0001F534"  # ROJO


def asignar_emoji_lluvia(valor):
    if valor < 1:
        return "\U0001F7E2"  # VERDE
    else:
        return "\U0001F534"  # ROJO


def asignar_emoji_viento_dji(valor):
    if valor < 10:
        return "\U0001F7E2"  # VERDE
    elif 10 <= valor < 30:
        return "\U0001F7E1"  # AMARRILLO
    else:
        return "\U0001F534"  # ROJO


def asignar_emoji_lluvia_dji(valor):
    if valor < 0.5:
        return "\U0001F7E2"  # VERDE
    else:
        return "\U0001F534"  # ROJO


@app.callback(
    Output("table-container", "children"),
    [
        Input("input-localidad", "value"),
        Input("input-id", "value"),
        Input("radio-conditions", "value"),
    ],
)
def update_table(nombre_localidad, id_localidad, radio_value):
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update

    resultado = buscar_localidades(nombre_localidad)

    if resultado and "localidad" in resultado:
        localidades_encontradas = resultado["localidad"]
        opciones_localidades = [
            {
                "label": f"{localidad['nombre']}, {', '.join(localidad['jerarquia'])} (ID: {localidad['id']})",
                "value": localidad["id"],
            }
            for localidad in localidades_encontradas
        ]

        if len(localidades_encontradas) > 0:
            datos_clima = obtener_datos_clima(id_localidad)

            if datos_clima:
                parsed_xml = minidom.parseString(datos_clima)
                df = obtener_tabla_datos_clima(
                    parsed_xml, radio_value
                )  # Pass radio_value here

                page_size = 8
                table = dash_table.DataTable(
                    data=df.to_dict("records"),
                    columns=[{"name": col, "id": col} for col in df.columns],
                    page_size=page_size,
                    style_table={"height": "300px", "overflowY": "auto"},
                    style_cell={"fontFamily": "Roboto"},
                )

                return table
            else:
                return "No se pudo obtener la información del clima."

    return "No se encontraron resultados para la búsqueda."


app.layout = html.Div(
    [
        html.H1(
            "Meteorólogo de Vuelo",
            style={"marginBottom": "20px", "fontFamily": "Roboto", "fontSize": "25px"},
        ),
        dcc.Input(
            id="input-localidad",
            type="text",
            placeholder="Ingrese el nombre de la localidad",
            style={"marginBottom": "10px", "fontFamily": "Roboto", "width": "400px"},
        ),
        dcc.Dropdown(
            id="input-id",
            options=[],
            placeholder="Seleccione el ID de la localidad",
            style={"marginBottom": "10px", "fontFamily": "Roboto"},
        ),
        html.Div(
            [
                html.Label(
                    "Seleccione el modelo de Drone:",
                    style={"fontFamily": "Roboto"},
                ),
                dcc.RadioItems(
                    id="radio-conditions",
                    options=[
                        {"label": "Matrice 300 RTK", "value": "RTK"},
                        {"label": "DJI M", "value": "DJI"},
                    ],
                    value="RTK",
                    labelStyle={"display": "block"},
                    style={"marginBottom": "10px", "fontFamily": "Roboto"},
                ),
                html.Div(id="table-container"),
            ],
            style={"marginTop": "20px"},
        ),
    ]
)


@app.callback(Output("input-id", "options"), [Input("input-localidad", "value")])
def update_dropdown_options(nombre_localidad):
    resultado = buscar_localidades(nombre_localidad)

    if resultado and "localidad" in resultado:
        localidades_encontradas = resultado["localidad"]
        opciones_localidades = [
            {
                "label": f"{localidad['nombre']}, {', '.join(localidad['jerarquia'])} (ID: {localidad['id']})",
                "value": localidad["id"],
            }
            for localidad in localidades_encontradas
        ]

        return opciones_localidades

    return []


if __name__ == "__main__":
    app.run_server(debug=False)
