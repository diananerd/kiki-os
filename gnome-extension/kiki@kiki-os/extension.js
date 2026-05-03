/**
 * Kiki Shell Bridge — GNOME Shell Extension  v2
 *
 * Exposes Shell / Mutter / Meta internals as DBus service io.kiki.Shell.
 *
 * GNOME 48+ blocks these to external callers:
 *   Eval, FocusSearch, ShowApplications, FocusApp, ShowOSD,
 *   ScreenTransition, and all Meta.Window operations.
 *
 * Methods added in v2 (over v1):
 *   Window management  — WindowList/Focus/Close/Min/Unmin/Max/Unmax/
 *                        Fullscreen/Move/Resize/MoveToWorkspace/SetAbove/Shake
 *   Running apps       — RunningApps
 *   Display            — Monitors
 *   Clipboard          — ClipboardGet (polled cache), ClipboardSet
 *   GSettings          — GSettingsGet, GSettingsSet (Gio.Settings, no subprocess)
 *   Workspace names    — WorkspaceGetName, WorkspaceSetName
 *   Misc               — ShellVersion, ShellMode, IdleTime, OverviewState
 *   Notification       — Notify (MessageTray, OSD fallback)
 *   Screenshot         — Screenshot, ScreenshotArea (async, via Shell.Screenshot)
 */

import GLib    from 'gi://GLib';
import Gio     from 'gi://Gio';
import St      from 'gi://St';
import Shell   from 'gi://Shell';
import Meta    from 'gi://Meta';
import Clutter from 'gi://Clutter';

import * as Main        from 'resource:///org/gnome/shell/ui/main.js';
import * as MessageTray from 'resource:///org/gnome/shell/ui/messageTray.js';
import * as Config      from 'resource:///org/gnome/shell/misc/config.js';
import {Extension}      from 'resource:///org/gnome/shell/extensions/extension.js';

const DBUS_NAME = 'io.kiki.Shell';
const DBUS_PATH = '/io/kiki/Shell';

