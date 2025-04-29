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

sheet_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTRvUazuzfWjGl5VWuZJUJslZEf-PpYyHZ_5G2SXwPtu16R71mPSKVQTYjen9UBwQ/pub?gid=865145678&single=true&output=csv"

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
server = app.server

app.layout = html.Div([
    html.H1("Gantt Postventa", style={'textAlign': 'center', 'margin': '20px 0'}),
    html.Div([
        html.Div([
            html.Label("Mes Finalización:"),
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
        ], style={'width': '48%', 'display': 'inline-block', 'marginLeft': '10px'})
    ], style={'marginBottom': '20px'}),

    html.Div([
        dcc.Graph(id='gantt-graph')
    ], style={'height': '80vh', 'overflowY': 'auto'})
])

@app.callback(
    Output('gantt-graph', 'figure'),
    [Input('mes-dropdown', 'value'),
     Input('estado-dropdown', 'value')]
)
def actualizar_grafico(mes, estado):
    df_filtrado = df.copy()
    if mes != 'Todos':
        df_filtrado = df_filtrado[df_filtrado['Mes'] == mes]
    if estado != 'Todos':
        df_filtrado = df_filtrado[df_filtrado['Estado'] == estado]
    if df_filtrado.empty:
        return px.scatter(title="Sin datos con los filtros seleccionados")

    # Ordenar por fecha de inicio (más viejos arriba)
    df_filtrado = df_filtrado.sort_values('Inicio', ascending=True)
    df_filtrado['RN_display'] = df_filtrado['RN']  # Usamos RN directamente como y

    fig = px.timeline(
        df_filtrado,
        x_start="Inicio",
        x_end="Fin",
        y="RN_display",  # Mostramos nombre del RN directamente
        color="Estado",
        color_discrete_map=color_estado,
        custom_data=["RN_display", "Inicio_str", "Fin_str", "Duracion"],
        labels={'Estado': 'Estado'},
        title=f"Postventa - {estado if estado != 'Todos' else 'Todos los estados'} | {mes if mes != 'Todos' else 'Todos los meses'}"
    )

    fig.update_traces(
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            "Inicio: %{customdata[1]}<br>"
            "Fin: %{customdata[2]}<br>"
            "Duración: %{customdata[3]} días"
        ),
        text=df_filtrado['RN_display'],
        textposition='inside',
        insidetextanchor='middle',
        textfont=dict(size=12, color='black'),
        marker=dict(line=dict(width=0.3, color='DarkSlateGrey'))
    )

    rows_count = len(df_filtrado)
    row_height = 25
    min_height = 400
    max_height = 1200
    dynamic_height = row_height * rows_count
    graph_height = max(min_height, min(dynamic_height, max_height))

    fig.update_yaxes(
        visible=False,
        showticklabels=False,
        showgrid=False,
        zeroline=False,
        autorange=False,
        categoryorder='array',
        categoryarray=df_filtrado['RN_display'][::-1]
    )

    fig.update_layout(
        height=graph_height,
        xaxis=dict(title="Fecha", tickformat="%Y-%m-%d"),
        legend=dict(
            title="Estado",
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.01
        ),
        plot_bgcolor='white',
        paper_bgcolor='white',
        margin=dict(l=20, r=200, t=80, b=20),
        bargap=0.15,
        uniformtext=dict(minsize=10, mode='show')
    )

    if rows_count > 0:
        fig.update_layout(
            yaxis_range=[-0.5, rows_count - 0.5]
        )

    return fig

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    debug_print("Iniciando servidor...")
    app.run(host='0.0.0.0', port=port, debug=False)


















