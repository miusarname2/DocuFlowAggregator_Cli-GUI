import flet as ft

import pandas as pd

import tkinter as tk # Used for file dialogs

from tkinter import filedialog # Used for file dialogs

import re

import os

import sys



# --- Dependency Check ---
# Add error handling for missing required libraries outside of the main loop
# This ensures a clear error message before Flet or Tkinter initializes fully
try:
    import flet as ft
    import pandas as pd
    import tkinter as tk
    from tkinter import filedialog
    import re
    import os
    import sys
    # Check for xlsxwriter and openpyxl, which are good dependencies for Excel handling
    import xlsxwriter # Used by pandas to_excel
    import openpyxl  # Used by pandas read_excel
except ImportError as e:
    print(f"Error: Falta una biblioteca requerida: {e}")
    print("Por favor, instale las bibliotecas necesarias usando pip:")
    print("pip install flet pandas openpyxl xlsxwriter")
    # Exit the program gracefully if essential libraries are missing
    sys.exit(1)

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
                      si no hay datos que coincidan con el filtro/criterio o si ocurre un error
                      en la selección de columnas.
    Raises:
        ValueError: Si falta el modo, si el modo es inválido, o si faltan columnas requeridas
                    en el DataFrame de entrada.
        Exception: Para otros errores de procesamiento no capturados específicamente.
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

    df_processed = None # Initialize df_processed variable
    final_df = pd.DataFrame() # Initialize final_df to an empty DataFrame

    try:
        # --- Mode-Specific Filtering, Column Preparation, Aggregation, Renaming, and Selection ---
        if mode == 'debito':
            print("Aplicando filtro: UNIDADES > 0")
            df_processed = df[df['UNIDADES'] > 0].copy() # Filter and create a copy

            expected_final_columns = [
                'TIPO DE DOCUMENTO', 'IDENTIFICACION', 'NOMBRECLIENTE', 'PRIMER_APELLIDO',
                'SEGUNDO_APELLIDO', 'PRIMER_NOMBRE', 'OTROS_NOMBRES', 'MontoBruto',
                'Descuento', 'Iva'
            ]

            # Check if data remains after filtering
            if df_processed.empty:
                print(f"No se encontraron registros con UNIDADES > 0.")
                # Return empty df with expected headers
                return pd.DataFrame(columns=expected_final_columns)

            # Define aggregation and rename maps for this mode
            agg_dict = {
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
            rename_map = {
                'TIPO_DE_DOCUMENTO_CLEANED': 'TIPO DE DOCUMENTO',
                'IVA': 'Iva'
            }


        elif mode == 'credito':
            print("Aplicando filtro: UNIDADES < 0")
            df_processed = df[df['UNIDADES'] < 0].copy() # Filter and create a copy

            expected_final_columns = [
                'TIPO DE DOCUMENTO', 'IDENTIFICACION', 'NOMBRECLIENTE', 'PRIMER_APELLIDO',
                'SEGUNDO_APELLIDO', 'PRIMER_NOMBRE', 'OTROS_NOMBRES', 'MontoBruto',
                'Descuento', 'Iva'
            ]

            # Check if data remains after filtering
            if df_processed.empty:
                 print(f"No se encontraron registros con UNIDADES < 0.")
                 return pd.DataFrame(columns=expected_final_columns)

            # Define aggregation and rename maps for this mode
            agg_dict = {
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
            rename_map = {
                'TIPO_DE_DOCUMENTO_CLEANED': 'TIPO DE DOCUMENTO',
                'IVA': 'Iva'
            }


        elif mode == 'split':
            print("Procesando todos los registros para dividir MontoBruto.")
            df_processed = df.copy() # Process all rows, create a copy

            expected_final_columns = [
                'TIPO DE DOCUMENTO', 'IDENTIFICACION', 'NOMBRECLIENTE', 'PRIMER_APELLIDO',
                'SEGUNDO_APELLIDO', 'PRIMER_NOMBRE', 'OTROS_NOMBRES',
                'MontoBruto Positivo', 'MontoBruto Negativo', # Split columns here
                'Descuento', 'Iva'
            ]

            # Check if data remains (should always have data unless input was empty)
            if df_processed.empty:
                print("El DataFrame de entrada está vacío para el modo 'split'.")
                return pd.DataFrame(columns=expected_final_columns)

            # Ensure MontoBruto is numeric BEFORE splitting
            df_processed['MontoBruto'] = pd.to_numeric(df_processed['MontoBruto'], errors='coerce').fillna(0)

            # Create temporary columns for positive and negative MontoBruto
            df_processed['MontoBruto_Positivo_temp'] = df_processed['MontoBruto'].apply(lambda x: x if x > 0 else 0)
            df_processed['MontoBruto_Negativo_temp'] = df_processed['MontoBruto'].apply(lambda x: x if x < 0 else 0)

            # Define aggregation and rename maps for this mode (using temporary column names)
            agg_dict = {
                'TIPO_DE_DOCUMENTO_CLEANED': 'first',
                'IDENTIFICACION': 'first',
                'PRIMER_APELLIDO': 'first',
                'SEGUNDO_APELLIDO': 'first',
                'PRIMER_NOMBRE': 'first',
                'OTROS_NOMBRES': 'first',
                'MontoBruto_Positivo_temp': 'sum', # Sum the temporary positive column
                'MontoBruto_Negativo_temp': 'sum', # Sum the temporary negative column
                'Descuento': 'sum',
                'IVA': 'sum'
            }
            rename_map = {
                'TIPO_DE_DOCUMENTO_CLEANED': 'TIPO DE DOCUMENTO',
                'MontoBruto_Positivo_temp': 'MontoBruto Positivo', # Rename the temporary column
                'MontoBruto_Negativo_temp': 'MontoBruto Negativo', # Rename the temporary column
                'IVA': 'Iva'
            }

        else:
            # This case should be caught by the initial validation, but good to have
            raise ValueError(f"Modo de procesamiento inválido especificado: '{mode}'. Use 'debito', 'credito' o 'split'.")

        # --- Common Processing Steps (applied to df_processed before aggregation) ---
        # These steps are now INSIDE each mode's block before the groupby call

        print(f"Filas encontradas para procesar después de filtrar ({mode}): {len(df_processed)}")

        # 1. Consolidar nombres específicos y patrones de cliente/consumidor final
        final_pattern_regex = r'(?i)(cliente|consumidor).*finall?'
        # Keep the corrected specific names list
        specific_names_to_consolidate_upper = [
            "CLIENTE CLIENTE".upper(),
            "CLIENTE CONSUMIDOR CLIENTE CONSUMID CLIENTE CONSUMID".upper(),
            "CLIENTE CONSUMIDOR CLIENTE CONSUMID CLIENTE CONSUMID CLIENTE CONSUMID".upper(), # Version with 4 repeats
            "CLIENTE UNO".upper(),
            "CLIENTES VARIOS CLIENTES VARIOS".upper(),
            "CONSUMIDOR FINAL".upper() # Ensure 'CONSUMIDOR FINAL' literal is included
        ]

        df_processed['NOMBRECLIENTE'] = df_processed['NOMBRECLIENTE'].astype(str) # Ensure string type
        mask_regex_match = df_processed['NOMBRECLIENTE'].str.contains(final_pattern_regex, na=False)
        mask_exact_match = df_processed['NOMBRECLIENTE'].str.upper().isin(specific_names_to_consolidate_upper)
        total_consolidation_mask = mask_regex_match | mask_exact_match
        df_processed.loc[total_consolidation_mask, 'NOMBRECLIENTE'] = 'CONSUMIDOR FINAL'
        print(f"Consolidación de 'CLIENTE FINAL'/'CONSUMIDOR FINAL' y nombres específicos aplicada.")

        # 2. Limpiar TIPO_DE_DOCUMENTO
        df_processed['TIPO_DE_DOCUMENTO_CLEANED'] = clean_tipo_documento(df_processed['TIPO_DE_DOCUMENTO'])
        print("Limpieza de TIPO_DE_DOCUMENTO aplicada.")

        # --- Perform Aggregation, Renaming, and Final Selection (Using maps defined IN the block) ---
        print(f"Agrupando por NOMBRECLIENTE y aplicando agregación para modo '{mode}'...")
        df_grouped = df_processed.groupby('NOMBRECLIENTE', as_index=False).agg(agg_dict)
        print(f"Agrupación completada. Registros resultantes: {len(df_grouped)}")

        df_grouped = df_grouped.rename(columns=rename_map)
        print("Columnas renombradas.")

        # 3. Select and Reorder columns based on the expected list for the current mode
        # This needs careful checking against the columns that *exist* in df_grouped *after* renaming.
        try:
            # Ensure all expected columns are in df_grouped *before* selecting
            missing_final_cols = [col for col in expected_final_columns if col not in df_grouped.columns]
            if missing_final_cols:
                 # This shouldn't happen if rename_map is correct, but good defense
                 raise KeyError(f"Columnas finales esperadas no encontradas después de renombrar: {missing_final_cols}")

            final_df = df_grouped[expected_final_columns]
            print("Columnas seleccionadas y reordenadas.")

        except KeyError as e:
            # This error handler is now specifically for the final column selection step
            print(f"Error seleccionando/reordenando columnas finales para modo '{mode}': {e}.")
            print(f"Columnas esperadas: {expected_final_columns}")
            print(f"Columnas disponibles después de agrupar y renombrar: {df_grouped.columns.tolist()}")
            # Return an empty DataFrame with the *attempted* expected headers in case of error
            return pd.DataFrame(columns=expected_final_columns)


    except ValueError as ve: # Catch specific ValueErrors (like missing columns in input)
         print(f"Error de validación o datos durante el procesamiento de '{mode}': {ve}")
         raise ve # Re-raise the ValueError so the UI handler can catch it

    except Exception as e: # Catch any other unexpected processing errors
         print(f"Error inesperado durante el procesamiento de '{mode}': {e}")
         # Log the traceback for debugging server-side (console)
         import traceback
         traceback.print_exc()
         raise e # Re-raise the general exception

    print(f"Procesamiento para '{mode}' finalizado exitosamente.")
    return final_df # Return the result from process_data


# --- Interfaz Gráfica (Flet) ---

def main(page: ft.Page):
    page.title = "Generador de Reportes de Ventas"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.window_width = 550
    page.window_height = 600 # Slightly more height might be nice
    page.padding = 30
    page.theme_mode = ft.ThemeMode.LIGHT

    # --- Tkinter setup (hidden root for dialogs) ---
    # Tkinter dialogs need a root window, but we don't want to show it
    root = tk.Tk()
    root.withdraw() # Hide the main Tkinter window
    # Prevent the hidden Tkinter window from blocking the main thread
    root.attributes('-topmost', True) # Keep dialogs on top

    # --- UI Controls ---
    title = ft.Text(
        "Generador de Reportes de Ventas",
        size=28,
        weight=ft.FontWeight.BOLD,
        text_align=ft.TextAlign.CENTER,
        color=ft.colors.PRIMARY
    )
    subtitle = ft.Text(
         "Seleccione el tipo de reporte a generar",
         size=16,
         text_align=ft.TextAlign.CENTER,
         color=ft.colors.BLACK87
    )


    status_text = ft.Text(
        "", # Initial empty message
        size=14,
        color=ft.colors.BLACK54, # Neutral color initially
        text_align=ft.TextAlign.CENTER,
        selectable=True # Allow copying error messages
    )
    status_container = ft.Container(
        status_text,
        alignment=ft.alignment.center,
        padding=ft.padding.symmetric(vertical=10),
        width=page.window_width * 0.8 # Give status text a bit more room
    )


    # --- Button Handler Function ---
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
        btn_split.disabled = True
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
                # Added explicit engine as a safeguard, though openpyxl is default for .xlsx
                df = pd.read_excel(input_file, engine='openpyxl')

                # Call the core processing function
                processed_df = process_data(df, mode_type)

            except pd.errors.EmptyDataError:
                status_text.value = f"Error: El archivo '{os.path.basename(input_file)}' está vacío."
                status_text.color = ft.colors.RED_ACCENT_700
                page.update()
                return # Exit handler if file is empty
            except ValueError as ve: # Catch specific ValueErrors raised by process_data
                status_text.value = f"Error de datos o formato en el archivo: {ve}"
                status_text.color = ft.colors.RED_ACCENT_700
                page.update()
                return # Exit handler on specific processing error
            except KeyError as ke: # Catch potential KeyErrors if columns issues persist
                 status_text.value = f"Error en el archivo: Columnas no encontradas o inesperadas: {ke}"
                 status_text.color = ft.colors.RED_ACCENT_700
                 page.update()
                 return
            except Exception as e: # Catch any other unexpected processing errors
                status_text.value = f"Error inesperado durante el procesamiento del archivo: {e}"
                status_text.color = ft.colors.RED_ACCENT_700
                # Print traceback to console for detailed debugging
                import traceback
                traceback.print_exc()
                page.update()
                return # Exit handler on general processing error


            # 3. Select output folder (Tkinter)
            # Always ask for output folder, even if df is empty, to save headers
            status_text.value = f"Procesado. Seleccione la carpeta de exportación para el reporte de {mode_display_name}..."
            status_text.color = ft.colors.ORANGE_ACCENT_700 if processed_df.empty else ft.colors.GREEN_ACCENT_700
            page.update()

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
            output_filename = {
                'debito': 'reporte_debito.xlsx',
                'credito': 'reporte_credito.xlsx',
                'split': 'reporte_negativos_positivos.xlsx'
            }.get(mode_type, 'reporte_desconocido.xlsx') # Default if mode is somehow wrong

            output_path = os.path.join(output_folder, output_filename)

            status_text.value = f"Guardando archivo en:\n{output_path}"
            status_text.color = ft.colors.BLUE_GREY_400
            page.update()

            try:
                # Use ExcelWriter, recommended for Pandas to Excel
                # Ensure directory exists - though askdirectory usually ensures this.
                os.makedirs(output_folder, exist_ok=True)
                with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
                     # Pass df, even if empty, to save headers
                     processed_df.to_excel(writer, index=False, sheet_name='Reporte')

                # Final success message based on if data was saved
                if processed_df.empty:
                     status_text.value = f"¡Reporte de {mode_display_name} (vacío con encabezados) guardado exitosamente en\n{output_path}!"
                else:
                     status_text.value = f"¡Reporte de {mode_display_name} generado y guardado exitosamente en\n{output_path}!"

                status_text.color = ft.colors.GREEN_700


            except Exception as e: # Catch saving errors
                status_text.value = f"Error al guardar el archivo:\n{e}"
                status_text.color = ft.colors.RED_700
                # Print traceback to console for detailed debugging
                import traceback
                traceback.print_exc()

            finally:
                # Always update page to show final status message
                page.update()


        except Exception as e: # Catch any other unexpected errors in the process flow (e.g., from file dialogs)
            status_text.value = f"Ocurrió un error inesperado en el flujo de la aplicación:\n{e}"
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
        width=350, # Give buttons a consistent, reasonable width
        height=50,
        icon=ft.icons.ARROW_UPWARD_ROUNDED
    )

    btn_credito = ft.ElevatedButton(
        "Generar reporte Credito",
        on_click=lambda e: handle_generate_report('credito'), # Pass 'credito' mode
        width=350,
        height=50,
        icon=ft.icons.ARROW_DOWNWARD_ROUNDED
    )

    btn_split = ft.ElevatedButton(
        "Crear Informe Negativos y Positivos",
        on_click=lambda e: handle_generate_report('split'), # Pass 'split' mode
        width=350,
        height=50,
        icon=ft.icons.BALANCE # Icon suggestive of balancing/splitting
    )


    # --- Add Controls to Page Layout ---
    page.add(
        ft.Container( # Use a container for styling and centering
             content=ft.Column(
                 [
                     title,
                     subtitle,
                     ft.Container(height=30), # Spacer
                     btn_debito,
                     btn_credito,
                     btn_split, # Add the new button here
                     ft.Container(height=40), # Spacer
                     status_container, # Use the container for status text
                 ],
                 horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                 spacing=15, # Space between controls in the column
                 tight=True # Keep column compact
             ),
             padding=ft.padding.all(20),
             alignment=ft.alignment.top_center, # Align column to top-center within container
             width=page.window_width, # Ensure container uses available width
             height=page.window_height # Ensure container uses available height
        )
    )

    # Initial state message
    status_text.value = "Listo para comenzar. Seleccione una opción."
    status_text.color = ft.colors.BLACK54
    page.update()


# --- Ejecutar la Aplicación Flet ---
if __name__ == "__main__":
    # The dependency check has been moved before this block
    ft.app(target=main)