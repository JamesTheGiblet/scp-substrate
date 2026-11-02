# Start-up guide

How to get the cube page running and work through your cubes. Run every command from the repo folder, `C:\Users\gilbe\Documents\scp-substrate`.

## First time only

1. Set the editing password. Nothing appears as you type, which is normal. Use at least 8 characters.

   ```powershell
   python keystone-gate/kg cube password
   ```

2. For model drafts, add your keys to `.env` in the repo folder. Git ignores this file.

   ```text
   claude_API_KEY=your-key
   gemini_API_KEY=your-key
   ```

3. Install the Anthropic SDK. Only Claude needs it.

   ```powershell
   pip install -r keystone-gate/requirements.txt
   ```

4. For the local fallback, install Ollama and get the model:

   ```powershell
   ollama pull llama3.2
   ```

5. To add repos, sign in to GitHub once:

   ```powershell
   gh auth login
   ```

The page works without steps 2 to 5. You can still read, write, accept and validate, but models cannot draft.

## Every time

```powershell
python keystone-gate/kg cube serve --by james
```

A tab opens at `http://127.0.0.1:8765/`. Leave the terminal running while you work, and press Ctrl+C there to stop.

## Checking drafts

1. Click **Grid** at the top right.
2. Click **Unlock to edit** and enter your password.
3. Click **Drafts to check** in the filter row.
4. Click a cube. Under each draft:
   - **Accept** if it is right.
   - **Edit** to change it first.
   - **Reject** to drop it. The face goes blank.
5. When all five faces are done, use **Validate** under HUMAN VALIDATION to say why the claim holds.
6. If you stand behind it, press **I stand behind this**. That attests the cube.

Editing locks again when you press Lock, reload the page, stop the server, or leave it idle for 30 minutes.

## Adding things

- **New cube:** in the unlocked grid, press **+ New cube**. Any face you leave empty is drafted automatically, and the text goes to Anthropic, then to Google if Claude fails.
- **Blank faces:** press **Fill blanks**. A message and the count in the tab title tell you when drafts arrive.
- **A repo:** run the command below, then press **Repos** under **Cluster by** in the 3D view. Private repos use Ollama only.

  ```powershell
  python keystone-gate/kg repo add JamesTheGiblet/repo-name
  ```

To draft everything at once at the terminal:

```powershell
python keystone-gate/kg cube draft     # every blank face
python keystone-gate/kg cube notes     # a suggested validation note for each cube
```

## Using it on your phone

Your phone uses the same page and the same data as this PC, so the PC must be on with `serve` running.

First time only:

1. Install Tailscale on this PC and your phone from tailscale.com, and sign in to the same account on both.
2. On this PC, in a terminal:

   ```powershell
   tailscale serve --bg 8765
   ```

   Keep the `https://....ts.net` address it prints. Only devices on your own Tailscale account can reach it.

Every time, start the server with that name, without `https://`:

```powershell
python keystone-gate/kg cube serve --by james --host your-pc.your-tailnet.ts.net
```

Then open the `https://` address on your phone, go to **Grid** and unlock it. The phone and PC unlock separately.

## Going back through time

In the 3D view, drag the bar at the bottom or press **Play**. Cubes appear when they were created, and faces fill in as they were written. The far right end of the bar is now.

## Other useful commands

```powershell
python keystone-gate/kg cube view                         # read-only page, no server
python keystone-gate/kg ask "what do I know about servo power"            # gated answer
python keystone-gate/kg ask --claude "what do I know about servo power"   # reworded by a model
python tests/run.py                                       # run all tests
```

## If something looks wrong

| What you see | Cause | What to do |
|---|---|---|
| No Accept or Edit buttons | The read-only page, or still locked | Check the address starts with `http://127.0.0.1:8765`, not `file:///`. Then go to Grid and unlock |
| `Set an editing password first` | No password yet | Run `kg cube password` |
| Page says the server has stopped | The terminal was closed or stopped | Run `kg cube serve` again and reload the page |
| Page says "wrong host" on the phone | `--host` is missing or mistyped | Restart `serve` with the exact name from `tailscale serve` |
| Forgot the password | | Delete `~/.config/scp/cube-edit.json` and set a new one |
| Credit error from Claude | No API credit | Nothing needed. The next model takes over |
| Gemini 503 or timeout | Google is busy | Nothing needed. Ollama takes over, or try later |
| Ollama timeout | Long README or a slow machine | Close other heavy programs and try again. `Canon` has not worked yet |
| Lines about `.bashrc` in a shell | The file is not saved as UTF-8 | Harmless. Commands still run |

Python errors mentioning a missing `anthropic` module mean step 3 was skipped. Drafting still moves on to Gemini.
