ZINIT_HOME="${XDG_DATA_HOME:-${HOME}/.local/share}/zinit/zinit.git"
[ ! -d $ZINIT_HOME ] && mkdir -p "$(dirname $ZINIT_HOME)"
[ ! -d $ZINIT_HOME/.git ] && git clone https://github.com/zdharma-continuum/zinit.git "$ZINIT_HOME"
source "${ZINIT_HOME}/zinit.zsh"

zinit light zdharma-continuum/fast-syntax-highlighting
zinit light zsh-users/zsh-completions
zinit light zsh-users/zsh-autosuggestions

zinit ice depth"1" # git clone depth
zinit light romkatv/powerlevel10k
[[ ! -f ~/.p10k.zsh ]] | source ~/.p10k.zsh

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

# compinit
 
# zprof
