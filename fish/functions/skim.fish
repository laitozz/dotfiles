function skim --wraps=rg\ --files\ -L\ -.\ \|\ sk\ --bind\ \'ctrl-t:execute\(nvim\ \{\}\)+abort\'\ --preview\ \'bat\ \{\}\ --color=always\' --description alias\ sk\ rg\ --files\ -L\ -.\ \|\ sk\ --bind\ \'ctrl-t:execute\(nvim\ \{\}\)+abort\'\ --preview\ \'bat\ \{\}\ --color=always\'
  rg --files -L -. | sk --bind 'ctrl-t:execute(nvim {})+abort' --preview 'bat {} --color=always' $argv
        
end
