## 🚀 Overview / 概览

**English:**  
Welcome to **DocuFlowAggregator**, your ultimate assistant for generating **Debit** and **Credit** sales reports! This project offers two complementary interfaces:
- **Graphical UI** with **Flet** for a friendly, visual experience.  
- **CLI** for terminal fans—just a couple of commands and your reports are ready.

Both share the powerful **process_data** function, engineered to filter, clean, and summarize transactions in one go. Say goodbye to dull spreadsheets and supercharge your workflow!

**中文：**  
欢迎使用 **DocuFlowAggregator**，您生成 **借记** 和 **贷记** 销售报告的终极助手！本项目提供两种互补界面：  
- **图形界面**（Flet）：直观友好，一键操作。  
- **命令行界面**：终端爱好者的最爱，只需几行命令即可完成报告。

两者都调用强大的 **process_data** 函数，一键筛选、清洗并汇总交易，告别枯燥表格，让流程焕然一新！

---

## 📦 Installation / 安装

**English:**
1. **Clone the repo**  
   ```bash
   git clone https://github.com/miusarname2/DocuFlowAggregator_Cli-GUI.git
   cd DocuFlowAggregator
   ```
2. **Create & activate venv**  
   ```bash
   python -m venv venv
   source venv/bin/activate   # Linux/macOS
   venv\Scripts\activate      # Windows
   ```
3. **Install deps**  
   ```bash
   pip install -r requirements.txt
   ```
   > **Main:** `flet`, `pandas`, `tkinter`

**中文：**
1. **克隆仓库**  
   ```bash
   git clone https://github.com/miusarname2/DocuFlowAggregator_Cli-GUI.git
   cd DocuFlowAggregator
   ```
2. **创建并激活虚拟环境**  
   ```bash
   python -m venv venv
   source venv/bin/activate   # Linux/macOS
   venv\Scripts\activate      # Windows
   ```
3. **安装依赖**  
   ```bash
   pip install -r requirements.txt
   ```
   > **核心依赖：** `flet`、`pandas`、`tkinter`

---

## 🎨 Project Structure / 项目结构

```
DocuFlowAggregator/
├── intefaz.py      # Flet UI + handlers
└── programGem.py     # CLI version
```

- **intefaz.py**: Builds the window, buttons & status. / 界面及交互  
- **programGem.py**: Loads Excel, shows menu, saves output. / 控制台脚本

---

## ✨ Core Functions / 核心函数

### `clean_tipo_documento(tipo_doc_series)`
- **What? / 功能**  
  Strips leading digits/spaces from document-type strings.  
  清除文档类型字段前置数字和空格。
- **How? / 原理**  
  Regex `r'^\d+\s*'` on a pandas Series.  
  使用正则 `r'^\d+\s*'` 在 pandas Series 上替换。
- **Returns / 返回**  
  “Cleaned” pandas Series ready for grouping.  
  清洗后的 Series，准备聚合。

---

### `process_data(df, mode)`
- **Params / 参数**  
  - `df` (`pd.DataFrame`): Original data / 原始数据  
  - `mode` (`str`): `"debito"` (UNIDADES > 0) or `"credito"` (UNIDADES < 0)  
- **Workflow / 流程**  
  1. **Filter** by mode. / 根据模式筛选  
  2. **Consolidate** any “cliente/consumidor…final” → `CONSUMIDOR FINAL`. / 合并“客户/消费者最终”  
  3. **Clean** document type via `clean_tipo_documento`. / 清洗文档类型  
  4. **Aggregate** sums & first-values. / 聚合求和与选首值  
  5. **Rename & reorder** columns. / 重命名并重排列  
- **Returns / 返回**  
  - DataFrame with `['TIPO DE DOCUMENTO','IDENTIFICACION',…,'Iva']`.  
    带有标准列的 DataFrame  
  - Empty DataFrame with headers if no matching rows.  
    无匹配时返回仅含表头的空 DataFrame  

---

## 🖥️ GUI Usage (Flet) / 图形界面使用

**English:**
1. ```bash
   python interface.py
   ```
2. Click **Generate Debit** or **Generate Credit**.  
3. Pick your `.xlsx`.  
4. Choose output folder — done!  
5. Status updates in real time: success, cancel, or errors.

**中文：**
1. ```bash
   python interface.py
   ```
2. 点击 “生成 借记 报告” 或 “生成 贷记 报告”。  
3. 选择 `.xlsx` 文件。  
4. 指定输出目录 — 完成！  
5. 实时显示状态：成功、取消或错误。

