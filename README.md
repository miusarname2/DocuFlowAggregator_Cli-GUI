Pensó durante un par de segundos


Below is the updated documentation reflecting all the new CLI & GUI features (multifile support, split mode, discount option, custom output folder, etc.). I’ve kept the trilingual layout (EN/中文/ES) and adjusted each section where needed.

---

## 🚀 Overview / 概览 / Visión General

**English:**
Welcome to **DocuFlowAggregator**, your all-in-one tool for **Debit**, **Credit** and now **Split (Negatives & Positives)** sales reports! Two ways to run it:

* **GUI** (Flet + Tkinter) for a guided, visual workflow.
* **CLI** for the terminal-lover, fully interactive with menus and prompts.

Both interfaces share the same rock-solid processing logic (`process_data_internal_sync` in GUI, `process_data` in CLI), which filters, cleans, consolidates and aggregates your Excel data in one step—goodbye manual spreadsheets!

**中文：**
欢迎使用 **DocuFlowAggregator**，您的终极销售报告助手，支持 **借记 (Debito)**、**贷记 (Credito)** 和 **正负分离 (Split)** 模式！提供两种交互方式：

* **图形界面**（Flet + Tkinter），引导式操作，无需命令行。
* **命令行界面**，互动式菜单、灵活多文件处理。

两者调用同一核心处理函数，可一键筛选、清洗、合并并汇总 Excel 数据，释放您的双手！

**Español:**
Bienvenido a **DocuFlowAggregator**, tu herramienta integral para reportes de **Débito**, **Crédito** y ahora **Negativos & Positivos (Split)**.

* **GUI** (Flet + Tkinter): paso a paso visual.
* **CLI**: menú interactivo en consola, con soporte para múltiples archivos.

Ambas comparten la misma lógica de `process_data`, que filtra, limpia, consolida nombres, agrega montos y exporta listo para usar.

---

## 📦 Installation / 安装 / Instalación

```bash
git clone https://github.com/miusarname2/DocuFlowAggregator_Cli-GUI.git
cd DocuFlowAggregator
python -m venv venv
# Linux/macOS:
source venv/bin/activate
# Windows:
venv\Scripts\activate
pip install -r requirements.txt
```

> **Main dependencies:**
>
> * `flet` (GUI)
> * `pandas` (data)
> * `tkinter` (file/folder pickers)
> * `openpyxl`, `xlsxwriter` (Excel I/O)

---

## 🎨 Project Structure / 项目结构 / Arquitectura del Código

```
DocuFlowAggregator/
├── .gitignore
├── LICENSE
├── README.md
├── intefaz.py     # Flet + Tkinter GUI
├── program.py
├── programGem.py  # CLI versión
└── requirements.tx
```

* **interfaz.py**: configura ventana, botones y diálogos GUI.
* **programGem.py**: menú de consola, múltiples archivos, modo y carpeta de salida.

---

## ✨ Core Functions / 核心函数 / Funciones Clave

### `clean_tipo_documento(tipo_doc_series)`

* **What?** Remove leading digits/spaces from `TIPO_DE_DOCUMENTO`.
* **How?** Regex `r'^\d+\s*'` on a pandas Series.
* **Returns:** Cleaned Series ready for grouping.

### `process_data(df, mode, subtract_discount=False)` (CLI)

* **Params:**

  * `df` (DataFrame)
  * `mode`: `"debito"` | `"credito"` | `"split"`
  * `subtract_discount` (bool)
* **Steps:**

  1. **Filter** by `UNIDADES` or process all (`split`).
  2. **Coerce** numeric (`MontoBruto`, `Descuento`, `IVA`) → fill NaN→ 0.
  3. **Split** `MontoBruto` into positive/negative if `mode=='split'`.
  4. **Consolidate** any “cliente/consumidor…final” → `CONSUMIDOR FINAL`.
  5. **Clean** `TIPO_DE_DOCUMENTO` via `clean_tipo_documento`.
  6. **Aggregate** sums & first-values.
  7. **(Optional)** Subtract absolute `Descuento`.
  8. **Select & reorder** final columns per mode.
* **Returns:** Processed DataFrame (data or empty with headers).

### `process_data_internal_sync(df_combined, mode)` (GUI)

Same pipeline as CLI’s `process_data`—filter, consolidate, clean, aggregate—except split logic and discount applied after grouping, then hands back the DataFrame to the GUI for saving.

---

## 🖥️ GUI Usage (Flet) / 图形界面使用 / Uso GUI

1. ```bash
   python interfaz.py
   ```
2. Choose one of three buttons:

   * **Generar reporte Débito**
   * **Generar reporte Crédito**
   * **Crear Informe Negativos y Positivos**
3. Enter **number of files** via dialog.
4. Pick each `.xlsx` file in turn.
5. (If data exists) choose **“¿Restar descuento?”**
6. Select **output folder**.
7. See **real-time status** (color-coded: blue=working, green=success, red=error).

---

## 💻 CLI Usage / 命令行使用 / Uso CLI

1. ```bash
   python programGem.py
   ```
2. **How many** Excel files? → enter `N`.
3. **Enter** each file path one by one.
4. **Mode?** (`debito` / `credito` / `split`)
5. **Subtract discount?** (s/n)
6. **Output folder?** (creates if needed)
7. **Done:** look for `reporte_debito.xlsx` / `reporte_credito.xlsx` / `reporte_negativos_positivos.xlsx` in your folder.

---

## 🎉 Example Flows / 示例流程 / Ejemplos

**GUI:**

```
[Generar reporte Débito] → “¿Cuántos archivos?” → 2
[File dialog x2] → “¿Restar descuento?” → Sí
[Folder dialog] → ¡Reporte guardado con éxito!
```

**CLI:**

```bash
$ python programGem.py
¿Cuántos archivos .xlsx? 3
Ruta archivo 1: ventas_ene.xlsx
Ruta archivo 2: ventas_feb.xlsx
Ruta archivo 3: ventas_mar.xlsx
Modo (debito/credito/split): split
¿Restar descuento? (s/n): n
Carpeta de salida: ./mis_reportes
Reporte guardado en: ./mis_reportes/reporte_negativos_positivos.xlsx
```

---

## 🛠️ Customization / 定制 / Personalización

* **Adjust regex** for other “final” aliases in `final_pattern_regex`.
* **Add metrics:** extend `agg_dict` (e.g. `Costo`, `Margen`).
* **Dark theme GUI:** `page.theme_mode = ft.ThemeMode.DARK`.

---

## ⚠️ Known Issues / 已知问题 / Problemas Conocidos

* Large Excel files (> 50 MB) → may be slow (in-memory).
* On some Linux, install `python3-tk` for file dialogs.
* Permissions: ensure write access to chosen output folder.

---

## 🎈 Contributing / 贡献 / Contribuir

1. Fork this repo.
2. Create `feature/your-tip` branch.
3. Add tests under `tests/`.
4. Submit PR with description of your changes.

---

Thank you for choosing **DocuFlowAggregator**! May your sales data always flow smoothly. 🚀
感谢使用 **DocuFlowAggregator**！愿您的销售报表一帆风顺。 🚀
¡Gracias por usar **DocuFlowAggregator**! Que tus reportes siempre te impulsen hacia el éxito. 🚀
