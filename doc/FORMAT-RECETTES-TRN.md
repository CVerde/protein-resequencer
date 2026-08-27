# Format de recettes TRN

Chaque recette est un fichier texte UTF-8 portant l'extension `.trn`. Les
identifiants sont internes au graphe et utilisent uniquement `a-z`, `0-9`, `_`
et `-`. Les lignes vides et celles commençant par `#` sont ignorées.

```text
title: Pain test
servings: 1 petit pain
source: Cahier personnel
prep: Préchauffer le four à 250 C

ingredient farine | 100 g | Farine
ingredient eau | 70 g | Eau

step melange | MELANGER | farine, eau
step petrissage | PETRIR | melange | 8 min
step cuisson | CUIRE | petrissage | 250 C / 12 min

finish: cuisson
```

## Instructions

- `title:` est obligatoire.
- `servings:`, `source:` et les lignes `prep:` sont facultatives.
- `ingredient id | quantité | nom` crée une feuille du graphe.
- `step id | action | entrées séparées par des virgules | détails` crée une
  opération. Le champ détails est facultatif.
- `finish:` désigne l'étape finale et rend le graphe imprimable.

Les entrées d'une étape peuvent référencer des ingrédients ou des étapes déjà
nommées. Toutes les branches doivent rejoindre `finish`. Pour partager un
ingrédient entre deux branches, déclare deux portions distinctes : la notation
TRN classique représente des combinaisons, pas la division d'un même élément.

Le rendu thermique adapte automatiquement la typographie jusqu'à sept niveaux
d'opérations sur une largeur validée de 384 dots.
