import pandas as pd
import plotly.express as px
from dash import Dash, dcc, html, Input, Output
import requests
import sys
import datetime

# --- Función de debug ---
def debug_print(message):
    print(f"DEBUG: {message}", file=sys.stderr)
    sys.stderr.flush()

# --- Carga de datos ---
sheet_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vT6s9qMzmA_sJRko5EDggumO4sybGVq3n-uOmZOMj8CJDnHo9AWZeZOXZGz7cTg4XoqeiPDIgQP3QER/pub?output=csv"

try:
    debug_print("Intentando cargar datos desde URL...")
    response = requests.get(sheet_url, timeout=15)
    response.raise_for_status()
    debug_print(f"Respuesta recibida. Status code: {response.status_code}")
    debug_print(f"Primeros 200 caracteres: {response.text[:200]}")
    df = pd.read_csv(sheet_url, encoding='utf-8')
    df.columns = df.columns.str.strip()
    df['RN'] = df['RN'].astype(str).str.strip()
    debug_print(f"Columnas detectadas: {df.columns.tolist()}")
    debug_print(f"Primeras filas: {df.head(2).to_dict()}")
    for col in ['Inicio', 'Fin']:
        try:
            df[col] = pd.to_datetime(df[col], format='%d/%m/%Y', errors='coerce')
        except:
            try:
                df[col] = pd.to_datetime(df[col], format='%d-%m-%Y', errors='coerce')
            except:
                try:
                    df[col] = pd.to_datetime(df[col], dayfirst=True, errors='coerce')
                except Exception as e:
                    debug_print(f"Error en conversión de fechas para columna {col}: {e}")
    debug_print(f"Muestra de fechas después de conversión: {df[['Inicio', 'Fin']].head(3)}")
    df = df.dropna(subset=['Inicio', 'Fin'])
    debug_print(f"Filas restantes después de eliminar NaT: {len(df)}")
    df['Inicio_str'] = df['Inicio'].dt.strftime('%d-%m-%Y')
    df['Fin_str'] = df['Fin'].dt.strftime('%d-%m-%Y')
    df['Duracion'] = (df['Fin'] - df['Inicio']).dt.days
    df['Mes'] = df['Fin'].dt.to_period('M').astype(str)
    df['RN_trunc'] = df['RN'].apply(lambda x: x if len(x) <= 30 else x[:27] + '...')
    debug_print(f"DataFrame procesado. Forma final: {df.shape}")
except Exception as e:
    debug_print(f"Error cargando datos: {e}")
    sample_dates = pd.date_range(start='2023-01-01', periods=3)
    df = pd.DataFrame({
        'RN': ['Error - Sin datos', 'Ejemplo 2', 'Ejemplo 3'],
        'Estado': ['Error', 'Error', 'Error'],
        'Inicio': sample_dates,
        'Fin': sample_dates + pd.Timedelta(days=30),
    })
    df['Inicio_str'] = df['Inicio'].dt.strftime('%d-%m-%Y')
    df['Fin_str'] = df['Fin'].dt.strftime('%d-%m-%Y')
    df['Duracion'] = 30
    df['Mes'] = df['Fin'].dt.to_period('M').astype(str)
    df['RN_trunc'] = df['RN']

# --- Colores por estado ---
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

# --- App Dash ---
app = Dash(__name__)
server = app.server

# --- Layout ---
app.layout = html.Div([
    html.H1("Gantt desarrollo ATI", style={'textAlign': 'center'}),
    html.Div(
        f"Fecha actual: {datetime.datetime.now().strftime('%d-%m-%Y')}",
        style={'textAlign': 'right', 'fontSize': '14px', 'color': '#888', 'marginBottom': '10px'}
    ),
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
                value=['Todos'],  # <-- Es lista, no string
                clearable=False,
                multi=True  # <-- Permite multiselección
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
            labelStyle={'display': 'inline-block', 'marginRight': '10px'}
        )
    ], style={'marginBottom': '20px'}),

    html.Div([
        dcc.Graph(id='gantt-graph', style={'height': '80vh'})
    ]),
    html.Div(id='debug-info', style={'whiteSpace': 'pre-wrap', 'padding': '10px', 'border': '1px solid #ddd'})
])

