# Development

How to run Intentional from source, test it, build the Windows executables and publish a release. To learn how the code is organised, start with the [code guide](code-guide.md).

- [Running from source](#running-from-source)
- [Testing](#testing)
- [The app icon](#the-app-icon)
- [Packaging the Windows executables](#packaging-the-windows-executables)
- [Running the web version](#running-the-web-version)
- [Releases and automated builds](#releases-and-automated-builds)
  - [Publishing a release](#publishing-a-release)
  - [Test builds without a release](#test-builds-without-a-release)

## Running from source

The project uses [uv](https://docs.astral.sh/uv/) to manage Python and the dependencies. Python 3.11 or newer is required. Clone the repository, open the folder in VS Code, and run these commands from the project folder:

`.python-version` selects Python 3.13 for local development and for the current GitHub workflows on Windows and Linux. The package metadata permits Python 3.11 or newer, but CI currently exercises Python 3.13.

| Task | Command |
|-|-|
| Create or update the environment (CLI, GUI and dev tools) | `uv sync --extra dev --extra gui` |
| CLI only | `uv sync` |
| Run the CLI | `uv run intentional-cli --help` |
| Run the GUI | `uv run intentional` or `uv run intentional-cli gui` |
| Run the tests | `uv run pytest` |
| Lint | `uv run ruff check src web/serve.py` |
| Format | `uv run ruff format src web/serve.py` (add `--check` to only report, without changing files) |
| Update the lock file after editing `pyproject.toml` | `uv lock` |
| Upgrade the dependencies | `uv lock --upgrade`, then `uv sync --extra dev --extra gui` |
| List dependencies with newer releases than `pyproject.toml` allows | `uv tree --outdated --depth 1` |

`uv lock --upgrade` moves every dependency, including the `gui` and `dev` extras, to the newest release allowed by the ranges in `pyproject.toml`. To go past a range (for example a new major version), raise it in `pyproject.toml` after checking the release notes, then run `uv lock`.

The GUI packages are optional (the `gui` extra), so the CLI can be installed without them. If `intentional-cli gui` is run without them, it explains how to install them.

If uv reports `invalid peer certificate: UnknownIssuer` (common behind a corporate proxy), add `--system-certs` to the uv command to use the operating system's certificates.

## Testing

The tests are in `src/intentional_py/tests` (see the [code guide](code-guide.md#tests) for what each file covers). They cover the CLI commands, the config checks, the core functions used by both front ends, and the GUI actions; no display is needed. Install the dev tools with `uv sync --extra dev --extra gui`, then run `uv run pytest`. The GUI command test is skipped if the `gui` extra is not installed. The same tests, plus `ruff check src web/serve.py` and `ruff format --check src web/serve.py`, run on GitHub for every push to `main` and every pull request.

```text
> uv run pytest -q
........................................................................ [ 55%]
..........................................................

                                 [100%]
130 passed
```

## The app icon

A speech bubble around a boxed checkmark (echoing the ✔ already used throughout the CLI/GUI output), simplified from the ChatGPT-generated `assets/icon-logo.png` design reference into flat, scalable shapes. The bubble's own border keeps that reference image's rainbow sweep regardless of accent; only the cube and the checkmark badge recolor. It's generated, not hand-edited: `intentional_py.gui.icon_render` draws it with the standard library only (no imaging package dependency), and `assets/generate_icon.py` calls it to write every static copy the project needs, baked at the default "blue" accent:

```bash
uv run python assets/generate_icon.py
```

| File | Used by |
|-|-|
| `assets/icon.ico` | `icon=` in both PyInstaller spec files (the `.exe` file icon) |
| `assets/icon.png` | The source PNG; not shipped anywhere by itself |
| `src/intentional_py/gui/icon.png` | The GUI's window/taskbar icon, loaded once at startup via `importlib.resources`, and the logo next to "Intentional" in its in-window heading (`_build_header()`) |
| `web/icon.png`, `web/favicon.ico` | The web version's favicon |
| `assets/icon.svg` | A hand-authored standalone copy of the web header's inline SVG logo, used at the top of `README.md` for repo branding. Not generated - update it by hand if the shape changes (see below). |

The GUI's window/taskbar icon is static on purpose (`_window_icon()`), not accent-driven - a window icon that changed color while open would be an odd surprise, unlike an in-page logo. The GUI also shows the logo in-window, next to a bold "Intentional" heading above the project folder row (`_build_header()`), mirroring the web version's header brand. The web version's header logo is the one place the icon does recolor: an inline SVG (`web/index.html`'s `.logo-mark`) with the cube/checkmark badge following `var(--accent)`/`var(--accent-fg)` and `color-mix()` for the cube's shaded faces, while its bubble border keeps the same fixed rainbow `<linearGradient>` as the static icon. The **Accent color** picker's own colors (`ACCENT_PRESETS` in `gui/app.py`) are the same hex values as the web version's `--accent`/`--accent-hover` pairs, so the two front ends' accent system looks like one brand rather than two independently-tuned palettes; `gui/theme.json`'s default colors match the "blue" preset for the same reason. Keeping the GUI and web versions visually matched is a standing goal - check both when changing either's colors or branding.

The CLI has no equivalent of its own (a terminal has no icon to recolor); the only touchpoint is `intentional-cli.exe`'s file/taskbar icon via `assets/icon.ico` above. A GitHub repository's social preview image (Settings > General > Social preview) also has to be uploaded manually rather than committed - `assets/icon.png` or a screenshot works for that if wanted.

To change the icon's shape, edit the coordinates in `intentional_py/gui/icon_render.py` (plain coordinate math in a 64x64 design space, no image editor needed), then rerun `generate_icon.py` and commit the regenerated files alongside it.

## Packaging the Windows executables

The GUI and the CLI can each be built as a standalone Windows executable that doesn't need Python installed. Releases are normally built by GitHub Actions (see [Releases and automated builds](#releases-and-automated-builds)); these steps build them by hand:

| Executable | Spec file | Use |
|-|-|-|
| `intentional.exe` | `intentional-gui.spec` | The GUI. Opens without a console window. |
| `intentional-cli.exe` | `intentional-cli.spec` | The CLI. Run it from a terminal with the same options as `intentional-cli`. |

On Windows, from the project folder:

```bash
uv sync --extra dev --extra gui
uv run pyinstaller --noconfirm intentional-gui.spec
uv run pyinstaller --noconfirm intentional-cli.spec
```

The executables are created in the `dist` folder. The version is shown in the GUI's title bar and next to the project folder, by `intentional-cli.exe --version`, and in each executable's file properties (Explorer > Properties > Details). The file properties are generated from the version in `pyproject.toml` by `version_info.py`. Both spec files only build on Windows; on Linux the CLI is run with `uv run intentional-cli`.

`intentional-cli.exe` is meant to be run from a terminal (for example `intentional-cli.exe nl -v FIN`). Double-clicking it runs the default DD build using `intents.cfg` in the executable's folder, then the console closes immediately. The GUI isn't included in `intentional-cli.exe`, so `intentional-cli.exe gui` points to `intentional.exe` instead.

## Running the web version

A third front end (see [code guide](code-guide.md#browser-front-end-web-folder)) that runs the core in the browser via [Pyodide](https://pyodide.org/), with no server beyond a static file server for the page itself. It isn't part of a release yet; try the hosted copy below, or run it from source:

```bash
python web/serve.py
```

Or double-click `web/run.bat` (Windows) / `web/run.sh` (Linux/macOS) — the same command, for anyone who'd rather not open a terminal; both just call `serve.py` and pause on error so the window doesn't vanish if something fails.

That's the one command needed: it builds the project wheel into `web/` if it's missing or older than the source (comparing file modification times, so no need to remember to rebuild after a code change), requiring `uv` on `PATH` to do so, writes `web/wheel-filename.txt` so `app.js` never hardcodes a version, then serves `web/` on `localhost` and opens it. `web/app.js` pins a specific Pyodide version (via the `jsdelivr` CDN in `web/index.html`); bump that version there if you want a newer Pyodide.

The page's **? Help** button opens the same per-task explanations as the GUI's Help window, defined directly in `web/index.html`. Open or start a project once (a zip upload or a folder - a folder needs a browser that supports picking one, e.g. Chrome/Edge/Firefox/Safari - or empty), then run as many tasks against it as needed — each task's output is immediately available to the next, and **Download project** zips the current state at any point.

The layout is responsive, down to phone-sized screens: the header's brand (logo/title) stays centered and its controls (Help/accent/theme) move below it on narrow widths rather than overlapping, and the form fields stack into a single column (`@media (max-width: 560px)`).

A hosted copy also runs on [GitHub Pages](https://andrewjstuart.github.io/intentional-py/), kept up to date by `.github/workflows/pages.yml` on every push to `main` (the same build-the-wheel-and-serve-`web/`-folder idea as `serve.py`, just run once in CI instead of locally). This is the option for a machine where even opening a terminal isn't possible — nothing but a browser is needed. The one-time setup on GitHub is **Settings > Pages > Source: GitHub Actions**; after that the workflow deploys on its own.

The page follows the browser's light/dark mode preference (`prefers-color-scheme`) by default; the toggle button overrides this and remembers the choice in the browser's `localStorage`, the web equivalent of `gui/settings.py`. The accent color swatch button next to it works the same way, picking from eight presets defined as CSS custom properties in `web/index.html` (`[data-theme][data-accent]` rules); the GUI has an equivalent **Accent color** menu (`ACCENT_PRESETS` in `gui/app.py`).

All eight tasks are implemented (`src/intentional_py/web/actions.py`, covered by `test_web_actions.py` like any other core-facing code — no browser needed to test it). They all operate on a single session workspace (a directory in Pyodide's virtual filesystem, created by `new_project`/`open_project`/`open_project_files` and held in a module-level global for as long as the page stays open), so later tasks see earlier tasks' output with no re-upload. Every task returns a JSON summary; `download_project` separately zips the workspace's current state on demand.

## Releases and automated builds

[GitHub Actions](https://docs.github.com/actions) runs three workflows from the `.github/workflows` folder on GitHub's own machines, so no local Windows machine is needed to build a release. Their runs, logs and results are listed on the repository's **Actions** tab.

| Workflow | File | Runs when | What it does |
|-|-|-|-|
| Tests | `tests.yml` | A push to `main`, any pull request, or **Run workflow** | Runs the tests on Windows and Linux. A failure is shown on the pull request and on the badge at the top of the README. |
| Release | `release.yml` | A tag starting with `v` is pushed, a release is published on GitHub (which creates the tag itself, without a push), or **Run workflow** | On Windows: runs the tests, builds both executables and `SHA256SUMS.txt`, and for a tag or a release publishes them to it. |
| Pages | `pages.yml` | A push to `main`, or **Run workflow** | Builds the wheel and deploys the `web/` folder to GitHub Pages (see [Running the web version](#running-the-web-version)). |

The Tests and Release workflows install with `uv sync --locked`, so they fail if `uv.lock` doesn't match `pyproject.toml`. Run `uv lock` and commit `uv.lock` to fix that.

[Dependabot](https://docs.github.com/code-security/dependabot) (`.github/dependabot.yml`) checks weekly for new versions of the Python dependencies and of the actions used by the workflows, and opens a pull request for each group of updates. The Tests workflow runs on each of those pull requests, so an update can be merged once its tests pass.

### Publishing a release

1. Update the version in **both** `pyproject.toml` and `src/intentional_py/__init__.py` (a test fails if they differ), for example to `1.1.0`.
2. Run `uv lock`, since `uv.lock` records the project's version, then `uv run pytest`.
3. Commit the changes and merge them into `main`.
4. Create a tag named `v` followed by the version, for example `v1.1.0`, in either of these ways:

   **On GitHub (no command line needed)**

   1. On the repository page, open **Releases** and select **Draft a new release**.
   2. Under **Choose a tag**, type `v1.1.0` and select **Create new tag: v1.1.0 on publish**.
   3. Set **Target** to `main`.
  4. Enter a **Release title** (e.g. `v1.1.0`) and select **Generate release notes** to list the changes since the previous release. Edit the generated notes to add any important usage changes or warnings.
   5. Optionally tick **Set as a pre-release**, so the release isn't shown as the latest until its executables are attached.
   6. Select **Publish release**. Don't use **Save draft**: a draft doesn't create the tag, so no build starts.

   Publishing creates the tag and starts the build. The executables are added to this release when the build finishes. If it was marked as a pre-release, edit the release afterwards, untick **Set as a pre-release** and tick **Set as the latest release**.

   **From the command line**

   ```bash
   git checkout main
   git pull
   git tag v1.1.0
   git push origin v1.1.0
   ```

   Pushing the tag starts the build, which creates the release with generated release notes.

5. Open the **Actions** tab and follow the **Release** run. When it finishes, the release under **Releases** has `intentional.exe`, `intentional-cli.exe` and `SHA256SUMS.txt` attached. Edit the release on GitHub at any time to change its notes.

The release is built from exactly the tagged commit, and the build fails without adding any files if the tag doesn't match the version in `pyproject.toml` or if any test fails. To retry after a fix, delete the release and then its tag on the **Releases** page (or delete the tag with `git tag -d v1.1.0` and `git push origin :refs/tags/v1.1.0`), then create the tag again from the fixed commit.

### Test builds without a release

On the **Actions** tab, select **Release**, then **Run workflow**, choose a branch and select **Run workflow** again. When the run finishes, download the executables from the **Artifacts** section at the bottom of the run's page (`intentional-windows`, a zip file). Nothing is published, and GitHub deletes artifacts after 90 days by default.
