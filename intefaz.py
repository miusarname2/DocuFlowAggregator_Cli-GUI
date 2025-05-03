import flet as ft
import pandas as pd
import tkinter as tk
from tkinter import filedialog
import re
import os
import sys
from functools import partial

# --- Dependency Check ---
try:
    import flet as ft
    import pandas as pd
    import tkinter as tk
    from tkinter import filedialog
    import re
    import os
    import sys
    # Check for xlsxwriter and openpyxl
    import xlsxwriter
    import openpyxl
except ImportError as e:
    print(f"Error: Falta una biblioteca requerida: {e}")
    print("Por favor, instale las bibliotecas necesarias usando pip:")
    print("pip install flet pandas openpyxl xlsxwriter")
    sys.exit(1)

# --- Funciones de Procesamiento de Datos (Síncronas) ---

def clean_tipo_documento(tipo_doc_series):
    """Limpia la serie 'TIPO_DE_DOCUMENTO' eliminando números y espacios al inicio."""
    # Asegura que la serie es de tipo string antes de aplicar regex
    return tipo_doc_series.astype(str).str.replace(r'^\d+\s*', '', regex=True)

def process_data_internal_sync(df_combined, mode):
    """
    Función interna SÍNCRONA que filtra, limpia, agrupa y agrega los datos.
    Opera sobre un DataFrame combinado.
    No realiza split ni resta de Descuento aquí.
    """
    print(f"[Proceso Datos] Iniciando procesamiento interno SÍNCRONO para '{mode}'...")

    required_cols = ['UNIDADES', 'NOMBRECLIENTE', 'TIPO_DE_DOCUMENTO',
                     'IDENTIFICACION', 'PRIMER_APELLIDO', 'SEGUNDO_APELLIDO',
                     'PRIMER_NOMBRE', 'OTROS_NOMBRES', 'MontoBruto', 'Descuento', 'IVA']

    if not all(col in df_combined.columns for col in required_cols):
        missing = [col for col in required_cols if col not in df_combined.columns]
        print(f"[Proceso Datos] Error de Columnas: Faltan las siguientes columnas requeridas: {missing}")
        # Create an empty structure to pass back for consistent handling
        intermediate_cols = ['NOMBRECLIENTE', 'IDENTIFICACION', 'TIPO DE DOCUMENTO',
                                 'PRIMER_APELLIDO', 'SEGUNDO_APELLIDO', 'PRIMER_NOMBRE',
                                 'OTROS_NOMBRES', 'MontoBruto', 'Descuento', 'Iva']
        empty_df_with_error = pd.DataFrame(columns=intermediate_cols)
        empty_df_with_error['ProcessingError'] = f"Columnas requeridas faltantes: {missing}"
        return empty_df_with_error # Return empty structure with error info

    df_filtered = pd.DataFrame()

    try:
        # --- Mode-Specific Filtering ---
        if mode == 'debito':
            print("[Proceso Datos] Aplicando filtro: UNIDADES > 0")
            df_filtered = df_combined[df_combined['UNIDADES'] > 0].copy()
        elif mode == 'credito':
            print("[Proceso Datos] Aplicando filtro: UNIDADES < 0")
            df_filtered = df_combined[df_combined['UNIDADES'] < 0].copy()
        elif mode == 'split':
            print("[Proceso Datos] Procesando todos los registros.")
            df_filtered = df_combined.copy()
        else:
            raise ValueError(f"[Proceso Datos] Modo de procesamiento interno inválido especificado: '{mode}'.")

        if df_filtered.empty:
            print(f"[Proceso Datos] No se encontraron registros que coincidan con el filtro ({mode}).")
            intermediate_cols = ['NOMBRECLIENTE', 'IDENTIFICACION', 'TIPO DE DOCUMENTO',
                                 'PRIMER_APELLIDO', 'SEGUNDO_APELLIDO', 'PRIMER_NOMBRE',
                                 'OTROS_NOMBRES', 'MontoBruto', 'Descuento', 'Iva']
            return pd.DataFrame(columns=intermediate_cols)


        print(f"[Proceso Datos] Filas encontradas para procesar después de filtrar ({mode}): {len(df_filtered)}")

        # 1. Consolidar nombres específicos y patrones
        final_pattern_regex = r'(?i)(cliente|consumidor).*finall?'
        specific_names_to_consolidate_upper = [
            "CLIENTE CLIENTE".upper(),
            "CLIENTE CONSUMIDOR CLIENTE CONSUMID CLIENTE CONSUMID".upper(),
            "CLIENTE CONSUMIDOR CLIENTE CONSUMID CLIENTE CONSUMID CLIENTE CONSUMID".upper(),
            "CLIENTE UNO".upper(),
            "CLIENTES VARIOS CLIENTES VARIOS".upper(),
            "CONSUMIDOR FINAL".upper()
        ]

        df_filtered['NOMBRECLIENTE'] = df_filtered['NOMBRECLIENTE'].astype(str)
        mask_regex_match = df_filtered['NOMBRECLIENTE'].str.contains(final_pattern_regex, na=False)
        mask_exact_match = df_filtered['NOMBRECLIENTE'].str.upper().isin(specific_names_to_consolidate_upper)
        total_consolidation_mask = mask_regex_match | mask_exact_match
        df_filtered.loc[total_consolidation_mask, 'NOMBRECLIENTE'] = 'CONSUMIDOR FINAL'
        print("[Proceso Datos] Consolidación de nombres aplicada.")

        # 2. Limpiar TIPO_DE_DOCUMENTO
        df_filtered['TIPO_DE_DOCUMENTO_CLEANED'] = clean_tipo_documento(df_filtered['TIPO_DE_DOCUMENTO'])
        print("[Proceso Datos] Limpieza de TIPO_DE_DOCUMENTO aplicada.")

        # --- Aggregation and Renaming ---
        group_keys = ['NOMBRECLIENTE', 'IDENTIFICACION']

        agg_dict = {
            'TIPO_DE_DOCUMENTO_CLEANED': 'first',
            'PRIMER_APELLIDO': 'first',
            'SEGUNDO_APELLIDO': 'first',
            'PRIMER_NOMBRE': 'first',
            'OTROS_NOMBRES': 'first',
            'MontoBruto': 'sum',
            'Descuento': 'sum',
            'IVA': 'sum'
        }

        for col_sum in ['MontoBruto', 'Descuento', 'IVA']:
            df_filtered[col_sum] = pd.to_numeric(df_filtered[col_sum], errors='coerce').fillna(0)

        print("[Proceso Datos] Agrupando por NOMBRECLIENTE e IDENTIFICACION...")
        df_grouped = df_filtered.groupby(group_keys, as_index=False).agg(agg_dict)
        print(f"[Proceso Datos] Agrupación completada. Registros resultantes: {len(df_grouped)}")

        rename_map = {
            'TIPO_DE_DOCUMENTO_CLEANED': 'TIPO DE DOCUMENTO',
            'IVA': 'Iva'
        }
        df_grouped = df_grouped.rename(columns=rename_map)
        print("[Proceso Datos] Columnas renombradas.")

        # --- Final Selection/Ordering of INTERMEDIATE Columns ---
        intermediate_cols_order = ['NOMBRECLIENTE', 'IDENTIFICACION', 'TIPO DE DOCUMENTO',
                                   'PRIMER_APELLIDO', 'SEGUNDO_APELLIDO', 'PRIMER_NOMBRE',
                                   'OTROS_NOMBRES', 'MontoBruto', 'Descuento', 'Iva']

        cols_to_select = [col for col in intermediate_cols_order if col in df_grouped.columns]
        final_df = df_grouped[cols_to_select].copy() # Use .copy() to avoid SettingWithCopyWarning

        # Add back missing intermediate columns as NA
        for col in intermediate_cols_order:
             if col not in final_df.columns:
                 final_df[col] = pd.NA # Use pandas' NA for missing values

        # Reorder to ensure consistent order
        final_df = final_df[intermediate_cols_order].copy()

    except ValueError as ve:
         print(f"[Proceso Datos] Error de validación o datos durante el procesamiento interno de '{mode}': {ve}")
         intermediate_cols = ['NOMBRECLIENTE', 'IDENTIFICACION', 'TIPO DE DOCUMENTO',
                                 'PRIMER_APELLIDO', 'SEGUNDO_APELLIDO', 'PRIMER_NOMBRE',
                                 'OTROS_NOMBRES', 'MontoBruto', 'Descuento', 'Iva']
         empty_df_with_error = pd.DataFrame(columns=intermediate_cols)
         empty_df_with_error['ProcessingError'] = str(ve)
         return empty_df_with_error

    except Exception as e:
         print(f"[Proceso Datos] Error inesperado durante el procesamiento interno de '{mode}': {e}")
         import traceback
         traceback.print_exc()
         intermediate_cols = ['NOMBRECLIENTE', 'IDENTIFICACION', 'TIPO DE DOCUMENTO',
                                 'PRIMER_APELLIDO', 'SEGUNDO_APELLIDO', 'PRIMER_NOMBRE',
                                 'OTROS_NOMBRES', 'MontoBruto', 'Descuento', 'Iva']
         empty_df_with_error = pd.DataFrame(columns=intermediate_cols)
         empty_df_with_error['ProcessingError'] = f"Unexpected error: {e}"
         return empty_df_with_error


    print(f"[Proceso Datos] Procesamiento interno SÍNCRONO para '{mode}' finalizado exitosamente.")
    return final_df

