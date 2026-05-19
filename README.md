# oil-empire-tool

A terminal utility for [Oil Empire](https://www.roblox.com/games/) (Roblox). Calculates how long until you have enough gas to reach a target cash amount.

## Features

- Calculate minutes/hours remaining until target cash is reached from current gas income
- Supports shorthand number input (`1.5B`, `200M`, `4T`)
- Persists your static variables (target, gas/sec, multiplier) between sessions

## Usage on Windows

1. Download the latest release (`oil-empire-tool.exe`) from the [Releases](../../releases) page.
2. Move the `.exe` to a folder of your choice (e.g. `C:\tools\bin`).
3. Add that folder to your **PATH** environment variable:
   - Open **Settings → System → About → Advanced system settings → Environment Variables**
   - Under *System variables*, select `Path` → **Edit** → **New** → paste your folder path → **OK**
4. Open a new terminal and run:
   ```
   oil-empire-tool
   ```

### First run

On first launch, you'll be prompted to enter three static variables:

| Variable | Description |
|---|---|
| **Target Cash** | The cash amount you're aiming for |
| **Gas per Second** | Your current gas income rate |
| **Cash Multiplier** | Your current cash multiplier |

These are saved to `config.json` next to the executable and reloaded on every launch.

### Main screen

Enter your **current cash** and **current gas**, then press `Enter`. The tool prints how many minutes (and hours) remain.

| Key | Action |
|---|---|
| `Enter` | Submit current field / compute |
| `e` | Edit static variables |
| `Ctrl+L` | Clear the log |
| `Ctrl+C` | Quit |
| `Esc` | Defocus inputs |

## Development

### Prerequisites

- Python 3.11+
- [`uv`](https://github.com/astral-sh/uv) (for installing dependencies)
- `make`

### Make commands

| Command | Description |
|---|---|
| `make install` | Install dependencies from `requirements-dev.txt` into the virtual environment |
| `make run` | Run the app directly with Python (no build needed) |
| `make build` | Build a standalone `oil-empire-tool.exe` via PyInstaller into `dist/` |
| `make deploy` | Build, then copy the exe to `C:\tools\bin\` |

### Setup

```bash
python -m venv venv
make install
make run
```

## Contributing

1. Fork this repository.
2. Create a branch for your change.
3. Make your changes and test locally with `make run`.
4. Open a pull request against `main`.

Keep PRs focused — one feature or fix per PR.

## Submitting issues

Open an issue on [GitHub Issues](../../issues). Include:

- What you expected to happen
- What actually happened
- Steps to reproduce
- Your OS and terminal

## License

[MIT](LICENSE)
