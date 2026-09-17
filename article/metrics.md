---
bibliography: config/references.bib
csl: config/style.csl
---
# Метрики Оцінки


## Chamfer Distance
Ця метрика оцінює відстань між двома хмарами точок (point clouds) за допомогою пошуку найближчих сусідів. У випадку з [@shenFlexibleIsosurfaceExtraction2023] на кожній із поверхонь обирається 100 000 точок для порівняння.
- [@heSparseFlexHighResolutionArbitraryTopology2025]
- [@xuInstantMeshEfficient3D2024]
- [@shenFlexibleIsosurfaceExtraction2023]
- [@chenNeuralMarchingCubes2021]
- [@parkDeepSDFLearningContinuous2019]
- [@meschederOccupancyNetworksLearning2019]



## F1 Score
Ця метрика обчислює гармонійне середнє між влучністю (precision) та повнотою (recall). Для обчислення обох складових обирається набір точок на поверхні Ground Truth та після результату перетворення. Розмір вибірки аналогічний до обчислення метрики Chamfer Distance. Після цього для кожної з точок знаходять найближчого сусіда. Для обчислення влучності (precision) порівнюється відстань від спрогнозованої поверхні до еталонної. Якщо вона менша за порогове значення то це вважається істинно позитивним, інакше - хибно позитивним. Для обчислення повноти навпаки перевіряється відстань від точки на еталонній поверхні до найближчої точки на спрогнозованій. Якщо ця відстань менша за порогове значення, то це враховується як істинно позитивне значення, інкаше як хибно негативне. В якості порогового значення у статті FlexiCubes  використовується 0.003 [@shenFlexibleIsosurfaceExtraction2023].
- [@heSparseFlexHighResolutionArbitraryTopology2025]
- [@xuInstantMeshEfficient3D2024] (As F-score)
- [@shenFlexibleIsosurfaceExtraction2023] (edged and vertices)
- [@chenNeuralMarchingCubes2021]


## Edge Chamfer Distance та Edge F1 score
Ці метрики призначені для оцінки відображення гострих особливостей сітки (граничних точок). Для отримання набору таких точок для кожної точки з вибірки обчислюється скалярний добуток між її нормаллю та нормалями її сусідів. Якщо середній скалярний добуток за граничне значення, то то така точка вважається граничною. З набору всіх точок спрогнозованої та еталонних поверхонь обирають лише граничні точки та для них обчислюється Chamfer Distance та F1 score.
- [@shenFlexibleIsosurfaceExtraction2023]
- [@chenNeuralDualContouring2022]
- [@chenNeuralMarchingCubes2021]


## PSNR

- [@xuInstantMeshEfficient3D2024]



## SSIM

- [@xuInstantMeshEfficient3D2024]



## LPIPS

- [@xuInstantMeshEfficient3D2024]



## Self-intersection

- [@hwangOccupancyBasedDualContouring2024a]


## Manifoldness

- [@hwangOccupancyBasedDualContouring2024a]


## Normal Consistency
Порівняння відмінності нормалей у прогнозованої поверхні з еталонною. Наприклад, [@shenFlexibleIsosurfaceExtraction2023] зберігає нормаль для кожної з обраних точок, потім знаходить найближчого сусіда на еталонній поверхні обчислює кут між ними. Для порівняння зберігають відсоток точок, у яких відхилення більше за 5 градусів.
- [@hwangOccupancyBasedDualContouring2024a]
- [@shenFlexibleIsosurfaceExtraction2023] Також вмимірюється відсоток невірних нормалей (більше 5 градусів)
- [@chenNeuralMarchingCubes2021]
- [@meschederOccupancyNetworksLearning2019]


## Кількість вершин

- [@shenFlexibleIsosurfaceExtraction2023]
- [@chenNeuralDualContouring2022]
- [@hwangOccupancyBasedDualContouring2024a]
- [@chenNeuralMarchingCubes2021]

## Кількість трикутників

- [@shenFlexibleIsosurfaceExtraction2023]
- [@chenNeuralDualContouring2022]
- [@hwangOccupancyBasedDualContouring2024a]
- [@chenNeuralMarchingCubes2021]


## Time

- [@hwangOccupancyBasedDualContouring2024a]
- [@chenNeuralDualContouring2022]
- [@shenFlexibleIsosurfaceExtraction2023]
- [@parkDeepSDFLearningContinuous2019]


## Memory usage

- [@shenFlexibleIsosurfaceExtraction2023]
- [@parkDeepSDFLearningContinuous2019]


## Earth Mover Distance

- [@parkDeepSDFLearningContinuous2019]


## Intersection Over Union

- [@meschederOccupancyNetworksLearning2019]

