# Step Recorder for QGIS

**Record what you do in QGIS and turn it into a step-by-step tutorial** - like the *Steps Recorder* in Windows, built for GIS.

Press record, do your task normally, and the plugin writes numbered, human-readable instructions with an annotated screenshot for each action. Edit them, then export a ready-to-share tutorial.

> Status: first public release (experimental). Feedback and bug reports are very welcome - see [Contributing](#contributing).

<!-- Add screenshots here, e.g. ![panel](docs/panel.png) -->

## Features

- **Records** menu choices (full path), opening of menus / submenus / toolbar drop-downs, toolbar and dialog buttons, checkboxes, radio buttons, tabs, combo boxes, typed and numeric values, file and CRS widgets, layer-tree and table clicks, map-canvas clicks / drags / zoom (with coordinates and active tool), keyboard shortcuts.
- **Understands results**: dialogs opening, message-bar messages, layers added / removed, edit mode, selections, project saved / opened, CRS changes.
- **Processing aware**: pressing *Run* lists every setting used and attaches the equivalent `processing.run(...)` Python command. Python Console runs are recorded too.
- **Screenshots** for every step with the clicked element highlighted.
- **Edit before export**: hide steps, drag to reorder, edit text, add notes and extra screenshots.
- **Export** to Markdown, HTML (single self-contained file), PDF, plain text, or save the session as JSON.
- **Languages**: English, العربية (Arabic), کوردی سۆرانی (Kurdish Sorani) - with right-to-left output.
- Passwords are never recorded.
- Works on QGIS 3.22+ (Qt5) and QGIS 4 (Qt6).

## Install

**From the QGIS Plugin Repository** (once approved): *Plugins ▸ Manage and Install Plugins*, search for **Step Recorder**. The plugin is flagged *experimental*, so enable *Show also experimental plugins* in the **Settings** tab.

**From a ZIP**: download `step_recorder.zip` from the [Releases](../../releases) page, then *Plugins ▸ Manage and Install Plugins ▸ Install from ZIP*.

**From source**: copy the `step_recorder` folder into your QGIS profile's `python/plugins/` directory and enable it.

## Use

1. Click the **Step Recorder** toolbar icon to open the panel.
2. Enter a tutorial title and choose the language.
3. Press **● Start recording** and perform your task. The panel floats so it stays out of screenshots.
4. Press **■ Stop recording**, then tidy the list (untick to hide, drag to reorder, double-click to edit, right-click for more).
5. Press **Export…**.

Step text uses simple markup: `**bold**` for interface elements and `` `code` `` for values.

## Screenshots

<img width="621" height="453" alt="image" src="https://github.com/user-attachments/assets/a1bce9fd-f41f-4176-a826-f9db90a592ac" />
<img width="637" height="433" alt="image" src="https://github.com/user-attachments/assets/4f0589dd-280c-4f5f-b643-f2984c3ed1d2" />
<img width="1258" height="661" alt="image" src="https://github.com/user-attachments/assets/7735d48a-f616-4824-a88b-a3ce9125208e" />


## Troubleshooting

If something is not recorded, open **View ▸ Panels ▸ Log Messages ▸ StepRecorder** - internal errors are written there. Please include that output when you report a problem.

## Contributing

Bug reports, ideas and translations are welcome - open an [issue](../../issues). When reporting a problem please include your QGIS version, operating system, what you did, and the Log Messages output.

All instruction wording lives in `step_recorder/i18n.py`, so adding a language means adding one dictionary there.

Run the tests (no QGIS needed):

```bash
python3 tests/test_pure.py          # text, model and export logic
python3 tests/test_import_stubs.py  # import / undefined-name smoke test
python3 tests/test_security_patterns.py  # mirrors the Bandit checks
```

(`test_pure.py` needs Pillow for its sample screenshots.)

## License

GPL-2.0-or-later - see [LICENSE](LICENSE).
