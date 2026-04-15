if status is-interactive
    if command -q tmux && [ "$TERM" != "tmux" ] && [ -z "$TMUX" ]
		ta
    end

    if command -q fd
		export FZF_DEFAULT_COMMAND='fd -H -E .git .'
    end

    if ! command -q fisher
	curl -sL https://raw.githubusercontent.com/jorgebucaran/fisher/main/functions/fisher.fish | source && fisher install jorgebucaran/fisher
    end

	set -gx fish_greeting 
	set -gx EDITOR nvim
	set -gx VISUAL nvim
	set -gx PAGER "nvim +Man!"
	set -q nvm_default_version; or set -U nvm_default_version latest
    fish_add_path $HOME/.cargo/bin $HOME/.local/share/bob/nvim-bin $HOME/.cabal/bin $HOME/.ghcup/bin $HOME/.local/bin
end
