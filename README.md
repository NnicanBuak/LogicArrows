# LogicArrows

Программы на ассемблере для компьютеров из логических стрелок Аркадия Чубрика.

## Компьютеры

Оригинальные схемы, документация и примеры программ находятся в
[репозитории chubrik/LogicArrows](https://github.com/chubrik/LogicArrows):

- [Computer v1 — первая версия компьютера](https://github.com/chubrik/LogicArrows/tree/main/computer-v1).
- [Computer v2 — вторая версия компьютера](https://github.com/chubrik/LogicArrows/tree/main/computer-v2).

## Эмулятор

[**Общий эмулятор Computer v2**](emulator/README.md) — запуск ASM, дисплей 16×16 и терминал настраиваемого размера. Память — **32 КБ**.

<img src="emulator/preview.png" alt="Общий эмулятор Computer v2: дисплей, терминал и управление программой" width="400">

## Программы

### 1 КБ

| Программа | Краткое описание | Скриншот |
|---|---|---|
| [**QR Terminal**](qr-terminal/README.md) | Генератор QR **21×21** для Computer v2: ввод до **16 байт CP1251**, вывод в терминал. **864 байта**. | <img src="qr-terminal/img/qr-terminal21.png" alt="QR Terminal: QR-код в терминале Computer v2" width="532"> |
| [**3DViewer**](3dviewer/README.md) | Куб с управлением стрелками: вращение вокруг двух осей, масштаб **×0,5…×3** с обрезкой по границам экрана, сброс ракурса и масштаба пробелом. **978 байт**. | <img src="3dviewer/preview.gif" alt="3DViewer: вращение, масштаб и сброс ракурса с клавиатуры" width="272"> |
| [**3DGraphics: компактный движок**](graphics3d/README.md#компактный-каркасный-движок) | Общий 3D-движок Computer v2: **896 байт + до 128 байт модели**, цветные линии, кадр в LCD RAM, вращение и пульсация. | <img src="graphics3d/compact/models/cube/preview.gif" alt="Компактный 3DGraphics: цветной каркасный куб" width="272"> |

### 32 КБ

| Программа | Краткое описание | Скриншот |
|---|---|---|
| [**3DEditor**](3deditor/README.md) | Просмотр и редактирование вершин, рёбер и граней: выбор, **g/r/s**, создание и удаление. **Зависит от [API 3DGraphics](graphics3d/API.md)**. **30 044 байт / 32 КБ**. | <img src="3deditor/preview.gif" alt="3DEditor: просмотр, выбор, трансформации и создание деталей" width="272"> |
| [**3DEditor Terminal**](3deditor-terminal/README.md) | Управляемый с клавиатуры 3D-редактор. Сцена выводится в терминал как растр **144×72 пикселя** из символов 6×8; отдельная строка для ввода. **30 044 байт / 32 КБ**. | <img src="3deditor-terminal/preview.png" alt="Куб в терминале: растр 144×72 пикселя" width="272"> |
| [**3DGraphics: полный API**](graphics3d/README.md#каркас-и-заливка-полного-api) | Перспектива, управление объектами и заливка граней. Демонстрационные программы занимают **5–6 КБ**. | <img src="graphics3d/build/preview.gif" alt="3DGraphics: каркасные модели и заполненные поверхности" width="272"> |
