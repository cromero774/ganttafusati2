import pandas as pd
import plotly.express as px
from dash import Dash, dcc, html, Input, Output
import sys
import requests
import os
from datetime import datetime
import io

def debug_print(message):
    """Función para imprimir mensajes de depuración"""
    print(f"DEBUG: {message}", file=sys.stderr)
    sys.stderr.flush()

debug_print("Iniciando aplicación...")

# URL de Google Sheets
sheet_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vT6s9qMzmA_sJRko5EDggumO4sybGVq3n-uOmZOMj8CJDnHo9AWZeZOXZGz7cTg4XoqeiPDIgQP3QER/pub?output=csv"

try:
    debug_print(f"Intentando cargar datos desde: {sheet_url}")
    # Cargar datos con timeout de 15 segundos
    response = requests.get(sheet_url, timeout=15)
    response.raise_for_status()  # Esto lanzará una excepción si hay un error HTTP
    
    # Mostrar los primeros bytes de la respuesta para diagnóstico
    debug_print(f"Primeros 500 caracteres de la respuesta: {response.text[:500]}")
    
    # Convertir a DataFrame
    df = pd.read_csv(io.StringIO(response.text))
    debug_print(f"Datos cargados. Columnas: {df.columns.tolist()}")
    debug_print(f"Número de filas original: {len(df)}")
    
    # Mostrar las primeras filas para diagnóstico
    debug_print(f"Primeras 2 filas del DataFrame:\n{df.head(2)}")
    
    # Limpiar columnas
    df.columns = df.columns.str.strip()
    if 'RN' in df.columns:
        df['RN'] = df['RN'].astype(str).str.replace(r'[\xa0\s]+', ' ', regex=True).str.strip()
    
    # Examinar formato de fechas antes de la conversión
    if 'Inicio' in df.columns and 'Fin' in df.columns:
        debug_print(f"Ejemplos de fechas Inicio: {df['Inicio'].head().tolist()}")
        debug_print(f"Ejemplos de fechas Fin: {df['Fin'].head().tolist()}")
    
    # Convertir fechas con múltiples formatos posibles
    formatos_fecha = ['%m/%d/%Y', '%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y']
    
    for col in ['Inicio', 'Fin']:
        if col in df.columns:
            # Intentar varios formatos de fecha
            for formato in formatos_fecha:
                # Primero intentar con este formato
                df[f'{col}_temp'] = pd.to_datetime(df[col], format=formato, errors='coerce')
                # Si más del 50% de las fechas se pudieron convertir, usar este formato
                if df[f'{col}_temp'].notna().mean() > 0.5:
                    df[col] = df[f'{col}_temp']
                    debug_print(f"Formato detectado para {col}: {formato}")
                    break
            
            # Si ningún formato específico funcionó, intentar con inferencia automática
            if df[col].isna().all():
                df[col] = pd.to_datetime(df[col], errors='coerce')
                debug_print(f"Usando inferencia automática para {col}")
            
            # Eliminar columnas temporales
            for temp_col in [c for c in df.columns if c.endswith('_temp')]:
                if temp_col in df.columns:
                    df = df.drop(columns=[temp_col])
    
    # Verificar fechas convertidas
    if 'Inicio' in df.columns and 'Fin' in df.columns:
        debug_print(f"Fechas iniciales convertidas (primeras 5): {df['Inicio'].head().tolist()}")
        debug_print(f"Fechas finales convertidas (primeras 5): {df['Fin'].head().tolist()}")
        debug_print(f"Fechas iniciales NaT: {df['Inicio'].isna().sum()}")
        debug_print(f"Fechas finales NaT: {df['Fin'].isna().sum()}")
    
    # Para tareas con fecha inicial pero sin fecha final, usar la fecha actual + 7 días como fecha final
    now = pd.Timestamp('now')
    if 'Inicio' in df.columns and 'Fin' in df.columns:
        mask = df['Fin'].isna() & df['Inicio'].notna()
        if mask.any():
            df.loc[mask, 'Fin'] = now + pd.Timedelta(days=7)
            debug_print(f"Se completaron {mask.sum()} fechas finales ausentes")
        
        # Para tareas con fecha final pero sin fecha inicial, usar la fecha final - 30 días como fecha inicial
        mask = df['Inicio'].isna() & df['Fin'].notna()
        if mask.any():
            df.loc[mask, 'Inicio'] = df.loc[mask, 'Fin'] - pd.Timedelta(days=30)
            debug_print(f"Se completaron {mask.sum()} fechas iniciales ausentes")
    
    # Eliminar filas donde aún falten fechas
    if 'Inicio' in df.columns and 'Fin' in df.columns:
        filas_antes = len(df)
        df = df.dropna(subset=['Inicio', 'Fin'])
        filas_despues = len(df)
        debug_print(f"Se eliminaron {filas_antes - filas_despues} filas con fechas faltantes")
        debug_print(f"Número de filas después de filtrar fechas: {len(df)}")
    
    # Si no hay datos, crear datos de ejemplo
    if df.empty or 'Inicio' not in df.columns or 'Fin' not in df.columns:
        debug_print("No hay datos válidos o formato incorrecto, creando ejemplos")
        sample_dates = pd.date_range(start='2023-01-01', periods=5)
        df = pd.DataFrame({
            'RN': ['Ejemplo 1', 'Ejemplo 2', 'Ejemplo 3', 'Ejemplo 4', 'Ejemplo 5'],
            'Estado': ['En desarrollo', 'Entregado', 'Backlog', 'Para refinar', 'Escribiendo'],
            'Inicio': sample_dates,
            'Fin': [d + pd.Timedelta(days=i*5+10) for i, d in enumerate(sample_dates)]
        })
    
    # Asegurar que todas las filas tienen un estado
    if 'Estado' not in df.columns:
        df['Estado'] = 'Sin estado'
    else:
        df['Estado'] = df['Estado'].fillna('Sin estado')
    
    # Crear columnas adicionales necesarias
    df['Inicio_str'] = df['Inicio'].dt.strftime('%Y-%m-%d')
    df['Fin_str'] = df['Fin'].dt.strftime('%Y-%m-%d')
    df['Duracion'] = (df['Fin'] - df['Inicio']).dt.days
    df['Mes'] = df['Fin'].dt.to_period('M').astype(str)
    
    debug_print(f"DataFrame final: {len(df)} filas")

