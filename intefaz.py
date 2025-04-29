import flet as ft
import pandas as pd
import tkinter as tk
from tkinter import filedialog
import re
import os
import sys

# --- Funciones de Procesamiento de Datos (Mejoradas) ---

def clean_tipo_documento(tipo_doc_series):
    """Limpia la serie 'TIPO_DE_DOCUMENTO' eliminando números y espacios al inicio."""
    # Asegura que la serie es de tipo string antes de aplicar regex
    return tipo_doc_series.astype(str).str.replace(r'^\d+\s*', '', regex=True)

def process_data(df, mode):
    """
    Filtra, limpia, agrupa y agrega los datos basándose en el modo ('debito' o 'credito').
    Consolida nombres de cliente/consumidor final basándose en un patrón regex.

    Args:
        df (pd.DataFrame): El DataFrame original con los datos.
        mode (str): 'debito' para UNIDADES > 0, 'credito' para UNIDADES < 0.

    Returns:
        pd.DataFrame: Un DataFrame procesado y agrupado, o un DataFrame vacío con encabezados
                      si no hay datos que coincidan con el filtro, o None si el modo es inválido.
        Raises:
            ValueError: Si faltan columnas requeridas.
            Exception: Para otros errores de procesamiento.
    """
    print(f"Iniciando procesamiento para '{mode}'...") # Log para depuración si es necesario

    if mode == 'debito':
        print("Aplicando filtro: UNIDADES > 0")
        df_filtered = df[df['UNIDADES'] > 0].copy()
    elif mode == 'credito':
        print("Aplicando filtro: UNIDADES < 0")
        df_filtered = df[df['UNIDADES'] < 0].copy()
    else:
        raise ValueError("Modo de procesamiento inválido especificado.")

    # Definir las columnas esperadas en la salida final
    expected_final_columns = [
        'TIPO DE DOCUMENTO', 'IDENTIFICACION', 'NOMBRECLIENTE', 'PRIMER_APELLIDO',
        'SEGUNDO_APELLIDO', 'PRIMER_NOMBRE', 'OTROS_NOMBRES', 'MontoBruto',
        'Descuento', 'Iva'
    ]

    if df_filtered.empty:
        print(f"No se encontraron registros con UNIDADES {' > 0' if mode == 'debito' else ' < 0'} para procesar.")
        # Devolver un DataFrame vacío pero con los encabezados esperados
        return pd.DataFrame(columns=expected_final_columns)

    print(f"Filas encontradas después del filtro: {len(df_filtered)}")

    # --- Pasos de Procesamiento ---

    # *** MODIFICACIÓN: Consolidar nombres que matchean el patrón de cliente/consumidor final ***
    # El patrón busca cadenas que contengan 'cliente' o 'consumidor', seguidas por
    # cualquier cosa (.*? - cero o más caracteres no codiciosos), y luego 'final' con
    # una 'l' opcional al final ('l?'), ignorando mayúsculas/minúsculas ((?i)).
    final_pattern = r'(?i)(cliente|consumidor).*finall?'
    # Asegurar que la columna es de tipo string antes de usar str.contains
    df_filtered['NOMBRECLIENTE'] = df_filtered['NOMBRECLIENTE'].astype(str)
    # Crear una máscara booleana: True para filas que matchean el patrón, False en caso contrario
    # na=False asegura que los valores nulos no se incluyan en la coincidencia
    mask_final_clients = df_filtered['NOMBRECLIENTE'].str.contains(final_pattern, na=False)
    # Reemplazar los valores en 'NOMBRECLIENTE' que matchean el patrón por 'CONSUMIDOR FINAL'
    df_filtered.loc[mask_final_clients, 'NOMBRECLIENTE'] = 'CONSUMIDOR FINAL'
    print(f"Consolidación de 'CLIENTE FINAL'/'CONSUMIDOR FINAL' aplicada.")


    # 1. Limpiar TIPO_DE_DOCUMENTO y agregarlo como una nueva columna para la agregación
    df_filtered['TIPO_DE_DOCUMENTO_CLEANED'] = clean_tipo_documento(df_filtered['TIPO_DE_DOCUMENTO'])
    print("Limpieza de TIPO_DE_DOCUMENTO aplicada.")

    # 2. Definir el diccionario de agregación
    agg_dict = {
        'TIPO_DE_DOCUMENTO_CLEANED': 'first', # Toma el primer tipo de documento limpio del grupo
        'IDENTIFICACION': 'first',
        'PRIMER_APELLIDO': 'first',
        'SEGUNDO_APELLIDO': 'first',
        'PRIMER_NOMBRE': 'first',
        'OTROS_NOMBRES': 'first',
        'MontoBruto': 'sum', # Suma MontoBruto
        'Descuento': 'sum', # Suma Descuento
        'IVA': 'sum'        # Suma IVA
    }

    # Agrupar por NOMBRECLIENTE y aplicar la agregación
    print(f"Agrupando por NOMBRECLIENTE...")
    df_grouped = df_filtered.groupby('NOMBRECLIENTE', as_index=False).agg(agg_dict)
    print(f"Agrupación completada. Registros resultantes: {len(df_grouped)}")


    # 3. Renombrar columnas para que coincidan con los nombres de salida deseados
    rename_map = {
        'TIPO_DE_DOCUMENTO_CLEANED': 'TIPO DE DOCUMENTO',
        'IVA': 'Iva'
    }
    df_grouped = df_grouped.rename(columns=rename_map)
    print("Columnas renombradas.")

    # 4. Seleccionar y Reordenar columnas según la lista de salida deseada
    try:
        final_df = df_grouped[expected_final_columns]
        print("Columnas seleccionadas y reordenadas.")
    except KeyError as e:
        print(f"Error: Columna faltante después de la agregación y renombramiento: {e}. Columnas disponibles: {df_grouped.columns.tolist()}")
        # Devolver un DataFrame vacío con headers en caso de error
        return pd.DataFrame(columns=expected_final_columns)

    print(f"Procesamiento para '{mode}' finalizado exitosamente.")
    return final_df

