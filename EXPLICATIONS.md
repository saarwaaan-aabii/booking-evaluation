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

```python
def export_city_summary(city: str) -> str:
    if not isinstance(city, str) or not city.strip():
        raise ValueError('city must be a non-empty string')
    requested = city.strip()

    location = Location.objects.filter(city__iexact=requested).first()
    city_name = location.city if location else requested

    rooms = Room.objects.filter(location__city__iexact=requested)
    total_capacity = rooms.aggregate(total=Sum('capacity'))['total'] or 0
    room_codes = sorted(rooms.values_list('code', flat=True))

    return json.dumps({
        'city': city_name,
        'total_rooms': len(room_codes),
        'total_capacity': total_capacity,
        'room_codes': room_codes,
    })
```

| Ligne | Sens |
|---|---|
| `isinstance(city, str)` | vérifie que c'est bien du texte (refuse `None`, `13`…) |
| `not city.strip()` | refuse `""` et `"   "` → `ValueError` |
| `Location.objects.filter(city__iexact=…).first()` | cherche la ville sans tenir compte des majuscules ; `.first()` renvoie la première trouvée ou `None` |
| `location.city if location else requested` | ville connue → son orthographe en base (`"Lyon"`) ; inconnue → le nom demandé nettoyé |
| `Room.objects.filter(location__city__iexact=…)` | les salles de cette ville (même principe que la vue) |
| `aggregate(total=Sum('capacity'))` | la base calcule la **somme** des capacités ; renvoie `{'total': 10}` |
| `or 0` | s'il n'y a aucune salle, la somme vaut `None` → on met `0` |
| `values_list('code', flat=True)` | récupère seulement les codes : `['lyo-desk', 'lyo-room']` |
| `sorted(...)` | trie les codes de A à Z |
| `json.dumps({...})` | transforme le dictionnaire Python en **texte JSON** |

Exemple pour `"  lyon  "` :

```json
{"city": "Lyon", "total_rooms": 2, "total_capacity": 10, "room_codes": ["lyo-desk", "lyo-room"]}
```

Pour `"Rennes"` : `{"city": "Rennes", "total_rooms": 0, "total_capacity": 0, "room_codes": []}`.

La fonction ne fait que **lire** la base : aucune création, modification ni suppression.

> Remarque : la consigne de la tâche parle de `room_count`, mais les tests et le README attendent
> `total_rooms`. C'est `total_rooms` qui est utilisé, pour que les tests passent.

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
