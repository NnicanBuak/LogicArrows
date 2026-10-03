# LogicArrows

Программы на ассемблере для компьютеров из логических стрелок Аркадия Чубрика.

## Компьютеры

Оригинальные схемы, документация и примеры программ находятся в
[репозитории chubrik/LogicArrows](https://github.com/chubrik/LogicArrows):

- [Computer v1 — первая версия компьютера](https://github.com/chubrik/LogicArrows/tree/main/computer-v1).
- [Computer v2 — вторая версия компьютера](https://github.com/chubrik/LogicArrows/tree/main/computer-v2).

## Программы

| Программа | Краткое описание | Скриншот |
|---|---|---|
| [**QR Terminal**](qr-terminal/README.md) | Генератор QR **21×21** для Computer v2: ввод до **16 байт CP1251**, вывод в терминал. **864 байта**. | <img src="qr-terminal/img/qr-terminal21.png" alt="QR Terminal: QR-код в терминале Computer v2" width="532"> |
| [**3DViewer**](3dviewer/README.md) | Куб с управлением стрелками: вращение вокруг двух осей, масштаб **×0,5…×3** с обрезкой по границам экрана, сброс ракурса и масштаба пробелом. **978 байт**. | <img src="3dviewer/preview.gif" alt="3DViewer: вращение, масштаб и сброс ракурса с клавиатуры" width="272"> |
| [**3DEditor**](3deditor/README.md) | Просмотр и редактирование вершин, рёбер и граней: выбор, **g/r/s**, создание и удаление. **Зависит от [API 3DGraphics](graphics3d/API.md)**. **30 044 байт / 32 КБ**. | <img src="3deditor/preview.gif" alt="3DEditor: просмотр, выбор, трансформации и создание деталей" width="272"> |
| [**3DGraphics**](graphics3d/README.md) | Общий 3D-движок для Computer v2: **896 байт + до 128 байт модели**, цветные линии, кадр в LCD RAM, вращение и пульсация. Демонстрации куба, пирамиды, кристалла и цилиндра. Полный API с перспективой и заполнением граней **>1 КБ**, для эмулятора до **32 КБ**. | <img src="graphics3d/compact/models/cube/preview.gif" alt="3DGraphics 1K: цветной каркасный куб на общем движке" width="272"> |
