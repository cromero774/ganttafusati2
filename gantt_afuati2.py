import pandas as pd
import plotly.express as px
from dash import Dash, dcc, html, Input, Output, callback_context
import requests
from datetime import datetime
import time

# --- Función de debug ---
def debug_print(message):
    pass  # Desactivado para entorno de producción

# --- Función para cargar datos ---
def cargar_datos():
    # URL CORRECTA (TU PLANILLA)
    sheet_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRjsVBlccFE_aAdseRIJb54NdCoR4C5nVRM-zXPIBr7zjsFXzewkJGEgfvaEUAwieBjjL1xPR75klmO/pub?output=csv"

    try:
        timestamp = int(time.time())
        if "?" in sheet_url:
            url_with_cache = f"{sheet_url}&timestamp={timestamp}"
        else:
            url_with_cache = f"{sheet_url}?timestamp={timestamp}"
            
        print(f"Intentando cargar datos desde: {url_with_cache}")
        response = requests.get(url_with_cache, timeout=15)
        response.raise_for_status()
        
        df = pd.read_csv(url_with_cache, encoding='utf-8')
        df.columns = df.columns.str.strip().str.lower()
        df['rn'] = df['rn'].astype(str).str.strip()

        if 'afu asignado' not in df.columns:
            df['afu asignado'] = 'Sin asignar'

        for col in ['inicio', 'fin']:
            try:
                df[col] = pd.to_datetime(df[col], format='%d/%m/%Y', errors='coerce')
            except:
                try:
                    df[col] = pd.to_datetime(df[col], format='%d-%m-%Y', errors='coerce')
                except:
                    try:
                        df[col] = pd.to_datetime(df[col], dayfirst=True, errors='coerce')
                    except Exception:
                        pass

        df = df.dropna(subset=['inicio', 'fin'])
        df['inicio_str'] = df['inicio'].dt.strftime('%d-%m-%Y')
        df['fin_str'] = df['fin'].dt.strftime('%d-%m-%Y')
        df['duracion'] = (df['fin'] - df['inicio']).dt.days
        df['mes'] = df['fin'].dt.to_period('M').astype(str)
        df['rn_trunc'] = df['rn'].str.lower().apply(lambda x: x if len(x) <= 30 else x[:27] + '...')

        print(f"Datos cargados con éxito: {len(df)} filas")
        return df, None

    except Exception as e:
        error_msg = f"Error al cargar datos: {e}"
        sample_dates = pd.date_range(start='2023-01-01', periods=3)
        df = pd.DataFrame({
            'rn': ['Error - Sin datos', 'Ejemplo 2', 'Ejemplo 3'],
            'estado': ['Error', 'Error', 'Error'],
            'afu asignado': ['Sin asignar', 'Sin asignar', 'Sin asignar'],
            'inicio': sample_dates,
            'fin': sample_dates + pd.Timedelta(days=30),
        })
        df['inicio_str'] = df['inicio'].dt.strftime('%d-%m-%Y')
        df['fin_str'] = df['fin'].dt.strftime('%d-%m-%Y')
        df['duracion'] = 30
        df['mes'] = df['fin'].dt.to_period('M').astype(str)
        df['rn_trunc'] = df['rn'].str.lower()
        return df, error_msg

# --- Colores por estado ---
color_estado = {
    'Entregado': '#2ecc71',
    'En desarrollo': '#1abc9c',
    'Backlog': '#f1c40f',
    'Para refinar': '#f5d76e',
    'Escribiendo': '#e67e22',
    'Para escribir': '#e74c3c',
    'En análisis': '#9b59b6',
    'Cancelado': '#95a5a6',
    'Error': '#e74c3c'
}

# --- Cargar datos iniciales ---
print("Iniciando carga de datos...")
df, error_inicial = cargar_datos()
print("Datos iniciales cargados")

# --- App Dash ---
app = Dash(__name__)
server = app.server

# Estilos para componentes personalizados
button_style = {
    'backgroundColor': '#4CAF50',
    'color': 'white',
    'padding': '10px 15px',
    'border': 'none',
    'borderRadius': '4px',
    'cursor': 'pointer',
    'fontSize': '14px'
}

alert_success_style = {
    'padding': '10px 15px',
    'backgroundColor': '#d4edda',
    'color': '#155724',
    'borderRadius': '4px',
    'marginBottom': '15px',
    'display': 'none'
}

alert_error_style = {
    'padding': '10px 15px',
    'backgroundColor': '#f8d7da',
    'color': '#721c24',
    'borderRadius': '4px',
    'marginBottom': '15px',
    'display': 'none'
}

alert_info_style = {
    'padding': '10px 15px',
    'backgroundColor': '#d1ecf1',
    'color': '#0c5460',
    'borderRadius': '4px',
    'marginBottom': '15px',
    'display': 'none'
}

