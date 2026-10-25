# gamedev-hub

Контрольная панель по всем игровым проектам. Генерируется автоматически из [`projects.yaml`](projects.yaml) и GitHub API, руками не правится.

**Дашборд:** https://artemiishabanov.github.io/gamedev-hub/ · **Процесс:** [WORKFLOW.md](WORKFLOW.md) · **Шаблон проекта:** [template/](template/)

## Проекты

| Игра | Фаза | Движок | Прогресс | Открыто | Последний коммит | 30 дн. | Всего |
|---|---|---|---|--:|---|--:|--:|
| **[RallyRivals](https://github.com/artemiiShabanov/RallyRivals)**<br><sub>Аркадные ралли-гонки против ИИ-соперников, 3D</sub> | контент | Godot 4.4 | `█████████░` 89% (132/149) | 17 | 2026-10-25<br><sub>Workflow: drop tasks.yaml, tasks.py and STATUS.md — the back</sub> | 2 | 278 |
| **[No-Extraction](https://github.com/artemiiShabanov/No-Extraction)**<br><sub>Снайпер на крепостной стене против волн рыцарей</sub> | вертикальный срез | Godot 4.7 | `██░░░░░░░░` 25% (13/53) | 40 | 2026-10-25<br><sub>project.yaml: next reflects the open M1 issue (#10)</sub> | 2 | 40 |
| **[slash-dash-slash](https://github.com/artemiiShabanov/slash-dash-slash)**<br><sub>Мобильный роглайк-слэшер, где рывок — единственный глагол; меч, самоцветы и офис 1970-х с настоящей магией</sub> | прототип | Godot 4.4 (mobile) | `█░░░░░░░░░` 14% (10/70) | 60 | 2026-10-25<br><sub>Align with gamedev-hub workflow: docs/, plan.yaml, sync_plan</sub> | 1 | 29 |
| **[FingerRally](https://github.com/artemiiShabanov/FingerRally)** · [App Store](https://apps.apple.com/ru/app/finger-rally/id6752858585?l=en-GB)<br><sub>Бесплатные бесконечные гонки на Godot (в App Store: Finger Rally)</sub> | выпущена | Godot 4.4 | — | — | 2025-10-06<br><sub>fixes</sub> | 0 | 18 |
| **[Just-Cards-Actually](https://github.com/artemiiShabanov/Just-Cards-Actually)** · [App Store](https://apps.apple.com/ru/app/card-collector-simulator/id6751577495?l=en-GB)<br><sub>Бесплатная игра про коллекционирование карт на Godot (в App Store: Card Collector Simulator)</sub> | выпущена | Godot 4.4 | — | — | 2025-09-05<br><sub>fix timer</sub> | 0 | 26 |
| **[Office-Worker-Simulator](https://github.com/artemiiShabanov/Office-Worker-Simulator)** · [App Store](https://apps.apple.com/ru/app/office-worker-simulator/id6448135661?l=en)<br><sub>2D-игра на SpriteKit, учебный проект</sub> | выпущена | SpriteKit (Swift) | — | — | 2023-04-30<br><sub>Update index.md</sub> | 0 | 7 |
| **[Cube-Squared](https://github.com/artemiiShabanov/Cube-Squared)** · [App Store](https://apps.apple.com/ru/app/cube-squared/id6446372432?l=en)<br><sub>2D-игра на SpriteKit, первая игра в App Store</sub> | выпущена | SpriteKit (Swift) | — | — | 2023-04-02<br><sub>Update README.md</sub> | 0 | 5 |

## Активность

Каждая клетка — день; цвет — игра, над которой шла работа; две игры в день делят клетку.

![calendar](docs/calendar.svg)

### RallyRivals

Дальше: M1: тюнинг чувства езды и честная гонка против ИИ, затем первая настоящая трасса

- M0 Сделано до миграции `██████████` 100% 132/132 · закрыта
- M1 Чувство езды и честная гонка `░░░░░░░░░░` 0% 0/6
- M2 Вертикальный срез `░░░░░░░░░░` 0% 0/3
- M3 Контент кампании `░░░░░░░░░░` 0% 0/4
- M4 Релиз `░░░░░░░░░░` 0% 0/4

### No-Extraction

Дальше: M1: закрыть плейтест 1 (#10) и ответить, весело ли ядро; дальше M2 контент

- M0 Прототип и проверка рисков `██████████` 100% 4/4 · закрыта
- M1 Вертикальный срез: один забег `█████████░` 90% 9/10
- M2 Контент и разнообразие `░░░░░░░░░░` 0% 0/10
- M3 Мета и прогрессия `░░░░░░░░░░` 0% 0/6
- M4 Смачность и полировка `░░░░░░░░░░` 0% 0/10
- M5 Релиз в Steam `░░░░░░░░░░` 0% 0/10
- M6 Если останется время `░░░░░░░░░░` 0% 0/3

### slash-dash-slash

Дальше: M1 Вертикальный срез: этаж B от старта до босса — сначала комбо гемов и арена с эскалацией (ROADMAP M7, M9)

- M0 Боевое ядро `██████████` 100% 10/10 · закрыта
- M1 Вертикальный срез: этаж B от старта до босса `░░░░░░░░░░` 0% 0/10
- M2 Контент и разнообразие `░░░░░░░░░░` 0% 0/11
- M3 Четыре этажа и история `░░░░░░░░░░` 0% 0/10
- M4 Мета и концовки `░░░░░░░░░░` 0% 0/8
- M5 Смачность и полировка `░░░░░░░░░░` 0% 0/9
- M6 Релиз `░░░░░░░░░░` 0% 0/8
- M7 Если останется время `░░░░░░░░░░` 0% 0/4

## Как пользоваться

- Добавить или изменить проект: правка `projects.yaml`, коммит. Фазу удобнее держать в `project.yaml` самого проекта, хаб её подхватит.
- Пересобрать вручную: `python3 tools/build_dashboard.py` (нужен `gh auth login` или `GITHUB_TOKEN`).
- Новый проект: `python3 tools/new_project.py MyGame --tagline "..."`.
- Автосборка: раз в сутки и при каждом пуше, см. `.github/workflows/dashboard.yml`.

<sub>Обновлено 2026-10-25T16:31+03:00 (Europe/Moscow)</sub>
