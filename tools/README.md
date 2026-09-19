# Складальник рукопису: markdown → docx / LaTeX

`tools/build_article.py` збирає розділи з `article/*.md` у єдиний `.docx`, застосовуючи
стилі шаблону видавця, або в `.tex` (`-f tex`). Обидва формати рендеряться з того самого
markdown — конвертації між docx і tex немає, тому жоден з них не «псує» інший.
Формат подання до редакції лишається `.docx`; `.tex` потрібен для PDF-вичитки,
препринту та майбутнього англомовного варіанта (див. розділ «LaTeX» нижче).

Підтримуються два шаблони Word:

- **`springer`** (типово) — офіційний `article_tepmlate/Author.dotm`; складальник нічого
  не форматує вручну, а лише розставляє стилі шаблону, як вимагає інструкція Springer
  Nature (див. [RULES-SPRINGER.md](../RULES-SPRINGER.md));
- **`journal`** — `article_rules/Зразок_рукопису.docx`; складальник створює власні стилі
  «Article *» за типографікою з секції `[style]`.

Склад розділів і варіанти документа задаються профілями у `article-build.toml`.

## Встановлення

```bash
pip install python-docx latex2mathml lxml      # або: poetry install --with article
```

## Використання

```bash
python tools/build_article.py                             # профіль full -> build/manuscript.docx
python tools/build_article.py --list                      # набори стилів і профілі
python tools/build_article.py -p proofread                # інший профіль
python tools/build_article.py --styleset journal          # інший шаблон
python tools/build_article.py -s 05-rezultaty.md -o build/rezultaty.docx
python tools/build_article.py -p full --no-figures        # разове складання без рисунків
python tools/build_article.py -f tex                      # профіль full -> build/manuscript.tex
python tools/build_article.py -f both                     # docx і tex з того ж тексту
```

| Ключ | Призначення |
|---|---|
| `-p, --profile` | профіль з `article-build.toml` (типово `full`) |
| `--styleset` | перевизначити набір стилів профілю |
| `-c, --config` | інший файл конфігурації |
| `-s, --sections` | разове перевизначення складу розділів (імена файлів або glob) |
| `-f, --format` | `docx` (типово), `tex` або `both` |
| `-o, --output` | шлях до вихідного файлу (несумісний з `--format both`) |
| `-t, --template` | `.docx`/`.dotm`, з якого беруться стилі та поля сторінки |
| `--no-figures`, `--no-tables` | зібрати без ілюстрацій / без таблиць |
| `--list` | показати набори стилів і профілі та вийти |

Після складання скрипт друкує звіт: які розділи увійшли, який шаблон використано, чи
знайдено таблицю стилів для формул і які попередження виникли (відсутнє зображення,
відсутній стиль, таблиця, що не вміщується).

## Набори стилів (`[stylesets.*]`)

Набір стилів описує, як елементи рукопису лягають на стилі конкретного шаблону.

```toml
[stylesets.<назва>]
description           = "опис для --list"
template              = "article_tepmlate/Author.dotm"   # .docx або .dotm/.dotx
create_styles         = false   # true — створити власні стилі «Article *»
manual_formatting     = false   # true — задавати шрифти/кеглі на рівні тексту
strip_heading_numbers = false   # true — прибрати «2.1.» (шаблон нумерує сам)
auto_list_numbers     = false   # true — прибрати маркери списку (стиль нумерує сам)
plain_title           = true    # зняти номер глави й розрив сторінки зі стилю назви
equation_tab          = true    # вести виносну формулу табуляцією (стиль центрує по табстопу)
landscape_wide_tables = true    # таблиці, що не вміщуються, — на власну альбомну сторінку
fit_table_columns     = true    # рахувати ширини стовпців; false — довіритись шаблону
table_style           = "Table Grid"

[stylesets.<назва>.styles]      # роль -> назва стилю в шаблоні
title = "Main_Title"
body  = "para"
# ... решта ролей нижче
```

Ролі: `title`, `authors`, `affiliation`, `udc`, `abstract`, `keywords`,
`heading1`–`heading4`, `body`, `body_after_heading`, `equation`, `figure`,
`figure_caption`, `table_caption`, `table_cell`, `list`, `reference`,
`references_heading`, `code`.

Якщо названого стилю в шаблоні немає, складальник підставляє `Normal` і попереджає про це
у звіті — мовчазної підміни оформлення не буває.

## Профілі (`[profiles.*]`)

```toml
[profiles.<назва>]
description       = "опис для --list"
output            = "manuscript.docx"       # відносно build.output_dir
styleset          = "springer"              # набір стилів
sections          = ["00-titul-anotatsiya.md", "01-vstup.md"]   # порядок; glob дозволено
exclude           = ["manuscript_full.md"]  # що прибрати з розкритих glob
page_break_before = ["05-rezultaty.md"]     # розрив сторінки перед розділом
drop_sections     = ["^Джерела розділу"]    # службові блоки, що не йдуть до редакції
include_figures   = true
include_tables    = true
heading_offset    = 0                       # зсув рівнів заголовків (для збірок)

[profiles.<назва>.style]                    # перекриває глобальний [style]
line_spacing = 1.5

[profiles.<назва>.metadata]                 # властивості файлу docx
title  = "..."
author = "..."
```