# --- Layout ---
app.layout = html.Div([
    html.H1("Gantt analisis funcional ATI", style={'textAlign': 'center'}),

    html.Div([
        html.Div([
            html.Label("Mes de entrega:"),
            dcc.Dropdown(
                id='mes-dropdown',
                options=[{'label': 'Todos', 'value': 'Todos'}] +
                        [{'label': mes, 'value': mes} for mes in sorted(df['mes'].unique())],
                value='Todos',
                clearable=False
            )
        ], style={'width': '24%', 'display': 'inline-block'}),

        html.Div([
            html.Label("Estado:"),
            dcc.Dropdown(
                id='estado-dropdown',
                options=[{'label': 'Todos', 'value': 'Todos'}] +
                        [{'label': estado, 'value': estado} for estado in sorted(df['estado'].unique())],
                value='Todos',
                clearable=False
            )
        ], style={'width': '24%', 'display': 'inline-block', 'marginLeft': '10px'}),

        html.Div([
            html.Label("AFU asignado:"),
            dcc.Dropdown(
                id='afu-dropdown',
                options=[{'label': 'Todos', 'value': 'Todos'}] +
                        [{'label': afu, 'value': afu} for afu in sorted(df['afu asignado'].unique())],
                value='Todos',
                clearable=False
            )
        ], style={'width': '24%', 'display': 'inline-block', 'marginLeft': '10px'}),

        html.Div([
            html.Label("Intervalo de actualización:"),
            dcc.Dropdown(
                id='refresh-interval',
                options=[
                    {'label': 'Manual', 'value': 0},
                    {'label': '30 segundos', 'value': 30},
                    {'label': '1 minuto', 'value': 60},
                    {'label': '5 minutos', 'value': 300},
                    {'label': '15 minutos', 'value': 900},
                ],
                value=60,
                clearable=False
            )
        ], style={'width': '24%', 'display': 'inline-block', 'marginLeft': '10px'}),
    ], style={'marginBottom': '15px'}),

    html.Div([
        html.Div([
            html.Label("Tema:"),
            dcc.RadioItems(
                id='theme-switch',
                options=[
                    {'label': 'Claro', 'value': 'light'},
                    {'label': 'Oscuro', 'value': 'dark'}
                ],
                value='light',
                labelStyle={'display': 'inline-block', 'marginRight': '10px'}
            )
        ], style={'width': '20%', 'display': 'inline-block'}),

        html.Div([
            html.Button(
                'Actualizar Datos', 
                id='refresh-button', 
                style=button_style
            ),
        ], style={'width': '20%', 'display': 'inline-block', 'verticalAlign': 'bottom'}),

        html.Div([
            html.Span(id='last-update-time', style={'marginLeft': '10px'}),
        ], style={'width': '50%', 'display': 'inline-block', 'verticalAlign': 'middle'}),

        dcc.Interval(
            id='interval-component',
            interval=60*1000,
            n_intervals=0
        ),

        dcc.Store(id='data-store'),
    ], style={'marginBottom': '20px'}),

    html.Div([
        html.Div(id='success-notification', style=alert_success_style),
        html.Div(id='error-notification', style=alert_error_style),
        html.Div(id='info-notification', style=alert_info_style)
    ], id='notification-container', style={'marginBottom': '10px'}),

    html.Div([
        dcc.Graph(id='gantt-graph', style={'height': '80vh'})
    ])
])

# Callbacks
@app.callback(
    Output('interval-component', 'interval'),
    Input('refresh-interval', 'value')
)
def update_interval(value):
    if value == 0:
        return 24 * 60 * 60 * 1000
    return value * 1000

@app.callback(
    Output('success-notification', 'children'),
    Output('success-notification', 'style'),
    Output('error-notification', 'children'),
    Output('error-notification', 'style'),
    Output('info-notification', 'children'),
    Output('info-notification', 'style'),
    Input('interval-component', 'n_intervals'),
    Input('refresh-button', 'n_clicks'),
    Input('data-store', 'data')
)
def update_notifications(n_intervals, n_clicks, data):
    trigger = callback_context.triggered[0]['prop_id'] if callback_context.triggered else None
    success_style = dict(alert_success_style)
    error_style = dict(alert_error_style)
    info_style = dict(alert_info_style)
    success_msg = ""
    error_msg = ""
    info_msg = ""
    if data and 'error' in data and data['error']:
        error_msg = f"Error: {data['error']}"
        error_style['display'] = 'block'
    elif trigger == 'refresh-button.n_clicks' and n_clicks:
        success_msg = "Datos actualizados manualmente"
        success_style['display'] = 'block'
    elif trigger == 'interval-component.n_intervals' and n_intervals > 0:
        info_msg = "Datos actualizados automáticamente"
        info_style['display'] = 'block'
    return success_msg, success_style, error_msg, error_style, info_msg, info_style

