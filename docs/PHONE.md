# Working on your phone with no laptop

How to carry the store on an Android phone and work on it with no network. The phone runs its own copy of the cube page, and git carries `sc.db` between the phone and the laptop.

If the laptop stays at home on wifi, you don't need this. Use Tailscale instead, as set out in [STARTUP.md](STARTUP.md).

## The one rule

`sc.db` is a single file, and git can't merge two copies of it. **Only one device changes it at a time.**

- Before you go, push from the laptop and pull on the phone.
- While you're out, don't change anything on the laptop.
- When you're back, push from the phone and pull on the laptop.

If both change it, one side's changes are lost. See [If both changed it](#if-both-changed-it).

## First time only

1. Install **Termux** from F-Droid (f-droid.org). The Play Store copy is out of date and its packages fail to install.
2. In Termux, install what the store needs:

   ```sh
   pkg update
   pkg install python git gh
   ```

   The store runs on Python's standard library alone, so nothing else is needed.

3. Sign in to GitHub. The repo is private, so the phone needs your account.

   ```sh
   gh auth login
   ```

   Pick GitHub.com, then HTTPS, and say yes to "Authenticate Git with your GitHub credentials". Log in with a web browser when it asks.

4. Get the repo, on the branch the laptop is using. To see which branch that is, run `git branch --show-current` on the laptop. It is `foundations-links-and-strands` at the time of writing.

   ```sh
   cd ~
   git clone -b foundations-links-and-strands https://github.com/JamesTheGiblet/scp-substrate.git
   cd scp-substrate
   ```

5. Set an editing password for the phone. It's kept on the phone only, never in git, so it can differ from the laptop's.

   ```sh
   python keystone-gate/kg cube password
   ```

## Before you go (needs network)

On the laptop:

1. Stop the cube server: press Ctrl+C in its terminal.
2. Push the store:

   ```powershell
   git add sc.db
   git commit -m "Store before going out"
   git push
   ```

   If git says "nothing to commit", the store hasn't changed. Just run `git push`.

On the phone:

```sh
cd ~/scp-substrate
git pull
```

Check that it says `Fast-forward` or `Already up to date`. Anything else, stop and sort it out before you go.

## While you're out (no network needed)

Start the page on the phone:

```sh
cd ~/scp-substrate
python keystone-gate/kg cube serve --by james --no-open
```

Then open `http://127.0.0.1:8765/` in Chrome on the phone. Go to **Grid** and unlock it with the phone's password. Everything works as on the laptop except model drafts, which need the network.

- **Keep Termux awake:** pull down the Termux notification and tap **Acquire wakelock**. Without it, Android can stop the server when the screen is off. Release it when you're done.
- **Stop the server:** in Termux, press Volume Down + C (that's Ctrl+C).
- **The terminal works too:** `kg import`, `kg ask` and the other commands run the same as on the laptop.

## When you're back (needs network)

On the phone, stop the server, then push:

```sh
cd ~/scp-substrate
git add sc.db
git commit -m "Store from the phone"
git push
```

Mobile data or a hotspot is enough for this.

On the laptop:

```powershell
git pull
```

It should say `Fast-forward`. The laptop now has everything you did on the phone.

## If both changed it

If the laptop's `git pull` says there is a conflict in `sc.db`, both devices changed the store. Git can't combine them, so you choose which copy to keep.

To keep the **phone's** copy, which loses what changed on the laptop:

```powershell
git checkout --theirs sc.db
git add sc.db
git commit -m "Keep the phone's store"
```

To keep the **laptop's** copy, which loses what changed on the phone:

```powershell
git checkout --ours sc.db
git add sc.db
git commit -m "Keep the laptop's store"
```

Then push. These are for the laptop. On the phone the two swap over: `--theirs` keeps the laptop's copy and `--ours` keeps the phone's.

If you need both sets of changes, stop before either of these and get help. The lost side's changes can be redone by hand, or copied across, but not merged by git.

## If something looks wrong

| What you see | Cause | What to do |
|---|---|---|
| `pkg install` fails with mirror errors | The Play Store Termux | Uninstall it and install Termux from F-Droid |
| `git clone` asks for a password | Git isn't signed in | Run `gh auth login` again and say yes to authenticating Git |
| "Set an editing password first" | No password on the phone yet | Run `python keystone-gate/kg cube password` |
| The page stops loading after a while | Android stopped Termux | Acquire the wakelock, then start the server again |
| `git push` is rejected | The laptop pushed while you were out | Run `git pull` on the phone, then see [If both changed it](#if-both-changed-it) |
