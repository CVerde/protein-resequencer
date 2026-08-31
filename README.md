# Protein Resequencer

## Système de fermentation contrôlée avec interface LCARS

### Fonctionnalités :

#### 🎮 **Préréglages disponibles :**
- **Natto** 🫘 - Fermentation soja (42°C, 24h)
- **Tempeh** 🟫 - Fermentation soja/légumineuses (32°C, 36h)
- **Koji Riz** 🍚 - Fermentation aspergillus (30-32°C, 48h)
- **Kombucha** 🧪 - Fermentation SCOBY (26°C, 7 jours)
- **Yaourt** 🥛 - Fermentation lactique (43°C, 8h)
- **Kimchi** 🌶️ - Lactofermentation légumes (20°C, 48h)
- **Lactoferment.** 🥒 - Légumes fermentés (22°C, 72h)
- **Miso** 🥣 - Pâte de soja fermentée (28°C, 30 jours)
- **Vinaigre** 🍯 - Acétification (28°C, 14 jours)
- **Désydra.** 💨 - Déshydratation (45°C, 12h)
- **Manuel** ⚙️ - Configuration libre

#### 🔧 **Contrôles :**
- Température (3 sondes + 1 SHT40)
- Humidité relative
- Ventilation interne/extraction
- Chauffage/humidification

#### 📱 **Interface :**
- Design LCARS Star Trek
- Écran tactile optimisé
- Clavier virtuel intégré
- Préréglages sur 2 lignes
- Historique et notes

### Installation sur Raspberry Pi :

#### Thermocouple four MAX6675

Le MAX6675 est lu directement par GPIO : VCC sur 3,3 V (pin 17), GND (pin 9),
SCK sur GPIO11 (pin 23), CS sur GPIO8 (pin 24) et SO sur GPIO9 (pin 21).
La sonde type K se branche sur T+ et T-. SPI n'a pas besoin d'être activé dans
`raspi-config` pour cette implémentation.

#### Imprimante thermique EM5820

L'EM5820 est alimentée séparément en 5 V (4 A recommandé) et reliée au
Raspberry Pi par USB. Elle est détectée comme `/dev/usb/lp0` et reçoit des
commandes ESC/POS via le module indépendant `printer`.

Le compte qui lance Flask doit appartenir au groupe `lp` :

```bash
sudo usermod -aG lp pi
sudo reboot
```

Le périphérique peut être remplacé avec la variable `THERMAL_PRINTER_DEVICE`.
La couche physique reste indépendante du moteur de recettes.

#### Recettes TRN

L'onglet **Recettes** permet de créer, valider, prévisualiser et imprimer des
fichiers `.trn`. Le moteur transforme chaque fichier en graphe de recette, puis
en tableau monochrome de 384 dots avant de l'envoyer à l'EM5820.

- Grammaire et exemple : `doc/FORMAT-RECETTES-TRN.md`
- Modèle vierge : `doc/template-recette.trn`
- Mission prête pour un agent : `doc/TEMPLATE-AGENT-RECETTES.md`
- Recettes enregistrées : `recipes_data/`

Lancer les tests sans utiliser l'imprimante :

```bash
python3 -m unittest discover -s tests -v
node --test tests/test_roon_daily_report.js
```

#### Compte rendu quotidien Roon

Au lancement, `scripts/roon_daily_report.js` écoute les événements
`now-playing-updated` de Songr sur le port 3333 et mémorise chaque changement
réel de morceau. À minuit (heure de Paris), il imprime la liste chronologique
complète de la journée, sans pochette. Un rapport manqué pendant un arrêt est
imprimé au redémarrage suivant.

L'en-tête indique la date longue en français, le nombre de pistes et leur durée
cumulée, puis laisse deux lignes blanches avant la liste chronologique.
Chaque piste tient sur une seule ligne compacte sous la forme
`heure · titre · album · artiste`, avec une taille identique et aucun interligne
supplémentaire.
Le titre est limité à 28 caractères, ellipse comprise.
Dans chaque ligne, le morceau est en italique, l'album est souligné et
l'artiste est en gras.

Le journal est stocké hors du dépôt dans
`/home/pi/.local/state/protein-resequencer/roon-daily-report.json`. Par défaut,
toutes les zones sont surveillées. `ROON_PRINT_ZONE_IDS` permet de fournir une
liste d'identifiants de zones séparés par des virgules. Les logs sont dans
`/tmp/protein-resequencer-roon-report.log`.

Une extension Roon directe de lecture seule explore les hiérarchies Browse et
Albums afin de préparer le ticket des ajouts quotidiens. Elle doit être
autorisée une fois dans **Roon > Réglages > Extensions**. Son journal est
`/tmp/protein-resequencer-roon-api.log`.

```bash
# Clone depuis GitHub
git clone https://github.com/CVerde/protein-resequencer.git
cd protein-resequencer

# Permissions
chmod +x *.sh

# Installation des icônes
cp protein-resequencer.desktop ~/Desktop/
cp protein-resequencer-update.desktop ~/Desktop/
chmod +x ~/Desktop/*.desktop

# Lancement
./start.sh
```

### Workflow de développement :

1. **Développement** sur Windows avec VS Code
2. **Commit/Push** vers GitHub 
3. **Mise à jour Pi** avec l'icône "PR Update & Start"

### Icônes disponibles :
- 🟢 **"Protein Resequencer"** - Lancement direct
- 🔄 **"PR Update & Start"** - Mise à jour depuis GitHub + lancement

### Architecture :
- **Backend** : Flask (Python)
- **Frontend** : HTML/CSS/JS avec design LCARS
- **Données** : JSON (historique, préréglages personnalisés)
- **Contrôle** : GPIO Raspberry Pi

test
