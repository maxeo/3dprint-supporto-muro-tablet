# Supporto Muro Tablet T65

Cornice da parete per il tablet Teclast T65 (13,4") usato come pannello di Home Assistant, montata su una scatola 503 aperta. Bordo bianco a filo (concept 4 in `concept/parete/`): il tablet entra da dietro nella cornice, tre fermi lo tengono sul vetro (due sopra, uno sotto, così la fotocamera frontale resta libera), il fondo si avvita al muro e la cornice si aggancia sopra.

**Guida di stampa e montaggio:** [guida.html](guida.html) · online: https://maxeo.github.io/3dprint-guide/supporto-muro-tablet/guida.html

## Pezzi

| Sigla | File | Ingombro di stampa, mm | PLA, g (pieno) |
|---|---|---|---|
| P01 | `stl/P01_Fondo.stl` | 240 × 226,4 × 11 | 360 |
| P02 | `stl/P02_Cornice_Sx.stl` | 171,2 × 231 × 16 | 42 |
| P03 | `stl/P03_Cornice_Dx.stl` | 177,3 × 231 × 16 | 45 |

La cornice (340 × 231 × 16) non sta sul piatto da 250 × 250, quindi si stampa in due metà con la faccia sul piatto, senza supporti. Le metà si uniscono con un giunto a cuneo a 45° nascosto, sopra e sotto, chiuso da due viti M3×6 dal retro. Due viti M3×10 da sotto fissano la cornice al fondo. Il fondo va al muro con le viti della 503 (interasse 83,5) e due tasselli.

## Cavo di alimentazione

Una spina USB-C dritta non entra nella tasca da 12,5 mm a sinistra: serve un cavo con la spina a 90° laterale, per esempio UGREEN 20855 (USB-A → USB-C, 0,5 m). Il cavo sale lungo il bordo, passa dietro il tablet e arriva nel canale del fondo fino alla scatola, dove sta l'alimentatore USB-A.

## Rigenerare

```
"C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup --python blender/costruisci.py
"C:/Program Files/Blender Foundation/Blender 5.2/5.2/python/bin/python.exe" dati/scrivi_spec.py
"C:/Program Files/Blender Foundation/Blender 5.2/5.2/python/bin/python.exe" "%USERPROFILE%/.claude/skills/guida-stampa-3d/scripts/build_guide.py" dati/guida_spec.json
```

`costruisci.py` scrive gli STL, `blender/Supporto_Muro_Tablet_T65.blend` e `dati/geometria.json` con pesi, spigoli aperti e i controlli di interferenza (tablet, fotocamera posteriore, fondo e metà della cornice).

## Note

- Non ancora stampato. Posizione della presa USB-C, sporgenza della spina, posizione della scatola (`Y_SCATOLA`) e rilievo della fotocamera posteriore sono stime da verificare sul tablet vero.
- I tasti di accensione e volume restano coperti: per usarli si toglie la cornice.
- Mockup e schermata sono su una casa e una dashboard di esempio (`dati/dashboard_finta.html`).
