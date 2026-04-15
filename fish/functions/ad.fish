function ad --description 'add dir to tmux_dirs'
	if set -q argv[1]
		echo $argv[1] >> ~/.dotfiles/utils/tmux_dirs
	else
		echo $PWD >> ~/.dotfiles/utils/tmux_dirs
	end
end
