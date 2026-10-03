# Validation — 1.5.0

## Release coverage

The application test suite has 96 checks. It covers controller edges and chords,
semantic Anki actions, stale/foreground/busy guards, scrolling, language switching,
controller rendering and action feedback. New checks verify standard labels for
fresh settings and preserve saved reversed profiles without rewriting them.

The suite uses isolated settings and synthetic input/fake Anki objects; it does
not grade a user's collection. Linux validation passed with Python 3.14.7 and
PySide6 6.11.2. The public CI matrix runs Linux and Windows with Python 3.13/3.14.
Windows release automation builds the exported source and exercises the packaged
executable in English and Simplified Chinese on Mappings and Controller Test.

The earlier 1.5.0rc1 build was packaged and accepted by the project owner for normal
live controller/Anki use on Windows. The 1.5.0 changes set the new-profile label
default, preserve existing preferences and improve the release documentation and
packaging checks; they do not change the semantic review action protocol.

## Package evidence

[Releases](https://github.com/zixi526526/anki-grip/releases) provides the tagged
Windows x64 package, checksums and build links. Each bundle includes
`build-info.json`, `SHA256SUMS.txt`, dependency notices, license texts and
`DEPENDENCY_SOURCES.md` with the upstream library sources and rebuild directions.

## Remaining coverage

An exhaustive controller/transport/Anki-version matrix, all display-scaling
levels and a clean-machine test without Python have not been established.
See the [coverage checklist](docs/RELEASE_CHECKLIST.md). Synthetic tests and a
Windows package smoke test are not proof of every hardware combination.
