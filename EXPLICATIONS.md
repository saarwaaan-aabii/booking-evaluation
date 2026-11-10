# Explications du code — Booking Evaluation

Ce document explique, pas à pas et en français simple, le code écrit pour les 4 tâches.
Il est pensé pour quelqu'un qui débute en Python et en Django.

## Sommaire

1. [Vue d'ensemble : comment une requête traverse le projet](#1-vue-densemble)
2. [Tâche 1 — Le template HTML (`catalogue.html`)](#2-tâche-1--le-template-html)
3. [Tâche 2 — Le serializer (`serializers.py`)](#3-tâche-2--le-serializer)
4. [Tâche 3 — La vue API (`views.py`)](#4-tâche-3--la-vue-api)
5. [Tâche 4 — Le rapport JSON (`reports.py`)](#5-tâche-4--le-rapport-json)
6. [Lancer les tests](#6-lancer-les-tests)
7. [Petit lexique](#7-petit-lexique)

---

## 1. Vue d'ensemble

### Les données

Deux tables sont liées entre elles (`rooms/models.py`) :

```
Table rooms_room                          Table rooms_location
┌──────────┬────────────┬──────────┬─────────────┐   ┌──────┬────────┐
│ code     │ name       │ capacity │ location_id │   │ code │ city   │
├──────────┼────────────┼──────────┼─────────────┤   ├──────┼────────┤
│ lyo-desk │ Open desk  │ 4        │ lyo ────────┼──►│ lyo  │ Lyon   │
│ lyo-room │ Meeting rm │ 6        │ lyo ────────┼──►│ lyo  │ Lyon   │
│ par-desk │ Focus desk │ 2        │ par ────────┼──►│ par  │ Paris  │
└──────────┴────────────┴──────────┴─────────────┘   └──────┴────────┘
```

Une salle (`Room`) ne contient **pas** le nom de la ville : elle contient seulement un **lien**
(`location`) vers une ligne de la table `Location`. En Python on écrit :

```python
room.location.city   # → "Lyon"
```

### Le chemin d'une requête API

```
Navigateur : GET /api/rooms/?city=Lyon
      │
      ▼
urls.py ──► RoomListView (views.py)       « quelles salles ? »
                 │
                 ▼
            RoomSerializer (serializers.py)   « comment les écrire en JSON ? »
                 │
                 ▼
            [{"code": "lyo-desk", "name": "Open desk", "capacity": 4, "location_city": "Lyon"}, ...]
```

| Élément | Son rôle | Analogie restaurant |
|---|---|---|
| **Vue** | choisit les salles à renvoyer | le serveur qui prend la commande |
| **Serializer** | traduit chaque salle en JSON | le cuisinier qui prépare l'assiette |
| **Modèle** | décrit les tables en base | le garde-manger |

---

## 2. Tâche 1 — Le template HTML

**Fichier :** `rooms/templates/rooms/catalogue.html`

```django
<ul>
    {% for room in rooms %}
        <li>
            <strong>{{ room.code }}</strong> —
            {{ room.name }} —
            {{ room.location.city }} —
            {{ room.capacity }} seats
        </li>
    {% empty %}
        <li>No rooms available.</li>
    {% endfor %}
</ul>
```

| Élément | Sens |
|---|---|
| `{% for room in rooms %}` | répète le bloc pour chaque salle. `rooms` est envoyé par la vue `web_views.py` |
| `{{ room.code }}` | affiche une valeur. Les doubles accolades = « affiche ça » |
| `{{ room.location.city }}` | suit le lien vers `Location` pour afficher la ville |
| `{{ room.capacity }} seats` | affiche par exemple `4 seats` |
| `{% empty %}` | ce qui s'affiche **à la place** de la boucle si la liste est vide |
| `{% endfor %}` | fin de la boucle |

### Pourquoi `{{ ... }}` protège la page (échappement HTML)

Si quelqu'un nomme une salle `<script>alert(1)</script>`, Django l'affiche comme du **texte**
(`&lt;script&gt;…`) au lieu de l'exécuter comme du code. C'est automatique avec `{{ ... }}`.
Il ne faut **pas** ajouter `|safe`, qui désactiverait cette protection.

---

## 3. Tâche 2 — Le serializer

**Fichier :** `rooms/serializers.py`

```python
class RoomSerializer(serializers.ModelSerializer):
    location_city = serializers.CharField(source='location.city', read_only=True)

    class Meta:
        model = Room
        fields = ['code', 'name', 'capacity', 'location_city']
        read_only_fields = fields
```

### 3.1 À quoi sert un serializer ?

En base, une salle est un **objet Python**. Une API doit renvoyer du **JSON** (du texte).
Le serializer fait la **traduction** :

```
Objet Room (Python)  ──serializer──►  {"code": "lyo-desk", "name": "Open desk", ...}
```

`ModelSerializer` est la version automatique : on lui donne le modèle, il devine comment traduire
les champs simples.

### 3.2 `class Meta` — la fiche de réglages

```python
class Meta:
    model = Room                                            # ① quel modèle traduire
    fields = ['code', 'name', 'capacity', 'location_city']  # ② quelles clés dans le JSON
    read_only_fields = fields                               # ③ tout en lecture seule
```

- **① `model = Room`** : le serializer lit `models.py` et sait que `code` est du texte, `capacity` un entier…
- **② `fields`** : la liste **exacte** des clés du JSON. Rien de plus, rien de moins.
- **③ `read_only_fields`** : voir 3.5.

### 3.3 `source='location.city'` — aller chercher la ville

`code`, `name` et `capacity` sont **directement dans `Room`** : `ModelSerializer` les trouve seul.

`location_city` **n'existe pas dans `Room`**. La ville est dans une **autre table**. On déclare donc
ce champ à la main et on dit où chercher :

```python
location_city = serializers.CharField(source='location.city', read_only=True)
#  ↑ nom dans le JSON      ↑ c'est du texte   ↑ où chercher : room.location.city
```

### 3.4 Comment `'location_city'` (texte) est relié à la variable `location_city`

C'est **par le nom**. DRF range chaque champ déclaré à la main dans un dictionnaire :

```python
champs_declares = {'location_city': CharField(source='location.city', read_only=True)}
```

Puis, pour chaque nom de `fields`, il fait à peu près :

```python
for nom in fields:
    if nom in champs_declares:                      # écrit à la main ?
        champ = champs_declares[nom]                # → on prend le vôtre
    else:
        champ = deviner_depuis_le_modele(Room, nom) # → sinon on le devine
```

| Nom dans `fields` | Déclaré à la main ? | Existe dans `Room` ? | Résultat |
|---|---|---|---|
| `'code'` | non | oui | créé automatiquement |
| `'name'` | non | oui | créé automatiquement |
| `'capacity'` | non | oui | créé automatiquement |
| `'location_city'` | **oui** | — | **votre `CharField`** |

Les deux noms doivent donc être écrits **exactement pareil**. Une faute de frappe provoque une erreur.

### 3.5 `read_only=True` et `read_only_fields = fields`

Un serializer marche dans **deux sens** :

```
LECTURE   : Room ──► JSON    (GET  : on affiche)
ÉCRITURE  : JSON ──► Room    (POST : on crée / modifie)
```

« Lecture seule » = le champ s'affiche, mais toute valeur envoyée pour lui est **ignorée**.
L'API sert seulement à consulter, donc les 4 champs sont en lecture seule.

Il faut **les deux lignes**, car elles ne visent pas les mêmes champs :

| Champ | Créé comment ? | Rendu lecture seule par |
|---|---|---|
| `location_city` | **à la main** | `read_only=True` |
| `code`, `name`, `capacity` | **automatiquement** | `read_only_fields` |

Règle de DRF : `read_only_fields` ne s'applique **qu'aux champs créés automatiquement**.
`read_only_fields = fields` est un raccourci pour `['code', 'name', 'capacity', 'location_city']`.

Le test vérifie ceci :

```python
serializer = RoomSerializer(data={'code': 'x', 'name': 'X', 'capacity': 20, 'location_city': 'Paris'})
serializer.is_valid()        # True
serializer.validated_data    # {}  ← vide : rien n'est retenu
```

---

## 4. Tâche 3 — La vue API

**Fichier :** `rooms/views.py`

```python
class RoomListView(generics.ListAPIView):
    serializer_class = RoomSerializer
    queryset = Room.objects.select_related('location').order_by('code')

    def get_queryset(self):
        queryset = super().get_queryset()
        city = self.request.query_params.get('city')
        if city is None:
            return queryset
        city = city.strip()
        if not city:
            raise ValidationError({'city': 'This parameter cannot be blank.'})
        return queryset.filter(location__city__iexact=city)
```

Une **vue** est le code qui répond quand quelqu'un appelle une URL. `urls.py` relie
`/api/rooms/` à `RoomListView`.

### 4.1 `class RoomListView(generics.ListAPIView)` — l'héritage

Les parenthèses veulent dire que `RoomListView` **hérite** de `ListAPIView` : elle récupère tout son
code sans le recopier. `ListAPIView` sait **afficher une liste** (`GET`) et rien d'autre.

Conséquence : un `POST` renvoie automatiquement **405 (méthode non autorisée)**. L'API est en
lecture seule sans écrire une ligne de plus.

### 4.2 `serializer_class = RoomSerializer` — où est-ce utilisé ?

On ne voit cette variable utilisée nulle part dans notre fichier : elle est lue **dans le code de
DRF** (la classe parente). Quand `GET /api/rooms/` arrive, DRF exécute en coulisses
(extraits réels de `rest_framework/generics.py` et `mixins.py`) :

```python
# ① ListAPIView.get
def get(self, request, *args, **kwargs):
    return self.list(request, *args, **kwargs)

# ② ListModelMixin.list
def list(self, request, *args, **kwargs):
    queryset = self.filter_queryset(self.get_queryset())   # ← NOTRE get_queryset
    serializer = self.get_serializer(queryset, many=True)
    return Response(serializer.data)

# ③ GenericAPIView.get_serializer
def get_serializer(self, *args, **kwargs):
    serializer_class = self.get_serializer_class()
    return serializer_class(*args, **kwargs)              # ← RoomSerializer(queryset, many=True)

# ④ GenericAPIView.get_serializer_class
def get_serializer_class(self):
    assert self.serializer_class is not None, "... should include a `serializer_class` attribute ..."
    return self.serializer_class                          # ← NOTRE serializer_class
```

DRF définit `serializer_class = None` par défaut. Notre ligne **remplace** ce `None`, car Python
cherche d'abord dans notre classe, puis dans les classes parentes. Sans elle, l'`assert` de l'étape ④
fait planter la vue.

C'est comme un **formulaire à remplir** : DRF a écrit tout le traitement, on remplit juste les cases
(`serializer_class`, `queryset`).

### 4.3 `queryset = Room.objects.select_related('location').order_by('code')`

Un **queryset** est une requête vers la base, préparée mais **pas encore exécutée**.

| Morceau | Sens |
|---|---|
| `Room.objects` | dans la table des salles… |
| `.select_related('location')` | …ramène aussi leur ville **dans la même requête** |
| `.order_by('code')` | …triées par code, de A à Z |

#### Pourquoi `select_related` ? (le problème « N+1 »)

Mesuré sur ce projet, pour afficher les 5 salles **avec leur ville** :

| | SQL envoyé | Nombre de requêtes |
|---|---|---|
| **Sans** `select_related` | `SELECT … FROM rooms_room ORDER BY code`, puis 1 requête par salle pour sa ville | **6** |
| **Avec** `select_related` | `SELECT … FROM rooms_room INNER JOIN rooms_location ON … ORDER BY code` | **1** |

Le `JOIN` colle les deux tables en une seule fois. Avec 1 000 salles, on passerait de 1 001 requêtes
à 1. C'est ce que demande la consigne : « éviter des requêtes répétées ».

#### La requête attend avant de partir

Écrire cette ligne ne contacte pas la base. La requête part seulement quand on a besoin des données
(quand le serializer parcourt les salles). On peut donc encore ajouter un `.filter()` ensuite, sans
requête en plus.

### 4.4 `get_queryset` — lire et vérifier le paramètre `city`

DRF appelle `get_queryset()` à chaque requête pour savoir quelles salles renvoyer.

```python
queryset = super().get_queryset()   # le queryset défini plus haut (toutes les salles, triées)
city = self.request.query_params.get('city')
```

`query_params.get('city')` lit `?city=...` dans l'URL. `.get()` renvoie `None` si le paramètre
n'existe pas, au lieu de planter.

| URL | Valeur de `city` |
|---|---|
| `/api/rooms/` | `None` (absent) |
| `/api/rooms/?city=` | `""` (vide) |
| `/api/rooms/?city=   ` | `"   "` (que des espaces) |
| `/api/rooms/?city=  lYoN  ` | `"  lYoN  "` |

### 4.5 `city is None` **vs** `city.strip()` + `if not city`

Ce sont **deux questions différentes** :

- **`city is None`** → le paramètre est-il **absent** ? → c'est normal : on renvoie **tout** (200).
- **`if not city`** (après `strip`) → il est **présent mais vide** ? → demande mal formée : **400**.

```python
if city is None:              # ① ABSENT
    return queryset           #    → toutes les salles

city = city.strip()           # ② enlève les espaces autour : "  lYoN  " → "lYoN", "   " → ""
if not city:                  # ③ PRÉSENT mais VIDE
    raise ValidationError(...)#    → 400
```

**Pourquoi cet ordre ?**

1. On teste `None` **en premier**, car `None.strip()` plante (`AttributeError`).
2. On fait `strip()` **avant** le test « vide », sinon `"   "` (3 espaces) serait considéré comme
   non vide et renverrait `[]` au lieu de 400.
3. On n'écrit pas seulement `if not city` au début, car `not None` vaut aussi `True` : une requête
   **sans** paramètre recevrait alors une erreur 400 au lieu de la liste complète.

`if not city` marche parce qu'en Python `""`, `None`, `0` et `[]` comptent comme « faux ».

`raise ValidationError(...)` arrête la vue ; DRF la transforme en réponse **400** avec le message
JSON `{"city": "This parameter cannot be blank."}`, au lieu d'un plantage 500.

```
city = get('city')
      │
      ├─ None ? ──────────────► oui → toutes les salles (200)
      ▼ non
city = city.strip()
      │
      ├─ vide ("") ? ─────────► oui → erreur (400)
      ▼ non
filtre par ville (iexact) ─────► 200 (liste, éventuellement [])
```

### 4.6 `return queryset.filter(location__city__iexact=city)`

`.filter(...)` garde seulement les salles qui respectent la condition.

Dans un filtre, Django utilise le **double underscore `__`** pour dire « aller dans… » (on ne peut
pas écrire de point dans un nom de paramètre) :

```
location   __   city   __   iexact
   │              │            └─ comment comparer : égal, sans tenir compte des majuscules
   │              └─ quel champ : la ville
   └─ suis le lien vers la table Location
```

C'est l'équivalent de `room.location.city == city`, mais fait **par la base de données**.

| Mot-clé | Sens | `"lyon"` trouve `"Lyon"` ? |
|---|---|---|
| `exact` | exactement égal | ❌ |
| **`iexact`** | égal, **sans tenir compte de la casse** (`i` = *insensitive*) | ✅ |

**Pourquoi `filter` et pas `get` ?**

| Méthode | Renvoie | Si rien ne correspond |
|---|---|---|
| `.get(...)` | **un seul** objet | ❌ plante (`DoesNotExist`) |
| `.filter(...)` | une **liste** (0, 1 ou plusieurs) | ✅ liste vide `[]` |

Le tri et le `select_related` sont **conservés** : le filtre s'ajoute au queryset existant, et tout
reste en **une seule requête**.

### 4.7 Résumé des cas

| Requête | Ce qui se passe | Réponse |
|---|---|---|
| `GET /api/rooms/` | pas de `city` | 200, les 5 salles triées |
| `GET /api/rooms/?city=  lYoN  ` | nettoyé, comparé sans casse | 200, `lyo-desk`, `lyo-room` |
| `GET /api/rooms/?city=Rennes` | aucune salle | 200, `[]` |
| `GET /api/rooms/?city=    ` | vide après `strip` | **400** |
| `POST /api/rooms/` | `ListAPIView` n'accepte que GET | **405** |

---

## 5. Tâche 4 — Le rapport JSON

**Fichier :** `rooms/reports.py`

Toutes les valeurs montrées dans cette partie sont des **résultats réels**, obtenus en lançant le
code sur la base du projet.

### Le code complet

```python
import json
from django.db.models import Sum
from rooms.models import Location, Room

def export_city_summary(city: str) -> str:
    if not isinstance(city, str) or not city.strip():                      # 5.2
        raise ValueError('city must be a non-empty string')
    requested = city.strip()                                               # 5.3

    location = Location.objects.filter(city__iexact=requested).first()     # 5.4
    city_name = location.city if location else requested                   # 5.5

    rooms = Room.objects.filter(location__city__iexact=requested)          # 5.6
    total_capacity = rooms.aggregate(total=Sum('capacity'))['total'] or 0  # 5.7
    room_codes = sorted(rooms.values_list('code', flat=True))              # 5.8

    return json.dumps({                                                    # 5.9
        'city': city_name,
        'total_rooms': len(room_codes),
        'total_capacity': total_capacity,
        'room_codes': room_codes,
    })
```

### 5.1 Ce que fait la fonction, en une phrase

On lui donne un **nom de ville**, elle renvoie un **texte JSON** qui résume les salles de cette ville.

| Appel | Résultat réel |
|---|---|
| `export_city_summary('Lyon')` | `{"city": "Lyon", "total_rooms": 2, "total_capacity": 10, "room_codes": ["lyo-desk", "lyo-room"]}` |
| `export_city_summary('  lyon  ')` | `{"city": "Lyon", "total_rooms": 2, "total_capacity": 10, "room_codes": ["lyo-desk", "lyo-room"]}` |
| `export_city_summary('PARIS')` | `{"city": "Paris", "total_rooms": 2, "total_capacity": 12, "room_codes": ["par-desk", "par-room"]}` |
| `export_city_summary('Rennes')` | `{"city": "Rennes", "total_rooms": 0, "total_capacity": 0, "room_codes": []}` |
| `export_city_summary('')`, `('   ')`, `(None)`, `(13)` | ❌ `ValueError: city must be a non-empty string` |

`def export_city_summary(city: str) -> str:` se lit ainsi : « la fonction reçoit `city`, qui devrait
être du texte (`: str`), et renvoie du texte (`-> str`) ». Ces indications sont des **notes pour les
humains** : Python ne les vérifie pas tout seul. C'est pour ça qu'on vérifie nous-mêmes à l'étape 5.2.

> **📌 Résumé 5.1** — Entrée : un nom de ville. Sortie : un texte JSON avec 4 clés
> (`city`, `total_rooms`, `total_capacity`, `room_codes`). Entrée invalide → `ValueError`.

---

### 5.2 Vérifier l'entrée : `isinstance` et `strip`

```python
if not isinstance(city, str) or not city.strip():
    raise ValueError('city must be a non-empty string')
```

Cette ligne pose **deux questions**, reliées par `or` (« ou »).

**Question A — `not isinstance(city, str)` : est-ce que ce n'est PAS du texte ?**

`isinstance(valeur, type)` vérifie **de quel type** est une valeur. `str` (*string*) = le type texte.

```python
isinstance("Lyon", str)   # True  → c'est du texte
isinstance(None, str)     # False → ce n'est pas du texte
isinstance(13, str)       # False → c'est un nombre
```

**Question B — `not city.strip()` : est-ce que le texte est VIDE ?**

`.strip()` enlève les espaces au début et à la fin. Un texte vide compte comme « faux » en Python.

```python
"".strip()        # → ""      → vide
"   ".strip()     # → ""      → vide
" Lyon ".strip()  # → "Lyon"  → pas vide
```

**Pourquoi la question A d'abord ? L'ordre compte.**

Avec `or`, Python **s'arrête dès que la première condition est vraie** : il ne regarde pas la seconde.
C'est indispensable, car `None.strip()` et `(13).strip()` **plantent** (`AttributeError`) : seul
le texte possède la méthode `.strip()`.

| `city` | A : pas du texte ? | B : vide ? | Résultat réel |
|---|---|---|---|
| `None` | ✅ oui → **stop** | *(pas évaluée)* | `ValueError` |
| `13` | ✅ oui → **stop** | *(pas évaluée)* | `ValueError` |
| `""` | non | ✅ oui | `ValueError` |
| `"   "` | non | ✅ oui | `ValueError` |
| `"  lyon  "` | non | non | ✅ on continue |

**`raise ValueError(...)`**

`raise` = « déclencher une erreur et **arrêter la fonction ici** ». `ValueError` est l'erreur standard
de Python pour « valeur non acceptable ».

| Où | Erreur utilisée | Pourquoi |
|---|---|---|
| Vue API (`views.py`) | `ValidationError` (DRF) | DRF la transforme en réponse HTTP **400** |
| Rapport (`reports.py`) | `ValueError` (Python) | simple fonction Python, pas d'API |

> **📌 Résumé 5.2** — On refuse ce qui n'est pas du texte (`None`, `13`) **puis** le texte vide
> (`""`, `"   "`). La question « est-ce du texte ? » vient en premier pour ne jamais appeler
> `.strip()` sur autre chose que du texte. Erreur → `ValueError`.

---

### 5.3 Nettoyer : `requested = city.strip()`

```python
requested = city.strip()
```

On garde la version **sans espaces** dans une nouvelle variable, `requested` (« demandée »).

| Avant | Après |
|---|---|
| `"  lyon  "` | `"lyon"` |
| `"PARIS"` | `"PARIS"` (les majuscules restent, seuls les espaces partent) |

On n'arrive ici **que si** l'étape 5.2 est passée : `city` est forcément du texte non vide.

> **📌 Résumé 5.3** — `requested` = le nom demandé, sans les espaces autour.

---

### 5.4 Chercher la ville en base : `filter(...).first()`

```python
location = Location.objects.filter(city__iexact=requested).first()
```

| Morceau | Sens |
|---|---|
| `Location.objects` | dans la table des villes… |
| `.filter(city__iexact=requested)` | …celles dont le nom est égal à `requested`, **sans tenir compte des majuscules** |
| `.first()` | …prends **la première**, ou `None` s'il n'y en a pas |

Ici c'est `city__iexact` (et pas `location__city__iexact`) parce qu'on cherche **directement dans
la table `Location`** : pas de lien à suivre.

**Avant / après `.first()` (résultats réels) :**

| Écriture | `'lyon'` | `'rennes'` |
|---|---|---|
| `.filter(...)` | `<QuerySet [<Location: Lyon>]>` (une **liste**) | `<QuerySet []>` (liste vide) |
| `.filter(...).first()` | `Lyon` (**un seul objet**) | `None` |
| `.get(...)` | `Lyon` | ❌ **plante** (`DoesNotExist`) |

`.first()` donne le meilleur des deux : **un objet** si la ville existe, **`None`** sinon, sans erreur.

> **📌 Résumé 5.4** — On cherche la ville sans tenir compte des majuscules. Résultat : l'objet
> `Location` si elle existe, sinon `None` (pas de plantage, contrairement à `.get()`).

---

### 5.5 Choisir le nom à afficher : `... if ... else ...`

```python
city_name = location.city if location else requested
```

C'est un **« si… sinon » écrit sur une seule ligne** :

```python
resultat = VALEUR_SI_VRAI if CONDITION else VALEUR_SI_FAUX
```

Ça fait **exactement la même chose** que :

```python
if location:
    city_name = location.city
else:
    city_name = requested
```

`if location` : un objet compte comme **vrai**, `None` compte comme **faux**. Donc la condition
veut dire « si on a trouvé la ville en base ».

| Demandé | `requested` | `location` | `city_name` |
|---|---|---|---|
| `"  lyon  "` | `"lyon"` | `Lyon` (trouvée) | **`"Lyon"`** (orthographe de la base) |
| `"PARIS"` | `"PARIS"` | `Paris` (trouvée) | **`"Paris"`** |
| `"Rennes"` | `"Rennes"` | `None` | **`"Rennes"`** (nom demandé) |

**Pourquoi pas toujours `requested` ?** La consigne veut l'orthographe **de la base** : `"Lyon"`,
pas `"lyon"`.
**Pourquoi pas toujours `location.city` ?** Pour une ville inconnue, `location` vaut `None`, et
`None.city` **plante**.

> **📌 Résumé 5.5** — Ville trouvée → son orthographe officielle (`"Lyon"`). Ville inconnue → le
> nom demandé, nettoyé (`"Rennes"`). Le `if location` évite le plantage `None.city`.

---

### 5.6 Les salles de la ville

```python
rooms = Room.objects.filter(location__city__iexact=requested)
```

Même principe que dans la vue API (voir 4.6) : `location__city` = « suis le lien vers `Location`,
puis regarde `city` ». `iexact` = sans tenir compte des majuscules.

| Ville | `rooms` (résultat réel : code, capacité) |
|---|---|
| Lyon | `lyo-desk` (4), `lyo-room` (6) |
| Paris | `par-desk` (2), `par-room` (10) |
| Nantes | `nan-room` (8) |
| Rennes | *(aucune)* |

La requête n'est **pas encore envoyée** à la base : elle partira aux étapes 5.7 et 5.8.

> **📌 Résumé 5.6** — `rooms` = la requête « toutes les salles de cette ville », prête à être
> utilisée pour calculer la somme et la liste des codes.

---

### 5.7 La somme des capacités : `aggregate(Sum(...))`

```python
total_capacity = rooms.aggregate(total=Sum('capacity'))['total'] or 0
```

| Morceau | Sens |
|---|---|
| `.aggregate(...)` | « fais **un calcul sur toutes les lignes** et renvoie **un seul résultat** » |
| `Sum('capacity')` | additionne le champ `capacity` |
| `total=` | le **nom** donné au résultat (au choix) |
| `['total']` | récupère la valeur rangée sous ce nom |
| `or 0` | si le résultat est `None`, mettre `0` |

`aggregate` renvoie un **dictionnaire** (des paires nom → valeur), d'où le `['total']` pour en sortir
le nombre. Le nom choisi (`total=`) et le nom lu (`['total']`) doivent être **identiques**.

**`A or B`** = « prends `A`, sauf s'il compte comme faux ; dans ce cas prends `B` » :

```python
10 or 0     # → 10
None or 0   # → 0
```

**Résultats réels étape par étape :**

| Ville | `aggregate(total=Sum('capacity'))` | `['total']` | `or 0` → `total_capacity` |
|---|---|---|---|
| Lyon | `{'total': 10}` | `10` | **10** |
| Paris | `{'total': 12}` | `12` | **12** |
| Nantes | `{'total': 8}` | `8` | **8** |
| Rennes | `{'total': None}` | `None` | **0** |

Pour une ville sans salle, la base renvoie `None` (« rien à additionner »), pas `0`. Le `or 0`
corrige ça pour que le JSON affiche `0` et non `null`.

En SQL, Django envoie à peu près : `SELECT SUM(capacity) AS total FROM rooms_room JOIN rooms_location … WHERE city LIKE 'Lyon'`.
C'est **la base** qui additionne. Une boucle Python (`sum(r.capacity for r in rooms)`) marcherait
aussi, mais chargerait toutes les salles en mémoire ; la consigne demande une **agrégation ORM**.

Autres calculs du même genre : `Count` (compter), `Avg` (moyenne), `Max`, `Min`.

> **📌 Résumé 5.7** — `aggregate(total=Sum('capacity'))` → la base additionne et renvoie
> `{'total': 10}`. `['total']` → `10`. `or 0` → transforme le `None` d'une ville vide en `0`.

---

### 5.8 La liste des codes : `values_list(..., flat=True)` et `sorted`

```python
room_codes = sorted(rooms.values_list('code', flat=True))
```

**① `values_list('code')` — seulement la colonne `code`**

Au lieu d'objets `Room` complets, la base renvoie seulement les codes, chacun dans un **tuple**
(une petite parenthèse) : `('par-desk',)`. Le tuple existe parce qu'on pourrait demander plusieurs
colonnes : `values_list('code', 'name')` → `('par-desk', 'Focus desk')`.

**② `flat=True` — enlever les parenthèses**

| Sans `flat=True` | Avec `flat=True` |
|---|---|
| `[('par-desk',), ('par-room',)]` | `['par-desk', 'par-room']` |

`flat=True` ne marche qu'avec **une seule colonne**.

**③ `sorted(...)` — trier de A à Z**

```python
sorted(['par-room', 'par-desk', 'lyo-room'])
# → ['lyo-room', 'par-desk', 'par-room']
```

`sorted` renvoie aussi une **vraie liste Python**, nécessaire pour `json.dumps` (qui ne sait pas
convertir un queryset).

**Résultats réels étape par étape :**

| Ville | `values_list('code')` | `+ flat=True` | `sorted(...)` → `room_codes` |
|---|---|---|---|
| Paris | `[('par-desk',), ('par-room',)]` | `['par-desk', 'par-room']` | **`['par-desk', 'par-room']`** |
| Rennes | `[]` | `[]` | **`[]`** |

> **📌 Résumé 5.8** — `values_list('code', flat=True)` → la liste simple des codes.
> `sorted(...)` → triée de A à Z, en vraie liste Python. Ville vide → `[]`.

---

### 5.9 Construire le JSON : `len` et `json.dumps`

```python
return json.dumps({
    'city': city_name,
    'total_rooms': len(room_codes),
    'total_capacity': total_capacity,
    'room_codes': room_codes,
})
```

**Les accolades `{ ... }`** créent un **dictionnaire** Python : des paires `'clé': valeur`.

**`len(room_codes)`** compte les éléments de la liste : `len(['lyo-desk', 'lyo-room'])` → `2`.
On réutilise la liste des codes : pas besoin d'une requête de plus pour compter.

**`json.dumps(...)`** transforme le dictionnaire Python en **texte JSON** (*dump string* = « écrire
en texte »). Avant / après (résultat réel) :

| | Type | Valeur |
|---|---|---|
| Avant `json.dumps` | `dict` (dictionnaire Python) | `{'city': 'Lyon', 'room_codes': ['a']}` |
| Après `json.dumps` | `str` (texte) | `{"city": "Lyon", "room_codes": ["a"]}` |

Remarquez : Python affiche des **apostrophes** `'`, le JSON utilise des **guillemets** `"`.
Le JSON est un **texte universel**, lisible par n'importe quel langage (JavaScript, Java…).

La consigne demande une **chaîne JSON**, pas un dictionnaire : le test vérifie
`assertIsInstance(result, str)`, puis relit le texte avec `json.loads(result)`.

**`return`** renvoie ce texte à celui qui a appelé la fonction.

> **📌 Résumé 5.9** — On range les 4 résultats dans un dictionnaire, `len()` compte les salles,
> `json.dumps()` transforme le tout en **texte JSON**, `return` le renvoie.

---

### 5.10 Ce que la fonction ne fait PAS

- **Aucune écriture en base** : seulement `filter`, `first`, `aggregate`, `values_list` (lectures).
  Le test `test_report_is_read_only` compte les salles avant/après : le nombre ne change pas.
- **Aucune valeur écrite en dur** : tout vient de la base (si on ajoute une salle à Lyon, le
  rapport change tout seul).

> Remarque : la consigne de la tâche parle de `room_count`, mais les tests et le README attendent
> `total_rooms`. C'est `total_rooms` qui est utilisé, pour que les tests passent.

---

### 5.11 📋 Résumé général de la tâche 4

| Étape | Code | Rôle | Exemple (`"  lyon  "`) |
|---|---|---|---|
| 5.2 | `isinstance(city, str)` / `city.strip()` | refuser ce qui n'est pas du texte, puis le vide | passe ✅ |
| 5.3 | `requested = city.strip()` | enlever les espaces | `"lyon"` |
| 5.4 | `Location…filter(city__iexact=…).first()` | trouver la ville, ou `None` | `Lyon` |
| 5.5 | `location.city if location else requested` | orthographe officielle ou nom demandé | `"Lyon"` |
| 5.6 | `Room…filter(location__city__iexact=…)` | les salles de la ville | `lyo-desk`, `lyo-room` |
| 5.7 | `aggregate(total=Sum('capacity'))['total'] or 0` | somme des capacités | `10` |
| 5.8 | `sorted(values_list('code', flat=True))` | codes triés | `['lyo-desk', 'lyo-room']` |
| 5.9 | `json.dumps({...})` | tout transformer en texte JSON | `{"city": "Lyon", "total_rooms": 2, …}` |

**Les 5 idées Python à retenir :**

1. **`isinstance(x, str)`** vérifie le type ; **`.strip()`** enlève les espaces.
2. **`A or B`** : Python s'arrête dès que `A` est vrai → sert de garde, et `None or 0` → `0`.
3. **`X if condition else Y`** = un `if/else` sur une ligne.
4. **`None`, `""`, `0`, `[]`** comptent comme « faux » dans un `if`.
5. **`json.dumps`** : dictionnaire Python → texte JSON.

**Les 4 outils Django (ORM) à retenir :**

1. **`.filter(champ__iexact=…)`** : chercher sans tenir compte des majuscules.
2. **`.first()`** : un seul objet ou `None`, sans planter.
3. **`.aggregate(nom=Sum('champ'))`** : la base fait le calcul, renvoie `{'nom': valeur}`.
4. **`.values_list('champ', flat=True)`** : seulement une colonne, en liste simple.

---

## 6. Lancer les tests

```bash
python check.py --todo0   # template        (3 tests)
python check.py --todo1   # serializer      (3 tests)
python check.py --todo2   # vue API         (5 tests)
python check.py --todo3   # rapport JSON    (5 tests)
python check.py           # tout            (16 tests)
```

Les tests ne doivent jamais être modifiés : un test qui échoue indique ce qu'il faut corriger.

---

## 7. Petit lexique

| Mot | Sens |
|---|---|
| **Modèle** | une classe Python qui décrit une table de la base (`Room`, `Location`) |
| **ORM** | l'outil de Django qui permet d'interroger la base en Python plutôt qu'en SQL |
| **Queryset** | une requête vers la base, préparée mais pas encore exécutée |
| **ForeignKey** | un lien d'une table vers une autre (`Room.location` → `Location`) |
| **Serializer** | traduit un objet Python en JSON (et inversement) |
| **Vue** | le code qui répond à une URL |
| **Héritage** | une classe récupère le code d'une classe parente : `class A(B)` |
| **`super()`** | appelle la version de la méthode dans la classe parente |
| **`None`** | « rien », l'absence de valeur |
| **`.strip()`** | enlève les espaces au début et à la fin d'un texte |
| **`__` (double underscore)** | dans un `filter`, veut dire « aller dans » (`location__city`) |
| **`iexact`** | égalité sans tenir compte des majuscules/minuscules |
| **200 / 400 / 405** | codes HTTP : OK / requête invalide / méthode non autorisée |
| **`isinstance(x, str)`** | vérifie si `x` est du texte |
| **`raise`** | déclenche une erreur et arrête la fonction |
| **`ValueError`** | erreur Python standard : « valeur non acceptable » |
| **`.first()`** | le premier résultat d'un queryset, ou `None` s'il est vide |
| **`aggregate` / `Sum`** | demander à la base un calcul global (ici une somme) |
| **`values_list(..., flat=True)`** | récupérer une seule colonne, en liste simple |
| **`sorted()`** | renvoie une nouvelle liste triée |
| **`len()`** | compte les éléments d'une liste |
| **dictionnaire (`dict`)** | paires `'clé': valeur` entre accolades `{}` |
| **`json.dumps()`** | transforme un dictionnaire Python en texte JSON |
