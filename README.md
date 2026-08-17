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
