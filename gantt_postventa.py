import pandas as pd
import plotly.express as px
from dash import Dash, dcc, html, Input, Output

# 1. Leer archivo Excel
file_path = r'C:\Users\cromero\OneDrive - EVOLTIS\Documentos\Maipu\Pedidos\Estimacion_ Paquetes.xlsx'
sheet_name = 'Paquete Dev postventa'
usecols = [2, 5, 6, 7]
skip_rows = 13

df = pd.read_excel(file_path, sheet_name=sheet_name, skiprows=skip_rows, usecols=usecols, header=0)

# 2. Preparar datos
df = df.rename(columns={
    df.columns[0]: 'RN',
    df.columns[1]: 'Estado',
    df.columns[2]: 'Inicio',
    df.columns[3]: 'Fin'
})

# Validación básica de columnas
columnas_requeridas = ['RN', 'Estado', 'Inicio', 'Fin']
if not all(col in df.columns for col in columnas_requeridas):
    raise ValueError(f"El archivo debe contener estas columnas: {columnas_requeridas}")

df = df.dropna(subset=['Inicio', 'Fin'])
df['Inicio'] = pd.to_datetime(df['Inicio'])
df['Fin'] = pd.to_datetime(df['Fin'])

# Convertir fechas a string para el hover
df['Inicio_str'] = df['Inicio'].dt.strftime('%Y-%m-%d')
df['Fin_str'] = df['Fin'].dt.strftime('%Y-%m-%d')

df = df.sort_values(by='Inicio', ascending=True).reset_index(drop=True)
df['Duracion'] = (df['Fin'] - df['Inicio']).dt.days
df['Mes'] = df['Fin'].dt.to_period('M').astype(str)

# Acortar nombres de RN
df['RN_short'] = df['RN'].str[:20] + ('...' if df['RN'].str.len().max() > 20 else '')

# 3. Colores personalizados por Estado
color_estado = {
    'Entregado': 'green',
    'En desarrollo': 'teal',
    'Backlog': 'yellow',
    'Para refinar': 'lightyellow',
    'Escribiendo': 'orange',
    'Para escribir': 'red'
}

# 4. Crear la app Dash
app = Dash(__name__)
server = app.server

# 5. Layout de la app
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

# 6. Callback modificado
@app.callback(
    Output('gantt-graph', 'figure'),
    [Input('mes-dropdown', 'value'),
     Input('estado-dropdown', 'value')]
)
def actualizar_gantt(mes_seleccionado, estado_seleccionado):
    # Filtrar datos
    df_filtrado = df if mes_seleccionado == 'Todos' else df[df['Mes'] == mes_seleccionado]
    df_filtrado = df_filtrado if estado_seleccionado == 'Todos' else df_filtrado[df_filtrado['Estado'] == estado_seleccionado]

    # Crear figura
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

    # Personalización del hover
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

    # Configuración del layout actualizada
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



