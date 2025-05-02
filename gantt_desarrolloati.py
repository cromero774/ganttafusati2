import pandas as pd
import plotly.express as px
from dash import Dash, dcc, html, Input, Output
import sys
import requests
import os

def debug_print(message):
    print(f"DEBUG: {message}", file=sys.stderr)
    sys.stderr.flush()

debug_print("Iniciando aplicación...")

# URL del NUEVO Excel (Google Sheets)
sheet_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vT6s9qMzmA_sJRko5EDggumO4sybGVq3n-uOmZOMj8CJDnHo9AWZeZOXZGz7cTg4XoqeiPDIgQP3QER/pub?output=csv"

try:
    response = requests.get(sheet_url, timeout=15)
    response.raise_for_status()
    df = pd.read_csv(sheet_url)
    df.columns = df.columns.str.strip()
    df['RN'] = df['RN'].astype(str).str.replace(r'[\xa0\s]+', ' ', regex=True).str.strip()

    for col in ['Inicio', 'Fin']:
        df[col] = pd.to_datetime(df[col], format='%m/%d/%Y', errors='coerce')
    df = df.dropna(subset=['Inicio', 'Fin'])

    if df.empty:
        sample_dates = pd.date_range(start='2023-01-01', periods=3)
        df = pd.DataFrame({
            'RN': ['Ejemplo 1', 'Ejemplo 2', 'Ejemplo 3'],
            'Estado': ['En desarrollo', 'Entregado', 'Backlog'],
            'Inicio': sample_dates,
            'Fin': sample_dates + pd.Timedelta(days=30)
        })

    df['Inicio_str'] = df['Inicio'].dt.strftime('%Y-%m-%d')
    df['Fin_str'] = df['Fin'].dt.strftime('%Y-%m-%d')
    df['Duracion'] = (df['Fin'] - df['Inicio']).dt.days
    df['Mes'] = df['Fin'].dt.to_period('M').astype(str)

except Exception as e:
    sample_dates = pd.date_range(start='2023-01-01', periods=3)
    df = pd.DataFrame({
        'RN': ['Error - Sin datos', 'Ejemplo 2', 'Ejemplo 3'],
        'Estado': ['Error', 'Error', 'Error'],
        'Inicio': sample_dates,
        'Fin': sample_dates + pd.Timedelta(days=30),
        'Inicio_str': sample_dates.strftime('%Y-%m-%d'),
        'Fin_str': (sample_dates + pd.Timedelta(days=30)).strftime('%Y-%m-%d'),
        'Duracion': [30, 30, 30],
        'Mes': sample_dates.strftime('%Y-%m')
    })

color_estado = {
    'Entregado': '#2ecc71',
    'En desarrollo': '#1abc9c',
    'Backlog': '#f1c40f',
    'Para refinar': '#f5d76e',
    'Escribiendo': '#e67e22',
    'Para escribir': '#e74c3c',
    'En Análisis': '#9b59b6',
    'Cancelado': '#95a5a6',
    'Error': '#e74c3c'
}

app = Dash(__name__)
server = app.server  # Necesario para el despliegue

app.layout = html.Div([
    html.H1("Gantt Postventa", style={'textAlign': 'center', 'margin': '20px 0'}),
    html.Div([
        html.Div([
            html.Label("Mes de entrega:"),
            dcc.Dropdown(
                id='mes-dropdown',
                options=[{'label': 'Todos', 'value': 'Todos'}] +
                        [{'label': mes, 'value': mes} for mes in sorted(df['Mes'].unique())],
                value='Todos',
                clearable=False
            )
        ], style={'width': '48%', 'display': 'inline-block'}),
        html.Div([
            html.Label("Estado:"),
            dcc.Dropdown(
                id='estado-dropdown',
                options=[{'label': 'Todos', 'value': 'Todos'}] +
                        [{'label': estado, 'value': estado} for estado in sorted(df['Estado'].unique())],
                value='Todos',
                clearable=False
            )
        ], style={'width': '48%', 'display': 'inline-block', 'marginLeft': '10px'}),
    ], style={'marginBottom': '20px'}),
    html.Div([
        html.Label("Tema:"),
        dcc.RadioItems(
            id='theme-switch',
            options=[
                {'label': 'Claro', 'value': 'light'},
                {'label': 'Oscuro', 'value': 'dark'}
            ],
            value='light',
            labelStyle={'display': 'inline-block', 'marginRight': '15px'}
        ),
    ], style={'marginBottom': '20px'}),
    html.Div([
        dcc.Graph(
            id='gantt-graph',
            responsive=True,
            style={'height': '100%', 'width': '100%'}
        )
    ], style={'height': '80vh', 'overflowY': 'auto', 'width': '100%'})
])

@app.callback(
    Output('gantt-graph', 'figure'),
    [Input('mes-dropdown', 'value'),
     Input('estado-dropdown', 'value'),
     Input('theme-switch', 'value')]
)
def actualizar_grafico(mes, estado, theme):
    filtered_df = df.copy()
    if mes != 'Todos':
        filtered_df = filtered_df[filtered_df['Mes'] == mes]
    if estado != 'Todos':
        filtered_df = filtered_df[filtered_df['Estado'] == estado]

    template = 'plotly_white' if theme == 'light' else 'plotly_dark'

    fig = px.timeline(
        filtered_df,
        x_start='Inicio',
        x_end='Fin',
        y='RN',
        color='Estado',
        color_discrete_map=color_estado,
        hover_data=['Inicio_str', 'Fin_str', 'Duracion', 'Estado'],
        template=template
    )
    fig.update_yaxes(autorange="reversed")
    fig.update_layout(margin=dict(l=20, r=20, t=40, b=20))
    return fig

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    debug_print("Iniciando servidor...")
    app.run(host='0.0.0.0', port=port, debug=False)

































