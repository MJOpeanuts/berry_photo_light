# Berry Photo Light

Application locale et légère pour Raspberry Pi : choix du disque de destination, prévisualisation de l'Arducam et capture de photos HD. Le lecteur Keyence n'est pas piloté par cette application.

## Pré-requis

- Raspberry Pi OS avec interface graphique
- Raspberry Pi 4 et caméra Arducam prise en charge par `libcamera` / Picamera2
- Python 3, Picamera2 et PyQt5 installés depuis les paquets Raspberry Pi OS

Sur Raspberry Pi OS, préférez les paquets système à `pip` pour Picamera2 :

```sh
sudo apt update
sudo apt install python3-picamera2 python3-pyqt5
```

Le module Qt de Picamera2 doit être disponible dans l'installation. Si l'import `picamera2.previews.qt` échoue, vérifiez les paquets de votre version de Raspberry Pi OS et l'installation du composant Qt de Picamera2.

## Installation et lancement

Clonez le dépôt dans le dossier personnel, puis :

```sh
cd ~/berry_photo_light
chmod +x run.sh install_desktop.sh
./run.sh
```

Pour installer le raccourci sur le bureau :

```sh
./install_desktop.sh
```

Si le bureau demande une confirmation, faites un clic droit sur le raccourci et autorisez son lancement. Vous pouvez aussi lancer l'application depuis un terminal pour voir les diagnostics.

## Utilisation

1. Choisissez **Disque local** ou une clé USB détectée et montée sous `/media/$USER` ou `/run/media/$USER`.
2. Si la clé n'est pas détectée, utilisez **Parcourir les dossiers…** pour sélectionner son point de montage.
3. Cadrez avec la prévisualisation.
4. Appuyez sur le bouton rouge pour enregistrer une photo.
5. Utilisez **Retour** en haut à gauche pour changer de destination.

Les photos sont enregistrées dans un sous-dossier daté, par exemple :

```text
~/Pictures/BerryPhotoLight/2026-09-28/photo_20260928_101541_123456.jpg
```

Sur une clé USB, le dossier `BerryPhotoLight/YYYY-MM-DD` est créé à la racine du point de montage. Une vérification d'écriture est faite lors du choix de destination et avant chaque capture. Si le support est retiré, l'application affiche l'erreur rencontrée sans fermer volontairement la fenêtre.

## Architecture

- `main.py` : interface Qt tactile et navigation
- `camera_service.py` : cycle Picamera2, preview Qt et capture haute résolution
- `storage_service.py` : destinations, test d'écriture et chemins de photos
- `capture_worker.py` : capture en arrière-plan pour garder l'interface réactive
- `run.sh` : lanceur de l'application
- `install_desktop.sh` : création du raccourci du bureau

## Limites de cette première version

- Pas de contrôle du Keyence, de lecture de codes ou de lien entre codes et photo.
- Pas de suppression ni de retouche des photos.
- Le nom et le format du fichier sont générés automatiquement.
- La caméra et le widget `QGlPicamera2` doivent être validés sur la version de Raspberry Pi OS et le modèle Arducam réellement utilisés.