# --- Interfaz Gráfica (Flet) ---

def main(page: ft.Page):
    page.title = "Generador de Reportes de Ventas"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.window_width = 550
    page.window_height = 450
    page.padding = 30
    page.theme_mode = ft.ThemeMode.LIGHT # O ft.ThemeMode.DARK

    # --- Tkinter setup (hidden root for dialogs) ---
    # Tkinter dialogs need a root window, but we don't want to show it
    root = tk.Tk()
    root.withdraw() # Hide the main Tkinter window

    # --- UI Controls ---
    title = ft.Text(
        "¿Qué deseas hacer hoy?",
        size=28,
        weight=ft.FontWeight.BOLD,
        text_align=ft.TextAlign.CENTER,
        color=ft.colors.PRIMARY
    )

    status_text = ft.Text(
        "", # Initial empty message
        size=14,
        color=ft.colors.BLACK54, # Neutral color initially
        text_align=ft.TextAlign.CENTER
    )

    # --- Button Handler Function ---
    # This function will handle clicks from both buttons based on the 'mode' parameter
    def handle_generate_report(mode):
        # Update status and disable buttons
        status_text.value = f"Seleccione el archivo Excel para el reporte de {mode}..."
        status_text.color = ft.colors.BLUE_ACCENT_700
        btn_debito.disabled = True
        btn_credito.disabled = True
        page.update()

        processed_df = None # Variable to hold the result DataFrame

        try:
            # 1. Select input file (Tkinter)
            input_file = filedialog.askopenfilename(
                title=f"Seleccionar Archivo de Datos ({mode})",
                filetypes=[("Excel files", "*.xlsx")],
                parent=root # Attach to hidden root
            )

            if not input_file:
                status_text.value = f"Selección de archivo cancelada para {mode}."
                status_text.color = ft.colors.RED_ACCENT_700
                page.update()
                return # Exit handler if cancelled

            if not input_file.lower().endswith('.xlsx'):
                 status_text.value = f"Error: El archivo seleccionado no es un archivo .xlsx válido."
                 status_text.color = ft.colors.RED_ACCENT_700
                 page.update()
                 return # Exit handler if invalid file type

            status_text.value = f"Leyendo y procesando datos para {mode} desde {os.path.basename(input_file)}..."
            status_text.color = ft.colors.BLUE_ACCENT_700
            page.update()

            # 2. Process data (using the function)
            try:
                df = pd.read_excel(input_file)

                # --- Check for required columns before processing ---
                required_cols = ['UNIDADES', 'NOMBRECLIENTE', 'TIPO_DE_DOCUMENTO',
                                 'IDENTIFICACION', 'PRIMER_APELLIDO', 'SEGUNDO_APELLIDO',
                                 'PRIMER_NOMBRE', 'OTROS_NOMBRES', 'MontoBruto', 'Descuento', 'IVA']
                if not all(col in df.columns for col in required_cols):
                    missing = [col for col in required_cols if col not in df.columns]
                    status_text.value = f"Error: El archivo Excel no contiene todas las columnas requeridas. Faltan: {missing}"
                    status_text.color = ft.colors.RED_ACCENT_700
                    page.update()
                    return # Exit handler if columns are missing

                processed_df = process_data(df, mode) # Call the processing function


            except pd.errors.EmptyDataError:
                status_text.value = f"Error: El archivo '{os.path.basename(input_file)}' está vacío."
                status_text.color = ft.colors.RED_ACCENT_700
                page.update()
                return # Exit handler if file is empty
            except Exception as e:
                status_text.value = f"Error durante la lectura/procesamiento: {e}"
                status_text.color = ft.colors.RED_ACCENT_700
                page.update()
                return # Exit handler on processing error


            # Handle cases where process_data returned no data but potentially headers
            if processed_df.empty:
                 if processed_df.columns.empty:
                    status_text.value = f"Procesado: No se generaron datos ni encabezados para guardar."
                    status_text.color = ft.colors.RED_ACCENT_700
                    page.update()
                    return # Exit handler if nothing to save
                 else:
                    status_text.value = f"Procesado: No se encontraron registros que cumplan el criterio. Seleccione carpeta para guardar archivo vacío con encabezados."
                    status_text.color = ft.colors.ORANGE_ACCENT_700
                    page.update()
                    # Continue to save empty file with headers


            else: # Data was processed and is not empty
                status_text.value = f"Procesado con éxito ({len(processed_df)} registros). Seleccione la carpeta de exportación para el reporte de {mode}..."
                status_text.color = ft.colors.GREEN_ACCENT_700
                page.update()


            # 3. Select output folder (Tkinter)
            output_folder = filedialog.askdirectory(
                title=f"Seleccionar Carpeta de Exportación ({mode})",
                parent=root # Attach to hidden root
            )

            if not output_folder:
                status_text.value = f"Selección de carpeta cancelada para {mode}."
                status_text.color = ft.colors.RED_ACCENT_700
                page.update()
                return # Exit handler if cancelled

            # 4. Save processed data
            output_filename = f'output_{mode}.xlsx'
            output_path = os.path.join(output_folder, output_filename)

            status_text.value = f"Guardando archivo en: {output_path}..."
            status_text.color = ft.colors.BLUE_GREY_400
            page.update()

            try:
                processed_df.to_excel(output_path, index=False) # index=False para no escribir el índice de pandas
                status_text.value = f"¡Reporte de {mode} generado y guardado exitosamente!"
                status_text.color = ft.colors.GREEN
            except Exception as e:
                status_text.value = f"Error al guardar el archivo: {e}"
                status_text.color = ft.colors.RED
            finally:
                # Always update page to show final status message
                 page.update()

        except Exception as e: # Catch any other unexpected errors in the process flow
            status_text.value = f"Ocurrió un error inesperado: {e}"
            status_text.color = ft.colors.RED_ACCENT_700
            page.update()

        finally:
            # Re-enable buttons after process finishes (either successfully or with error)
            btn_debito.disabled = False
            btn_credito.disabled = False
            page.update()
            # The UI stays on the same page, ready for the next action

    # --- Define Buttons (using the shared handler) ---
    btn_debito = ft.ElevatedButton(
        "Generar reporte Debito",
        on_click=lambda e: handle_generate_report('debito'), # Pass 'debito' mode
        width=280,
        height=50,
        icon=ft.icons.ARROW_UPWARD_ROUNDED # Icon suggestive of Debito
    )

    btn_credito = ft.ElevatedButton(
        "Generar reporte Credito",
        on_click=lambda e: handle_generate_report('credito'), # Pass 'credito' mode
        width=280,
        height=50,
        icon=ft.icons.ARROW_DOWNWARD_ROUNDED # Icon suggestive of Credito
    )

    # --- Add Controls to Page Layout ---
    page.add(
        ft.Container( # Use a container for styling and centering
             content=ft.Column(
                [
                    title,
                    ft.Container(height=20), # Spacer
                    btn_debito,
                    btn_credito,
                    ft.Container(height=30), # Spacer
                    status_text, # Area to display status messages
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=15, # Space between controls in the column
             ),
             padding=ft.padding.all(20),
             alignment=ft.alignment.center,
             width=page.window_width, # Ensure container uses available width
             height=page.window_height # Ensure container uses available height
        )
    )

    # Optional: Destroy Tkinter root when Flet app closes (needs more complex shutdown handling)
    # For this simple script, leaving it is generally fine, but for long-running apps, manage resource

# --- Ejecutar la Aplicación Flet ---
if __name__ == "__main__":
    ft.app(target=main)