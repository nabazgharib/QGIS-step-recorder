# -*- coding: utf-8 -*-
"""Tests for the Qt-free parts: textutils, i18n, model, exporter.

Run:  python3 tests/test_pure.py
"""
import importlib.util
import json
import os
import sys
import tempfile
import types
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PKG_DIR = os.path.join(ROOT, "step_recorder")

# Load the package WITHOUT executing __init__ side effects / needing qgis.
pkg = types.ModuleType("step_recorder")
pkg.__path__ = [PKG_DIR]
sys.modules["step_recorder"] = pkg

from step_recorder import textutils, i18n, model, exporter  # noqa: E402  (after sys.modules patch)


def _png(path, color=(200, 30, 30)):
    from PIL import Image
    Image.new("RGB", (120, 60), color).save(path)


def make_session(tmp, lang="en"):
    s = model.Session("Buffer tutorial", "Tester", "Make a buffer.", lang, base_dir=tmp)
    img = s.new_image_path()
    _png(img)
    s.add(model.Step(i18n.T(lang, "menu_bar", path="Vector ▸ Geoprocessing Tools ▸ Buffer…"),
                     image=img, kind="menu"))
    s.add(model.Step(i18n.T(lang, "dialog_open", title="Buffer"), role=model.ROLE_RESULT, kind="dialog"))
    s.add(model.Step(i18n.wrap_context(lang, ("dialog", "Buffer"),
                     i18n.T(lang, "set_value", label="Distance", value="500")), kind="field"))
    s.add(model.Step(i18n.T(lang, "button", name="Run"), kind="button",
                     details=["**Distance**: `500`", "**Input layer**: `roads`"]))
    s.add(model.Step(i18n.T(lang, "proc_done", name="Buffer"), role=model.ROLE_RESULT,
                     command="processing.run('native:buffer', {'DISTANCE': 500})"))
    s.add(model.Step("Tip: save often!", role=model.ROLE_NOTE))
    s.add(model.Step("hidden step", enabled=False))
    s.add(model.Step(i18n.T(lang, "button", name="Close")))
    return s


class TextUtils(unittest.TestCase):
    def test_clean_text(self):
        self.assertEqual(textutils.clean_text("&Open Project…\tCtrl+O"), "Open Project…")
        self.assertEqual(textutils.clean_text("Save && Close"), "Save & Close")
        self.assertEqual(textutils.clean_text("<b>Run</b>  now"), "Run now")

    def test_clean_label(self):
        self.assertEqual(textutils.clean_label("Distance (meters):"), "Distance (meters)")

    def test_pretty_name(self):
        self.assertEqual(textutils.pretty_name("mLineEdit_bufferDistance"), "Buffer distance")
        self.assertEqual(textutils.pretty_name("qt_spinbox_lineedit"), "")
        self.assertEqual(textutils.pretty_name("cmbLayer"), "Layer")

    def test_clean_title(self):
        self.assertEqual(textutils.clean_title("roads — Features Total: 10, Filtered: 10, Selected: 0"),
                         "roads — Attribute Table")
        self.assertEqual(textutils.clean_title("Buffer"), "Buffer")

    def test_strip_markup(self):
        self.assertEqual(textutils.strip_markup("Click **OK** and type `5`"), "Click OK and type 5")

    def test_shorten(self):
        self.assertEqual(len(textutils.shorten("x" * 200, 30)), 30)


class I18N(unittest.TestCase):
    def test_all_english_keys_exist_in_other_languages(self):
        for lang in ("ar", "ckb"):
            self.assertEqual(set(i18n.TEMPLATES["en"]) ^ set(i18n.TEMPLATES[lang]), set(), lang)

    def test_languages_registered(self):
        self.assertEqual(set(i18n.LANGUAGES), {"en", "ar", "ckb"})
        self.assertTrue(i18n.is_rtl("ckb") and i18n.is_rtl("ar") and not i18n.is_rtl("en"))

    def test_placeholders_match(self):
        import re
        ph = lambda t: set(re.findall(r"\{(\w+)\}", t))  # noqa: E731
        for lang in ("ar", "ckb"):
            for k, v in i18n.TEMPLATES["en"].items():
                self.assertEqual(ph(v), ph(i18n.TEMPLATES[lang][k]), (lang, k))

    def test_wrap_context_lowercases_en(self):
        self.assertEqual(i18n.wrap_context("en", ("dialog", "Buffer"), "Click **Run**"),
                         "In the **Buffer** dialog, click **Run**")
        self.assertEqual(i18n.wrap_context("en", ("panel", "Layers"), "Click **roads**"),
                         "In the **Layers** panel, click **roads**")
        self.assertEqual(i18n.wrap_context("en", None, "Click **Run**"), "Click **Run**")

    def test_wrap_tool(self):
        self.assertEqual(i18n.wrap_tool("en", "Pan Map", "Click on the map canvas"),
                         "With the **Pan Map** tool active, click on the map canvas")

    def test_unknown_key_falls_back(self):
        self.assertEqual(i18n.T("xx", "button", name="OK"), "Click **OK**")


