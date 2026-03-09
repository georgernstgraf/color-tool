# Project State

Current status as of 2026-03-09.

## Current Focus
The theme pipeline now uses committed numbered-cluster `palette.css` files under `themes/` as the editable source between dual-image extraction and generated `themes/<name>/theme.css` files.

## Completed (this cycle)
- [x] Captured the generation pipeline, CSS load order, glass architecture, dark-mode strategy, testing approach, and deployment assumptions from `README.md` and `ARCHITECTURE.md`
- [x] Added the AI knowledge bootstrap instructions in `AGENTS.md`
- [x] Removed `ARCHITECTURE.md` after migrating the remaining architecture details into `docs/ai/`
- [x] Refactored `ColorSim.py` into dual-image extraction, `palette.css`, and palette-to-theme modes
- [x] Moved active bundled themes to `themes/` and reduced the preview/build to valid dual-image themes only
- [x] Preserved numbered cluster variables in `palette.css` and refined the semantic `*-source` mappings for `alien`, `krokus`, and `lego`
- [x] Changed bundled generated theme output to `themes/<name>/theme.css` and let `generate_all.sh` auto-create missing palettes from valid dual-image assets
- [x] Cleaned `themes/leisure/` asset naming, removed the stray SVG typo file, and let `generate_all.sh` create its first `palette.css`

## Pending
- [ ] None

## Blockers
- None

## Next Session Suggestion
Start with `docs/ai/HANDOFF.md`, then inspect `themes/<name>/palette.css` and `ColorSim.py` if the next task changes extraction heuristics, palette semantics, or the set of active dual-image themes.