---

## 💻 CLI Usage / 命令行使用

**English:**
1. ```bash
   python programGem.py
   ```
2. Read prompt and choose:
   ```
   1. Debito (UNIDADES > 0)
   2. Credito (UNIDADES < 0)
   ```
3. Outputs `output_debito.xlsx` or `output_credito.xlsx`.

**中文：**
1. ```bash
   python programGem.py
   ```
2. 根据提示选择：
   ```
   1. 借记 (UNIDADES > 0)
   2. 贷记 (UNIDADES < 0)
   ```
3. 在项目文件夹生成 `output_debito.xlsx` 或 `output_credito.xlsx`。

---

## 🎉 Example Flow / 示例流程

```bash
$ python interface.py
> What do you want to do today?
[Generate Debit Report] [Generate Credit Report]
…Selected Debit…
> Select Excel for debit report…
> Processing ventas_april.xlsx…
> Processed successfully (125 rows). Choose export folder…
> Saving to /home/user/reports/output_debito.xlsx…
✅ Debit report generated!
```

```bash
$ python programGem.py
--- Sales Data Processing ---
1. Debito (UNIDADES > 0)
2. Credito (UNIDADES < 0)
Enter choice (1 or 2): 1
…Saving output_debito.xlsx…
```

```bash
$ python programGem.py
Error: Input file not found. Exiting.
```

---

## 🛠️ Customization / 定制与扩展

- **Final-pattern**: adjust `final_pattern` for other aliases.  
  修改 `final_pattern` 以适配更多别名。  
- **Extra metrics**: add fields in `agg_dict` (e.g. `Cost`, `Margin`).  
  在 `agg_dict` 中增添更多指标（如 成本、利润率）。  
- **Dark theme**: `page.theme_mode = ft.ThemeMode.DARK`.  
  使用深色模式：`page.theme_mode = ft.ThemeMode.DARK`。

---

## ❓ FAQ / 常见问题

> **Q: Extra columns in Excel?**  
> The script ignores non-required columns and only checks essentials.

> **问：如果 Excel 有额外列？**  
> 脚本会忽略不需要的列，仅验证必需字段。

> **Q: Support CSV?**  
> Yes—use `pd.read_csv()` and pass the DataFrame to `process_data`.

> **问：能处理 CSV 吗？**  
> 可以：用 `pd.read_csv()` 读取后传入 `process_data`。

> **Q: How to handle errors?**  
> GUI shows red messages; CLI prints clear error origins.

> **问：如何处理错误？**  
> 界面会用红色提示；命令行会打印明确的错误信息。

---

## 🎈 Contributing / 贡献指南

1. **Fork** the repo.  
2. Create `feature/your-improvement` branch.  
3. Add tests under `tests/`.  
4. Open a **Pull Request** describing your changes.

---

Thank you for choosing **DocuFlowAggregator**! May every report tell a clear, ordered story of your sales. 🚀  
感谢选择 **DocuFlowAggregator**！愿每份报告都清晰呈现您的销售故事。 🚀

# Español

## 🚀 Visión General

¡Bienvenido a **DocuFlowAggregator**, tu asistente definitivo para generar reportes de ventas en modo **Débito** y **Crédito**! Este proyecto ofrece dos interfaces complementarias:

- **Interfaz Gráfica** con **Flet** para una experiencia amigable y visual.  
- **CLI (Línea de Comandos)** para los fanáticos del terminal, donde un par de líneas bastan para obtener tus reportes.

Ambas versiones comparten la poderosa función de **procesamiento de datos** (`process_data`), diseñada para filtrar, limpiar y resumir transacciones con un solo comando. ¡Olvídate de las hojas de cálculo monótonas y dale un empujón creativo a tu flujo de trabajo!

---

## 📦 Instalación

1. **Clona este repositorio**  
   ```bash
   git clone https://github.com/miusarname2/DocuFlowAggregator_Cli-GUI
   cd DocuFlowAggregator
   ```

