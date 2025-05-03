import pandas as pd
import sys
import re
import os

def clean_tipo_documento(tipo_doc_series):
    return tipo_doc_series.astype(str).str.replace(r'^\d+\s*', '', regex=True)

def process_data(df, mode, subtract_discount=False):
    required_cols = ['UNIDADES','NOMBRECLIENTE','TIPO_DE_DOCUMENTO','IDENTIFICACION',
                     'PRIMER_APELLIDO','SEGUNDO_APELLIDO','PRIMER_NOMBRE','OTROS_NOMBRES',
                     'MontoBruto','Descuento','IVA']
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Faltan columnas requeridas: {missing}")

    # filter
    if mode == 'debito':
        df_proc = df[df['UNIDADES']>0].copy()
        final_cols = ['TIPO DE DOCUMENTO','IDENTIFICACION','NOMBRECLIENTE','PRIMER_APELLIDO',
                      'SEGUNDO_APELLIDO','PRIMER_NOMBRE','OTROS_NOMBRES','MontoBruto','Descuento','Iva']
    elif mode == 'credito':
        df_proc = df[df['UNIDADES']<0].copy()
        final_cols = ['TIPO DE DOCUMENTO','IDENTIFICACION','NOMBRECLIENTE','PRIMER_APELLIDO',
                      'SEGUNDO_APELLIDO','PRIMER_NOMBRE','OTROS_NOMBRES','MontoBruto','Descuento','Iva']
    elif mode == 'split':
        df_proc = df.copy()
        df_proc['MontoBruto'] = pd.to_numeric(df_proc['MontoBruto'], errors='coerce').fillna(0)
        df_proc['MontoBruto Positivo'] = df_proc['MontoBruto'].apply(lambda x: x if x>0 else 0)
        df_proc['MontoBruto Negativo'] = df_proc['MontoBruto'].apply(lambda x: x if x<0 else 0)
        final_cols = ['TIPO DE DOCUMENTO','IDENTIFICACION','NOMBRECLIENTE','PRIMER_APELLIDO',
                      'SEGUNDO_APELLIDO','PRIMER_NOMBRE','OTROS_NOMBRES',
                      'MontoBruto Positivo','MontoBruto Negativo','Descuento','Iva']
    else:
        raise ValueError(f"Modo inválido: {mode}")

    if df_proc.empty:
        return pd.DataFrame(columns=final_cols)

    # consolidate names
    regex = re.compile(r'(?i)(cliente|consumidor).*finall?')
    df_proc['NOMBRECLIENTE'] = df_proc['NOMBRECLIENTE'].astype(str)
    mask = df_proc['NOMBRECLIENTE'].str.upper().isin([
        'CLIENTE CLIENTE','CLIENTE UNO','CLIENTES VARIOS CLIENTES VARIOS','CONSUMIDOR FINAL'
    ]) | df_proc['NOMBRECLIENTE'].str.contains(regex)
    df_proc.loc[mask,'NOMBRECLIENTE']='CONSUMIDOR FINAL'

    # clean doc type
    df_proc['TIPO_DE_DOCUMENTO_CLEANED'] = clean_tipo_documento(df_proc['TIPO_DE_DOCUMENTO'])

    # aggregate
    agg = {}
    if mode in ['debito','credito']:
        agg = {
            'TIPO_DE_DOCUMENTO_CLEANED':'first','IDENTIFICACION':'first',
            'PRIMER_APELLIDO':'first','SEGUNDO_APELLIDO':'first',
            'PRIMER_NOMBRE':'first','OTROS_NOMBRES':'first',
            'MontoBruto':'sum','Descuento':'sum','IVA':'sum'
        }
    else:
        agg = {
            'TIPO_DE_DOCUMENTO_CLEANED':'first','IDENTIFICACION':'first',
            'PRIMER_APELLIDO':'first','SEGUNDO_APELLIDO':'first',
            'PRIMER_NOMBRE':'first','OTROS_NOMBRES':'first',
            'MontoBruto Positivo':'sum','MontoBruto Negativo':'sum',
            'Descuento':'sum','IVA':'sum'
        }
    df_grp = df_proc.groupby('NOMBRECLIENTE',as_index=False).agg(agg)
    df_grp = df_grp.rename(columns={
        'TIPO_DE_DOCUMENTO_CLEANED':'TIPO DE DOCUMENTO','IVA':'Iva'
    })

    # subtract discount
    if subtract_discount:
        df_grp['Descuento'] = pd.to_numeric(df_grp['Descuento'],errors='coerce').fillna(0).abs()
        if mode in ['debito','credito']:
            df_grp['MontoBruto'] = df_grp['MontoBruto'] - df_grp['Descuento']
        else:
            df_grp['MontoBruto Positivo'] = df_grp['MontoBruto Positivo'] - df_grp['Descuento']
            df_grp['MontoBruto Negativo'] = df_grp['MontoBruto Negativo'] - df_grp['Descuento']

    # select final
    return df_grp[final_cols]

if __name__=='__main__':
    print("== Reporte de Ventas Versión Consola ==")
    # archivos
    n = int(input("¿Cuántos archivos .xlsx desea procesar? "))
    files = []
    for i in range(n):
        path = input(f"Ruta archivo {i+1}: ").strip()
        if not os.path.isfile(path) or not path.lower().endswith('.xlsx'):
            print(f"Error: '{path}' no es un archivo .xlsx válido.")
            sys.exit(1)
        files.append(path)

    # leer y combinar
    dfs = []
    for f in files:
        dfs.append(pd.read_excel(f,engine='openpyxl'))
    df_all = pd.concat(dfs,ignore_index=True)

    # modo
    m = input("Elija modo (debito/credito/split): ").strip().lower()
    sd = False
    if m in ['debito','credito','split']:
        ans = input("¿Restar descuento? (s/n): ").strip().lower()
        sd = (ans=='s')
    else:
        print("Modo inválido.")
        sys.exit(1)

    # procesar
    result = process_data(df_all,m,subtract_discount=sd)
    if result.empty:
        print("No hay registros para el reporte. Se generará un archivo solo con encabezados.")

    # carpeta y guardar
    out_dir = input("Ruta carpeta de salida: ").strip()
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir,exist_ok=True)
    out_name = {
        'debito':'reporte_debito.xlsx',
        'credito':'reporte_credito.xlsx',
        'split':'reporte_negativos_positivos.xlsx'
    }[m]
    out_path = os.path.join(out_dir,out_name)
    with pd.ExcelWriter(out_path,engine='xlsxwriter') as w:
        result.to_excel(w,index=False,sheet_name=m)
    print(f"Reporte guardado en: {out_path}")