except Exception as e:
    debug_print(f"Error al cargar datos: {str(e)}")
    import traceback
    debug_print(f"Stack trace: {traceback.format_exc()}")
    
    # Crear datos de ejemplo en caso de error
    sample_dates = pd.date_range(start='2023-01-01', periods=5)
    df = pd.DataFrame({
        'RN': ['Error - Sin datos', 'Ejemplo 2', 'Ejemplo 3', 'Ejemplo 4', 'Ejemplo 5'],
        'Estado': ['Error', 'En desarrollo', 'Backlog', 'Entregado', 'Para refinar'],
        'Inicio': sample_dates,
        'Fin': [d + pd.Timedelta(days=30) for d in sample_dates]
    })
    df['Inicio_str'] = df['Inicio'].dt.strftime('%Y-%m-%d')
    df['Fin_str'] = df['Fin'].dt.strftime('%Y-%m-%d')
    df['Duracion'] = (df['Fin'] - df['Inicio']).dt.days
    df['Mes'] = df['Inicio'].dt.to_period('M').astype(str)

# Mapa de colores para los estados
color_estado = {
    'Entregado': '#2ecc71',
    'En desarrollo': '#1abc9c',
    'Backlog': '#f1c40f',
    'Para refinar': '#f5d76e',
    'Escribiendo': '#e67e22',
    'Para escribir': '#e74c3c',
    'En Análisis': '#9b59b6',
    'Cancelado': '#95a5a6',
    'Error': '#e74c3c',
    'Sin estado': '#34495e'
}

