# Timeline replay

Attack timelines on **Timeline** can be stepped through chronologically with play/pause controls.

## Features

- **Play / pause** — auto-advance through events using inter-event timing (scaled by speed)
- **Step controls** — restart, next step
- **Scrubber** — jump to any step in the chain
- **Speed** — 0.5x, 1x, 2x, 4x
- **Visual progress** — connector line and highlight follow the current step; future steps stay dimmed until reached

## Deep links

```
/timeline?timeline={uuid}
/timeline?host={host_uuid}&timeline={uuid}
```

## API

Uses existing endpoints:

```
GET /api/v1/timelines
GET /api/v1/timelines/{id}/events
```

Events are ordered by `timestamp` ascending for replay.
