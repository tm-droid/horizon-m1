# Horizon relocation (2026-11-10)
Old: ~/Library/Application Support/ElyPrismLauncher/outputs/horizon-runtime/launcher-app/Horizon.app -> /Applications/Horizon.app
Old: .../horizon-runtime/launcher-data -> ~/Library/Application Support/horizon-launcher
Old: .../horizon-runtime/game -> ~/Library/Application Support/horizon
Old: .../horizon-runtime (scripts, m1-performance-r*, toolchain, ...) -> ~/Developer/Horizon/outputs/horizon-runtime (scripts/ and builds/ are symlinks to it)
Old: ElyPrismLauncher/outputs/horizon-{compatibility,converter,native,native-packs,src-nightly} -> ~/Developer/Horizon/outputs/
Old: ElyPrismLauncher/{tools,tests,docs}/horizon* -> ~/Developer/Horizon/{tools,tests,docs}/
Scripts compute ROOT from __file__ (ROOT/outputs/horizon-runtime), so ~/Developer/Horizon is the new ROOT. horizon-runtime/{launcher-data,game,launcher-app/Horizon.app} are symlinks to the new homes.
Historical .json/.md/.log records still contain the old absolute paths on purpose.
