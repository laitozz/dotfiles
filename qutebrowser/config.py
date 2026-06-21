import catppuccin

catppuccin.setup(c, 'macha', True)
config.load_autoconfig(False)

c.tabs.position = "left"
c.tabs.last_close = "default-page"
c.tabs.select_on_remove = 'last-used'
c.url.searchengines = {
  'DEFAULT': 'http://localhost:8888/search?q={}',
  'aw': 'https://wiki.archlinux.org/?search={}',
  'gh': 'https://github.com/search?q={}',
  'no': 'https://search.nixos.org/options?channel=unstable&query={}',
  'np': 'https://search.nixos.org/packages?channel=unstable&query={}',
  'nh': 'https://home-manager-options.extranix.com/?query={}&release=master',
  'nw': 'https://wiki.nixos.org/w/index.php?search={}',
  'jetf': 'https://www.justetf.com/en/search.html?search=ALL&query={}',

  'b': 'https://search.brave.com/search?q={}',
  'd': 'https://duckduckgo.com?q={}',
  'g': 'https://google.com/search?query={}',
  'm': 'https://mojeek.com/search?q={}',
  'dg': 'https://degoog.org?q={}',
}
c.url.default_page = "localhost:8888/search"
c.editor.command = [ "kitty", "nvim", "{}" ]
c.content.blocking.method = "both"
c.content.blocking.adblock.lists = [
  'https://easylist.to/easylist/easylist.txt',
  'https://easylist.to/easylist/easyprivacy.txt',
]
c.scrolling.smooth = True
c.fonts.default_size = '14pt'
c.fonts.hints = "bold 14pt default_family"
c.fonts.keyhint = 'default_size default_family'
c.colors.webpage.darkmode.enabled = True
c.colors.webpage.preferred_color_scheme = 'dark'
c.colors.webpage.darkmode.algorithm = 'lightness-cielab'
c.input.insert_mode.auto_enter = True
c.input.insert_mode.auto_leave = False

#########
# Binds #
#########

# Leader
config.bind('<space>r', "config-source")
config.bind('<space>e', "config-edit")
config.bind('<space>h', "cmd-set-text -s :help -t")
config.bind('<space>m', "spawn mpv {url}")
config.bind('<space>c', "open -t {clipboard}")
config.bind('<space>x', "open -t http://localhost:8888/preferences")
config.bind('<space>oc', "open -t https://claude.ai/new")
config.bind('<space>oh', "open -t https://hyperagent.com/threads/new")
config.bind(',o', "cmd-set-text :open -t !!")
config.bind(',u', "edit-url")
config.bind(',r', "greasemonkey-reload")
config.bind(',m', "hint links spawn mpv {hint-url}")
config.bind(',j', 'config-cycle content.javascript.enabled true false')
config.bind(',d', 'config-cycle colors.webpage.darkmode.enabled true false')
config.bind(',t', 'config-cycle tabs.position top left')
config.bind(',f', 'spawn --userscript focus_common_input.sh')

# Hints
# config.bind(';e', "hint inputs")

# Navigation
config.bind('x', "tab-close")
config.bind('d', 'cmd-run-with-count 12 scroll down') # for smooth scroll
config.bind('e', 'cmd-run-with-count 12 scroll up')
config.bind('E', 'tab-prev')
config.bind('R', 'tab-next')
config.bind('o', 'cmd-set-text -s :open -t')
config.bind('O', 'cmd-set-text -s :open')
config.bind('b', 'cmd-set-text -s :quickmark-load -t')
config.bind('B', 'cmd-set-text -s :quickmark-load')
config.bind('<Escape>', 'mode-leave ;; jseval -q document.activeElement.blur()', mode='insert')

config.bind('j', "spawn --userscript pass-j.sh")
config.bind('k', "spawn --userscript pass-k.sh")
config.bind('<Return>', "spawn --userscript pass-enter.sh")
config.bind('<Shift-Return>', "spawn --userscript pass-enter.sh")
