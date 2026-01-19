# Protein Resequencer

## Migration depuis MINSHARA-F

Le projet a été renommé de **MINSHARA-F** vers **Protein Resequencer**.

### Changements effectués :

1. **MINSHARA-F.desktop** → **protein-resequencer.desktop**
   - Nom d'affichage : "Protein Resequencer"
   - Chemins mis à jour vers `/home/pi/protein-resequencer/`

2. **app.py** : En-tête mise à jour vers "Protein Resequencer - Chambre de Fermentation Contrôlée"

3. **start.sh** : Chemins mis à jour et commentaire actualisé

4. **templates/index.html** :
   - Titre de la page : "Protein Resequencer"
   - Titre par défaut dans l'interface
   - Message de confirmation de sortie

### Installation sur Raspberry Pi :

```bash
# Arrêter l'ancienne version si elle tourne
sudo systemctl stop minshara-f 2>/dev/null

# Copier les fichiers
sudo mkdir -p /home/pi/protein-resequencer
sudo cp * /home/pi/protein-resequencer/
sudo cp -r templates /home/pi/protein-resequencer/
sudo cp -r doc /home/pi/protein-resequencer/

# Permissions
sudo chown -R pi:pi /home/pi/protein-resequencer
sudo chmod +x /home/pi/protein-resequencer/start.sh

# Copier le fichier desktop
sudo cp protein-resequencer.desktop /home/pi/Desktop/
sudo cp protein-resequencer.desktop /usr/share/applications/

# Démarrer
/home/pi/protein-resequencer/start.sh
```

### Fonctionnalités conservées :

- Interface LCARS complète
- Contrôle température/humidité/ventilation  
- Préréglages système (natto, tempeh, koji, etc.)
- Préréglages personnalisés
- Historique et notes
- Mode kiosque sur écran tactile
