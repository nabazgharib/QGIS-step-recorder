# -*- coding: utf-8 -*-
"""Data model: Step and Session (pure Python, no Qt)."""
import json
import os
import shutil
import tempfile
import time
import uuid

from .textutils import strip_markup

ROLE_ACTION = "action"   # something the reader must do  (numbered)
ROLE_RESULT = "result"   # something that happens         (sub-bullet)
ROLE_NOTE = "note"       # free text / extra screenshot   (paragraph)
ROLES = (ROLE_ACTION, ROLE_RESULT, ROLE_NOTE)


class Step(object):
    def __init__(self, text, role=ROLE_ACTION, kind="manual", image="",
                 details=None, command="", command_lang="python",
                 enabled=True, uid=None, ts=None, merge_key=None, count=1):
        self.uid = uid or uuid.uuid4().hex[:12]
        self.text = text
        self.role = role if role in ROLES else ROLE_ACTION
        self.kind = kind
        self.image = image or ""            # absolute path of a PNG, or ""
        self.details = list(details or [])  # extra bullet lines
        self.command = command or ""        # code block shown under the step
        self.command_lang = command_lang
        self.enabled = bool(enabled)
        self.ts = ts or time.time()
        self.merge_key = merge_key          # runtime only (not saved)
        self.count = count                  # runtime only

    def plain(self):
        return strip_markup(self.text)

    def to_dict(self, image_ref=None):
        return {
            "uid": self.uid,
            "text": self.text,
            "role": self.role,
            "kind": self.kind,
            "image": image_ref if image_ref is not None else self.image,
            "details": self.details,
            "command": self.command,
            "command_lang": self.command_lang,
            "enabled": self.enabled,
            "ts": self.ts,
        }

    @classmethod
    def from_dict(cls, d, base_dir=""):
        img = d.get("image") or ""
        if img and base_dir and not os.path.isabs(img):
            img = os.path.join(base_dir, img)
        return cls(
            d.get("text", ""), d.get("role", ROLE_ACTION), d.get("kind", "manual"),
            img, d.get("details"), d.get("command", ""),
            d.get("command_lang", "python"), d.get("enabled", True),
            d.get("uid"), d.get("ts"),
        )


class Session(object):
    """An ordered list of steps plus tutorial metadata."""

    def __init__(self, title="", author="", description="", lang="en", base_dir=None):
        self.title = title
        self.author = author
        self.description = description
        self.lang = lang
        self.steps = []
        self._listeners = []
        self.base_dir = base_dir or tempfile.mkdtemp(prefix="step_recorder_")
        os.makedirs(self.base_dir, exist_ok=True)

    # ---- observers -------------------------------------------------
    def add_listener(self, fn):
        """fn(event, step) with event in 'added','updated','removed','reset','order'."""
        self._listeners.append(fn)

    def remove_listener(self, fn):
        if fn in self._listeners:
            self._listeners.remove(fn)

    def _fire(self, event, step=None):
        for fn in list(self._listeners):
            try:
                fn(event, step)
            except Exception:  # a broken view must never break recording
                pass

    # ---- editing ---------------------------------------------------
    def new_image_path(self):
        os.makedirs(self.base_dir, exist_ok=True)
        return os.path.join(self.base_dir, "shot_%s.png" % uuid.uuid4().hex[:8])

    def add(self, step, index=None):
        if index is None or index >= len(self.steps):
            self.steps.append(step)
        else:
            self.steps.insert(max(0, index), step)
        self._fire("added", step)
        return step

    def touch(self, step):
        self._fire("updated", step)

    def remove(self, step):
        if step in self.steps:
            self.steps.remove(step)
            self._fire("removed", step)

    def set_order(self, steps):
        known = {s.uid: s for s in self.steps}
        new = [known[s.uid] for s in steps if s.uid in known]
        if len(new) == len(self.steps):
            self.steps = new
            self._fire("order", None)

    def clear(self, delete_images=True):
        if delete_images:
            for s in self.steps:
                self._delete_image(s)
        self.steps = []
        self._fire("reset", None)

    def _delete_image(self, step):
        try:
            if step.image and os.path.dirname(os.path.abspath(step.image)) == os.path.abspath(self.base_dir):
                os.remove(step.image)
        except OSError:
            pass

    def last(self):
        return self.steps[-1] if self.steps else None

    def enabled_steps(self):
        return [s for s in self.steps if s.enabled]

    def action_count(self):
        return sum(1 for s in self.steps if s.enabled and s.role == ROLE_ACTION)

    # ---- persistence ----------------------------------------------
    def to_dict(self, image_refs=None):
        image_refs = image_refs or {}
        return {
            "format": "qgis-step-recorder",
            "version": 1,
            "title": self.title,
            "author": self.author,
            "description": self.description,
            "lang": self.lang,
            "steps": [s.to_dict(image_refs.get(s.uid)) for s in self.steps],
        }

    def save(self, path):
        """Save to JSON; screenshots are copied to '<name>_files/' next to it."""
        stem = os.path.splitext(path)[0]
        folder = stem + "_files"
        refs = {}
        for s in self.steps:
            if s.image and os.path.exists(s.image):
                os.makedirs(folder, exist_ok=True)
                name = os.path.basename(s.image)
                shutil.copy2(s.image, os.path.join(folder, name))
                refs[s.uid] = "%s/%s" % (os.path.basename(folder), name)
            else:
                refs[s.uid] = ""
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(self.to_dict(refs), fh, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, path):
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if data.get("format") != "qgis-step-recorder":
            raise ValueError("Not a Step Recorder file")
        sess = cls(data.get("title", ""), data.get("author", ""),
                   data.get("description", ""), data.get("lang", "en"))
        base = os.path.dirname(os.path.abspath(path))
        for d in data.get("steps", []):
            sess.steps.append(Step.from_dict(d, base))
        return sess
