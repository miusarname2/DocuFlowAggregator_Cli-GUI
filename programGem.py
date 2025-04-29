import pandas as pd
import sys # Para salir del script en caso de error
import re  # Para usar expresiones regulares en la limpieza y matching

def clean_tipo_documento(tipo_doc_series):
    """Limpia la serie 'TIPO_DE_DOCUMENTO' eliminando números y espacios al inicio."""
    # Asegura que la serie es de tipo string antes de aplicar regex
    # r'^\d+\s*' busca:
    # ^        -> Inicio de la cadena
    # \d+      -> Uno o más dígitos
    # \s*      -> Cero o más espacios en blanco
    # regex=True es necesario para indicar que el patrón es una expresión regular
    # El método str.replace ya maneja valores no string adecuadamente cuando se usa con .astype(str)
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
    """

    if mode == 'debito':
        print("Procesando para 'Debito' (UNIDADES > 0)...")
        # Usamos .copy() para evitar el SettingWithCopyWarning al modificar el df filtrado
        df_filtered = df[df['UNIDADES'] > 0].copy()
    elif mode == 'credito':
        print("Procesando para 'Credito' (UNIDADES < 0)...")
        df_filtered = df[df['UNIDADES'] < 0].copy()
    else:
        print("Modo de procesamiento inválido.")
        return None # Esto no debería ocurrir si el menú valida correctamente

    # Definir las columnas esperadas en la salida final, incluso si el DataFrame está vacío
    expected_final_columns = [
        'TIPO DE DOCUMENTO', 'IDENTIFICACION', 'NOMBRECLIENTE', 'PRIMER_APELLIDO',
        'SEGUNDO_APELLIDO', 'PRIMER_NOMBRE', 'OTROS_NOMBRES', 'MontoBruto',
        'Descuento', 'Iva'
    ]

    if df_filtered.empty:
        print(f"No se encontraron registros con UNIDADES {' > 0' if mode == 'debito' else ' < 0'} para procesar.")
        # Devolver un DataFrame vacío pero con los encabezados esperados
        return pd.DataFrame(columns=expected_final_columns)

    # --- Pasos de Procesamiento ---

    # *** MODIFICACIÓN: Consolidar nombres que matchean el patrón de cliente/consumidor final ***
    # El patrón busca cadenas que contengan 'cliente' o 'consumidor', seguidas por
    # cualquier cosa (.*? - cero o más caracteres no codiciosos), y luego 'final' con
    # una 'l' opcional al final ('l?'), ignorando mayúsculas/minúsculas ((?i)).
    final_pattern = r'(?i)(cliente|consumidor).*finall?'
    # Asegurar que la columna es de tipo string antes de usar str.contains
    df_filtered['NOMBRECLIENTE'] = df_filtered['NOMBRECLIENTE'].astype(str)
    # Crear una máscara booleana: True para filas que matchean el patrón, False en caso contrario
    mask_final_clients = df_filtered['NOMBRECLIENTE'].str.contains(final_pattern, na=False)
    # Reemplazar los valores en 'NOMBRECLIENTE' que matchean el patrón por 'CONSUMIDOR FINAL'
    df_filtered.loc[mask_final_clients, 'NOMBRECLIENTE'] = 'CONSUMIDOR FINAL'
    # **************************************************************************************


    # 1. Limpiar TIPO_DE_DOCUMENTO y agregarlo como una nueva columna para la agregación
    df_filtered['TIPO_DE_DOCUMENTO_CLEANED'] = clean_tipo_documento(df_filtered['TIPO_DE_DOCUMENTO'])

    # 2. Definir el diccionario de agregación
    # Usamos la columna limpia para el tipo de documento (tomamos el primero encontrado)
    # Usamos las columnas originales para otros campos (tomamos el primero encontrado)
    # Sumamos los valores financieros
    agg_dict = {
        'TIPO_DE_DOCUMENTO_CLEANED': 'first',
        'IDENTIFICACION': 'first',
        'PRIMER_APELLIDO': 'first',
        'SEGUNDO_APELLIDO': 'first',
        'PRIMER_NOMBRE': 'first',
        'OTROS_NOMBRES': 'first',
        'MontoBruto': 'sum',
        'Descuento': 'sum',
        'IVA': 'sum' # Sumamos el IVA, lo renombraremos después
    }

    # Agrupar por NOMBRECLIENTE (ahora incluye la combinación) y aplicar la agregación
    # as_index=False mantiene NOMBRECLIENTE como una columna regular en el resultado
    df_grouped = df_filtered.groupby('NOMBRECLIENTE', as_index=False).agg(agg_dict)

    # 3. Renombrar columnas para que coincidan con los nombres de salida deseados
    # Mapeamos los nombres de las columnas agregadas a los nombres finales requeridos
    rename_map = {
        'TIPO_DE_DOCUMENTO_CLEANED': 'TIPO DE DOCUMENTO', # Renombra la columna limpia
        'IVA': 'Iva' # Renombra IVA a Iva
        # Las otras columnas (IDENTIFICACION, NOMBRECLIENTE, etc.) ya tienen el nombre correcto
    }
    df_grouped = df_grouped.rename(columns=rename_map)

    # 4. Seleccionar y Reordenar columnas según la lista de salida deseada
    # Asegurarse de que todas las columnas en expected_final_columns existan en el DataFrame
    # después del renombramiento.
    try:
        final_df = df_grouped[expected_final_columns]
    except KeyError as e:
        print(f"Error: Columna faltante después de la agregación y renombramiento: {e}. Columnas disponibles: {df_grouped.columns.tolist()}")
        return pd.DataFrame(columns=expected_final_columns) # Devolver un DataFrame vacío con headers en caso de error

    return final_df

# --- Ejecución Principal del Script ---
if __name__ == "__main__":
    input_filename = 'example.xlsx' # Usando el nombre del archivo original
    output_filename_debito = 'output_debito.xlsx'
    output_filename_credito = 'output_credito.xlsx'

    print(f"--- Procesamiento de Datos de Ventas ---")
    print(f"Intentando leer el archivo: {input_filename}")

    try:
        # Intentar leer el archivo Excel
        # Especificar dtype=str para la columna 'IDENTIFICACION' puede ser útil si contiene ceros iniciales
        # que Excel o pandas podrían interpretar como números y eliminar (aunque en tu ejemplo parece manejarlos como string)
        # Si necesitas que 'IDENTIFICACION' se mantenga exactamente como está (ej: "000000000000"), podrías agregar:
        # df = pd.read_excel(input_filename, dtype={'IDENTIFICACION': str})
        df = pd.read_excel(input_filename)
        print("Archivo leído correctamente.")

        # Verificación básica de que las columnas esenciales existen
        required_cols = ['UNIDADES', 'NOMBRECLIENTE', 'TIPO_DE_DOCUMENTO',
                         'IDENTIFICACION', 'PRIMER_APELLIDO', 'SEGUNDO_APELLIDO',
                         'PRIMER_NOMBRE', 'OTROS_NOMBRES', 'MontoBruto', 'Descuento', 'IVA']
        if not all(col in df.columns for col in required_cols):
            missing = [col for col in required_cols if col not in df.columns]
            print(f"Error: El archivo Excel no contiene todas las columnas requeridas. Faltan: {missing}")
            sys.exit(1) # Salir si faltan columnas

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
    print("1. Procesar 'Debito' (UNIDADES > 0)")
    print("2. Procesar 'Credito' (UNIDADES < 0)")
    print("-----------------------------")

    choice = input("Por favor, ingrese su elección (1 o 2): ").strip() # Leer entrada y eliminar espacios extra

    processed_df = None # DataFrame que contendrá el resultado procesado
    output_file = None  # Nombre del archivo de salida
    mode = None         # Modo de procesamiento ('debito' o 'credito')

    if choice == '1':
        mode = 'debito'
        output_file = output_filename_debito
        processed_df = process_data(df, mode)
    elif choice == '2':
        mode = 'credito'
        output_file = output_filename_credito
        processed_df = process_data(df, mode)
    else:
        print("Elección no válida. Por favor, ingrese '1' o '2'. Saliendo del script.")
        sys.exit(1) # Salir si la elección no es 1 o 2

    # Guardar el resultado si el procesamiento fue exitoso y devolvió un DataFrame
    # process_data devuelve un DataFrame (incluso vacío con headers) o None (solo para modo inválido, ya manejado)
    if processed_df is not None:
        if not processed_df.empty:
            print(f"\nGuardando resultados procesados en: {output_file}")
            try:
                # Guardar el DataFrame procesado en un nuevo archivo Excel
                processed_df.to_excel(output_file, index=False) # index=False para no escribir el índice de pandas
                print(f"¡Proceso completado exitosamente! El archivo '{output_file}' ha sido creado.")
            except Exception as e:
                print(f"Error al guardar el archivo '{output_file}': {e}")
        else:
             # El mensaje de que no se encontraron datos ya se imprimió en process_data
             # Si el DataFrame está vacío pero tiene columnas, crea el archivo con solo encabezados
             if not processed_df.columns.empty:
                 print(f"\nNo se encontraron registros que coincidieran con el criterio. Creando archivo '{output_file}' con encabezados.")
                 try:
                    processed_df.to_excel(output_file, index=False)
                    print(f"Archivo vacío con encabezados creado: '{output_file}'.")
                 except Exception as e:
                    print(f"Error al guardar el archivo vacío '{output_file}': {e}")
             else:
                 print("\nNo se generaron datos ni encabezados válidos para guardar.")

    print("Fin del script.")