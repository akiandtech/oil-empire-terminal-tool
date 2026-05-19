# Formula:
# gas_to_cash_multiplier = 15 * current_cash_multiplier
# mins_to_target_cash = (target_cash - current_cash - (current_gas * gas_to_cash_multiplier)) / (gas_per_second * gas_to_cash_multiplier) / 60

import json
import os
import re
import sys
from datetime import datetime

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen, ModalScreen
from textual.widgets import Button, Footer, Input, Label, Rule, Static, RichLog

_base_dir = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(_base_dir, "config.json")

STATIC_VARS = ["target_cash", "gas_per_second", "current_cash_multiplier"]
LABELS = {
    "target_cash": "Target",
    "gas_per_second": "Gas/sec",
    "current_cash_multiplier": "Multiplier",
}
LABELS_FULL = {
    "target_cash": "Target Cash",
    "gas_per_second": "Gas per Second",
    "current_cash_multiplier": "Cash Multiplier",
}


def load_config() -> dict:
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return dict.fromkeys(STATIC_VARS)


def save_config(config: dict) -> None:
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


_SUFFIX_MULTIPLIERS = {"M": 1_000_000, "B": 1_000_000_000, "T": 1_000_000_000_000}


def parse_number(value: str) -> float:
    s = value.strip().replace(",", "")
    m = re.fullmatch(r"([0-9]*\.?[0-9]+)\s*([mMbBtT])", s)
    if m:
        return float(m.group(1)) * _SUFFIX_MULTIPLIERS[m.group(2).upper()]
    return float(s)


def compute_minutes(target_cash, current_cash, current_gas, gas_per_second, current_cash_multiplier) -> float:
    gas_to_cash_multiplier = 15 * current_cash_multiplier
    mins = (target_cash - current_cash - (current_gas * gas_to_cash_multiplier)) / (gas_per_second * gas_to_cash_multiplier) / 60
    return mins


