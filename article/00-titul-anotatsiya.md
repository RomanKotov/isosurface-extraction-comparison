<!-- Профіль journal (7-розділова схема). Вимоги: article_rules/Зразок_рукопису.docx
     Титульна частина рукопису:
     УДК, назва (орієнтована на результат), автори, резюме (1800–1900 знаків із пробілами),
     ключові слова (рівно 10 слів). -->

**УДК 004.92:519.6**

# Полігонізація геометричних моделей, заданих R-функціями, методом FlexiCubes

**А. Б. Лісняк, Р. О. Котов, С. В. Чопоров**

Кафедра програмної інженерії, математичний факультет, Запорізький національний університет, Запоріжжя, Україна

# FlexiCubes-Based Polygonization of Geometric Models Defined by R-Functions

**Andrii Lisniak, Roman Kotov, Serhii Choporov**

Department of Software Engineering, Faculty of Mathematics, Zaporizhzhia National University, Zaporizhzhia, Ukraine

---

### Резюме

*Об'єктом дослідження є процес просторової дискретизації неперервних тривимірних областей, аналітично заданих за допомогою апарату R-функцій, у трикутні поверхневі сітки для препроцесингу методу скінченних елементів (МКЕ). Однією з найскладніших проблем при підготовці моделей інженерного аналізу є деградація якості розрахункових сіток, що проявляється в утворенні вироджених трикутників (sliver-елементів) з кутами менше 10°, появі нерізноманітних топологічних дефектів та геометричному спотворенні ліній гострих ребер і концентраторів напружень. У роботі встановлено фундаментальні закономірності формування розрахункових поверхонь при використанні прямого алгоритму Marching Cubes (MC), двоїстих методів Dual Marching Cubes (DMC) і Dual Contouring (DC) та варіаційного методу FlexiCubes (FC). Встановлено, що класичний алгоритм MC генерує від 4.08 % до 9.74 % вироджених sliver-трикутників із критично малими кутами менше 0.5°, що спричиняє погану обумовленість глобальної матриці жорсткості МКЕ. На противагу цьому алгоритм DMC за рахунок центроїдного позиціонування вершин у внутрішніх полігонах первинного розбиття забезпечує стабільний мінімальний плоский кут від 14.03° до 15.66° при строго нульовій частці sliver-елементів (0.00 %) та гарантованому збереженні топологічної герметичності. Виявлено, що алгоритм DC на полях R-функцій високого порядку зазнає чисельної деградації через погану обумовленість функціоналу QEF (похибка поверхні досягає 4.285 комірок, частка sliver-елементів зростає до 24.01 %). Доведено, що варіаційний метод FlexiCubes у поєднанні з оптимізацією зменшує нев'язку поверхні у 2.1 раза (до 0.086 комірки), а запропоновані багатостадійні конвеєри геометричної постобробки забезпечують кут більше 21.37° при тривалості обчислень лише 0.168 с. Отримані результати можуть бути безпосередньо застосовані в автоматизованих препроцесорах САПР/CAE.*

**Ключові слова**: R-функції, неявне геометричне моделювання, ізоповерхнева екстракція, Marching Cubes, Dual Contouring, Dual Marching Cubes, FlexiCubes, якість розрахункової сітки, метод скінченних елементів, sliver-елементи.

---

### Abstract

*The object of the study is the spatial discretization of continuous three-dimensional domains analytically defined using the R-functions framework into triangular surface meshes intended for finite element method (FEM) preprocessing. One of the most critical challenges in preparing engineering analysis models is mesh quality degradation, manifested by the formation of degenerate triangular elements (slivers) with planar angles below 10°, topological non-manifold defects, and the distortion of sharp feature creases and stress concentration zones. This paper establishes fundamental regularities of surface mesh generation when applying the primal Marching Cubes (MC) algorithm, dual schemes including Dual Marching Cubes (DMC) and Dual Contouring (DC), and the variational FlexiCubes (FC) method. It was determined that the classical MC algorithm generates between 4.08% and 9.74% degenerate sliver triangles with minimal angles below 0.5°, leading to severe ill-conditioning of the global FEM stiffness matrix. In contrast, DMC utilizes centroid positioning of vertices within internal primal polygons, guaranteeing a stable minimum planar angle between 14.03° and 15.66°, a strictly zero fraction of sliver elements (0.00%), and complete topological watertightness. The DC algorithm is found to experience severe numerical degradation on high-order R-function fields due to the ill-conditioning of the QEF functional (surface error reaching 4.285 cells, sliver fraction rising to 24.01%). The variational FlexiCubes method combined with optimization reduces surface residual by a factor of 2.1 (down to 0.086 cells), while proposed multi-stage post-processing pipelines achieve angles exceeding 21.37° in only 0.168 s. The obtained results can be directly applied in automated CAD/CAE preprocessors.*

**Keywords**: R-functions, implicit surface modeling, isosurface extraction, Marching Cubes, Dual Contouring, Dual Marching Cubes, FlexiCubes, mesh quality control, finite element method, sliver elements.

---