@app.callback(
    Output('data-store', 'data'),
    Output('last-update-time', 'children'),
    Output('mes-dropdown', 'options'),
    Output('estado-dropdown', 'options'),
    Output('afu-dropdown', 'options'),
    Input('interval-component', 'n_intervals'),
    Input('refresh-button', 'n_clicks'),
    prevent_initial_call=False
)
def refresh_data(n_intervals, n_clicks):
    df_new, error_msg = cargar_datos()
    current_time = datetime.now().strftime('%d-%m-%Y %H:%M:%S')
    mes_options = [{'label': 'Todos', 'value': 'Todos'}] + [{'label': mes, 'value': mes} for mes in sorted(df_new['mes'].unique())]
    estado_options = [{'label': 'Todos', 'value': 'Todos'}] + [{'label': estado, 'value': estado} for estado in sorted(df_new['estado'].unique())]
    afu_options = [{'label': 'Todos', 'value': 'Todos'}] + [{'label': afu, 'value': afu} for afu in sorted(df_new['afu asignado'].unique())]
    last_update = f"Última actualización: {current_time}"
    store_data = {
        'df': df_new.to_json(date_format='iso', orient='split'),
        'timestamp': current_time,
        'error': error_msg
    }
    return store_data, last_update, mes_options, estado_options, afu_options

@app.callback(
    Output('gantt-graph', 'figure'),
    Input('data-store', 'data'),
    Input('mes-dropdown', 'value'),
    Input('estado-dropdown', 'value'),
    Input('afu-dropdown', 'value'),
    Input('theme-switch', 'value')
)
def actualizar_grafico(stored_data, mes, estado, afu, theme):
    if not stored_data:
        return px.scatter(title="Sin datos disponibles")
    df = pd.read_json(stored_data['df'], orient='split')
    df_filtrado = df.copy()
    if mes != 'Todos':
        df_filtrado = df_filtrado[df_filtrado['mes'] == mes]
    if estado != 'Todos':
        df_filtrado = df_filtrado[df_filtrado['estado'] == estado]
    if afu != 'Todos':
        df_filtrado = df_filtrado[df_filtrado['afu asignado'] == afu]
    if df_filtrado.empty:
        return px.scatter(title="Sin datos con los filtros seleccionados")
    if theme == 'dark':
        plot_bgcolor = '#23272f'
        paper_bgcolor = '#23272f'
        font_color = '#f0f0f0'
        gridcolor = '#444'
        fecha_actual_color = 'rgba(255, 255, 255, 0.15)'
        fecha_text_color = '#e2e8f0'
    else:
        plot_bgcolor = 'white'
        paper_bgcolor = 'white'
        font_color = '#222'
        gridcolor = '#eee'
        fecha_actual_color = 'rgba(66, 153, 225, 0.15)'
        fecha_text_color = '#3182ce'
    df_filtrado = df_filtrado.sort_values('inicio')
    rn_order = df_filtrado['rn_trunc'].unique().tolist()
    df_filtrado['rn_order'] = df_filtrado['rn_trunc'].map({rn: i for i, rn in enumerate(rn_order)})
    df_filtrado = df_filtrado.sort_values('rn_order')
    try:
        fig = px.timeline(
            df_filtrado,
            x_start="inicio",
            x_end="fin",
            y="rn_trunc",
            color="estado",
            custom_data=["rn", "inicio_str", "fin_str", "duracion", "afu asignado"],
            color_discrete_map=color_estado,
            title=f"ATI - {estado if estado != 'Todos' else 'Todos los estados'} | {mes if mes != 'Todos' else 'Todos los meses'} | {afu if afu != 'Todos' else 'Todos los AFU'}"
        )
        fig.update_traces(
            hovertemplate="<b>%{customdata[0]}</b><br>Inicio: %{customdata[1]}<br>Fin: %{customdata[2]}<br>Duración: %{customdata[3]} días<br>AFU: %{customdata[4]}",
            marker=dict(line=dict(width=0.3, color='DarkSlateGrey'))
        )
        fecha_actual = datetime.now()
        fecha_actual_str = fecha_actual.strftime('%d-%m-%Y')
        fig.add_shape(
            type="rect",
            x0=fecha_actual,
            x1=fecha_actual + pd.Timedelta(hours=3),
            y0=-0.5,
            y1=len(rn_order),
            xref="x",
            yref="y",
            fillcolor=fecha_actual_color,
            opacity=0.6,
            layer="below",
            line_width=0
        )
        fig.add_annotation(
            x=fecha_actual,
            y=len(rn_order) + 0.5,
            text=f"Hoy: {fecha_actual_str}",
            showarrow=False,
            yshift=5,
            xshift=0,
            xanchor="center",
            yanchor="bottom",
            font=dict(color=fecha_text_color, size=9),
            opacity=0.9
        )
        fig.update_layout(
            xaxis=dict(title="Fecha", tickformat="%d-%m-%Y", gridcolor=gridcolor),
            yaxis=dict(
                autorange="reversed", 
                title="Requerimiento",
                categoryorder='array',
                categoryarray=rn_order,
                tickfont=dict(size=11),
                title_font=dict(size=13)
            ),
            plot_bgcolor=plot_bgcolor,
            paper_bgcolor=paper_bgcolor,
            font=dict(color=font_color),
            legend=dict(title="Estado", x=1.01, y=1),
            margin=dict(l=20, r=250, t=50, b=50),
            height=max(400, 25 * len(df_filtrado))
        )
        return fig
    except Exception as e:
        return px.scatter(title=f"Error al generar gráfico: {e}")

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)



































































