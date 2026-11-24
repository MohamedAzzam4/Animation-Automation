# Anna + Ben Asset Pack for Godot — source art

This ZIP is a curated handoff of the actual images generated in the chat. It is **not yet a finished game-ready rig**. The PNG sheets are RGBA, but multiple assets share a canvas, some elements include imperfect transparency or residue, and some source art variants have different pose angles. Inspect and crop/mask/clean individual pieces; do not assert that Godot-ready sprites are supplied.

Canonical characters:
- Anna: copper-red bob hair, teal overshirt, white undershirt, brown trousers.
- Ben: curly dark brown hair, short beard, mustard-yellow overshirt, white undershirt, dark brown trousers.

Contents:
- `reference/`: canonical character portraits to compare identity and clothing.
- `design/`: costume/turnaround source sheets.
- `parts_sheets/`: tentative rig cutout sheets; require extraction and QC.
- `faces/`: expression sheets and candidate facial masks/mouth shapes.
- `poses/`: gestures, seated and conversational reference/fallback composites.
- `backgrounds/`: four original 1672×941 landscape backgrounds; maps to student room, station, café, park.
- `storyboard/`: pilot mood/storyboard only, not actual frames.
- `pilot/lesson_ticket.json`: proposed test storyline, manual fixture; no voice files included.
- `GLM_IMPLEMENTATION_PROMPT.md`: main agent handoff with phased acceptance tests and official Godot download.
- `manifest.json`: inventory with SHA-256 checksums and source properties.

**Important:** `reference/` and sheet files are *art references/source sheets*, not individual separately exported Godot `Sprite2D` resources. No hand-painted missing anatomy or frame-perfect animations have been added. The agent must measure/verify any rig/pivots, correct artifacts, and document missing parts or use composite fallback.

Install Godot from https://godotengine.org/download/ . Learn Godot Movie Maker: https://docs.godotengine.org/en/stable/tutorials/animation/creating_movies.html
