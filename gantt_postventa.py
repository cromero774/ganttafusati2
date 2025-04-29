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

# Configuración CSV
sheet_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTRvUazuzfWjGl5VWuZJUJslZEf-PpYyHZ_5G2SXwPtu16R71mPSKVQTYjen9UBwQ/pub?gid=865145678&single=true&output=csv"

# Carga y limpieza de datos
try:
    response = requests.get(sheet_url, timeout=15)
    response.raise_for_status()
    
    df = pd.read_csv(sheet_url)
    df.columns = df.columns.str.strip()
    
    # Limpieza avanzada de datos
    df['RN'] = df['RN'].astype(str).str.replace(r'[\xa0\s]+', ' ', regex=True).str.strip()
    
    # Procesamiento de fechas robusto
    date_cols = ['Inicio', 'Fin']
    for col in date_cols:
        df[col] = pd.to_datetime(df[col], format='%m/%d/%Y', errors='coerce')
    
    df = df.dropna(subset=date_cols)
    
    if df.empty:
        debug_print("Usando datos de muestra...")
        sample_dates = pd.date_range(start='2023-01-01', periods=3)
        df = pd.DataFrame({
            'RN': ['Muestra 1', 'Muestra 2', 'Muestra 3'],
            'Estado': ['En desarrollo', 'Entregado', 'Backlog'],
            'Inicio': sample_dates,
            'Fin': sample_dates + pd.Timedelta(days=30)
        })

    # Cálculo de métricas
    df['Inicio_str'] = df['Inicio'].dt.strftime('%Y-%m-%d')
    df['Fin_str'] = df['Fin'].dt.strftime('%Y-%m-%d')
    df['Duracion'] = (df['Fin'] - df['Inicio']).dt.days
    df['Mes'] = df['Fin'].dt.to_period('M').astype(str)
    df['RN_short'] = df['RN'].str.wrap(15).str.split('\n').str[0] + '...'  # Ajustado a 15 caracteres

except Exception as e:
    debug_print(f"Error: {str(e)}")
    sample_dates = pd.date_range(start='2023-01-01', periods=3)
    df = pd.DataFrame({
        'RN': ['Error - Datos', 'Ejemplo 1', 'Ejemplo 2'],
        'Estado': ['Error', 'Muestra', 'Muestra'],
        'Inicio': sample_dates,
        'Fin': sample_dates + pd.Timedelta(days=30),
        'Inicio_str': sample_dates.strftime('%Y-%m-%d'),
        'Fin_str': (sample_dates + pd.Timedelta(days=30)).strftime('%Y-%m-%d'),
        'Duracion': [30, 30, 30],
        'Mes': sample_dates.strftime('%Y-%m'),
        'RN_short': ['Error...', 'Muestra 1...', 'Muestra 2...']
    })

# Paleta de colores personalizada
color_estado = {
    'Entregado': '#2ecc71',       # Verde
    'En desarrollo': '#1abc9c',   # Verde azulado
    'Backlog': '#f1c40f',         # Amarillo
    'Para refinar': '#f5d76e',    # Amarillo claro
    'Escribiendo': '#e67e22',     # Naranja
    'Para escribir': '#e74c3c',   # Rojo
    'En Análisis': '#9b59b6',     # Púrpura (adicional)
    'Cancelado': '#95a5a6',       # Gris (adicional)
    'Error': '#e74c3c'            # Rojo para errores
}

# Configuración de la aplicación
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
    
    dcc.Graph(id='gantt-graph', style={'height': '75vh'})
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
    
    # Ordenar por fecha de inicio (más antiguos arriba)
    df_filtrado = df_filtrado.sort_values('Inicio', ascending=False)  # Invertir para mostrar más antiguos arriba
    
    fig = px.timeline(
        df_filtrado,
        x_start="Inicio",
        x_end="Fin",
        y="RN",
        color="Estado",
        color_discrete_map=color_estado,
        custom_data=["RN", "Inicio_str", "Fin_str", "Duracion"],
        labels={'Estado': 'Estado'},
        title=f"Postventa - {estado if estado != 'Todos' else 'Todos los estados'} | {mes if mes != 'Todos' else 'Todos los meses'}"
    )
    
    # Personalización del texto en barras
    fig.update_traces(
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            "Inicio: %{customdata[1]}<br>"
            "Fin: %{customdata[2]}<br>"
            "Duración: %{customdata[3]} días"
        ),
        textposition='inside',
        insidetextanchor='start',
        text=df_filtrado['RN_short'],
        textfont=dict(size=11, color='black'),
        marker=dict(line=dict(width=0.5, color='DarkSlateGrey'))
    )
    
    fig.update_layout(
        xaxis=dict(title="Fecha", tickformat="%Y-%m-%d"),
        yaxis=dict(
            title="",
            autorange=False,  # Desactivar autorange para mantener el orden
            categoryorder='array',  # Orden personalizado
            categoryarray=df_filtrado['RN'][::-1],  # Invertir el orden para mostrar más antiguos arriba
            automargin=True
        ),
        legend=dict(title="Estado", orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        plot_bgcolor='white',
        paper_bgcolor='white',
        margin=dict(l=20, r=20, t=80, b=20),
        bargap=0.3,
        height=600,
        uniformtext=dict(minsize=9, mode='show')
    )
    
    return fig

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    debug_print("Iniciando servidor...")
    app.run(host='0.0.0.0', port=port, debug=False)








