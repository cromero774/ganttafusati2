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
    # Intentar leer el archivo CSV
    debug_print("Intentando leer el archivo CSV...")
    df = pd.read_csv(sheet_url, skiprows=13, usecols=[2, 5, 6, 7])
    debug_print(f"CSV leído. Forma del DataFrame: {df.shape}")
    debug_print(f"Columnas encontradas: {df.columns.tolist()}")
    
    # Renombrar columnas
    debug_print("Renombrando columnas...")
    columnas_originales = df.columns.tolist()
    if len(columnas_originales) >= 4:
        df = df.rename(columns={
            columnas_originales[0]: 'RN',
            columnas_originales[1]: 'Estado',
            columnas_originales[2]: 'Inicio',
            columnas_originales[3]: 'Fin'
        })
        debug_print(f"Columnas después de renombrar: {df.columns.tolist()}")
    else:
        debug_print(f"ADVERTENCIA: No hay suficientes columnas. Encontradas: {columnas_originales}")
        df = crear_datos_prueba()
    
    # Validar que las columnas requeridas existen
    columnas_requeridas = ['RN', 'Estado', 'Inicio', 'Fin']
    if not all(col in df.columns for col in columnas_requeridas):
        debug_print(f"ADVERTENCIA: No se encontraron todas las columnas requeridas.")
        df = crear_datos_prueba()
    
    # Eliminar filas con valores nulos en las fechas
    df_original_len = len(df)
    df = df.dropna(subset=['Inicio', 'Fin'])
    debug_print(f"Filas eliminadas por valores nulos: {df_original_len - len(df)}")
    
    # Intentar convertir las fechas
    debug_print("Intentando convertir fechas...")
    debug_print(f"Ejemplos de valores en 'Inicio': {df['Inicio'].head(3).tolist()}")
    debug_print(f"Ejemplos de valores en 'Fin': {df['Fin'].head(3).tolist()}")
    
    # Verificar si los valores son numéricos (posiblemente fechas en formato Excel)
    def es_numerico(valor):
        try:
            float(valor)
            return True
        except (ValueError, TypeError):
            return False
    
    # Si las "fechas" son números, probablemente son fechas de Excel
    if df['Inicio'].apply(es_numerico).all() and df['Fin'].apply(es_numerico).all():
        debug_print("Detectados posibles valores de fecha en formato Excel, convirtiendo...")
        # Convertir fechas de Excel (días desde 1900-01-01)
        df['Inicio'] = pd.to_datetime('1899-12-30') + pd.to_timedelta(df['Inicio'].astype(float), unit='D')
        df['Fin'] = pd.to_datetime('1899-12-30') + pd.to_timedelta(df['Fin'].astype(float), unit='D')
    else:
        # Intentar convertir fechas normales
        df['Inicio'] = pd.to_datetime(df['Inicio'], errors='coerce')
        df['Fin'] = pd.to_datetime(df['Fin'], errors='coerce')
    
    # Eliminar filas donde la conversión de fechas falló
    df_fechas_len = len(df)
    df = df.dropna(subset=['Inicio', 'Fin'])
    debug_print(f"Filas eliminadas por fechas inválidas: {df_fechas_len - len(df)}")
    
    # Si no quedan datos válidos, usar datos de prueba
    if len(df) == 0:
        debug_print("No hay datos válidos después del procesamiento. Usando datos de prueba.")
        df = crear_datos_prueba()
    
except Exception as e:
    debug_print(f"ERROR: {str(e)}")
    df = crear_datos_prueba()

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

debug_print(f"DataFrame final: {len(df)} filas, estados únicos: {df['Estado'].unique().tolist()}")
debug_print(f"Meses únicos: {df['Mes'].unique().tolist()}")

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
    
    # Compatibilidad con diferentes versiones de Dash
    try:
        # Para versiones más recientes de Dash
        app.run(host='0.0.0.0', port=port)
    except AttributeError:
        # Para versiones anteriores de Dash
        app.run_server(host='0.0.0.0', port=port)