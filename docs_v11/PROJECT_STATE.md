# Состояние проекта (v11)
Python/Tkinter/Pillow, локальный llama.cpp.
Модули: main.py (UI), world.py (мир, Duel), core.py (время, каста, события, цены, журнал, статистика), story_data.py + story10.py (92 сцены), lore.py (что знает NPC), meta.py (слоты, настройки, достижения), menu.py (меню), uikit.py (EventWindow, QuickGame, MapView, Tutorial), fight.py (движок боя), fightui.py (окно боя), sound.py, ai.py, runtime_manager.py.
Сохранения: saves/autosave.json (+.bak), slot1-3.json, legacy town_v4.json. Настройки: settings.json, достижения: achievements.json.
Состояние игры: world.s; новые данные в s['core'] (flags, done, timers, weak, ousted, counters, inv, stash).