# Inicializar app
app = Dash(__name__, suppress_callback_exceptions=True)
server = app.server

# Diseño de la aplicación
app.layout = html.Div([
    html.H1("Gantt desarrollo ATI", style={'textAlign': 'center', 'margin': '20px 0'}),
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
            style={'height': '600px', 'width': '100%'}  # Altura fija inicial
        )
    ], style={'height': 'auto', 'overflowY': 'auto', 'width': '100%'}),
    
    # Panel de información de depuración (visible por defecto para diagnóstico)
    html.Details([
        html.Summary("Información de depuración"),
        html.Pre(id='debug-info', style={'whiteSpace': 'pre-wrap', 'wordBreak': 'break-all'})
    ], style={'marginTop': '20px'}, open=True)
])

@app.callback(
    [Output('gantt-graph', 'figure'),
     Output('debug-info', 'children')],
    [Input('mes-dropdown', 'value'),
     Input('estado-dropdown', 'value'),
     Input('theme-switch', 'value')]
)
def actualizar_grafico(mes, estado, theme):
    debug_info = []
    debug_info.append(f"Filtros: Mes={mes}, Estado={estado}, Tema={theme}")
    debug_info.append(f"Total filas en DataFrame: {len(df)}")
    
    # Aplicar filtros
    filtered_df = df.copy()
    if mes != 'Todos':
        filtered_df = filtered_df[filtered_df['Mes'] == mes]
    if estado != 'Todos':
        filtered_df = filtered_df[filtered_df['Estado'] == estado]
    
    debug_info.append(f"Filas después de filtrar: {len(filtered_df)}")
    
    # Asegurarse de que hay datos para mostrar
    if filtered_df.empty:
        debug_info.append("¡ADVERTENCIA! No hay datos para mostrar con los filtros actuales")
        # Crear un gráfico vacío con mensaje
        fig = px.scatter(title="No hay datos para mostrar con los filtros seleccionados")
        fig.add_annotation(
            text="No hay datos para mostrar con los filtros seleccionados",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=20)
        )
        return fig, "\n".join(debug_info)
    
    # Seleccionar plantilla según tema
    template = 'plotly_white' if theme == 'light' else 'plotly_dark'
    
    # Crear gráfico de Gantt
    try:
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
        
        # Configurar eje Y
        fig.update_yaxes(
            autorange="reversed",  # Para que el primer elemento esté arriba
            tickfont=dict(size=12),
            automargin=True,
            title_text=""  # Removemos el título del eje Y
        )
        
        # Ajustar altura según cantidad de elementos
        height_px = max(400, len(filtered_df) * 40)
        
        # Configurar layout
        fig.update_layout(
            margin=dict(l=250, r=20, t=50, b=20),
            height=height_px,
            xaxis_title="Fechas",
            legend_title="Estado",
            title={
                'text': f"Tareas: {len(filtered_df)}",
                'x': 0.5,
                'xanchor': 'center'
            }
        )
        
        # Línea de la fecha actual
        hoy = datetime.now().date()
        fig.add_vline(
            x=hoy,
            line_dash="dash",
            line_color="red",
            annotation_text="Hoy",
            annotation_position="top right",
            opacity=0.8
        )
        
        debug_info.append("Gráfico creado exitosamente")
        return fig, "\n".join(debug_info)
        
    except Exception as e:
        debug_info.append(f"ERROR al crear gráfico: {str(e)}")
        import traceback
        debug_info.append(f"Stack trace: {traceback.format_exc()}")
        
        # Crear un gráfico de error
        fig = px.scatter(title="Error al generar el gráfico")
        fig.add_annotation(
            text=f"Error: {str(e)}",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="red")
        )
        return fig, "\n".join(debug_info)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    debug_print(f"Iniciando servidor en puerto: {port}")
    app.run(host='0.0.0.0', port=port, debug=True)  # Debug=True para desarrollo



































