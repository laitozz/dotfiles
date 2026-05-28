-------------------
---- VARIABLES ----
-------------------

G = {}
G.mainMod = "SUPER" -- Sets "Windows" key as main modifier

G.term = "kitty"
G.terminal = "kitty fish -c ta"
G.fileManager = "dolphin"
G.browser = "firefox"
G.emacs = "emacsclient -c"
G.menu_wofi = "wofi --show drun"
G.menu_rofi = "rofi -show drun"
G.menu_tofi = "kitty -e \"$(tofi-run)\""
G.menu = G.menu_rofi

local function get_hostname()
  local handle = io.popen("hostname")
  if not handle then return nil end
  local result = handle:read("*l")
  handle:close()
  return result
end

G.hostname = get_hostname()

-------------------------------
---- ENVIRONMENT VARIABLES ----
-------------------------------

-- See https://wiki.hypr.land/Configuring/Advanced-and-Cool/Environment-variables/

hl.env("XCURSOR_SIZE", "24")
hl.env("HYPRCURSOR_SIZE", "24")
