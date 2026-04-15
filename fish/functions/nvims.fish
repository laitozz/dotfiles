function nvims
	set opts "alt-name" "nvim"
	if count $argv > /dev/null
		set -f val $argv
	else
		set val (echo $opts | string split ' ' | fzf)
	end
	set -x NVIM_APPNAME $val
	nvim
end