class Model(unittest.TestCase):
    def test_events_and_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = model.Session(base_dir=tmp)
            events = []
            s.add_listener(lambda e, st: events.append(e))
            a, b = model.Step("a"), model.Step("b")
            s.add(a)
            s.add(b)
            s.set_order([b, a])
            s.touch(a)
            s.remove(a)
            self.assertEqual(events, ["added", "added", "order", "updated", "removed"])
            self.assertEqual([x.text for x in s.steps], ["b"])

    def test_save_load_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = make_session(os.path.join(tmp, "sess"))
            path = os.path.join(tmp, "out", "t.json")
            os.makedirs(os.path.dirname(path))
            s.save(path)
            data = json.load(open(path, encoding="utf-8"))
            self.assertEqual(data["format"], "qgis-step-recorder")
            self.assertTrue(data["steps"][0]["image"].endswith(".png"))
            loaded = model.Session.load(path)
            self.assertEqual(len(loaded.steps), len(s.steps))
            self.assertTrue(os.path.exists(loaded.steps[0].image))
            self.assertEqual(loaded.steps[3].details, s.steps[3].details)
            self.assertFalse(loaded.steps[6].enabled)

    def test_load_rejects_foreign_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = os.path.join(tmp, "x.json")
            json.dump({"hello": 1}, open(p, "w"))
            with self.assertRaises(ValueError):
                model.Session.load(p)


class Export(unittest.TestCase):
    def test_blocks_grouping(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = make_session(tmp)
            bl = exporter.blocks(s)
            # menu(+dialog opens), field, Run(+algorithm ran), note, Close   (hidden step skipped)
            self.assertEqual([b["type"] for b in bl], ["action", "action", "action", "note", "action"])
            self.assertEqual([b["n"] for b in bl if b["type"] == "action"], [1, 2, 3, 4])
            self.assertEqual(len(bl[0]["results"]), 1)       # dialog opens
            self.assertEqual(len(bl[1]["results"]), 0)
            self.assertEqual(len(bl[2]["results"]), 1)       # algorithm ran
            self.assertNotIn("hidden step", exporter.to_markdown(s))

    def test_markdown(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = make_session(tmp)
            out = os.path.join(tmp, "tut.md")
            exporter.export(s, out, "md")
            md = open(out, encoding="utf-8").read()
            self.assertIn("# Buffer tutorial", md)
            self.assertIn("1. From the menu bar, choose **Vector ▸ Geoprocessing Tools ▸ Buffer…**", md)
            self.assertIn("   - The **Buffer** dialog opens", md)
            self.assertIn("![", md)
            self.assertIn("```python", md)
            self.assertIn("Settings used:", md)
            self.assertTrue(os.path.exists(os.path.join(tmp, "tut_images", "step_001.png")))

    def test_html_embedded(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = make_session(tmp)
            out = os.path.join(tmp, "tut.html")
            exporter.export(s, out, "html", embed_html=True)
            h = open(out, encoding="utf-8").read()
            self.assertIn("data:image/png;base64,", h)
            self.assertIn("<strong>Run</strong>", h)
            self.assertIn("<code>500</code>", h)
            self.assertIn('<div class="num">4</div>', h)
            self.assertNotIn("hidden step", h)

    def test_html_escapes(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = model.Session("<script>alert(1)</script>", base_dir=tmp)
            s.add(model.Step("Type `<b>x</b> & y`"))
            h = exporter.build_html(s)
            self.assertNotIn("<script>alert", h)
            self.assertIn("&lt;b&gt;x&lt;/b&gt; &amp; y", h)

    def test_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            t = exporter.to_text(make_session(tmp))
            self.assertIn("1. From the menu bar, choose Vector", t)
            self.assertIn("   -> The Buffer dialog opens", t)
            self.assertNotIn("**", t)

    def test_arabic_rtl(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = make_session(tmp, "ar")
            h = exporter.build_html(s)
            self.assertIn('dir="rtl"', h)
            self.assertIn("lang=\"ar\"", h)
            self.assertIn("انقر", h)  # "انقر"

    def test_kurdish_sorani_rtl(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = make_session(tmp, "ckb")
            h = exporter.build_html(s)
            self.assertIn('dir="rtl"', h)
            self.assertIn('lang="ckb"', h)
            self.assertIn("\u0647\u06d5\u0646\u06af\u0627\u0648\u06d5\u06a9\u0627\u0646", h)  # heading
            md = exporter.to_markdown(s)
            self.assertIn("\u0644\u06d5 \u0634\u0631\u06cc\u062a\u06cc \u0645\u06ce\u0646\u06cc\u0648\u06d5\u06a9\u0627\u0646", md)
            import re
            self.assertIsNone(re.search(r"\{[a-z_]+\}", md))   # no unfilled placeholders

    def test_menu_open_strings(self):
        for lang in ("en", "ar", "ckb"):
            for key, kw in (("menu_open_bar", {"name": "Vector"}), ("menu_open_sub", {"name": "X"}),
                            ("toolbar_menu", {"name": "A", "toolbar": "B"}),
                            ("toolbar_menu_nobar", {"name": "A"})):
                out = i18n.T(lang, key, **kw)
                self.assertIn(kw["name"], out)
                self.assertNotIn("{", out)

    def test_commands_can_be_hidden(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = make_session(tmp)
            self.assertNotIn("processing.run", exporter.to_markdown(s, include_commands=False))
            self.assertIn("processing.run", exporter.to_markdown(s, include_commands=True))


if __name__ == "__main__":
    unittest.main(verbosity=2)
