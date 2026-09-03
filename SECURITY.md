# Security

Report privately to eric@smejkal.design. Don't open a public issue for these.

What counts:

- anything that makes brainbuddy read the contents of a note. It counts files with
  `glob` and `stat` and never calls `open()`. A path that gets it reading is a bug
  of this kind even if nothing is printed.
- anything that leaks a path or a filename into output, a log, or a crash trace,
  including `doctor`.
- any network call outside the documented explicit commands. Nothing on the render
  path or in a hook should ever touch the network.
- anything that writes outside `~/.claude/brainbuddy/` and the statusline shim it
  installs, or that runs code it found in a note.

Expect a reply within a few days. Please include the version from `brainbuddy doctor`
and enough to reproduce. Scrub your own paths before sending; that's the whole point.
