# run sway
# TODO: move to zinit or similar
if [ -z "$WAYLAND_DISPLAY" ] && [ "$XDG_VTNR" -ge 1 ]; then
	sway
	exit
fi

# zmodload zsh/zprof
if [[ -r "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh" ]]; then
  source "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh"
fi


# Download Znap, if it's not there yet.
[[ -f ~/Git/zsh-snap/znap.zsh ]] ||
    git clone --depth 1 -- \
        https://github.com/marlonrichert/zsh-snap.git ~/Git/zsh-snap

source ~/Git/zsh-snap/znap.zsh  # Start Znap

# `znap prompt` makes your prompt visible in just 15-40ms!
znap source romkatv/powerlevel10k
[[ ! -f ~/.p10k.zsh ]] || source ~/.p10k.zsh

# znap source zsh-users/zsh-autosuggestions
znap source zdharma-continuum/fast-syntax-highlighting
# `znap source` automatically downloads and starts your plugins.
znap source marlonrichert/zsh-autocomplete

# `znap eval` caches and runs any kind of command output for you.

# `znap function` lets you lazy-load features you don't always need.
znap function _pyenv pyenv 'eval "$( pyenv init - --no-rehash )"'
compctl -K    _pyenv pyenv

# Load bash profile
[[ -e ~/.profile ]] && emulate sh -c 'source ~/.profile'

# Enable history 
HISTFILE=~/.zsh-history
HISTSIZE=1000
SAVEHIST=1000
setopt appendhistory

timezsh() {
  shell=${1-$SHELL}
  for i in $(seq 1 10); do /usr/bin/time $shell -i -c exit; done
}

bindkey -e

# Bind <M-j> and <M-k> to <Up> and <Down>
bindkey -s 'j' 'OB'
bindkey -s 'k' 'OA'

# Open Neovim with <M-n>
bindkey -s '^[o' 'nvim $(sk)^M'
bindkey -s '^[n' 'nvim'


# Backwards i-search 
bindkey -s '' history-incremental-pattern-search-backward


# Better history navigation
bindkey '' up-history
bindkey '' down-history

fpath+=~/.zfunc

compinit

# if [ -e /home/user/.nix-profile/etc/profile.d/nix.sh ]; then . /home/user/.nix-profile/etc/profile.d/nix.sh; fi # added by Nix installer



## TODO: conditional zoxide eval
# znap eval zoxide "zoxide init zsh"
# eval "$(zoxide init zsh)"

if command -v tmux &> /dev/null && [ -n "$PS1" ] && [[ ! "$TERM" =~ screen ]] && [[ ! "$TERM" =~ tmux ]] && [ -z "$TMUX" ] && [[ -O LOGIN ]]; then
    # TODO: copy fish script for not always attaching
  exec tmux attach
fi

# zprof

export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"  # This loads nvm
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"  # This loads nvm bash_completion

[ -f "/home/user/.ghcup/env" ] && source "/home/user/.ghcup/env" # ghcup-env

# TODO: conditional broot management
# source /home/user/.config/broot/launcher/bash/br
