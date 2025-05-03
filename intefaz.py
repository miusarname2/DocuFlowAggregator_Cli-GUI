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
    Aplica la lógica de split antes de agrupar si el modo es 'split'.
    """
    print(f"[Proceso Datos] Iniciando procesamiento interno SÍNCRONO para '{mode}'...")

    required_cols = ['UNIDADES', 'NOMBRECLIENTE', 'TIPO_DE_DOCUMENTO',
                     'IDENTIFICACION', 'PRIMER_APELLIDO', 'SEGUNDO_APELLIDO',
                     'PRIMER_NOMBRE', 'OTROS_NOMBRES', 'MontoBruto', 'Descuento', 'IVA']

    if not all(col in df_combined.columns for col in required_cols):
        missing = [col for col in required_cols if col not in df_combined.columns]
        print(f"[Proceso Datos] Error de Columnas: Faltan las siguientes columnas requeridas: {missing}")
        # Create an empty structure to pass back for consistent handling
        # Use potential final columns for the empty error DataFrame structure
        error_cols_structure = ['NOMBRECLIENTE', 'IDENTIFICACION', 'TIPO DE DOCUMENTO',
                                 'PRIMER_APELLIDO', 'SEGUNDO_APELLIDO', 'PRIMER_NOMBRE',
                                 'OTROS_NOMBRES', 'MontoBruto', 'Descuento', 'Iva', # Columns for non-split
                                 'MontoBruto Positivo', 'MontoBruto Negativo'] # Columns for split
        empty_df_with_error = pd.DataFrame(columns=[col for col in error_cols_structure if col in df_combined.columns or col in ['ProcessingError'] + ['MontoBruto Positivo', 'MontoBruto Negativo', 'MontoBruto']]) # Include relevant ones + split specific
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
            # Return an empty DataFrame with potential output columns based on mode
            if mode in ['debito', 'credito']:
                 empty_cols = ['NOMBRECLIENTE', 'IDENTIFICACION', 'TIPO DE DOCUMENTO',
                                 'PRIMER_APELLIDO', 'SEGUNDO_APELLIDO', 'PRIMER_NOMBRE',
                                 'OTROS_NOMBRES', 'MontoBruto', 'Descuento', 'Iva']
            elif mode == 'split':
                 empty_cols = ['NOMBRECLIENTE', 'IDENTIFICACION', 'TIPO DE DOCUMENTO',
                                 'PRIMER_APELLIDO', 'SEGUNDO_APELLIDO', 'PRIMER_NOMBRE',
                                 'OTROS_NOMBRES', 'MontoBruto Positivo', 'MontoBruto Negativo', 'Descuento', 'Iva']
            else:
                 empty_cols = [] # Should be caught by the ValueError above

            return pd.DataFrame(columns=empty_cols)


        print(f"[Proceso Datos] Filas encontradas para procesar después de filtrar ({mode}): {len(df_filtered)}")

        # Ensure numeric conversions happen early for relevant columns
        for col_sum in ['UNIDADES', 'MontoBruto', 'Descuento', 'IVA']:
            if col_sum in df_filtered.columns:
                 df_filtered[col_sum] = pd.to_numeric(df_filtered[col_sum], errors='coerce').fillna(0)
        print("[Proceso Datos] Conversión a numérico aplicada.")


        # --- Apply Split Logic *Before* Grouping (for split mode only) ---
        # Initialize split columns for all modes to avoid KeyError during aggregation definition
        df_filtered['MontoBruto Positivo_Temp'] = 0.0
        df_filtered['MontoBruto Negativo_Temp'] = 0.0

        if mode == 'split':
            print("[Proceso Datos] Aplicando split de MontoBruto *antes* de agrupar para modo 'split'.")
            # Populate the positive/negative columns based on ORIGINAL row MontoBruto
            # Only do this if MontoBruto column actually exists
            if 'MontoBruto' in df_filtered.columns:
                df_filtered['MontoBruto Positivo_Temp'] = df_filtered['MontoBruto'].apply(lambda x: x if x > 0 else 0)
                df_filtered['MontoBruto Negativo_Temp'] = df_filtered['MontoBruto'].apply(lambda x: x if x < 0 else 0)
                # Drop the original MontoBruto column if it's not needed in final output for 'split'
                # We need it for debito/credito, so drop conditionally after potential split logic
                # df_filtered = df_filtered.drop(columns=['MontoBruto'], errors='ignore').copy() # Don't drop yet, handle in aggregation/selection
            else:
                 print("[Proceso Datos] Advertencia: Columna 'MontoBruto' no encontrada para aplicar split en modo 'split'.")


        # 1. Consolidar nombres específicos y patrones (Apply AFTER filtering, BEFORE grouping)
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

        # 2. Limpiar TIPO_DE_DOCUMENTO (Apply AFTER filtering, BEFORE grouping)
        df_filtered['TIPO_DE_DOCUMENTO_CLEANED'] = clean_tipo_documento(df_filtered['TIPO_DE_DOCUMENTO'])
        print("[Proceso Datos] Limpieza de TIPO_DE_DOCUMENTO aplicada.")


        # --- Aggregation Definition (Conditional based on mode) ---
        group_keys = ['NOMBRECLIENTE', 'IDENTIFICACION'] # Group by name and ID for all modes

        # Base aggregation dictionary for identity/name columns
        agg_dict = {
            'TIPO_DE_DOCUMENTO_CLEANED': 'first',
            'PRIMER_APELLIDO': 'first',
            'SEGUNDO_APELLIDO': 'first',
            'PRIMER_NOMBRE': 'first',
            'OTROS_NOMBRES': 'first',
            'Descuento': 'sum',
            'IVA': 'sum'
        }

        # Add MontoBruto aggregation based on mode
        if mode == 'split':
            # For split, sum the new temporary positive/negative columns
            agg_dict['MontoBruto Positivo_Temp'] = 'sum'
            agg_dict['MontoBruto Negativo_Temp'] = 'sum'
        else: # 'debito' or 'credito' modes
            # For other modes, sum the original MontoBruto
            agg_dict['MontoBruto'] = 'sum'

        print("[Proceso Datos] Agrupando por NOMBRECLIENTE e IDENTIFICACION...")
        # Ensure all columns in agg_dict and group_keys are actually in df_filtered before grouping
        valid_agg_dict = {col: agg_func for col, agg_func in agg_dict.items() if col in df_filtered.columns}
        valid_group_keys = [key for key in group_keys if key in df_filtered.columns]

        if not valid_group_keys:
             print("[Proceso Datos] Error: Columnas de agrupación (NOMBRECLIENTE, IDENTIFICACION) no encontradas.")
             error_cols_structure = ['NOMBRECLIENTE', 'IDENTIFICACION', 'TIPO DE DOCUMENTO',
                                 'PRIMER_APELLIDO', 'SEGUNDO_APELLIDO', 'PRIMER_NOMBRE',
                                 'OTROS_NOMBRES', 'MontoBruto', 'Descuento', 'Iva',
                                 'MontoBruto Positivo', 'MontoBruto Negativo']
             empty_df_with_error = pd.DataFrame(columns=error_cols_structure)
             empty_df_with_error['ProcessingError'] = "Columnas de agrupación (NOMBRECLIENTE, IDENTIFICACION) faltantes."
             return empty_df_with_error


        df_grouped = df_filtered.groupby(valid_group_keys, as_index=False).agg(valid_agg_dict)
        print(f"[Proceso Datos] Agrupación completada. Registros resultantes: {len(df_grouped)}")

        # --- Renaming ---
        rename_map = {
            'TIPO_DE_DOCUMENTO_CLEANED': 'TIPO DE DOCUMENTO',
            'IVA': 'Iva',
            'MontoBruto Positivo_Temp': 'MontoBruto Positivo', # Rename temp columns to final names
            'MontoBruto Negativo_Temp': 'MontoBruto Negativo'
        }
        # Apply renaming, ignoring keys that are not in the grouped df columns
        df_grouped = df_grouped.rename(columns={k:v for k,v in rename_map.items() if k in df_grouped.columns})
        print("[Proceso Datos] Columnas renombradas.")


        # --- Final Column Selection/Ordering (Conditional based on mode) ---
        if mode in ['debito', 'credito']:
             final_cols_order = [
                 'TIPO DE DOCUMENTO', 'IDENTIFICACION', 'NOMBRECLIENTE', 'PRIMER_APELLIDO',
                 'SEGUNDO_APELLIDO', 'PRIMER_NOMBRE', 'OTROS_NOMBRES', 'MontoBruto',
                 'Descuento', 'Iva'
             ]
        elif mode == 'split':
             final_cols_order = [
                 'TIPO DE DOCUMENTO', 'IDENTIFICACION', 'NOMBRECLIENTE', 'PRIMER_APELLIDO',
                 'SEGUNDO_APELLIDO', 'PRIMER_NOMBRE', 'OTROS_NOMBRES',
                 'MontoBruto Positivo', 'MontoBruto Negativo', # Use the renamed columns
                 'Descuento', 'Iva'
             ]
        else:
             # Fallback, should not happen due to initial check
             print(f"[Proceso Datos] Advertencia: Modo desconocido '{mode}' para definir columnas finales.")
             final_cols_order = df_grouped.columns.tolist()

        # Select and reorder, adding missing columns as NA
        final_df = pd.DataFrame() # Start with an empty df for safety

        # Add columns that are in the order list and the grouped df
        cols_to_select_present = [col for col in final_cols_order if col in df_grouped.columns]
        final_df = df_grouped[cols_to_select_present].copy()

        # Add columns that are in the order list but NOT in the grouped df, filling with NA
        # This ensures the structure is correct even if some columns are missing (e.g., all debit/credit are 0)
        for col in final_cols_order:
             if col not in final_df.columns:
                 # Decide what default value makes sense. NA is often good, 0 might be better for numeric columns.
                 # Let's use 0 for the MontoBruto/Descuento/Iva columns if they were expected but missing after grouping.
                 if col in ['MontoBruto', 'MontoBruto Positivo', 'MontoBruto Negativo', 'Descuento', 'Iva']:
                      final_df[col] = 0.0
                 else:
                     final_df[col] = pd.NA


        # Ensure final order
        final_df = final_df[final_cols_order].copy()

        # Ensure numeric columns have float type for consistency, even if they were added as 0
        numeric_cols_final = ['MontoBruto', 'MontoBruto Positivo', 'MontoBruto Negativo', 'Descuento', 'Iva']
        for col in numeric_cols_final:
             if col in final_df.columns:
                  final_df[col] = pd.to_numeric(final_df[col], errors='coerce').fillna(0.0)


    except ValueError as ve:
         print(f"[Proceso Datos] Error de validación o datos durante el procesamiento interno de '{mode}': {ve}")
         error_cols_structure = ['NOMBRECLIENTE', 'IDENTIFICACION', 'TIPO DE DOCUMENTO',
                                 'PRIMER_APELLIDO', 'SEGUNDO_APELLIDO', 'PRIMER_NOMBRE',
                                 'OTROS_NOMBRES', 'MontoBruto', 'Descuento', 'Iva',
                                 'MontoBruto Positivo', 'MontoBruto Negativo']
         empty_df_with_error = pd.DataFrame(columns=error_cols_structure)
         empty_df_with_error['ProcessingError'] = str(ve)
         return empty_df_with_error

    except Exception as e:
         print(f"[Proceso Datos] Error inesperado durante el procesamiento interno de '{mode}': {e}")
         import traceback
         traceback.print_exc()
         error_cols_structure = ['NOMBRECLIENTE', 'IDENTIFICACION', 'TIPO DE DOCUMENTO',
                                 'PRIMER_APELLIDO', 'SEGUNDO_APELLIDO', 'PRIMER_NOMBRE',
                                 'OTROS_NOMBRES', 'MontoBruto', 'Descuento', 'Iva',
                                 'MontoBruto Positivo', 'MontoBruto Negativo']
         empty_df_with_error = pd.DataFrame(columns=error_cols_structure)
         empty_df_with_error['ProcessingError'] = f"Unexpected error: {e}"
         return empty_df_with_error


    print(f"[Proceso Datos] Procesamiento interno SÍNCRONO para '{mode}' finalizado exitosamente.")
    return final_df

# --- Interfaz Gráfica (Flet Síncrona) ---
# Resto del código de la interfaz gráfica (main, dialogs, handlers) permanece igual
# porque ya maneja la posibilidad de que el DataFrame procesado tenga
# las columnas 'MontoBruto Positivo' y 'MontoBruto Negativo' para el modo 'split'
# y 'MontoBruto' para los otros modos.

# Global state to pass info between dialog steps in synchronous flow
processing_state = {}
license_dialog = None

def open_license_dialog(e):
    """Abre el diálogo de licencia usando la página del evento."""
    dlg = license_dialog
    if dlg:
        e.page.dialog = dlg
        e.page.open(dlg)
        e.page.update()

def close_license_dialog(e):
    """Cierra el diálogo actual en la página del evento."""
    if e.page.dialog and e.page.dialog.open:
        e.page.dialog.open = False
        e.page.dialog = None
        e.page.update()

def main(page: ft.Page):
    global license_dialog
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

    license_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Licencia MIT"),
            content=ft.Text(
            "🔒 Licencia MIT / MIT License / MIT许可协议\n\n"
            "🌐 Español:\n"
            "Esta aplicación se distribuye bajo la licencia MIT, que otorga libertad total para usar, copiar, modificar, fusionar, publicar, distribuir, sublicenciar y/o vender copias del software. "
            "Únicamente se requiere conservar este aviso de licencia en todas las copias o partes sustanciales del software.\n"
            "Para más información sobre la licencia, consulte: https://github.com/miusarname2/DocuFlowAggregator_Cli-GUI/blob/master/LICENSE\n\n"

            "🌐 English:\n"
            "This application is distributed under the MIT License, which grants full permission to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the software. "
            "The only requirement is to retain this license notice in all copies or substantial portions of the software.\n"
            "For more information about the license, please visit: https://github.com/miusarname2/DocuFlowAggregator_Cli-GUI/blob/master/LICENSE\n\n"

            "🌐 中文（简体）:\n"
            "本应用程序依据 MIT 许可协议发布，您可以自由使用、复制、修改、合并、出版、分发、再授权和/或销售本软件的副本。"
            "唯一的要求是在所有副本或实质性部分中保留本许可声明。\n"
            "有关许可证的更多信息，请访问：https://github.com/miusarname2/DocuFlowAggregator_Cli-GUI/blob/master/LICENSE"
        ),
                    actions=[ft.TextButton("Cerrar", on_click=close_license_dialog)],
            actions_alignment=ft.MainAxisAlignment.END
        )
    
    # Botón Licencia
    license_button = ft.TextButton(
        "Licencia y Términos de Uso",
        on_click=open_license_dialog
    )


    # --- UI Controls ---
    header = ft.Row([
        ft.Text("Generador de Reportes de Ventas", size=28, weight=ft.FontWeight.BOLD),
        license_button
    ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        width=page.window_width * 0.85
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
                # Pass the empty processed_df to save_results - it will generate the correct headers
                save_results(page, processed_df)
            else:
                 # If data is NOT empty, ask about discount
                 print("[Flow] processed_df contiene datos. Procediendo a preguntar sobre descuento.")
                 # The split logic is now inside process_data_internal_sync *before* grouping for 'split' mode.
                 # So we just need to ask about discount and then save.
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
         # Use the correct wording based on the potential presence of split columns
         mode_type = processing_state.get('mode', '')
         discount_question = "¿Desea restar el valor del 'Descuento' del 'MontoBruto'?"
         if mode_type == 'split':
              discount_question = "¿Desea restar el valor del 'Descuento' de los 'MontoBruto Positivo' y 'MontoBruto Negativo'?"

         dialog = ft.AlertDialog(
             modal=True,
             title=ft.Text("Opciones de Procesamiento"),
             content=ft.Text(discount_question),
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
        # Check based on a keyword in the content text
        dialog_content_text = page.dialog.content.value if page.dialog and page.dialog.content else ""
        if "Desea restar el valor del 'Descuento'" in dialog_content_text:
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

        # Ensure Descuento is numeric and positive for subtraction
        if 'Descuento' in processed_df.columns:
             processed_df['Descuento'] = pd.to_numeric(processed_df['Descuento'], errors='coerce').fillna(0).abs()
        else:
             print("[Flow] Advertencia: Columna 'Descuento' no encontrada para restar.")
             processed_df['Descuento'] = 0.0 # Add as 0 if missing to avoid errors

        if subtract is True:
             print("[Flow] Aplicando lógica de resta de Descuento.")
             update_status("Aplicando resta de Descuento...", ft.colors.BLUE_GREY_400)

             if mode_type in ['debito', 'credito']:
                  if 'MontoBruto' in processed_df.columns:
                       processed_df['MontoBruto'] = processed_df['MontoBruto'] - processed_df['Descuento']
                       print("[Flow] Resta de descuento aplicada a MontoBruto.")
                  else:
                       print("[Flow] Advertencia: Columna 'MontoBruto' no encontrada para restar descuento en modo debito/credito.")
             elif mode_type == 'split':
                  # Apply subtraction to both positive and negative columns if they exist
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

             # The Discount column itself should probably remain as the original discount value,
             # not become 0 after subtraction, unless the requirement is to zero it out.
             # Assuming it should remain, no change needed to processed_df['Descuento'] here.
             # If it *should* be zeroed out, add: processed_df['Descuento'] = 0.0

             # Update the stored dataframe in state
             processing_state['processed_df'] = processed_df # processed_df is already modified in place

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
                 'MontoBruto Positivo', 'MontoBruto Negativo', # Use the actual column names from processing
                 'Descuento', 'Iva'
             ]
        else:
             # Should not happen, but fallback to actual columns if available, otherwise empty list
             print(f"[Flow] save_results: Modo desconocido '{mode_type}'. Usando columnas actuales.")
             expected_final_columns = final_df.columns.tolist() if not final_df.empty else []


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
            # Use expected_final_columns for structure, even if df is empty
            df_to_save = pd.DataFrame(columns=expected_final_columns)

            if not final_df.empty:
                 # Copy data for columns that are in both the expected list and the processed df
                 for col in expected_final_columns:
                     if col in final_df.columns:
                         df_to_save[col] = final_df[col]
                     # If col is in expected but not in final_df, it was created as 0.0 or pd.NA
                     # by process_data_internal_sync, so it's already in final_df structure
                     # unless final_df was an error DF. The error DF case is handled.

                 # Ensure numeric columns are indeed numeric before saving
                 numeric_cols_save = ['MontoBruto', 'MontoBruto Positivo', 'MontoBruto Negativo', 'Descuento', 'Iva']
                 for col in numeric_cols_save:
                     if col in df_to_save.columns:
                          df_to_save[col] = pd.to_numeric(df_to_save[col], errors='coerce').fillna(0.0)


            print(f"[Flow] DataFrame para guardar preparado. Columnas finales: {df_to_save.columns.tolist()}. Está vacío: {df_to_save.empty}")


            with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
                 # Pass df_to_save. It will have the correct structure based on expected_final_columns
                 df_to_save.to_excel(writer, index=False, sheet_name='Reporte')
            print("[Flow] Archivo Excel guardado exitosamente.")


            # Check if the resulting dataframe to be saved was empty
            if df_to_save.empty:
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
                     header,
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