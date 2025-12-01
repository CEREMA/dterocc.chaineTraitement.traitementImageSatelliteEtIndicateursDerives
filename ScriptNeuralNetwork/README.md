# Neural Network Segmentation

Ce dépot contient la pipeline pour la **segmentation sémantique supervisée** d'images satelittes, à l'aide d'un Deep ResU-net configurable via un script shell `run_segmentation.sh` et codé dans le fichier `NeuralNetworkSegmentation.py`

## Requirements

- **Keras** 3.10.0
- **Tensorflow** 2.19.0

En sachant que les temps d'entrainement sont très long, il est préférable d'utiliser une carte GPU pour cette phase. Un CPU suffit pour l'inférence.
Par ailleurs, il est fortement recommandé de travailler avec des fichiers uniquement dans le RAM_disk

Le prétraitement des données s'appuie sur plusieurs fonctions issues de la Chaine de Traitement du CEREMA et plus particulièrement des libraires :
- `Lib_display.py`
- `Lib_log.py`
- `Lib_operator.py`
- `Lib_vector.py`
- `QualityIndicatorComputation.py`
- `Lib_raster.py`
- `Lib_text.py`

## Shell script

`run_segmentation.sh` : ce script permet de configurer et exécuter le Deep ResU-net

### Généralité

Les arguments du script se répartissent en deux catégories :
- Les arguments à valeur explicite, pour lesquels une valeur doit être fournie explicitement :
- Les arguments booléens, qui activen (ou désactivent) une option lorsqu'ils sont présents.

<details>
<summary>Voir les arguments à valeur explicite</summary>

```markdown
    ***Chemins***

- `input_raster_path` => Chemin vers l'image d'entrée (déjà stackée et normalisée) ('.tif')
- `groundtruth_path` => Chemin vers la vérité terrain ('.tif')
- `output_raster_path` => Chemin vers l'image prédite par le modèle ; ne doit pas être un fichier existant (.'tif')

- `model_input` => Chemin vers un modèle que l'on souhaite réentrainer ou avec lequel on souhaite inférer ('.hdv5' ou '.keras')
- `model_output` => Chemin vers le modèle que l'on souhaite générer après l'entrainement ('.keras')

- `vector_train` => Chemin vers le vecteur délimitant l'emprise de la zone d'entrainement ('.shp')
- `vector_valid` => Chemin vers le vecteur délimitant l'emprise de la zone de validation ('.shp')
- `vector_test` => Chemin vers le vecteur délimitant l'emprise de la zone de test ('.shp')

- `grid_path` => Chemin vers la grille de découpe des imagettes si elle existe déjà ('.shp')

- `evaluation_path` => Chemin vers le fichier servant à l'évaluation de notre modèle après l'inférence ('.shp' ou '.tif')

    ***Paramètres***

- `number_class` => Nombre de classe sans compter le background (*int*)
- `neural_network_mode="resunet"` => Pas d'autres modes pour le moment

- `size_grid` => Taille des imagettes (avant débord) (*int*)
- `debord` => Taille du débord souhaité (*int*)

- `batch` => Taille des batchs (*int*)
- `n_conv_filter` => Nombre de filtres en entrée du réseau (*int*)
- `kernel_size` => Taille des filtres , constante dans tout le réseau (*int*)
- `dropout_rate` => Coefficient de spatial Dropout dans l'espace latent (*float*)
- `l2_reg` => Coefficient de régularisation L2 appliqué aux poids du réseau (*float*)
- `alpha_loss` => Coefficient pour la focal loss, il doit y en avoir number_class +1 (*string*)

- `number_epoch` => Nombre max d'époch pour l'entrainement (*int*)
- `es_monitor` =>Métrique surveillée pour l'early stopping (*string*)
- `es_patience` => Nombre d'époch de patience pour l'early stopping (*int*)
- `es_min_delta` => Variation minimale pour l'early stopping (*float*)
- `rl_monitor` => Métrique surveillée pour la mise à jour du learning rate (*string*)
- `rl_factor` => Facteur de diminution du learning rate (*float*)
- `rl_patience` => Nombre d'époch de patience avant diminution du learning rate (*int*)
- `rl_min_lr` => Valeur minimal du learning rate (*float*)

- `id_graphic_card` => Si plusieurs carte GPU, id de la carte que l'utilisateur souhaite utiliser (*int*)
- `percent_no_data` => Pourcentage de NoData autorisée avant de supprimer une imagette de l'entrainement (*int*)
```
</details>


<details>
<summary>Voir les arguments booléens</summary>

```markdown
`-at`   # Si présent, active l'augmentation de données pendant l'entraînement
`-now`  # Si présent, empêche l'écrasement des fichiers existants (overwrite désactivé)
`-ugc`  # Si présent, active l'utilisation du GPU
`-sav`  # Si présent, conserve les fichiers temporaires intermédiaires
`-cb`  # Si présent, complète l'arrière plan en associant aux pixels de la classe 0 la 2ème classe la plus probable

```
</details>


### Lancer un entrainement et une classification

Pour entrainer (et générer un nouveau modèle) et une classification les arguments obligatoires sont :
- `input_raster_path`
- `output_raster_path`
- `groundtruth_path`
- `model_output`
- `vector_train`
- `vector_valid`
- `vector_test`
Et il faut nécessairement `model_input=""`

### Lancer simplement une classification

Pour générer une classification à partir d'un modèle déjà entrainé les arguments obligatoires sont :
- `input_raster_path`
- `output_raster_path`
- `model_input`
- `vector_test`

Et il faut nécessairement `groundtruth_path=""`

### Lancer un ré entrainement et une classification

Dernier cas, pour ré entrainer un modèle déjà entrainé et générer une classification alors les arguments obligatoires sont:
- `input_raster_path`
- `output_raster_path`
- `model_input`
- `groundtruth_path`
- `vector_train`
- `vector_valid`
- `vector_test`

---

## Script NeuralNetwork.py
`NeuralNetworkSegmentation.py` : ce fichier contient toutes les fonctions définissant le réseau, permettant le prétraitement ainsi que l'entrainement et l'inférence.

### Généralité


ps : ce qui est codé en dur: le facteur d'augmentation