class EditModal(ModalScreen):
    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("ctrl+s", "save", "Save"),
    ]

    def compose(self) -> ComposeResult:
        cfg = self.app.config
        with Vertical(id="modal_container"):
            yield Static("Edit Variables", id="modal_title")
            yield Rule()
            for key in STATIC_VARS:
                yield Label(LABELS_FULL[key], classes="field_label")
                current_val = str(cfg[key]) if cfg.get(key) is not None else ""
                yield Input(value=current_val, id=f"input_{key}", classes="field_input")
            yield Rule()
            with Horizontal(id="modal_buttons"):
                yield Button("Save  ctrl+s", id="save", variant="primary")
                yield Button("Cancel  esc", id="cancel", variant="default")

    def on_mount(self) -> None:
        self.query_one(f"#input_{STATIC_VARS[0]}", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        inputs = list(self.query(Input))
        idx = inputs.index(event.input)
        if idx < len(inputs) - 1:
            inputs[idx + 1].focus()
        else:
            self.action_save()

    def action_save(self) -> None:
        new_config = {}
        for key in STATIC_VARS:
            val = self.query_one(f"#input_{key}", Input).value.strip()
            if not val:
                self.notify(f"{LABELS_FULL[key]} is required.", severity="error")
                return
            try:
                new_config[key] = parse_number(val)
            except ValueError:
                self.notify(f"{LABELS_FULL[key]} must be a number.", severity="error")
                return
        save_config(new_config)
        self.app.config = new_config
        self.dismiss(True)

    def action_cancel(self) -> None:
        self.dismiss(False)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save":
            self.action_save()
        elif event.button.id == "cancel":
            self.action_cancel()


class OnboardingScreen(Screen):
    BINDINGS = [Binding("ctrl+c", "app.quit", "Quit")]

    def __init__(self, config: dict, missing: list):
        super().__init__()
        self.config = config
        self.missing = missing

    def compose(self) -> ComposeResult:
        yield Static("oil-empire", id="brand")
        yield Static("first run — set your static variables to continue", id="subtitle")
        yield Rule()
        with Vertical(id="form"):
            for key in self.missing:
                yield Label(LABELS_FULL[key], classes="field_label")
                yield Input(placeholder=f"enter {LABELS_FULL[key].lower()}", id=f"input_{key}", classes="field_input")
        yield Static("", id="onboard_error")
        yield Button("continue →", id="save", variant="primary")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one(f"#input_{self.missing[0]}", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        inputs = list(self.query(Input))
        idx = inputs.index(event.input)
        if idx < len(inputs) - 1:
            inputs[idx + 1].focus()
        else:
            self._save()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save":
            self._save()

    def _save(self) -> None:
        for key in self.missing:
            val = self.query_one(f"#input_{key}", Input).value.strip()
            if not val:
                self.query_one("#onboard_error", Static).update(f"⚠  {LABELS_FULL[key]} is required")
                return
            try:
                self.config[key] = parse_number(val)
            except ValueError:
                self.query_one("#onboard_error", Static).update(f"⚠  {LABELS_FULL[key]} must be a number")
                return
        save_config(self.config)
        self.app.config = self.config
        self.app.switch_screen(MainScreen())


CASH_INPUT = "#current_cash"
GAS_INPUT = "#current_gas"


class MainScreen(Screen):
    BINDINGS = [
        Binding("e", "edit", "Edit vars"),
        Binding("ctrl+l", "clear_log", "Clear"),
        Binding("ctrl+c", "app.quit", "Quit"),
        Binding("escape", "blur_inputs", "Defocus", priority=True),
    ]

    def compose(self) -> ComposeResult:
        yield Static(self._topbar_text(), id="topbar")
        yield RichLog(id="log", highlight=True, markup=True, wrap=True)
        yield Rule(id="input_rule")
        with Horizontal(id="inputbar"):
            yield Label("current cash", classes="input_label")
            yield Input(id="current_cash", placeholder="0")
            yield Label("current gas", classes="input_label")
            yield Input(id="current_gas", placeholder="0")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one(CASH_INPUT, Input).focus()
        log = self.query_one("#log", RichLog)
        log.write("[dim]enter cash and gas → press Enter to compute[/dim]")
        log.write("[dim]e to edit variables · ctrl+l to clear · ctrl+c to quit[/dim]")
        log.write("")

    def _topbar_text(self) -> str:
        cfg = self.app.config
        parts = []
        for key in STATIC_VARS:
            val = cfg.get(key)
            display = f"{val:,.2f}" if val is not None else "—"
            parts.append(f"[dim]{LABELS[key]}[/dim] {display}")
        return "  [bold]oil-empire[/bold]   " + "   [dim]·[/dim]   ".join(parts)

    def on_screen_resume(self) -> None:
        self.query_one("#topbar", Static).update(self._topbar_text())

    def action_edit(self) -> None:
        def on_dismiss(saved: bool) -> None:
            if saved:
                self.query_one("#topbar", Static).update(self._topbar_text())
                self.query_one("#log", RichLog).write("[dim]─── variables updated ───[/dim]")
        self.app.push_screen(EditModal(), on_dismiss)

    def action_blur_inputs(self) -> None:
        self.query_one(CASH_INPUT, Input).blur()
        self.query_one(GAS_INPUT, Input).blur()

    def action_clear_log(self) -> None:
        self.query_one("#log", RichLog).clear()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "current_cash":
            self.query_one(GAS_INPUT, Input).focus()
        elif event.input.id == "current_gas":
            self._compute()

    def _compute(self) -> None:
        cash_raw = self.query_one(CASH_INPUT, Input).value
        gas_raw = self.query_one(GAS_INPUT, Input).value
        log = self.query_one("#log", RichLog)

        try:
            current_cash = parse_number(cash_raw)
            current_gas = parse_number(gas_raw)
        except ValueError:
            log.write("[red]⚠  enter valid numbers for cash and gas[/red]")
            return

        try:
            mins = compute_minutes(
                self.app.config["target_cash"],
                current_cash,
                current_gas,
                self.app.config["gas_per_second"],
                self.app.config["current_cash_multiplier"],
            )
        except (ZeroDivisionError, TypeError) as e:
            log.write(f"[red]⚠  compute error: {e}[/red]")
            return

        gas_cash = current_gas * 15 * self.app.config["current_cash_multiplier"]
        total_cash = current_cash + gas_cash
        ts = datetime.now().strftime("%H:%M:%S")
        if mins <= 0:
            log.write(
                f"[dim]{ts}[/dim]  [green bold]already at or past target[/green bold]  "
                f"[dim]cash={current_cash:,.0f}  gas≈{gas_cash:,.0f}  total≈{total_cash:,.0f}[/dim]"
            )
        else:
            hours = int(mins // 60)
            rem = mins % 60
            time_str = f"{hours}h {rem:.1f}m" if hours > 0 else f"{mins:.1f}m"
            log.write(
                f"[dim]{ts}[/dim]  "
                f"[cyan bold]{mins:.2f} min[/cyan bold]  [dim]({time_str})[/dim]"
                f"  [dim]cash={current_cash:,.0f}  gas≈{gas_cash:,.0f}  total≈{total_cash:,.0f}[/dim]"
            )

        self.query_one(CASH_INPUT, Input).clear()
        self.query_one(GAS_INPUT, Input).clear()
        self.query_one(CASH_INPUT, Input).focus()


class OilEmpireApp(App):
    CSS = """
    Screen {
        background: $background;
    }

    /* Onboarding */
    #brand {
        color: $accent;
        text-style: bold;
        margin: 1 2 0 2;
    }
    #subtitle {
        color: $text-muted;
        margin: 0 2 1 2;
    }
    #form {
        margin: 0 2;
    }
    .field_label {
        color: $text-muted;
        margin: 1 0 0 0;
    }
    .field_input {
        border: tall $panel;
    }
    .field_input:focus {
        border: tall $accent;
    }
    #onboard_error {
        color: $error;
        margin: 1 0 0 0;
    }
    #save {
        margin: 1 0;
    }

    /* Main */
    #topbar {
        height: 1;
        padding: 0 1;
        background: $panel;
        color: $text;
    }
    #log {
        height: 1fr;
        padding: 0 2;
        scrollbar-gutter: stable;
    }
    #input_rule {
        margin: 0;
        color: $panel;
    }
    #inputbar {
        height: 3;
        padding: 0 2;
        align: left middle;
        background: $surface;
    }
    .input_label {
        color: $text-muted;
        width: auto;
        padding: 0 1 0 0;
    }
    #inputbar Input {
        width: 28;
        margin-right: 3;
        border: none;
        background: $background;
    }
    #inputbar Input:focus {
        border: tall $accent;
        background: $background;
    }

    /* Edit Modal */
    EditModal {
        align: center middle;
    }
    #modal_container {
        background: $surface;
        border: round $accent;
        padding: 1 2;
        width: 56;
        height: auto;
    }
    #modal_title {
        text-style: bold;
        text-align: center;
        margin-bottom: 1;
    }
    #modal_buttons {
        margin-top: 1;
        align: right middle;
    }
    #modal_buttons Button {
        margin-left: 1;
    }
    """

    def __init__(self):
        super().__init__()
        self.config = load_config()

    def on_mount(self) -> None:
        missing = [k for k in STATIC_VARS if self.config.get(k) is None]
        if missing:
            self.push_screen(OnboardingScreen(self.config, missing))
        else:
            self.push_screen(MainScreen())


if __name__ == "__main__":
    OilEmpireApp().run()