const DBUS_XML = `
<node>
  <interface name="io.kiki.Shell">

    <!-- ── Core ─────────────────────────────────────────── -->
    <method name="Ping">
      <arg type="s" direction="out" name="pong"/>
    </method>
    <method name="Eval">
      <arg type="s" direction="in"  name="script"/>
      <arg type="s" direction="out" name="result_json"/>
    </method>
    <method name="ShellVersion">
      <arg type="s" direction="out" name="version"/>
    </method>
    <method name="ShellMode">
      <arg type="s" direction="out" name="mode"/>
    </method>
    <method name="IdleTime">
      <arg type="u" direction="out" name="ms"/>
    </method>

    <!-- ── Overview / Search ─────────────────────────────── -->
    <method name="FocusSearch">
      <arg type="s" direction="in" name="query"/>
    </method>
    <method name="ShowApplications"/>
    <method name="OverviewState">
      <arg type="s" direction="out" name="json"/>
    </method>

    <!-- ── App management ────────────────────────────────── -->
    <method name="FocusApp">
      <arg type="s" direction="in"  name="app_id"/>
      <arg type="s" direction="out" name="result"/>
    </method>
    <method name="RunningApps">
      <arg type="s" direction="out" name="json"/>
    </method>

    <!-- ── Window management ─────────────────────────────── -->
    <method name="WindowList">
      <arg type="s" direction="out" name="json"/>
    </method>
    <method name="WindowFocus">
      <arg type="u" direction="in" name="seq"/>
    </method>
    <method name="WindowClose">
      <arg type="u" direction="in" name="seq"/>
    </method>
    <method name="WindowMinimize">
      <arg type="u" direction="in" name="seq"/>
    </method>
    <method name="WindowUnminimize">
      <arg type="u" direction="in" name="seq"/>
    </method>
    <method name="WindowMaximize">
      <arg type="u" direction="in" name="seq"/>
    </method>
    <method name="WindowUnmaximize">
      <arg type="u" direction="in" name="seq"/>
    </method>
    <method name="WindowFullscreen">
      <arg type="u" direction="in" name="seq"/>
      <arg type="b" direction="in" name="on"/>
    </method>
    <method name="WindowMove">
      <arg type="u" direction="in" name="seq"/>
      <arg type="i" direction="in" name="x"/>
      <arg type="i" direction="in" name="y"/>
    </method>
    <method name="WindowResize">
      <arg type="u" direction="in" name="seq"/>
      <arg type="i" direction="in" name="w"/>
      <arg type="i" direction="in" name="h"/>
    </method>
    <method name="WindowMoveToWorkspace">
      <arg type="u" direction="in" name="seq"/>
      <arg type="i" direction="in" name="workspace"/>
    </method>
    <method name="WindowSetAbove">
      <arg type="u" direction="in" name="seq"/>
      <arg type="b" direction="in" name="above"/>
    </method>
    <method name="WindowShake">
      <arg type="u" direction="in" name="seq"/>
    </method>

    <!-- ── Workspaces ─────────────────────────────────────── -->
    <method name="Workspaces">
      <arg type="s" direction="out" name="json"/>
    </method>
    <method name="SwitchWorkspace">
      <arg type="i" direction="in" name="index"/>
    </method>
    <method name="WorkspaceGetName">
      <arg type="i" direction="in"  name="index"/>
      <arg type="s" direction="out" name="name"/>
    </method>
    <method name="WorkspaceSetName">
      <arg type="i" direction="in" name="index"/>
      <arg type="s" direction="in" name="name"/>
    </method>

    <!-- ── Display / Monitors ────────────────────────────── -->
    <method name="Monitors">
      <arg type="s" direction="out" name="json"/>
    </method>

    <!-- ── Clipboard ─────────────────────────────────────── -->
    <method name="ClipboardGet">
      <arg type="s" direction="out" name="text"/>
    </method>
    <method name="ClipboardSet">
      <arg type="s" direction="in" name="text"/>
    </method>

    <!-- ── GSettings (Gio.Settings, no subprocess) ───────── -->
    <method name="GSettingsGet">
      <arg type="s" direction="in"  name="schema"/>
      <arg type="s" direction="in"  name="key"/>
      <arg type="s" direction="out" name="value"/>
    </method>
    <method name="GSettingsSet">
      <arg type="s" direction="in"  name="schema"/>
      <arg type="s" direction="in"  name="key"/>
      <arg type="s" direction="in"  name="value"/>
      <arg type="s" direction="out" name="result"/>
    </method>

    <!-- ── Visual feedback ───────────────────────────────── -->
    <method name="ShowOSD">
      <arg type="s" direction="in" name="text"/>
      <arg type="s" direction="in" name="icon"/>
      <arg type="d" direction="in" name="level"/>
    </method>
    <method name="ScreenTransition"/>
    <method name="Notify">
      <arg type="s" direction="in" name="title"/>
      <arg type="s" direction="in" name="body"/>
      <arg type="s" direction="in" name="icon"/>
    </method>

    <!-- ── Screenshot (async) ────────────────────────────── -->
    <method name="Screenshot">
      <arg type="s" direction="in"  name="path"/>
      <arg type="s" direction="out" name="result_path"/>
    </method>
    <method name="ScreenshotArea">
      <arg type="i" direction="in"  name="x"/>
      <arg type="i" direction="in"  name="y"/>
      <arg type="i" direction="in"  name="w"/>
      <arg type="i" direction="in"  name="h"/>
      <arg type="s" direction="in"  name="path"/>
      <arg type="s" direction="out" name="result_path"/>
    </method>

  </interface>
</node>`;


// ── Helpers ───────────────────────────────────────────────────────────────

function _shellVersion() {
    try { return Config.PACKAGE_VERSION ?? '?'; }
    catch (_) { return '?'; }
}

// Use stable_sequence as window ID — works on both X11 and Wayland.
// get_id() returns XID (0 on Wayland), get_stable_sequence() is always unique.
function _winSeq(win) {
    return win.get_stable_sequence();
}

function _winInfo(win) {
    const r    = win.get_frame_rect();
    const maxF = win.get_maximized();
    let appId  = '';
    try {
        appId = Shell.WindowTracker.get_default().get_window_app(win)?.get_id() ?? '';
    } catch (_) {}
    return {
        id:        _winSeq(win),
        title:     win.get_title() ?? '',
        app:       appId,
        pid:       win.get_pid(),
        workspace: win.get_workspace()?.index() ?? -1,
        x: r.x, y: r.y, w: r.width, h: r.height,
        state: {
            active:     win.has_focus(),
            minimized:  win.minimized,
            maximized:  !!(maxF & Meta.MaximizeFlags.BOTH),
            max_h:      !!(maxF & Meta.MaximizeFlags.HORIZONTAL),
            max_v:      !!(maxF & Meta.MaximizeFlags.VERTICAL),
            fullscreen: win.is_fullscreen(),
            above:      win.is_above(),
        },
    };
}

function _findWin(seq) {
    for (const actor of global.get_window_actors()) {
        const win = actor.meta_window;
        if (win && _winSeq(win) === seq) return win;
    }
    return null;
}

