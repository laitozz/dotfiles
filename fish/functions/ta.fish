function ta --description 'attach or create new session'
	if set -q argv[1]
		set session $argv[1]
	else 
		set session user
	end
	tmux attach -t $session 2> /dev/null || tmux new-session -s $session
end