Готові профілі: `full` (подання до редакції), `blind` (без титулу — для рецензування),
`abstract` (лише титул і резюме), `results` (методи + результати + обговорення),
`proofread` (без рисунків, полуторний інтервал), `draft` (кожен розділ з нової сторінки).

`drop_sections` — регулярні вирази; збіг видаляє блок і все далі до наступного заголовка
того ж або вищого рівня. Саме так із рукопису прибираються робочі таблиці
«Джерела розділу N».

## Що підтримує конвертер

- Заголовки `#`…`####`; титул і рядок авторів розпізнаються автоматично у преамбулі,
  резюме та ключові слова — за заголовком і за початком абзацу.
- Абзаци, жирний/курсив, `код`, посилання, мʼякі переноси (два пробіли в кінці рядка, `<br>`).
- Формули LaTeX: рядкові `$…$` та виносні `$$…$$` перетворюються на нативні формули Word
  (OMML) через `latex2mathml` + `MML2OMML.XSL` з комплекту MS Office. Якщо таблицю стилів
  не знайдено, формула вставляється як текст, а звіт складання це зазначає.
  Шлях можна задати явно: `build.math_xsl` або змінна оточення `MML2OMML_XSL`.
- Таблиці з вирівнюванням стовпців, повторюваним заголовком і автоматичним підбором ширин:
  стовпець ніколи не вужчий за найдовше слово; широка таблиця спершу виходить у поля
  (до `style.table_max_width_cm`), потім зменшується кегль (до
  `style.table_min_font_size_pt`), і лише тоді — альбомна сторінка.
- Рисунки `![alt](assets/…)` з масштабуванням до `style.figure_max_width_cm` і не ширше
  смуги набору.
- Підписи `*Таблиця N*` / `*Рис. N …*` отримують окремі стилі; підпис таблиці не
  відривається від самої таблиці.
- Нумеровані та марковані списки; список літератури — з висячим відступом і збереженням
  вихідної нумерації.
- Шаблони `.dotm`/`.dotx` відкриваються напряму: пакет перепаковується в памʼяті у
  звичайний документ (макроси відкидаються, стилі, нумерація та поля зберігаються).

## LaTeX (`[latex]`)

`-f tex` рендерить ті самі розділи в `.tex`. Роль кожного елемента рукопису (назва,
автори, афіліація, УДК, резюме, ключові слова) лягає на макрос преамбули так само, як у
docx вона лягає на стиль шаблону, — таблиця відповідності в `[latex.macros]`:

```toml
[latex]
engine = "xelatex"          # xelatex/lualatex: fontspec+polyglossia; pdflatex: T2A+babel
documentclass = "article"
bibliography = "thebibliography"

[latex.macros]
title = "arttitle"
```

Типографіка (кегль, інтерліньяж, абзацний відступ, кегль таблиць) береться з `[style]`,
тому docx і tex не розходяться. `define_macros = true` генерує визначення макросів у
преамбулі; щоб перейти на клас видавця, достатньо вимкнути його та описати власні
макроси через `preamble`. Профіль може перевизначити будь-який параметр у
`[profiles.<назва>.latex]`, а імʼя файлу — у `latex_output`.

Що робить рендерер:

- заголовки → `\section*`…`\paragraph*` (зірочка, бо нумерація вже є в тексті;
  `number_headings = true` віддає нумерацію LaTeX);
- виносні формули → `equation` (або `equation*`), рядкові — `$…$`; LaTeX із markdown
  переноситься без конвертації, тобто на відміну від docx проміжного OMML тут немає;
- рисунки → `figure` + `includegraphics` з відносним шляхом до `article/assets/`;
- таблиці → `booktabs`; таблиця, ширша за `wide_table_columns`, іде в `sidewaystable`
  і масштабується під висоту сторінки (`wide_table_resize`);
- підписи `*Рис. N*` / `*Таблиця N*` → `caption` з вимкненою автонумерацією
  (`number_captions = false`), бо номер уже є в тексті підпису;
- список літератури → `thebibliography` з `bibitem`; заголовок розділу підставляється в
  `refname`, а розбіжність нумерації джерел зі порядком потрапляє в попередження;
- URL у тексті обертаються в `url{}`, решта спецсимволів LaTeX екранується.

Компілятор у репозиторії не встановлюється; для збирання PDF потрібні XeLaTeX
(`texlive-xetex`, `texlive-lang-cyrillic`, `texlive-latex-extra`) та шрифт Times New
Roman або заміна в `latex.main_font`.

## Структура

| Файл | Призначення |
|---|---|
| `build_article.py` | CLI |
| `article_builder/config.py` | `article-build.toml`: набори стилів, профілі, типографіка, `[latex]` |
| `article_builder/template.py` | відкриття шаблону, зокрема `.dotm` |
| `article_builder/mdparse.py` | markdown → блоки |
| `article_builder/inline.py` | рядкова розмітка → форматовані фрагменти |
| `article_builder/semantics.py` | розпізнавання ролей елементів (спільне для обох рендерерів) |
| `article_builder/omml.py` | LaTeX → OMML |
| `article_builder/docx_writer.py` | блоки → docx за ролями стилів |
| `article_builder/latex_writer.py` | блоки → LaTeX за ролями макросів |
| `article_builder/builder.py` | звʼязує все разом |