function _findActor(seq) {
    for (const actor of global.get_window_actors()) {
        if (actor.meta_window && _winSeq(actor.meta_window) === seq) return actor;
    }
    return null;
}

function _gsSettings(schema) {
    return new Gio.Settings({ schema_id: schema });
}

function _gvariantFromString(currentVariant, value) {
    const t = currentVariant.get_type_string();
    if (t === 's')   return GLib.Variant.new_string(value);
    if (t === 'b')   return GLib.Variant.new_boolean(value === 'true' || value === '1');
    if (t === 'i')   return GLib.Variant.new_int32(parseInt(value, 10));
    if (t === 'u')   return GLib.Variant.new_uint32(parseInt(value, 10));
    if (t === 'x')   return GLib.Variant.new_int64(parseInt(value, 10));
    if (t === 'd')   return GLib.Variant.new_double(parseFloat(value));
    if (t === 'as')  return new GLib.Variant('as', JSON.parse(value));
    if (t === 'ai')  return new GLib.Variant('ai', JSON.parse(value));
    // Fallback: GVariant text format (e.g. "'dark'" for strings, "true" for bools)
    return GLib.Variant.parse(null, value, null, null);
}


// ── Implementation ────────────────────────────────────────────────────────

class KikiImpl {
    constructor() {
        this._clipText  = '';
        this._clipTimer = 0;
    }

    // ── Core ──────────────────────────────────────────────────────────

    Ping() {
        return `kiki-shell-bridge v2 gnome-${_shellVersion()}`;
    }

    ShellVersion() {
        return _shellVersion();
    }

    ShellMode() {
        try { return Main.sessionMode.currentMode; }
        catch (_) { return 'user'; }
    }

    IdleTime() {
        try { return global.backend.get_core_idle_monitor().get_idletime(); }
        catch (_) { return 0; }
    }

    Eval(script) {
        try {
            const fn = new Function(
                'Main', 'Shell', 'Gio', 'GLib', 'Meta', 'Clutter', 'St', 'global',
                `return (() => { ${script} })()`
            );
            const r = fn(Main, Shell, Gio, GLib, Meta, Clutter, St, global);
            return JSON.stringify({ ok: true, result: String(r ?? 'ok') });
        } catch (e) {
            return JSON.stringify({ ok: false, error: String(e) });
        }
    }

    // ── Overview / Search ─────────────────────────────────────────────

    FocusSearch(query) {
        Main.overview.show();
        if (query && query.length > 0) {
            GLib.timeout_add(GLib.PRIORITY_DEFAULT, 200, () => {
                try {
                    const entry = Main.overview.searchEntry
                        ?? Main.overview._overview?.controls?._searchEntry;
                    if (entry) { entry.set_text(query); entry.grab_key_focus(); }
                } catch (_) {}
                return GLib.SOURCE_REMOVE;
            });
        }
    }

    ShowApplications() {
        if (typeof Main.overview.showApps === 'function') {
            Main.overview.showApps();
        } else {
            Main.overview.show();
            GLib.timeout_add(GLib.PRIORITY_DEFAULT, 150, () => {
                try {
                    const btn = Main.overview._overview?.controls?._showAppsButton;
                    if (btn) btn.checked = true;
                } catch (_) {}
                return GLib.SOURCE_REMOVE;
            });
        }
    }

    OverviewState() {
        try {
            const ov       = Main.overview;
            const controls = ov._overview?.controls;
            return JSON.stringify({
                visible: ov.visible,
                view:    controls?._showAppsButton?.checked ? 'apps' : 'overview',
            });
        } catch (_) {
            return JSON.stringify({ visible: false, view: 'unknown' });
        }
    }

    // ── App management ────────────────────────────────────────────────

    FocusApp(appId) {
        if (!appId.endsWith('.desktop')) appId += '.desktop';
        const app = Shell.AppSystem.get_default().lookup_app(appId);
        if (app) { app.activate(); return `activated: ${appId}`; }
        return `not found: ${appId}`;
    }

    RunningApps() {
        try {
            const apps = Shell.AppSystem.get_default().get_running();
            return JSON.stringify(apps.map(app => ({
                id:      app.get_id(),
                name:    app.get_name(),
                windows: app.get_windows().length,
                state:   String(app.state),
            })));
        } catch (e) {
            return JSON.stringify([]);
        }
    }

    // ── Window management ─────────────────────────────────────────────

