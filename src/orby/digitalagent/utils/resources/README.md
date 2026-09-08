## injected-agent.js

This is a prebuilt Chrome extension content script, checked in as a binary
artifact. It is injected into every frame by
`orby.digitalagent.utils.env_utils.make` to expose page state to the agent.

The script is built from an internal Orby repository that is not public, so it
cannot be rebuilt from this repository. Use the checked-in file as-is. If you
need different behaviour, replace this file with your own script; the only
requirement is that it is valid JavaScript that can run as a Playwright init
script.
