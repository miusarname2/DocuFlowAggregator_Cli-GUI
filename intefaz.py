import flet as ft
import pandas as pd
import tkinter as tk
from tkinter import filedialog
import re
import os
import sys

# --- Funciones de Procesamiento de Datos ---

def clean_tipo_documento(tipo_doc_series):
    """Limpia la serie 'TIPO_DE_DOCUMENTO' eliminando números y espacios al inicio."""
    # Asegura que la serie es de tipo string antes de aplicar regex
    return tipo_doc_series.astype(str).str.replace(r'^\d+\s*', '', regex=True)

def process_data(df, mode):
    """
    Filtra, limpia, agrupa y agrega los datos basándose en el modo ('debito', 'credito', o 'split').
    Consolida nombres de cliente/consumidor final basándose en un patrón regex y una lista
    de nombres específicos. En modo 'split', divide la suma de MontoBruto en positivo y negativo.

    Args:
        df (pd.DataFrame): El DataFrame original con los datos.
        mode (str): 'debito' para UNIDADES > 0, 'credito' para UNIDADES < 0,
                    'split' para procesar todos y dividir MontoBruto.

    Returns:
        pd.DataFrame: Un DataFrame procesado y agrupado, o un DataFrame vacío con encabezados
                      si no hay datos que coincidan con el filtro/criterio.
        Raises:
            ValueError: Si falta el modo o si el modo es inválido o si faltan columnas requeridas.
            Exception: Para otros errores de procesamiento.
    """
    print(f"Iniciando procesamiento para '{mode}'...")

    # Definir las columnas requeridas en el DataFrame de entrada
    required_cols = ['UNIDADES', 'NOMBRECLIENTE', 'TIPO_DE_DOCUMENTO',
                     'IDENTIFICACION', 'PRIMER_APELLIDO', 'SEGUNDO_APELLIDO',
                     'PRIMER_NOMBRE', 'OTROS_NOMBRES', 'MontoBruto', 'Descuento', 'IVA']

    # Verificar que las columnas requeridas existen en el DataFrame de entrada
    if not all(col in df.columns for col in required_cols):
        missing = [col for col in required_cols if col not in df.columns]
        raise ValueError(f"Columnas requeridas faltantes en el archivo de entrada: {missing}")


    # --- Filtrado según el modo ---
    if mode == 'debito':
        print("Aplicando filtro: UNIDADES > 0")
        df_processed = df[df['UNIDADES'] > 0].copy()
        expected_final_columns = [
            'TIPO DE DOCUMENTO', 'IDENTIFICACION', 'NOMBRECLIENTE', 'PRIMER_APELLIDO',
            'SEGUNDO_APELLIDO', 'PRIMER_NOMBRE', 'OTROS_NOMBRES', 'MontoBruto',
            'Descuento', 'Iva'
        ]
        # Columnas a agrupar y agregar (para modo 'debito'/'credito')
        agg_dict_base = {
            'TIPO_DE_DOCUMENTO_CLEANED': 'first',
            'IDENTIFICACION': 'first',
            'PRIMER_APELLIDO': 'first',
            'SEGUNDO_APELLIDO': 'first',
            'PRIMER_NOMBRE': 'first',
            'OTROS_NOMBRES': 'first',
            'MontoBruto': 'sum',
            'Descuento': 'sum',
            'IVA': 'sum'
        }
        # Mapa de renombre (para modo 'debito'/'credito')
        rename_map_base = {
            'TIPO_DE_DOCUMENTO_CLEANED': 'TIPO DE DOCUMENTO',
            'IVA': 'Iva'
        }


    elif mode == 'credito':
        print("Aplicando filtro: UNIDADES < 0")
        df_processed = df[df['UNIDADES'] < 0].copy()
        expected_final_columns = [
            'TIPO DE DOCUMENTO', 'IDENTIFICACION', 'NOMBRECLIENTE', 'PRIMER_APELLIDO',
            'SEGUNDO_APELLIDO', 'PRIMER_NOMBRE', 'OTROS_NOMBRES', 'MontoBruto',
            'Descuento', 'Iva'
        ]
        # Columnas a agrupar y agregar (para modo 'debito'/'credito')
        agg_dict_base = {
            'TIPO_DE_DOCUMENTO_CLEANED': 'first',
            'IDENTIFICACION': 'first',
            'PRIMER_APELLIDO': 'first',
            'SEGUNDO_APELLIDO': 'first',
            'PRIMER_NOMBRE': 'first',
            'OTROS_NOMBRES': 'first',
            'MontoBruto': 'sum',
            'Descuento': 'sum',
            'IVA': 'sum'
        }
         # Mapa de renombre (para modo 'debito'/'credito')
        rename_map_base = {
            'TIPO_DE_DOCUMENTO_CLEANED': 'TIPO DE DOCUMENTO',
            'IVA': 'Iva'
        }


    elif mode == 'split':
        print("Procesando todos los registros para dividir MontoBruto.")
        df_processed = df.copy() # Procesar todas las filas
        expected_final_columns = [
            'TIPO DE DOCUMENTO', 'IDENTIFICACION', 'NOMBRECLIENTE', 'PRIMER_APELLIDO',
            'SEGUNDO_APELLIDO', 'PRIMER_NOMBRE', 'OTROS_NOMBRES',
            'MontoBruto Positivo', 'MontoBruto Negativo', # Nuevas columnas aquí
            'Descuento', 'Iva'
        ]
         # Columnas a agrupar y agregar (para modo 'split')
        # Creamos columnas temporales para los Montos
        # Aseguramos que MontoBruto es numérico antes de aplicar la lógica de positivo/negativo
        df_processed['MontoBruto'] = pd.to_numeric(df_processed['MontoBruto'], errors='coerce').fillna(0)

        df_processed['MontoBruto_Positivo'] = df_processed['MontoBruto'].apply(lambda x: x if x > 0 else 0)
        df_processed['MontoBruto_Negativo'] = df_processed['MontoBruto'].apply(lambda x: x if x < 0 else 0)

        agg_dict = {
            'TIPO_DE_DOCUMENTO_CLEANED': 'first',
            'IDENTIFICACION': 'first',
            'PRIMER_APELLIDO': 'first',
            'SEGUNDO_APELLIDO': 'first',
            'PRIMER_NOMBRE': 'first',
            'OTROS_NOMBRES': 'first',
            'MontoBruto_Positivo': 'sum', # Suma de positivos
            'MontoBruto_Negativo': 'sum', # Suma de negativos
            'Descuento': 'sum',
            'IVA': 'sum'
        }
        # Mapa de renombre (para modo 'split')
        rename_map = {
            'TIPO_DE_DOCUMENTO_CLEANED': 'TIPO DE DOCUMENTO',
            'MontoBruto_Positivo': 'MontoBruto Positivo', # Renombrar columna temporal
            'MontoBruto_Negativo': 'MontoBruto Negativo', # Renombrar columna temporal
            'IVA': 'Iva'
        }

    else:
        raise ValueError(f"Modo de procesamiento inválido especificado: '{mode}'. Use 'debito', 'credito' o 'split'.")


    if df_processed.empty:
        print(f"No se encontraron registros para procesar en modo '{mode}'.")
        # Devolver un DataFrame vacío pero con los encabezados esperados para el modo actual
        return pd.DataFrame(columns=expected_final_columns)

    print(f"Filas encontradas para procesar: {len(df_processed)}")

    # --- Pasos de Procesamiento (aplicados a df_processed) ---

    # *** MODIFICACIÓN: Consolidar nombres específicos y patrones de cliente/consumidor final ***

    # 1. Definir el patrón regex (existente)
    final_pattern_regex = r'(?i)(cliente|consumidor).*finall?'

    # 2. Definir la lista de nombres específicos a consolidar (CORREGIDO)
    # Convertimos la lista a mayúsculas para hacer la comparación insensible a mayúsculas/minúsculas
    specific_names_to_consolidate_upper = [
        "CLIENTE CLIENTE".upper(),
        "CLIENTE CONSUMIDOR CLIENTE CONSUMID CLIENTE CONSUMID".upper(), # La versión anterior (3 repeticiones)
        "CLIENTE CONSUMIDOR CLIENTE CONSUMID CLIENTE CONSUMID CLIENTE CONSUMID".upper(), # La versión CORREGIDA (4 repeticiones)
        "CLIENTE UNO".upper(),
        "CLIENTES VARIOS CLIENTES VARIOS".upper(),
        "CONSUMIDOR FINAL".upper() # Aseguramos que 'CONSUMIDOR FINAL' literal también se incluya
    ]

    # 3. Asegurar que la columna es de tipo string
    df_processed['NOMBRECLIENTE'] = df_processed['NOMBRECLIENTE'].astype(str)

    # 4. Crear máscara booleana para el patrón regex
    mask_regex_match = df_processed['NOMBRECLIENTE'].str.contains(final_pattern_regex, na=False)

    # 5. Crear máscara booleana para los nombres específicos (comparación insensible a mayúsculas/minúsculas)
    mask_exact_match = df_processed['NOMBRECLIENTE'].str.upper().isin(specific_names_to_consolidate_upper)

    # 6. Combinar las máscaras
    total_consolidation_mask = mask_regex_match | mask_exact_match

    # 7. Aplicar la consolidación
    df_processed.loc[total_consolidation_mask, 'NOMBRECLIENTE'] = 'CONSUMIDOR FINAL'
    print(f"Consolidación de 'CLIENTE FINAL'/'CONSUMIDOR FINAL' y nombres específicos aplicada.")

    # 8. Limpiar TIPO_DE_DOCUMENTO
    df_processed['TIPO_DE_DOCUMENTO_CLEANED'] = clean_tipo_documento(df_processed['TIPO_DE_DOCUMENTO'])
    print("Limpieza de TIPO_DE_DOCUMENTO aplicada.")

    # 9. Definir y aplicar diccionario de agregación basado en el modo
    if mode in ['debito', 'credito']:
         agg_dict = agg_dict_base
         rename_map = rename_map_base
    elif mode == 'split':
         agg_dict = agg_dict_split
         rename_map = rename_map_split

    print(f"Agrupando por NOMBRECLIENTE y aplicando agregación para modo '{mode}'...")
    df_grouped = df_processed.groupby('NOMBRECLIENTE', as_index=False).agg(agg_dict)
    print(f"Agrupación completada. Registros resultantes: {len(df_grouped)}")

    # 10. Renombrar columnas
    df_grouped = df_grouped.rename(columns=rename_map)
    print("Columnas renombradas.")

    # 11. Seleccionar y Reordenar columnas según la lista de salida deseada para el modo actual
    try:
        final_df = df_grouped[expected_final_columns]
        print("Columnas seleccionadas y reordenadas.")
    except KeyError as e:
        print(f"Error: Columna faltante después de la agregación y renombramiento para modo '{mode}': {e}.")
        print(f"Columnas esperadas: {expected_final_columns}")
        print(f"Columnas disponibles después de agrupar y renombrar: {df_grouped.columns.tolist()}")
        # Devolver un DataFrame vacío con headers esperados en caso de error
        return pd.DataFrame(columns=expected_final_columns)

    print(f"Procesamiento para '{mode}' finalizado exitosamente.")
    return final_df