    WindowList() {
        try {
            const wins = global.get_window_actors()
                .map(a => a.meta_window)
                .filter(w => {
                    if (!w) return false;
                    const t = w.get_window_type();
                    return (t === Meta.WindowType.NORMAL
                         || t === Meta.WindowType.DIALOG
                         || t === Meta.WindowType.MODAL_DIALOG);
                })
                .map(w => _winInfo(w));
            return JSON.stringify(wins);
        } catch (e) {
            return JSON.stringify([]);
        }
    }

    WindowFocus(seq) {
        _findWin(seq)?.activate(global.get_current_time());
    }

    WindowClose(seq) {
        _findWin(seq)?.delete(global.get_current_time());
    }

    WindowMinimize(seq) {
        _findWin(seq)?.minimize();
    }

    WindowUnminimize(seq) {
        _findWin(seq)?.unminimize();
    }

    WindowMaximize(seq) {
        _findWin(seq)?.maximize(Meta.MaximizeFlags.BOTH);
    }

    WindowUnmaximize(seq) {
        _findWin(seq)?.unmaximize(Meta.MaximizeFlags.BOTH);
    }

    WindowFullscreen(seq, on) {
        const win = _findWin(seq);
        if (!win) return;
        if (on) win.make_fullscreen();
        else    win.unmake_fullscreen();
    }

    WindowMove(seq, x, y) {
        _findWin(seq)?.move_frame(true, x, y);
    }

    WindowResize(seq, w, h) {
        const win = _findWin(seq);
        if (!win) return;
        const r = win.get_frame_rect();
        win.move_resize_frame(true, r.x, r.y, w, h);
    }

    WindowMoveToWorkspace(seq, wsIndex) {
        const win = _findWin(seq);
        if (!win) return;
        const ws = global.workspace_manager.get_workspace_by_index(wsIndex);
        if (ws) win.change_workspace(ws);
    }

    WindowSetAbove(seq, above) {
        const win = _findWin(seq);
        if (!win) return;
        if (above) win.make_above();
        else       win.unmake_above();
    }

    WindowShake(seq) {
        const actor = _findActor(seq);
        if (!actor) return;
        const ox = actor.x;
        const d  = 10;
        const ms = 55;
        actor.ease({ x: ox - d, duration: ms, onComplete: () =>
            actor.ease({ x: ox + d, duration: ms, onComplete: () =>
                actor.ease({ x: ox - d / 2, duration: ms, onComplete: () =>
                    actor.ease({ x: ox, duration: ms })
                })
            })
        });
    }

    // ── Workspaces ────────────────────────────────────────────────────

    Workspaces() {
        const wm     = global.workspace_manager;
        const count  = wm.get_n_workspaces();
        const active = wm.get_active_workspace_index();
        const ws = [];
        for (let i = 0; i < count; i++)
            ws.push({ index: i, active: i === active, name: this.WorkspaceGetName(i) });
        return JSON.stringify({ count, active, workspaces: ws });
    }

    SwitchWorkspace(index) {
        global.workspace_manager.get_workspace_by_index(index)
            ?.activate(global.get_current_time());
    }

    WorkspaceGetName(index) {
        try {
            const names = _gsSettings('org.gnome.desktop.wm.preferences')
                .get_strv('workspace-names');
            return names[index] || `Workspace ${index + 1}`;
        } catch (_) {
            return `Workspace ${index + 1}`;
        }
    }

    WorkspaceSetName(index, name) {
        try {
            const s     = _gsSettings('org.gnome.desktop.wm.preferences');
            const names = s.get_strv('workspace-names');
            while (names.length <= index) names.push('');
            names[index] = name;
            s.set_strv('workspace-names', names);
        } catch (_) {}
    }

    // ── Display / Monitors ────────────────────────────────────────────

    Monitors() {
        try {
            const d  = global.display;
            const n  = d.get_n_monitors();
            const ms = [];
            for (let i = 0; i < n; i++) {
                const r = d.get_monitor_geometry(i);
                ms.push({
                    index:   i,
                    primary: d.get_primary_monitor() === i,
                    x: r.x, y: r.y, w: r.width, h: r.height,
                    scale:   d.get_monitor_scale(i),
                });
            }
            return JSON.stringify(ms);
        } catch (e) {
            return JSON.stringify([]);
        }
    }

    // ── Clipboard ─────────────────────────────────────────────────────

    ClipboardGet() {
        // Returns value from 500ms polling cache — see startClipboardPolling()
        return this._clipText;
    }

    ClipboardSet(text) {
        try {
            St.Clipboard.get_default().set_text(St.ClipboardType.CLIPBOARD, text);
            this._clipText = text;
        } catch (_) {}
    }

    _refreshClipboard() {
        try {
            St.Clipboard.get_default().get_text(
                St.ClipboardType.CLIPBOARD,
                (_cb, text) => { this._clipText = text ?? ''; }
            );
        } catch (_) {}
    }

