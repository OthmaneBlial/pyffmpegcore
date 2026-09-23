# ROADMAP — PyFFmpegCore

> Audit initial du 19 septembre 2026, `main` à `a3705d4`. Le tableau de diagnostic
> ci-dessous conserve cette photographie de départ. Les encarts **État** suivent
> ensuite l'exécution : une case cochée renvoie à la preuve et au run cités, tandis
> qu'une tâche partielle reste ouverte. Ce document remplace le plan du 25 août.
>
> Périmètre de l'audit initial : fichiers suivis par Git, métadonnées du dépôt
> GitHub, release et journaux de workflows, exécution locale sur macOS avec
> Python 3.14.6 et FFmpeg 9.0.1. Les validations locales ne prouvent ni une
> publication nouvelle, ni le bon fonctionnement sur Windows/Linux, ni une
> adoption par des utilisateurs. La comparaison concurrentielle a été revérifiée
> sur les sources officielles à la tâche 3.4.

## Diagnostic : ce qui existe réellement

| Domaine | État vérifié | Écart qui compte |
| --- | --- | --- |
| Produit | CLI et API Python autour d'un cycle préflight → plan → exécution → résultat/receipt. Profils, conversion, compression à taille cible, audio, sous-titres, images, lots et pipelines typés sont présents dans `pyffmpegcore/`. `smoke-test` réussit localement sur un média synthétique. | La première réussite mise en avant est une vignette synthétique ; le parcours « problème réel → plan → fichier utile → receipt » demande plusieurs pages et un média fourni par l'utilisateur. Le bénéfice distinctif arrive tard dans le README. |
| Qualité et architecture | 333 cas collectés localement, dont de nombreux tests FFmpeg réels. CI déclarée pour Python 3.10–3.14, roues installées sur trois OS, couverture à 80 %, Ruff, mypy et vérification des distributions. Le moteur est déjà séparé en modules. | La dernière [CI générale au commit courant](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/33053408044) est rouge dès Ruff. `cli.py` (1 412 lignes), `cli_parser.py` (1 025), `planning.py` (1 069) et `pipeline.py` (933) concentrent encore la maintenance. |
| Compatibilité | `doctor`, inventaire de capacités, épreuves média et politique de compatibilité documentés. | Le [contrôle hebdomadaire du 14 septembre](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/34834651539) échoue sur Windows : `tests/media_utils.py` lit `manifest.json` sans `encoding="utf-8"` et le runner utilise CP1252. L'affirmation de suivi continu des trois OS est donc actuellement trop forte. |
| Sécurité | Arguments de processus sous forme de listes, refus d'écrasement par défaut, limites reconnues dans `docs/SECURITY_MODEL.md`, signature du tag `v0.2.2` vérifiée localement, workflow d'attestation et scan du conteneur. | Le [scan du 16 septembre](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35083830821) bloque l'image candidate sur deux avis HIGH corrigés pour `libpcre2-8-0` (CVE-2026-86145 et CVE-2026-89161). Le script de la GitHub Action valide les chemins lexicalement : un test isolé a créé `result.json` hors du workspace via un lien symbolique, avec code de sortie 0. Le modèle de sécurité reconnaît aussi l'absence de sandbox média et de limites universelles de ressources. |
| Installation et distribution | La [release GitHub v0.2.2](https://github.com/OthmaneBlial/pyffmpegcore/releases/tag/v0.2.2) existe et propose wheel, sdist, `SHA256SUMS` et rapport d'artefacts. `pyproject.toml` expose une commande installable. Une image GHCR et une Action référencées par digest/SHA sont documentées. | Aucun exécutable autonome macOS/Windows/Linux n'est joint à la release ; ce choix est explicite dans `CLI_DISTRIBUTION.md`. Ce fichier dit néanmoins que seuls wheel et sdist sont distribués, alors que les docs présentent aussi conteneur et Action. La publication du conteneur suivant est bloquée par le scan. La release est présentée comme une bêta, mais GitHub ne la marque pas « prerelease ». |
| Présentation et UX | README avec bannière SVG, recettes, tableaux de preuve et liens ; site MkDocs avec identité visuelle, CSS responsive et bouton de copie ; cast terminal réel et transcription. | Le cast public montre `0.2.1` alors que l'installation mise en avant est `0.2.2`. `docs/index.md` montre une console HTML illustrative ; elle ne remplace pas une capture du logiciel. Aucune vidéo finale ni capture vérifiée du parcours complet n'est suivie dans le dépôt. Le rendu mobile, le clavier et le lecteur d'écran n'ont pas été observés lors de cet audit. |
| Confiance et communauté | Licence, sécurité, support, contribution, formulaires d'issues, notes de release, workflows CodeQL et Scorecard sont présents ; les Discussions sont documentées. | `RELEASE_CHECKLIST.md` affiche toutes ses cases comme accomplies, y compris un cast de la version exacte, sans renvoyer à une vérification actuelle. Le journal de publication de `LAUNCH.md` est vide : aucun partage externe ni première activation indépendante n'est prouvé par ce dépôt. |
| Positionnement | `docs/comparison.md` distingue PyFFmpegCore de FFmpeg brut, `ffmpeg-python`, `python-ffmpeg`, `ffmpegio` et PyAV par ses tâches inspectables et receipts. | Comparaison datée du 25 août, sans scénario reproductible montrant le coût/avantage pour un nouvel utilisateur. Aucun gain de vitesse, facilité ou popularité face à ces projets n'est démontré. |

**Lecture du test local.** Le premier passage complet a donné 316 réussites, 7 exclusions et 10 échecs : neuf venaient de l'absence d'installation du paquet dans l'environnement temporaire d'audit, un de l'absence de Docker. Après installation du paquet, les tests concernés ont donné 14 réussites et une exclusion liée au filtre FFmpeg local. Le cas Action restant requiert Docker ; il n'a pas été revérifié sur cet hôte. `smoke-test` et `scripts/check_docs.py` ont réussi. Aucun test macOS ne clôt les échecs CI Windows ou conteneur.

## Cap produit et ordre des priorités

**Promesse défendable :** un orchestrateur FFmpeg local pour développeurs et créateurs techniques qui rend les tâches média courantes inspectables avant écriture, vérifiables après exécution et reproductibles en CI. Le moteur FFmpeg reste une dépendance système. Le produit n'est ni un langage général de graphes de filtres, ni une API de frames/paquets, ni un sandbox pour médias hostiles.

Une bibliothèque déjà publiable en bêta doit d'abord retrouver des signaux de confiance verts, puis prouver un premier résultat utile et rendre la maintenance durable. Ajouter beaucoup de commandes, une GUI ou des exécutables natifs avant ces étapes augmenterait les obligations de support sans preuve de demande. Les stars sont un indicateur secondaire d'usage et de partage, jamais un critère d'acceptation technique.

```text
Phase 0 — corriger les échecs et la frontière de sécurité
   ↓
Phase 1 — raccourcir le premier résultat utile
   ↓
Phase 2 — solidifier moteur, compatibilité et sécurité
   ↓
Phase 3 — aligner documentation, preuve visuelle et comparaison
   ↓
Phase 4 — livrer et vérifier une release cohérente
   ↓
Phase 5 — valider auprès d'utilisateurs et diffuser avec des preuves
   ↓
Phase 6 — filmer le produit terminé
```

Les phases suivantes sont des gates successifs. Une tâche n'est close que si ses critères et sa preuve sont enregistrés avec le commit ou le run concerné. Un échec externe est signalé comme bloqué, pas coché par substitution documentaire.

## Phase 0 — P0 : rétablir la crédibilité du build et des frontières

### 0.1 Remettre la CI générale au vert

**État :** [x] Corrections Ruff et version d'outil fixée dans `aa2cf4a` ; la [CI complète du SHA `57be43d`](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35441425762) a réussi tous ses jobs, dont couverture, matrice, wheels et documentation.

- **Objectif :** que le commit proposé pour publication passe réellement ses contrôles de qualité.
- **Changements :** corriger les cinq erreurs Ruff visibles dans le dernier run (cache de `scripts/check_docs.py` et variables inutilisées de `tests/test_docs_contract.py`) ; décider d'une politique de mise à jour des outils de développement pour que `ruff>=0.6.0` ne change pas silencieusement les règles entre deux releases ; garder format et mypy actifs.
- **Fichiers :** `scripts/check_docs.py`, `tests/test_docs_contract.py`, `pyproject.toml`, `.github/workflows/ci.yml`, si la politique de dépendances change.
- **Acceptation :** Ruff, format, mypy, fast tests, couverture, matrice Python, vérification wheel et docs passent sur le **même nouveau SHA** ; lien vers ce run dans le dossier de release.
- **Validation :** commandes de `DEVELOPMENT.md` dans un environnement propre, puis chaque job du workflow CI, sans neutraliser les règles fautives.
- **Dépendances/risques :** première tâche ; une mise à jour de Ruff peut révéler d'autres diagnostics, à corriger explicitement.

### 0.2 Corriger le contrôle Windows en encodage natif non UTF‑8

**État :** [x] Correctif `ddf9641` ; [workflow fixtures sur les trois OS](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35439890072) réussi. Régression CP1252 et 17 tests ciblés réussis localement.

- **Objectif :** rendre les fixtures et les tests reproductibles sur le Windows effectivement annoncé.
- **Changements :** lire explicitement le manifeste et tout autre fichier texte contrôlé par le dépôt en UTF‑8 ; auditer les `read_text`/`write_text` et sorties `subprocess` du chemin fixtures/exemples ; ajouter une régression sous locale Windows/CP1252 sans masquer les échecs par des skips.
- **Fichiers :** `tests/media_utils.py`, `tests/media/download_fixtures.py`, tests des exemples/fixtures, `.github/workflows/fixtures.yml`.
- **Acceptation :** le job Windows hebdomadaire exécute les 16 cas précédemment cassés et le workflow complet réussit sur les trois OS ; un test ciblé reproduit puis prévient le décodage implicite.
- **Validation :** exécution Windows avec cache vide, Python 3.14, FFmpeg et `pytest` ; inspection des artefacts de compatibilité du run.
- **Dépendances/risques :** 0.1 pour la validation globale ; différences de console/FFmpeg Windows à relever séparément plutôt que changer les attentes à l'aveugle.

### 0.3 Débloquer la chaîne de l'image sans désactiver le scan

**État :** [x] Base rafraîchie dans `aeb2805` ; le
[run conteneur `35446437477`](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35446437477)
a réussi les smokes non-root et scans bloquants sur amd64 et arm64 (QEMU),
puis publié l’index
`sha256:796661ae57874f07221e9ad258499b9a9473282544744615c7b40b719aadbc9a`
depuis le SHA `7685c02`, avec SBOM, provenance et attestation vérifiée. Les
deux rapports complets gardent respectivement 874 et 863 constats sans version
corrigée connue. Le candidat Debian Trixie du SHA `d7b352e` a ensuite passé le
build, les smokes non-root et les scans amd64/arm64 dans le
[run `35449281881`](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35449281881)
avec zéro HIGH/CRITICAL corrigible, mais il n'a pas été publié : la publication
est désormais réservée au `workflow_dispatch` avec `publish=true`.

- **Objectif :** produire un digest de conteneur maintenu dont le scan de publication passe.
- **Changements :** rafraîchir la base Debian épinglée et les paquets corrigés, vérifier la disponibilité de la version FFmpeg retenue, reconstruire l'image multi-architecture, conserver la liste des licences et le SBOM. Identifier dans le rapport Trivy les deux CVE `libpcre2-8-0` et traiter toute nouvelle alerte fixable.
- **Fichiers :** `Containerfile`, `.github/workflows/container.yml`, `docs/container.md` ; les références de l'Action sont alignées en phase 4 après publication vérifiée.
- **Acceptation :** scan HIGH/CRITICAL corrigibles vert, smoke en utilisateur non-root, images `linux/amd64` et `linux/arm64` publiées avec digest, SBOM et provenance ; guide conteneur sur ce digest exact. L'Action est alignée et validée en 4.2.
- **Validation :** nouveau run Container réussi, examen de `trivy-blocking.json` et `trivy-results.sarif`, test `doctor`/`smoke-test` de chaque architecture ou de son émulation documentée.
- **Dépendances/risques :** 0.1 ; changements amont Debian, taille d'image et politique de codecs/licences. Ne pas ajouter d'exception CVE pour obtenir un vert artificiel.

### 0.4 Fermer l'évasion du workspace de la GitHub Action

**État :** [x] Correctif `2635773` ; six cas de lien symbolique et chemins Unicode/espaces validés localement, puis [intégration Action](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35440123285) et [réexécution avec le digest actualisé](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35440788514) réussies. Une modification concurrente du workspace reste hors garantie et est documentée.

- **Objectif :** garantir que les chemins d'entrée, état, événements, receipts et résultat restent dans `GITHUB_WORKSPACE`, même avec des liens symboliques.
- **Changements :** résoudre et vérifier les parents réels avant création/écriture, refuser les symlinks non sûrs et les chemins externes, prévoir la course entre validation et écriture ; limiter aussi les chemins d'artefacts acceptés. Documenter clairement ce que la vérification ne peut pas garantir si un autre processus modifie le workspace en parallèle.
- **Fichiers :** `scripts/run_pipeline_action.sh`, `tests/test_github_action.py`, `docs/github-action.md` et `docs/SECURITY_MODEL.md`.
- **Acceptation :** la reproduction avec `workspace/out` pointant vers un répertoire externe échoue avant écriture ; aucun fichier externe n'apparaît ; chemins ordinaires, espaces et noms Unicode restent utilisables.
- **Validation :** test shell/pytest avec faux Docker et liens symboliques, puis workflow Action intégration sur GitHub.
- **Dépendances/risques :** avant une nouvelle version de l'Action ; résolution portable des chemins Bash, liens introduits après validation et écriture atomique à traiter explicitement.

**Gate 0 :** CI générale, compatibilité hebdomadaire et scan conteneur verts sur les révisions ciblées ; régression du chemin symbolique et tests de l'Action verts. La parité complète de l'Action avec le nouveau digest est exigée au gate 4.

## Phase 1 — P1 : montrer une valeur utile dès la première session

### 1.1 Fournir un parcours complet sans média privé

**État :** guide et contrôle du wheel ajoutés dans `c0d939c` ; le
[run CI `35441425762`](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35441425762)
a validé les six installations sur Linux, macOS et Windows (Python 3.10 et
3.14). Relecture indépendante du guide encore à faire avant de cocher.
Une nouvelle exécution locale depuis un environnement vierge avec la wheel
publique `pyffmpegcore==0.2.2` a aussi réussi `--version`, `doctor --json`,
`smoke-test --keep-dir`, un profil H.264/AAC avec `--explain`, l'écriture d'un
receipt et sa validation schema 1.0. Le 24 septembre, le parcours complet a été
rejoué après installation dans un venv jetable sous macOS arm64, Python 3.14.6
et FFmpeg 9.0.1 ; `--explain` n'a pas créé le MP4, `probe --json` a confirmé les
codecs H.264/AAC et la validation a renvoyé `valid: true`. Cette preuve locale
ne remplace pas la relecture indépendante ni une nouvelle matrice publique. Le
validateur de l'artefact exact issu du dry-run a ensuite exécuté 26 commandes
sur macOS arm64, dont le parcours complet, les profils web/taille/audio/
sous-titres, batch/pipeline et quatre refus attendus avec leurs codes/remèdes.

- **Objectif :** faire vivre la promesse « diagnostiquer → expliquer → produire → vérifier » depuis une installation propre, sans demander immédiatement un fichier personnel.
- **Changements :** assembler un exemple synthétique court, généré localement, qui mène de `doctor` et `smoke-test --keep-dir` à un profil web, `--explain`, exécution, `probe` et validation du receipt ; garder les commandes copiables pour Bash/zsh et PowerShell. Si le parcours révèle un trou d'API/CLI, le corriger dans le moteur partagé avant de documenter un contournement.
- **Fichiers :** `README.md`, `docs/quickstart.md`, `docs/installation.md`, `scripts/validate_cli_install.py`, `tests/test_cli_installed_real.py` et, seulement si nécessaire, `pyffmpegcore/cli.py`.
- **Acceptation :** un utilisateur du wheel public peut obtenir un MP4 inspecté et un receipt validé en moins de cinq minutes hors téléchargement initial de FFmpeg ; aucune commande ne dépend de `tests/` ni d'un chemin privé ; le parcours fonctionne sans média personnel.
- **Validation :** exécution depuis wheel dans un environnement vide sur les trois OS, contrôle `ffprobe` de sortie, validation de receipt et relecture par une personne qui n'a pas écrit le guide.
- **Dépendances/risques :** gate 0 ; temps d'installation FFmpeg variable, choix de codecs selon build. Écrire les prérequis et variantes réellement testées.

### 1.2 Rendre l'installation et les erreurs actionnables

**État :** guides FFmpeg par OS ajoutés ; `0fd47fe` affiche des remèdes pour
outils manquants et sorties refusées ; `16371ec` évite l'écho d'une URL secrète
dans les commandes directes et le résultat JSON d'un pipeline. Tests ciblés et
pipeline HTTP local réussis. Le contrôle de wheel installé exerce désormais
quatre refus (binaire et encodeur absents, sortie présente, parent de sortie
invalide) et vérifie leurs remèdes : les six cellules Linux/macOS/Windows ont
passé [26/26 contrôles](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35448000531).
Installation réelle via WinGet/Fedora/Arch et revue humaine des textes d'erreur
sur chaque OS encore à vérifier ; la tâche reste ouverte.
Le 24 septembre, les sources de paquets officielles ont été revérifiées :
WinGet `Gyan.FFmpeg` 8.1.2, Fedora 44 `ffmpeg-free` avec `ffprobe`, Arch
x86_64 FFmpeg 9.0.2 et Homebrew `ffmpeg` 9.0.2. Les liens d'installation ont
été actualisés ; aucun installateur Windows/Fedora/Arch n'a été exécuté.
Le même validateur de wheel a toutefois vérifié localement les quatre refus
attendus (FFmpeg absent, encodeur absent, sortie existante, parent invalide)
avec les codes 3/4 et les remèdes correspondants ; cela ne remplace pas les
essais d'installation natifs demandés pour Windows, Fedora et Arch.

- **Objectif :** éviter que « installez FFmpeg » ou une erreur de capacité soit une impasse.
- **Changements :** expliquer, pour chaque OS supporté, comment installer et vérifier `ffmpeg`/`ffprobe` avec une source de paquets identifiée et un chemin de rattrapage ; faire afficher par `doctor` et les erreurs de préflight la capacité précise, le binaire utilisé et l'étape suivante. Préserver les contrats JSON et les codes de sortie.
- **Fichiers :** `docs/installation.md`, `docs/troubleshooting.md`, `docs/COMPATIBILITY.md`, `pyffmpegcore/cli.py`, `preflight.py`, `presentation.py`, tests de `doctor` et d'erreurs.
- **Acceptation :** les cas « exécutable absent », « encodeur absent », « destination non inscriptible » et « sortie déjà présente » mènent à un remède testable ; le texte et JSON ne se contredisent pas ; aucune erreur ne révèle un secret d'URL.
- **Validation :** tests de fautes injectées et essais propres Linux/macOS/Windows, y compris chemins avec espaces.
- **Dépendances/risques :** 1.1 et 0.2 ; commandes d'installation externes sujettes à dérive, donc revérifiées avant release.

### 1.3 Mettre trois résultats phares à l'épreuve

**État :** replay synthétique du 19 septembre consigné dans
[`docs/evidence.md`](docs/evidence.md), avec receipts validés, décodage complet
et mesure LUFS. Le cas VP9 montre une sortie web 78,2 % plus volumineuse.
Les plans de conversion avertissent maintenant que la sélection par défaut
omet les pistes supplémentaires ; le mode audio seul décrit aussi ses
omissions, et `--dry-run` comme `--explain` affichent cet avertissement. Les
tests ciblés passent. Depuis `ba0312f`, les profils intégrés vérifient dans
FFprobe les codecs promis et les types de pistes requis. Le commit `3df1dc0`
ajoute la vérification du format pixel `yuv420p` du profil web ; les 30 tests
ciblés, dont les cinq tests réels des profils, passent localement. CI, CodeQL,
Benchmarks et Scorecard sont verts sur le SHA exact.
Le 24 septembre, le checkout `0.3.0` a aussi exécuté un clip synthétique
`testsrc2` de 1 s en 320×180 avec une tonalité de 660 Hz. `--explain` n'a rien
créé ; `web/mp4-compatible` a produit un MP4 H.264/AAC `yuv420p` de 47 423
octets. `ffprobe`, la validation du receipt schema 1.0 et le décodage complet
ont réussi ; une frame synthétique a été inspectée visuellement. Cette preuve
ne mesure pas la qualité d'un média réel.

Un contrôle audio séparé a normalisé 8,77 s de parole synthétique macOS `say`
avec `normalize-audio --method loudnorm` : EBU R128 est passé de −19,3 à
−16,4 LUFS, le true peak mesuré est −1,8 dBFS face à une cible −1,5 dBTP, et
le MP3 192 kb/s de 212 012 octets passe le probe, le receipt schema 1.0 et le
décodage complet. Aucune écoute humaine ni média vocal représentatif consenti
n'a encore été évalué. La tâche reste ouverte.

Le 24 septembre, le checkout `0.3.0` a rejoué la recette exact-size sur le
fixture H.264/AAC synthétique de 4 042 503 octets : `--explain` n'a rien créé,
puis le mode deux passes a produit 248 417 octets sous la limite de 262 144.
Probe H.264/AAC `yuv420p`, validation du receipt schema 1.0 et décodage complet
réussis ; reçu conservé dans [`docs/evidence.md`](docs/evidence.md). Cette
preuve ferme le contrôle de limite de taille sur ce fixture, pas la revue de
qualité visuelle sur un média représentatif.
Une seconde exécution sur le même hôte a produit le même SHA-256 de sortie que
le receipt. Le filtre FFmpeg SSIM donne `All:0.926144` sur ce fixture généré ;
cette mesure propre au fixture ne remplace pas une revue humaine de média
représentatif.

- **Objectif :** concentrer l'investissement produit sur la vidéo web, la taille d'upload et la voix/podcast, déjà présents dans le dépôt.
- **Changements :** rejouer chaque recette avec médias générés et médias consentis représentatifs ; relever durée, codecs, pistes conservées/perdues, taille et qualité audible/visible ; expliciter les cas où le profil refuse ou avertit. Corriger dans le moteur partagé les défauts observés avant tout nouveau preset.
- **Fichiers :** `docs/recipes/web-video.md`, `exact-size.md`, `podcast.md`, `pyffmpegcore/profiles.py`, `planning.py`, `preflight.py`, `tests/test_profiles_real.py` et tests de compression/audio.
- **Acceptation :** chaque recette a une commande, un plan, une entrée reproductible, une sortie sondée, un receipt et une limite documentée ; aucun résultat de média synthétique n'est présenté comme une étude d'utilisateurs.
- **Validation :** tests FFmpeg réels, comparaison de pistes et métadonnées, vérification de taille cible, mesure LUFS et écoute/visionnage humain quand approprié.
- **Dépendances/risques :** 1.1 ; variations des builds FFmpeg et mesures de qualité non réductibles à un seul nombre.

**Gate 1 :** une installation neuve mène à un fichier utile vérifié ; les trois recettes phares sont reproductibles et leurs limites sont compréhensibles.

## Phase 2 — P1 : robustesse et contrat de sécurité

### 2.1 Réduire les points de maintenance risqués

**État :** [x] les deux adaptateurs `cli_planning.py` et `pipeline.py` convergent
déjà vers `WorkflowPlanner` ; leurs branches similaires acceptent des formats
d'entrée et des contrats différents. La carte de ces responsabilités est dans
[`docs/architecture.md`](docs/architecture.md). Le rendu des quatre scripts de
complétion a été extrait de `cli.py` vers `cli_completion.py` sans changer les
sorties (hashes comparés localement). La
[CI complète après extraction](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35446437482)
a réussi. Deux contrats directs vérifient la parité des plans normalisés
CLI/pipeline pour `convert` et le profil web ; un nouvel essai FFmpeg réel
compare désormais les sorties et valide les receipts des deux chemins.
Essai ciblé local et [CI complète du SHA `ec5dc0c`](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35447328360)
réussis, avec 88 % de couverture globale. Aucun schéma public n'a changé.

- **Objectif :** permettre de corriger un workflow sans propager des divergences entre CLI, profils, moteur et pipelines.
- **Changements :** cartographier les branches encore dupliquées dans les quatre gros modules ; découper seulement les responsabilités où les tests montrent un couplage réel ; garder une seule compilation des arguments et des contrats stables pour plans, résultats, receipts et codes de sortie.
- **Fichiers :** `pyffmpegcore/cli.py`, `cli_parser.py`, `planning.py`, `pipeline.py`, `workflow.py`, `domain.py` et tests de contrats.
- **Acceptation :** mêmes plans normalisés et mêmes résultats pour les scénarios de référence avant/après ; fonctions plus ciblées et dépendances lisibles ; aucune rupture silencieuse de `__all__` ou des schémas versionnés.
- **Validation :** suite unitaire/intégration, mypy, couverture des erreurs, golden tests CLI/JSON et test de migration si un schéma évolue.
- **Dépendances/risques :** gate 1 ; refactorisation étendue sans bénéfice observable à éviter.

### 2.2 Borner les tâches coûteuses et les entrées hostiles

**État :** [x] contrôle des URL et redaction des diagnostics de pipeline ;
capture des pipes et historique de progression bornés pour la politique
`TAIL` ; timeout explicite, catégorie `timeout`, nettoyage de sortie partielle,
annulation et préflight de disque bas couverts par des régressions. La
[CI complète `35445459849`](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35445459849)
a réussi avec 87,93 % de couverture des lignes. Le modèle de sécurité précise
qu'aucun plafond dur universel ne protège la mémoire, le disque ou la taille
des sorties ; un quota OS/conteneur reste nécessaire pour un média hostile.

- **Objectif :** réduire les surprises de temps, espace et réseau tout en annonçant honnêtement que PyFFmpegCore n'est pas un sandbox.
- **Changements :** définir des plafonds optionnels/explicites de temps et de sortie là où le moteur peut les garantir, distinguer préflight estimatif et limite dure, durcir redaction des diagnostics et politique URL/protocoles, tester nettoyage après annulation/timeout/disque plein. Maintenir l'exécution en vecteur d'arguments et `-nostdin`.
- **Fichiers :** `pyffmpegcore/executor.py`, `preflight.py`, `receipt.py`, `pipeline.py`, `docs/SECURITY_MODEL.md`, `docs/receipts.md`, tests de sécurité et échecs.
- **Acceptation :** une tâche dépassant un seuil explicite s'arrête avec catégorie stable et sans sortie présentée comme complète ; URL à identifiants et chemins privés ne sont pas copiés dans le receipt par défaut ; les limites impossibles à garantir restent dites telles quelles.
- **Validation :** fixtures adversariales locales, timeout/annulation/écriture partielle, tests de redaction, relecture du modèle de menace ; aucun média hostile réel exécuté sur l'hôte sans isolation.
- **Dépendances/risques :** 2.1 ; contrôle de mémoire/CPU nécessite l'OS ou le conteneur, FFmpeg peut déjà avoir écrit un résultat partiel.

### 2.3 Maintenir une matrice de compatibilité vérifiable

**État :** [x] la [CI complète `35444560165`](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35444560165)
a réussi les cinq contrats paquet Linux et les six essais du wheel exact
Linux/macOS/Windows. Le nouveau job de synthèse a vérifié le SHA commun, les
22 commandes par cellule, les versions FFmpeg et les deux capacités optionnelles
manquantes sur macOS ; son artefact Markdown est téléchargeable depuis le run.

- **Objectif :** faire correspondre chaque affirmation Python/OS/FFmpeg à un run actuel et aux capacités réellement disponibles.
- **Changements :** garder tests paquet 3.10–3.14 et wheel média sur trois OS ; rendre visibles les skips de codecs/filtres ; tester au moins une version FFmpeg de référence par famille et un build récent (FFmpeg 9.0.1 est l'environnement local d'audit, pas une preuve multi-OS) ; produire un rapport lisible depuis les artefacts CI.
- **Fichiers :** `.github/workflows/ci.yml`, `fixtures.yml`, `scripts/validate_capability_catalog.py`, `docs/COMPATIBILITY.md`, `docs/test-methodology.md`.
- **Acceptation :** tableau « testé / attendu / non pris en charge » daté et relié aux runs ; un skip ne transforme jamais une combinaison en support garanti ; les commandes phares passent sur les cellules annoncées.
- **Validation :** matrices GitHub, artefacts `doctor --json`, contrôle des versions et de la provenance des wheels.
- **Dépendances/risques :** 0.2, 1.3 et 2.2 ; dérive des runners et des paquets FFmpeg.

### 2.4 Réduire les alertes de chaîne logicielle par des corrections prouvées

**État :** verrous avec hashes appliqués aux outils CI/docs, pipx, au terminal
demo et au build conteneur ; [matrice CI complète](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35445459849),
[release à blanc](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35445461779),
[conteneur multi-architecture](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35449281881)
et [ClusterFuzzLite](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35449599477)
réussis. Le correctif `dab7197` remplace aussi le `read-all` global du workflow
ClusterFuzzLite par des permissions explicites ; la [CI déclenchée sur ce SHA](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35451503286)
et le [fuzzing avec ces permissions](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35451677762)
ont réussi. Le corpus de mutations a révélé puis corrigé une exception UTF-8 du
lecteur de receipts ; trois cibles et deux seeds ont tourné dans CI, puis la
cible Atheris a été reconnue par Scorecard. Au dernier inventaire après
`b9ceea7`, la [CI complète](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35449898003),
le [CodeQL](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35449897997)
et le [Scorecard](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35449898050)
ont aussi réussi ; le contrôle Scorecard relancé après la réduction des
permissions a également réussi dans le [run 35451875057](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35451875057).
Au relevé du 23 septembre après `0952c0e`, **483 alertes Trivy** restent
ouvertes (97 high, 199 medium, 164 low, 23 sans niveau de sévérité). Elles
proviennent d'instances du scan planifié `35847548151` sur l'ancien SHA
`25adc431` ; aucun nouveau scan de conteneur n'a été lancé. Il reste un signal
Scorecard : l'inscription externe OpenSSF Best Practices. Les trois alertes
Scorecard `TokenPermissionsID` ont disparu après le contrôle réussi
[`35913522219`](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35913522219).
Le triage détaillé figure dans `SECURITY_TRIAGE.md`. Le candidat Trixie n'est
pas encore publié. Le 24 septembre, les déclencheurs automatiques pull request,
push et planification du workflow Container ont été désactivés conformément à
l'instruction de ne pas exécuter Docker ; une exécution manuelle reste possible
mais n'est pas autorisée pendant cette pause. La validation des deux
architectures et l'inventaire récent des alertes restent incomplets.
L'inventaire GitHub paginé du 24 septembre confirme 484 alertes ouvertes : 483
Trivy liées à l'ancien SHA `25adc431` et une alerte LOW
`CIIBestPracticesID` liée à `main` sur `6d0994a`. CodeQL
[`35933577055`](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35933577055)
et Scorecard
[`35933576993`](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35933576993)
ont réussi sur ce SHA exact. Cette lecture API n'a déclenché aucun scan.

- **Objectif :** distinguer les vulnérabilités corrigibles, les avis sans correctif, les signaux de politique et les doublons historiques, puis réduire les causes plutôt que masquer les alertes.
- **Changements :** tenir `SECURITY_TRIAGE.md` à jour pour chaque digest ; tester et scanner aussi l'image arm64 avant publication ; remplacer les installations `pip` non verrouillées en CI/release/demo par des locks avec hashes pour la matrice Python/OS ; maintenir le corpus et l'intégration ClusterFuzzLite reconnus par Scorecard ; contrôler la couverture CodeQL et des tests sur les révisions proposées ; préparer les preuves du badge OpenSSF sans revendiquer son octroi prématurément.
- **Fichiers :** `Containerfile`, `.clusterfuzzlite/`, `.github/workflows/container.yml`, `ci.yml`, `release.yml`, `codeql.yml`, `scorecard.yml`, `scripts/run_terminal_demo.sh`, `pyproject.toml`, fichiers de lock, `tests/`, `fuzz_targets/`, `SECURITY_TRIAGE.md`.
- **Acceptation :** les deux architectures passent le filtre HIGH/CRITICAL corrigible et un smoke non-root ; installations CI/release déterministes avec hashes et contrôle des distributions ; cibles de fuzzing reproduisant au moins les erreurs de validation connues et exécutées en CI ; Scorecard et Code Scanning récents liés au même SHA, avec chaque alerte ouverte catégorisée. Le badge externe n'est annoncé que s'il est accordé.
- **Validation :** artefacts Trivy amd64/arm64, manifest OCI, exécution du lock sur Python 3.10–3.14 et les trois OS, corpus de fuzzing et crash replay, CodeQL/CI/Scorecard sur un SHA identique, revue manuelle des alertes restant ouvertes.
- **Dépendances/risques :** 0.3, 0.4 et 2.3 ; les avis Debian sans version corrigée ne peuvent pas être fermés honnêtement par un changement local, le score de revue dépend de la politique PR et le badge exige une validation externe.

**Gate 2 :** aucune régression des schémas publics, des politiques d'écrasement et d'annulation ; tests de sécurité, matrice et preuves de chaîne logicielle pertinents verts. Les alertes sans correctif restent visibles et suivies.

## Phase 3 — P1 : documentation, UX visuelle et positionnement

### 3.1 Corriger les documents qui décrivent une autre époque

**État :** checklist de prochaine release, canaux de distribution, politique
de dépréciation, URL GitHub canonique et étiquetage du cast `0.2.1` corrigés
localement. Un nouveau cast réel du wheel public `0.2.2` a été validé à
89,5 secondes avec transcript et deux images tirées de ses frames ; l'ancien
`0.2.1` reste archivé. Le 23 septembre, le site MkDocs construit et validé par
la [CI `35913779148`](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35913779148)
sur `86ff62d` a été publié dans le dépôt Pages par le commit `5c207a1`; le
[déploiement `35915228205`](https://github.com/OthmaneBlial/OthmaneBlial.github.io/actions/runs/35915228205)
a réussi. La page d'accueil et le cast public affichent maintenant `0.2.2`;
leurs liens GitHub pointent vers le dépôt canonique. Les pages en ligne
répondent HTTP 200. Le prochain changement de version devra republier et
revalider son propre site.

- **Objectif :** un nouvel utilisateur et un mainteneur lisent la même vérité sur la version et les canaux disponibles.
- **Changements :** remplacer les cases historiques de `RELEASE_CHECKLIST.md` par une checklist à remplir pour chaque version avec URLs de preuves ; aligner `CLI_DISTRIBUTION.md` sur wheel/sdist, image et Action ; résoudre la contradiction de fenêtre de dépréciation entre `docs/RELEASING.md` et `docs/api-stability.md` ; enlever le contournement `repo_url: https://github.com//...` devenu obsolète ; distinguer le cast `0.2.1` de la release `0.2.2` ou enregistrer un nouveau cast réel de la version publiée.
- **Fichiers :** documents cités, `mkdocs.yml`, `docs/terminal-demo.md`, `docs/index.md`, `README.md`.
- **Acceptation :** une recherche des versions, digests, durées et canaux ne laisse pas de contradiction ; chaque affirmation de release renvoie à son artefact exact ; les liens GitHub du site vont au dépôt canonique.
- **Validation :** `scripts/check_docs.py`, build MkDocs strict, `scripts/validate_terminal_demo.py` si cast renouvelé, revue humaine de la checklist et des liens.
- **Dépendances/risques :** gates 0–2 ; le cast existant doit rester archivé comme preuve de `0.2.1`, non être retouché pour paraître `0.2.2`.

Rendu public revérifié en clair et en sombre. Le rendu local a été contrôlé à
320, 375 et 1280 px sans débordement ; le site en ligne a été contrôlé à sa
largeur effective de 469 px, également sans débordement.

### 3.2 Faire voir l'application réelle dès le README

**État :** l'installation PyPI `0.2.2` a été enregistrée en PTY réel sur
macOS arm64/Python 3.14.6/FFmpeg 9.0.1 ; le validateur du dépôt accepte le
cast de 89,5 secondes. Deux PNG rendent sans ajout de texte les frames du
plan et du résultat/receipt, avec source et limites précisées dans le README.
Rendu du README vérifié visuellement sur GitHub en affichage clair par défaut
et à 375 px, y compris les deux PNG et leurs liens pleine résolution. À 375 px,
la largeur du document et celle du viewport valent toutes deux 375 px : aucun
débordement horizontal n'a été observé. Mode sombre et mise à jour après
prochaine release encore à vérifier.

- **Objectif :** que la première vue GitHub montre une commande, une décision de plan et un résultat réellement obtenus.
- **Changements :** raccourcir le mur de badges et placer un parcours vérifié au premier écran ; capturer de vraies images de terminal avec version, OS, date et fixture non privée ; montrer avant/après utile (format, pistes, taille ou loudness) avec un lien vers les receipts. Conserver la bannière SVG si elle aide la lecture, sans confondre console illustrative HTML et capture.
- **Fichiers :** `README.md`, `docs/assets/`, `docs/evidence.md`, `docs/recipes/`, éventuellement `scripts/record_terminal_demo.sh`.
- **Acceptation :** chaque image a source, légende et texte alternatif ; le haut du README dit pour qui, quel problème est résolu, comment installer et quel résultat attendre ; les chiffres viennent du média et du receipt cités.
- **Validation :** recopie du parcours sur wheel, contrôle des images et liens, revue du rendu GitHub en mode clair/sombre et sur écran étroit.
- **Dépendances/risques :** gates 1–2 ; données personnelles ou chemins privés dans une capture, captures périmées à chaque release.

### 3.3 Vérifier le site rendu et son accessibilité

**État :** page d'accueil locale contrôlée en navigateur à 320, 375, 768 et
1280 px sans débordement horizontal ; premier appel à l'action avancé sur
mobile, copie exacte de la commande vérifiée, thèmes clair/sombre et console
sans erreur observés. Les liens HTML du site sont désormais soumis au
contrôle des ancres. Sur l'accueil, le focus clavier est visible jusqu'à la
commande de copie. Les tableaux débordants d'architecture et de comparaison
ont maintenant une région nommée et focalisable à 320 px ; une flèche droite
fait défiler la colonne masquée, et le tab-stop disparaît à 1280 px. Revue
complète au lecteur d'écran encore à faire. Le 23 septembre, le site public a
aussi été vérifié sur `quickstart`, `terminal-demo`, `installation`, `recipes`
et `pipelines` (HTTP 200). Leurs arbres d'accessibilité exposent une navigation
nominative, des titres structurés et des liens descriptifs ; les deux captures
du cast ont un texte alternatif. Sur `quickstart`, la première tabulation montre
un focus visible sur « Skip to content » et le bouton d'installation confirme
la copie. Aucun défaut évident n'a été relevé dans cet échantillon ; les autres
pages et la revue avec lecteur d'écran restent à faire. Le 24 septembre, les
vérifications clavier des pages publiques `recipes` et `quickstart` ont montré
le lien « Skip to content » au premier focus ; Entrée place le fragment sur le
titre, puis la tabulation reprend dans le contenu. La page `terminal-demo`
expose deux images chargées avec un texte alternatif descriptif et des titres
de niveaux 1 puis 2. Cet échantillon navigateur ne remplace pas une revue avec
lecteur d'écran.

- **Objectif :** que l'identité visuelle existante serve la compréhension sur mobile et au clavier.
- **Changements :** auditer le site MkDocs réel à 320/375/768 px et desktop en clair/sombre ; contrôler débordements de code et tableaux, contraste, focus, réduction du mouvement, bouton de copie, navigation, liens de recette et absence d'erreurs console ; corriger uniquement les défauts observés. Garder une solution sans JavaScript pour copier l'installation.
- **Fichiers :** `docs/index.md`, `docs/stylesheets/extra.css`, `docs/javascripts/site.js`, `mkdocs.yml` et pages de référence.
- **Acceptation :** pas de défilement horizontal parasite, tous les contrôles atteignables au clavier, focus visible, commande copiée exacte, liens d'installation/release valides ; preuves par captures et notes de QA.
- **Validation :** build strict, navigateur réel, console et parcours clavier/lecteur d'écran de base sur tailles ciblées.
- **Dépendances/risques :** 3.1 ; audit de source CSS seul insuffisant, dépendance MkDocs/Material susceptible de changer.

### 3.4 Actualiser la comparaison concurrentielle par tâches

**État :** [x] comparaison datée du 19 septembre, cinq alternatives reliées
à leurs documentations officielles, scénario PyFFmpegCore relié au replay et
au receipt vérifiés, sans benchmark comparatif. Build strict, contrôle des
liens internes et tableau mobile validés localement. Sources externes à
réexaminer lors des prochaines releases majeures.

- **Objectif :** expliquer le bon choix d'outil sans promesse de supériorité inventée.
- **Changements :** reprendre `docs/comparison.md` avec une date, les documentations officielles actuelles de FFmpeg, `ffmpeg-python`, `python-ffmpeg`, `ffmpegio` et PyAV, puis un scénario commun (conversion contrôlée avec diagnostic, plan, sortie et preuve) ; distinguer capacités testées ici, capacités documentées ailleurs et limites. Relier les véritables différences au README.
- **Fichiers :** `docs/comparison.md`, `README.md`, `research_pyffmpegcore_roadmap/` ou notes de preuve renouvelées.
- **Acceptation :** chaque fait sur un concurrent a une source primaire datée ; aucun benchmark comparatif sans protocole équitable ; les cas où FFmpeg brut ou PyAV conviennent mieux restent explicites.
- **Validation :** revue des sources, reproduction du scénario PyFFmpegCore et contrôle des liens.
- **Dépendances/risques :** gates 1–2 ; les produits voisins évoluent, revue à chaque release majeure.

**Gate 3 :** README, docs et captures concordent avec le produit et l'artefact testés ; site vérifié visuellement ; comparaison sourcée.

## Phase 4 — P1 : packaging et prochaine release fiable

### 4.1 Vérifier exactement ce qui sera téléchargé

**État au 23 septembre 2026 :** le dry-run du candidat `0.3.0`
[`35921444046`](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35921444046)
a réussi sur le SHA exact `2d577f5ae9e83eb7343b618162a1b597adb005ce` : un bundle
wheel/sdist, contrôles `twine`/contenu/SHA-256, fixtures déterministes forcées
et six installations/tests du wheel exact sur Linux, macOS et Windows avec
Python 3.10/3.14. La CI générale `35920627403` du même SHA passe la qualité,
la matrice Python 3.10–3.14, la couverture à 80 %, la documentation, le fuzz et
les six ancres wheel ; CodeQL `35920627493` et Scorecard `35920627411` passent
aussi. Le dispatch `dry_run=true` saute signature de tag, attestations, PyPI,
installation publique et GitHub Release. Le candidat n'est ni signé ni publié.

**État :** [release à blanc `35447937367`](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35447937367)
réussie : bundle wheel/sdist construit une seule fois, SHA-256 contrôlés,
`twine check`, contenu et installations propres sur les six ancres OS/Python.
Le bundle du SHA `c22be1b` donne `71e89526…` pour le wheel et `df8823cf…`
pour le sdist ; les deux hashes et les archives ont été revérifiés après
téléchargement. Ils portent encore la version de travail `0.2.2` et ne sont
pas les fichiers PyPI déjà publiés sous ce numéro.
La [CI `35448000531`](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35448000531)
a de nouveau installé un seul wheel préconstruit sur ces six ancres. Sur macOS
arm64, `uv tool` 0.12.17 a installé hors réseau ce wheel CI exact
(`c5a00fc…` du run `35447046421`) en environnement isolé ; `--version`,
`doctor` et `smoke-test` ont réussi. L'essai `uv tool` du prochain artefact sur
les autres OS, la version finale, les attestations de publication et les
SHA-256 publics restent à valider ; tâche ouverte. Le [dry-run release
`35450686248`](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35450686248)
du SHA `94f4f9f` a depuis construit un bundle `0.2.2` unique, validé `twine`
et les six ancres Linux/macOS/Windows Python 3.10/3.14. L'artefact a été
téléchargé et ses sommes vérifiées : wheel
`9f0778000c5d84c2f65f3f01a83fedf2d3429d151dcf565ae915b7e5b0afa2cb`, sdist
`a9bdd153a52b1dd5166f1cc62725da8151e2fbb4836e2cd9d77882585254b675`. Ce
dry-run ne crée ni tag, ni nouvelle release, ni publication PyPI. Un nouveau
[dry-run `35916876361`](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35916876361)
sur le SHA `700e19b` a reconstruit le bundle une fois (395 561 octets), passé
`twine check` et le contrôle de contenu, puis validé le même wheel exact sur
les six ancres Linux/macOS/Windows et Python 3.10/3.14. Il confirme le bundle
de la tête courante ; la vérification du tag, les attestations et les contrôles
publics sont ignorés en dispatch manuel, et la version construite reste `0.2.2`.
Sur le SHA `d25e6ca3b90074aab78f1588dcd7a2064daaa2d5`, la CI générale a aussi
reconstruit les distributions une fois et réussi les six essais du wheel exact,
la couverture complète et les autres contrôles : 19 vérifications sur 19.
Aucun workflow Container n'a tourné. Cette preuve ne crée ni signature,
attestation, tag, release GitHub ou publication PyPI.
L'artefact `python-distributions` de ce run a été téléchargé (405 463 octets)
et contrôlé : wheel `pyffmpegcore-0.3.0-py3-none-any.whl`, 94 684 octets,
SHA-256 `729b408acd6be7aa850dc7b375893cc47f7cf469978e6f8e164c679472b21310` ;
sdist `pyffmpegcore-0.3.0.tar.gz`, 311 490 octets,
SHA-256 `dbd38ebfb8b8fe47492c4ca700f9d9ce3d0a6b981400e6786acdf3cc2644e7a0`.
Wheel, sdist et code source portent `0.3.0` ; le sdist contient README et
licence. L'artefact reste non publié et non attesté.

- **Objectif :** qu'un installateur retrouve dans wheel/sdist le même comportement que le checkout.
- **Changements :** bâtir une seule fois les distributions, inspecter contenu, version, licence et README rendu ; installer ces fichiers en environnement vierge ; vérifier `pipx`, `pip` et `uv tool` annoncés ; synchroniser le numéro de version entre code, tag, docs, Action et conteneur quand ils sont publiés ensemble.
- **Fichiers :** `pyproject.toml`, `MANIFEST.in`, `scripts/build_cli_artifacts.py`, `scripts/validate_cli_install.py`, `.github/workflows/release.yml`, `docs/installation.md`.
- **Acceptation :** wheel et sdist nommés, signés/attestés selon le pipeline, contenu contrôlé, sommes SHA-256 concordantes et CLI réelle testée depuis chaque canal annoncé ; aucune distribution reconstruite dans le job privilégié.
- **Validation :** `twine check`, inspection d'archives, installations propres sur OS de référence, comparaison des SHA-256 de release.
- **Dépendances/risques :** gates 0–3 ; dépôt PyPI et GitHub externes, paquet déjà publié immuable.

### 4.2 Aligner conteneur et Action sur un digest sain

**État :** [x] le digest `796661ae` de 0.3 est épinglé dans l'Action au SHA
`3a7315d` ; le [run `35447046432`](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35447046432)
a réussi la comparaison local/conteneur/Action et a produit les trois sorties.
L'index et ses deux manifests ont été récupérés anonymement et comparés à
leurs SHA-256 ; l'attestation du digest est valide. À rejouer sur le SHA de la
prochaine release avant de fermer le gate 4.

- **Objectif :** donner aux utilisateurs CI une intégration reproductible qui ne pointe pas vers un runtime ancien par inadvertance.
- **Changements :** après 0.3/0.4, remplacer le digest dans l'Action, le test d'intégration et les guides ; contrôler local/conteneur/Action sur la même pipeline et receipt normalisé ; conserver le réseau fermé par défaut et la politique de licences/SBOM.
- **Fichiers :** `action.yml`, `.github/workflows/action-integration.yml`, `tests/test_github_action.py`, `docs/container.md`, `docs/github-action.md`.
- **Acceptation :** le digest référencé existe, passe l'attestation et les scans, et le workflow d'intégration compare les sorties des trois chemins ; la documentation ne publie aucun digest non testé.
- **Validation :** récupération/inspection du digest, run Action intégration, sondage des médias générés et vérification des receipts.
- **Dépendances/risques :** 0.3, 0.4 et 4.1 ; propagation de plusieurs références, différence FFmpeg entre hôte et image.

### 4.3 Décider explicitement des exécutables autonomes

**État :** décision de distribution documentée dans
[`CLI_DISTRIBUTION.md`](CLI_DISTRIBUTION.md) : wheel/sdist restent les
artefacts officiels, le conteneur et l'Action sont des canaux séparés, et aucun
binaire autonome n'est annoncé. Aucun issue ou PR ouvert ne demande aujourd'hui
un exécutable natif ; la décision pourra être rouverte après les essais
indépendants de la phase 5. La preuve utilisateur requise pour fermer cette
tâche n'existe pas encore.

- **Objectif :** répondre au besoin de binaires téléchargeables sans confondre paquet Python et application autonome.
- **Changements :** relever, pendant les essais utilisateurs, si Python/pipx est le vrai obstacle ; chiffrer taille, démarrage, signature/notarisation, mises à jour de sécurité et dépendance FFmpeg externe. Si la demande est avérée, prototyper un exécutable sur un OS, puis étendre seulement avec CI, signatures, hashes et tests propres ; sinon maintenir wheel/sdist comme téléchargement officiel et expliquer ce choix.
- **Fichiers :** `CLI_DISTRIBUTION.md`, `docs/installation.md`, et, si retenu, scripts de packaging, `.github/workflows/release.yml` et guide de vérification.
- **Acceptation :** décision écrite avec observations utilisateurs et coûts ; si binaire livré, téléchargement par OS/architecture, `--version`/`doctor`/`smoke-test` sur machine propre, signature et checksums vérifiés. Si refusé, aucune mention « binaire autonome » dans le README.
- **Validation :** essais utilisateur phase 5 préparatoires, prototype isolé, tests de sécurité et d'installation ; revue des licences si FFmpeg devait un jour être embarqué.
- **Dépendances/risques :** 4.1 et demandes d'installation déjà observables dans les issues/support ; coût Apple/Windows et maintenance de FFmpeg. Les essais de 5.1 pourront rouvrir la décision, sans bloquer une release Python saine.

### 4.4 Publier la prochaine version et contrôler son état public

**État au 23 septembre 2026 :** le candidat `0.3.0` a passé son
[dry-run `35921444046`](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35921444046)
sur le SHA `2d577f5ae9e83eb7343b618162a1b597adb005ce`; tous les contrôles de
construction et les six tests du wheel exact ont réussi. Aucun tag `v0.3.0`,
attestation, release GitHub ou upload PyPI n'a été créé. Le PyPI public reste
`0.2.2`. La publication exige une autorisation et les gates publics ; l'Action
et le conteneur n'ont pas été revalidés pour ce candidat, et aucun build
conteneur n'a été exécuté conformément à l'instruction du mainteneur.

**État historique :** les dry-runs `35450686248` et
[`35916876361`](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35916876361)
construisent et testent les bundles `0.2.2`, mais aucun nouveau tag, release
GitHub ou upload PyPI n'a été créé. Une publication réelle nécessite une
autorisation et les contrôles publics correspondants ; la release `v0.2.2`
reste l'artefact public de référence.

- **Objectif :** remplacer la preuve historique `v0.2.2` par une release qui inclut les corrections précédentes.
- **Changements :** remplir la checklist par liens réels ; changelog et notes de migration ; tag annoté signé ; exécuter le pipeline de publication existant ; vérifier les fichiers publics PyPI et GitHub, checksums, attestations, installation, page docs et digest GHCR/Action si annoncés ; faire correspondre le statut de la release GitHub au classifier de maturité du paquet. En cas de gate rouge, corriger puis publier une nouvelle version sans réécrire l'ancienne.
- **Fichiers :** `CHANGELOG.md`, `RELEASE_CHECKLIST.md`, `docs/RELEASING.md`, `.github/release-notes/`, `README.md`, `docs/COMPATIBILITY.md`.
- **Acceptation :** tag, version CLI, PyPI, wheel, sdist, release GitHub, attestations et notes nomment la même version ; tous les chemins annoncés sont accessibles ; aucun run requis rouge au SHA de release.
- **Validation :** lecture des runs exacts jusqu'à succès, installation depuis PyPI et assets publics sur trois OS, sondage du conteneur et QA des liens du README/site.
- **Dépendances/risques :** gates 0–3 et 4.1–4.2 ; permissions des services externes, délais d'indexation et releases immuables.

**Gate 4 :** une version nouvelle, installable et traçable est publique. Wheel/sdist sont obligatoires ; exécutables natifs restent conditionnels à la décision 4.3.

## Phase 5 — P2 : adoption et contributions fondées sur l'usage

### 5.1 Observer des premiers usages indépendants

**État :** reportée pour le moment à la demande du mainteneur le 23 septembre
2026 ; aucune invitation ni sollicitation ne doit être lancée. Le dépôt ne
contient pas cinq essais consentis par des utilisateurs indépendants ; les
installations locales et CI ne peuvent pas les remplacer.

- **Objectif :** savoir si les promesses de cinq minutes, diagnostic et receipt sont compréhensibles hors de l'équipe.
- **Changements :** faire essayer l'installation et un résultat utile à au moins cinq personnes du public cible sur des machines différentes, avec consentement ; relever OS, version FFmpeg, temps, blocages et résultat, sans collecter leurs médias ni télémétrie par défaut ; corriger les obstacles récurrents avant une diffusion large.
- **Fichiers :** `docs/quickstart.md`, `docs/troubleshooting.md`, `docs/community.md`, issues et tests correspondant aux défauts ; note anonymisée de protocole/résultats.
- **Acceptation :** cinq essais documentés, réussite/échec et temps séparés, au moins quatre parcours complets sans aide ou une itération supplémentaire si ce seuil n'est pas atteint ; limites honnêtes publiées.
- **Validation :** observation directe ou transcript consenti, reproductibilité des défauts, nouveau test et nouvel essai après correction.
- **Dépendances/risques :** gate 4 pour tester l'artefact public final ; recrutement et confidentialité, résultat externe non fabriquable par CI.

### 5.2 Garder une entrée de contribution vivante

**État :** structure documentaire prête, mais aucune nouvelle contribution
indépendante n'est prouvée. La vérification GitHub du 24 septembre confirme
que la file historique d'issues `#7`–`#11` est fermée et que la liste des
issues ouvertes est vide ; aucune tâche communautaire active ne peut être
citée.

- **Objectif :** transformer les demandes réelles en améliorations maintenables.
- **Changements :** vérifier que les issues `#7`–`#11` et labels cités dans `docs/community.md` sont toujours ouverts/pertinents ; fermer ou réécrire les sujets obsolètes, ajouter des tâches bornées tirées des essais, préciser tests et critères ; créditer les contributeurs et appliquer les délais de support annoncés.
- **Fichiers :** `CONTRIBUTING.md`, `SUPPORT.md`, `docs/community.md`, formulaires `.github/ISSUE_TEMPLATE/` et issues GitHub.
- **Acceptation :** au moins cinq premières contributions réellement actionnables, chacune avec fichier de départ, résultat attendu et commande de validation ; pas d'issue « facile » bloquée par une décision produit non prise.
- **Validation :** essai du parcours contributeur depuis un clone propre et revue des liens/états des issues.
- **Dépendances/risques :** 5.1 ; capacité de triage, disponibilité d'autres contributeurs.

### 5.3 Partager une preuve vérifiable dans les bons canaux

**État :** non publié. `LAUNCH.md` contient le runbook et des brouillons, mais
aucune publication communautaire vérifiable liée à une nouvelle release n'a
été effectuée.

- **Objectif :** faire connaître un outil qui résout un problème concret, sans sollicitation artificielle de stars.
- **Changements :** réviser les règles actuelles de chaque communauté avant publication ; publier un exemple reproductible et l'affiliation du mainteneur ; consigner URL, date, release et retour technique dans `LAUNCH.md` ; améliorer les recettes à partir des questions répétées.
- **Fichiers :** `LAUNCH.md`, `README.md`, `docs/recipes/`, notes de release et issues pertinentes.
- **Acceptation :** au moins une publication publique toujours accessible et liée à une release fonctionnelle ; retours qualifiés séparés des vues, téléchargements et stars ; aucune revendication « le plus rapide/le plus sûr » non mesurée.
- **Validation :** ouverture des liens publics, relecture du texte posté et essai de la commande partagée depuis l'artefact public.
- **Dépendances/risques :** gates 4 et 5.1 ; règles communautaires changeantes et absence possible de retours.

**Gate 5 :** retours indépendants intégrés, parcours contributeur vérifié, au moins un partage public documenté. Si les essais entraînent une correction du produit, repasser par les gates concernés et publier une version corrigée avant la vidéo. Les stars et téléchargements ne remplacent aucun de ces critères.

## Phase 6 — finale : vraie vidéo du produit terminé

> **Interdiction de produire cette vidéo avant validation des gates 0 à 5.** Le cast `v0.2.1` existant reste une archive de preuve ; il ne satisfait pas cette phase. Utiliser obligatoirement la skill **`ffmpeg-video-editor`** au moment de la capture et du montage.

**État :** bloquée par les gates 4 et 5 non clôturés. Aucun export vidéo final
ne doit être présenté comme la démonstration du produit terminé tant qu'une
release publique et des retours indépendants ne sont pas prouvés.

### 6.1 Écrire un scénario à partir de la release finale

- **Objectif :** montrer en moins de deux minutes le problème résolu et le chemin réel vers un résultat.
- **Changements :** choisir un média de démonstration légal et reproductible ; storyboard « commande FFmpeg fragile/problème d'upload ou de profil → installation/démarrage → `doctor` → `--explain` → exécution/progress → `probe`/receipt → sortie lue ». Inscrire version, OS, FFmpeg et commandes exactes dans un journal de tournage.
- **Fichiers :** nouveau dossier de captures et storyboard sous `docs/assets/` ou `media/`, `README.md` après export, release liée.
- **Acceptation :** chaque phrase du script correspond à une étape visible ou à une preuve liée ; pas de fonctionnalité, sortie, comparaison ou gain simulé.
- **Validation :** rejouer le scénario sur l'artefact public de la phase 4 et vérifier le média/receipt avant enregistrement.
- **Dépendances/risques :** gates 0–5 ; média privé, outil ou build différent du produit publié.

### 6.2 Capturer l'utilisation réelle

- **Objectif :** enregistrer les vrais pixels du terminal et la vraie sortie du produit.
- **Changements :** capturer une installation ou un démarrage depuis l'artefact public, puis les fonctionnalités principales ; enregistrer la sortie média et sa lecture réelle ; conserver les prises brutes et leur provenance, masquer seulement les informations personnelles. Refaire une prise si une étape échoue au lieu de fabriquer une console.
- **Fichiers :** prises brutes, journal de capture, média d'entrée autorisé, receipt et sortie vérifiée.
- **Acceptation :** vidéo source continue ou prises traçables ; aucun mockup, écran fictif, fausse progression ou commande non exécutée.
- **Validation :** cohérence des horodatages, comparaison des commandes et receipts, sondage `ffprobe` du fichier produit et visionnage des prises.
- **Dépendances/risques :** 6.1 ; terminal illisible, chemins privés, temps morts et encodeur absent.

### 6.3 Monter et exporter avec `ffmpeg-video-editor`

- **Objectif :** créer une démonstration courte, lisible et professionnelle sans déformer les faits.
- **Changements :** suivre la skill : sonder d'abord les sources, découper les attentes, poser des titres sobres, recadrages/zooms utiles et transitions discrètes ; nettoyer/normaliser la voix si utilisée, sinon garder un silence intentionnel ; fournir sous-titres/transcription accessibles. Exporter un MP4 H.264 `yuv420p` avec `+faststart` adapté à un lien README/GitHub, poster et, si le récit tient, une variante courte pour réseaux sociaux. Publier les fichiers avec la release ou un hébergement durable et lier la vidéo depuis le README.
- **Fichiers :** sources, script/commande de montage, export MP4, poster, transcription, `README.md`, page `docs/terminal-demo.md` ou page vidéo dédiée.
- **Acceptation :** installation/démarrage, problème, plan, exécution et résultat restent lisibles ; export principal et variante éventuelle pointent vers la même version finale ; droits du média et de l'audio documentés.
- **Validation :** contrôle visuel du montage complet et des titres, écoute au casque si audio, contrôle des liens publiés.
- **Dépendances/risques :** 6.2 ; poids GitHub, lisibilité après compression, codecs audio et musique sous licence.

### 6.4 Vérifier le fichier livré de bout en bout

- **Objectif :** ne publier qu'une vidéo réellement lisible et conforme à ses annonces.
- **Changements :** consigner durée, résolution, fréquence d'images, codecs, taille et SHA-256 par `ffprobe`/`shasum` ; décoder intégralement avec FFmpeg vers `null` ; lire le fichier du début à la fin dans un lecteur, puis ouvrir les liens README/release publiés. Vérifier poster, transcription et version courte séparément.
- **Fichiers :** rapport de vérification de vidéo, exports, `README.md`, release finale.
- **Acceptation :** décodage sans erreur, lecture humaine complète, son propre si présent, dimensions/durée/poids documentés, liens fonctionnels et aucun plan qui affirme un résultat absent.
- **Validation :** `ffprobe -show_streams -show_format`, décodage FFmpeg complet, somme SHA-256 source/destination et lecture réelle.
- **Dépendances/risques :** 6.3 ; l'upload réussi ne prouve ni la lecture intégrale ni le rendu sur la page GitHub.

## Résultat attendu

Une release Python et des intégrations CI dont les contrôles actuels sont verts ; un premier workflow utile reproductible en quelques minutes ; une documentation et une présentation visuelle fidèles au produit ; une frontière de sécurité explicite ; des retours d'utilisateurs et de contributeurs vérifiables ; puis seulement une vidéo montrant le produit final en action. Cet ensemble peut rendre PyFFmpegCore recommandable et plus visible. Aucun nombre de stars n'est garanti.