2. **Crea y activa un entorno virtual**  
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/macOS
   venv\Scripts\activate     # Windows
   ```

3. **Instala dependencias**  
   ```bash
   pip install -r requirements.txt
   ```
   > **Requisitos principales**:  
   > - `flet` para la GUI  
   > - `pandas` para manipulación de datos  
   > - `tkinter` para diálogos de archivos

---

## 🎨 Arquitectura del Código

```
DocuFlowAggregator/
├── intefaz.py           # Interfaz Flet + handlers
└── programGem.py           # Versión de consola
```

- **intefaz.py**: Monta la ventana, botones y mensajes de estado.  
- **programGem.py**: Lee `example.xlsx`, muestra menú y guarda los resultados.

---

## ✨ Funciones Clave

### `clean_tipo_documento(tipo_doc_series)`
- **¿Qué hace?**  
  Elimina cualquier prefijo numérico y espacios en blanco en la columna de tipo de documento.
- **Cómo lo hace:**  
  Usa una expresión regular `r'^\d+\s*'` para descartar dígitos iniciales.  
- **Devuelve:**  
  Una serie de pandas con valores “limpios” listos para agrupar.

---

### `process_data(df, mode)`
- **Parámetros:**  
  - `df` (`pd.DataFrame`): Datos originales.  
  - `mode` (`str`): `"debito"` (UNIDADES > 0) o `"credito"` (UNIDADES < 0).
- **Flujo interno:**
  1. **Filtrado** según `mode`.  
  2. **Consolidación** de cualquier nombre que coincida con patrón `(?i)(cliente|consumidor).*finall?` → “CONSUMIDOR FINAL”.  
  3. **Limpieza** de la columna de documento con `clean_tipo_documento`.  
  4. **Agregación**: suma de montos y toma del primer valor para identificadores y nombres.  
  5. **Renombramiento** y **reordenamiento** de columnas (salida estandarizada).
- **Retorna:**  
  - DataFrame con columnas `['TIPO DE DOCUMENTO','IDENTIFICACION',…,'Iva']`.  
  - En caso de no haber datos, un DataFrame vacío con los mismos encabezados.

---

## 🖥️ Uso de la Interfaz Gráfica (Flet)

1. **Ejecuta**:
   ```bash
   python intefaz.py
   ```
2. **Selecciona** “Generar reporte Débito” o “Crédito”.  
3. **Escoge** tu archivo `.xlsx`.  
4. **Elige** carpeta de destino y ¡listo!  
5. Visualiza mensajes de estado en tiempo real: éxito, cancelación o errores.

---

## 💻 Uso en Consola (CLI)

1. **Ejecuta**:
   ```bash
   python programGem.py
   ```
2. Lee el mensaje de bienvenida y elige:
   ```
   1. Procesar 'Debito' (UNIDADES > 0)
   2. Procesar 'Credito' (UNIDADES < 0)
   ```
3. El script crea `output_debito.xlsx` o `output_credito.xlsx` en la carpeta del proyecto.

---

## 🎉 Ejemplo de Flujo

```bash
$ python intefaz.py
> ¿Qué deseas hacer hoy?
[Generar reporte Débito] [Generar reporte Crédito]
...Seleccioné Débito...
> Seleccione archivo Excel para el reporte de debito...
> Leyendo y procesando datos desde ventas_abril.xlsx...
> Procesado con éxito (125 registros). Seleccione carpeta de exportación...
> Guardando archivo en: /home/usuario/reportes/output_debito.xlsx...
¡Reporte de debito generado y guardado exitosamente!
```

---

## 🛠️ Personalización y Extensión

- **Patrones de cliente final**: modifica `final_pattern` para adaptarlo a otros alias.  
- **Columnas adicionales**: incluye más métricas en `agg_dict` (por ejemplo, `Costo`, `Margen`).  
- **Temas Flet**: prueba `page.theme_mode = ft.ThemeMode.DARK` para modo nocturno.

---

## ❓ Preguntas Frecuentes

> **¿Qué pasa si mi Excel tiene columnas extra?**  
El script ignora columnas no requeridas. Sólo valida que estén las esenciales.

> **¿Puedo procesar archivos CSV?**  
Sí: lee el CSV con `pd.read_csv()` y pásalo a `process_data`.

> **¿Cómo manejo errores?**  
Revisa los mensajes en rojo en la GUI o en la consola; indican claramente el origen del fallo (columnas faltantes, archivo vacío, selección cancelada…).

---

## 🎈 Contribuir

1. Haz un **fork** del repositorio.  
2. Crea una rama `feature/tu-mejora`.  
3. Añade tests unitarios en `tests/`.  
4. Abre un **pull request** describiendo tu aporte.

---

¡Gracias por elegir **DocuFlowAggregator**! Que cada reporte sea una historia clara y ordenada de tus ventas. 🚀