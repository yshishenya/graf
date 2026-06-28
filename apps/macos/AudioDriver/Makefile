CXX ?= clang++
CXXFLAGS ?= -std=c++17 -Wall -Wextra -Werror
BUILD_DIR ?= .build/proof
PROOF_BIN := $(BUILD_DIR)/audio-driver-proof
RUNTIME_PROBE_BIN := $(BUILD_DIR)/runtime-device-probe
HAL_IO_PROBE_BIN := $(BUILD_DIR)/hal-io-probe
PLUGIN_BUNDLE := $(BUILD_DIR)/GrafProof.driver
PLUGIN_BINARY := $(PLUGIN_BUNDLE)/Contents/MacOS/GrafProof
PLUGIN_INSTALL_DIR := /Library/Audio/Plug-Ins/HAL
PROOF_SOURCES := \
	Sources/Proof/ProofRunner.cpp \
	Sources/Proof/VirtualDeviceProof.cpp \
	Sources/Proof/PassthroughTimingProof.cpp \
	Sources/Proof/SharedAudioBufferProof.cpp \
	Sources/Routing/MicrophoneRoute.cpp \
	Sources/Routing/SpeakerRoute.cpp \
	Sources/Timing/TrackClock.cpp
RUNTIME_PROBE_SOURCES := Sources/Proof/RuntimeDeviceProbe.cpp
HAL_IO_PROBE_SOURCES := Sources/Proof/HALIOProbe.cpp
PLUGIN_SOURCES := \
	Sources/Plugin/GrafProofDriver.cpp \
	Sources/Device/VirtualDeviceRegistry.cpp \
	Sources/Bridge/AudioBridge.cpp
PLUGIN_HEADERS := \
	Sources/Device/VirtualDeviceRegistry.hpp \
	Sources/Bridge/SharedAudioBuffer.hpp

.PHONY: proof-scaffold-build proof-scaffold-run proof-runtime-probe-build proof-runtime-probe-run proof-hal-io-probe-build proof-hal-io-probe-run proof-plugin-build proof-plugin-install proof-plugin-uninstall proof-plugin-trace-reset proof-plugin-trace-enable proof-plugin-trace-disable proof-plugin-trace-read clean

proof-scaffold-build: $(PROOF_BIN)

proof-scaffold-run: proof-scaffold-build
	@$(PROOF_BIN)

proof-runtime-probe-build: $(RUNTIME_PROBE_BIN)

proof-runtime-probe-run: proof-runtime-probe-build
	@$(RUNTIME_PROBE_BIN) $(RUNTIME_PROBE_ARGS)

proof-hal-io-probe-build: $(HAL_IO_PROBE_BIN)

proof-hal-io-probe-run: proof-hal-io-probe-build
	@$(HAL_IO_PROBE_BIN)

proof-plugin-build: $(PLUGIN_BINARY)

proof-plugin-install: proof-plugin-build
	sudo rm -rf "$(PLUGIN_INSTALL_DIR)/GrafProof.driver"
	sudo rm -rf "$(PLUGIN_INSTALL_DIR)/2brainRecProof.driver"
	sudo cp -R "$(PLUGIN_BUNDLE)" "$(PLUGIN_INSTALL_DIR)/"
	sudo xattr -cr "$(PLUGIN_INSTALL_DIR)/GrafProof.driver"
	sudo xattr -dr com.apple.provenance "$(PLUGIN_INSTALL_DIR)/GrafProof.driver" || true
	sudo xattr -dr com.apple.quarantine "$(PLUGIN_INSTALL_DIR)/GrafProof.driver" || true
	sudo killall coreaudiod

proof-plugin-uninstall:
	sudo rm -rf "$(PLUGIN_INSTALL_DIR)/GrafProof.driver"
	sudo rm -rf "$(PLUGIN_INSTALL_DIR)/2brainRecProof.driver"
	sudo killall coreaudiod || true

proof-plugin-trace-reset:
	sudo rm -f /tmp/graf-proof-driver.trace

proof-plugin-trace-enable:
	touch /tmp/graf-proof-driver.verbose
	@echo "Verbose plugin trace enabled for next coreaudiod/plugin restart."

proof-plugin-trace-disable:
	rm -f /tmp/graf-proof-driver.verbose

proof-plugin-trace-read:
	@test -f /tmp/graf-proof-driver.trace && tail -n 200 /tmp/graf-proof-driver.trace || true

$(PROOF_BIN): $(PROOF_SOURCES)
	@mkdir -p $(BUILD_DIR)
	$(CXX) $(CXXFLAGS) $(PROOF_SOURCES) -o $(PROOF_BIN)

$(RUNTIME_PROBE_BIN): $(RUNTIME_PROBE_SOURCES)
	@mkdir -p $(BUILD_DIR)
	$(CXX) $(CXXFLAGS) $(RUNTIME_PROBE_SOURCES) -framework CoreAudio -framework CoreFoundation -o $(RUNTIME_PROBE_BIN)

$(HAL_IO_PROBE_BIN): $(HAL_IO_PROBE_SOURCES)
	@mkdir -p $(BUILD_DIR)
	$(CXX) $(CXXFLAGS) $(HAL_IO_PROBE_SOURCES) -framework CoreAudio -framework CoreFoundation -o $(HAL_IO_PROBE_BIN)

$(PLUGIN_BINARY): $(PLUGIN_SOURCES) $(PLUGIN_HEADERS) Resources/ProofPlugin/Info.plist
	@mkdir -p "$(PLUGIN_BUNDLE)/Contents/MacOS"
	@cp Resources/ProofPlugin/Info.plist "$(PLUGIN_BUNDLE)/Contents/Info.plist"
	$(CXX) $(CXXFLAGS) -fvisibility=hidden -bundle $(PLUGIN_SOURCES) -framework CoreAudio -framework CoreFoundation -o $(PLUGIN_BINARY)
	codesign --force --sign - "$(PLUGIN_BUNDLE)"

clean:
	rm -rf $(BUILD_DIR)
