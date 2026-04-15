function stmux --wraps='tmux source ~/.tmux.conf' --description 'alias stmux tmux source ~/.tmux.conf'
  tmux source ~/.tmux.conf $argv
        
end
