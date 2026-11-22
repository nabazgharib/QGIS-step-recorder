# -*- coding: utf-8 -*-
"""Instruction templates (English / Arabic).

Pure Python - no Qt/QGIS imports, so it can be unit-tested anywhere.

Markup used inside generated text:
    **name**   a user-interface element (menu, button, field, layer ...)
    `value`    a value the user typed or chose
"""

LANGUAGES = {"en": "English", "ar": "العربية", "ckb": "کوردی (سۆرانی)"}
RTL_LANGUAGES = {"ar", "ckb"}

TEMPLATES = {
    "en": {
        # menus / buttons
        "menu_bar": "From the menu bar, choose **{path}**",
        "menu_ctx": "From the menu, choose **{path}**",
        "menu_check_on": "In the menu, check **{path}**",
        "menu_check_off": "In the menu, uncheck **{path}**",
        "toolbar_btn": "Click the **{name}** button in the **{toolbar}** toolbar",
        "toolbar_btn_nobar": "Click the **{name}** button",
        "button": "Click **{name}**",
        "dots_btn": "Click the **{name}** button next to **{label}**",
        "collapse": "Collapse the **{name}** section",
        "expand": "Expand the **{name}** section",
        # fields
        "check": "Check **{label}**",
        "uncheck": "Uncheck **{label}**",
        "radio": "Select the **{label}** option",
        "tab": "Open the **{name}** tab",
        "combo": "Select `{value}` in the **{label}** list",
        "text": "In the **{label}** field, type `{value}`",
        "text_secret": "In the **{label}** field, type your password",
        "text_block": "In the **{label}** box, enter the following text",
        "set_value": "Set **{label}** to `{value}`",
        "color": "Set the colour of **{label}** to `{value}`",
        "no_label": "this field",
        # item views
        "item_click": "Click **{item}**",
        "item_dbl": "Double-click **{item}**",
        "item_right": "Right-click **{item}**",
        "header_click": "Click the **{name}** column header",
        # map canvas
        "where": " at {coords}",
        "map_click": "Click on the map canvas{where}",
        "map_click_n": "Click {n} times on the map canvas",
        "map_rclick": "Right-click on the map canvas{where}",
        "map_drag": "Click and drag on the map canvas{where}",
        "map_drag_pan": "Click and drag on the map canvas to pan the map",
        "wheel_in": "Scroll the mouse wheel up over the map canvas to zoom in",
        "wheel_out": "Scroll the mouse wheel down over the map canvas to zoom out",
        "tool_prefix": "With the **{tool}** tool active, {action}",
        # keyboard
        "shortcut": "Press **{keys}**",
        "shortcut_named": "Press **{keys}** ({name})",
        # context wrappers
        "ctx_dialog": "In the **{ctx}** dialog, {action}",
        "ctx_panel": "In the **{ctx}** panel, {action}",
        # observations
        "dialog_open": "The **{title}** dialog opens",
        "msgbox": "A message box appears: “{text}”",
        "msgbar": "The message bar shows a {level} message: “{text}”",
        "lvl_Info": "information",
        "lvl_Warning": "warning",
        "lvl_Critical": "error",
        "lvl_Success": "success",
        "layer_added": "The layer **{name}** is added to the project",
        "layers_added": "{n} layers are added to the project: {names}",
        "layer_removed": "The layer **{name}** is removed from the project",
        "layers_removed": "{n} layers are removed from the project: {names}",
        "edit_on": "The layer **{name}** is now in edit mode",
        "edit_off": "Editing of the layer **{name}** is stopped",
        "selected": "{n} feature(s) selected in **{name}**",
        "sel_cleared": "The selection in **{name}** is cleared",
        "proc_done": "The algorithm **{name}** has run",
        "py_run": "Run the algorithm **{name}** from the Python Console",
        "menu_open_bar": "Click the **{name}** menu in the menu bar",
        "menu_open_sub": "The **{name}** submenu opens",
        "toolbar_menu": "Click the **{name}** button in the **{toolbar}** toolbar to open its list",
        "toolbar_menu_nobar": "Click the **{name}** button to open its list",
        "menu_context": "A context menu appears",
        "menu_popup": "A menu appears",
        "proj_saved": "The project is saved{where}",
        "proj_new": "A new project is created",
        "proj_read": "The project **{name}** is opened",
        "crs_changed": "The project CRS is now `{value}`",
        # misc / export
        "val_on": "checked",
        "val_off": "unchecked",
        "val_sel": "selected",
        "summary_title": "Settings used:",
        "steps_heading": "Steps",
        "generated": "Created with Step Recorder for QGIS",
        "untitled": "Untitled tutorial",
        "cmd_heading": "Python command",
    },
    "ar": {
        "menu_bar": "من شريط القوائم، اختر **{path}**",
        "menu_ctx": "من القائمة، اختر **{path}**",
        "menu_check_on": "في القائمة، فعّل **{path}**",
        "menu_check_off": "في القائمة، ألغِ تفعيل **{path}**",
        "toolbar_btn": "انقر على الزر **{name}** في شريط الأدوات **{toolbar}**",
        "toolbar_btn_nobar": "انقر على الزر **{name}**",
        "button": "انقر على **{name}**",
        "dots_btn": "انقر على الزر **{name}** بجانب **{label}**",
        "collapse": "اطوِ القسم **{name}**",
        "expand": "وسّع القسم **{name}**",
        "check": "فعّل الخيار **{label}**",
        "uncheck": "ألغِ تفعيل الخيار **{label}**",
        "radio": "اختر الخيار **{label}**",
        "tab": "افتح تبويب **{name}**",
        "combo": "اختر `{value}` من قائمة **{label}**",
        "text": "في الحقل **{label}** اكتب `{value}`",
        "text_secret": "في الحقل **{label}** اكتب كلمة المرور",
        "text_block": "في الصندوق **{label}** أدخل النص التالي",
        "set_value": "اضبط **{label}** على `{value}`",
        "color": "اضبط لون **{label}** إلى `{value}`",
        "no_label": "هذا الحقل",
        "item_click": "انقر على **{item}**",
        "item_dbl": "انقر نقراً مزدوجاً على **{item}**",
        "item_right": "انقر بزر الفأرة الأيمن على **{item}**",
        "header_click": "انقر على عنوان العمود **{name}**",
        "where": " عند {coords}",
        "map_click": "انقر على لوحة الخريطة{where}",
        "map_click_n": "انقر {n} مرات على لوحة الخريطة",
        "map_rclick": "انقر بزر الفأرة الأيمن على لوحة الخريطة{where}",
        "map_drag": "اسحب بالفأرة على لوحة الخريطة{where}",
        "map_drag_pan": "اسحب بالفأرة على لوحة الخريطة لتحريك الخريطة",
        "wheel_in": "حرّك عجلة الفأرة للأعلى فوق لوحة الخريطة للتكبير",
        "wheel_out": "حرّك عجلة الفأرة للأسفل فوق لوحة الخريطة للتصغير",
        "tool_prefix": "أثناء تفعيل أداة **{tool}**، {action}",
        "shortcut": "اضغط على **{keys}**",
        "shortcut_named": "اضغط على **{keys}** ({name})",
        "ctx_dialog": "في نافذة **{ctx}**، {action}",
        "ctx_panel": "في لوحة **{ctx}**، {action}",
        "dialog_open": "تفتح نافذة **{title}**",
        "msgbox": "تظهر رسالة: «{text}»",
        "msgbar": "يعرض شريط الرسائل ({level}): «{text}»",
        "lvl_Info": "معلومة",
        "lvl_Warning": "تحذير",
        "lvl_Critical": "خطأ",
        "lvl_Success": "نجاح",
        "layer_added": "تتم إضافة الطبقة **{name}** إلى المشروع",
        "layers_added": "تتم إضافة {n} طبقات إلى المشروع: {names}",
        "layer_removed": "تتم إزالة الطبقة **{name}** من المشروع",
        "layers_removed": "تتم إزالة {n} طبقات من المشروع: {names}",
        "edit_on": "أصبحت الطبقة **{name}** في وضع التحرير",
        "edit_off": "يتوقف تحرير الطبقة **{name}**",
        "selected": "تم تحديد {n} عنصر في **{name}**",
        "sel_cleared": "تم مسح التحديد في **{name}**",
        "proc_done": "تم تشغيل الخوارزمية **{name}**",
        "py_run": "شغّل الخوارزمية **{name}** من وحدة تحكم بايثون",
        "menu_open_bar": "انقر على القائمة **{name}** في شريط القوائم",
        "menu_open_sub": "تفتح القائمة الفرعية **{name}**",
        "toolbar_menu": "انقر على الزر **{name}** في شريط الأدوات **{toolbar}** لفتح قائمته",
        "toolbar_menu_nobar": "انقر على الزر **{name}** لفتح قائمته",
        "menu_context": "تظهر قائمة سياقية",
        "menu_popup": "تظهر قائمة",
        "proj_saved": "يتم حفظ المشروع{where}",
        "proj_new": "يتم إنشاء مشروع جديد",
        "proj_read": "يتم فتح المشروع **{name}**",
        "crs_changed": "أصبح نظام إحداثيات المشروع `{value}`",
        "val_on": "مفعّل",
        "val_off": "غير مفعّل",
        "val_sel": "محدد",
        "summary_title": "الإعدادات المستخدمة:",
        "steps_heading": "الخطوات",
        "generated": "تم الإنشاء بواسطة Step Recorder لبرنامج QGIS",
        "untitled": "درس بدون عنوان",
        "cmd_heading": "أمر بايثون",
    },
    "ckb": {
        # مێنیو و دوگمەکان
        "menu_bar": "لە شریتی مێنیوەکان، **{path}** هەڵبژێرە",
        "menu_ctx": "لە مێنیوەکە، **{path}** هەڵبژێرە",
        "menu_check_on": "لە مێنیوەکە، **{path}** چالاک بکە",
        "menu_check_off": "لە مێنیوەکە، **{path}** ناچالاک بکە",
        "toolbar_btn": "کلیک لە دوگمەی **{name}** بکە لە شریتی ئامرازی **{toolbar}**",
        "toolbar_btn_nobar": "کلیک لە دوگمەی **{name}** بکە",
        "button": "کلیک لە **{name}** بکە",
        "dots_btn": "کلیک لە دوگمەی **{name}** بکە لە تەنیشت **{label}**",
        "collapse": "بەشی **{name}** بپێچەوە",
        "expand": "بەشی **{name}** بکەرەوە",
        # خانەکان
        "check": "هەڵبژاردەی **{label}** چالاک بکە",
        "uncheck": "هەڵبژاردەی **{label}** ناچالاک بکە",
        "radio": "هەڵبژاردەی **{label}** دیاری بکە",
        "tab": "تابی **{name}** بکەرەوە",
        "combo": "`{value}` هەڵبژێرە لە لیستی **{label}**",
        "text": "لە خانەی **{label}** بنووسە `{value}`",
        "text_secret": "لە خانەی **{label}** وشەی نهێنی بنووسە",
        "text_block": "لە بۆکسی **{label}** ئەم دەقە بنووسە",
        "set_value": "**{label}** بکە بە `{value}`",
        "color": "ڕەنگی **{label}** بکە بە `{value}`",
        "no_label": "ئەم خانەیە",
        "item_click": "کلیک لە **{item}** بکە",
        "item_dbl": "دوو جار کلیک لە **{item}** بکە",
        "item_right": "کلیکی ڕاست لە **{item}** بکە",
        "header_click": "کلیک لە ناونیشانی ستوونی **{name}** بکە",
        # نەخشە
        "where": " لە {coords}",
        "map_click": "کلیک لەسەر نەخشەکە بکە{where}",
        "map_click_n": "{n} جار کلیک لەسەر نەخشەکە بکە",
        "map_rclick": "کلیکی ڕاست لەسەر نەخشەکە بکە{where}",
        "map_drag": "کلیک بکە و ڕایبکێشە لەسەر نەخشەکە{where}",
        "map_drag_pan": "کلیک بکە و ڕایبکێشە لەسەر نەخشەکە بۆ جوڵاندنی نەخشەکە",
        "wheel_in": "چەرخی ماوس بەرەو سەرەوە بسوڕێنە لەسەر نەخشەکە بۆ گەورەکردن",
        "wheel_out": "چەرخی ماوس بەرەو خوارەوە بسوڕێنە لەسەر نەخشەکە بۆ بچووککردن",
        "tool_prefix": "لەکاتی چالاکبوونی ئامرازی **{tool}**، {action}",
        "shortcut": "**{keys}** دابگرە",
        "shortcut_named": "**{keys}** دابگرە ({name})",
        "ctx_dialog": "لە پەنجەرەی **{ctx}**، {action}",
        "ctx_panel": "لە پانێڵی **{ctx}**، {action}",
        # ئەنجامەکان
        "dialog_open": "پەنجەرەی **{title}** دەکرێتەوە",
        "msgbox": "پەیامێک دەردەکەوێت: \u00ab{text}\u00bb",
        "msgbar": "شریتی پەیام پەیامێکی ({level}) پیشان دەدات: \u00ab{text}\u00bb",
        "lvl_Info": "زانیاری",
        "lvl_Warning": "ئاگاداری",
        "lvl_Critical": "هەڵە",
        "lvl_Success": "سەرکەوتوو",
        "layer_added": "چینی **{name}** زیاد دەکرێت بۆ پڕۆژەکە",
        "layers_added": "{n} چین زیاد دەکرێن بۆ پڕۆژەکە: {names}",
        "layer_removed": "چینی **{name}** لە پڕۆژەکە لادەبرێت",
        "layers_removed": "{n} چین لە پڕۆژەکە لادەبرێن: {names}",
        "edit_on": "چینی **{name}** ئێستا لە دۆخی دەستکاریکردنە",
        "edit_off": "دەستکاریکردنی چینی **{name}** ڕادەوەستێت",
        "selected": "{n} فیچەر دیاریکرا لە **{name}**",
        "sel_cleared": "دیاریکراوەکان لە **{name}** سڕدرانەوە",
        "proc_done": "ئەلگۆریتمی **{name}** کار پێکرا",
        "py_run": "ئەلگۆریتمی **{name}** لە کۆنسۆڵی پایثۆن کار پێبکە",
        "menu_open_bar": "کلیک لە مێنیوی **{name}** بکە لە شریتی مێنیوەکان",
        "menu_open_sub": "مێنیوی لاوەکیی **{name}** دەکرێتەوە",
        "toolbar_menu": "کلیک لە دوگمەی **{name}** بکە لە شریتی ئامرازی **{toolbar}** بۆ کردنەوەی لیستەکەی",
        "toolbar_menu_nobar": "کلیک لە دوگمەی **{name}** بکە بۆ کردنەوەی لیستەکەی",
        "menu_context": "مێنیویەکی ناوەڕۆک دەردەکەوێت",
        "menu_popup": "مێنیویەک دەردەکەوێت",
        "proj_saved": "پڕۆژەکە پاشەکەوت دەکرێت{where}",
        "proj_new": "پڕۆژەیەکی نوێ دروست دەکرێت",
        "proj_read": "پڕۆژەی **{name}** دەکرێتەوە",
        "crs_changed": "CRS ی پڕۆژەکە ئێستا `{value}` ـە",
        "val_on": "چالاک",
        "val_off": "ناچالاک",
        "val_sel": "دیاریکراو",
        "summary_title": "ڕێکخستنە بەکارهێنراوەکان:",
        "steps_heading": "هەنگاوەکان",
        "generated": "دروستکراوە بە Step Recorder بۆ QGIS",
        "untitled": "وانەی بێ ناونیشان",
        "cmd_heading": "فەرمانی پایثۆن",
    },
}


