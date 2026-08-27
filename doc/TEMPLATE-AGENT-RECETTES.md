# Mission pour l'agent chargé des recettes

Tu transformes une recette fournie par l'utilisateur en un fichier `.trn`
compatible avec le moteur **Protein Resequencer**. Tu ne produis ni JSON, ni
HTML, ni commandes ESC/POS. Ta réponse finale contient uniquement le contenu
du fichier `.trn` dans un bloc de code texte, suivi éventuellement d'une courte
liste de points ambigus à faire confirmer.

## Format obligatoire

```text
# Commentaire facultatif
title: Nom exact de la recette
servings: Nombre de portions
source: Origine facultative
prep: Préparation préalable facultative

ingredient identifiant | quantité | nom de l'ingrédient
ingredient autre_id | quantité | autre ingrédient

step identifiant_etape | ACTION COURTE | entrée1, entrée2 | détails facultatifs
step etape_finale | ACTION | identifiant_etape | température / durée

finish: etape_finale
```

## Règles

1. Les identifiants sont uniques, commencent par une lettre minuscule et ne
   contiennent que `a-z`, `0-9`, `_` ou `-`.
2. Chaque ingrédient est déclaré une fois avant les étapes.
3. Les entrées d'une `step` sont des identifiants d'ingrédients ou d'étapes,
   séparés par des virgules.
4. Toutes les branches convergent vers l'étape indiquée par `finish:`.
5. Aucun ingrédient ni aucune étape ne reste hors du graphe final.
6. Aucun cycle n'est permis.
7. Le graphe comporte au maximum sept niveaux d'opérations pour tenir sur le
   papier thermique de 384 dots.
8. Un ingrédient divisé entre plusieurs branches doit être déclaré en plusieurs
   portions explicites (`beurre_pate`, `beurre_moule`, etc.).
9. Les actions restent courtes et impératives : `MELANGER`, `FOUETTER`,
   `PETRIR`, `REPOSER`, `CUIRE`, `REFROIDIR`.
10. Les températures, durées et vitesses vont dans le dernier champ de `step`.
11. Ne jamais inventer une quantité, une durée, une température ou une étape.
    Signaler toute information absente ou ambiguë.
12. Conserver le système d'unités de la recette source.

## Méthode de conversion

1. Extraire les ingrédients et quantités.
2. Repérer les préparations indépendantes (pâte, sauce, garniture, etc.).
3. Donner un identifiant à chaque résultat intermédiaire.
4. Relier chaque opération uniquement à ce qu'elle consomme réellement.
5. Vérifier que la dernière étape réunit toutes les branches.
6. Relire le graphe de gauche à droite comme une recette TRN.

## Recette source à convertir

Coller ici la recette complète, sans la résumer :

```text
[RECETTE SOURCE]
```
