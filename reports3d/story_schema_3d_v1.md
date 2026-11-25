# 3D Story Schema — `3d_story_v1`

Versioned input contract for the 3D renderer. The AI (or a human) writes ONLY
this JSON; every capability it references is validated against
`character_capabilities.json`-derived catalogs before rendering. Unknown IDs
fail with the allowed list — never silently replaced.

```json
{
  "schema_version": "3d_story_v1",
  "title": "string",
  "language": "de-DE | en-US | es-ES",
  "level": "A1..C2",
  "seed": 42,
  "scenes": [
    {
      "environment": "student_room | hallway | cafe | park",
      "turns": [
        {
          "text": "one spoken line (required)",
          "action": "idle | walk_to | sit | sit_idle | stand | talk_gesture | sit_talk_gesture | wave | point_at | think | nod | shake_head | fold_arms | read_book | drink | look_around",
          "target_anchor": "chair_approach | door | bench   (walk_to only)",
          "expression": {"name": "neutral | happy | smile | sad | surprised | angry | laugh | relaxed | worried | confused | thinking", "intensity": 0.0..1.0},
          "gaze_target": "camera | door | mug | book | window | table | forward | trees | bench | chair",
          "camera": "establishing | medium | closeup | fullbody | side | over_shoulder | tracking | push_in",
          "pause_ms": 400
        }
      ]
    }
  ]
}
```

Validation rules (enforced in `sandbox3d/story_compiler.py`):
- unknown environment / action / expression / gaze_target / camera -> error
  listing the allowed values;
- `sit*` requires a `chair` anchor in the environment; `drink` a mug;
  `read_book` a book; `walk_to` a target anchor;
- intensity clamped to 0..1; every turn must have `text`;
- per-turn beat duration = max(action min_dur, 0.5 s + speech + pause_ms).

## AI story-generation prompt (paste into any chat model)

```
Write a short language-learning story as JSON following schema 3d_story_v1
(schema below). Rules:
- Level A2 German, 10-13 turns across 2-3 scenes; every turn's "text" is ONE
  simple spoken sentence (max ~12 words) suitable for a beginner.
- Use ONLY the enum values listed in the schema. Do not invent actions,
  expressions, gaze targets, camera names, or environments.
- Give every turn an expression and a camera; vary the camera
  (establishing -> medium/closeup -> ...); use "tracking" for walk_to turns.
- Express the story through the capability list: walk_to to change place,
  sit/sit_idle at chairs, drink/read_book when a mug/book anchor exists,
  wave/point_at/think/nod/shake_head/fold_arms for gestures.
- End with a turn gazing at "camera".
[insert 3d_story_v1 schema block here]
Return ONLY the JSON, no markdown fences.
```

## Compiled timeline (`interaction_v1`) — consumed by godot3d/director.gd
Absolute-frame parallel tracks at 30 fps: paths, turns, body (clip+blend),
attachments (hand/world + tween), expressions, gaze, blinks, visemes,
head_nod, camera (absolute / avatar_relative / yaw_relative + bounds +
push_to + track_avatar + smooth), scenes, scene_objects, subtitles, fades,
door. Deterministic: same story JSON + seed -> byte-identical timeline.
