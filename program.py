"""
Script to aggregate transactions in example.xlsx based on 'UNIDADES'.
Options:
- Debito: includes records with UNIDADES > 0.
- Credito: includes records with UNIDADES < 0.

Aggregates by NOMBRECLIENTE (and related fields), summing MontoBruto, Descuento, IVA.
Cleans TIPO_DE_DOCUMENTO by removing leading numbers.
Exports to Excel.
"""
import pandas as pd
import re

def clean_document_type(doc_type: str) -> str:
    """Remove leading numbers and whitespace from document type."""
    # Remove any leading digits and non-letter characters
    return re.sub(r"^[^A-Za-zÁÉÍÓÚÜÑ]+", "", doc_type).strip()


def aggregate(df: pd.DataFrame, filter_positive: bool) -> pd.DataFrame:
    """
    Filter by UNIDADES > 0 if filter_positive is True (Debito), else UNIDADES < 0 (Credito).
    Aggregate sums for each group.
    """
    if filter_positive:
        df_filtered = df[df['UNIDADES'] > 0]
    else:
        df_filtered = df[df['UNIDADES'] < 0]

    # Clean document type
    df_filtered['TIPO_DE_DOCUMENTO'] = df_filtered['TIPO_DE_DOCUMENTO'].apply(clean_document_type)

    # Define grouping fields
    group_fields = [
        'TIPO_DE_DOCUMENTO', 'IDENTIFICACION', 'NOMBRECLIENTE',
        'PRIMER_APELLIDO', 'SEGUNDO_APELLIDO', 'PRIMER_NOMBRE', 'OTROS_NOMBRES'
    ]

    # Perform aggregation
    agg_df = df_filtered.groupby(group_fields, as_index=False).agg({
        'MontoBruto': 'sum',
        'Descuento': 'sum',
        'IVA': 'sum'
    })

    return agg_df


def main():
    # Load data
    input_file = 'example1.xlsx'
    try:
        df = pd.read_excel(input_file)
    except FileNotFoundError:
        print(f"Error: \"{input_file}\" not found.")
        return

    # Ensure numeric columns are correct type
    for col in ['UNIDADES', 'MontoBruto', 'Descuento', 'IVA']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # Menu
    print("Seleccione una opción:")
    print("1. Debito (UNIDADES > 0)")
    print("2. Credito (UNIDADES < 0)")
    choice = input("Ingrese 1 o 2: ").strip()

    if choice == '1':
        result_df = aggregate(df, filter_positive=True)
        output_file = 'output_debito.xlsx'
    elif choice == '2':
        result_df = aggregate(df, filter_positive=False)
        output_file = 'output_credito.xlsx'
    else:
        print("Opción no válida. Saliendo.")
        return

    # Export to Excel
    result_df.to_excel(output_file, index=False)
    print(f"Archivo generado: {output_file}")

if __name__ == '__main__':
    main()
