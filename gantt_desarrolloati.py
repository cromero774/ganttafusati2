import pandas as pd
import plotly.express as px
from dash import Dash, dcc, html, Input, Output
import requests
import sys

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
    df = pd.read_csv(sheet_url, encoding='utf-8')
    df.columns = df.columns.str.strip()
    df['RN'] = df['RN'].astype(str).str.strip()
    for col in ['Inicio', 'Fin']:
        try:
            df[col] = pd.to_datetime(df[col], format='%d/%m/%Y', errors='coerce')
        except:
            try:
                df[col] = pd.to_datetime(df[col], format='%d-%m-%Y', errors='coerce')
            except:
                df[col] = pd.to_datetime(df[col], dayfirst=True, errors='coerce')
    df = df.dropna(subset=['Inicio', 'Fin'])
    df['Inicio_str'] = df['Inicio'].dt.strftime('%d-%m-%Y')
    df['Fin_str'] = df['Fin'].dt.strftime('%d-%m-%Y')
    df['Duracion'] = (df['Fin'] - df['Inicio']).dt.days
    df['Mes'] = df['Fin'].dt.to_period('M').astype(str)
    # RN en minúscula, truncado y sin espacios extra
    df['RN_trunc'] = df['RN'].str.lower().str.strip().apply(lambda x: x if len(x) <= 30 else x[:27] + '...')
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
    df['RN_trunc'] = df['RN'].str.lower()

# --- Colores por estado (modernos) ---
color_estado = {
    'Entregado': '#4caf50',
    'En desarrollo': '#2196f3',
    'Backlog': '#ffc107',
    'Para refinar': '#ff9800',
    'Escribiendo': '#9c27b0',
    'Para escribir': '#f44336',
    'En Análisis': '#00bcd4',
    'Cancelado': '#bdbdbd',
    'Error': '#f44336'
}

# --- App Dash ---
app = Dash(__name__)
server = app.server

# --- Layout ---
app.layout = html.Div([
    html.H1("Gantt desarrollo ATI", style={'textAlign': 'center', 'fontFamily': 'Montserrat, Arial, sans-serif', 'fontWeight': 'bold', 'fontSize': '2.5rem', 'marginBottom': '10px'}),
    html.Div([
        html.Div([
            html.Label("Mes de entrega:", style={'fontFamily': 'Montserrat, Arial, sans-serif', 'fontSize': '1rem'}),
            dcc.Dropdown(
                id='mes-dropdown',
                options=[{'label': 'Todos', 'value': 'Todos'}] +
                        [{'label': mes, 'value': mes} for mes in sorted(df['Mes'].unique())],
                value='Todos',
                clearable=False,
                style={'fontSize': '1rem'}
            )
        ], style={'width': '48%', 'display': 'inline-block'}),
        html.Div([
            html.Label("Estado:", style={'fontFamily': 'Montserrat, Arial, sans-serif', 'fontSize': '1rem'}),
            dcc.Dropdown(
                id='estado-dropdown',
                options=[{'label': 'Todos', 'value': 'Todos'}] +
                        [{'label': estado, 'value': estado} for estado in sorted(df['Estado'].unique())],
                value='Todos',
                clearable=False,
                style={'fontSize': '1rem'}
            )
        ], style={'width': '48%', 'display': 'inline-block', 'marginLeft': '10px'}),
    ], style={'marginBottom': '10px'}),

    html.Div([
        html.Label("Tema:", style={'fontFamily': 'Montserrat, Arial, sans-serif', 'fontSize': '1rem'}),
        dcc.RadioItems(
            id='theme-switch',
            options=[
                {'label': 'Claro', 'value': 'light'},
                {'label': 'Oscuro', 'value': 'dark'}
            ],
            value='light',
            labelStyle={'display': 'inline-block', 'marginRight': '10px', 'fontFamily': 'Montserrat, Arial, sans-serif', 'fontSize': '1rem'}
        )
    ], style={'marginBottom': '10px'}),

    html.Div([
        dcc.Graph(id='gantt-graph', style={'height': '80vh'})
    ]),
], style={'maxWidth': '1100px', 'margin': '0 auto', 'padding': '10px', 'fontFamily': 'Montserrat, Arial, sans-serif', 'background': '#fafbfc'})

# --- Callback ---
@app.callback(
    Output('gantt-graph', 'figure'),
    [Input('mes-dropdown', 'value'),
     Input('estado-dropdown', 'value'),
     Input('theme-switch', 'value')]
)
def actualizar_grafico(mes, estado, theme):
    df_filtrado = df.copy()
    if mes != 'Todos':
        df_filtrado = df_filtrado[df_filtrado['Mes'] == mes]
    if estado != 'Todos':
        df_filtrado = df_filtrado[df_filtrado['Estado'] == estado]
    if df_filtrado.empty:
        return px.scatter(title="Sin datos con los filtros seleccionados")

    # Ordenar por inicio y RN
    df_filtrado = df_filtrado.sort_values(['Inicio', 'RN_trunc'])
    rn_order = df_filtrado['RN_trunc'].unique().tolist()
    df_filtrado['RN_order'] = df_filtrado['RN_trunc'].map({rn: i for i, rn in enumerate(rn_order)})
    df_filtrado = df_filtrado.sort_values('RN_order')

    # Tema claro/oscuro
    if theme == 'dark':
        plot_bgcolor = '#23272f'
        paper_bgcolor = '#23272f'
        font_color = '#f0f0f0'
        gridcolor = '#444'
    else:
        plot_bgcolor = '#fafbfc'
        paper_bgcolor = '#fafbfc'
        font_color = '#222'
        gridcolor = '#e0e0e0'

    fig = px.timeline(
        df_filtrado,
        x_start="Inicio",
        x_end="Fin",
        y="RN_trunc",
        color="Estado",
        custom_data=["RN", "Inicio_str", "Fin_str", "Duracion"],
        color_discrete_map=color_estado,
        title=None
    )

    # Barras finas y separadas
    fig.update_traces(
        width=0.18,
        marker=dict(line=dict(width=0.2, color='#888')),
        hovertemplate="<b>%{customdata[0]}</b><br>Inicio: %{customdata[1]}<br>Fin: %{customdata[2]}<br>Días: %{customdata[3]}"
    )

    # Eje Y en minúscula, letra pequeña, fuente moderna
    fig.update_layout(
        xaxis=dict(
            title="Fecha",
            tickformat="%d-%m-%Y",
            gridcolor=gridcolor,
            title_font=dict(size=16, family='Montserrat, Arial, sans-serif')
        ),
        yaxis=dict(
            autorange="reversed",
            title="requerimiento",
            categoryorder='array',
            categoryarray=rn_order,
            tickfont=dict(size=11, family='Montserrat, Arial, sans-serif', color=font_color),
            title_font=dict(size=14, family='Montserrat, Arial, sans-serif', color=font_color)
        ),
        plot_bgcolor=plot_bgcolor,
        paper_bgcolor=paper_bgcolor,
        font=dict(color=font_color, family='Montserrat, Arial, sans-serif', size=13),
        legend=dict(
            title="Estado",
            x=1.01, y=1,
            font=dict(size=12, family='Montserrat, Arial, sans-serif'),
            bgcolor='rgba(0,0,0,0)'
        ),
        margin=dict(l=10, r=160, t=30, b=30),
        height=730,
        hoverlabel=dict(
            font_size=13,
            font_family='Montserrat, Arial, sans-serif',
            bgcolor='#fff',
            bordercolor='#888',
            font_color='#222'
        ),
        title=None
    )

    return fig

# --- Ejecutar ---
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)





















































