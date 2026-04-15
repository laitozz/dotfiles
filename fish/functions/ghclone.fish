function ghclone --wraps='git clone https://github.com/' --description 'alias ghclone git clone https://github.com/'
  git clone https://github.com/ $argv
        
end