# --- Interfaz Gráfica (Flet) ---

def main(page: ft.Page):
    page.title = "Generador de Reportes de Ventas"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.window_width = 550
    page.window_height = 550 # Increased height to fit the new button
    page.padding = 30
    page.theme_mode = ft.ThemeMode.LIGHT

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
    # This function will handle clicks from all buttons based on the 'mode' parameter
    def handle_generate_report(mode_type):
        # Map internal mode to display name and filename suffix
        mode_display_name = {
            'debito': 'Débito',
            'credito': 'Crédito',
            'split': 'Negativos y Positivos'
        }.get(mode_type, 'Desconocido')

        # Update status and disable buttons
        status_text.value = f"Seleccione el archivo Excel para el reporte de {mode_display_name}..."
        status_text.color = ft.colors.BLUE_ACCENT_700
        # Disable all buttons during processing
        btn_debito.disabled = True
        btn_credito.disabled = True
        btn_split.disabled = True # Disable the new button too
        page.update()

        processed_df = None # Variable to hold the result DataFrame
        input_file = None # Keep track of input file for status messages

        try:
            # 1. Select input file (Tkinter)
            input_file = filedialog.askopenfilename(
                title=f"Seleccionar Archivo de Datos ({mode_display_name})",
                filetypes=[("Excel files", "*.xlsx")],
                parent=root # Attach to hidden root
            )

            if not input_file:
                status_text.value = f"Selección de archivo cancelada para reporte de {mode_display_name}."
                status_text.color = ft.colors.RED_ACCENT_700
                page.update()
                return # Exit handler if cancelled

            if not input_file.lower().endswith('.xlsx'):
                 status_text.value = f"Error: El archivo seleccionado '{os.path.basename(input_file)}' no es un archivo .xlsx válido."
                 status_text.color = ft.colors.RED_ACCENT_700
                 page.update()
                 return # Exit handler if invalid file type

            status_text.value = f"Leyendo y procesando datos para reporte de {mode_display_name} desde {os.path.basename(input_file)}..."
            status_text.color = ft.colors.BLUE_ACCENT_700
            page.update()

            # 2. Read and Process data
            try:
                df = pd.read_excel(input_file)

                # Pass the mode_type ('debito', 'credito', 'split') directly to process_data
                processed_df = process_data(df, mode_type)

            except pd.errors.EmptyDataError:
                status_text.value = f"Error: El archivo '{os.path.basename(input_file)}' está vacío."
                status_text.color = ft.colors.RED_ACCENT_700
                page.update()
                return # Exit handler if file is empty
            except ValueError as ve: # Catch specific ValueError for missing columns or invalid mode
                 status_text.value = f"Error en datos o configuración: {ve}"
                 status_text.color = ft.colors.RED_ACCENT_700
                 page.update()
                 return # Exit handler on specific processing error
            except Exception as e:
                status_text.value = f"Error inesperado durante la lectura/procesamiento: {e}"
                status_text.color = ft.colors.RED_ACCENT_700
                page.update()
                return # Exit handler on general processing error


            # Handle cases where process_data returned no data but potentially headers
            if processed_df.empty:
                 if processed_df.columns.empty:
                    status_text.value = f"Procesado: No se generaron datos ni encabezados para guardar."
                    status_text.color = ft.colors.RED_ACCENT_700
                    page.update()
                    return # Exit handler if nothing to save
                 else:
                    status_text.value = f"Procesado: No se encontraron registros que cumplan el criterio para el reporte de {mode_display_name}. Seleccione carpeta para guardar archivo vacío con encabezados."
                    status_text.color = ft.colors.ORANGE_ACCENT_700
                    page.update()
                    # Continue to save empty file with headers


            else: # Data was processed and is not empty
                status_text.value = f"Procesado con éxito ({len(processed_df)} registros). Seleccione la carpeta de exportación para el reporte de {mode_display_name}..."
                status_text.color = ft.colors.GREEN_ACCENT_700
                page.update()


            # 3. Select output folder (Tkinter)
            output_folder = filedialog.askdirectory(
                title=f"Seleccionar Carpeta de Exportación ({mode_display_name})",
                parent=root # Attach to hidden root
            )

            if not output_folder:
                status_text.value = f"Selección de carpeta de exportación cancelada para reporte de {mode_display_name}."
                status_text.color = ft.colors.RED_ACCENT_700
                page.update()
                return # Exit handler if cancelled

            # 4. Save processed data
            # Determine output filename based on mode
            output_filename = {
                'debito': 'reporte_debito.xlsx',
                'credito': 'reporte_credito.xlsx',
                'split': 'reporte_negativos_positivos.xlsx'
            }.get(mode_type, 'reporte_desconocido.xlsx') # Default if mode is somehow wrong

            output_path = os.path.join(output_folder, output_filename)

            status_text.value = f"Guardando archivo en: {output_path}..."
            status_text.color = ft.colors.BLUE_GREY_400
            page.update()

            try:
                # Use ExcelWriter for potentially better handling of large files or future multiple sheets
                with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
                     processed_df.to_excel(writer, index=False, sheet_name='Reporte')

                status_text.value = f"¡Reporte de {mode_display_name} generado y guardado exitosamente en\n{output_path}!"
                status_text.color = ft.colors.GREEN

            except Exception as e:
                status_text.value = f"Error al guardar el archivo: {e}"
                status_text.color = ft.colors.RED
            finally:
                # Always update page to show final status message
                 page.update()

        except Exception as e: # Catch any other unexpected errors in the process flow
            status_text.value = f"Ocurrió un error inesperado en el flujo de la aplicación: {e}"
            status_text.color = ft.colors.RED_ACCENT_700
            # Also print to console for debugging
            import traceback
            traceback.print_exc()
            page.update()

        finally:
            # Re-enable buttons after process finishes (either successfully or with error)
            btn_debito.disabled = False
            btn_credito.disabled = False
            btn_split.disabled = False # Re-enable the new button
            page.update()


    # --- Define Buttons (using the shared handler) ---
    btn_debito = ft.ElevatedButton(
        "Generar reporte Debito",
        on_click=lambda e: handle_generate_report('debito'), # Pass 'debito' mode
        width=300, # Increased width slightly for potentially longer text
        height=50,
        icon=ft.icons.ARROW_UPWARD_ROUNDED # Icon suggestive of Debito
    )

    btn_credito = ft.ElevatedButton(
        "Generar reporte Credito",
        on_click=lambda e: handle_generate_report('credito'), # Pass 'credito' mode
        width=300, # Increased width slightly
        height=50,
        icon=ft.icons.ARROW_DOWNWARD_ROUNDED # Icon suggestive of Credito
    )

    # --- New Button for Split Report ---
    btn_split = ft.ElevatedButton(
        "Crear Informe Negativos y Positivos",
        on_click=lambda e: handle_generate_report('split'), # Pass 'split' mode
        width=300, # Consistent width
        height=50,
        icon=ft.icons.BALANCE # Icon suggestive of balancing/splitting
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
                    btn_split, # Add the new button here
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


# --- Ejecutar la Aplicación Flet ---
if __name__ == "__main__":
    # Add error handling for missing required libraries
    try:
        import flet as ft
        import pandas as pd
        import tkinter as tk
        from tkinter import filedialog
        import re
        import os
        import sys
        # Check for xlsxwriter, which is needed for pd.ExcelWriter
        import xlsxwriter
        import openpyxl # Also good practice for reading xlsx
    except ImportError as e:
        print(f"Error: Missing required library: {e}")
        print("Please install required libraries using pip:")
        print("pip install flet pandas openpyxl xlsxwriter")
        sys.exit(1) # Exit if libraries are missing


    ft.app(target=main)