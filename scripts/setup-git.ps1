# setup-git.ps1 — Configure git locally so bot-generated data files never trigger
# an interactive merge (Vim) or a conflict again, and add a one-shot `git ship`.
#
# Run ONCE on this machine:  .\scripts\setup-git.ps1
#
# What it does:
#  1. Declares the "theirs" merge driver referenced by .gitattributes
#     (on conflict in a bot data file, take the incoming/remote version).
#  2. Makes `git pull` rebase by default (linear history, fewer merge prompts).
#  3. Never opens an editor for merge messages.
#  4. Adds `git ship`  = pull (rebase, autostash) + push, in one command.

Write-Host "Configuring git for to1000..." -ForegroundColor Cyan

# 1. merge driver used by .gitattributes (merge=theirs)
git config merge.theirs.name "always take the incoming version"
git config merge.theirs.driver "cp -f %B %A"

# 2. pull = rebase, auto-stash local noise
git config pull.rebase true
git config rebase.autoStash true

# 3. never open an editor for merge/rebase messages
git config core.mergeoptions --no-edit

# 4. one-command sync: `git ship`
git config alias.ship '!git pull --rebase --autostash && git push'

Write-Host "Done." -ForegroundColor Green
Write-Host ""
Write-Host "From now on, to publish your local commits just run:" -ForegroundColor Yellow
Write-Host "    git ship" -ForegroundColor White
Write-Host ""
Write-Host "It pulls (rebasing over bot commits, auto-resolving data files) then pushes." -ForegroundColor Gray
Write-Host "The auto-deploy workflow then ships it to Cloudflare. No Vim, no conflicts." -ForegroundColor Gray