# --- Callback ---
@app.callback(
    [Output('gantt-graph', 'figure'),
     Output('debug-info', 'children')],
    Input('mes-dropdown', 'value'),
    Input('estado-dropdown', 'value'),  # Recibe lista
    Input('theme-switch', 'value')
)
def actualizar_grafico(mes, estados, theme):
    df_filtrado = df.copy()
    debug_info = f"Datos cargados: {len(df)} filas\n"
    debug_info += f"Filtros: Mes={mes}, Estado={estados}\n"
    if mes != 'Todos':
        df_filtrado = df_filtrado[df_filtrado['Mes'] == mes]
    # Multi-selección de estado
    if isinstance(estados, list):
        if 'Todos' not in estados:
            df_filtrado = df_filtrado[df_filtrado['Estado'].isin(estados)]
    else:
        if estados != 'Todos':
            df_filtrado = df_filtrado[df_filtrado['Estado'] == estados]
    debug_info += f"Datos filtrados: {len(df_filtrado)} filas\n"
    if df_filtrado.empty:
        debug_info += "¡No hay datos después del filtrado!"
        return px.scatter(title="Sin datos con los filtros seleccionados"), debug_info

    if theme == 'dark':
        plot_bgcolor = '#23272f'
        paper_bgcolor = '#23272f'
        font_color = '#f0f0f0'
        gridcolor = '#444'
        current_line_color = '#e74c3c'
    else:
        plot_bgcolor = 'white'
        paper_bgcolor = 'white'
        font_color = '#222'
        gridcolor = '#eee'
        current_line_color = '#e74c3c'

    df_filtrado = df_filtrado.sort_values('Inicio')
    rn_order = df_filtrado['RN_trunc'].unique().tolist()
    df_filtrado['RN_order'] = df_filtrado['RN_trunc'].map({rn: i for i, rn in enumerate(rn_order)})
    df_filtrado = df_filtrado.sort_values('RN_order')

    debug_info += f"Estados únicos: {df_filtrado['Estado'].unique().tolist()}\n"
    debug_info += f"Rango de fechas: {df_filtrado['Inicio'].min().strftime('%d-%m-%Y')} a {df_filtrado['Fin'].max().strftime('%d-%m-%Y')}\n"

    try:
        fig = px.timeline(
            df_filtrado,
            x_start="Inicio",
            x_end="Fin",
            y="RN_trunc",
            color="Estado",
            custom_data=["RN", "Inicio_str", "Fin_str", "Duracion"],
            color_discrete_map=color_estado,
            title=f"Postventa - {', '.join(estados) if isinstance(estados, list) and 'Todos' not in estados else 'Todos los estados'} | {mes if mes != 'Todos' else 'Todos los meses'}"
        )

        # Barras más delgadas
        fig.update_traces(
            hovertemplate="<b>%{customdata[0]}</b><br>Inicio: %{customdata[1]}<br>Fin: %{customdata[2]}<br>Días: %{customdata[3]}",
            marker=dict(line=dict(width=0.3, color='DarkSlateGrey')),
            width=0.3
        )

        # Línea vertical para la fecha actual
        fecha_actual = datetime.datetime.now()
        fig.add_vline(
            x=fecha_actual,
            line_width=2,
            line_dash="dash",
            line_color=current_line_color,
            annotation_text="Hoy",
            annotation_position="top",
            annotation_font_color=current_line_color,
            annotation_bgcolor=plot_bgcolor
        )

        fig.update_layout(
            xaxis=dict(title="Fecha", tickformat="%d-%m-%Y", gridcolor=gridcolor),
            yaxis=dict(
                autorange="reversed", 
                title="Requerimiento",
                categoryorder='array',
                categoryarray=rn_order
            ),
            plot_bgcolor=plot_bgcolor,
            paper_bgcolor=paper_bgcolor,
            font=dict(color=font_color),
            legend=dict(title="Estado", x=1.01, y=1),
            margin=dict(l=20, r=250, t=50, b=50),
            height=800
        )
        debug_info += "Gráfico generado correctamente"
        return fig, debug_info
    except Exception as e:
        debug_info += f"Error al generar gráfico: {e}"
        return px.scatter(title=f"Error al generar gráfico: {e}"), debug_info

# --- Ejecutar ---
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)









































