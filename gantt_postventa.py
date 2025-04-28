import pandas as pd
import plotly.express as px
from dash import Dash, dcc, html, Input, Output
import sys

# Función para imprimir mensajes de depuración
def debug_print(message):
    print(f"DEBUG: {message}", file=sys.stderr)
    sys.stderr.flush()

debug_print("Iniciando aplicación...")

# URL pública para exportar Google Sheets como CSV (primera hoja)
sheet_url = "https://docs.google.com/spreadsheets/d/13d_Jei6oAufaEJFa5i5GJk4yYvFSNYEI/export?format=csv"
debug_print(f"URL de la hoja: {sheet_url}")

# Crear datos de prueba para garantizar que siempre haya datos válidos
def crear_datos_prueba():
    debug_print("Creando datos de prueba...")
    data = {
        'RN': ['Tarea 1', 'Tarea 2', 'Tarea 3', 'Tarea 4', 'Tarea 5'],
        'Estado': ['Entregado', 'En desarrollo', 'Backlog', 'Para refinar', 'Escribiendo'],
        'Inicio': pd.to_datetime(['2025-01-01', '2025-01-15', '2025-02-01', '2025-02-15', '2025-03-01']),
        'Fin': pd.to_datetime(['2025-01-14', '2025-01-30', '2025-02-15', '2025-02-28', '2025-03-15'])
    }
    return pd.DataFrame(data)

try:
    debug_print("Intentando leer el archivo CSV...")

    # Leer tabla azul: encabezado en fila 14 (índice 13), columnas 0,3,4,5
    df = pd.read_csv(sheet_url, skiprows=13, usecols=[0, 3, 4, 5])
    debug_print(f"CSV leído. Forma del DataFrame: {df.shape}")
    debug_print(f"Columnas encontradas: {df.columns.tolist()}")

    # Renombrar columnas para trabajar con nombres estándar
    df = df.rename(columns={
        df.columns[0]: 'RN',
        df.columns[1]: 'Estado',
        df.columns[2]: 'Inicio',
        df.columns[3]: 'Fin'
    })
    debug_print(f"Columnas después de renombrar: {df.columns.tolist()}")

    # Validar que las columnas requeridas existen
    columnas_requeridas = ['RN', 'Estado', 'Inicio', 'Fin']
    if not all(col in df.columns for col in columnas_requeridas):
        debug_print("ADVERTENCIA: No se encontraron todas las columnas requeridas.")
        df = crear_datos_prueba()

    # Eliminar filas con valores nulos en fechas
    df_original_len = len(df)
    df = df.dropna(subset=['Inicio', 'Fin'])
    debug_print(f"Filas eliminadas por valores nulos: {df_original_len - len(df)}")

    # Detectar si las fechas están en formato numérico (fecha Excel)
    def es_numerico(valor):
        try:
            float(valor)
            return True
        except (ValueError, TypeError):
            return False

    if df['Inicio'].apply(es_numerico).all() and df['Fin'].apply(es_numerico).all():
        debug_print("Fechas en formato numérico detectadas, convirtiendo desde formato Excel...")
        df['Inicio'] = pd.to_datetime('1899-12-30') + pd.to_timedelta(df['Inicio'].astype(float), unit='D')
        df['Fin'] = pd.to_datetime('1899-12-30') + pd.to_timedelta(df['Fin'].astype(float), unit='D')
    else:
        df['Inicio'] = pd.to_datetime(df['Inicio'], errors='coerce')
        df['Fin'] = pd.to_datetime(df['Fin'], errors='coerce')

    # Eliminar filas con fechas inválidas tras conversión
    df_fechas_len = len(df)
    df = df.dropna(subset=['Inicio', 'Fin'])
    debug_print(f"Filas eliminadas por fechas inválidas: {df_fechas_len - len(df)}")

    # Si no quedan datos válidos, usar datos de prueba
    if len(df) == 0:
        debug_print("No hay datos válidos después del procesamiento. Usando datos de prueba.")
        df = crear_datos_prueba()

except Exception as e:
    debug_print(f"ERROR al leer CSV: {str(e)}")
    df = crear_datos_prueba()

# Preparar columnas para hover y visualización
df['Inicio_str'] = df['Inicio'].dt.strftime('%Y-%m-%d')
df['Fin_str'] = df['Fin'].dt.strftime('%Y-%m-%d')

df = df.sort_values(by='Inicio').reset_index(drop=True)
df['Duracion'] = (df['Fin'] - df['Inicio']).dt.days
df['Mes'] = df['Fin'].dt.to_period('M').astype(str)
df['RN_short'] = df['RN'].str.slice(0, 20) + df['RN'].apply(lambda x: '...' if len(str(x)) > 20 else '')

debug_print(f"DataFrame final: {len(df)} filas, estados únicos: {df['Estado'].unique().tolist()}")
debug_print(f"Meses únicos: {df['Mes'].unique().tolist()}")

# Colores personalizados para estados
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
            options=[{'label': 'Todos', 'value': 'Todos'}] +
                    [{'label': estado, 'value': estado} for estado in sorted(df['Estado'].unique())],
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
    debug_print(f"Callback ejecutado: mes={mes_seleccionado}, estado={estado_seleccionado}")

    df_filtrado = df if mes_seleccionado == 'Todos' else df[df['Mes'] == mes_seleccionado]
    df_filtrado = df_filtrado if estado_seleccionado == 'Todos' else df_filtrado[df_filtrado['Estado'] == estado_seleccionado]

    debug_print(f"DataFrame filtrado: {len(df_filtrado)} filas")

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
    debug_print("Figura creada y enviada al cliente")
    return fig

if __name__ == '__main__':
    debug_print("Iniciando servidor...")
    import os
    port = int(os.environ.get('PORT', 8080))
    debug_print(f"Puerto configurado: {port}")

    try:
        app.run(host='0.0.0.0', port=port)
    except AttributeError:
        app.run_server(host='0.0.0.0', port=port)