def is_rtl(lang):
    return lang in RTL_LANGUAGES


def T(lang, key, **kw):  # noqa: N802
    """Return the template *key* for *lang* (falls back to English)."""
    table = TEMPLATES.get(lang) or TEMPLATES["en"]
    tpl = table.get(key)
    if tpl is None:
        tpl = TEMPLATES["en"].get(key, key)
    try:
        return tpl.format(**kw)
    except (KeyError, IndexError):
        return tpl


def _lower_first(text):
    """Lower-case the first letter unless it starts a UI name (**...**)."""
    if not text or text.startswith("**") or text.startswith("`"):
        return text
    return text[0].lower() + text[1:]


def wrap_context(lang, ctx, action):
    """Prefix *action* with its dialog/panel context.

    ctx is ``None`` or a ``(kind, title)`` tuple where kind is 'dialog'/'panel'.
    """
    if not ctx or not ctx[1]:
        return action
    kind, title = ctx
    key = "ctx_panel" if kind == "panel" else "ctx_dialog"
    if lang == "en":
        action = _lower_first(action)
    return T(lang, key, ctx=title, action=action)


def wrap_tool(lang, tool, action):
    if not tool:
        return action
    if lang == "en":
        action = _lower_first(action)
    return T(lang, "tool_prefix", tool=tool, action=action)
