# Karaoke Generator

Genera video karaoke MP4 a partire da una traccia vocale e una strumentale MP3.  
La sincronizzazione testo-audio è automatica tramite **Whisper medium** (OpenAI).

---

## Funzionamento

1. Fornisci il titolo e l'artista del brano
2. Carica la traccia **vocale** MP3 (usata da Whisper per la trascrizione)
3. Carica la traccia **strumentale** MP3 (usata come audio nel video finale)
4. Trascrivi con Whisper → correggi il testo nell'editor → genera il video

### Struttura del video generato

```
[Titolo + Artista]       ← intro
[♪ Strumentale ♪]        ← durante pause lunghe (> 4 secondi)
[Karaoke parola x parola] ← parola corrente in giallo, prossima riga in grigio
[♪ Strumentale ♪]        ← eventuale coda strumentale
[Ending]
[by Frank]
```

---

## Requisiti di sistema

- Windows 10/11
- Python 3.10 o superiore
- FFmpeg
- GPU NVIDIA con CUDA (consigliata — funziona anche su CPU ma è molto più lento)

---

## Installazione passo passo

### 1. Installa Python

Scarica e installa Python 3.11 da [python.org](https://www.python.org/downloads/).  
Durante l'installazione spunta **"Add Python to PATH"**.

Verifica dal terminale:
```
python --version
```

### 2. Installa FFmpeg

```
winget install ffmpeg
```

Oppure scaricalo da [ffmpeg.org](https://ffmpeg.org/download.html) e aggiungi la cartella `bin` al PATH di sistema.

Verifica:
```
ffmpeg -version
```

### 3. Clona il repository

```
git clone https://github.com/sabatinicentocinquanta-dotcom/karaoke-generator.git
cd karaoke-generator
```

Oppure scarica lo ZIP da GitHub (pulsante verde **Code → Download ZIP**) ed estrailo.

### 4. Verifica la versione CUDA (solo se hai GPU NVIDIA)

```
nvidia-smi
```

Cerca la riga `CUDA Version: XX.X` in alto a destra.  
Se è diversa da **12.1**, apri `setup.bat` con un editor di testo e sostituisci `cu121` con la tua versione (es. `cu118` per CUDA 11.8, `cu124` per CUDA 12.4).

### 5. Esegui il setup

Fai doppio clic su `setup.bat` oppure da terminale:

```
setup.bat
```

Lo script:
- Crea un ambiente virtuale Python (`venv/`)
- Installa PyTorch con supporto CUDA
- Installa tutte le dipendenze (stable-ts, moviepy, Pillow, …)
- Verifica che FFmpeg sia disponibile

Al termine verrà mostrato se la GPU è stata rilevata correttamente.

> **Nota:** il modello Whisper medium (~1.5 GB) viene scaricato automaticamente al primo avvio dell'app, non durante il setup.

---

## Avvio

Fai doppio clic su `run.bat` oppure:

```
run.bat
```

---

## Uso dell'applicazione

### Passo 1 — Compila i campi

| Campo | Contenuto |
|---|---|
| Titolo brano | Es. `Volare` |
| Artista | Es. `Domenico Modugno` |
| MP3 Vocale | Traccia con sola voce (usata da Whisper) |
| MP3 Strumentale | Traccia senza voce (audio del video finale) |
| Output MP4 | Percorso e nome del file video da generare |
| Lingua | `auto` rileva automaticamente; puoi forzare `it`, `en`, ecc. |

### Passo 2 — Trascrivi

Clicca **"1 ▶ Trascrivi con Whisper"**.  
La prima esecuzione scarica il modello (~1.5 GB, solo una volta).  
Al termine si apre automaticamente l'**editor segmenti**.

### Passo 3 — Correggi il testo (editor segmenti)

Ogni riga del testo trascritto è modificabile:

| Azione | Come |
|---|---|
| Correggere una parola | Clicca sulla riga e modifica il testo |
| Eliminare una riga | Pulsante **×** |
| Unire due righe consecutive | Pulsante **↓** |
| Riaprire l'editor in seguito | Pulsante **✎ Editor segmenti** nella finestra principale |

Clicca **✓ Conferma** per salvare le correzioni.

> Se modifichi il numero di parole in una riga, i timestamp vengono ridistribuiti proporzionalmente sull'intervallo del segmento.

### Passo 4 — Genera il video

Seleziona il file di output MP4, poi clicca **"2 ▶ Genera Video MP4"**.  
L'operazione richiede alcuni minuti (molto meno con GPU).

---

## Indicatore GPU/CPU

In alto a destra nella finestra è sempre visibile lo stato hardware:

- **`⚡ GPU: NVIDIA GeForce RTX ...`** — CUDA disponibile, trascrizione veloce
- `CPU (nessuna GPU CUDA)` — funziona ma la trascrizione è più lenta
- `CPU (torch non installato)` — esegui `setup.bat`

---

## Dipendenze principali

| Pacchetto | Funzione |
|---|---|
| `stable-ts` | Whisper con timestamp a livello di parola |
| `moviepy 1.0.3` | Assemblaggio video |
| `Pillow` | Rendering frame karaoke |
| `torch` | Backend per Whisper |
| `ffmpeg` | Codifica audio/video finale |
