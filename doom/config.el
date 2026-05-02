;;; $DOOMDIR/config.el -*- lexical-binding: t; -*-

;; Place your private configuration here! Remember, you do not need to run 'doom
;; sync' after modifying this file!


;; Some functionality uses this to identify you, e.g. GPG configuration, email
;; clients, file templates and snippets. It is optional.
;; (setq user-full-name "John Doe"
;;       user-mail-address "john@doe.com")

;; Doom exposes five (optional) variables for controlling fonts in Doom:
;;
;; - `doom-font' -- the primary font to use
;; - `doom-variable-pitch-font' -- a non-monospace font (where applicable)
;; - `doom-big-font' -- used for `doom-big-font-mode'; use this for
;;   presentations or streaming.
;; - `doom-symbol-font' -- for symbols
;; - `doom-serif-font' -- for the `fixed-pitch-serif' face
;;
;; See 'C-h v doom-font' for documentation and more examples of what they
;; accept. For example:
;;
;;(setq doom-font (font-spec :family "Fira Code" :size 12 :weight 'semi-light)
;;      doom-variable-pitch-font (font-spec :family "Fira Sans" :size 13))
;;
;; If you or Emacs can't find your font, use 'M-x describe-font' to look them
;; up, `M-x eval-region' to execute elisp code, and 'M-x doom/reload-font' to
;; refresh your font settings. If Emacs still can't find your font, it likely
;; wasn't installed correctly. Font issues are rarely Doom issues!

;; There are two ways to load a theme. Both assume the theme is installed and
;; available. You can either set `doom-theme' or manually load a theme with the
;; `load-theme' function. This is the default:
(setq doom-theme 'doom-one)

;; This determines the style of line numbers in effect. If set to `nil', line
;; numbers are disabled. For relative line numbers, set this to `relative'.
(setq display-line-numbers-type 'visual)

;; Whenever you reconfigure a package, make sure to wrap your config in an
;; `after!' block, otherwise Doom's defaults may override your settings. E.g.
;;
;;   (after! PACKAGE
;;     (setq x y))
;;
;; The exceptions to this rule:
;;
;;   - Setting file/directory variables (like `org-directory')
;;   - Setting variables which explicitly tell you to set them before their
;;     package is loaded (see 'C-h v VARIABLE' to look up their documentation).
;;   - Setting doom variables (which start with 'doom-' or '+').
;;
;; Here are some additional functions/macros that will help you configure Doom.
;;
;; - `load!' for loading external *.el files relative to this one
;; - `use-package!' for configuring packages
;; - `after!' for running code after a package has loaded
;; - `add-load-path!' for adding directories to the `load-path', relative to
;;   this file. Emacs searches the `load-path' when you load packages with
;;   `require' or `use-package'.
;; - `map!' for binding new keys
;;
;; To get information about any of these functions/macros, move the cursor over
;; the highlighted symbol at press 'K' (non-evil users must press 'C-c c k').
;; This will open documentation for it, including demos of how they are used.
;; Alternatively, use `C-h o' to look up a symbol (functions, variables, faces,
;; etc).
;;
;; You can also try 'gd' (or 'C-c c d') to jump to their definition and see how
;; they are implemented.

;; Options
(setq! scroll-margin 10
       display-line-numbers 'visual)
(setq-default tab-width 4)
(setq! evil-shift-width 4)
(setq! which-key-idle-delay 0.1)
(setq doom-font (font-spec :size 16))
(setq doom-big-font doom-font)
;; TODO: set tab width to 2 spaces in elisp

;; enter calc already in emacs mode
(add-hook 'calc-mode-hook 'evil-emacs-state)

;; rebind C-u and C-d to recenter the screen
(map! :n "C-u" nil)
(map! :n "C-d" nil)
(map! :n "C-u" (lambda () (interactive)
  (evil-scroll-up 25)
  (recenter)
))
(map! :n "C-d" (lambda () (interactive)
  (evil-scroll-down 25)
  (recenter)
))

;; Help grep
(map! :leader :n "h s" nil)
(map! :leader (:prefix ("h s" . "search")
  :desc "info"          :n "i" #'info-apropos
  :desc "commands"      :n "c" #'apropos-command
  :desc "documentation" :n "d" #'apropos-documentation
))


;; hide compilation menu when exiting without errors
(add-hook 'compilation-finish-functions
  (lambda (_buf str)
    (if (null (string-match ".*exited abnormally.*" str))
        ;;no errors, make the compilation window go away in a few seconds
        (progn
          (run-at-time
           "2 sec" nil 'delete-windows-on
           (get-buffer-create "*compilation*"))
          (message "No Compilation Errors!")))))

;; Org config
(after! org
  (setq org-directory "~/org/")
  (setq org-agenda-files '("~/org/agenda.org" "~/org/todo.org"))
  (setq org-roam-directory "~/notes/")
)

;; Custom templates to disable automatic linking to current file
(setq org-capture-templates
      '(("t" "Personal todo" entry (file+headline +org-capture-todo-file "Inbox")
         "* [ ] %?\n%i" :prepend nil)
        ("n" "Personal notes" entry (file+headline +org-capture-notes-file "Inbox")
         "* %u %?\n%i" :prepend t)
        ("j" "Journal" entry (file+olp+datetree +org-capture-journal-file)
         "* %U %?\n%i" :prepend t)

        ("c" "Templates with link to current file")
        ("ct" "Capture todo" entry (file+headline +org-capture-todo-file "Inbox")
         "* [ ] %?\n %i\n %a" :prepend nil)
        ("cn" "Capture notes" entry (file+headline +org-capture-notes-file "Inbox")
         "* %u %?\n %a\n %i" :prepend t)
        ("cj" "Capture journal" entry (file+headline +org-capture-journal-file "Inbox")
         "* %U %?\n %a\n %i" :prepend t)

        ("p" "Templates for projects")
        ("pt" "Project-local todo" entry
         (file+headline +org-capture-project-todo-file "Inbox") "* TODO %?\n%i\n%a"
         :prepend t)
        ("pn" "Project-local notes" entry
         (file+headline +org-capture-project-notes-file "Inbox") "* %U %?\n%i\n%a"
         :prepend t)
        ("pc" "Project-local changelog" entry
         (file+headline +org-capture-project-changelog-file "Unreleased")
         "* %U %?\n%i\n%a" :prepend t)

        ("o" "Centralized templates for projects")
        ("ot" "Project todo" entry #'+org-capture-central-project-todo-file
         "* TODO %?\n %i\n %a" :heading "Tasks" :prepend nil)
        ("on" "Project notes" entry #'+org-capture-central-project-notes-file
         "* %U %?\n %i\n %a" :heading "Notes" :prepend t)
        ("oc" "Project changelog" entry #'+org-capture-central-project-changelog-file
         "* %U %?\n %i\n %a" :heading "Changelog" :prepend t)
        ))

;; Custom org roam templates, TODO:
(setq org-roam-capture-templates
      '(("d" "default" plain "* %?"
         :target (file+head "${slug}.org" "#+title: ${title}\n")
         :unnarrowed t)
        ("s" "school" entry "* %?"
         :target (file+head "${slug}.org" "#+title: ${title}\n#+FILETAGS: :school:\n")
         :unnarrowed t)
))

;; NOTE: use C-k l* to insert a lambda char

;; ORG HOOKS
(after! org ;; Hooks that change default behaviour have to be loaded after the module
  (add-hook 'org-mode-hook (lambda () (electric-indent-local-mode -1)))) ;; Disable indent

;; M-<return> seems to work
(map! :after org
      :map evil-org-mode-map
      ;; Reamap all return combinations
      :ni "C-<return>"  #'+org/insert-item-below
      ;; :ni "M-<return>"  #'+org/insert-item-below
      ;; :ni "S-<return>"  #'+org/insert-item-below
      ;; :ni "C-S-<return>"  #'+org/insert-item-below
      ;; :ni "M-S-<return>"  #'+org/insert-item-below
      ;; :ni "C-M-<return>"  #'+org/insert-item-below
      ;; :ni "C-M-S-<return>"  #'+org/insert-item-below
      ;; MISC
      "M-o" #'org-mark-ring-goto
)
;; TODO: bind org-toggle-checkbox
