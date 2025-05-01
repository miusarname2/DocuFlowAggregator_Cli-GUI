import pandas as pd
import sys # Para salir del script en caso de error
import re  # Para usar expresiones regulares en la limpieza y matching
import os  # Para construir rutas de archivo

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
    print(f"\nIniciando procesamiento para '{mode}'...")

    # Definir las columnas requeridas en el DataFrame de entrada
    required_cols = ['UNIDADES', 'NOMBRECLIENTE', 'TIPO_DE_DOCUMENTO',
                     'IDENTIFICACION', 'PRIMER_APELLIDO', 'SEGUNDO_APELLIDO',
                     'PRIMER_NOMBRE', 'OTROS_NOMBRES', 'MontoBruto', 'Descuento', 'IVA']

    # Verificar que las columnas requeridas existen en el DataFrame de entrada
    if not all(col in df.columns for col in required_cols):
        missing = [col for col in required_cols if col not in df.columns]
        # En lugar de imprimir y retornar None, lanzamos una excepción que la parte principal puede capturar
        raise ValueError(f"Columnas requeridas faltantes en el archivo de entrada: {missing}")


    # --- Filtrado según el modo y definición de estructuras de procesamiento ---
    if mode == 'debito':
        print("Aplicando filtro: UNIDADES > 0")
        df_processed = df[df['UNIDADES'] > 0].copy()
        expected_final_columns = [
            'TIPO DE DOCUMENTO', 'IDENTIFICACION', 'NOMBRECLIENTE', 'PRIMER_APELLIDO',
            'SEGUNDO_APELLIDO', 'PRIMER_NOMBRE', 'OTROS_NOMBRES', 'MontoBruto',
            'Descuento', 'Iva'
        ]
        # Columnas a agrupar y agregar (para modo 'debito'/'credito')
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
        # Mapa de renombre (para modo 'debito'/'credito')
        rename_map = {
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
         # Mapa de renombre (para modo 'debito'/'credito')
        rename_map = {
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
        # Coerce errors to NaN, then fill NaNs with 0 if desired, or handle appropriately
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
        # Esto no debería alcanzarse si la validación del menú funciona correctamente,
        # pero lo mantenemos para robustez.
        print(f"Error interno: Modo de procesamiento desconocido '{mode}'.")
        # Lanzar una excepción en lugar de retornar None para manejo de errores más claro
        raise ValueError(f"Modo de procesamiento inválido especificado: '{mode}'. Use 'debito', 'credito' o 'split'.")


    if df_processed.empty:
        print(f"No se encontraron registros relevantes para procesar en modo '{mode}'.")
        # Devolver un DataFrame vacío pero con los encabezados esperados para el modo actual
        return pd.DataFrame(columns=expected_final_columns)

    print(f"Filas encontradas para procesar: {len(df_processed)}")

    # --- Pasos de Procesamiento (aplicados a df_processed) ---

    # *** Consolidar nombres específicos y patrones de cliente/consumidor final ***

    # 1. Definir el patrón regex
    final_pattern_regex = r'(?i)(cliente|consumidor).*finall?'

    # 2. Definir la lista de nombres específicos a consolidar (NUEVO)
    # Convertimos la lista a mayúsculas para hacer la comparación insensible a mayúsculas/minúsculas
    specific_names_to_consolidate_upper = [
        "CLIENTE CLIENTE".upper(),
        "CLIENTE CONSUMIDOR CLIENTE CONSUMID CLIENTE CONSUMID".upper(),
        "CLIENTE UNO".upper(),
        "CLIENTES VARIOS CLIENTES VARIOS".upper(),
        "CONSUMIDOR FINAL".upper()
    ]

    # 3. Asegurar que la columna NOMBRECLIENTE es de tipo string
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

    # 8. Limpiar TIPO_DE_DOCUMENTO (aplicado después de la consolidación de nombre)
    df_processed['TIPO_DE_DOCUMENTO_CLEANED'] = clean_tipo_documento(df_processed['TIPO_DE_DOCUMENTO'])
    print("Limpieza de TIPO_DE_DOCUMENTO aplicada.")


    # 9. Agrupar por NOMBRECLIENTE y aplicar la agregación
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
        print(f"Error: Columna '{e}' faltante después de la agregación y renombramiento para modo '{mode}'.")
        print(f"Columnas esperadas: {expected_final_columns}")
        print(f"Columnas disponibles después de agrupar y renombrar: {df_grouped.columns.tolist()}")
        # Devolver un DataFrame vacío con headers esperados en caso de error
        return pd.DataFrame(columns=expected_final_columns)

    print(f"Procesamiento para '{mode}' finalizado exitosamente.")
    return final_df


# --- Ejecución Principal del Script ---
if __name__ == "__main__":
    # Add error handling for missing required libraries for the script version
    try:
        import pandas as pd
        import sys
        import re
        import os
        import openpyxl # Recommended for reading xlsx
        import xlsxwriter # Recommended for writing xlsx
    except ImportError as e:
        print(f"Error: Missing required library for the script version: {e}")
        print("Please install required libraries using pip:")
        print("pip install pandas openpyxl xlsxwriter")
        sys.exit(1) # Exit if libraries are missing


    input_filename = 'example.xlsx' # Usando el nombre del archivo original

    print(f"--- Procesamiento de Datos de Ventas (Versión Consola) ---")
    print(f"Intentando leer el archivo: {input_filename}")

    df = None # Initialize df outside try block
    try:
        # Intentar leer el archivo Excel
        # Especificar dtype=str para la columna 'IDENTIFICACION' puede ser útil si contiene ceros iniciales
        # También especificar para MontoBruto y otras columnas financieras puede ayudar si Excel lo guarda raro,
        # pero pd.to_numeric con errors='coerce' en process_data es una forma robusta también.
        # Mantengamos la lectura simple aquí y confiemos en la coerción dentro de process_data.
        df = pd.read_excel(input_filename)
        print("Archivo leído correctamente.")

        # La verificación detallada de columnas ahora se realiza dentro de process_data,
        # donde podemos lanzar una excepción específica.

    except FileNotFoundError:
        print(f"Error: El archivo '{input_filename}' no fue encontrado en la misma carpeta que el script.")
        sys.exit(1) # Salir si el archivo no existe
    except pd.errors.EmptyDataError:
         print(f"Error: El archivo '{input_filename}' está vacío.")
         sys.exit(1) # Salir si el archivo está vacío
    except Exception as e:
        print(f"Error inesperado al leer el archivo '{input_filename}': {e}")
        sys.exit(1) # Salir en caso de otro error de lectura

    # Mostrar Menú
    print("\n--- Menú de Procesamiento ---")
    print("Seleccione el tipo de operación a realizar:")
    print("1. Generar reporte Debito (UNIDADES > 0)")
    print("2. Generar reporte Credito (UNIDADES < 0)")
    print("3. Crear Informe Negativos y Positivos (Todas las UNIDADES, MontoBruto separado)")
    print("--------------------------------------------------------------------------------")

    choice = input("Por favor, ingrese su elección (1, 2, o 3): ").strip() # Leer entrada y eliminar espacios extra

    processed_df = None # DataFrame que contendrá el resultado procesado
    output_file = None  # Nombre del archivo de salida
    mode = None         # Modo de procesamiento ('debito', 'credito', 'split')
    mode_display_name = "Reporte" # Nombre amigable para los mensajes de salida

    if choice == '1':
        mode = 'debito'
        output_file = 'output_debito.xlsx'
        mode_display_name = "Reporte Debito"
    elif choice == '2':
        mode = 'credito'
        output_file = 'output_credito.xlsx'
        mode_display_name = "Reporte Credito"
    elif choice == '3':
        mode = 'split'
        output_file = 'output_negativos_positivos.xlsx'
        mode_display_name = "Informe Negativos y Positivos"
    else:
        print("Elección no válida. Por favor, ingrese '1', '2' o '3'. Saliendo del script.")
        sys.exit(1) # Salir si la elección no es válida

    try:
        # Llamar a la función de procesamiento con el modo seleccionado
        processed_df = process_data(df, mode)

        # Guardar el resultado si el procesamiento fue exitoso
        if processed_df is not None: # process_data ya no retorna None para errores, solo para modo inválido (que ya validamos)
            if not processed_df.empty:
                print(f"\nGuardando {mode_display_name} en: {output_file}")
                try:
                    # Usar ExcelWriter para robustez
                    with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
                        processed_df.to_excel(writer, index=False, sheet_name=mode_display_name)

                    print(f"¡Proceso completado exitosamente! El archivo '{output_file}' ha sido creado.")
                except Exception as e:
                    print(f"Error al guardar el archivo '{output_file}': {e}")
            else:
                 # Si el DataFrame está vacío pero tiene columnas (indicando que no hubo filas con el criterio, pero los headers están listos)
                 if not processed_df.columns.empty:
                     print(f"\nNo se encontraron registros que coincidieran con el criterio para {mode_display_name}. Creando archivo '{output_file}' con encabezados.")
                     try:
                        with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
                            processed_df.to_excel(writer, index=False, sheet_name=mode_display_name)
                        print(f"Archivo vacío con encabezados creado: '{output_file}'.")
                     except Exception as e:
                        print(f"Error al guardar el archivo vacío '{output_file}': {e}")
                 else:
                     # Si el DataFrame está completamente vacío (sin headers), no hay nada que guardar.
                     # El mensaje de que no se encontraron datos relevantes ya se imprimió en process_data.
                     pass # No hacemos nada más aquí si no hay headers

    except ValueError as ve: # Capturar la excepción de ValueError de process_data (ej. columnas faltantes)
        print(f"\nError de procesamiento: {ve}")
        sys.exit(1) # Salir debido al error de procesamiento
    except Exception as ex: # Capturar cualquier otra excepción inesperada durante process_data
        print(f"\nOcurrió un error inesperado durante el procesamiento: {ex}")
        import traceback
        traceback.print_exc() # Imprimir el traceback para ayudar en la depuración
        sys.exit(1) # Salir debido al error

    print("\nFin del script.")