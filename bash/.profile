# ~/.profile: executed by the command interpreter for login shells.
# This file is not read by bash(1), if ~/.bash_profile or ~/.bash_login
# exists.
# see /usr/share/doc/bash/examples/startup-files for examples.
# the files are located in the bash-doc package.

# the default umask is set in /etc/profile; for setting the umask
# for ssh logins, install and configure the libpam-umask package.
#umask 022

# if running bash
# if [ -n "$BASH_VERSION" ]; then
# 	# include .bashrc if it exists
# 	if [ -f "$HOME/.bashrc" ]; then
# 		. "$HOME/.bashrc"
# 	fi
# fi

if [ $TILIX_ID ] || [ $VTE_VERSION ]; then
        source /etc/profile.d/vte.sh
fi

# Preferred editor for local and remote sessions
if [[ -n $SSH_CONNECTION ]]; then
	export EDITOR='vim'
else
	export EDITOR='nvim'
	export SUDO_EDITOR='/home/user/.local/share/bob/nvim-bin/nvim'
fi

# if [ -e /home/user/.nix-profile/etc/profile.d/nix.sh ]; then . /home/user/.nix-profile/etc/profile.d/nix.sh; fi # added by Nix installer

# set PATH so it includes user's private bin if it exists
#if [ -d "$HOME/bin" ] ; then
# PATH="$HOME/bin:$PATH"
#fi

# export NVM_DIR="$HOME/.nvm"
# [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"  # This loads nvm

if fd &> /dev/null
then 
    export FZF_DEFAULT_COMMAND='fd -H -E .git .'
fi

if [ -e $HOME/.cargo/env ]; then
    . "$HOME/.cargo/env"
fi

PATH=$PATH:~/.local/share/bob/nvim-bin

alias cls='clear'
alias winuser='cd /mnt/c/Users/Omistaja'
alias br='br -h'
alias e='exit'
alias lg='lazygit'
alias t='tmux'
alias ta='tmux attach'
alias tconfig='nvim ~/.tmux.conf'
alias v='nvim'
alias stmux='tmux source ~/.tmux.conf'
alias ta='tmux a'
alias apexconfig='cd /mnt/c/Program Files (x86)/Steam/steamapps/common/Apex Legends/cfg'
alias ghclone='git clone https://github.com/' 
alias l='ls -CF'
alias la='ls -A'
alias ll='ls -alF'
alias ls='ls --color=auto'
alias sl="ls"
alias ..="cd .."
alias ...="cd ../.."
alias ....="cd ../../.."
alias s="sk --preview='bat {} --color=always'"
alias ns="nvim -c SessionsLoad"
alias so="exec zsh"
alias sk="rg --files -L -. | sk --bind 'ctrl-t:execute(nvim {})+abort' --preview 'bat {} --color=always'"
alias make="make -s"

if [ -e /mnt/c/Users ]; then
    alias alacritty='cd /mnt/c/Users/Omistaja/AppData/Roaming/alacritty'
fi

if [ -e /home/user/.nix-profile/etc/profile.d/nix.sh ]; then . /home/user/.nix-profile/etc/profile.d/nix.sh; fi # added by Nix installer

# export NVM_DIR="$HOME/.nvm"
# [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"  # This loads nvm