# --- Interfaz Gráfica (Flet Síncrona) ---

# Global state to pass info between dialog steps in synchronous flow
processing_state = {}

def main(page: ft.Page):
    page.title = "Generador de Reportes de Ventas"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.window_width = 600
    page.window_height = 650
    page.padding = 30
    page.theme_mode = ft.ThemeMode.LIGHT

    # --- Tkinter setup (hidden root for dialogs) ---
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True) # Ensure dialogs stay on top


    # --- UI Controls ---
    title = ft.Text(
        "Generador de Reportes de Ventas",
        size=28,
        weight=ft.FontWeight.BOLD,
        text_align=ft.TextAlign.CENTER,
        color=ft.colors.PRIMARY
    )
    subtitle = ft.Text(
         "Seleccione el tipo de reporte y cargue los archivos",
         size=16,
         text_align=ft.TextAlign.CENTER,
         color=ft.colors.BLACK87
    )

    status_text = ft.Text(
        "",
        size=14,
        color=ft.colors.BLACK54,
        text_align=ft.TextAlign.CENTER,
        selectable=True
    )
    status_container = ft.Container(
        status_text,
        alignment=ft.alignment.center,
        padding=ft.padding.symmetric(vertical=10),
        width=page.window_width * 0.85,
        height=100,
        border_radius=ft.border_radius.all(5),
        border=ft.border.all(1, ft.colors.BLACK12),
        bgcolor=ft.colors.BLACK12
    )

    # --- Helper Functions for UI State ---
    def disable_buttons():
        print("[UI Helper] Deshabilitando botones")
        btn_debito.disabled = True
        btn_credito.disabled = True
        btn_split.disabled = True
        page.update()

    def enable_buttons():
        print("[UI Helper] Habilitando botones")
        btn_debito.disabled = False
        btn_credito.disabled = False
        btn_split.disabled = False
        page.update()

    def update_status(message, color=ft.colors.BLACK54):
        print(f"[UI Status] {message}") # Print status to console as well
        status_text.value = message
        status_text.color = color
        page.update()

    def close_dialog(dialog):
        print("[UI Dialog] Cerrando diálogo")
        if page.dialog and page.dialog.open: # Check if a dialog is actually open
             page.dialog.open = False
             page.dialog = None # Nullify the reference
             page.update()

    # --- Synchronous Step-by-Step Handlers ---

    # Step 1: Start the process by asking for the number of files
    def on_report_button_click(e, mode_type):
        print(f"[Flow] Botón de reporte '{mode_type}' clickeado")
        update_status(f"Preparando reporte de {mode_display_names.get(mode_type, 'Desconocido')}...", ft.colors.BLUE_ACCENT_700)
        disable_buttons()
        processing_state['mode'] = mode_type # Store mode for later steps
        print('[Flow] Llamando a show_num_files_dialog')
        show_num_files_dialog(page, mode_type)


    # Step 2: Show dialog to ask for the number of files
    def show_num_files_dialog(page, mode_type):
        print('[Flow] show_num_files_dialog iniciado')
        num_input = ft.TextField(
            label="Número de archivos",
            value="1",
            keyboard_type=ft.KeyboardType.NUMBER,
             # CORRECT InputFilter syntax based on previous errors and 0.27.6 indications
            input_filter=ft.NumbersOnlyInputFilter(), # This form caused 'missing regex_string' earlier
                                                  # If *this exact line* causes an error on 0.27.6,
                                                  # the syntax might be `ft.InputFilter(True, r"[0-9]")`
                                                  # or ft.InputFilter(allow="0123456789"), but based on the *last*
                                                  # InputFilter error you reported, `ft.InputFilter(r"[0-9]")` was needed.
            width=150
        )
        # Store num_input in state to access its value later
        processing_state['num_input_control'] = num_input

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Cantidad de Archivos"),
            content=ft.Column([ft.Text("¿Cuántos archivos desea procesar?"), num_input], tight=True, spacing=15),
            actions=[
                # Partial is used to pass arguments to the handler function
                ft.TextButton("Cancelar", on_click=lambda e: handle_num_files_response(page, e, True)),
                ft.TextButton("Aceptar",  on_click=lambda e: handle_num_files_response(page, e, False)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            # on_dismiss fires if the user clicks outside the modal area
        )
        print('[Flow] Diálogo de cantidad de archivos creado. Mostrando...')
        page.dialog = dialog # Assign the dialog
        page.open(dialog)    # Tell Flet to open it
        page.update()         # Request UI update to show the dialog
        print('[Flow] Llamada a page.update() después de abrir diálogo.')


    # Step 3: Handle the response from the number of files dialog
    def handle_num_files_response(page,e, canceled):
        print('[Flow] handle_num_files_response iniciado')
        # Check if dialog is the one we expect before closing
        if page.dialog and isinstance(page.dialog.content, ft.Column) and isinstance(page.dialog.content.controls[1], ft.TextField) and page.dialog.content.controls[1] == processing_state.get('num_input_control'):
             close_dialog(page.dialog) # Close the dialog first
        else:
             print("[Flow] Advertencia: Dialogo inesperado cerrado.")
             close_dialog(page.dialog) # Close anyway to clear it


        if canceled:
            print('[Flow] Selección de número de archivos cancelada.')
            update_status(f"Selección de archivo cancelada.", ft.colors.RED_ACCENT_700)
            enable_buttons()
            processing_state.clear() # Clean up state
            return

        num_input_control = processing_state.get('num_input_control')
        if not num_input_control:
             print("[Flow] Error: Control de número de archivos no encontrado en estado.")
             update_status("Error interno: Control de número de archivos no encontrado.", ft.colors.RED_ACCENT_700)
             enable_buttons()
             processing_state.clear()
             return

        raw_num = num_input_control.value
        print(f"[Flow] Valor ingresado para número de archivos: '{raw_num}'")
        try:
            num_files = int(raw_num)
            if num_files <= 0:
                print(f"[Flow] Error: Número de archivos '{num_files}' no es positivo.")
                update_status("Error: El número de archivos debe ser un entero positivo.", ft.colors.RED_ACCENT_700)
                enable_buttons()
                processing_state.clear()
                return
        except ValueError:
            print(f"[Flow] Error: Valor ingresado '{raw_num}' no es un número entero.")
            update_status("Error: Entrada inválida para el número de archivos. Por favor, ingrese un número entero.", ft.colors.RED_ACCENT_700)
            enable_buttons()
            processing_state.clear()
            return

        print(f"[Flow] Número de archivos validado: {num_files}. Iniciando secuencia de selección.")
        processing_state['num_files_total'] = num_files
        processing_state['selected_files_list'] = []
        # Start the file selection sequence with the first file (index 0)
        select_file_sequence(page, 0)


    # Step 4: Sequence for selecting multiple files
    def select_file_sequence(page, file_index):
        num_files_total = processing_state['num_files_total']
        mode_type = processing_state['mode']
        mode_display_name = mode_display_names.get(mode_type, 'Desconocido')

        print(f"[Flow] Iniciando selección de archivo {file_index+1} de {num_files_total}")
        update_status(f"Seleccionando archivo {file_index+1} de {num_files_total} para reporte de {mode_display_name}...", ft.colors.BLUE_ACCENT_700)

        # This filedialog call WILL block the UI until user selects a file or cancels
        print("[Flow] Llamando a filedialog.askopenfilename (esto bloqueará la UI)")
        input_file = filedialog.askopenfilename(
             title=f"Seleccionar Archivo {file_index+1} de {num_files_total} ({mode_display_name})",
             filetypes=[("Excel files", "*.xlsx")],
             parent=root
        )
        print(f"[Flow] filedialog.askopenfilename retornó: {input_file}")

        if not input_file:
            print(f"[Flow] Selección de archivo {file_index+1} cancelada por el usuario.")
            update_status(f"Selección de archivo {file_index+1} cancelada. Proceso detenido.", ft.colors.RED_ACCENT_700)
            enable_buttons()
            processing_state.clear()
            return

        if not input_file.lower().endswith('.xlsx'):
            print(f"[Flow] Error: Archivo seleccionado '{os.path.basename(input_file)}' no es XLSX.")
            update_status(f"Error: El archivo seleccionado '{os.path.basename(input_file)}' no es un archivo .xlsx válido. Proceso detenido.", ft.colors.RED_ACCENT_700)
            enable_buttons()
            processing_state.clear()
            return

        print(f"[Flow] Archivo {file_index+1} seleccionado y validado: {input_file}")
        processing_state['selected_files_list'].append(input_file)

        # Check if more files need to be selected
        if file_index + 1 < num_files_total:
             print(f"[Flow] Quedan {num_files_total - (file_index + 1)} archivos por seleccionar. Continuando...")
             # Continue to the next file
             select_file_sequence(page, file_index + 1)
        else:
             print("[Flow] Todos los archivos seleccionados. Combinando y procesando.")
             # All files selected, proceed to combining and processing
             combine_and_process_files(page)


    # Step 5: Combine and process the selected files
    def combine_and_process_files(page):
        print('[Flow] combine_and_process_files iniciado')
        selected_files = processing_state['selected_files_list']
        mode_type = processing_state['mode']
        mode_display_name = mode_display_names.get(mode_type, 'Desconocido')

        update_status(f"Leyendo y combinando {len(selected_files)} archivo(s)...", ft.colors.BLUE_ACCENT_700)
        print(f"[Flow] Leyendo {len(selected_files)} archivos...")

        dataframes_list = []
        try:
            for i, file_path in enumerate(selected_files):
                 print(f"[Flow] Leyendo archivo {i+1}/{len(selected_files)}: {os.path.basename(file_path)}")
                 update_status(f"Leyendo archivo {i+1} de {len(selected_files)}:\n{os.path.basename(file_path)}...", ft.colors.BLUE_ACCENT_700)
                 # This read_excel call can block
                 df_single = pd.read_excel(file_path, engine='openpyxl')
                 if df_single.empty:
                      print(f"[Flow] Advertencia: Archivo '{os.path.basename(file_path)}' está vacío. Se omitirá.")
                      continue
                 dataframes_list.append(df_single)

            if not dataframes_list:
                 print("[Flow] Error: No se pudieron leer DataFrames válidos de los archivos seleccionados.")
                 update_status(f"Error: Todos los archivos seleccionados estaban vacíos o hubo un error de lectura.", ft.colors.RED_ACCENT_700)
                 enable_buttons()
                 processing_state.clear()
                 return

            print(f"[Flow] {len(dataframes_list)} DataFrames leídos exitosamente. Concatenando.")
            update_status(f"Combinando {len(dataframes_list)} archivo(s)...", ft.colors.BLUE_ACCENT_700)
            # This concat call can block
            combined_df = pd.concat(dataframes_list, ignore_index=True)
            print(f"[Flow] Archivos combinados. Filas totales: {len(combined_df)}")

            if combined_df.empty:
                print("[Flow] Error: DataFrame combinado está vacío.")
                update_status(f"Error: El DataFrame combinado está vacío después de leer los archivos.", ft.colors.RED_ACCENT_700)
                enable_buttons()
                processing_state.clear()
                return

        except Exception as e:
            print(f"[Flow] Error inesperado al leer o combinar archivos: {e}")
            update_status(f"Error inesperado al leer o combinar archivos:\n{e}", ft.colors.RED_ACCENT_700)
            import traceback
            traceback.print_exc()
            enable_buttons()
            processing_state.clear()
            return

        # Proceed to internal data processing
        print("[Flow] Llamando a process_combined_data")
        process_combined_data(page, combined_df)


    # Step 6: Run internal data processing and then decide next step (discount or save)
    def process_combined_data(page, combined_df):
        print('[Flow] process_combined_data iniciado')
        mode_type = processing_state['mode']
        mode_display_name = mode_display_names.get(mode_type, 'Desconocido')

        update_status(f"Procesando datos combinados para reporte de {mode_display_name}...", ft.colors.BLUE_ACCENT_700)
        print(f"[Flow] Llamando a process_data_internal_sync para modo '{mode_type}'. Esto puede bloquear.")

        try:
            # This call contains the heavy Pandas processing and can block
            processed_df = process_data_internal_sync(combined_df.copy(), mode_type)

            processing_state['processed_df'] = processed_df # Store the result
            print(f"[Flow] process_data_internal_sync finalizado. processed_df es vacío: {processed_df.empty}")


            # Check for processing errors (indicated by 'ProcessingError' column)
            if not processed_df.empty and 'ProcessingError' in processed_df.columns:
                 error_msg = processed_df['ProcessingError'].iloc[0]
                 print(f"[Flow] Error detectado en el DataFrame procesado: {error_msg}")
                 update_status(f"Error durante el procesamiento interno:\n{error_msg}", ft.colors.RED_ACCENT_700)
                 enable_buttons()
                 processing_state.clear()
                 return


            # If data is empty after processing/filtering
            if processed_df.empty:
                print("[Flow] processed_df está vacío después del procesamiento interno.")
                update_status(f"Procesamiento completado, pero no se encontraron registros que cumplieran los criterios para el reporte de {mode_display_name}.", ft.colors.ORANGE_ACCENT_700)
                print(f"DataFrame procesado está vacío. Columnas: {processed_df.columns.tolist()}")
                # Still proceed to save stage, it will save an empty file with headers
                print("[Flow] processed_df vacío. Procediendo directamente a guardar.")
                save_results(page, processed_df)
            else:
                 # If data is NOT empty, proceed with split (if needed) and ask about discount
                 print("[Flow] processed_df contiene datos. Aplicando lógica de split y descuento si es necesario.")
                 # --- Apply 'split' logic here before asking about discount ---
                 if mode_type == 'split':
                      print("[Flow] Modo es 'split'. Aplicando lógica de positivos/negativos.")
                      update_status("Aplicando lógica de positivos/negativos...", ft.colors.BLUE_GREY_400)
                       # Ensure MontoBruto exists and is numeric before splitting
                      if 'MontoBruto' in processed_df.columns:
                          processed_df['MontoBruto'] = pd.to_numeric(processed_df['MontoBruto'], errors='coerce').fillna(0)
                           # Create temporary columns for positive and negative MontoBruto based on the AGGREGATED MontoBruto
                          processed_df['MontoBruto Positivo'] = processed_df['MontoBruto'].apply(lambda x: x if x > 0 else 0)
                          processed_df['MontoBruto Negativo'] = processed_df['MontoBruto'].apply(lambda x: x if x < 0 else 0)
                           # Drop the original combined MontoBruto column now
                          processed_df = processed_df.drop(columns=['MontoBruto']).copy() # Use copy()
                          print("[Flow] Lógica de split aplicada.")
                      else:
                           print("[Flow] Advertencia: Columna 'MontoBruto' no encontrada para aplicar split.")

                 # Update state with the potentially modified DataFrame (after split)
                 processing_state['processed_df'] = processed_df

                 # Now ask about discount
                 print("[Flow] Llamando a show_subtract_discount_dialog")
                 show_subtract_discount_dialog(page)


        except ValueError as ve: # Catch ValueErrors specifically from process_data_internal_sync
             print(f"[Flow] ValueError durante el procesamiento interno: {ve}")
             update_status(f"Error de datos o formato en el archivo: {ve}", ft.colors.RED_ACCENT_700)
             enable_buttons()
             processing_state.clear()
        except Exception as e: # Catch other unexpected processing errors
            print(f"[Flow] Error inesperado durante el procesamiento interno: {e}")
            update_status(f"Error inesperado durante el procesamiento:\n{e}", ft.colors.RED_ACCENT_700)
            import traceback
            traceback.print_exc()
            enable_buttons()
            processing_state.clear()


    # Step 7: Show dialog asking about subtracting discount
    def show_subtract_discount_dialog(page):
         print('[Flow] show_subtract_discount_dialog iniciado')
         dialog = ft.AlertDialog(
             modal=True,
             title=ft.Text("Opciones de Procesamiento"),
             content=ft.Text("¿Desea restar el valor del 'Descuento' del 'MontoBruto' (o sus partes, si aplica)?"),
             actions=[
                 ft.TextButton("No", on_click=lambda e: handle_subtract_discount_response(page, e, False)),
                 ft.TextButton("Sí", on_click=lambda e: handle_subtract_discount_response(page, e, True)),
             ],
             actions_alignment=ft.MainAxisAlignment.END,
             on_dismiss=partial(handle_subtract_discount_response, page, subtract=False) # Default to No if dialog is dismissed
         )
         print('[Flow] Diálogo de descuento creado. Mostrando...')
         page.dialog = dialog # Assign the dialog
         page.open(dialog)    # Tell Flet to open it
         page.update()         # Request UI update to show the dialog
         print('[Flow] Llamada a page.update() después de abrir diálogo de descuento.')


    # Step 8: Handle response from discount dialog and apply discount if needed
    def handle_subtract_discount_response(page, e, subtract):
        print(f'[Flow] handle_subtract_discount_response iniciado. Restar descuento: {subtract}')
        # Check if dialog is the one we expect before closing
        if page.dialog and isinstance(page.dialog.content, ft.Text) and "Desea restar el valor" in page.dialog.content.value:
             close_dialog(page.dialog)
        else:
            print("[Flow] Advertencia: Dialogo inesperado cerrado desde handler de descuento.")
            close_dialog(page.dialog)


        processed_df = processing_state.get('processed_df')
        mode_type = processing_state.get('mode')

        if processed_df is None or mode_type is None:
             print("[Flow] Error interno: processed_df o mode_type no disponibles en estado.")
             update_status("Error interno: Datos de procesamiento no disponibles.", ft.colors.RED_ACCENT_700)
             enable_buttons()
             processing_state.clear()
             return

        if subtract is True:
             print("[Flow] Aplicando lógica de resta de Descuento.")
             update_status("Aplicando resta de Descuento...", ft.colors.BLUE_GREY_400)

             # Ensure 'Descuento' is numeric before subtraction
             # It should be numeric from process_data_internal_sync, but double-check
             processed_df['Descuento'] = pd.to_numeric(processed_df['Descuento'], errors='coerce').fillna(0).abs()

             if mode_type in ['debito', 'credito']:
                  if 'MontoBruto' in processed_df.columns:
                       processed_df['MontoBruto'] = processed_df['MontoBruto'] - processed_df['Descuento']
                       print("[Flow] Resta de descuento aplicada a MontoBruto.")
                  else:
                       print("[Flow] Advertencia: Columna 'MontoBruto' no encontrada para restar descuento en modo debito/credito.")
             elif mode_type == 'split':
                  if 'MontoBruto Positivo' in processed_df.columns:
                       processed_df['MontoBruto Positivo'] = processed_df['MontoBruto Positivo'] - processed_df['Descuento']
                       print("[Flow] Resta de descuento aplicada a MontoBruto Positivo.")
                  else:
                       print("[Flow] Advertencia: Columna 'MontoBruto Positivo' no encontrada para restar descuento en modo split.")
                  if 'MontoBruto Negativo' in processed_df.columns:
                       processed_df['MontoBruto Negativo'] = processed_df['MontoBruto Negativo'] - processed_df['Descuento']
                       print("[Flow] Resta de descuento aplicada a MontoBruto Negativo.")
                  else:
                       print("[Flow] Advertencia: Columna 'MontoBruto Negativo' no encontrada para restar descuento en modo split.")

             # Update the stored dataframe in state (even if no subtraction happened due to missing columns)
             processing_state['processed_df'] = processed_df
        else:
             print("[Flow] No se aplicará la resta de Descuento (usuario seleccionó No).")


        # Proceed to saving the results
        print("[Flow] Llamando a save_results")
        save_results(page, processing_state['processed_df'])


    # Step 9: Select output folder and save the file
    def save_results(page, final_df):
        print('[Flow] save_results iniciado')
        mode_type = processing_state.get('mode')
        mode_display_name = mode_display_names.get(mode_type, 'Desconocido')

        # Handle the case where final_df is the empty dataframe indicating processing error
        is_processing_error = not final_df.empty and 'ProcessingError' in final_df.columns
        if is_processing_error:
            print("[Flow] save_results detectó un error de procesamiento. Terminando flujo.")
            # Error message already shown, just clean up and enable buttons
            enable_buttons()
            processing_state.clear()
            return # Stop here if it's a fatal processing error structure

        # Define expected final columns based on mode BEFORE saving
        if mode_type in ['debito', 'credito']:
             expected_final_columns = [
                 'TIPO DE DOCUMENTO', 'IDENTIFICACION', 'NOMBRECLIENTE', 'PRIMER_APELLIDO',
                 'SEGUNDO_APELLIDO', 'PRIMER_NOMBRE', 'OTROS_NOMBRES', 'MontoBruto',
                 'Descuento', 'Iva'
             ]
        elif mode_type == 'split':
             expected_final_columns = [
                 'TIPO DE DOCUMENTO', 'IDENTIFICACION', 'NOMBRECLIENTE', 'PRIMER_APELLIDO',
                 'SEGUNDO_APELLIDO', 'PRIMER_NOMBRE', 'OTROS_NOMBRES',
                 'MontoBruto Positivo', 'MontoBruto Negativo',
                 'Descuento', 'Iva'
             ]
        else:
             # Should not happen, but fallback to actual columns
             print(f"[Flow] save_results: Modo desconocido '{mode_type}'. Usando columnas actuales.")
             expected_final_columns = final_df.columns.tolist()


        update_status(f"Seleccione la carpeta de exportación para el reporte de {mode_display_name}...", ft.colors.ORANGE_ACCENT_700 if final_df.empty else ft.colors.GREEN_ACCENT_700)
        print("[Flow] Llamando a filedialog.askdirectory (esto bloqueará la UI)")

        # This filedialog call WILL block the UI
        output_folder = filedialog.askdirectory(
             title=f"Seleccionar Carpeta de Exportación ({mode_display_name})",
             parent=root
        )
        print(f"[Flow] filedialog.askdirectory retornó: {output_folder}")


        if not output_folder:
            print("[Flow] Selección de carpeta de exportación cancelada.")
            update_status(f"Selección de carpeta de exportación cancelada para reporte de {mode_display_name}.", ft.colors.RED_ACCENT_700)
            enable_buttons()
            processing_state.clear()
            return

        output_filename = {
            'debito': 'reporte_debito.xlsx',
            'credito': 'reporte_credito.xlsx',
            'split': 'reporte_negativos_positivos.xlsx'
        }.get(mode_type, 'reporte_desconocido.xlsx')

        output_path = os.path.join(output_folder, output_filename)

        update_status(f"Guardando archivo en:\n{output_path}", ft.colors.BLUE_GREY_400)
        print(f"[Flow] Guardando archivo en: {output_path}. Esto puede bloquear.")

        try:
            os.makedirs(output_folder, exist_ok=True)

            # Select and reorder columns for the final output
            final_cols_present = [col for col in expected_final_columns if col in final_df.columns]
            # Ensure empty DF gets correct headers based on expected columns, not just present ones from the error structure
            df_to_save = final_df[final_cols_present].copy() if not final_df.empty else pd.DataFrame(columns=expected_final_columns)
            print(f"[Flow] DataFrame para guardar preparado. Columnas finales: {df_to_save.columns.tolist()}. Está vacío: {df_to_save.empty}")


            with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
                 # Pass df_to_save. If processed_df was empty, this will be empty with correct headers.
                 df_to_save.to_excel(writer, index=False, sheet_name='Reporte')
            print("[Flow] Archivo Excel guardado exitosamente.")


            if df_to_save.empty and final_df.empty:
                # Check if the *original* processed_df was empty (meaning no data filtered in)
                # not just if df_to_save became empty due to column selection (less likely)
                 update_status(f"¡Reporte de {mode_display_name} (vacío con encabezados) guardado exitosamente en\n{output_path}!", ft.colors.GREEN_700)
                 print("[Flow] Mensaje final: Guardado vacío.")
            else:
                 update_status(f"¡Reporte de {mode_display_name} generado y guardado exitosamente en\n{output_path}!", ft.colors.GREEN_700)
                 print("[Flow] Mensaje final: Guardado exitoso.")


        except Exception as e:
            print(f"[Flow] Error al guardar el archivo: {e}")
            update_status(f"Error al guardar el archivo:\n{e}", ft.colors.RED_700)
            import traceback
            traceback.print_exc()

        finally:
            print("[Flow] Proceso de guardado finalizado. Habilitando botones y limpiando estado.")
            enable_buttons()
            processing_state.clear() # Clean up state after finishing


    # Mapping for display names
    mode_display_names = {
        'debito': 'Débito',
        'credito': 'Crédito',
        'split': 'Negativos y Positivos'
    }

    # --- Define Buttons (calling the starting handler) ---
    btn_debito = ft.ElevatedButton(
        "Generar reporte Debito",
        on_click=partial(on_report_button_click, mode_type='debito'), # Start the sequence
        width=350,
        height=50,
        icon=ft.icons.ARROW_UPWARD_ROUNDED
    )

    btn_credito = ft.ElevatedButton(
        "Generar reporte Credito",
        on_click=partial(on_report_button_click, mode_type='credito'), # Start the sequence
        width=350,
        height=50,
        icon=ft.icons.ARROW_DOWNWARD_ROUNDED
    )

    btn_split = ft.ElevatedButton(
        "Crear Informe Negativos y Positivos",
        on_click=partial(on_report_button_click, mode_type='split'), # Start the sequence
        width=350,
        height=50,
        icon=ft.icons.BALANCE
    )


    # --- Add Controls to Page Layout ---
    page.add(
        ft.Container(
             content=ft.Column(
                 [
                     title,
                     subtitle,
                     ft.Container(height=20),
                     btn_debito,
                     btn_credito,
                     btn_split,
                     ft.Container(height=30),
                     status_container,
                 ],
                 horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                 spacing=15,
                 tight=True
             ),
             padding=ft.padding.all(20),
             alignment=ft.alignment.top_center,
             width=page.window_width,
             height=page.window_height
        )
    )

    # Initial state message
    update_status("Listo para comenzar. Seleccione una opción.", ft.colors.BLACK54)


# --- Run the Flet App (Synchronously) ---
if __name__ == "__main__":
    # Dependency check is at the top
    # Run the synchronous Flet app
    ft.app(target=main)