    startClipboardPolling() {
        this._refreshClipboard();
        this._clipTimer = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 500, () => {
            this._refreshClipboard();
            return GLib.SOURCE_CONTINUE;
        });
    }

    stopClipboardPolling() {
        if (this._clipTimer) {
            GLib.source_remove(this._clipTimer);
            this._clipTimer = 0;
        }
    }

    // ── GSettings (Gio.Settings — no subprocess) ──────────────────────

    GSettingsGet(schema, key) {
        try {
            const v = _gsSettings(schema).get_value(key);
            return v.print(true);
        } catch (e) {
            return `error: ${e}`;
        }
    }

    GSettingsSet(schema, key, value) {
        try {
            const s       = _gsSettings(schema);
            const current = s.get_value(key);
            s.set_value(key, _gvariantFromString(current, value));
            return 'ok';
        } catch (e) {
            return `error: ${e}`;
        }
    }

    // ── Visual feedback ───────────────────────────────────────────────

    ShowOSD(text, icon, level) {
        let iconObj = null;
        try { iconObj = Gio.icon_new_for_string(icon || 'dialog-information'); } catch (_) {}
        Main.osdWindowManager.show(-1, iconObj, text, level >= 0 ? level / 100.0 : -1);
    }

    ScreenTransition() {
        try {
            const stage = global.stage;
            stage.ease({
                opacity: 0, duration: 200, mode: Clutter.AnimationMode.EASE_OUT_QUAD,
                onComplete: () => stage.ease({
                    opacity: 255, duration: 300, mode: Clutter.AnimationMode.EASE_IN_QUAD,
                }),
            });
        } catch (e) {
            console.warn('[kiki] ScreenTransition:', e);
        }
    }

    Notify(title, body, icon) {
        try {
            let source;
            if (typeof MessageTray.getSystemSource === 'function') {
                // GNOME 48+
                source = MessageTray.getSystemSource();
            } else {
                source = new MessageTray.Source({
                    title:    'Kiki',
                    iconName: icon || 'dialog-information',
                });
                Main.messageTray.add(source);
            }
            const n = new MessageTray.Notification({
                source,
                title,
                body,
                ...(icon ? { gicon: Gio.icon_new_for_string(icon) } : {}),
            });
            source.addNotification(n);
        } catch (e) {
            console.warn('[kiki] Notify fallback:', e);
            this.ShowOSD(`${title}${body ? ': ' + body : ''}`,
                         icon || 'dialog-information', -1);
        }
    }

    // ── Screenshot (async via Shell.Screenshot) ───────────────────────
    //
    // GJS promisifies Shell.Screenshot methods in GNOME 48+ — use async/await.
    // wrapJSObject awaits the returned Promise and auto-replies with the value.

    async Screenshot(path) {
        const file   = Gio.File.new_for_path(path);
        const stream = file.replace(null, false, Gio.FileCreateFlags.NONE, null);
        const ss     = new Shell.Screenshot();
        await ss.screenshot(true, stream);
        stream.close(null);
        return path;
    }

    async ScreenshotArea(x, y, w, h, path) {
        const file   = Gio.File.new_for_path(path);
        const stream = file.replace(null, false, Gio.FileCreateFlags.NONE, null);
        const ss     = new Shell.Screenshot();
        await ss.screenshot_area(x, y, w, h, stream);
        stream.close(null);
        return path;
    }
}


// ── Extension lifecycle ───────────────────────────────────────────────────

export default class KikiExtension extends Extension {
    constructor(metadata) {
        super(metadata);
        this._impl   = null;
        this._dbus   = null;
        this._nameId = 0;
    }

    enable() {
        this._impl = new KikiImpl();
        this._dbus = Gio.DBusExportedObject.wrapJSObject(DBUS_XML, this._impl);
        this._dbus.export(Gio.DBus.session, DBUS_PATH);

        this._nameId = Gio.bus_own_name(
            Gio.BusType.SESSION,
            DBUS_NAME,
            Gio.BusNameOwnerFlags.NONE,
            null, null, null
        );

        this._impl.startClipboardPolling();

        console.log(`[kiki] Shell Bridge v2 active — ${DBUS_NAME} @ ${DBUS_PATH}`);
    }

    disable() {
        this._impl?.stopClipboardPolling();

        if (this._nameId) {
            Gio.bus_unown_name(this._nameId);
            this._nameId = 0;
        }
        if (this._dbus) {
            this._dbus.unexport();
            this._dbus = null;
        }
        this._impl = null;
    }
}
