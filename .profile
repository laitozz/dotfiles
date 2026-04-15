# ~/.profile: executed by the command interpreter for login shells.
# This file is not read by bash(1), if ~/.bash_profile or ~/.bash_login
# exists.
# see /usr/share/doc/bash/examples/startup-files for examples.
# the files are located in the bash-doc package.

# the default umask is set in /etc/profile; for setting the umask
# for ssh logins, install and configure the libpam-umask package.
#umask 022

# Preferred editor for local and remote sessions
if [[ -n $SSH_CONNECTION ]]; then
	export EDITOR='vim'
else
	export EDITOR='nvim'
	export SUDO_EDITOR='/home/user/.local/share/bob/nvim-bin/nvim'
fi

alias lg='lazygit'
alias ta='tmux attach'
alias tconfig='nvim ~/.tmux.conf'
alias stmux='tmux source ~/.tmux.conf'
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
