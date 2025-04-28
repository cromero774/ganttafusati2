import pandas as pd
import plotly.express as px
from dash import Dash, dcc, html, Input, Output

# URL pública para exportar Google Sheets como CSV (primera hoja)
sheet_url = "https://docs.google.com/spreadsheets/d/13d_Jei6oAufaEJFa5i5GJk4yYvFSNYEI/export?format=csv"

# Leer CSV con manejo de errores
try:
    df = pd.read_csv(sheet_url, skiprows=13, usecols=[2, 5, 6, 7])
except Exception as e:
    raise RuntimeError(f"No se pudo leer el Google Sheet: {e}")

# Renombrar columnas
df = df.rename(columns={
    df.columns[0]: 'RN',
    df.columns[1]: 'Estado',
    df.columns[2]: 'Inicio',
    df.columns[3]: 'Fin'
})

# Validar columnas requeridas
columnas_requeridas = ['RN', 'Estado', 'Inicio', 'Fin']
if not all(col in df.columns for col in columnas_requeridas):
    raise ValueError(f"El archivo debe contener estas columnas: {columnas_requeridas}")

# Eliminar filas con fechas vacías
df = df.dropna(subset=['Inicio', 'Fin'])

# Convertir fechas con manejo de errores y coerción
df['Inicio'] = pd.to_datetime(df['Inicio'], errors='coerce')
df['Fin'] = pd.to_datetime(df['Fin'], errors='coerce')

# Eliminar filas donde la conversión falló
df = df.dropna(subset=['Inicio', 'Fin'])

# Crear columnas para hover
df['Inicio_str'] = df['Inicio'].dt.strftime('%Y-%m-%d')
df['Fin_str'] = df['Fin'].dt.strftime('%Y-%m-%d')

# Ordenar y resetear índice
df = df.sort_values(by='Inicio').reset_index(drop=True)

# Calcular duración y mes
df['Duracion'] = (df['Fin'] - df['Inicio']).dt.days
df['Mes'] = df['Fin'].dt.to_period('M').astype(str)

# Acortar nombres RN
df['RN_short'] = df['RN'].str.slice(0, 20) + df['RN'].apply(lambda x: '...' if len(str(x)) > 20 else '')

# Colores personalizados
color_estado = {
    'Entregado': 'green',
    'En desarrollo': 'teal',
    'Backlog': 'yellow',
    'Para refinar': 'lightyellow',
    'Escribiendo': 'orange',
    'Para escribir': 'red'
}

# Crear app Dash
app = Dash(__name__)
server = app.server

app.layout = html.Div([
    html.H1("Gantt Desarrollo Postventa", style={'textAlign': 'center'}),
    
    html.Div([
        html.Label("Seleccionar Mes (por fecha de finalización):"),
        dcc.Dropdown(
            id='mes-dropdown',
            options=[{'label': 'Todos', 'value': 'Todos'}] + 
                    [{'label': mes, 'value': mes} for mes in sorted(df['Mes'].unique())],
            value='Todos'
        )
    ], style={'width': '48%', 'display': 'inline-block'}),
    
    html.Div([
        html.Label("Seleccionar Estado:"),
        dcc.Dropdown(
            id='estado-dropdown',
            options=[{'label': estado, 'value': estado} for estado in sorted(df['Estado'].unique())] + [{'label': 'Todos', 'value': 'Todos'}],
            value='Todos'
        )
    ], style={'width': '48%', 'display': 'inline-block', 'marginLeft': '10px'}),
    
    dcc.Graph(id='gantt-graph')
])

@app.callback(
    Output('gantt-graph', 'figure'),
    [Input('mes-dropdown', 'value'),
     Input('estado-dropdown', 'value')]
)
def actualizar_gantt(mes_seleccionado, estado_seleccionado):
    df_filtrado = df if mes_seleccionado == 'Todos' else df[df['Mes'] == mes_seleccionado]
    df_filtrado = df_filtrado if estado_seleccionado == 'Todos' else df_filtrado[df_filtrado['Estado'] == estado_seleccionado]

    fig = px.timeline(
        df_filtrado,
        x_start="Inicio",
        x_end="Fin",
        y="RN",
        color="Estado",
        color_discrete_map=color_estado,
        custom_data=["RN", "Inicio_str", "Fin_str"],
        hover_data={},
        title=f"Gantt - Mes: {mes_seleccionado} - Estado: {estado_seleccionado}",
        text="RN_short"
    )

    fig.update_traces(
        hovertemplate=(
            "<b>RN: %{customdata[0]}</b><br>"
            "Inicio: %{customdata[1]}<br>"
            "Fin: %{customdata[2]}"
        ),
        texttemplate='%{text}',
        textposition='inside',
        insidetextanchor='middle',
        textfont=dict(size=11, color='black')
    )

    fig.update_layout(
        height=750,
        xaxis_title="Fecha",
        yaxis_title="",
        legend_title="Estado",
        hovermode="closest",
        bargap=0.2,
        uniformtext=dict(minsize=8, mode='hide'),
        yaxis=dict(
            autorange="reversed",
            showticklabels=False,
            showgrid=False,
            visible=False
        )
    )

    return fig

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080)


